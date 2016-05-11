#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include "energymon/energymon-default.h"
#include "energymon/energymon-time-util.h"

int main()
{
    energymon monitor;
    uint64_t time_start_ns;
    uint64_t time_end_ns;
    uint64_t energy_start_uj;
    uint64_t energy_end_uj;

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

    errno = 0;
    result = monitor.fread(&monitor);

    if(result == 0 && errno)
    {
        perror("fread");
	monitor.ffinish(&monitor)
        return 1;
    }
    
    printf("Got reading: %"PRIu64"\n", result);

    if(monitor.ffinish(&monitor))
    {
        perror("ffinish");
        return 1;
    }
    
    printf("Finished reading\n");

    return 0;
}
