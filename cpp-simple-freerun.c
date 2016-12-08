#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <signal.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

#define PATH_BUFF_SIZE 255
#define CMD_BUFF_SIZE 512
#define COPY_INTO_TIMES 1 // randomness written COPY_INTO_TIMES into same file

const int TRIALS = 20;
const char * REPO_PATH = "/home/odroid/bd3/repos/energy-AES-1"; // No trailing /
const char * RANDOM_PATH = "/home/odroid/bd3/repos/energy-AES-1/data.random";
const int CLEANUP = 0;
const int NO_SHMOO = 1;

// Prepare to catch interrupt
static volatile int keepRunning = 1;

// Working now!
void interrupt_handler(int dummy)
{
    keepRunning = 0;
}

/**
 * Appends path to REPO_PATH, separated by a /, and places it in buff. A maximum
 * of PATH_BUFF_SIZE bytes will be written into buff.
 *
 * @param  buff Buffer to put the resultant string into
 * @param  path String to append to the end of REPO_PATH
 *
 * @return      The result of snprintf()
 */
int get_real_path(char * buff, const char * path)
{
    return snprintf(buff, PATH_BUFF_SIZE, "%s/%s", REPO_PATH, path);
}

/**
 * Returns the result of calling system(x) where x is the string
 * REPO_PATH + "/" + exec_path (see below). Path will at most be PATH_BUFF_SIZE
 * bytes in size.
 *
 * @param  exec_path Path to the executable file starting at REPO_PATH
 *
 * @return           The result of system()
 */
int callsys(const char * exec_path)
{
    char realpath[PATH_BUFF_SIZE];
    get_real_path(realpath, exec_path);
    printf("callsys: %s\n", realpath);
    return system(realpath);
}

