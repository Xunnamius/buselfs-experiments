#!/usr/bin/env python3

import os

from collections import namedtuple
from datetime import datetime

import initrunner
from librunner import Librunner

if __name__ == "__main__":
    config = initrunner.parseConfigVars()
    lib = Librunner(config)

    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        lib.lexit('must be root/sudo', exitcode=1)
    
    # Bare bones basic initialization
    initrunner.initialize()

    if not os.path.exists(config['RAM0_PATH']):
        lib.lexit("did you forget to do the initial setup? (can't find {})".format(config['RAM0_PATH']), exitcode=2)

    if not os.path.exists('/dev/nbd0'):
        lib.lexit("did you forget to do the initial setup? (can't find /dev/nbd0)", exitcode=3)

    if not os.path.exists('{}/bin/sequential-freerun'.format(config['REPO_PATH'])) \
       or not os.path.exists('{}/bin/random-freerun'.format(config['REPO_PATH'])):
        lib.lexit("did you forget to run `make all` in buselfs-experiments?", exitcode=4)

    if not os.path.exists('{}/build/buselfs'.format(config['BUSELFS_PATH'])):
        lib.lexit("did you forget to run `make` in buselfs/build?", exitcode=10)

    with open(config['LOG_FILE_PATH'], 'w') as file:
        print(str(datetime.now()), '\n---------\n', file=file)

        os.chdir(config['RAM0_PATH'])
        lib.lprint('working directory set to {}'.format(config['RAM0_PATH']), logfile=file)

        lib.clearBackstoreFiles()

        lib.lprint('constructing configurations', logfile=file)

        num_nbd_devices = 16
        num_nbd_device = 0
        filesizes = ['1k', '4k', '512k', '5m', '40m']

        backendFnTuples = [
            (lib.createRawBackend, lib.destroyRawBackend, 'raw-vanilla'),
            (lib.createVanillaBackend, lib.destroyVanillaBackend, 'vanilla'),
            (lib.createDmcBackend, lib.destroyDmcBackend, 'dmcrypt'),
            (lib.createSbBackend, lib.destroySbBackend, 'strongbox')
        ]

        Configuration = namedtuple('Configuration', ['proto_test_name', 'fs_type', 'mount_args'])

        # TODO: add ability to provide configuration parameters to SB from here!
        configurations = (
            Configuration('nilfs2', 'nilfs2', []),
            Configuration('f2fs', 'f2fs', ['-o', 'background_gc_off']),
            Configuration('f2fs', 'f2fs', []),
            #Configuration('ext4-oj', 'ext4', []),
            #Configuration('ext4-fj', 'ext4', ['-o', 'data=journal'])
        )

        lib.lprint('starting experiment', logfile=file)

        for conf in configurations:
            for backendFn in backendFnTuples:
                for runFn in (lib.sequentialFreerun, lib.randomFreerun):
                    for filesize in filesizes:
                        device = 'nbd{}'.format(num_nbd_device)

                        backend = backendFn[0](file, device, conf.fs_type, conf.mount_args)
                        lib.dropPageCache()
                        runFn(file, device, filesize, '{}-{}-{}'.format(filesize, conf.proto_test_name, backendFn[2]))
                        backendFn[1](file, device, backend)
                        lib.clearBackstoreFiles()

                        num_nbd_device = (num_nbd_device + 1) % num_nbd_devices

        lib.clearBackstoreFiles()

        print('\n---------\n(finished)', file=file)
        lib.lprint('done', severity='OK')
