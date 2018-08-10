"""Utility objects for use with the librunner library"""

import sys
import time
import contextlib

from tqdm import tqdm
from collections import namedtuple

STANDARD_WAIT = 30
REDUCED_WAIT = 15
NBD_DEVICE_UPPER_BOUND = 16
DEFAULT_GLOBAL_TIMEOUT = None
KBYTES_IN_A_MB = 1024
BYTES_IN_A_KB = 1024
BACKEND_FILE_TEMPLATE = '{}/logfs-{}.bkstr'
DEFAULT_DATA_FILE = '{}/data/data{}.random'
DEFAULT_DATA_SYM = '{}/data/data.target'
SB_EXECUTABLE_FILE = '{}/build/sb'
RESULTS_FILE_NAME = '{}.ram.{}.results'
RESULTS_PATH = '{}/results/{}'

Configuration = namedtuple('Configuration', ['proto_test_name', 'fs_type', 'mount_args', 'device_args'])

class DummyTqdmFile():
    """Dummy file-like object that will write to the tqdm progress bar"""

    fd = None
    accumulator = ''

    def __init__(self, fd):
        self.fd = fd

    def write(self, string):
        # Avoid print() second call (useless \n)
        if len(string.rstrip()) > 0:
            if not string.endswith(' '):
                tqdm.write('{}{}'.format(self.accumulator, string), file=self.fd)
                self.accumulator = ''
            
            else:
                self.accumulator += string

    def flush(self):
        return getattr(self.fd, "flush", lambda: None)()

@contextlib.contextmanager
def outputProgressBarRedirection():
    originalOutputFiles = sys.stdout, sys.stderr

    try:
        sys.stdout, sys.stderr = map(DummyTqdmFile, originalOutputFiles)

        for fd in originalOutputFiles:
            yield fd

    except Exception as exc:
        raise exc
    
    finally:
        sys.stdout, sys.stderr = originalOutputFiles

def printInstabilityWarning(lib, config):
    lib.print('THE SYSTEM IS VERY LIKELY IN AN UNSTABLE STATE!', severity='CRITICAL')
    lib.print('1. `umount` any mounted NBD/mapper devices', severity='CRITICAL')
    lib.print('2. `fprocs` and `kill -9` any experimental backend processes', severity='CRITICAL')
    lib.print('3. `sudo rm {}/*`'.format(config['RAM0_PATH']), severity='CRITICAL')
    lib.print('4. call `sync`', severity='CRITICAL')
