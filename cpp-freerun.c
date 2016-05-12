#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

#define PATH_BUFF_SIZE 255
#define CMD_BUFF_SIZE 512

const int TRIALS = 20;
const char * REPO_PATH = "/home/odroid/bd3/rsync/energy-AES-1"; // No trailing /
const int CLEANUP = 1;
const int NO_SHMOO = 1;

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
    return system(realpath);
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

int main(int argc, char * argv[])
{
    energymon monitor;
    char output_path[PATH_BUFF_SIZE];
    FILE * foutput;

    // Accept non-optional args core_type, fs_type, write_to
    if(argc != 4)
    {
        printf("Usage: cpp-freerun <core_type> <fs_type> <write_to>");
        printf("No trailing slash for <write_to>!");
        return -1;
    }

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];

    printf("core_type: %s", core_type);
    printf("fs_type: %s", fs_type);
    printf("write_to: %s", write_to);

    if(energymon_get_default(&monitor))
    {
        perror("energymon_get_default");
        return 1;
    }

    if(monitor.finit(&monitor))
    {
        perror("finit");
        return 2;
    }

    char path_shard[PATH_BUFF_SIZE];
    snprintf(path_shard, PATH_BUFF_SIZE, "results/shmoo.%s.%s.results", core_type, fs_type);
    get_real_path(output_path, path_shard);

    foutput = fopen(output_path, "a");

    // Begin the trials
    int trials = TRIALS;

    while(trials--)
    {
        uint64_t time_start_ns;
        uint64_t time_end_ns;
        uint64_t energy_start_uj;
        uint64_t energy_end_uj;
        double power;
        double energy;
        double duration;

        int trial = TRIALS - trials;
        printf("--> beginning trial %d of %d", trial, TRIALS);

        char write_cmd[CMD_BUFF_SIZE];
        char read_cmd[CMD_BUFF_SIZE];
        char target[PATH_BUFF_SIZE];

        snprintf(target, PATH_BUFF_SIZE, "%s/%d", write_to, trial);
        snprintf(write_cmd, CMD_BUFF_SIZE, "dd-write.sh %s %s %s", target, core_type, fs_type);
        snprintf(read_cmd, CMD_BUFF_SIZE, "dd-read.sh %s %s %s", target, core_type, fs_type);

        printf("target: %s", target);
        printf("write_cmd: %s", write_cmd);
        printf("read_cmd: %s", read_cmd);

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

        // Run the dd-write and then dd-read
        int write_ret = callsys(write_cmd);
        printf("write_cmd returned %d", write_ret);
        int read_ret = callsys(read_cmd);
        printf("read_cmd returned %d", read_ret);

        // Grab the terminal energy use and time
        errno = 0;
        energy_end_uj = monitor.fread(&monitor);

        if(!energy_end_uj && errno)
        {
            perror("fread");
            monitor.ffinish(&monitor);
            return 3;
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
            printf("removing target %s", target);
            remove(target);
        }
    }

    if(NO_SHMOO)
        fprintf(foutput, "%s", "mf: 0x10 2000000");

    if(monitor.ffinish(&monitor))
    {
        perror("ffinish");
        return 5;
    }
    
    printf("Finished reading\n");
    fclose(foutput);

    return 0;
}
