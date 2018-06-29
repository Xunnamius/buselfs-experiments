"""Utility objects for use with the librunner library"""

import time

from collections import namedtuple

STANDARD_WAIT = 30
REDUCED_WAIT = 15
NBD_DEVICE_UPPER_BOUND = 16
DEFAULT_GLOBAL_TIMEOUT = None
KBYTES_IN_A_MB = 1024
BYTES_IN_A_KB = 1024
ESTIMATION_METRIC = 45 / 60
BACKEND_FILE_TEMPLATE = '{}/logfs-{}.bkstr'
DEFAULT_DATA_FILE = '{}/data/data{}.random'
DEFAULT_DATA_SYM = '{}/data/data.target'
SB_EXECUTABLE_FILE = '{}/build/sb'

Configuration = namedtuple('Configuration', ['proto_test_name', 'fs_type', 'mount_args', 'device_args'])
