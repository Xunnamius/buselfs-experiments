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

# TODO: add stringified names to experiments (tuples?)
experiments = [lib.sequentialFreerun]

ciphers = [#'sc_hc128', # ! too slow to test (see buselfs source for rationale)
           'sc_rabbit',
           'sc_sosemanuk',
           'sc_salsa8',
           'sc_salsa12',
           'sc_salsa20',
           'sc_aes128_ctr',
           'sc_aes256_ctr',
           'sc_chacha20_neon',
           'sc_chacha12_neon',
           'sc_chacha8_neon',
           'sc_freestyle_fast',
           'sc_freestyle_balanced',
           'sc_freestyle_secure',
]

backendFnTuples = [
    (lib.createSbBackend, lib.destroySbBackend, 'strongbox')
]

# ? Constructed automatically later, but any manual entries can be added here
configurations = []

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

    for filesystem in filesystems:
        configurations.append(Configuration('{}#baseline'.format(filesystem), filesystem, [], []))
        configurations.extend([Configuration('{}#{}'.format(filesystem, cipher), filesystem, [], ['--cipher', cipher]) for cipher in ciphers])

    confcount = len(configurations) * len(backendFnTuples) * len(dataClasses) * len(experiments)

    lib.clearBackstoreFiles()
    lib.print('starting experiment ({} configurations)'.format(confcount))

    # TODO: factor this all out and replace the custom parts with lambda/function pointers
    # ! This is old code. If we use this to gather results, it must be updated like optflknug and swap2019 are
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

                                predictedResultFileName = RESULTS_FILE_NAME.format(runFn.experiment_name, identifier)

                                predictedResultFilePath = os.path.realpath(
                                    RESULTS_PATH.format(config['REPO_PATH'], predictedResultFileName)
                                )

                                lib.print(' ------------------ {} experiment: {} ------------------'.format(
                                    runFn.experiment_name,
                                    identifier
                                ))

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
                                        # TODO: instead of printing the warning
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
