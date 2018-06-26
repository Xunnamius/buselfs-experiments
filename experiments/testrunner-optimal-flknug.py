#!/usr/bin/env python3

import os
from datetime import datetime

import initrunner
from librunner import Librunner, Configuration

config = initrunner.parseConfigVars()
lib = Librunner(config)

### Configurables ###

num_nbd_devices = 16
num_nbd_device = 0

filesystems = ['nilfs', 'f2fs']
filesizes = ['1k', '4k', '512k', '5m', '40m']

flksizes = [128, 256, 512, 1024, 2048, 8192, 16384, 32768, 65536]
fpns = [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]

experiments = [lib.sequentialFreerun] #[lib.sequentialFreerun, lib.randomFreerun]

ciphers = ['sc_chacha8',
           'sc_chacha12',
           'sc_salsa8',
           'sc_salsa12',
           'sc_salsa20',
           'sc_aes128_ctr',
           'sc_aes256_ctr',
           'sc_hc128',
           'sc_rabbit',
           'sc_sosemanuk'
]

backendFnTuples = [
    #(lib.createRawBackend, lib.destroyRawBackend, 'raw-vanilla'),
    #(lib.createVanillaBackend, lib.destroyVanillaBackend, 'vanilla'),
    #(lib.createDmcBackend, lib.destroyDmcBackend, 'dmcrypt'),
    (lib.createSbBackend, lib.destroySbBackend, 'strongbox')
]

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        lib.lexit('must be root/sudo', exitcode=1)
    
    # Bare bones basic initialization
    initrunner.initialize()
    lib.checkSanity()

    with open(config['LOG_FILE_PATH'], 'w') as file:
        print(str(datetime.now()), '\n---------\n', file=file)

        os.chdir(config['RAM0_PATH'])
        
        lib.lprint('working directory set to {}'.format(config['RAM0_PATH']), logfile=file)
        lib.clearBackstoreFiles()
        lib.lprint('constructing configurations', logfile=file)

        # * Optimal flake/nugget size perf test
        configurations = []
        for filesystem in filesystems:
            configurations.append(Configuration('{}#baseline'.format(filesystem), filesystem, [], []))
            for fpn in fpns:
                for flk_size in flksizes:
                    configurations += [
                        Configuration('{}#{}'.format(filesystem, cipher),
                                      filesystem,
                                      [],
                                      ['--cipher', cipher, '--flake-size', str(flk_size), '--flakes-per-nugget', str(fpn)]
                        ) for cipher in ciphers]

        confcount = len(configurations) * len(backendFnTuples) * len(filesizes) * len(experiments)
        
        lib.lprint('starting experiment ({} configurations; estimated {} minutes)'
           .format(confcount, confcount * 45 / 60), logfile=file)

        for conf in configurations:
            for backendFn in backendFnTuples:
                for runFn in experiments:
                    for filesize in filesizes:
                        device = 'nbd{}'.format(num_nbd_device)

                        backend = backendFn[0](file, device, conf.fs_type, conf.mount_args, conf.sb_args)
                        lib.dropPageCache()
                        runFn(file, device, filesize, '{}-{}-{}'.format(filesize, conf.proto_test_name, backendFn[2]))
                        backendFn[1](file, device, backend)
                        lib.clearBackstoreFiles()

                        num_nbd_device = (num_nbd_device + 1) % num_nbd_devices

        lib.clearBackstoreFiles()

        print('\n---------\n(finished)', file=file)
        lib.lprint('done', severity='OK')