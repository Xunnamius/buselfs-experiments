#define _XOPEN_SOURCE 500
#define _FILE_OFFSET_BITS 64

#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/types.h>
#include <string.h>
#include <sched.h>
#include <sys/stat.h>
#include <signal.h>
#include <limits.h>
#include <assert.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

#define RETURN_PRIMARY_LENGTH 0
#define RETURN_SWAP_LENGTH 1

#define SWAP_RATIO_0S_100P 0
#define SWAP_RATIO_25S_75P 1
#define SWAP_RATIO_50S_50P 2
#define SWAP_RATIO_75S_25P 3

#define SWAP_RATIO_0S_100P_STR "0"
#define SWAP_RATIO_25S_75P_STR "1"
#define SWAP_RATIO_50S_50P_STR "2"
#define SWAP_RATIO_75S_25P_STR "3"

#define LOW_BATTERY_WAIT 60U // In seconds

#define IOSIZE 131072U
//#define IOSIZE INT_MAX
#define PATH_BUFF_SIZE 255U
#define STDOUT_BUFF_SIZE 1035U
#define CMD_BUFF_SIZE 512U
#define COPY_INTO_TIMES 1U // randomness written COPY_INTO_TIMES into same file

#define SRAND_SEED1 76532543U
#define SRAND_SEED2 34567970U
#define SRAND_SEED3 98763503U
#define SRAND_SEED4 11874641U

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

#ifndef BUSELFS_PATH // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "BUSELFS_PATH must be defined in vars.mk!"
    #endif
    #define BUSELFS_PATH "" // ! Dead code, but vscode needs it
#endif

#ifndef BLFS_SV_QUEUE_INCOMING_NAME // see config/vars.mk
    #ifndef __INTELLISENSE__
        #error "BLFS_SV_QUEUE_INCOMING_NAME must be defined in vars.mk!"
    #endif
    #define BLFS_SV_QUEUE_INCOMING_NAME "" // ! Dead code, but vscode needs it
#endif

#define MIN(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a < _b ? _a : _b; })
#define MAX(a,b) __extension__ ({ __typeof__ (a) _a = (a); __typeof__ (b) _b = (b); _a > _b ? _a : _b; })

#define STRINGIZE(x) #x
#define STRINGIZE_VALUE_OF(x) STRINGIZE(x)

#define CMD_SWAP_ARGS "write " STRINGIZE_VALUE_OF(BLFS_SV_QUEUE_INCOMING_NAME) " 1 2>&1"
#define CMD_THROTTLE_ARGS ""
// #define CMD_PIDOF_ARGS STRINGIZE_VALUE_OF(BUSELFS_PATH) "/build/sb"
#define CMD_PIDOF_ARGS "sb" // ! This must be consistent with __init__.py

#define WORM_BUILTIN_SWAP_RATIO SWAP_RATIO_50S_50P

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

// Holds duration/energy/power data
typedef struct metrics_t {
    uint64_t time_ns;
    uint64_t energy_uj;
} metrics_t;

/**
 * Collect energy and timing metrics using energymon
 *
 * @return 0 if no error
 */
void collect_metrics(metrics_t * metrics, energymon * monitor)
{
    errno = 0;

    // Grab the initial energy use and time
    metrics->energy_uj = monitor->fread(monitor);

    if(errno)
    {
        perror("energymon fread failure");
        monitor->ffinish(monitor);
        exit(245);
    }

    metrics->time_ns = energymon_gettime_ns();
}

/**
 * Configures a bit mask for setting CPU affinity during throttling
 */
void get_throttled_cpu_set(cpu_set_t * throttle_mask)
{
    CPU_ZERO(throttle_mask);
    CPU_SET(0, throttle_mask);
    CPU_SET(1, throttle_mask);
    CPU_SET(2, throttle_mask);
    CPU_SET(3, throttle_mask);
}

/**
 * Configures a bit mask for setting CPU affinity during UNthrottling
 */
