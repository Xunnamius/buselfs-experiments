#define _XOPEN_SOURCE 500
#define _FILE_OFFSET_BITS 64

// * Experiment 2

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

#define IOSIZE 131072U
//#define IOSIZE INT_MAX
#define SRAND_SEED1 76532543U
#define SRAND_SEED2 34567970U
#define PATH_BUFF_SIZE 255U
#define CMD_BUFF_SIZE 512U
#define COPY_INTO_TIMES 1U // randomness written COPY_INTO_TIMES into same file

#ifndef REPO_PATH // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "REPO_PATH must be defined in vars.mk!"
    #endif
    #define REPO_PATH "" // ! Dead code, but vscode needs it
#endif

#ifndef TRIALS_INT // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "TRIALS_INT must be defined in vars.mk!"
    #endif
    #define TRIALS_INT 0 // ! Dead code, but vscode needs it
#endif

#define MIN(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a < _b ? _a : _b; })
#define MAX(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a > _b ? _a : _b; })

#define STRINGIZE(x) #x
#define STRINGIZE_VALUE_OF(x) STRINGIZE(x)

const int CLEANUP = 0;

// For random data from /dev/urandom
const char * RANDOM_PATH = STRINGIZE_VALUE_OF(REPO_PATH)"/data/data.target";

// Prepare to catch interrupt
static volatile int keepRunning = 1;

// Working now!
void interrupt_handler(int dummy)
{
    (void) dummy;
    keepRunning = 0;
}

// Struct that holds duration/energy/power data
typedef struct Metrics {
    uint64_t time_ns;
    uint64_t energy_uj;
} Metrics;

/**
 * Collect energy and timing metrics using energymon
 *
 * @return 0 if no error
 */
int collect_metrics(Metrics * metrics, energymon * monitor)
{
    errno = 0;

    // Grab the initial energy use and time
    metrics->energy_uj = monitor->fread(monitor);

    if(errno)
    {
        perror("energymon fread failure");
        monitor->ffinish(monitor);
        return 3;
    }

    metrics->time_ns = energymon_gettime_ns();
    return 0;
}

/**
 * Appends `path` to the `base` path, separated by a /, and places it in buff. A
 * maximum of PATH_BUFF_SIZE bytes will be written into buff.
 *
 * @return The result of snprintf()
 */
int get_real_path(char * buff, const char * base, const char * path)
{
    return snprintf(buff, PATH_BUFF_SIZE, "%s/%s", base, path);
}

/**
 * Wrapping your function call with ignore_result makes it more clear to
 * readers, compilers and linters that you are, in fact, ignoring the
 * function's return value on purpose.
 */
static inline void ignore_result(long long int unused_result)
{
    (void) unused_result;
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

    // ? Accept non-optional args core_type, fs_type, write_to
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
    snprintf(path_shard, PATH_BUFF_SIZE, "results/random_freerun.%s.%s.results", core_type, fs_type);
    get_real_path(output_path, STRINGIZE_VALUE_OF(REPO_PATH), path_shard);

    printf("output_path: %s\n", output_path);
    printf("RANDOM_PATH: %s\n", RANDOM_PATH);

    errno = 0;

    flog_output = fopen(output_path, "a");

    if(!flog_output || errno)
    {
        perror("failed to fopen output_path");
        return 6;
    }

    // Read entire randomness file into memory buffer

    errno = 0;

    frandom = fopen(RANDOM_PATH, "rb+");

    if(!frandom || errno)
    {
        perror("failed to fopen RANDOM_PATH");
        return 8;
    }

    errno = 0;

    int fsk = fseek(frandom, 0, SEEK_END);

    if(fsk || errno)
    {
        perror("failed to fseek RANDOM_PATH");
        return 9;
    }

    errno = 0;

    u_int64_t fsize = ftell(frandom);

    if(!fsize || errno)
    {
        perror("ftell failed on RANDOM_PATH");
        return 10;
    }

    errno = 0;

    fsk = fseek(frandom, 0, SEEK_SET);

    if(errno)
    {
        perror("failed to rewind RANDOM_PATH");
        return 9;
    }

    errno = 0;

    char * randomness = malloc(fsize + 1); // + the NULL TERMINATOR

    if(!randomness || errno)
    {
        perror("malloc failed");
        return 11;
    }

    errno = 0;

    size_t frd = fread(randomness, 1, fsize, frandom);

    if(frd != fsize || errno)
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

        int trialoutfd = open(writeout_target, O_CREAT | O_RDWR | O_SYNC, 0777);

        if(trialoutfd < 0)
        {
            fprintf(stderr, "open of %s failed\n", writeout_target);
            monitor.ffinish(&monitor);
            return 13;
        }

        // ? WRITE whole file

        Metrics write_metrics_start;
        retval = collect_metrics(&write_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write_metrics_start.energy_uj);
        printf("WRITE METRICS:: got start time (ns): %"PRIu64"\n", write_metrics_start.time_ns);

        u_int64_t writelen = fsize;
        char * randomnessCopy = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);
        srand(SRAND_SEED1);

        while(writelen > 0)
        {
            errno = 0;

            u_int64_t iosize_actual = MAX(MIN(writelen / 2, IOSIZE), 1U);
            u_int64_t seeklimit = writelen - iosize_actual;
            u_int64_t offset = !seeklimit ? 0 : rand() % seeklimit;
            u_int64_t bytesWritten = pwrite(trialoutfd, randomnessCopy + offset, iosize_actual, offset);

            if(errno)
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

        // ? READ whole file

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

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
            errno = 0;

            u_int64_t iosize_actual = MAX(MIN(readlen / 2, IOSIZE), 1U);
            u_int64_t seeklimit = readlen - iosize_actual;
            u_int64_t offset = !seeklimit ? 0 : rand() % seeklimit;
            u_int64_t bytesRead = pread(trialoutfd, readback, iosize_actual, offset);

            if(errno)
            {
                perror("read failed");
                monitor.ffinish(&monitor);
                return 15;
            }

            readlen -= bytesRead;
            readback = readback + bytesRead;
        }

        // Make sure anything relevant gets written through
        sync();

        Metrics read_metrics_end;
        retval = collect_metrics(&read_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("READ METRICS :: got end energy (uj): %"PRIu64"\n", read_metrics_end.energy_uj);
        printf("READ METRICS :: got end time (ns): %"PRIu64"\n", read_metrics_end.time_ns);

        free(readbackOriginal);

        // ? Crunch results

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

        // ? Output the results

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

        // ? Flush the results

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

    // ? Free randomness buffer

    free(randomness);
    fclose(flog_output);
    close(pcachefd);

    printf("Done!\n");

    return 0;
}
