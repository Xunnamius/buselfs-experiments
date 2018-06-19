#define _XOPEN_SOURCE 500
#define _FILE_OFFSET_BITS 64

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <signal.h>
#include <limits.h>
#include <assert.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

#define IOSIZE 131072
//#define IOSIZE INT_MAX
#define SRAND_SEED1 76532543U
#define SRAND_SEED2 34567970U
#define PATH_BUFF_SIZE 255
#define CMD_BUFF_SIZE 512
#define COPY_INTO_TIMES 1 // randomness written COPY_INTO_TIMES into same file

#ifndef REPO_PATH
#define REPO_PATH "." // No trailing / ; see config/vars.mk
#endif

#ifndef TRIALS_INT
#define TRIALS_INT 10 // No trailing / ; see config/vars.mk
#endif

#define MIN(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a < _b ? _a : _b; })

const int CLEANUP = 0;

// For random data from /dev/urandom
const char * RANDOM_PATH = REPO_PATH"/data.target";

// Prepare to catch interrupt
static volatile int keepRunning = 1;

// Working now!
void interrupt_handler(int dummy)
{
    keepRunning = 0;
}

// Struct that holds duration/energy/power data
typedef struct Metrics {
    uint64_t time_ns;
    uint64_t energy_uj;
} Metrics;

