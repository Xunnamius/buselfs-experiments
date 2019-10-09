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

    check_args_and_perms_noratio(argc, "sequential-worm-wcs");

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);
    printf("write_to: %s\n", write_to);

    // Get read path from shards

    char path_shard[PATH_BUFF_SIZE];
    snprintf(path_shard, PATH_BUFF_SIZE, "results/sequential_worm_wcs.%s.%s.results", core_type, fs_type);
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

        // ? Initial write
        // ! The initial write op is not measured as part of the experiment!

        u_int64_t write1len = calc_len(fsize, WORM_BUILTIN_SWAP_RATIO, RETURN_PRIMARY_LENGTH);
        char * randomnessCopy1 = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(write1len > 0)
        {
            u_int64_t bytesWritten1 = write(trialoutfd, randomnessCopy1, MIN(write1len, IOSIZE));

            if(bytesWritten1 <= 0)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 14;
            }

            write1len -= bytesWritten1;
            randomnessCopy1 = randomnessCopy1 + bytesWritten1;
        }

        // Make sure everything writes through
        sync();

        // ? READ 1/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        Metrics read1_metrics_start;
        retval = collect_metrics(&read1_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("1 READ METRICS :: got start energy (uj): %"PRIu64"\n", read1_metrics_start.energy_uj);
        printf("1 READ METRICS :: got start time (ns): %"PRIu64"\n", read1_metrics_start.time_ns);

        u_int64_t read1len = calc_len(fsize, WORM_BUILTIN_SWAP_RATIO, RETURN_PRIMARY_LENGTH);
        char * read1back = malloc(read1len);
        char * read1backOriginal = read1back;

        // ? Start at the beginning
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

        printf("1 READ METRICS :: got end energy (uj): %"PRIu64"\n", read1_metrics_end.energy_uj);
        printf("1 READ METRICS :: got end time (ns): %"PRIu64"\n", read1_metrics_end.time_ns);

        free(read1backOriginal);

        // ? Schedule a cipher swap

        swap_ciphers();

        // ? READ 2/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        Metrics read2_metrics_start;
        retval = collect_metrics(&read2_metrics_start, &monitor);

        if(retval != 0)
            return retval;

        printf("2 READ METRICS :: got start energy (uj): %"PRIu64"\n", read2_metrics_start.energy_uj);
        printf("2 READ METRICS :: got start time (ns): %"PRIu64"\n", read2_metrics_start.time_ns);

        u_int64_t read2len = calc_len(fsize, WORM_BUILTIN_SWAP_RATIO, RETURN_SWAP_LENGTH);
        char * read2back = malloc(read2len);
        char * read2backOriginal = read2back;

        // ? Start at the beginning
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

        printf("2 READ METRICS :: got end energy (uj): %"PRIu64"\n", read2_metrics_end.energy_uj);
        printf("2 READ METRICS :: got end time (ns): %"PRIu64"\n", read2_metrics_end.time_ns);

        free(read2backOriginal);

        // ? Crunch results

        double r1_energy = read1_metrics_end.energy_uj - read1_metrics_start.energy_uj;
        double r1_duration = read1_metrics_end.time_ns - read1_metrics_start.time_ns;
        double r1_power = r1_energy * 1000.0 / r1_duration;

        double r2_energy = read2_metrics_end.energy_uj - read2_metrics_start.energy_uj;
        double r2_duration = read2_metrics_end.time_ns - read2_metrics_start.time_ns;
        double r2_power = r2_energy * 1000.0 / r2_duration;

        double r_energy = r1_energy + r2_energy;
        double r_duration = r1_duration + r2_duration;
        double r_power = r1_power + r2_power;

        printf("==> READS <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
               r_energy / 1000000.0,
               r_duration / 1000000000.0,
               r_power);

        // ? Output the results

        fprintf(flog_output,
                "r_energy: %f\nr_duration: %f\nr_power: %f\n---\n",
                r_energy,
                r_duration,
                r_power);

        // ? Schedule a cipher swap to swap back to normal
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
