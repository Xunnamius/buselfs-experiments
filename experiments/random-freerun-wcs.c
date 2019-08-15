#define _XOPEN_SOURCE 500
#define _FILE_OFFSET_BITS 64

// * Experiment 4

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

#define RETURN_PRIMARY_LENGTH 0
#define RETURN_SWAP_LENGTH 1

#define IOSIZE 131072U
//#define IOSIZE INT_MAX
#define SRAND_SEED1 76532543U
#define SRAND_SEED2 34567970U
#define SRAND_SEED3 25349875U
#define SRAND_SEED4 57968308U
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
#define MAX(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a > _b ? _a : _b; })

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

    if(retval)
    {
        printf("swap_ciphers (call to shell) failed with retval: %i\n", retval);
        exit(retval);
    }

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

/**
 * Calculates the length of the operation (in bytes) using fsize and swap_ratio,
 * which details how much of the I/O operations are reserved for the swap
 * cipher. primary_or_swap determines which percentage of the backing store, in
 * bytes, is returned.
 */
u_int64_t calc_len(u_int64_t fsize, int swap_ratio, int primary_or_swap)
{
    u_int64_t result = 0;

    if(swap_ratio == 1)
        result = llabs(fsize * 25 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? fsize : 0));

    else if(swap_ratio == 2)
        result = fsize / 2;

    else if(swap_ratio == 3)
        result = llabs(fsize * 75 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? fsize : 0));

    return result;
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

    // ? Accept non-optional args core_type, fs_type, write_to, swap_ratio
    if(argc != 5)
    {
        printf("Usage: random-freerun-wcs <core_type> <fs_type> <write_to> <swap_ratio>\n");
        printf("<swap_ratio> must be either: 1 (25%% swap), 2 (50%% swap), 3 (75%% swap)!\n");
        printf("No trailing slash for <write_to>!\n");
        return 253;
    }

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];
    char * swap_ratio_str = argv[4];
    int swap_ratio = 2;

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);
    printf("write_to: %s\n", write_to);
    printf("swap_ratio_str: %s\n", swap_ratio_str);

    if(strcmp(swap_ratio_str, "1") == 0)
        swap_ratio = 1;

    else if(strcmp(swap_ratio_str, "2") == 0)
        swap_ratio = 2;

    else if(strcmp(swap_ratio_str, "3") == 0)
        swap_ratio = 3;

    else
    {
        printf("<swap_ratio> must be either: 1 (25%% swap), 2 (50%% swap), 3 (75%% swap)!\n");
        return 254;
    }

    // Get read path from shards

    char path_shard[PATH_BUFF_SIZE];
    snprintf(path_shard, PATH_BUFF_SIZE, "results/random_freerun_wcs.%s.%s.results", core_type, fs_type);
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

        // ? WRITE 1/2

        Metrics write1_metrics_start;
        retval = collect_metrics(&write1_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("1 WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write1_metrics_start.energy_uj);
        printf("1 WRITE METRICS:: got start time (ns): %"PRIu64"\n", write1_metrics_start.time_ns);

        u_int64_t write1len = calc_len(fsize, swap_ratio, RETURN_PRIMARY_LENGTH);
        char * randomnessCopy1 = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);
        srand(SRAND_SEED1);

        while(write1len > 0)
        {
            errno = 0;

            u_int64_t iosize1_actual = MAX(MIN(write1len / 2, IOSIZE), 1U);
            u_int64_t seeklimit1 = write1len - iosize1_actual;
            u_int64_t offset1 = rand() % seeklimit1;
            u_int64_t bytesWritten1 = pwrite(
                trialoutfd,
                randomnessCopy1 + offset1,
                iosize1_actual,
                offset1
            );

            if(errno)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 14;
            }

            write1len -= bytesWritten1;
            //randomnessCopy1 = randomnessCopy1 + bytesWritten1;
        }

        // Make sure everything writes through
        sync();

        Metrics write1_metrics_end;
        retval = collect_metrics(&write1_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("1 WRITE METRICS:: got end energy (uj): %"PRIu64"\n", write1_metrics_end.energy_uj);
        printf("1 WRITE METRICS:: got end time (ns): %"PRIu64"\n", write1_metrics_end.time_ns);

        // ? READ 1/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        Metrics read1_metrics_start;
        retval = collect_metrics(&read1_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("1 READ METRICS :: got start energy (uj): %"PRIu64"\n", read1_metrics_start.energy_uj);
        printf("1 READ METRICS :: got start time (ns): %"PRIu64"\n", read1_metrics_start.time_ns);

        u_int64_t read1len = calc_len(fsize, swap_ratio, RETURN_PRIMARY_LENGTH);
        char * read1back = malloc(read1len);
        char * read1backOriginal = read1back;

        lseek64(trialoutfd, 0, SEEK_SET);
        srand(SRAND_SEED2);

        while(read1len > 0)
        {
            errno = 0;

            u_int64_t iosize1_actual = MAX(MIN(read1len / 2, IOSIZE), 1U);
            u_int64_t seeklimit1 = read1len - iosize1_actual;
            u_int64_t offset1 = rand() % seeklimit1;
            u_int64_t bytesRead1 = pread(
                trialoutfd,
                read1back,
                iosize1_actual,
                offset1
            );

            if(errno)
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

        printf("1 READ METRICS :: got end energy (uj): %"PRIu64"\n", read1_metrics_end.energy_uj);
        printf("1 READ METRICS :: got end time (ns): %"PRIu64"\n", read1_metrics_end.time_ns);

        free(read1backOriginal);

        // ? Schedule a cipher swap

        swap_ciphers();

        // ? WRITE 2/2

        // Drop the page cache before the next write
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        Metrics write2_metrics_start;
        retval = collect_metrics(&write2_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("2 WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write2_metrics_start.energy_uj);
        printf("2 WRITE METRICS:: got start time (ns): %"PRIu64"\n", write2_metrics_start.time_ns);

        u_int64_t write2len = calc_len(fsize, swap_ratio, RETURN_SWAP_LENGTH);
        char * randomnessCopy2 = randomness;

        // ? Start writing at the end of the initial write
        lseek64(trialoutfd, calc_len(fsize, swap_ratio, RETURN_PRIMARY_LENGTH), SEEK_SET);
        srand(SRAND_SEED3);

        while(write2len > 0)
        {
            errno = 0;

            u_int64_t iosize2_actual = MAX(MIN(write2len / 2, IOSIZE), 1U);
            u_int64_t seeklimit2 = write2len - iosize2_actual;
            u_int64_t offset2 = rand() % seeklimit2;
            u_int64_t bytesWritten2 = pwrite(
                trialoutfd,
                randomnessCopy2 + offset2,
                iosize2_actual,
                offset2
            );

            if(errno)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 144;
            }

            write2len -= bytesWritten2;
            //randomnessCopy2 = randomnessCopy2 + bytesWritten;
        }

        // Make sure everything writes through
        sync();

        Metrics write2_metrics_end;
        retval = collect_metrics(&write2_metrics_end, &monitor);

        if(retval != 0)
            return retval;

        printf("2 WRITE METRICS:: got end energy (uj): %"PRIu64"\n", write2_metrics_end.energy_uj);
        printf("2 WRITE METRICS:: got end time (ns): %"PRIu64"\n", write2_metrics_end.time_ns);

        // ? READ 2/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        Metrics read2_metrics_start;
        retval = collect_metrics(&read2_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("2 READ METRICS :: got start energy (uj): %"PRIu64"\n", read2_metrics_start.energy_uj);
        printf("2 READ METRICS :: got start time (ns): %"PRIu64"\n", read2_metrics_start.time_ns);

        u_int64_t read2len = calc_len(fsize, swap_ratio, RETURN_SWAP_LENGTH);
        char * read2back = malloc(read2len);
        char * read2backOriginal = read2back;

        // ? Start reading at the end of the initial write
        lseek64(trialoutfd, calc_len(fsize, swap_ratio, RETURN_PRIMARY_LENGTH), SEEK_SET);
        srand(SRAND_SEED4);

        while(read2len > 0)
        {
            errno = 0;

            u_int64_t iosize2_actual = MAX(MIN(read2len / 2, IOSIZE), 1U);
            u_int64_t seeklimit2 = read2len - iosize2_actual;
            u_int64_t offset2 = rand() % seeklimit2;
            u_int64_t bytesRead2 = pread(
                trialoutfd,
                read2back,
                iosize2_actual,
                offset2
            );

            if(errno)
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

        printf("2 READ METRICS :: got end energy (uj): %"PRIu64"\n", read2_metrics_end.energy_uj);
        printf("2 READ METRICS :: got end time (ns): %"PRIu64"\n", read2_metrics_end.time_ns);

        free(read2backOriginal);

        // ? Crunch results

        double w1_energy = write1_metrics_end.energy_uj - write1_metrics_start.energy_uj;
        double w1_duration = write1_metrics_end.time_ns - write1_metrics_start.time_ns;
        double w1_power = w1_energy * 1000.0 / w1_duration;

        double r1_energy = read1_metrics_end.energy_uj - read1_metrics_start.energy_uj;
        double r1_duration = read1_metrics_end.time_ns - read1_metrics_start.time_ns;
        double r1_power = r1_energy * 1000.0 / r1_duration;

        double w2_energy = write2_metrics_end.energy_uj - write2_metrics_start.energy_uj;
        double w2_duration = write2_metrics_end.time_ns - write2_metrics_start.time_ns;
        double w2_power = w2_energy * 1000.0 / w2_duration;

        double r2_energy = read2_metrics_end.energy_uj - read2_metrics_start.energy_uj;
        double r2_duration = read2_metrics_end.time_ns - read2_metrics_start.time_ns;
        double r2_power = r2_energy * 1000.0 / r2_duration;

        double w_energy = (w1_energy + w2_energy) / 2.0;
        double w_duration = (w1_duration + w2_duration) / 2.0;
        double w_power = (w1_power + w2_power) / 2.0;

        double r_energy = (r1_energy + r2_energy) / 2.0;
        double r_duration = (r1_duration + r2_duration) / 2.0;
        double r_power = (r1_power + r2_power) / 2.0;

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
