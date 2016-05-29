#!/usr/bin/env python3

"""This script generates hashes for the experiment, timing it and reporting on
the results"""

# pylint: disable=E0401

import os
import sys
import time
import subprocess
import serial
from vendor.pyWattsup import WattsUp

TTY = '/dev/ttyUSB0'
REPO = '/home/odroid/bd3/repos/energy-AES-1'
#REPO = '/home/xunnamius/repos/research/energy-AES-1'
NO_SHMOO = True # set to False if shmoo-ing
CLEANUP = True # delete files directly after trial finishes so as to not take up space

TRIALS = 20

################################################################################

if len(sys.argv) != 4:
    print('Usage: {} <coretype> <fstype> <writeto>'.format(sys.argv[0]))
    sys.exit(1)

coreType = sys.argv[1]
fsType = sys.argv[2]
writeto = sys.argv[3]

trials = TRIALS

wattsup = WattsUp(TTY, 115200, verbose=False)

#print("prescript execution returned: ", subprocess.call([REPO + '/freerun-prescript.sh']))

with open(REPO + '/results/shmoo.{}.{}.results'.format(coreType, fsType), 'a') as out:
    while trials:
        trials = trials - 1
        trial = TRIALS-trials
        print('beginning trial {} of {}'.format(trial, TRIALS))

        print('waiting for write buffer flush...')

        time.sleep(2)
        print('opening connection...')
        try:
            wattsup.serial.open()
        except serial.serialutil.SerialException:
            print('Serial exception (ignoring because already open)!')

        print('beginning...')

        wattsup.clearMemory()
        wattsup.logInternal(1)

        target = os.path.join(writeto, '') + str(trial)
        print('writing -> ' + target)

        # Begin logging with Wattsup (above), run filebench (here), close out the
        # Wattsup logger (below)
        print("dd-write returned: ", subprocess.call([REPO + '/dd-write-old.sh', target, coreType, fsType], stdout=out))
        print("dd-read returned: ", subprocess.call([REPO + '/dd-read-old.sh', target, coreType, fsType], stdout=out))

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

        if CLEANUP:
            print('removing ' + target)
            os.remove(target)

        print('trial {}/{} complete'.format(trial, TRIALS))

    if NO_SHMOO:
        print("mf: 0x10 2000000", file=out)

wattsup.serial.close()
print('done')
exit(0)
