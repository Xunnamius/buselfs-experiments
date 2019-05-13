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
#include <string.h>
#include <limits.h>
#include <assert.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

#define IOSIZE 131072U
//#define IOSIZE INT_MAX
#define PATH_BUFF_SIZE 255U
#define CMD_BUFF_SIZE 512U
#define COPY_INTO_TIMES 1U // randomness written COPY_INTO_TIMES into same file

#ifndef BUSELFS_PATH // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "BUSELFS_PATH must be defined in vars.mk!"
    #endif
    #define BUSELFS_PATH "" // ! Dead code, but vscode needs it
#endif

#ifndef REPO_PATH // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "REPO_PATH must be defined in vars.mk!"
    #endif
    #define REPO_PATH "" // ! Dead code, but vscode needs it
#endif

#ifndef BLFS_SV_QUEUE_INCOMING_NAME // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "BLFS_SV_QUEUE_INCOMING_NAME must be defined in vars.mk!"
    #endif
    #define BLFS_SV_QUEUE_INCOMING_NAME "" // ! Dead code, but vscode needs it
#endif

#ifndef TRIALS_INT // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "TRIALS_INT must be defined in vars.mk!"
    #endif
    #define TRIALS_INT 0 // ! Dead code, but vscode needs it
#endif

#define MIN(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a < _b ? _a : _b; })

#define STRINGIZE(x) #x
#define STRINGIZE_VALUE_OF(x) STRINGIZE(x)

