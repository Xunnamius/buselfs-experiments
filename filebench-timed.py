#!/usr/bin/env python3

# This script generates hashes for the experiment, timing it and reporting on the
# results

import subprocess
from vendor.pyWattsup import WattsUp


################################################################################

wattsup = WattsUp('/dev/ttyUSB0', 115200, verbose=False)

wattsup.clearMemory()
wattsup.logInternal(1)

with open('/home/odroid/bd3/rsync/energy-AES-1/results/shmoo.results', 'a') as out:

    # Begin logging with Wattsup (above), run filebench (here), close out the
    # Wattsup logger (below)
    print("filebench returned: ", subprocess.run(["filebench", "-f", "/home/odroid/bd3/rsync/energy-AES-1/fb-personalities/fileserver-noninteractive.f"]).returncode)

    # This loop handles any annoying errors we may encounter
    while True:
        try:
            wattsup.printStats(wattsup.getInternalData(), out)
            wattsup.serial.close()
            break

        except ValueError:
            print('[+] recovered from ValueError')
            wattsup.serial.close()
            wattsup.serial.open()
            continue

print('done')
exit(0)
