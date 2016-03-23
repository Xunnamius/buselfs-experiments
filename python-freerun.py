#!/usr/bin/env python3

"""This script generates hashes for the experiment, timing it and reporting on
the results"""

# pylint: disable=E0401

import sys
import time
import subprocess
import serial
from vendor.pyWattsup import WattsUp

TRIALS = 4

################################################################################

if len(sys.argv) != 4:
    print('Usage: {} <coretype> <fstype> <writeto>'.format(sys.argv[0]))
    sys.exit(1)

coreType = sys.argv[1]
fsType = sys.argv[2]
writeto = sys.argv[3]

trials = TRIALS

wattsup = WattsUp('/dev/ttyUSB0', 115200, verbose=False)

with open('/home/odroid/bd3/rsync/energy-AES-1/results/shmoo.{}.{}.results'.format(coreType, fsType), 'a') as out:
    while trials:
        trials = trials - 1
        trial = TRIALS-trials
        print('beginning trial {} of {}'.format(trial, TRIALS))

        print('waiting for write buffer flush...')
        time.sleep(2)

        try:
            wattsup.serial.open()
        except serial.serialutil.SerialException:
            pass

        wattsup.clearMemory()
        wattsup.logInternal(1)

        # Begin logging with Wattsup (above), run filebench (here), close out the
        # Wattsup logger (below)
        print("dd-write returned: ", subprocess.call(['/home/odroid/bd3/rsync/energy-AES-1/dd-write.sh', writeto + str(trial), coreType, fsType], stdout=out))
        print("dd-read returned: ", subprocess.call(['/home/odroid/bd3/rsync/energy-AES-1/dd-read.sh', writeto + str(trial), coreType, fsType], stdout=out))

        # This loop handles any annoying errors we may encounter
        while True:
            try:
                wattsup.printStats(wattsup.getInternalData(), out)
                wattsup.serial.close()
                break

            except ValueError:
                print('[+] recovered from ValueError')
                wattsup.serial.close()
                time.sleep(0.1) # Give Wattsup a moment to get its shit together
                wattsup.serial.open()
                continue
        print('trial {}/{} complete'.format(trial, TRIALS))

wattsup.serial.close()
print('done')
exit(0)