int main(int argc, char * argv[])
{
    uid_t euid = geteuid();

    if(euid != 0)
    {
        printf("Must run this as root!\n");
        return -2;
    }

    struct sigaction act;
    act.sa_handler = interrupt_handler;
    sigaction(SIGINT, &act, NULL);

    energymon monitor;
    char output_path[PATH_BUFF_SIZE];
    FILE * foutput;
    FILE * frandom;

    // Accept non-optional args core_type, fs_type, write_to
    if(argc != 4)
    {
        printf("Usage: cpp-freerun <core_type> <fs_type> <write_to>\n");
        printf("No trailing slash for <write_to>!\n");
        return -1;
    }

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);
    printf("write_to: %s\n", write_to);

    // Get read path from shards

    char path_shard[PATH_BUFF_SIZE];
    snprintf(path_shard, PATH_BUFF_SIZE, "results/shmoo.%s.%s.results", core_type, fs_type);
    get_real_path(output_path, path_shard);
    
    printf("output_path: %s\n", output_path);
    
    errno = 0;
    foutput = fopen(output_path, "a");
    
    if(!foutput && errno)
    {
        perror("failed to fopen output_path");
        return 6;
    }

    // Read entire randomness file into memory buffer
    
    errno = 0;
    frandom = fopen(RANDOM_PATH, "rb+");

    if(!frandom && errno)
    {
        perror("failed to fopen RANDOM_PATH");
        return 8;
    }

    int fsk = 0;
    errno = 0;

    fsk = fseek(frandom, 0, SEEK_END);

    if(!fsk && errno)
    {
        perror("failed to fseek RANDOM_PATH");
        return 9;
    }

    errno = 0;
    long fsize = ftell(frandom);

    if(fsize < 0 && errno)
    {
        perror("ftell failed on RANDOM_PATH");
        return 10;
    }

    errno = 0;
    rewind(frandom);

    if(errno)
    {
        perror("failed to rewind RANDOM_PATH");
        return 9;
    }

    errno = 0;
    char * randomness = malloc(fsize + 1); // + the NULL TERMINATOR

    if(!randomness && errno)
    {
        perror("malloc failed");
        return 11;
    }

    errno = 0;
    size_t frd = fread(randomness, fsize, 1, frandom);

    if(frd != fsize && errno)
    {
        perror("fread of RANDOM_PATH failed");
        return 12;
    }

    // Close randomness file
    fclose(frandom);

    // Add the NULL TERMINATOR for good measure
    randomness[fsize] = 0;

    printf("randomness fsize (+1): %ld\n", fsize);

    // Setup energymon
    errno = 0;

    if(energymon_get_default(&monitor))
    {
        perror("energymon_get_default");
        return 1;
    }

    errno = 0;

    if(monitor.finit(&monitor))
    {
        perror("finit");
        return 2;
    }

    // Begin the trials
    int trials = TRIALS;
    int pcachefd = open("/proc/sys/vm/drop_caches", O_WRONLY);

    const char * droppcache = "3";

    while(keepRunning && trials--)
    {
        uint64_t time_start_ns;
        uint64_t time_end_ns;
        uint64_t energy_start_uj;
        uint64_t energy_end_uj;
        double power;
        double energy;
        double duration;

        int trial = TRIALS - trials;
        printf("--> beginning trial %d of %d\n", trial, TRIALS);

        /*char write_cmd[CMD_BUFF_SIZE];
        char read_cmd[CMD_BUFF_SIZE];*/
        char target[PATH_BUFF_SIZE];

        snprintf(target, PATH_BUFF_SIZE, "%s/%d", write_to, trial);
        /*snprintf(write_cmd, CMD_BUFF_SIZE, "dd-write.sh %s %s %s", target, core_type, fs_type);
        snprintf(read_cmd, CMD_BUFF_SIZE, "dd-read.sh %s %s %s", target, core_type, fs_type);*/

        printf("target: %s\n", target);
        /*printf("write_cmd: %s\n", write_cmd);
        printf("read_cmd: %s\n", read_cmd);*/

        // Grab the initial energy use and time
        errno = 0;
        energy_start_uj = monitor.fread(&monitor);

        if(!energy_start_uj && errno)
        {
            perror("fread");
            monitor.ffinish(&monitor);
            return 3;
        }
        
        printf("got start reading: %"PRIu64"\n", energy_start_uj);
        time_start_ns = energymon_gettime_ns();
        printf("got start time: %"PRIu64"\n", time_start_ns);

        // Run the experiment here
        // energymon_sleep_us(2000000); // Sleep for two seconds

        /*// Run the dd-write and then dd-read
        int write_ret = callsys(write_cmd);
        printf("write_cmd returned %d\n", write_ret);
        int read_ret = callsys(read_cmd);
        printf("read_cmd returned %d\n", read_ret);*/

        // Run the simpler version of the experiment with writes coming from the
        // random oracle file RANDOM_PATH, i.e. randomness
        unsigned int times = COPY_INTO_TIMES;
        // | O_DIRECT | O_SYNC
        int trailoutf = open(target, O_CREAT | O_RDWR | O_SYNC, 0777);

        if(trailoutf < 0)
        {
            fprintf(stderr, "%s\n", "open failed");
            monitor.ffinish(&monitor);
            return 13;
        }

        /*while(times--)
        {*/
            // Write should be small enough to go through in one pass without a
            // loop, but we check just in case (marked FIXME:)
            size_t wrtsize = write(trailoutf, randomness, fsize);
            if(wrtsize != fsize)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 14;
            }
        /*
        }*/

        sync();

        // Drop the page cache before the next read
        write(pcachefd, droppcache, sizeof(char));

        /*while(times--)
        {*/
            // Read should be small enough to go through in one pass without a
            // loop, but we check just in case (marked FIXME:)
            size_t rdsize = read(trailoutf, randomness, fsize);
            if(rdsize != fsize)
            {
                perror("read failed");
                monitor.ffinish(&monitor);
                return 15;
            }
        /*
        }*/
        
        // Grab the terminal energy use and time
        errno = 0;
        energy_end_uj = monitor.fread(&monitor);

        if(!energy_end_uj && errno)
        {
            perror("fread");
            monitor.ffinish(&monitor);
            return 4;
        }
        
        printf("got end reading: %"PRIu64"\n", energy_end_uj);
        time_end_ns = energymon_gettime_ns();
        printf("got end time: %"PRIu64"\n", time_end_ns);

        energy = energy_end_uj - energy_start_uj;
        duration = time_end_ns - time_start_ns;
        power = energy * 1000.0 / duration;

        printf("energy: %fuj\nduration: %fns\npower: %fw\n", energy, duration, power);

        // Output the results
        fprintf(foutput, "energy: %f\nduration: %f\npower: %f\n---\n", energy, duration, power);

        if(CLEANUP)
        {
            printf("removing target %s\n", target);
            remove(target);
        }

        // Flush the results
        fflush(foutput);
    }

    if(!keepRunning)
    {
        printf("Interrupted!\n");
        return 7;
    }

    if(NO_SHMOO)
        fprintf(foutput, "%s", "mf: 0x10 2000000\n");

    if(monitor.ffinish(&monitor))
    {
        perror("ffinish");
        return 5;
    }

    // Free randomness buffer
    free(randomness);
    
    printf("Done!\n");
    fclose(foutput);
    close(pcachefd);

    return 0;
}
