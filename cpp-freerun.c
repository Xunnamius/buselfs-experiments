#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include "energymon/energymon-default.h"
#include "vendor/energymon/energymon-time-util.h"

int main()
{
    energymon monitor;
    uint64_t time_start_ns;
    uint64_t time_end_ns;
    uint64_t energy_start_uj;
    uint64_t energy_end_uj;
    double watts;

    if(energymon_get_default(&monitor))
    {
        perror("energymon_get_default");
        return 1;
    }

    if(monitor.finit(&monitor))
    {
        perror("finit");
        return 2;
    }

    // Grab the initial energy use and time
    errno = 0;
    energy_start_uj = monitor.fread(&monitor);

    if(!energy_start_uj && errno)
    {
        perror("fread");
        monitor.ffinish(&monitor);
        return 3;
    }
    
    printf("Got start reading: %"PRIu64"\n", energy_start_uj);
    time_start_ns = energymon_gettime_ns();
    printf("Got start time: %"PRIu64"\n", time_start_ns);

    // Run the experiment here
    energymon_sleep_us(2000000); // Sleep for two seconds

    // Grab the end energy use and time
    errno = 0;
    energy_end_uj = monitor.fread(&monitor);

    if(!energy_end_uj && errno)
    {
        perror("fread");
        monitor.ffinish(&monitor);
        return 3;
    }
    
    printf("Got end reading: %"PRIu64"\n", energy_end_uj);
    time_end_ns = energymon_gettime_ns();
    printf("Got end time: %"PRIu64"\n", time_end_ns);

    watts = (energy_end_uj - energy_start_uj) * 1000.0 / (time_end_ns - time_start_ns);
    printf("Watts: %f\n", watts);

    if(monitor.ffinish(&monitor))
    {
        perror("ffinish");
        return 5;
    }
    
    printf("Finished reading\n");

    return 0;
}
