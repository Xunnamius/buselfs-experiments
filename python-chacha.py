#!/usr/bin/env python3

# This script generates hashes for the experiment, timing it and reporting on the
# results

import os
import sys
import time
import subprocess
import serial
from vendor.pyWattsup import WattsUp

TRIALS = 5

################################################################################

if len(sys.argv) != 4:
    print('Usage: {} <coretype> <writeto>'.format(sys.argv[0]))
    sys.exit(1)

coreType = sys.argv[1]
writeto = sys.argv[2]

trials = TRIALS

wattsup = WattsUp('/dev/ttyUSB0', 115200, verbose=False)

def trial(description, fn):
    print(description)
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
    print("command returned: ", fn)

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

with open('/home/odroid/bd3/rsync/energy-AES-1/results/shmoo.{}.results'.format(coreType), 'a') as out:
    while trials:
        trials = trials - 1
        trial = TRIALS-trials

        trial('beginning trial {}-1-1 of {} (small.random, AES-CTR)'.format(trial, TRIALS), '')

        print('beginning trial {}-1-2 of {} (small.random, ChaCha20)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')
        
        time.sleep(2)

        print('beginning trial {}-1-3 of {} (small.random, AES-GCM)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')
        
        time.sleep(2)

        print('beginning trial {}-1-4 of {} (small.random, ChaCha20-Poly1305)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')
        
        time.sleep(2)

        print('beginning trial {}-2-1 of {} (large.random, AES-CTR)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')
        
        time.sleep(2)

        print('beginning trial {}-2-2 of {} (large.random, ChaCha20)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')

        time.sleep(2)

        print('beginning trial {}-2-3 of {} (large.random, AES-GCM)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')
        
        time.sleep(2)

        print('beginning trial {}-2-4 of {} (large.random, ChaCha20-Poly1305)'.format(trial, TRIALS))
        print('waiting for write buffer flush...')

        time.sleep(2)

        
        print('trial {}/{} complete'.format(trial, TRIALS))

wattsup.serial.close()
print('done')
exit(0)
