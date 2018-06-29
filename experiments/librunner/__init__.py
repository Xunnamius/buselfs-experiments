"""This is a base Python package that holds most of the shared test suite code. If you're looking to add new test features, start here."""

import os
import time
import glob
import pexpect

from subprocess import Popen
from datetime import datetime
from librunner.exception import CommandExecutionError, TaskError, ExperimentError
from librunner.util import (
    STANDARD_WAIT,
    REDUCED_WAIT,
    NBD_DEVICE_UPPER_BOUND,
    DEFAULT_GLOBAL_TIMEOUT,
    KBYTES_IN_A_MB,
    BYTES_IN_A_KB,
    BACKEND_FILE_TEMPLATE,
    DEFAULT_DATA_FILE,
    DEFAULT_DATA_SYM,
    SB_EXECUTABLE_FILE
)

# TODO: replace timeout mechanic with retry mechanic; all timeout params set to None!
# TODO: later: re-implement experiments as strategy pattern instances
# TODO: later: try to exit normally, then try to kill the sb process via sudo kill -9, then quarantine and move along
# TODO: if quarantined by the end, recommend breaking the glass (super shutdown)
class Librunner():
    """This class is responsible for running and managing experiments in an automated fashion"""

    def __init__(self, config={}):
        self.config = config
        self._logFile = None
        self.timeout = DEFAULT_GLOBAL_TIMEOUT
        self._backendSizeBytes = config['BACKEND_SIZE_INT'] * KBYTES_IN_A_MB * BYTES_IN_A_KB
        self._backendFilePath = BACKEND_FILE_TEMPLATE.format(config['RAM0_PATH'], '{}')
        self.verbose = config['verbose'] if 'verbose' in config else True
        self._deviceList = list(range(NBD_DEVICE_UPPER_BOUND))
        self._quarantinedDeviceList = []
        self._lingeringBackgroundProcess = None

        self._deviceList.reverse()

    # *
    # * Properties
    # *

    @property
    def deviceList(self):
        """Returns a list of non-quarantined nbd device numbers"""

        return list(self._deviceList)
    
    @property
    def quarantinedDeviceList(self):
        """Returns a list of quarantined nbd device numbers"""

        return list(self._quarantinedDeviceList)
    
    @property
    def currentDeviceNumber(self):
        """Returns the number of the currently active nbd device"""

        return self._deviceList[-1]
    
    @property
    def currentDeviceName(self):
        """Returns the file name version of self.currentDeviceNumber"""

        return 'nbd{}'.format(self.currentDeviceNumber)
    
    @property
    def currentDeviceDevPath(self):
        """Returns a path to the current nbd device in /dev"""

        return '/dev/{}'.format(self.currentDeviceName)
    
    @property
    def currentDeviceTmpPath(self):
        """Returns the path to the current device's corresponding tmp folder"""

        return '{}/{}'.format(self.config['TMP_ROOT_PATH'], self.currentDeviceName)
    
    @property
    def currentDeviceMapperPath(self):
        """Returns the path to the current device's corresponding tmp folder"""

        return '/dev/mapper/{}'.format(self.currentDeviceName)
    
    @property
    def backendSizeBytes(self):
        """Returns the size in bytes of the backstore (aka: backend) file """

        return self._backendSizeBytes
    
    @property
    def logFile(self):
        """Returns the internal file object representing the logging file"""

        return self._logFile
    
    @logFile.setter
    def logFile(self, logFile):
        """Sets the internal file object to a user-defined value"""

        if logFile:
            self.print('logging file set to {}'.format(logFile.name))
        else:
            self.print('logging file unset')

        self._logFile = logFile
    
    # ! internal
    @property
    def backendFilePath(self):
        """Returns the correct backend file path given the current device"""

        return self._backendFilePath.format(self.currentDeviceName)

    # *
    # * State
    # *

    def quarantineDevice(self, device):
        """Quarantine a device via its device number"""

        self.print('quarantining nbd device {}!'.format(device), severity='WARN')

        self._deviceList.remove(device)
        self._quarantinedDeviceList.append(device)
    
    def useNextDevice(self):
        """Advances internal state so that the next nbd device becomes the
           current device.
        """

        if len(self._deviceList) == 0:
            raise RuntimeError('_deviceList is empty (all devices quarantined?)')

        self._deviceList = [self._deviceList.pop()] + self._deviceList
        self.print('device set to {}'.format(self.currentDeviceName))

    # *
    # * Utilities
    # *

    def print(self, *args, severity='INFO'):
        """Specialized print method that includes datetime, severity, and other
           info; also simultaneously outputs to log files
        """

        timestamp = '{0:%B} {0:%d} at {0:%I:%M:%S%p} {0:%f}'.format(datetime.now())
        preamble = '[{} | {}:{}]: '.format(timestamp, severity, self.currentDeviceName)

        if self.verbose:
            print(preamble.expandtabs(self.config['EXPAND_TABS_INT']), *args, flush=True)

        if self.logFile:
            fileno = self.logFile.fileno()

            os.fsync(fileno)
            print(preamble.expandtabs(0), *args, file=self.logFile)
            self.logFile.flush()
            os.fsync(fileno)

    def dropPageCache(self):
        """Drop the linux page cache programmatically"""

        self.print('dropping the page cache')

        with open(self.config['DROP_CACHE_PATH'], 'w') as cache:
            cache.write('1\n')

    def sleep(self, seconds):
        """Pause for a little bit (typically a courtesy period)"""

        self.print('idling for {} seconds...'.format(seconds))
        time.sleep(seconds)

    def clearBackstoreFiles(self):
        """Removes all RAM0_PATH/* files"""

        self.print('clearing backstore files')

        files = glob.glob('{}/*'.format(self.config['RAM0_PATH']))
        for f in files:
            os.remove(f)
    
    def symlinkDataClass(self, data_class):
        """Symlinks the proper data file to be written and read in by
           experiments
        """

        datafile = DEFAULT_DATA_FILE.format(self.config['REPO_PATH'], data_class)
        symlfile = DEFAULT_DATA_SYM.format(self.config['REPO_PATH'])

        self.print('setting data target to class {}'.format(data_class))

        if not os.path.exists(datafile):
            raise TaskError('data class "{}" does not exist at {}'.format(data_class, datafile))

        try:
            os.remove(symlfile)

        except FileNotFoundError:
            pass

        os.symlink(datafile, symlfile)

        if not os.path.exists(symlfile):
            raise TaskError('os.symlink failed to create {}'.format(symlfile))
    
    def checkSanity(self):
        """Bails out of the program if the environment isn't set up properly"""

        self.print('performing sanity checks...')
        
        if not os.path.exists(self.config['RAM0_PATH']):
            raise TaskError("did initrunner.py fail?! (can't find {})".format(self.config['RAM0_PATH']))

        if not os.path.exists('/dev/nbd0'):
            raise TaskError("did initrunner.py fail to modprobe nbd?! (can't find /dev/nbd0)")

        # ! Don't forget to check for any other experiments that are added later!
        # TODO: strategy pattern will solve this...
        if not os.path.exists('{}/bin/sequential-freerun'.format(self.config['REPO_PATH'])) \
        or not os.path.exists('{}/bin/random-freerun'.format(self.config['REPO_PATH'])):
            raise TaskError("did you forget to run `make` in this repository?")

        if not os.path.exists('{}/build/sb'.format(self.config['BUSELFS_PATH'])):
            raise TaskError('did you forget to run `make` in {}?'.format(self.config['BUSELFS_PATH']))

        if not os.path.exists(self.config['BUSE_PATH']):
            raise TaskError('did you forget to run `make buselogfs` in the BUSE repository? (looking for {})'.format(self.config['BUSE_PATH']))

        if os.getcwd() != os.path.abspath(self.config['RAM0_PATH']):
            raise TaskError('current working directory is incorrect (should be {})'.format(self.config['RAM0_PATH']))
        
        # TODO: add checks for existing sb processes and check if nbd device already mounted
    
    def createScratchFile(self, filepath=None, filesize=None):
        """Takes a filepath and filesize and creates a scratch file of that
           size
        """

        filepath = filepath or self.backendFilePath
        filesize = filesize or self.backendSizeBytes

        self.print('creating scratch file of ({} bytes) at {}...'.format(filesize, filepath))

        with open(filepath, 'wb') as f:
            f.seek(filesize - 1)
            f.write(b'\0')
        
        fsize = os.path.getsize(filepath)

        if fsize != filesize:
            raise TaskError('file creation failed (unexpected size returned: {} (expected) != {})'.format(fsize, filesize))

    # *
    # * CLI Wrappers (Commands)
    # * -----------------------
    # * Note that all CLI wrappers implement their own self-check and retry code
    # *

    def _shell_saw(self, executable, args):
        self.print('<shell saw: `{}`>'.format('{}{}'.format(executable, ' ' + ' '.join(str(a) for a in args) if len(args) else '')))

    def _spawn_actual(self, executable, args, spawn_expect=None, timeout=None):
        self._shell_saw(executable, args)

        if timeout:
            timeout = int(timeout)
            self.print(
                'the next command will be terminated by force if it does not complete in {} seconds'.format(timeout),
                severity='WARN'
            )
        else:
            timeout = self.timeout

        time.sleep(1)
        proc = pexpect.spawn(executable, args, logfile=self.logFile, echo=False, timeout=timeout, encoding='utf-8')

        if not spawn_expect:
            proc.expect(pexpect.EOF)
            proc.close()

            if proc.exitstatus != 0:
                raise CommandExecutionError('process {} exited abnormally ({})'.format(executable, proc.exitstatus), proc.exitstatus)

        else:
            spawn_expect(executable, args, proc)

        return proc
    
    def _spawn(self, executable, args, runMessage=None, verifyMessage=None, spawn_expect=None):
        checkFn = getattr(self, '_check_{}'.format(executable))

        self.print((runMessage or 'running {}').format(executable))

        proc = self._spawn_actual(executable, args)

        self.print((verifyMessage or 'verifying {} completed successfully').format(executable))

        checkFn(executable, args, proc)

        return proc

    def _mkfs(self, args):
        return self._spawn('mkfs', args)
    
    def _mount(self, args):
        return self._spawn('mount', args)

    def _umount(self, args):
        return self._spawn('umount', args)

    def _cryptsetup_init(self, args):
        def spawn_expect(executable, args, proc):
            try:
                proc.expect(r'\(Type uppercase yes\): ')
                proc.sendline('YES')
                proc.expect('Enter passphrase: ')
                proc.sendline('t')
                proc.expect('Verify passphrase: ')
                proc.sendline('t')
                proc.expect('Command successful.')

            except pexpect.EOF:
                raise TaskError('process {} failed (returned unexpected output)'.format(executable))

        return self._spawn('cryptsetup', args, spawn_expect=spawn_expect)
    
    def _cryptsetup_open(self, args):
        def spawn_expect(executable, args, proc):
            try:
                proc.expect('Enter passphrase for {}: '.format(self.backendFilePath))
                proc.sendline('t')
                proc.expect(pexpect.EOF)

            except pexpect.EOF:
                raise TaskError('process {} failed (returned unexpected output)'.format(executable))

        return self._spawn('cryptsetup', args, runMessage='opening dm-crypt LUKS volume', spawn_expect=spawn_expect)

    def _cryptsetup_close(self, args=None):
        args = args or []
        return self._spawn('cryptsetup', ['close', self.currentDeviceName] + args, runMessage='closing dm-crypt LUKS volume')

    def _cp(self, args):
        return self._spawn('cp', args)

    def _check_mkfs(self, executable, args, proc):
        # ? A good exit code will do just nicely
        pass
    
    def _check_mount(self, executable, args, proc):
        def spawn_expect(executable, args, proc):
            try:
                proc.expect(r'on {}'.format(self.currentDeviceTmpPath))

            except pexpect.EOF:
                raise TaskError('could not verify successful mount onto {}'.format(self.currentDeviceTmpPath))

        self._spawn_actual('mount', [], spawn_expect=spawn_expect)

    def _check_umount(self, executable, args, proc):
        def spawn_expect(executable, args, proc):
            try:
                proc.expect(r'on {}'.format(self.currentDeviceTmpPath))
                raise TaskError('could not verify successful umount from {}'.format(self.currentDeviceTmpPath))

            except pexpect.EOF:
                pass # ? Success!

        self._spawn_actual('mount', [], spawn_expect=spawn_expect)

    def _check_cryptsetup(self, executable, args, proc):
        # ? A good exit code will do just nicely
        pass

    def _check_cp(self, executable, args, proc):
        # ? A good exit code will do just nicely
        pass

    # *
    # * Backends (Creation)
    # *

    def createRawBackend(self, fs_type, mount_args=None, device_args=None):
        """Creates a non-BUSE raw drive-backed backend. Does not advance current
           device.
        """

        self.useNextDevice()

        mount_args = mount_args or []
        device_args = device_args or []

        self.print('creating RAW backend ({} @ {})'.format(self.backendFilePath, self.currentDeviceTmpPath))

        self.createScratchFile()
        self._mkfs(['-t', fs_type, self.backendFilePath])
        self._mount(mount_args + ['-t', fs_type, self.backendFilePath, self.currentDeviceTmpPath, '-o', 'loop'])

    def createRawDmcBackend(self, fs_type, mount_args=None, device_args=None):
        """Creates a non-BUSE raw drive-backed dm-crypt backend and returns the
           path. Also advances the current device!"""

        self.useNextDevice()

        mount_args = mount_args or []
        device_args = device_args or []

        self.print('creating RAW dm-crypt LUKS volume backend ({} @ {})'.format(self.backendFilePath, self.currentDeviceTmpPath))

        self.createScratchFile()

        self._cryptsetup_init([
            '--verbose', '--cipher', 'aes-xts-plain64', '--key-size', '512', '--hash', 'sha512',
            '--iter-time', '5000', '--use-urandom'] + device_args + ['luksFormat', self.backendFilePath])

        self._cryptsetup_open(['open', '--type', 'luks', self.backendFilePath, self.currentDeviceName])
        self._mkfs(['-t', fs_type, self.currentDeviceMapperPath])
        self._mount(mount_args + ['-t', fs_type, self.currentDeviceMapperPath, self.currentDeviceTmpPath, '-o', 'loop'])

    def createVanillaBackend(self, fs_type, mount_args=None, device_args=None):
        """Creates a buselogfs backend and returns the path"""

        assert self._lingeringBackgroundProcess == None

        self.useNextDevice()

        mount_args = mount_args or []
        device_args = device_args or []

        args = ['--size', str(self.backendSizeBytes), self.currentDeviceDevPath] + device_args
        
        self.print('creating vanilla backend (@ {})'.format(self.currentDeviceTmpPath))
        self._shell_saw(self.config['BUSE_PATH'], args)

        buse = Popen([self.config['BUSE_PATH']] + args, stdout=self.logFile, stderr=self.logFile)

        self.sleep(5)

        bpoll = buse.poll()

        if bpoll is not None:
            CommandExecutionError('the buselogfs process does not appear to have survived ({})'.format(bpoll), bpoll)

        self._mkfs(['-t', fs_type, self.currentDeviceDevPath])
        self._mount(mount_args + ['-t', fs_type, self.currentDeviceDevPath, self.currentDeviceTmpPath])

        self._lingeringBackgroundProcess = buse

    def createSbBackend(self, fs_type, mount_args=None, device_args=None):
        """Creates a StrongBox backend"""

        assert self._lingeringBackgroundProcess == None

        self.useNextDevice()

        mount_args = mount_args or []
        device_args = device_args or []
        executable = SB_EXECUTABLE_FILE.format(self.config['BUSELFS_PATH'])

        args = [
            '--backstore-size',
            str(self.config['BACKEND_SIZE_INT']),
            '--default-password'
        ] + device_args + ['create', self.currentDeviceName]

        self.print('creating StrongBox backend ({} @ {})'.format(self.backendFilePath, self.currentDeviceTmpPath))
        self._shell_saw(executable, args)

        buse = Popen([executable] + args, stdout=self.logFile, stderr=self.logFile)
        waittimes = [STANDARD_WAIT, REDUCED_WAIT]

        while True:
            self.sleep(waittimes[0])
            waittimes.reverse()

            bpoll = buse.poll()

            if bpoll is not None:
                raise CommandExecutionError('the StrongBox process does not appear to have survived (exit code {})'.format(bpoll), bpoll)

            try:
                self._mkfs(['-t', fs_type, self.currentDeviceDevPath])
                self.print('mkfs succeeded!', severity='OK')
                break
            
            except CommandExecutionError as e:
                if int(e.exitcode) >= 255:
                    self.print('failed to create backend: system is likely in an unstable state (try calling `sync`). Please reboot!', severity='FATAL')
                    raise TaskError('failed to create backend due to system instability')

                else:
                    self.print(e.message, severity='WARN')

        self._mount(mount_args + ['-t', fs_type, self.currentDeviceDevPath, self.currentDeviceTmpPath])

        self._lingeringBackgroundProcess = buse

    def createDmcBackend(self, fs_type, mount_args=None, device_args=None):
        """Creates a dm-crypt + AES-XTS backend and returns the path"""

        assert self._lingeringBackgroundProcess == None

        self.useNextDevice()

        mount_args = mount_args or []
        buse_args = ['--size', str(self.backendSizeBytes), self.currentDeviceDevPath]

        self.print('creating dm-crypt LUKS volume buselogfs backend ({} @ {})'.format(self.backendFilePath, self.currentDeviceTmpPath))
        self._shell_saw(self.config['BUSE_PATH'], buse_args)

        buse = Popen([self.config['BUSE_PATH']] + buse_args, stdout=self.logFile, stderr=self.logFile)

        self.sleep(5)

        bpoll = buse.poll()

        if bpoll is not None:
            CommandExecutionError('the buselogfs process does not appear to have survived ({})'.format(bpoll), bpoll)

        self._cryptsetup_init(['--verbose', '--cipher', 'aes-xts-plain64', '--key-size', '512', '--hash', 'sha512',
                               '--iter-time', '5000', '--use-urandom'] + device_args + ['luksFormat', self.currentDeviceDevPath])

        self._cryptsetup_open(['open', '--type', 'luks', self.currentDeviceDevPath, self.currentDeviceName])
        self._mkfs(['-t', fs_type, self.currentDeviceMapperPath])
        self._mount(mount_args + ['-t', fs_type, self.currentDeviceMapperPath, self.currentDeviceTmpPath])

        self._lingeringBackgroundProcess = buse

    # *
    # * Backends (Destruction)
    # *

    def _terminateLingeringProcesses(self):
        self.print('terminating background fs process')
        
        self._lingeringBackgroundProcess.terminate()
        self._lingeringBackgroundProcess = None

    def destroyRawBackend(self):
        """Unmounts, deletes files, terminates proc but does not delete files in
           RAM0_PATH!
        """

        self._umount([self.currentDeviceTmpPath])

    def destroyRawDmcBackend(self):
        """Unmounts, deletes files, terminates proc but does not delete files in
           RAM0_PATH!
        """

        self._umount([self.currentDeviceTmpPath])
        self._cryptsetup_close()

    def destroyVanillaBackend(self):
        """Unmounts, deletes files, terminates proc but does not delete files in
           RAM0_PATH!
        """

        self._umount([self.currentDeviceTmpPath])
        self._terminateLingeringProcesses()

    def destroySbBackend(self):
        """Unmounts, deletes files, terminates proc but does not delete files in
           RAM0_PATH!
        """

        self._umount([self.currentDeviceTmpPath])
        self._terminateLingeringProcesses()

    def destroyDmcBackend(self):
        """Unmounts, deletes files, terminates proc but does not delete files in
           RAM0_PATH!
        """

        self._umount([self.currentDeviceTmpPath])
        self._cryptsetup_close()
        self._terminateLingeringProcesses()

    # *
    # * Experiments
    # *

    def sequentialFreerun(self, data_class, test_name):
        """Runs the sequential freerun tests"""

        self.symlinkDataClass(data_class)

        self.print('running sequential freerun test target {}'.format(test_name))

        try:
            return self._spawn_actual(
                '{}/bin/sequential-freerun'.format(self.config['REPO_PATH']),
                ['ram', test_name, self.currentDeviceTmpPath],
                timeout=self.config['FREERUN_TIMEOUT_INT']
            )
        
        except pexpect.TIMEOUT:
            raise ExperimentError('experiment timed out (exceeded {} seconds'.format(self.config['FREERUN_TIMEOUT_INT']))

    def randomFreerun(self, data_class, test_name):
        """Runs the random freerun tests"""

        self.symlinkDataClass(data_class)

        self.print('running random freerun test target {}'.format(test_name))

        try:
            return self._spawn_actual(
                '{}/bin/random-freerun'.format(self.config['REPO_PATH']),
                ['ram', test_name, self.currentDeviceTmpPath],
                timeout=self.config['FREERUN_TIMEOUT_INT']
            )
        
        except pexpect.TIMEOUT:
            raise ExperimentError('experiment timed out (exceeded {} seconds'.format(self.config['FREERUN_TIMEOUT_INT']))
