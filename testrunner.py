#!/usr/bin/env python3

from subprocess import Popen
from collections import namedtuple
from datetime import datetime

import os
import sys
import time
import glob
import pexpect

BACKEND_SIZE    = 800 # MiB
EXPAND_TABS     = 15 # tab stops
FREERUN_TIMEOUT = 900 # seconds
DROP_CACHE_PATH = '/proc/sys/vm/drop_caches'
TMP_ROOT_PATH   = '/tmp'
RAM0_PATH       = '/tmp/ram0'
BUSE_PATH       = '/home/odroid/bd3/repos/BUSE/buselogfs'
BUSELFS_PATH    = '/home/odroid/bd3/repos/buselfs/build/buselfs'
LOG_FILE_PATH   = '/home/odroid/bd3/runner.log'

################################################################################

def lprint(*args, logfile=None, severity='INFO', device=None):
    """Super special print"""
    preamble = '[{}{}]:\t'.format(severity, ':{}'.format(device) if device else '')
    print(preamble.expandtabs(EXPAND_TABS), *args, flush=True)

    if logfile:
        print(preamble.expandtabs(0), *args, file=logfile)

def lexit(*args, logfile=None, device=None, exitcode=1):
    """Super special exit"""
    if not args:
        args=['non-zero error code encountered ({})'.format(exitcode)]

    lprint(*args, severity='FATAL', logfile=logfile, device=device)
    sys.exit(exitcode)

def dropPageCache():
    """Drop the linux page cache programmatically"""
    lprint('dropping the page cache')

    with open(DROP_CACHE_PATH, 'w') as cache:
        cache.write('1\n')

def sleep(seconds):
    """Pause for a little bit (typically a courtesy period)"""
    lprint('waiting for {} seconds...'.format(seconds))
    time.sleep(seconds)

def clearBackstoreFiles():
    """Removes all RAM0_PATH/* files"""
    lprint('clearing backstore files')

    files = glob.glob('{}/*'.format(RAM0_PATH))
    for f in files:
        os.remove(f)

