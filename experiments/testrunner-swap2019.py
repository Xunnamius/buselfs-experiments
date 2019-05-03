#!/usr/bin/env python3

import os
import sys
from datetime import datetime
from tqdm import tqdm

import initrunner
from librunner import Librunner
from librunner.util import outputProgressBarRedirection, printInstabilityWarning, Configuration, RESULTS_PATH, RESULTS_FILE_NAME
from librunner.exception import ExperimentError

config = initrunner.parseConfigVars()
lib = Librunner(config)

### * Configurables * ###

# ! REMEMBER: it's nilfs2 (TWO) with a 2! Not just 'nilfs'!
filesystems = ['f2fs']
dataClasses = ['1k', '4k', '512k', '5m', '40m']

flksizes = [512, 1024, 2048, 4096, 8192]#, 16384]
fpns = [8, 16, 32, 64, 128, 256]

# TODO: add stringified names to experiments (tuples?)
experiments = [lib.sequentialFreerun, lib.randomFreerun]

# ? These are all the cipher swapping pairs that will be tested
# ? each element: (primary cipher, swap cipher, swap strategy)
cipherpairs = [
    ('', '', ''),
    ('', '', '')
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
    initrunner.initialize(config)
    initrunner.cwdToRAMDir(config)
    lib.checkSanity()

    lib.print('working directory set to {}'.format(config['RAM0_PATH']))
    lib.clearBackstoreFiles()
    lib.print('constructing configurations')

    # * Optimal flake/nugget size perf test
    configurations = []
    for filesystem in filesystems:
        configurations.append(Configuration('{}#baseline'.format(filesystem), filesystem, [], []))
        for fpn in fpns:
            for flk_size in flksizes:
                configurations.extend([
                    Configuration(
                        '{}#{}#{}#{}#{}#{}'.format(filesystem, cipherpair[0], flk_size, fpn, cipherpair[1], cipherpair[2]),
                        filesystem,
                        [],
                        [
                            '--cipher', cipherpair[0],
                            '--flake-size', str(flk_size),
                            '--flakes-per-nugget', str(fpn),
                            '--swap-cipher', cipherpair[1],
                            '--swap-strategy', cipherpair[2]
                        ]
                    ) for cipherpair in cipherpairs])

    confcount = len(configurations) * len(backendFnTuples) * len(dataClasses) * len(experiments)

    lib.clearBackstoreFiles()
    lib.print('starting experiment ({} configurations)'.format(confcount))

    # TODO:! factor this all out and replace the custom parts with lambda/function pointers
    with outputProgressBarRedirection() as originalStdOut:
        with tqdm(total=confcount, file=originalStdOut, dynamic_ncols=True) as progressBar:
            for conf in configurations:
                for backendFn in backendFnTuples:
                    for runFn in experiments:
                        for dataClass in dataClasses:
                            with open(config['LOG_FILE_PATH'], 'w') as file:
                                print(str(datetime.now()), '\n---------\n', file=file)

                                lib.logFile = file
                                identifier = '{}-{}-{}'.format(dataClass, conf.proto_test_name, backendFn[2])

                                predictedResultFileName = RESULTS_FILE_NAME.format(
                                    'sequential' if experiments == lib.sequentialFreerun else 'random',
                                    identifier
                                )

                                predictedResultFilePath = os.path.realpath(
                                    RESULTS_PATH.format(config['REPO_PATH'], predictedResultFileName)
                                )

                                lib.print(' ------------------ Experiment "{}" ------------------'.format(identifier))

                                # ? If the results file exists already, then skip this experiment!
                                if os.path.exists(predictedResultFilePath):
                                    lib.print('Results file {} was found, experiment skipped!'.format(predictedResultFilePath))

                                else:
                                    backendFn[0](conf.fs_type, conf.mount_args, conf.device_args)
                                    lib.dropPageCache()

                                    try:
                                        runFn(dataClass, identifier)

                                    # TODO: make ctrl-c exit when appropriate
                                    except ExperimentError:
                                        printInstabilityWarning(lib, config)
                                        # TODO:! instead of printing the warning
                                        # TODO: and raising the error, just run
                                        # TODO: the commands and attempt to
                                        # TODO: continue! (but raise if it fails
                                        # TODO: twice in a row)
                                        raise

                                    backendFn[1]()
                                    lib.clearBackstoreFiles()

                                lib.print(' ------------------ *** ------------------')
                                lib.logFile = None

                                progressBar.update()

    lib.print('done', severity='OK')
