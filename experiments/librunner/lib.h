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
#include <sys/stat.h>
#include <signal.h>
#include <limits.h>
#include <assert.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

#define RETURN_PRIMARY_LENGTH 0
#define RETURN_SWAP_LENGTH 1

#define SWAP_RATIO_25S_75P 1
#define SWAP_RATIO_50S_50P 2
#define SWAP_RATIO_75S_25P 3

#define SWAP_RATIO_25S_75P_STR "1"
#define SWAP_RATIO_50S_50P_STR "2"
#define SWAP_RATIO_75S_25P_STR "3"

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

#define CMD_ARGS "write " STRINGIZE_VALUE_OF(BLFS_SV_QUEUE_INCOMING_NAME) " 1 2>&1"

#define WORM_BUILTIN_SWAP_RATIO 2

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
 * @return The result of running the command
 */
void swap_ciphers()
{
    char path[PATH_BUFF_SIZE];
    char std_output[STDOUT_BUFF_SIZE];
    char cmd[sizeof(path) + sizeof(CMD_ARGS) + 1];
    FILE * fp;

    get_real_path(path, STRINGIZE_VALUE_OF(BUSELFS_PATH), "build/sbctl");

    snprintf(cmd, sizeof cmd, "%s %s", path, CMD_ARGS);
    printf("swap_ciphers (call to shell): %s\n", cmd);

    fp = popen(cmd, "r");

    if(fp == NULL)
    {
        printf("swap_ciphers (call to shell) failed to run");
        exit(252);
    }

    while(fgets(std_output, sizeof(std_output) - 1, fp) != NULL)
        printf("swap_ciphers stdout: %s\n", std_output);

    int exitcode = pclose(fp); // ? Waits on process to exit

    if(exitcode != 0)
    {
        exitcode = WEXITSTATUS(exitcode);
        printf("swap_ciphers (call to shell) failed with retval: %i\n", exitcode);
        exit(exitcode);
    }

    sync();
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

void print_swap_help()
{
    printf(
        "<swap_ratio> must be either: %i (25%% swap), %i (50%% swap), %i (75%% swap)!\n",
        SWAP_RATIO_25S_75P, SWAP_RATIO_50S_50P, SWAP_RATIO_75S_25P
    );
}

void check_root()
{
    uid_t euid = geteuid();

    if(euid != 0)
    {
        printf("Must run this as root!\n");
        // exit(255); // TODO: UNCOMMENT ME!
    }
}

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

uint8_t str_to_swap_ratio(const char * swap_ratio_str)
{
    if(strcmp(swap_ratio_str, SWAP_RATIO_25S_75P_STR) == 0)
        return SWAP_RATIO_25S_75P;

    else if(strcmp(swap_ratio_str, SWAP_RATIO_50S_50P_STR) == 0)
        return SWAP_RATIO_50S_50P;

    else if(strcmp(swap_ratio_str, SWAP_RATIO_75S_25P_STR) == 0)
        return SWAP_RATIO_75S_25P;

    else
    {
        print_swap_help();
        exit(254);
    }
}
