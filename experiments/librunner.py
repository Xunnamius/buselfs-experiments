"""This is a base Python module that holds most of the shared test suite code. If you're looking to add new test features, start here."""

import os
import sys
import time
import glob
import pexpect
import inspect

from subprocess import Popen

# TODO: DRY the methods of this class out (so much repetition!)
class Librunner():
    def __init__(self, config={}):
        self.config = config

    def lprint(self, *args, logfile=None, severity='INFO', device=None):
        """Super special print"""
        preamble = '[{}{}]: '.format(severity, ':{}'.format(device) if device else '')
        print(preamble.expandtabs(self.config['EXPAND_TABS_INT']), *args, flush=True)

        if logfile:
            print(preamble.expandtabs(0), *args, file=logfile)

    def lexit(self, *args, logfile=None, device=None, exitcode=1):
        """Super special exit"""
        if not args:
            args=['non-zero error code encountered ({})'.format(exitcode)]

        self.lprint(*args, severity='FATAL', logfile=logfile, device=device)
        sys.exit(exitcode)

    def dropPageCache(self, ):
        """Drop the linux page cache programmatically"""
        self.lprint('dropping the page cache')

        with open(self.config['DROP_CACHE_PATH'], 'w') as cache:
            cache.write('1\n')

    def sleep(self, seconds):
        """Pause for a little bit (typically a courtesy period)"""
        self.lprint('waiting for {} seconds...'.format(seconds))
        time.sleep(seconds)

    def clearBackstoreFiles(self, ):
        """Removes all RAM0_PATH/* files"""
        self.lprint('clearing backstore files')

        files = glob.glob('{}/*'.format(self.config['RAM0_PATH']))
        for f in files:
            os.remove(f)

    def createRawBackend(self, logfile, device, fs_type, mount_args=None):
        """Creates a non-BUSE raw drive-backed backend"""

        mount_args = mount_args or []
        backend_size_bytes = self.config['BACKEND_SIZE_INT'] * 1024 * 1024
        backend_file_name = '{}/logfs-{}.bkstr'.format(self.config['RAM0_PATH'], device)

        self.lprint('creating RAW backend ({} @ {})'.format(device, backend_file_name), logfile=logfile, device=device)

        f = open(backend_file_name, 'wb')
        f.seek(backend_size_bytes - 1)
        f.write(b'\0')
        f.close()

        fsize = os.path.getsize(backend_file_name)
        if fsize != backend_size_bytes:
            self.lexit('RAW backend file could not be created ({}!={})'.format(fsize, backend_size_bytes),
                logfile=logfile, device=device, exitcode=17)

        self.lprint('running mkfs', logfile=logfile, device=device)

        mkfs = pexpect.spawn('mkfs',
                            ['-t', fs_type, backend_file_name],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mkfs.expect(pexpect.EOF)
        mkfs.close()

        if mkfs.exitstatus != 0:
            self.lexit('mkfs -t {} {} failed ({})'.format(fs_type, backend_file_name, mkfs.exitstatus),
                logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

        self.lprint('running mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            mount_args + ['-t', fs_type, backend_file_name, '{}/{}'.format(self.config['TMP_ROOT_PATH'], device), '-o', 'loop'],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()
        
        self.lprint('checking mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount_out = mount.expect([r'on {}/{}'.format(self.config['TMP_ROOT_PATH'], device), pexpect.EOF])
        if mount_out == 1:
            self.lexit('Could not verify successful mount of {} on {}/{}'.format(backend_file_name, self.config['TMP_ROOT_PATH'], device), logfile=logfile,
                device=device,
                exitcode=19)

        mount.close()
        return backend_file_name

    def createRawDmcBackend(self, logfile, device, fs_type, mount_args=None):
        """Creates a non-BUSE raw drive-backed dm-crypt backend"""

        mount_args = mount_args or []
        backend_size_bytes = self.config['BACKEND_SIZE_INT'] * 1024 * 1024
        backend_file_name = '{}/logfs-{}.bkstr'.format(self.config['RAM0_PATH'], device)

        self.lprint('creating RAW dm-crypt LUKS volume backend ({} @ {})'.format(device, backend_file_name),
            logfile=logfile, device=device)

        f = open(backend_file_name, 'wb')
        f.seek(backend_size_bytes - 1)
        f.write(b'\0')
        f.close()

        fsize = os.path.getsize(backend_file_name)
        if fsize != backend_size_bytes:
            self.lexit('RAW dm-crypt LUKS volume backend file could not be created ({}!={})'.format(fsize, backend_size_bytes),
                logfile=logfile, device=device, exitcode=17)

        self.lprint('using cryptsetup', logfile=logfile, device=device)

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
            self.lexit(logfile=logfile, device=device, exitcode=9)

        self.lprint('opening dm-crypt LUKS volume', logfile=logfile, device=device)

        setup = pexpect.spawn('cryptsetup',
                            ['open', '--type', 'luks', backend_file_name, device],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        setup.expect('Enter passphrase for {}: '.format(backend_file_name))
        setup.sendline('t')

        setup.expect(pexpect.EOF)

        self.lprint('running mkfs', logfile=logfile, device=device)

        mkfs = pexpect.spawn('mkfs',
                            ['-t', fs_type, '/dev/mapper/{}'.format(device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mkfs.expect(pexpect.EOF)
        mkfs.close()

        if mkfs.exitstatus != 0:
            self.lexit('mkfs -t {} {} failed'.format(fs_type, '/dev/mapper/{}'.format(device)),
                logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

        self.lprint('running mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            mount_args + ['-t', fs_type, '/dev/mapper/{}'.format(device), '{}/{}'.format(self.config['TMP_ROOT_PATH'], device), '-o', 'loop'],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()
        
        self.lprint('checking mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount_out = mount.expect([r'on {}/{}'.format(self.config['TMP_ROOT_PATH'], device), pexpect.EOF])

        if mount_out == 1:
            self.lexit("could not verify successful mount of /dev/mapper/{} on {}/{}".format(device, self.config['TMP_ROOT_PATH'], device),
                logfile=logfile,
                device=device,
                exitcode=7)

        mount.close()
        return backend_file_name

    def createVanillaBackend(self, logfile, device, fs_type, mount_args=None):
        """Creates a buselogfs backend"""

        mount_args = mount_args or []

        self.lprint('creating vanilla backend ({})'.format(device), logfile=logfile, device=device)

        buse = Popen([self.config['BUSE_PATH'], '--size', str(self.config['BACKEND_SIZE_INT'] * 1024 * 1024), '/dev/{}'.format(device)],
                    stdout=logfile,
                    stderr=logfile)

        self.sleep(3)

        if buse.poll() is not None:
            self.lexit('the buselogfs process does not appear to have survived', logfile=logfile, device=device, exitcode=17)

        self.lprint('running mkfs', logfile=logfile, device=device)

        mkfs = pexpect.spawn('mkfs',
                            ['-t', fs_type, '/dev/{}'.format(device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mkfs.expect(pexpect.EOF)
        mkfs.close()

        if mkfs.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

        self.lprint('running mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            mount_args + ['-t', fs_type, '/dev/{}'.format(device), '{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()
        
        self.lprint('checking mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount_out = mount.expect([r'on {}/{}'.format(self.config['TMP_ROOT_PATH'], device), pexpect.EOF])

        if mount_out == 1:
            self.lexit("could not verify successful mount of /dev/{} on {}/{}".format(device, self.config['TMP_ROOT_PATH'], device),
                logfile=logfile,
                device=device,
                exitcode=19)

        mount.close()
        return buse

    def createSbBackend(self, logfile, device, fs_type, mount_args=None):
        """Creates a StrongBox backend"""

        mount_args = mount_args or []

        self.lprint('creating StrongBox backend ({})'.format(device), logfile=logfile, device=device)

        buse = Popen(['{}/build/buselfs'.format(self.config['BUSELFS_PATH']), '--backstore-size', str(self.config['BACKEND_SIZE_INT']), '--default-self, password', 'create', device],
                    stdout=logfile,
                    stderr=logfile)

        self.sleep(30)

        if buse.poll() is not None:
            self.lexit('the StrongBox process does not appear to have survived', logfile=logfile, device=device, exitcode=17)

        self.lprint('running mkfs', logfile=logfile, device=device)

        mkfs = pexpect.spawn('mkfs',
                            ['-t', fs_type, '/dev/{}'.format(device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mkfs.expect(pexpect.EOF)
        mkfs.close()

        if mkfs.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

        self.lprint('running mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            mount_args + ['-t', fs_type, '/dev/{}'.format(device), '{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()
        
        self.lprint('checking mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount_out = mount.expect([r'on {}/{}'.format(self.config['TMP_ROOT_PATH'], device), pexpect.EOF])

        if mount_out == 1:
            self.lexit("could not verify successful mount of /dev/{} on {}/{}".format(device, self.config['TMP_ROOT_PATH'], device),
                logfile=logfile,
                device=device,
                exitcode=15)
        
        mount.close()
        return buse

    def createDmcBackend(self, logfile, device, fs_type, mount_args=None):
        """Creates a dm-crypt + AES-XTS backend"""

        mount_args = mount_args or []

        self.lprint('creating dm-crypt LUKS volume buselogfs backend ({})'.format(device), logfile=logfile, device=device)

        buse = Popen([self.config['BUSE_PATH'], '--size', str(self.config['BACKEND_SIZE_INT'] * 1024 * 1024), '/dev/{}'.format(device)],
                    stdout=logfile,
                    stderr=logfile)

        self.sleep(3)

        if buse.poll() is not None:
            self.lexit('the buselogfs process does not appear to have survived', logfile=logfile, device=device, exitcode=8)

        self.lprint('using cryptsetup', logfile=logfile, device=device)

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
            self.lexit(logfile=logfile, device=device, exitcode=9)

        self.lprint('opening dm-crypt LUKS volume', logfile=logfile, device=device)

        setup = pexpect.spawn('cryptsetup',
                            ['open', '--type', 'luks', '/dev/{}'.format(device), device],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        setup.expect('Enter passphrase for /dev/{}: '.format(device))
        setup.sendline('t')

        setup.expect(pexpect.EOF)

        self.lprint('running mkfs', logfile=logfile, device=device)

        mkfs = pexpect.spawn('mkfs',
                            ['-t', fs_type, '/dev/mapper/{}'.format(device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mkfs.expect(pexpect.EOF)
        mkfs.close()

        if mkfs.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=-1*mkfs.exitstatus)

        self.lprint('running mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            mount_args + ['-t', fs_type, '/dev/mapper/{}'.format(device), '{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()

        self.lprint('checking mount', logfile=logfile, device=device)

        mount = pexpect.spawn('mount',
                            logfile=logfile,
                            echo=False,
                            timeout=5,
                            encoding='utf-8')

        mount_out = mount.expect([r'on {}/{}'.format(self.config['TMP_ROOT_PATH'], device), pexpect.EOF])

        if mount_out == 1:
            self.lexit("could not verify successful mount of /dev/mapper/{} on {}/{}".format(device, self.config['TMP_ROOT_PATH'], device),
                logfile=logfile,
                device=device,
                exitcode=7)

        mount.close()
        return buse

    def destroyRawBackend(self, logfile, device, backend_proc):
        """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

        self.lprint('running umount', logfile=logfile, device=device)

        mount = pexpect.spawn('umount',
                            ['{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()

        if mount.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=21)

        self.lprint('deleting raw file-based backing store {}'.format(backend_proc), logfile=logfile, device=device)

        if not os.path.isfile(backend_proc):
            self.lexit('RAW backend file {} does not exist?!'.format(backend_proc), logfile=logfile, device=device, exitcode=23)

        os.remove(backend_proc)

        if os.path.isfile(backend_proc):
            self.lexit('RAW backend file {} could not be destroyed?!'.format(backend_proc), logfile=logfile, device=device, exitcode=22)

    def destroyRawDmcBackend(self, logfile, device, backend_proc):
        """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

        self.lprint('running umount', logfile=logfile, device=device)

        mount = pexpect.spawn('umount',
                            ['{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()

        if mount.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=20)

        self.lprint('closing dm-crypt LUKS volume', logfile=logfile, device=device)

        setup = pexpect.spawn('cryptsetup',
                            ['close', device],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        setup.expect(pexpect.EOF)

        self.lprint('deleting raw file-based backing store {}'.format(backend_proc), logfile=logfile, device=device)

        if not os.path.isfile(backend_proc):
            self.lexit('RAW backend file {} does not exist?!'.format(backend_proc), logfile=logfile, device=device, exitcode=23)

        os.remove(backend_proc)

        if os.path.isfile(backend_proc):
            self.lexit('RAW backend file {} could not be destroyed?!'.format(backend_proc), logfile=logfile, device=device, exitcode=21)

    def destroyVanillaBackend(self, logfile, device, backend_proc):
        """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

        self.lprint('running umount', logfile=logfile, device=device)

        mount = pexpect.spawn('umount',
                            ['{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()

        if mount.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=21)

        self.lprint('terminating background fs process', logfile=logfile, device=device)

        backend_proc.terminate()

    def destroySbBackend(self, logfile, device, backend_proc):
        """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

        self.lprint('running umount', logfile=logfile, device=device)

        mount = pexpect.spawn('umount',
                            ['{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()

        if mount.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=22)

        self.lprint('terminating background fs process', logfile=logfile, device=device)

        backend_proc.terminate()

    def destroyDmcBackend(self, logfile, device, backend_proc):
        """Destroys the backend, unmounts, deletes files, etc (but does not end proc)"""

        self.lprint('running umount', logfile=logfile, device=device)

        mount = pexpect.spawn('umount',
                            ['{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        mount.expect(pexpect.EOF)
        mount.close()

        if mount.exitstatus != 0:
            self.lexit(logfile=logfile, device=device, exitcode=20)

        self.lprint('closing dm-crypt LUKS volume', logfile=logfile, device=device)

        setup = pexpect.spawn('cryptsetup',
                            ['close', device],
                            logfile=logfile,
                            echo=False,
                            encoding='utf-8')

        setup.expect(pexpect.EOF)

        self.lprint('terminating background fs process', logfile=logfile, device=device)

        backend_proc.terminate()

    def symlinkDataClass(self, logfile, device, data_class):
        """Symlinks the proper data file to be written and read in by experiments"""

        datafile = '{}/data/data{}.random'.format(self.config['REPO_PATH'], data_class)
        symlfile = '{}/data/data.target'.format(self.config['REPO_PATH'])

        self.lprint('setting data target to class {}'.format(data_class), logfile=logfile, device=device)

        if not os.path.exists(datafile):
            self.lexit('data class "{}" does not exist at {}'.format(data_class, datafile),
                logfile=logfile,
                device=device,
                exitcode=25)

        try:
            os.remove(symlfile)
        except FileNotFoundError:
            pass

        os.symlink(datafile, symlfile)

        if not os.path.exists(symlfile):
            self.lexit('os.symlink failed to create {}'.format(symlfile), logfile=logfile, device=device, exitcode=26)

    def sequentialFreerun(self, logfile, device, data_class, test_name):
        """Runs the sequential freerun tests"""

        self.symlinkDataClass(logfile, device, data_class)

        self.lprint('running sequential freerun test target {}'.format(test_name), logfile=logfile, device=device)

        test = pexpect.spawn('{}/bin/sequential-freerun'.format(self.config['REPO_PATH']),
                            ['ram', test_name, '{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            timeout=self.config['FREERUN_TIMEOUT_INT'])

        test_out = test.expect([pexpect.EOF, pexpect.TIMEOUT])
        test.close()

        if test_out == 1:
            self.lexit('sequential-freerun timed out', logfile=logfile, device=device, exitcode=23)

        elif test.exitstatus != 0:
            self.lexit('sequential-freerun returned non-zero error code (-{})'.format(test.exitstatus),
                logfile=logfile,
                device=device,
                exitcode=24)

    def randomFreerun(self, logfile, device, data_class, test_name):
        """Runs the random freerun tests"""

        self.symlinkDataClass(logfile, device, data_class)

        self.lprint('running random freerun test target {}'.format(test_name), logfile=logfile, device=device)

        test = pexpect.spawn('{}/bin/random-freerun'.format(self.config['REPO_PATH']),
                            ['ram', test_name, '{}/{}'.format(self.config['TMP_ROOT_PATH'], device)],
                            timeout=self.config['FREERUN_TIMEOUT_INT'])

        test_out = test.expect([pexpect.EOF, pexpect.TIMEOUT])
        test.close()

        if test_out == 1:
            self.lexit('random-freerun timed out', logfile=logfile, device=device, exitcode=27)

        elif test.exitstatus != 0:
            self.lexit('random-freerun returned non-zero error code (-{})'.format(test.exitstatus),
                logfile=logfile,
                device=device,
                exitcode=28)