void get_unthrottled_cpu_set(cpu_set_t * unthrottle_mask)
{
    CPU_ZERO(unthrottle_mask);
    CPU_SET(0, unthrottle_mask);
    CPU_SET(1, unthrottle_mask);
    CPU_SET(2, unthrottle_mask);
    CPU_SET(3, unthrottle_mask);
    CPU_SET(4, unthrottle_mask);
    CPU_SET(5, unthrottle_mask);
    CPU_SET(6, unthrottle_mask);
    CPU_SET(7, unthrottle_mask);
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
 * @return The result of running the command
 */
void swap_ciphers()
{
    char path[PATH_BUFF_SIZE];
    char std_output[STDOUT_BUFF_SIZE];
    char cmd[sizeof(path) + sizeof(CMD_SWAP_ARGS) + 1];
    FILE * fp;

    get_real_path(path, STRINGIZE_VALUE_OF(BUSELFS_PATH), "build/sbctl");

    snprintf(cmd, sizeof cmd, "%s %s", path, CMD_SWAP_ARGS);
    printf("swap_ciphers (call to shell): %s\n", cmd);

    fp = popen(cmd, "r");

    if(fp == NULL)
    {
        printf("swap_ciphers (call to shell) failed to run\n");
        exit(252);
    }

    while(fgets(std_output, sizeof(std_output) - 1, fp) != NULL)
        printf("swap_ciphers stdout: %s\n", std_output);

    int exitcode = pclose(fp); // ? Waits on process to exit

    if(exitcode != 0)
    {
        exitcode = WEXITSTATUS(exitcode);
        printf("swap_ciphers (call to shell) failed with exit code: %i\n", exitcode);
        exit(exitcode);
    }

    sync();
}

/**
 * Returns the PID of the currently running StrongBox process
 */
void set_strongbox_affinity(cpu_set_t * mask)
{
    char std_output_pidof[STDOUT_BUFF_SIZE + 1];
    char cmd_pidof[sizeof(CMD_PIDOF_ARGS) + 10];
    FILE * fp_pidof;

    std_output_pidof[STDOUT_BUFF_SIZE] = 0;
    snprintf(cmd_pidof, sizeof cmd_pidof, "pidof %s", CMD_PIDOF_ARGS);
    printf("getting pid of StrongBox process (via call to shell): %s\n", cmd_pidof);

    fp_pidof = popen(cmd_pidof, "r");

    if(fp_pidof == NULL)
    {
        printf("pidof failed to run\n");
        exit(250);
    }

    if(fgets(std_output_pidof, sizeof(std_output_pidof), fp_pidof) == NULL)
    {
        printf("fgets failed to read pidof output\n");
        exit(249);
    }

    printf("saw pid string for StrongBox: %s\n", std_output_pidof);

    char * pid_str = strtok(std_output_pidof, " ");

    do
    {
        pid_t pid = 0;
        pid = strtoul(pid_str, NULL, 10);
        printf("derived pid for StrongBox: %jd\n", (intmax_t) pid);

        if(pid == 0)
        {
            printf("pid tokenize failed\n");
            exit(251);
        }

        errno = 0;

        int exitcode = sched_setaffinity(pid, sizeof(mask), mask); // ? Waits on process to exit

        if(exitcode != 0)
        {
            printf("sched_setaffinity failed with errno: %i\n", errno);
            exit(247);
        }
    } while((pid_str = strtok(NULL, " ")) != NULL);

    printf("StrongBox processes' affinity set successfully!\n");
}

/**
 * Attempt to force the odroid to use the little cores
 */
void throttle_sys()
{
    char path_throttle[PATH_BUFF_SIZE];
    char std_output_throttle[STDOUT_BUFF_SIZE];
    char cmd_throttle[sizeof(path_throttle) + sizeof(CMD_THROTTLE_ARGS) + 1];
    FILE * fp_throttle;

    get_real_path(path_throttle, STRINGIZE_VALUE_OF(REPO_PATH), "vendor/odroidxu3-throttle.sh");

    snprintf(cmd_throttle, sizeof cmd_throttle, "%s %s", path_throttle, CMD_THROTTLE_ARGS);
    printf("throttling odroid (via call to shell): %s\n", cmd_throttle);

    fp_throttle = popen(cmd_throttle, "r");

    if(fp_throttle == NULL)
    {
        printf("throttling odroid (via call to shell) failed to run\n");
        exit(252);
    }

    while(fgets(std_output_throttle, sizeof(std_output_throttle) - 1, fp_throttle) != NULL)
        printf("throttling odroid stdout: %s\n", std_output_throttle);

    int exitcode = pclose(fp_throttle); // ? Waits on process to exit

    if(exitcode != 0)
    {
        exitcode = WEXITSTATUS(exitcode);
        printf("throttling odroid (via call to shell) failed with exit code: %i\n", exitcode);
        exit(exitcode);
    }

    cpu_set_t throttle_mask;

    get_throttled_cpu_set(&throttle_mask);
    set_strongbox_affinity(&throttle_mask);

    sync();
    printf("sleeping for 5 seconds...\n");
    sleep(5);
}

/**
 * Attempt to force the odroid to use the BIG cores
 */
void unthrottle_sys()
{
    char path[PATH_BUFF_SIZE];
    char std_output[STDOUT_BUFF_SIZE];
    char cmd[sizeof(path) + sizeof(CMD_THROTTLE_ARGS) + 1];
    FILE * fp;

    get_real_path(path, STRINGIZE_VALUE_OF(REPO_PATH), "vendor/odroidxu3-unthrottle.sh");

    snprintf(cmd, sizeof cmd, "%s %s", path, CMD_THROTTLE_ARGS);
    printf("unthrottling odroid (via call to shell): %s\n", cmd);

    fp = popen(cmd, "r");

    if(fp == NULL)
    {
        printf("unthrottling odroid (via call to shell) failed to run\n");
        exit(252);
    }

    while(fgets(std_output, sizeof(std_output) - 1, fp) != NULL)
        printf("unthrottling odroid stdout: %s\n", std_output);

    int exitcode = pclose(fp); // ? Waits on process to exit

    if(exitcode != 0)
    {
        exitcode = WEXITSTATUS(exitcode);
        printf("unthrottling odroid (via call to shell) failed with exit code: %i\n", exitcode);
        exit(exitcode);
    }

    cpu_set_t unthrottle_mask;

    get_unthrottled_cpu_set(&unthrottle_mask);
    set_strongbox_affinity(&unthrottle_mask);

    sync();
    printf("sleeping for 5 seconds...\n");
    sleep(5);
}

/**
 * Wrapping your function call with ignore_result makes it more clear to
 * readers, compilers and linters that you are, in fact, ignoring the
 * function's return value on purpose.
 */
void ignore_result(long long int unused_result)
{
    (void) unused_result;
}

/**
 * Calculates the length of the operation (in bytes) using fsize and swap_ratio,
 * which details how much of the I/O operations are reserved for the swap
 * cipher. primary_or_swap determines which percentage of the backing store, in
 * bytes, is returned.
 */
uint64_t calc_len(uint64_t fsize, int swap_ratio, int primary_or_swap)
{
    uint64_t result = 0;

    if(swap_ratio == 1)
        result = llabs(fsize * 25 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? fsize : 0));

    else if(swap_ratio == 2)
        result = fsize / 2;

    else if(swap_ratio == 3)
        result = llabs(fsize * 75 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? fsize : 0));

    else
    {
        printf("Invalid swap_ratio (calc_len)\n");
        exit(255);
    }

    return result;
}

