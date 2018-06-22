#!/usr/bin/env python3

"""Formerly known as the 'new age' initializing bash commands, this python
script is responsible for ensuring the system is ready to run experiments"""

import os
import sys
import pprint
import pexpect
import argparse

# ! All of these are dirs that will be prefixed with CONFIG['TMP_ROOT_PATH']/
MODPROBE_DIRS = ['nbd0',
                 'nbd1',
                 'nbd2',
                 'nbd3',
                 'nbd4',
                 'nbd5',
                 'nbd6',
                 'nbd7',
                 'nbd8',
                 'nbd9',
                 'nbd10',
                 'nbd11',
                 'nbd12',
                 'nbd13',
                 'nbd14',
                 'nbd15',
                 'config',
                 'run'
] # + [CONFIG['RAM0_PATH']]

CONFIG_PATH = "{}/../config/vars.mk".format(os.path.dirname(os.path.realpath(__file__)))
CONFIG_KEY = "CONFIG_COMPILE_FLAGS"
RAMDISK_SIZE = "1024M"

CONFIG = {}

################################################################################

def parseConfigLine(configLine):
    lhs_rhs = ''.join(configLine.split(' \\')[0].split('-D')[1:]).split('=')
    rhs = ''.join(lhs_rhs[1:]).strip('"\' ')
    lhs = lhs_rhs[0].strip(' ')
    
    return (lhs, rhs)

def parseConfigVars():
    try:
        with open(CONFIG_PATH, 'r') as varsFile:
            inConfigVar = False

            for line in varsFile:
                if line.startswith(CONFIG_KEY):
                    inConfigVar = True
                    continue
                
                if inConfigVar:
                    line = line.strip('\n')
                    if not line.endswith("\\"):
                        inConfigVar = False
                    
                    (varName, varValue) = parseConfigLine(line)
                    CONFIG[varName] = int(varValue) if varName.endswith('_INT') else varValue

    except FileNotFoundError:
        raise FileNotFoundError('vars.mk not found')

    return CONFIG

def checkMount():
    mount = pexpect.spawn('mount',
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    expecting = mount.expect([r'on {}'.format(CONFIG['RAM0_PATH']), pexpect.EOF])
    mount.close()

    return expecting

def initialize(verbose=False, force=False):
    """Idempotent initialization of the experimental testbed."""

    # 1 => not found
    if force or checkMount() == 1:
        print('(mounted ramdisk not found or re-initialization forced; executing initialization procedure...)')

        for mod in ('nbd', 'nilfs2', 'f2fs'): #('nbd', 'nilfs2', 'f2fs'):
            modprobe = pexpect.spawn('modprobe', [mod], timeout=5, encoding='utf-8')

            modprobe.logfile = sys.stdout if verbose else None
            modprobe.expect(pexpect.EOF)
            modprobe.close()

            if modprobe.exitstatus != 0:
                print('modprobe {} returned non-zero error code (-{})'.format(mod, modprobe.exitstatus))
                sys.exit(2)
        
        mkdir = pexpect.spawn('mkdir',
            ['-p'] + ['{}/{}'.format(CONFIG['TMP_ROOT_PATH'], dirr) for dirr in MODPROBE_DIRS] + [CONFIG['RAM0_PATH']],
            timeout=5,
            encoding='utf-8'
        )

        mkdir.logfile = sys.stdout if verbose else None
        mkdir.expect(pexpect.EOF)
        mkdir.close()

        if mkdir.exitstatus != 0:
            print('mkdir returned non-zero error code (-{})'.format(mkdir.exitstatus))
            sys.exit(3)
        
        cp = pexpect.spawn('cp',
            ['{}/config/zlog_conf.conf'.format(CONFIG['BUSELFS_PATH']), '{}/config/'.format(CONFIG['TMP_ROOT_PATH'])],
            timeout=5,
            encoding='utf-8'
        )

        cp.logfile = sys.stdout if verbose else None
        cp.expect(pexpect.EOF)
        cp.close()

        if cp.exitstatus != 0:
            print('cp returned non-zero error code (-{})'.format(cp.exitstatus))
            sys.exit(4)

        mount = pexpect.spawn('mount',
            ['-t', 'tmpfs', '-o', 'size={}'.format(RAMDISK_SIZE), 'tmpfs', CONFIG['RAM0_PATH']],
            echo=False,
            timeout=5,
            encoding='utf-8'
        )

        mount.logfile = sys.stdout if verbose else None
        mount.expect(pexpect.EOF)
        mount.close()

        if checkMount() == 1:
            print('Could not verify successful initialization mount on {}'.format(CONFIG['RAM0_PATH']))
            sys.exit(5)

        if mount.exitstatus != 0:
            print('Could not verify successful initialization mount on {} (bad exit status {})'.format(CONFIG['RAM0_PATH'], mount.exitstatus))
            sys.exit(6)
    else:
        print('(found mounted ramdisk, initialization procedure skipped! Use --force to force re-initialization)')

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        print('must be root/sudo')
        sys.exit(1)

    if not parseConfigVars():
        raise ValueError('')

    pprint.PrettyPrinter(indent=4).pprint(CONFIG)
    print()

    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    options = parser.parse_args()

    initialize(verbose=True, force=options.force)

    print("Testbed manual initialization successful.")