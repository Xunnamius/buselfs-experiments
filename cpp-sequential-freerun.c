#define _XOPEN_SOURCE 500

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
#define PATH_BUFF_SIZE 255
#define CMD_BUFF_SIZE 512
#define COPY_INTO_TIMES 1 // randomness written COPY_INTO_TIMES into same file
#define REPO_PATH "/home/odroid/bd3/repos/energy-AES-1" // No trailing /

#define MIN(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a < _b ? _a : _b; })

const int TRIALS = 15;
const int CLEANUP = 0;
const int MOUNT_CLEANUP = 1;
const int NO_SHMOO = 1;

// For random data from /dev/urandom
const char * RANDOM_PATH_1 = REPO_PATH"/data.random0";
const char * RANDOM_PATH_2 = REPO_PATH"/data.random1";
const char * RANDOM_PATH_3 = REPO_PATH"/data.random2";
const char * RANDOM_PATH_4 = REPO_PATH"/data.random3";

const char * WRITE_OUT_1 = "/tmp/nbd0";
const char * WRITE_OUT_2 = "/tmp/nbd1";
const char * WRITE_OUT_3 = "/tmp/nbd2";
const char * WRITE_OUT_4 = "/tmp/nbd3";

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
    char output_path[4][PATH_BUFF_SIZE];

    FILE * flog_output[4];
    FILE * frandom[4];

    // Accept non-optional args core_type, fs_type, write_to
    if(argc != 3)
    {
        printf("Usage: cpp-freerun <core_type> <fs_type>\n");
        return -1;
    }

    char * core_type = argv[1];
    char * fs_type = argv[2];

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);

    // Get read path from shards

    char path_shard[4][PATH_BUFF_SIZE];

    snprintf(path_shard[0], PATH_BUFF_SIZE, "results/sequential-d0.%s.%s.results", core_type, fs_type);
    snprintf(path_shard[1], PATH_BUFF_SIZE, "results/sequential-d1.%s.%s.results", core_type, fs_type);
    snprintf(path_shard[2], PATH_BUFF_SIZE, "results/sequential-d2.%s.%s.results", core_type, fs_type);
    snprintf(path_shard[3], PATH_BUFF_SIZE, "results/sequential-d3.%s.%s.results", core_type, fs_type);

    get_real_path(output_path[0], path_shard[0]);
    get_real_path(output_path[1], path_shard[1]);
    get_real_path(output_path[2], path_shard[2]);
    get_real_path(output_path[3], path_shard[3]);
    
    printf("output_path[0]: %s\n", output_path[0]);
    printf("output_path[1]: %s\n", output_path[1]);
    printf("output_path[2]: %s\n", output_path[2]);
    printf("output_path[3]: %s\n", output_path[3]);
    
    errno = 0;

    flog_output[0] = fopen(output_path[0], "a");
    flog_output[1] = fopen(output_path[1], "a");
    flog_output[2] = fopen(output_path[2], "a");
    flog_output[3] = fopen(output_path[3], "a");
    
    if(!(flog_output[0] || flog_output[1] || flog_output[2] || flog_output[3]) && errno)
    {
        perror("failed to fopen output_path");
        return 6;
    }

    // Read entire randomness file into memory buffer
    
    errno = 0;

    frandom[0] = fopen(RANDOM_PATH_1, "rb+");
    frandom[1] = fopen(RANDOM_PATH_2, "rb+");
    frandom[2] = fopen(RANDOM_PATH_3, "rb+");
    frandom[3] = fopen(RANDOM_PATH_4, "rb+");

    if(!(frandom[0] || frandom[1] || frandom[2] || frandom[3]) && errno)
    {
        perror("failed to fopen RANDOM_PATH");
        return 8;
    }

    int fsk[4] = { 0 };

    errno = 0;

    fsk[0] = fseek(frandom[0], 0, SEEK_END);
    fsk[1] = fseek(frandom[1], 0, SEEK_END);
    fsk[2] = fseek(frandom[2], 0, SEEK_END);
    fsk[3] = fseek(frandom[3], 0, SEEK_END);

    if(!(fsk[0] || fsk[1] || fsk[2] || fsk[3]) && errno)
    {
        perror("failed to fseek RANDOM_PATH");
        return 9;
    }

    errno = 0;

    u_int64_t fsize[4] = { 0 };

    fsize[0] = ftell(frandom[0]);
    fsize[1] = ftell(frandom[1]);
    fsize[2] = ftell(frandom[2]);
    fsize[3] = ftell(frandom[3]);

    if((fsize[0] < 0 || fsize[1] < 0 || fsize[2] < 0 || fsize[3] < 0) && errno)
    {
        perror("ftell failed on RANDOM_PATH");
        return 10;
    }

    u_int64_t iosize_actual[4] = { 0 };

    iosize_actual[0] = MIN(fsize[0], IOSIZE);
    iosize_actual[1] = MIN(fsize[1], IOSIZE);
    iosize_actual[2] = MIN(fsize[2], IOSIZE);
    iosize_actual[3] = MIN(fsize[3], IOSIZE);

    errno = 0;

    rewind(frandom[0]);
    rewind(frandom[1]);
    rewind(frandom[2]);
    rewind(frandom[3]);

    if(errno)
    {
        perror("failed to rewind RANDOM_PATH");
        return 9;
    }

    errno = 0;
    char * randomness[4];

    randomness[0] = malloc(fsize[0] + 1); // + the NULL TERMINATOR
    randomness[1] = malloc(fsize[1] + 1); // + the NULL TERMINATOR
    randomness[2] = malloc(fsize[2] + 1); // + the NULL TERMINATOR
    randomness[3] = malloc(fsize[3] + 1); // + the NULL TERMINATOR

    if(!(randomness[0] || randomness[1] || randomness[2] || randomness[3]) && errno)
    {
        perror("malloc failed");
        return 11;
    }

    errno = 0;

    size_t frd[4];
    frd[0] = fread(randomness[0], fsize[0], 1, frandom[0]);
    frd[1] = fread(randomness[1], fsize[1], 1, frandom[1]);
    frd[2] = fread(randomness[2], fsize[2], 1, frandom[2]);
    frd[3] = fread(randomness[3], fsize[3], 1, frandom[3]);

    if((frd[0] != fsize[0] || frd[1] != fsize[1] || frd[2] != fsize[2] || frd[3] != fsize[3]) && errno)
    {
        perror("fread of RANDOM_PATH failed");
        return 12;
    }

    // Close randomness file
    fclose(frandom[0]);
    fclose(frandom[1]);
    fclose(frandom[2]);
    fclose(frandom[3]);

    // Add the NULL TERMINATOR for good measure
    randomness[0][fsize[0]] = 0;
    randomness[1][fsize[1]] = 0;
    randomness[2][fsize[2]] = 0;
    randomness[3][fsize[3]] = 0;

    printf("randomness[0]fsize[0] (+1): %"PRIu64"\n", fsize[0]);
    printf("randomness[1]fsize[1] (+1): %"PRIu64"\n", fsize[1]);
    printf("randomness[2]fsize[2] (+1): %"PRIu64"\n", fsize[2]);
    printf("randomness[3]fsize[3] (+1): %"PRIu64"\n", fsize[3]);

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
    int round = 0;

    for(; keepRunning && round < 4; ++round)
    {
        int trials = TRIALS;
        const char * writeout[4] = { WRITE_OUT_1, WRITE_OUT_2, WRITE_OUT_3, WRITE_OUT_4 };

        while(keepRunning && trials--)
        {
            int retval = 0;
            int trial = TRIALS - trials;

            printf("--> beginning trial %d of %d (round %d)\n", trial, TRIALS, round + 1);

            char writeout_target[PATH_BUFF_SIZE];

            snprintf(writeout_target,
                     PATH_BUFF_SIZE,
                     "%s/%d",
                     writeout[round],
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
                fprintf(stderr, "%s\n", "open failed");
                monitor.ffinish(&monitor);
                return 13;
            }

            u_int64_t writelen = fsize[round];
            char * randomnessCopy = randomness[round];

            lseek64(trialoutfd, 0, SEEK_SET);

            while(writelen > 0)
            {
                u_int64_t bytesWritten = write(trialoutfd, randomnessCopy, iosize_actual[round]);

                if(bytesWritten <= 0)
                {
                    perror("write failed");
                    monitor.ffinish(&monitor);
                    return 14;
                }

                writelen -= bytesWritten;
                randomnessCopy = randomnessCopy + bytesWritten;
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

            u_int64_t readlen = fsize[round];
            char * readback = malloc(readlen);
            char * readbackOriginal = readback;

            lseek64(trialoutfd, 0, SEEK_SET);

            while(readlen > 0)
            {
                u_int64_t bytesRead = read(trialoutfd, readback, iosize_actual[round]);

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

            printf("==> WRITES <==\nenergy: %fj\nduration: %fs\npower: %fw\n", w_energy / 1000000.0, w_duration / 1000000000.0, w_power);
            printf("==> READS <==\nenergy: %fj\nduration: %fs\npower: %fw\n", r_energy / 1000000.0, r_duration / 1000000000.0, r_power);

            // Output the results
            fprintf(flog_output[round], "w_energy: %f\nw_duration: %f\nw_power: %f\nr_energy: %f\nr_duration: %f\nr_power: %f\n---\n",
                    w_energy, w_duration, w_power, r_energy, r_duration, r_power);

            close(trialoutfd);

            if(CLEANUP)
            {
                printf("removing target %s\n", writeout_target);
                remove(writeout_target);
            }

            // Flush the results
            fflush(flog_output[round]);
        }

        if(!keepRunning)
        {
            printf("Interrupted!\n");
            return 7;
        }

        /*if(NO_SHMOO)
            fprintf(flog_output[round], "%s", "mf: 0x10 2000000\n");*/

        if(MOUNT_CLEANUP)
        {
            char umount_cmd[CMD_BUFF_SIZE];
            snprintf(umount_cmd, CMD_BUFF_SIZE, "umount /tmp/nbd%i", round);
            printf("#############\numount_cmd: %s\n", umount_cmd);

            int cmd_ret1 = system(umount_cmd);
            int cmd_ret2 = system("rm -f /tmp/ram0/logfs-* /tmp/ram0/blfs-*");

            if((WIFSIGNALED(cmd_ret1) && (WTERMSIG(cmd_ret1) == SIGINT || WTERMSIG(cmd_ret1) == SIGQUIT))
               || (WIFSIGNALED(cmd_ret2) && (WTERMSIG(cmd_ret2) == SIGINT || WTERMSIG(cmd_ret2) == SIGQUIT)))
            {
                printf("Interrupted!\n");
                return 7;
            }

            printf("cmd_ret1: %i\n", cmd_ret1);
            printf("cmd_ret2: %i\n", cmd_ret2);
            printf("syncing before moving on...\n");

            sync();

            printf("#############\n");
        }
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
    free(randomness[0]);
    free(randomness[1]);
    free(randomness[2]);
    free(randomness[3]);
    
    printf("Done!\n");

    fclose(flog_output[0]);
    fclose(flog_output[1]);
    fclose(flog_output[2]);
    fclose(flog_output[3]);

    close(pcachefd);

    return 0;
}
