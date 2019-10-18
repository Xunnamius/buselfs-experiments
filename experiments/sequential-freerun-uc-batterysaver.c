#include "librunner/lib.h"

int main(int argc, char * argv[])
{
    struct sigaction act;
    act.sa_handler = interrupt_handler;
    sigaction(SIGINT, &act, NULL);

    energymon monitor;
    char output_path[PATH_BUFF_SIZE];

    FILE * flog_output;
    FILE * frandom;

    check_args_and_perms_noratio(argc, "sequential-freerun-uc-batterysaver");

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);
    printf("write_to: %s\n", write_to);

    // Get read path from shards

    char path_shard[PATH_BUFF_SIZE];
    snprintf(path_shard, PATH_BUFF_SIZE, "results/sequential_freerun_uc_batterysaver.%s.%s.results", core_type, fs_type);
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

    uint64_t fsize = ftell(frandom);

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

    uint64_t wait_time_ns = LOW_BATTERY_WAIT * 1000000000ULL;
    printf(": wait_time_ns = %"PRIu64"\n", wait_time_ns);

    while(keepRunning && trials--)
    {
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

        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        // ? WRITE fsize total bytes to backing store in one loop!

        int system_is_throttled = 0;

        metrics_t outer_write_metrics_start;
        metrics_t outer_write_metrics_end;
        metrics_t inner_write_metrics_end;

        collect_metrics(&outer_write_metrics_start, &monitor);

        printf("OUTER WRITE METRICS:: got start energy (uj): %"PRIu64"\n", outer_write_metrics_start.energy_uj);
        printf("OUTER WRITE METRICS:: got start time (ns): %"PRIu64"\n", outer_write_metrics_start.time_ns);

        uint64_t outer_writelen = fsize;
        char * randomness_copy = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(outer_writelen > 0)
        {
            uint64_t outer_bytes_written = write(trialoutfd, randomness_copy, MIN(outer_writelen, IOSIZE));

            if(outer_bytes_written <= 0)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 14;
            }

            outer_writelen -= outer_bytes_written;
            randomness_copy = randomness_copy + outer_bytes_written;

            // ? Schedule a record metrics, cipher swap, and core switch if
            // ? elapsed time >= LOW_BATTERY_WAIT && !system_is_throttled
            if(!system_is_throttled)
            {
                collect_metrics(&inner_write_metrics_end, &monitor);

                if(inner_write_metrics_end.time_ns - outer_write_metrics_start.time_ns >= wait_time_ns)
                {
                    system_is_throttled = 1;

                    sync();

                    printf("INNER WRITE METRICS:: got end energy (uj): %"PRIu64"\n", inner_write_metrics_end.energy_uj);
                    printf("INNER WRITE METRICS:: got end time (ns): %"PRIu64"\n", inner_write_metrics_end.time_ns);

                    swap_ciphers();
                    throttle_sys();
                }
            }
        }

        // ? Make sure everything writes through
        sync();

        collect_metrics(&outer_write_metrics_end, &monitor);

        printf("OUTER WRITE METRICS:: got end energy (uj): %"PRIu64"\n", outer_write_metrics_end.energy_uj);
        printf("OUTER WRITE METRICS:: got end time (ns): %"PRIu64"\n", outer_write_metrics_end.time_ns);

        // ? Unthrottle the system
        unthrottle_sys();

        // ? Crunch results

        double wo_energy = outer_write_metrics_end.energy_uj - outer_write_metrics_start.energy_uj;
        double wo_duration = outer_write_metrics_end.time_ns - outer_write_metrics_start.time_ns;
        double wo_power = wo_energy * 1000.0 / wo_duration;

        double wi_energy = inner_write_metrics_end.energy_uj - outer_write_metrics_start.energy_uj;
        double wi_duration = inner_write_metrics_end.time_ns - outer_write_metrics_start.time_ns;
        double wi_power = wi_energy * 1000.0 / wi_duration;

        printf("==> TOTAL WRITES <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               wo_energy / 1000000.0,
               wo_duration / 1000000000.0,
               wo_power);

        printf("==> WRITES BEFORE SWITCH <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               wi_energy / 1000000.0,
               wi_duration / 1000000000.0,
               wi_power);

        // ? Output the results

        fprintf(flog_output,
                "wo_energy: %f\nwo_duration: %f\nwo_power: %f\n---\n",
                wo_energy,
                wo_duration,
                wo_power);

        fprintf(flog_output,
                "wi_energy: %f\nwi_duration: %f\nwi_power: %f\n---\n---\n",
                wi_energy,
                wi_duration,
                wi_power);

        // ? Schedule a cipher swap to swap back to normal if we swapped at all
        if(system_is_throttled)
            swap_ciphers();

        close(trialoutfd);
        sync();

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