#define CMD_ARGS "write " STRINGIZE_VALUE_OF(BLFS_SV_QUEUE_INCOMING_NAME) " 1"

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

    if(!metrics->energy_uj || errno)
    {
        perror("fread");
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
 * Call out to sbctl, which will send a POSIX message instructing StrongBox to
 * switch ciphers at its earliest convenience.
 *
 * @return The result of system()
 */
int swap_ciphers()
{
    char path[PATH_BUFF_SIZE];
    char cmd[sizeof(path) + sizeof(CMD_ARGS) + 1];
    int retval = 0;

    get_real_path(path, STRINGIZE_VALUE_OF(BUSELFS_PATH), "build/sbctl");

    snprintf(cmd, sizeof cmd, "%s %s", path, CMD_ARGS);
    printf("swap_ciphers (call to shell): %s\n", cmd);

    retval = system(cmd);
    sync();

    return retval;
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
    char output_paths[3][PATH_BUFF_SIZE];

    FILE * flog_outputs[3];
    FILE * frandom;

    // Accept non-optional args core_type, fs_type, write_to
    if(argc != 4)
    {
        printf("Usage: sequential-freerun-wcs <core_type> <fs_type> <write_to>\n");
        printf("No trailing slash for <write_to>!\n");
        return -1;
    }

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);
    printf("write_to: %s\n", write_to);

    // Get read paths from shards

    for(size_t i = 0; i < 3; ++i)
    {
        char ident_shard[PATH_BUFF_SIZE];
        char path_shard[PATH_BUFF_SIZE];

        // ? fs_type has "%d" contained within it (passed from python)!
        snprintf(ident_shard, PATH_BUFF_SIZE, "results/sequential.%s.%s.results", core_type, fs_type);
        snprintf(path_shard, PATH_BUFF_SIZE, ident_shard, i + 1);

        get_real_path(output_paths[i], STRINGIZE_VALUE_OF(REPO_PATH), path_shard);

        printf("output_path[%d]: %s\n", i, output_paths[i]);

        errno = 0;

        flog_outputs[i] = fopen(output_paths[i], "a");

        if(!flog_outputs[i] || errno)
        {
            perror("failed to fopen output path");
            return 6;
        }
    }

    printf("RANDOM_PATH: %s\n", RANDOM_PATH);

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

    if(!fsk || errno)
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

    rewind(frandom);

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

        // ? WRITE initial whole file
        // ! This is part of the setup, not part of the experiment!

        u_int64_t write1len = fsize;
        char * randomnessCopy1 = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(write1len > 0)
        {
            u_int64_t bytesWritten1 = write(trialoutfd, randomnessCopy1, MIN(write1len, IOSIZE));

            if(bytesWritten1 <= 0)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 144;
            }

            write1len -= bytesWritten1;
            randomnessCopy1 = randomnessCopy1 + bytesWritten1;
        }

        // Make sure everything writes through
        sync();

        // ? READ 1/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        // Swap ciphers
        swap_ciphers();

        Metrics read1_metrics_start;
        retval = collect_metrics(&read1_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("+1 READ METRICS :: got start energy (uj): %"PRIu64"\n", read1_metrics_start.energy_uj);
        printf("+1 READ METRICS :: got start time (ns): %"PRIu64"\n", read1_metrics_start.time_ns);

        u_int64_t read1len = fsize / 2;
        char * read1back = malloc(read1len);
        char * read1backOriginal = read1back;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(read1len > 0)
        {
            u_int64_t bytesRead1 = read(trialoutfd, read1back, MIN(read1len, IOSIZE));

            if(bytesRead1 <= 0)
            {
                perror("read failed");
                monitor.ffinish(&monitor);
                return 15;
            }

            read1len -= bytesRead1;
            read1back = read1back + bytesRead1;
        }

        // Make sure anything relevant gets written through
        sync();

        Metrics read1_metrics_end;
        retval = collect_metrics(&read1_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("+1 READ METRICS :: got end energy (uj): %"PRIu64"\n", read1_metrics_end.energy_uj);
        printf("+1 READ METRICS :: got end time (ns): %"PRIu64"\n", read1_metrics_end.time_ns);

        free(read1backOriginal);

        // ? WRITE 3/4

        // Drop the page cache before the next write
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        // Swap ciphers
        swap_ciphers();

        Metrics write_metrics_start;
        retval = collect_metrics(&write_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("+2 WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write_metrics_start.energy_uj);
        printf("+2 WRITE METRICS:: got start time (ns): %"PRIu64"\n", write_metrics_start.time_ns);

        u_int64_t write2len = 3 * fsize / 4;
        char * randomnessCopy2 = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(write2len > 0)
        {
            u_int64_t bytesWritten = write(trialoutfd, randomnessCopy2, MIN(write2len, IOSIZE));

            if(bytesWritten <= 0)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 14;
            }

            write2len -= bytesWritten;
            randomnessCopy2 = randomnessCopy2 + bytesWritten;
        }

        // Make sure everything writes through
        sync();

        Metrics write_metrics_end;
        retval = collect_metrics(&write_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("+2 WRITE METRICS:: got end energy (uj): %"PRIu64"\n", write_metrics_end.energy_uj);
        printf("+2 WRITE METRICS:: got end time (ns): %"PRIu64"\n", write_metrics_end.time_ns);

        // ? READ 1 (the whole thing)

        // Again, drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        // Swap ciphers
        swap_ciphers();

        Metrics read2_metrics_start;
        retval = collect_metrics(&read2_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("+3 READ METRICS :: got start energy (uj): %"PRIu64"\n", read2_metrics_start.energy_uj);
        printf("+3 READ METRICS :: got start time (ns): %"PRIu64"\n", read2_metrics_start.time_ns);

        u_int64_t read2len = fsize;
        char * read2back = malloc(read2len);
        char * read2backOriginal = read2back;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(read2len > 0)
        {
            u_int64_t bytesRead2 = read(trialoutfd, read2back, MIN(read2len, IOSIZE));

            if(bytesRead2 <= 0)
            {
                perror("read failed");
                monitor.ffinish(&monitor);
                return 155;
            }

            read2len -= bytesRead2;
            read2back = read2back + bytesRead2;
        }

        // Make sure anything relevant gets written through
        sync();

        Metrics read2_metrics_end;
        retval = collect_metrics(&read2_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("+3 READ METRICS :: got end energy (uj): %"PRIu64"\n", read2_metrics_end.energy_uj);
        printf("+3 READ METRICS :: got end time (ns): %"PRIu64"\n", read2_metrics_end.time_ns);

        free(read2backOriginal);

        // ? Crunch results

        double w_energy = write_metrics_end.energy_uj - write_metrics_start.energy_uj;
        double w_duration = write_metrics_end.time_ns - write_metrics_start.time_ns;
        double w_power = w_energy * 1000.0 / w_duration;

        double r1_energy = read1_metrics_end.energy_uj - read1_metrics_start.energy_uj;
        double r1_duration = read1_metrics_end.time_ns - read1_metrics_start.time_ns;
        double r1_power = r1_energy * 1000.0 / r1_duration;

        double r2_energy = read2_metrics_end.energy_uj - read2_metrics_start.energy_uj;
        double r2_duration = read2_metrics_end.time_ns - read2_metrics_start.time_ns;
        double r2_power = r2_energy * 1000.0 / r2_duration;

        printf("==> READS (1) <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               r1_energy / 1000000.0,
               r1_duration / 1000000000.0,
               r1_power);

        printf("==> WRITES <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               w_energy / 1000000.0,
               w_duration / 1000000000.0,
               w_power);

        printf("==> READS (2) <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               r2_energy / 1000000.0,
               r2_duration / 1000000000.0,
               r2_power);

        // ? Output the results

        fprintf(flog_outputs[0],
                "r_energy: %f\nr_duration: %f\nr_power: %f\n---\n",
                r1_energy,
                r1_duration,
                r1_power);

        fprintf(flog_outputs[1],
                "w_energy: %f\nw_duration: %f\nw_power: %f\n---\n",
                w_energy,
                w_duration,
                w_power);

        fprintf(flog_outputs[2],
                "r_energy: %f\nr_duration: %f\nr_power: %f\n---\n",
                r2_energy,
                r2_duration,
                r2_power);

        close(trialoutfd);

        if(CLEANUP)
        {
            printf("removing target %s\n", writeout_target);
            remove(writeout_target);
        }

        // Flush the results
        fflush(flog_outputs[0]);
        fflush(flog_outputs[1]);
        fflush(flog_outputs[2]);
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

    free(randomness);
    printf("Done!\n");

    fclose(flog_outputs[0]);
    fclose(flog_outputs[1]);
    fclose(flog_outputs[2]);

    close(pcachefd);

    return 0;
}
