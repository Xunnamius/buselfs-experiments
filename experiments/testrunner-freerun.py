#!/usr/bin/env python3

import os
import sys
from datetime import datetime

import initrunner
from librunner import Librunner
from librunner.util import Configuration, ESTIMATION_METRIC

config = initrunner.parseConfigVars()
lib = Librunner(config)

### * Configurables * ###

filesystems = ['f2fs', 'nilfs'] #['f2fs', 'nilfs']
dataClasses = ['1k', '40m'] #['1k', '4k', '512k', '5m', '40m']

experiments = [lib.sequentialFreerun] #[lib.sequentialFreerun, lib.randomFreerun]

ciphers = [#'sc_hc128', # ! too slow to test >:O
           'sc_rabbit',
           'sc_sosemanuk',
           'sc_salsa8',
           'sc_salsa12',
           'sc_salsa20',
           'sc_aes128_ctr',
           'sc_aes256_ctr'
]

backendFnTuples = [
    #(lib.createRawBackend, lib.destroyRawBackend, 'raw-vanilla'),
    #(lib.createVanillaBackend, lib.destroyVanillaBackend, 'vanilla'),
    #(lib.createDmcBackend, lib.destroyDmcBackend, 'dmcrypt'),
    (lib.createSbBackend, lib.destroySbBackend, 'strongbox')
]

### *** ###

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        sys.exit('must be root/sudo')
    
    # Bare bones basic initialization
    initrunner.initialize()
    initrunner.cwdToRAMDir()
    lib.checkSanity()
    
    lib.print('working directory set to {}'.format(config['RAM0_PATH']))
    lib.clearBackstoreFiles()
    lib.print('constructing configurations')

    # * Normal perf tests
    # TODO: split ^ off into testrunner-asplos17
    # configurations = (
        # Configuration('nilfs2', 'nilfs2', [], []),
        # Configuration('f2fs', 'f2fs', ['-o', 'background_gc_off'], []),
        # Configuration('f2fs', 'f2fs', [], []),
        # Configuration('ext4-oj', 'ext4', [], []),
        # Configuration('ext4-fj', 'ext4', ['-o', 'data=journal'], [])
    # )

    # * Cipher suite perf tests
    configurations = []

    for filesystem in filesystems:
        configurations.append(Configuration('{}#baseline'.format(filesystem), filesystem, [], []))
        configurations.extend([Configuration('{}#{}'.format(filesystem, cipher), filesystem, [], ['--cipher', cipher]) for cipher in ciphers])

    confcount = len(configurations) * len(backendFnTuples) * len(dataClasses) * len(experiments)
    
    lib.clearBackstoreFiles()
    lib.print('starting experiment ({} configurations; estimated {} minutes)'.format(confcount, confcount * ESTIMATION_METRIC))

    for conf in configurations:
        for backendFn in backendFnTuples:
            for runFn in experiments:
                for dataClass in dataClasses:
                    with open(config['LOG_FILE_PATH'], 'w') as file:
                        print(str(datetime.now()), '\n---------\n', file=file)

                        lib.logFile = file
                        identifier = '{}-{}-{}'.format(dataClass, conf.proto_test_name, backendFn[2])

                        lib.print(' ------------------ Experiment "{}" ------------------ '.format(identifier))
                        backendFn[0](conf.fs_type, conf.mount_args, conf.device_args)
                        lib.dropPageCache()
                        runFn(dataClass, identifier)
                        backendFn[1]()
                        lib.clearBackstoreFiles()

                        lib.print(' ------------------ *** ------------------ ')
                        lib.logFile = None
    
    lib.print('done', severity='OK')
