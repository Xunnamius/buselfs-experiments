#!/usr/bin/env python3
# pylint: disable=no-member

import os
import sys
from datetime import datetime
from tqdm import tqdm

import initrunner
from librunner import Librunner
from librunner.util import outputProgressBarRedirection, printInstabilityWarning, ExtendedConfiguration, RESULTS_PATH, RESULTS_FILE_NAME
from librunner.exception import ExperimentError

config = initrunner.parseConfigVars()
lib = Librunner(config)

### * Configurables * ###

KEEP_RUNNER_LOGS = False
DIE_ON_EXCEPTION = True

# ! REMEMBER: it's nilfs2 (TWO) with a 2! Not just 'nilfs'!
filesystems = [
    #'nilfs2',
    'f2fs',
]

dataClasses = [
    #'1k',
    #'4k',
    #'512k',
    '5m',
    #'40m',
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

experiments = [
    lib.sequentialFreerunWithCipherSwitching,
    lib.randomFreerunWithCipherSwitching,
]

# ? These are all the cipher swapping pairs that will be tested
# ? each element: (primary cipher, swap cipher, swap strategy)
cipherpairs = [
    ('sc_chacha8_neon', 'sc_freestyle_secure', 'swap_0_forward'),

    # ('sc_chacha8_neon', 'sc_chacha20_neon', 'swap_0_forward'),
    # #('sc_chacha8_neon', 'sc_freestyle_fast', 'swap_0_forward'),
    # ('sc_chacha20_neon', 'sc_freestyle_fast', 'swap_0_forward'),
    # ('sc_freestyle_fast', 'sc_freestyle_balanced', 'swap_0_forward'),
    # ('sc_freestyle_balanced', 'sc_freestyle_secure', 'swap_0_forward'),

    # ('sc_chacha8_neon', 'sc_chacha20_neon', 'swap_1_forward'),
    # #('sc_chacha8_neon', 'sc_freestyle_fast', 'swap_1_forward'),
    # ('sc_chacha20_neon', 'sc_freestyle_fast', 'swap_1_forward'),
    # ('sc_freestyle_fast', 'sc_freestyle_balanced', 'swap_1_forward'),
    # ('sc_freestyle_balanced', 'sc_freestyle_secure', 'swap_1_forward'),

    # ('sc_chacha8_neon', 'sc_chacha20_neon', 'swap_2_forward'),
    # #('sc_chacha8_neon', 'sc_freestyle_fast', 'swap_2_forward'),
    # ('sc_chacha20_neon', 'sc_freestyle_fast', 'swap_2_forward'),
    # ('sc_freestyle_fast', 'sc_freestyle_balanced', 'swap_2_forward'),
    # ('sc_freestyle_balanced', 'sc_freestyle_secure', 'swap_2_forward'),

    # ('sc_chacha8_neon', 'sc_chacha20_neon', 'swap_mirrored'),
    # #('sc_chacha8_neon', 'sc_freestyle_fast', 'swap_mirrored'),
    # ('sc_chacha20_neon', 'sc_freestyle_fast', 'swap_mirrored'),
    # ('sc_freestyle_fast', 'sc_freestyle_balanced', 'swap_mirrored'),
    # ('sc_freestyle_balanced', 'sc_freestyle_secure', 'swap_mirrored')
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

    try:
        # Bare bones basic initialization
        initrunner.initialize(config)
        initrunner.cwdToRAMDir(config)
        lib.checkSanity()

        lib.print('working directory set to {}'.format(config['RAM0_PATH']))
        lib.clearBackstoreFiles()
        lib.print('constructing extended configurations')

        # * And it begins!
        configurations = []
        for filesystem in filesystems:
            for fpn in fpns:
                for flk_size in flksizes:
                    for swap_rat in range(1, 3): # ! (1, 4) means 1 through 3 inclusive!
                        configurations.extend([
                            ExtendedConfiguration(
                                '{}#{}#{}#{}#{}#{}+{}'.format(filesystem, cipherpair[0], flk_size, fpn, cipherpair[1], cipherpair[2], swap_rat),
                                filesystem,
                                swap_rat,
                                [],
                                [
                                    '--cipher', cipherpair[0],
                                    '--flake-size', str(flk_size),
                                    '--flakes-per-nugget', str(fpn),
                                    '--swap-cipher', cipherpair[1],
                                    '--swap-strategy', cipherpair[2]
                                ]
                            ) for cipherpair in cipherpairs
                        ])

        confcount = len(configurations) * len(backendFnTuples) * len(dataClasses) * len(experiments)

        lib.clearBackstoreFiles()
        lib.print('starting experiment ({} extended configurations)'.format(confcount))

        # TODO: factor this all out and replace the custom parts with lambda/function pointers
        with outputProgressBarRedirection() as originalStdOut:
            with tqdm(total=confcount, file=originalStdOut, unit='observation', dynamic_ncols=True) as progressBar:
                for conf in configurations:
                    for backendFn in backendFnTuples:
                        for runFn in experiments:
                            for dataClass in dataClasses:
                                    identifier = '[unknown]'

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

                                    if KEEP_RUNNER_LOGS:
                                        filename, fileext = os.path.splitext(os.path.basename(config['LOG_FILE_PATH']))
                                        os.rename(
                                            config['LOG_FILE_PATH'],
                                            '{}/{}-{}{}'.format(
                                                os.path.dirname(config['LOG_FILE_PATH']),
                                                filename,
                                                identifier,
                                                fileext
                                            )
                                        )

        lib.print('done', severity='OK')

    except KeyboardInterrupt:
        lib.print('done (experiment terminated via keyboard interrupt)', severity='WARN')