def createRawBackend(logfile, device, fs_type, mount_args=None):
    """Creates a non-BUSE raw drive-backed backend"""

    mount_args = mount_args or []
    backend_size_bytes = BACKEND_SIZE * 1024 * 1024
    backend_file_name = '{}/logfs-{}.bkstr'.format(RAM0_PATH, device)

    lprint('creating RAW backend ({} @ {})'.format(device, backend_file_name), logfile=logfile, device=device)

    f = open(backend_file_name, 'wb')
    f.seek(backend_size_bytes - 1)
    f.write(b'\0')
    f.close()

    fsize = os.path.getsize(backend_file_name)
    if fsize != backend_size_bytes:
        lexit('RAW backend file could not be created ({}!={})'.format(fsize, backend_size_bytes),
              logfile=logfile, device=device, exitcode=17)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, backend_file_name],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit('mkfs -t {} {} failed ({})'.format(fs_type, backend_file_name, mkfs.exitstatus),
            logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, backend_file_name, '{}/{}'.format(TMP_ROOT_PATH, device), '-o', 'loop'],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    
    lprint('checking mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount_out = mount.expect([r'on {}/{}'.format(TMP_ROOT_PATH, device), pexpect.EOF])
    if mount_out == 1:
        lexit('Could not verify successful mount of {} on {}/{}'.format(backend_file_name, TMP_ROOT_PATH, device), logfile=logfile,
              device=device,
              exitcode=19)

    return backend_file_name

def createRawDmcBackend(logfile, device, fs_type, mount_args=None):
    """Creates a non-BUSE raw drive-backed dm-crypt backend"""

    mount_args = mount_args or []
    backend_size_bytes = BACKEND_SIZE * 1024 * 1024
    backend_file_name = '{}/logfs-{}.bkstr'.format(RAM0_PATH, device)

    lprint('creating RAW dm-crypt LUKS volume backend ({} @ {})'.format(device, backend_file_name),
           logfile=logfile, device=device)

    f = open(backend_file_name, 'wb')
    f.seek(backend_size_bytes - 1)
    f.write(b'\0')
    f.close()

    fsize = os.path.getsize(backend_file_name)
    if fsize != backend_size_bytes:
        lexit('RAW dm-crypt LUKS volume backend file could not be created ({}!={})'.format(fsize, backend_size_bytes),
              logfile=logfile, device=device, exitcode=17)

    lprint('using cryptsetup', logfile=logfile, device=device)

    setup = pexpect.spawn('cryptsetup',
                         ['--verbose', '--cipher', 'aes-xts-plain64', '--key-size', '512', '--hash', 'sha512',
                          '--iter-time', '5000', '--use-urandom', 'luksFormat', backend_file_name],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    setup.expect(r'\(Type uppercase yes\): ')
    setup.sendline('YES')
    setup.expect('Enter passphrase: ')
    setup.sendline('t')
    setup.expect('Verify passphrase: ')
    setup.sendline('t')

    setup_out = setup.expect(['Command successful.', pexpect.EOF])

    if setup_out == 1:
        lexit(logfile=logfile, device=device, exitcode=9)

    lprint('opening dm-crypt LUKS volume', logfile=logfile, device=device)

    setup = pexpect.spawn('cryptsetup',
                         ['open', '--type', 'luks', backend_file_name, device],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    setup.expect('Enter passphrase for {}: '.format(backend_file_name))
    setup.sendline('t')

    setup.expect(pexpect.EOF)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, '/dev/mapper/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit('mkfs -t {} {} failed'.format(fs_type, '/dev/mapper/{}'.format(device)),
              logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/mapper/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device), '-o', 'loop'],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    
    lprint('checking mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount_out = mount.expect([r'on {}/{}'.format(TMP_ROOT_PATH, device), pexpect.EOF])

    if mount_out == 1:
        lexit("could not verify successful mount of /dev/mapper/{} on {}/{}".format(device, TMP_ROOT_PATH, device),
              logfile=logfile,
              device=device,
              exitcode=7)

    return backend_file_name

def createVanillaBackend(logfile, device, fs_type, mount_args=None):
    """Creates a buselogfs backend"""

    mount_args = mount_args or []

    lprint('creating vanilla backend ({})'.format(device), logfile=logfile, device=device)

    buse = Popen([BUSE_PATH, '--size', str(BACKEND_SIZE * 1024 * 1024), '/dev/{}'.format(device)],
                 stdout=logfile,
                 stderr=logfile)

    sleep(3)

    if buse.poll() is not None:
        lexit('the buselogfs process does not appear to have survived', logfile=logfile, device=device, exitcode=17)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    
    lprint('checking mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount_out = mount.expect([r'on {}/{}'.format(TMP_ROOT_PATH, device), pexpect.EOF])

    if mount_out == 1:
        lexit("could not verify successful mount of /dev/{} on {}/{}".format(device, TMP_ROOT_PATH, device),
              logfile=logfile,
              device=device,
              exitcode=19)

    return buse

def createSbBackend(logfile, device, fs_type, mount_args=None):
    """Creates a StrongBox backend"""

    mount_args = mount_args or []

    lprint('creating StrongBox backend ({})'.format(device), logfile=logfile, device=device)

    buse = Popen([BUSELFS_PATH, '--backstore-size', str(BACKEND_SIZE), '--cipher', 'sc_hc128', '--default-password', 'create', device],
                 stdout=logfile,
                 stderr=logfile)

    sleep(30)

    if buse.poll() is not None:
        lexit('the StrongBox process does not appear to have survived', logfile=logfile, device=device, exitcode=17)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    
    lprint('checking mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount_out = mount.expect([r'on {}/{}'.format(TMP_ROOT_PATH, device), pexpect.EOF])

    if mount_out == 1:
        lexit("could not verify successful mount of /dev/{} on {}/{}".format(device, TMP_ROOT_PATH, device),
              logfile=logfile,
              device=device,
              exitcode=15)

    return buse

def createDmcBackend(logfile, device, fs_type, mount_args=None):
    """Creates a dm-crypt + AES-XTS backend"""

    mount_args = mount_args or []

    lprint('creating dm-crypt LUKS volume buselogfs backend ({})'.format(device), logfile=logfile, device=device)

    buse = Popen([BUSE_PATH, '--size', str(BACKEND_SIZE * 1024 * 1024), '/dev/{}'.format(device)],
                 stdout=logfile,
                 stderr=logfile)

    sleep(3)

    if buse.poll() is not None:
        lexit('the buselogfs process does not appear to have survived', logfile=logfile, device=device, exitcode=8)

    lprint('using cryptsetup', logfile=logfile, device=device)

    setup = pexpect.spawn('cryptsetup',
                         ['--verbose', '--cipher', 'aes-xts-plain64', '--key-size', '512', '--hash', 'sha512',
                          '--iter-time', '5000', '--use-urandom', 'luksFormat', '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    setup.expect(r'\(Type uppercase yes\): ')
    setup.sendline('YES')
    setup.expect('Enter passphrase: ')
    setup.sendline('t')
    setup.expect('Verify passphrase: ')
    setup.sendline('t')

    setup_out = setup.expect(['Command successful.', pexpect.EOF])

    if setup_out == 1:
        lexit(logfile=logfile, device=device, exitcode=9)

    lprint('opening dm-crypt LUKS volume', logfile=logfile, device=device)

    setup = pexpect.spawn('cryptsetup',
                         ['open', '--type', 'luks', '/dev/{}'.format(device), device],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    setup.expect('Enter passphrase for /dev/{}: '.format(device))
    setup.sendline('t')

    setup.expect(pexpect.EOF)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, '/dev/mapper/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/mapper/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    
    lprint('checking mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    mount_out = mount.expect([r'on {}/{}'.format(TMP_ROOT_PATH, device), pexpect.EOF])

    if mount_out == 1:
        lexit("could not verify successful mount of /dev/mapper/{} on {}/{}".format(device, TMP_ROOT_PATH, device),
              logfile=logfile,
              device=device,
              exitcode=7)

    return buse

def destroyRawBackend(logfile, device, backend_proc):
    """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

    lprint('running umount', logfile=logfile, device=device)

    mount = pexpect.spawn('umount',
                         ['{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=21)

    lprint('deleting raw file-based backing store {}'.format(backend_proc), logfile=logfile, device=device)

    if not os.path.isfile(backend_proc):
        lexit('RAW backend file {} does not exist?!'.format(backend_proc), logfile=logfile, device=device, exitcode=23)

    os.remove(backend_proc)

    if os.path.isfile(backend_proc):
        lexit('RAW backend file {} could not be destroyed?!'.format(backend_proc), logfile=logfile, device=device, exitcode=22)

def destroyRawDmcBackend(logfile, device, backend_proc):
    """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

    lprint('running umount', logfile=logfile, device=device)

    mount = pexpect.spawn('umount',
                         ['{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=20)

    lprint('closing dm-crypt LUKS volume', logfile=logfile, device=device)

    setup = pexpect.spawn('cryptsetup',
                         ['close', device],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    setup.expect(pexpect.EOF)

    lprint('deleting raw file-based backing store {}'.format(backend_proc), logfile=logfile, device=device)

    if not os.path.isfile(backend_proc):
        lexit('RAW backend file {} does not exist?!'.format(backend_proc), logfile=logfile, device=device, exitcode=23)

    os.remove(backend_proc)

    if os.path.isfile(backend_proc):
        lexit('RAW backend file {} could not be destroyed?!'.format(backend_proc), logfile=logfile, device=device, exitcode=21)

def destroyVanillaBackend(logfile, device, backend_proc):
    """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

    lprint('running umount', logfile=logfile, device=device)

    mount = pexpect.spawn('umount',
                         ['{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=21)

    lprint('terminating background fs process', logfile=logfile, device=device)

    backend_proc.terminate()

def destroySbBackend(logfile, device, backend_proc):
    """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

    lprint('running umount', logfile=logfile, device=device)

    mount = pexpect.spawn('umount',
                         ['{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=22)

    lprint('terminating background fs process', logfile=logfile, device=device)

    backend_proc.terminate()

def destroyDmcBackend(logfile, device, backend_proc):
    """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

    lprint('running umount', logfile=logfile, device=device)

    mount = pexpect.spawn('umount',
                         ['{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=20)

    lprint('closing dm-crypt LUKS volume', logfile=logfile, device=device)

    setup = pexpect.spawn('cryptsetup',
                         ['close', device],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    setup.expect(pexpect.EOF)

    lprint('terminating background fs process', logfile=logfile, device=device)

    backend_proc.terminate()

def symlinkDataClass(logfile, device, data_class):
    """Symlinks the proper data file to be written and read in by experiments"""

    datafile = '/home/odroid/bd3/repos/energy-AES-1/data{}.random'.format(data_class)
    symlfile = '/home/odroid/bd3/repos/energy-AES-1/data.target'

    lprint('setting data target to class {}'.format(data_class), logfile=logfile, device=device)

    if not os.path.exists(datafile):
        lexit('data class "{}" does not exist at {}'.format(data_class, datafile),
              logfile=logfile,
              device=device,
              exitcode=25)

    try:
        os.remove(symlfile)
    except FileNotFoundError:
        pass

    os.symlink(datafile, symlfile)

    if not os.path.exists(symlfile):
        lexit('os.symlink failed to create {}'.format(symlfile), logfile=logfile, device=device, exitcode=26)

def sequentialFreerun(logfile, device, data_class, test_name):
    """Runs the sequential cpp freerun tests"""

    symlinkDataClass(logfile, device, data_class)

    lprint('running sequential freerun test target {}'.format(test_name), logfile=logfile, device=device)

    test = pexpect.spawn('/home/odroid/bd3/repos/energy-AES-1/bin/cpp-sequential-freerun',
                         ['ram', test_name, '{}/{}'.format(TMP_ROOT_PATH, device)],
                         timeout=FREERUN_TIMEOUT)

    test_out = test.expect([pexpect.EOF, pexpect.TIMEOUT])
    test.close()

    if test_out == 1:
        lexit('cpp-sequential-freerun timed out', logfile=logfile, device=device, exitcode=23)

    elif test.exitstatus != 0:
        lexit('cpp-sequential-freerun returned non-zero error code (-{})'.format(test.exitstatus),
              logfile=logfile,
              device=device,
              exitcode=24)

def randomFreerun(logfile, device, data_class, test_name):
    """Runs the random cpp freerun tests"""

    symlinkDataClass(logfile, device, data_class)

    lprint('running random freerun test target {}'.format(test_name), logfile=logfile, device=device)

    test = pexpect.spawn('/home/odroid/bd3/repos/energy-AES-1/bin/cpp-random-freerun',
                         ['ram', test_name, '{}/{}'.format(TMP_ROOT_PATH, device)],
                         timeout=FREERUN_TIMEOUT)

    test_out = test.expect([pexpect.EOF, pexpect.TIMEOUT])
    test.close()

    if test_out == 1:
        lexit('cpp-random-freerun timed out', logfile=logfile, device=device, exitcode=27)

    elif test.exitstatus != 0:
        lexit('cpp-random-freerun returned non-zero error code (-{})'.format(test.exitstatus),
              logfile=logfile,
              device=device,
              exitcode=28)

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        lexit('must be root/sudo', exitcode=1)

    if not os.path.exists(RAM0_PATH):
        lexit("did you forget to do the initial setup? (can't find {})".format(RAM0_PATH), exitcode=2)

    if not os.path.exists('/dev/nbd0'):
        lexit("did you forget to do the initial setup? (can't find /dev/nbd0)", exitcode=3)

    if not os.path.exists('/home/odroid/bd3/repos/energy-AES-1/bin/cpp-sequential-freerun') \
       or not os.path.exists('/home/odroid/bd3/repos/energy-AES-1/bin/cpp-random-freerun'):
        lexit("did you forget to run `make all` in energy-AES-1?", exitcode=4)

    if not os.path.exists(BUSELFS_PATH):
        lexit("did you forget to run `make` in buselfs/build?", exitcode=10)

    with open(LOG_FILE_PATH, 'w') as file:
        print(str(datetime.now()), '\n---------\n', file=file)

        os.chdir(RAM0_PATH)
        lprint('working directory set to {}'.format(RAM0_PATH), logfile=file)

        clearBackstoreFiles()

        lprint('constructing configurations', logfile=file)

        num_nbd_devices = 16
        num_nbd_device = 0
        #filesizes = ['1k', '4k', '512k', '5m', '40m']
        #filesizes = ['5g']
        filesizes = ['1k', '5m']

        backendFnTuples = [
            #(createRawBackend, destroyRawBackend, 'raw-vanilla'),
            #(createVanillaBackend, destroyVanillaBackend, 'vanilla'),
            #(createDmcBackend, destroyDmcBackend, 'dmcrypt'),
            (createSbBackend, destroySbBackend, 'strongbox')
        ]

        Configuration = namedtuple('Configuration', ['proto_test_name', 'fs_type', 'mount_args'])

        # TODO: add ability to provide configuration parameters to SB from here!
        configurations = (
            #Configuration('nilfs2', 'nilfs2', []),
            #Configuration('f2fs', 'f2fs', ['-o', 'background_gc_off']),
            Configuration('f2fs', 'f2fs', []),
            #Configuration('ext4-oj', 'ext4', []),
            #Configuration('ext4-fj', 'ext4', ['-o', 'data=journal'])
        )

        lprint('starting experiment', logfile=file)

        for conf in configurations:
            for backendFn in backendFnTuples:
                for runFn in [sequentialFreerun]: #(sequentialFreerun, randomFreerun):
                    for filesize in filesizes:
                        device = 'nbd{}'.format(num_nbd_device)

                        backend = backendFn[0](file, device, conf.fs_type, conf.mount_args)
                        dropPageCache()
                        runFn(file, device, filesize, '{}-{}-{}'.format(filesize, conf.proto_test_name, backendFn[2]))
                        backendFn[1](file, device, backend)
                        clearBackstoreFiles()

                        num_nbd_device = (num_nbd_device + 1) % num_nbd_devices

        clearBackstoreFiles()

        print('\n---------\n(finished)', file=file)
        lprint('done', severity='OK')
