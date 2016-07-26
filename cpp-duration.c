#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include <unistd.h>
#include <sys/types.h>
#include <signal.h>
#include "vendor/energymon/energymon-time-util.h"

#define PATH_BUFF_SIZE 255
#define CMD_BUFF_SIZE 512

const int TRIALS = 20;
// const char * REPO_PATH = "/home/odroid/bd3/repos/energy-AES-1"; // No trailing /
const char * REPO_PATH = "/home/xunnamius/repos/research/energy-AES-1";
const int CLEANUP = 1;
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

    char output_path[PATH_BUFF_SIZE];
    FILE * foutput;

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

    // Begin the trials
    int trials = TRIALS;

    while(keepRunning && trials--)
    {
        uint64_t time_start_ns;
        uint64_t time_end_ns;
        double duration;

        int trial = TRIALS - trials;
        printf("--> beginning trial %d of %d\n", trial, TRIALS);

        char write_cmd[CMD_BUFF_SIZE];
        char read_cmd[CMD_BUFF_SIZE];
        char target[PATH_BUFF_SIZE];

        snprintf(target, PATH_BUFF_SIZE, "%s/%d", write_to, trial);
        snprintf(write_cmd, CMD_BUFF_SIZE, "dd-write.sh %s %s %s", target, core_type, fs_type);
        snprintf(read_cmd, CMD_BUFF_SIZE, "dd-read.sh %s %s %s", target, core_type, fs_type);

        printf("target: %s\n", target);
        printf("write_cmd: %s\n", write_cmd);
        printf("read_cmd: %s\n", read_cmd);

        // Grab the initial time
        time_start_ns = energymon_gettime_ns();
        printf("got start time: %"PRIu64"\n", time_start_ns);

        // Run the experiment here
        // energymon_sleep_us(2000000); // Sleep for two seconds

        // Break out if we're interrupted
        if(!keepRunning) break;

        // Run the dd-write and then dd-read
        int write_ret = callsys(write_cmd);
        printf("write_cmd returned %d\n", write_ret);

        // Break out if we're interrupted
        if(!keepRunning) break;

        int read_ret = callsys(read_cmd);
        printf("read_cmd returned %d\n", read_ret);

        // Grab the terminal time
        time_end_ns = energymon_gettime_ns();
        printf("got end time: %"PRIu64"\n", time_end_ns);

        duration = time_end_ns - time_start_ns;

        printf("duration: %fns\n", duration);

        // Output the results
        fprintf(foutput, "duration: %f\n", duration);

        // Break out if we're interrupted
        if(!keepRunning) break;

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
    
    printf("Finished reading\n");
    fclose(foutput);

    return 0;
}
