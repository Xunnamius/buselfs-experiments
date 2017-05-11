#!/usr/bin/env python3

import os
import sys
import time
import glob
import pexpect
from datetime import datetime

BACKEND_SIZE    = 900 # MiB
EXPAND_TABS     = 15 # tab stops
FREERUN_TIMEOUT = 300 # seconds
DROP_CACHE_PATH = '/proc/sys/vm/drop_caches'
TMP_ROOT_PATH   = '/tmp'
RAM0_PATH       = '/tmp/ram0'
BUSE_PATH       = '/home/odroid/bd3/repos/BUSE/buselogfs'
BUSELFS_PATH    = '/home/odroid/bd3/repos/buselfs/build/buselfs'
LOG_FILE_PATH   = '/tmp/runner.log'

################################################################################

def lprint(*args, logfile=None, severity='INFO', device=None):
    """Super special print"""
    preamble = '[{}{}]:\t'.format(severity, ':{}'.format(device) if device else '')
    print(preamble.expandtabs(EXPAND_TABS), *args)

    if logfile:
        print(preamble.expandtabs(0), *args, file=logfile)

def lexit(*args, logfile=None, device=None, exitcode=-1):
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
    
def createVanillaBackend(logfile, device, fs_type, mount_args=None):
    """Creates a buselogfs backend"""

    mount_args = mount_args or []

    lprint('creating vanilla backend ({})'.format(device), logfile=logfile, device=device)

    buse = pexpect.spawn(BUSE_PATH,
                         ['--size', str(BACKEND_SIZE * 1024 * 1024), '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=True,
                         encoding='utf-8')

    sleep(5)

    if not buse.isalive():
        lexit('the buselogfs process does not appear to have survived', logfile=logfile, device=device, exitcode=16)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=17)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=18)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount_out = mount.expect([r'/dev/{} on {}/{}'.format(device, TMP_ROOT_PATH, device), pexpect.EOF])
    
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

    buse = pexpect.spawn(BUSELFS_PATH,
                         ['--backstore-size', str(BACKEND_SIZE),
                         '--default-password', 'create', device],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    buse_out = buse.expect(['100%', pexpect.EOF])

    if buse_out == 1:
        lexit('the StrongBox process does not appear to have survived', logfile=logfile, device=device, exitcode=11)

    lprint('running mkfs', logfile=logfile, device=device)

    mkfs = pexpect.spawn('mkfs',
                         ['-t', fs_type, '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=13)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=14)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount_out = mount.expect([r'/dev/{} on {}/{}'.format(device, TMP_ROOT_PATH, device), pexpect.EOF])
    
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

    buse = pexpect.spawn(BUSE_PATH,
                         ['--size', str(BACKEND_SIZE * 1024 * 1024), '/dev/{}'.format(device)],
                         logfile=logfile,
                         echo=True,
                         encoding='utf-8')

    sleep(5)

    if not buse.isalive():
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
                         encoding='utf-8')

    mkfs.expect(pexpect.EOF)
    mkfs.close()

    if mkfs.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=5)

    lprint('running mount', logfile=logfile, device=device)

    mount = pexpect.spawn('mount',
                         mount_args + ['-t', fs_type, '/dev/mapper/{}'.format(device), '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount.expect(pexpect.EOF)
    mount.close()

    if mount.exitstatus != 0:
        lexit(logfile=logfile, device=device, exitcode=6)

    mount = pexpect.spawn('mount',
                         logfile=logfile,
                         echo=False,
                         encoding='utf-8')

    mount_out = mount.expect([r'/dev/mapper/{} on {}/{}'.format(device, TMP_ROOT_PATH, device), pexpect.EOF])
    
    if mount_out == 1:
        lexit("could not verify successful mount of /dev/mapper/{} on {}/{}".format(device, TMP_ROOT_PATH, device),
              logfile=logfile,
              device=device,
              exitcode=7)

    return buse
    
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

    backend_proc.terminate(True)

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

    backend_proc.terminate(True)

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

    backend_proc.terminate(True)

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
    
    lprint('running sequential freerun test', logfile=logfile, device=device)

    test = pexpect.spawn('/home/odroid/bd3/repos/energy-AES-1/bin/cpp-sequential-freerun',
                         ['ram', test_name, '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         timeout=FREERUN_TIMEOUT,
                         echo=False,
                         encoding='utf-8')

    test_out = test.expect([pexpect.EOF, pexpect.TIMEOUT])
    test.close()

    if test_out == 1:
        lexit('cpp-sequential-freerun timed out', logfile=logfile, device=device, exitcode=23)

    elif test.exitstatus != 0:
        lexit('cpp-sequential-freerun returned non-zero error code <{}>'.format(test.exitstatus),
              logfile=logfile,
              device=device,
              exitcode=24)

def randomFreerun(logfile, device, data_class, test_name):
    """Runs the random cpp freerun tests"""
    
    symlinkDataClass(logfile, device, data_class)
    
    lprint('running random freerun test', logfile=logfile, device=device)

    test = pexpect.spawn('/home/odroid/bd3/repos/energy-AES-1/bin/cpp-random-freerun',
                         ['ram', test_name, '{}/{}'.format(TMP_ROOT_PATH, device)],
                         logfile=logfile,
                         timeout=FREERUN_TIMEOUT,
                         echo=False,
                         encoding='utf-8')

    test_out = test.expect([pexpect.EOF, pexpect.TIMEOUT])
    test.close()

    if test_out == 1:
        lexit('cpp-random-freerun timed out', logfile=logfile, device=device, exitcode=27)

    elif test.exitstatus != 0:
        lexit('cpp-random-freerun returned non-zero error code <{}>'.format(test.exitstatus),
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

        # clearBackstoreFiles()

        # nbd0 = createVanillaBackend(file, 'nbd0', 'ext4', ['-o', 'data=journal'])

        # dropPageCache()

        # sleep(30)

        # destroyVanillaBackend(file, 'nbd0', nbd0)

        # clearBackstoreFiles()

        #sequentialFreerun(file, 'nbd13', 'data512k', 'faker-faker-faker2')
        #randomFreerun(file, 'nbd13', 'data512k', 'faker-faker-faker3')
        print('\n---------\n(finished)', file=file)
        lprint('done', severity='OK')
