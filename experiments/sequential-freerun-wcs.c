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

    check_args_and_perms_with_ratio(argc, "sequential-freerun-wcs");

    char * core_type = argv[1];
    char * fs_type = argv[2];
    char * write_to = argv[3];
    char * swap_ratio_str = argv[4];
    int swap_ratio;

    printf("core_type: %s\n", core_type);
    printf("fs_type: %s\n", fs_type);
    printf("write_to: %s\n", write_to);
    printf("swap_ratio_str: %s\n", swap_ratio_str);

    swap_ratio = str_to_swap_ratio(swap_ratio_str);

    // Get read path from shards

    char path_shard[PATH_BUFF_SIZE];
    snprintf(path_shard, PATH_BUFF_SIZE, "results/sequential_freerun_wcs.%s.%s.results", core_type, fs_type);
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

    int current_file_count = 1;
    int total_files_count = TRIALS_INT;
    int trialoutfds[TRIALS_INT];
    int files_switch_threshold = calc_num_files(TRIALS_INT, swap_ratio, RETURN_PRIMARY_LENGTH);

    metrics_t total_write_metrics = { 0 };
    metrics_t total_read_metrics = { 0 };

    for(int i = 1; i <= total_files_count; ++i)
    {
        printf("--> creating file %i of %i\n", i, total_files_count);

        char writeout_target[PATH_BUFF_SIZE];

        snprintf(writeout_target,
                 PATH_BUFF_SIZE,
                 "%s/%d",
                 write_to,
                 i);

        printf("writeout_target: %s\n", writeout_target);

        int trialoutfd = trialoutfds[i - 1] = open(writeout_target, O_CREAT | O_RDWR | O_SYNC, 0777);

        if(trialoutfd < 0)
        {
            fprintf(stderr, "open of %s failed\n", writeout_target);
            monitor.ffinish(&monitor);
            return 13;
        }
    }

    for(; keepRunning && current_file_count <= files_switch_threshold; ++current_file_count)
    {
        printf("--> committing 1/2 I/O with file %i of %i\n", current_file_count, files_switch_threshold);
        int trialoutfd = trialoutfds[current_file_count - 1];

        // ? WRITE 1/2

        metrics_t write1_metrics_start;
        collect_metrics(&write1_metrics_start, &monitor);

        printf("1 WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write1_metrics_start.energy_uj);
        printf("1 WRITE METRICS:: got start time (ns): %"PRIu64"\n", write1_metrics_start.time_ns);

        uint64_t write1len = fsize;
        char * randomnessCopy1 = randomness;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(write1len > 0)
        {
            uint64_t bytesWritten1 = write(trialoutfd, randomnessCopy1, MIN(write1len, IOSIZE));

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

        metrics_t write1_metrics_end;
        collect_metrics(&write1_metrics_end, &monitor);

        printf("1 WRITE METRICS:: got end energy (uj): %"PRIu64"\n", write1_metrics_end.energy_uj);
        printf("1 WRITE METRICS:: got end time (ns): %"PRIu64"\n", write1_metrics_end.time_ns);

        total_write_metrics.energy_uj += write1_metrics_end.energy_uj - write1_metrics_start.energy_uj;
        total_write_metrics.time_ns += write1_metrics_end.time_ns - write1_metrics_start.time_ns;

        // ? READ 1/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        metrics_t read1_metrics_start;
        collect_metrics(&read1_metrics_start, &monitor);

        printf("1 READ METRICS :: got start energy (uj): %"PRIu64"\n", read1_metrics_start.energy_uj);
        printf("1 READ METRICS :: got start time (ns): %"PRIu64"\n", read1_metrics_start.time_ns);

        uint64_t read1len = fsize;
        char * read1back = malloc(read1len);
        char * read1backOriginal = read1back;

        lseek64(trialoutfd, 0, SEEK_SET);

        while(read1len > 0)
        {
            uint64_t bytesRead1 = read(trialoutfd, read1back, MIN(read1len, IOSIZE));

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

        metrics_t read1_metrics_end;
        collect_metrics(&read1_metrics_end, &monitor);

        printf("1 READ METRICS :: got end energy (uj): %"PRIu64"\n", read1_metrics_end.energy_uj);
        printf("1 READ METRICS :: got end time (ns): %"PRIu64"\n", read1_metrics_end.time_ns);

        total_read_metrics.energy_uj += read1_metrics_end.energy_uj - read1_metrics_start.energy_uj;
        total_read_metrics.time_ns += read1_metrics_end.time_ns - read1_metrics_start.time_ns;

        close(trialoutfd);
        free(read1backOriginal);
    }

    // ? Schedule a cipher swap
    swap_ciphers();

    // Drop the page cache before the next write
    ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

    for(; keepRunning && current_file_count <= total_files_count; ++current_file_count)
    {
        printf("--> committing 2/2 I/O with file %i of %i\n", current_file_count, total_files_count);
        int trialoutfd = trialoutfds[current_file_count - 1];

        // ? WRITE 2/2

        metrics_t write2_metrics_start;
        collect_metrics(&write2_metrics_start, &monitor);

        printf("2 WRITE METRICS:: got start energy (uj): %"PRIu64"\n", write2_metrics_start.energy_uj);
        printf("2 WRITE METRICS:: got start time (ns): %"PRIu64"\n", write2_metrics_start.time_ns);

        uint64_t write2len = fsize;
        char * randomnessCopy2 = randomness;

        // ? Start writing at the end of the initial write
        lseek64(trialoutfd, 0, SEEK_SET);

        while(write2len > 0)
        {
            uint64_t bytesWritten2 = write(trialoutfd, randomnessCopy2, MIN(write2len, IOSIZE));

            if(bytesWritten2 <= 0)
            {
                perror("write failed");
                monitor.ffinish(&monitor);
                return 144;
            }

            write2len -= bytesWritten2;
            randomnessCopy2 = randomnessCopy2 + bytesWritten2;
        }

        // Make sure everything writes through
        sync();

        metrics_t write2_metrics_end;
        collect_metrics(&write2_metrics_end, &monitor);

        printf("2 WRITE METRICS:: got end energy (uj): %"PRIu64"\n", write2_metrics_end.energy_uj);
        printf("2 WRITE METRICS:: got end time (ns): %"PRIu64"\n", write2_metrics_end.time_ns);

        total_write_metrics.energy_uj += write2_metrics_end.energy_uj - write2_metrics_start.energy_uj;
        total_write_metrics.time_ns += write2_metrics_end.time_ns - write2_metrics_start.time_ns;

        // ? READ 2/2

        // Drop the page cache before the next read
        ignore_result(pwrite(pcachefd, droppcache, sizeof(char), 0));

        metrics_t read2_metrics_start;
        collect_metrics(&read2_metrics_start, &monitor);

        printf("2 READ METRICS :: got start energy (uj): %"PRIu64"\n", read2_metrics_start.energy_uj);
        printf("2 READ METRICS :: got start time (ns): %"PRIu64"\n", read2_metrics_start.time_ns);

        uint64_t read2len = fsize;
        char * read2back = malloc(read2len);
        char * read2backOriginal = read2back;

        // ? Rewind
        lseek64(trialoutfd, 0, SEEK_SET);

        while(read2len > 0)
        {
            uint64_t bytesRead2 = read(trialoutfd, read2back, MIN(read2len, IOSIZE));

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

        metrics_t read2_metrics_end;
        collect_metrics(&read2_metrics_end, &monitor);

        printf("2 READ METRICS :: got end energy (uj): %"PRIu64"\n", read2_metrics_end.energy_uj);
        printf("2 READ METRICS :: got end time (ns): %"PRIu64"\n", read2_metrics_end.time_ns);

        total_read_metrics.energy_uj += read2_metrics_end.energy_uj - read2_metrics_start.energy_uj;
        total_read_metrics.time_ns += read2_metrics_end.time_ns - read2_metrics_start.time_ns;

        close(trialoutfd);
        free(read2backOriginal);
    }

    // ? Crunch results

    double w_power = total_write_metrics.energy_uj * 1000.0 / total_write_metrics.time_ns;
    double r_power = total_read_metrics.energy_uj * 1000.0 / total_read_metrics.time_ns;

    printf("==> WRITES <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
            total_write_metrics.energy_uj / 1000000.0,
            total_write_metrics.time_ns / 1000000000.0,
            w_power);

    printf("==> READS <==\nenergy: %fj\nduration: %fs\npower: %fw\n",
            total_read_metrics.energy_uj / 1000000.0,
            total_read_metrics.time_ns / 1000000000.0,
            r_power);

    // ? Output the results

    fprintf(flog_output,
            "w_energy: %"PRIu64"\nw_duration: %"PRIu64"\nw_power: %f\nr_energy: %"PRIu64"\nr_duration: %"PRIu64"\nr_power: %f\n---\n",
            total_write_metrics.energy_uj,
            total_write_metrics.time_ns,
            w_power,
            total_read_metrics.energy_uj,
            total_read_metrics.time_ns,
            r_power);

    sync();

    // ? Flush the results

    fflush(flog_output);

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