/**
 * Calculates the number of files that should be operated on before we trigger
 * the cipher swap.
 *
 * swap_ratio = 1 => 3 primary files for every 1 swap cipher files
 * swap_ratio = 2 => 1 primary file for every 1 swap cipher file
 * swap_ratio = 3 => 1 primary files for every 3 swap cipher files
 *
 * Only integers file counts are returned. Floor division is always used.
 * Remaining files in the calculation are divided evenly between primary and
 * swap counts. Ideally, TRIALS_INT should be an even multiple of 4 (e.g. 12).
 *
 * primary_or_swap determines which count is returned (for primary or for swap).
 */
int calc_num_files(int total_files_count, int swap_ratio, int primary_or_swap)
{
    uint64_t result = 0;

    if(swap_ratio == 0)
        result = primary_or_swap == RETURN_PRIMARY_LENGTH ? total_files_count : 0;

    else if(swap_ratio == 1)
        result = llabs(total_files_count * 25 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? total_files_count : 0));

    else if(swap_ratio == 2)
        result = llabs(total_files_count * 50 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? total_files_count : 0));

    else if(swap_ratio == 3)
        result = llabs(total_files_count * 75 / 100 - (primary_or_swap == RETURN_PRIMARY_LENGTH ? total_files_count : 0));

    else
    {
        printf("Invalid swap_ratio (calc_num_files)\n");
        exit(246);
    }

    return result;
}

/**
 * Print ratio param help text
 */
void print_swap_help()
{
    printf(
        "<swap_ratio> must be either: %i (NO swap), %i (25%% swap), %i (50%% swap), %i (75%% swap)!\n",
        SWAP_RATIO_0S_100P, SWAP_RATIO_25S_75P, SWAP_RATIO_50S_50P, SWAP_RATIO_75S_25P
    );
}

/**
 * Ensure we're running as root
 */
void check_root()
{
    uid_t euid = geteuid();

    if(euid != 0)
    {
        printf("Must run this as root!\n");
        exit(255);
    }
}

/**
 * Throw out the help text WITHOUT ratio param
 */
void check_args_and_perms_noratio(int argc, const char * name)
{
    check_root();

    if(argc != 4)
    {
        printf("Usage: %s <core_type> <fs_type> <write_to>\n", name);
        printf("No trailing slash for <write_to>!\n");
        exit(253);
    }
}

/**
 * Throw out the help text with ratio param
 */
void check_args_and_perms_with_ratio(int argc, const char * name)
{
    check_root();

    if(argc != 5)
    {
        printf("Usage: %s <core_type> <fs_type> <write_to> <swap_ratio>\n", name);
        print_swap_help();
        printf("No trailing slash for <write_to>!\n");
        exit(253);
    }
}

/**
 * Convert a string into a swap ration constant (an integer)
 */
uint8_t str_to_swap_ratio(const char * swap_ratio_str)
{
    if(strcmp(swap_ratio_str, SWAP_RATIO_25S_75P_STR) == 0)
        return SWAP_RATIO_25S_75P;

    else if(strcmp(swap_ratio_str, SWAP_RATIO_50S_50P_STR) == 0)
        return SWAP_RATIO_50S_50P;

    else if(strcmp(swap_ratio_str, SWAP_RATIO_75S_25P_STR) == 0)
        return SWAP_RATIO_75S_25P;

    else if(strcmp(swap_ratio_str, SWAP_RATIO_0S_100P_STR) == 0)
        return SWAP_RATIO_0S_100P;

    else
    {
        print_swap_help();
        exit(254);
    }
}
