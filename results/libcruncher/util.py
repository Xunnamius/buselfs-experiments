"""Utility objects for use with the libcruncher library"""

from collections import namedtuple

# 0 = least secure, 3 = most secure
SC_SECURITY_RANKING = {
    'sc_chacha8_neon': 0,
    'sc_chacha12_neon': 1,
    'sc_chacha20_neon': 2,
    'sc_chacha20': 2,
    'sc_salsa8': 0,
    'sc_salsa12': 1,
    'sc_salsa20': 2,
    'sc_aes128_ctr': 1,
    'sc_aes256_ctr': 2,
    'sc_hc128': 2,
    'sc_rabbit': 1,
    'sc_sosemanuk': 1,
    'sc_freestyle_fast': 1,
    'sc_freestyle_balanced': 2,
    'sc_freestyle_secure': 3,
    'sc_aes256_xts': 2,
}

DEFAULT_CIPHER_IDENT = 'sc_chacha20'
DEFAULT_FLAKESIZE = 4096
DEFAULT_FPN = 64

COLORS_A = ['rgb(49,130,189)', 'rgb(204,204,204)', 'rgb(255,102,0)']
COLORS_B = ['rgb(25,65,95)', 'rgb(102,102,102)', 'rgb(255,102,0)']

ResultProperties = namedtuple('ResultProperties', ['path', 'name', 'order', 'medium', 'iops', 'backstore', 'fs', 'cipher', 'flakesize', 'fpn', 'baseline'])

ResultProperty = namedtuple('ResultProperty', ['name', 'value'])

ExecutionProperties = namedtuple('ExecutionProperties', ['resultFiles', 'observeBaseline', 'filterProps', 'filterStrict'])
