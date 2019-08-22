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