int collect_metrics(Metrics * metrics, energymon * monitor)
{
    // Grab the initial energy use and time
    errno = 0;
    metrics->energy_uj = monitor->fread(monitor);

    if(!metrics->energy_uj && errno)
    {
        perror("fread");
        monitor->ffinish(monitor);
        return 3;
    }

    metrics->time_ns = energymon_gettime_ns();
    return 0;
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

    FILE * flog_output;
    FILE * frandom;

    // Accept non-optional args core_type, fs_type, write_to
    if(argc != 4)
    {
        printf("Usage: random-freerun <core_type> <fs_type> <write_to>\n");
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
    snprintf(path_shard, PATH_BUFF_SIZE, "results/random.%s.%s.results", core_type, fs_type);
    get_real_path(output_path, path_shard);
    
    printf("output_path: %s\n", output_path);
    
    errno = 0;
    flog_output = fopen(output_path, "a");
    
    if(!flog_output && errno)
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
    u_int64_t fsize = 0;
    fsize = ftell(frandom);

    if(fsize < 0 && errno)
    {
        perror("ftell failed on RANDOM_PATH");
        return 10;
    }

    u_int64_t iosize_actual = 0;
    u_int64_t seeklimit = 0;

    iosize_actual = MIN(fsize / 2, IOSIZE);
    seeklimit = fsize - iosize_actual;
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

    printf("randomness[fsize] (+1): %"PRIu64"\n", fsize);

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
    
    int pcachefd = open("/proc/sys/vm/drop_caches", O_WRONLY);
    const char * droppcache = "3";
    int trials = TRIALS_INT;

    while(keepRunning && trials--)
    {
        int retval = 0;
        int trial = TRIALS_INT - trials;

        printf("--> beginning trial %d of %d\n", trial, TRIALS_INT);

        char writeout_target[PATH_BUFF_SIZE];

        snprintf(writeout_target,
                 PATH_BUFF_SIZE,
                 "%s/%d",
                 write_to,
                 trial);

        printf("writeout_target: %s\n", writeout_target);

        Metrics write_metrics_start;
        retval = collect_metrics(&write_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write_metrics_start.energy_uj);
        printf("WRITE METRICS:: got start time (ns): %"PRIu64"\n", write_metrics_start.time_ns);

        // Run the simpler version of the experiment with writes coming from the
        // random oracle file RANDOM_PATH, i.e. randomness
        // unsigned int times = COPY_INTO_TIMES;
        // | O_DIRECT | O_SYNC
        int trialoutfd = open(writeout_target, O_CREAT | O_RDWR | O_SYNC, 0777);

        if(trialoutfd < 0)
        {
            fprintf(stderr, "open of %s failed\n", writeout_target);
            monitor.ffinish(&monitor);
            return 13;
        }

        u_int64_t writelen = fsize;
        char * randomnessCopy = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);
        srand(SRAND_SEED1);

        while(writelen > 0)
        {
            u_int64_t offset = rand() % seeklimit;
            u_int64_t bytesWritten = pwrite(trialoutfd, randomnessCopy + offset, iosize_actual, fsize - writelen);

            if(bytesWritten <= 0)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 14;
            }

            writelen -= bytesWritten;
            //randomnessCopy = randomnessCopy + bytesWritten;
        }

        // Make sure everything writes through
        sync();

        Metrics write_metrics_end;
        retval = collect_metrics(&write_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("WRITE METRICS:: got end energy (uj): %"PRIu64"\n", write_metrics_end.energy_uj);
        printf("WRITE METRICS:: got end time (ns): %"PRIu64"\n", write_metrics_end.time_ns);

        // Drop the page cache before the next read
        pwrite(pcachefd, droppcache, sizeof(char), 0);

        Metrics read_metrics_start;
        retval = collect_metrics(&read_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("READ METRICS :: got start energy (uj): %"PRIu64"\n", read_metrics_start.energy_uj);
        printf("READ METRICS :: got start time (ns): %"PRIu64"\n", read_metrics_start.time_ns);

        u_int64_t readlen = fsize;
        char * readback = malloc(readlen);
        char * readbackOriginal = readback;

        lseek64(trialoutfd, 0, SEEK_SET);
        srand(SRAND_SEED2);

        while(readlen > 0)
        {
            u_int64_t offset = rand() % seeklimit;
            u_int64_t bytesRead = pread(trialoutfd, readback, iosize_actual, offset);

            if(bytesRead <= 0)
            {
                perror("read failed");
                monitor.ffinish(&monitor);
                return 15;
            }

            readlen -= bytesRead;
            readback = readback + bytesRead;
        }

        Metrics read_metrics_end;
        retval = collect_metrics(&read_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("READ METRICS :: got end energy (uj): %"PRIu64"\n", read_metrics_end.energy_uj);
        printf("READ METRICS :: got end time (ns): %"PRIu64"\n", read_metrics_end.time_ns);

        free(readbackOriginal);

        // Crunch the results
        double w_energy = write_metrics_end.energy_uj - write_metrics_start.energy_uj;
        double w_duration = write_metrics_end.time_ns - write_metrics_start.time_ns;
        double w_power = w_energy * 1000.0 / w_duration;

        double r_energy = read_metrics_end.energy_uj - read_metrics_start.energy_uj;
        double r_duration = read_metrics_end.time_ns - read_metrics_start.time_ns;
        double r_power = r_energy * 1000.0 / r_duration;

        printf("==> WRITES <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               w_energy / 1000000.0,
               w_duration / 1000000000.0,
               w_power);

        printf("==> READS <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               r_energy / 1000000.0,
               r_duration / 1000000000.0,
               r_power);

        // Output the results
        fprintf(flog_output,
                "w_energy: %f\nw_duration: %f\nw_power: %f\nr_energy: %f\nr_duration: %f\nr_power: %f\n---\n",
                w_energy,
                w_duration,
                w_power,
                r_energy,
                r_duration,
                r_power);

        close(trialoutfd);

        if(CLEANUP)
        {
            printf("removing target %s\n", writeout_target);
            remove(writeout_target);
        }

        // Flush the results
        fflush(flog_output);
    }

    if(!keepRunning)
    {
        printf("Interrupted!\n");
        return 7;
    }

    if(monitor.ffinish(&monitor))
    {
        perror("ffinish");
        return 5;
    }

    if(!keepRunning)
    {
        printf("Interrupted!\n");
        return 7;
    }

    // Free randomness buffer
    free(randomness);
    printf("Done!\n");
    fclose(flog_output);
    close(pcachefd);

    return 0;
}
