#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <inttypes.h>
#include "energymon-default.h"

int main()
{
    energymon monitor;
    uint64_t result;

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
    result = em.fread(&em);

    if(result == 0 && errno)
    {
        perror("fread");
        return 1;
    }
    
    printf("Got reading: %"PRIu64"\n", result);

    if(em.ffinish(&em))
    {
        perror("ffinish");
        return 1;
    }
    
    printf("Finished reading from %s\n", source);

    return 0;
}
