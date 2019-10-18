#!/usr/bin/env python3
"""An experimental framework meant to find the optimal flk/nug configuration;
used to generate tradeoff spaces and other things too"""

import os
import sys
from datetime import datetime
from tqdm import tqdm

import initrunner
from librunner import Librunner
from librunner.util import outputProgressBarRedirection, printInstabilityWarning, ExtendedConfiguration, RESULTS_PATH, RESULTS_FILE_NAME

config = initrunner.parseConfigVars()
lib = Librunner(config)

### * Configurables * ###

DIE_ON_EXCEPTION  = True
REPEAT_TEST_TIMES = 3

experiments = [
    #lib.sequentialFreerunUsecase_BatterySaver,
    #lib.randomFreerunUsecase_BatterySaver,
    lib.sequentialFreerunWithCipherSwitching,
    lib.randomFreerunWithCipherSwitching,
]

ciphers = [
    #'sc_salsa8',
    #'sc_salsa12',
    #'sc_aes128_ctr',
    #'sc_aes256_ctr',
    #'sc_hc128', # ! too slow to test (see buselfs source for rationale)
    #'sc_rabbit',
    #'sc_sosemanuk',
    'sc_chacha8_neon',
    #'sc_chacha12_neon',
    'sc_chacha20_neon',
    'sc_freestyle_fast',
    'sc_freestyle_balanced',
    'sc_freestyle_secure',
]

dataClasses = [
    #'1k',
    '4k',
    '512k',
    '5m',
    '40m',
    #'5g',
]

flksizes = [
    #512,
    #1024,
    #2048,
    4096,
    #8192,
    #16384,
    #32768,
    #65536,
]

fpns = [
    #1, (too small)
    #2, (too small)
    #4, (too small)
    #8,
    #16,
    #32,
    64,
    #128,
    #256,
]

# ! REMEMBER: it's nilfs2 (TWO) with a 2! Not just 'nilfs'!
filesystems = [
    #'nilfs2',
    'f2fs',
]

backendFnTuples = [
    #(lib.createRawBackend, lib.destroyRawBackend, 'raw-vanilla'),
    #(lib.createVanillaBackend, lib.destroyVanillaBackend, 'vanilla'),
    #(lib.createDmcBackend, lib.destroyDmcBackend, 'dmcrypt'),
    (lib.createSbBackend, lib.destroySbBackend, 'strongbox'),
]

### *** ###

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        sys.exit('must be root/sudo')

    try:
        # Bare bones basic initialization
        initrunner.initialize(config)
        initrunner.cwdToRAMDir(config)
        lib.checkSanity()

        lib.print('working directory set to {}'.format(config['RAM0_PATH']))
        lib.clearBackstoreFiles()
        lib.print('constructing configurations')

        # * And it begins!
        configurations = []
        for filesystem in filesystems:
            for fpn in fpns:
                for flk_size in flksizes:
                    configurations.extend([
                        ExtendedConfiguration(
                            '{}#{}#{}#{}'.format(filesystem, cipher, flk_size, fpn),
                            filesystem,
                            0,
                            [],
                            [
                                '--cipher', cipher,
                                '--flake-size', str(flk_size),
                                '--flakes-per-nugget', str(fpn)
                            ]
                        ) for cipher in ciphers
                    ])

        confcount = len(configurations) * len(backendFnTuples) * len(dataClasses) * len(experiments)

        lib.clearBackstoreFiles()
        lib.print('starting experiment ({} configurations)'.format(confcount))

        # TODO: factor this all out and replace the custom parts with lambda/function pointers
        with outputProgressBarRedirection() as originalStdOut:
            with tqdm(total=confcount, file=originalStdOut, unit='observation', dynamic_ncols=True) as progressBar:
                for conf in configurations:
                    for backendFn in backendFnTuples:
                        for runFn in experiments:
                            for dataClass in dataClasses:
                                with open(config['LOG_FILE_PATH'], 'w') as file:
                                    print(str(datetime.now()), '\n---------\n', file=file)

                                    lib.logFile = file
                                    identifier = '{}-{}-{}'.format(
                                        dataClass,
                                        conf.proto_test_name,
                                        backendFn[2]
                                    )

                                    predictedResultFileName = RESULTS_FILE_NAME.format(runFn.experiment_name, identifier)

                                    predictedResultFilePath = RESULTS_PATH.format(
                                        os.path.realpath(config['REPO_PATH']),
                                        predictedResultFileName
                                    )

                                    lib.print('------------------ {} experiment: {} ------------------'.format(
                                        runFn.experiment_name,
                                        identifier
                                    ))

                                    # ? If the results file exists already, then skip this experiment!
                                    if os.path.exists(predictedResultFilePath):
                                        lib.print('results file {} was found, experiment skipped!'.format(predictedResultFilePath))

                                    else:
                                        for i in range(1, REPEAT_TEST_TIMES + 1):
                                            lib.print('=> run {}/{}'.format(i, REPEAT_TEST_TIMES))

                                            try:
                                                backendFn[0](conf.fs_type, conf.mount_args, conf.device_args)
                                                lib.dropPageCache()

                                            except KeyboardInterrupt:
                                                progressBar.close()
                                                lib.print('keyboard interrupt received, cleaning up...')
                                                raise

                                            try:
                                                runFn(dataClass, identifier, conf.swap_ratio)

                                            except KeyboardInterrupt:
                                                progressBar.close()
                                                lib.print('keyboard interrupt received, cleaning up...')
                                                raise

                                            except:
                                                if DIE_ON_EXCEPTION:
                                                    progressBar.close()

                                                lib.print('UNHANDLED EXCEPTION ENCOUNTERED!', severity='FATAL')

                                                if DIE_ON_EXCEPTION:
                                                    raise

                                            finally:
                                                try:
                                                    backendFn[1]()
                                                    lib.clearBackstoreFiles()

                                                except:
                                                    progressBar.close()
                                                    printInstabilityWarning(lib, config)
                                                    raise

                                    lib.print('------------------ *** ------------------')
                                    lib.logFile = None

                                    progressBar.update()

        lib.print('done', severity='OK')

    except KeyboardInterrupt:
        lib.print('done (experiment terminated via keyboard interrupt)', severity='WARN')
