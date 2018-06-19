#!/usr/bin/env python3

"""Formerly known as the 'new age' initializing bash commands, this python
script is responsible for ensuring the system is ready to run experiments"""

import os
import sys
import pprint
import pexpect

# ! All of these dirs will be prefixed with CONFIG['TMP_ROOT_PATH']
MODPROBE_DIRS = ['/nbd0', '/nbd1', '/nbd2', '/nbd3', '/nbd4', '/nbd5', '/nbd6', '/nbd7', '/nbd8', '/nbd9', '/nbd10', '/nbd11', '/nbd12', '/nbd13', '/nbd14', '/nbd15', '/config', '/run'] # + [CONFIG['RAM0_PATH']]

CONFIG_PATH = "{}/config/vars.mk".format(os.path.dirname(os.path.realpath(__file__)))
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

    return CONFIG

def checkMount():
    mount = pexpect.spawn('mount',
                         echo=False,
                         timeout=5,
                         encoding='utf-8')

    expecting = mount.expect([r'on {}'.format(CONFIG['RAM0_PATH']), pexpect.EOF])
    mount.close()

    return expecting

def initialize():
    """Idempotent initialization of the experimental testbed."""

    # 1 => not found
    if checkMount() == 1:
        print('(ramdisk not found, executing initialization procedure...)')

        for mod in ('nbd', 'logfs', 'nilfs', 'f2fs'):
            modprobe = pexpect.spawn('modprobe', ['nbd'], timeout=5, encoding='utf-8')
            modprobe.expect(pexpect.EOF)
            modprobe.close()

            if modprobe.exitstatus != 0:
                print('modprobe {} returned non-zero error code (-{})'.format(mod, modprobe.exitstatus))
                sys.exit(2)
        
        mkdir = pexpect.spawn('mkdir',
            ['{}/{}'.format(CONFIG['TMP_ROOT_PATH'], dirr) for dirr in MODPROBE_DIRS] + [CONFIG['RAM0_PATH']],
            timeout=5,
            encoding='utf-8'
        )
        
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

        mount.expect(pexpect.EOF)
        mount.close()

        if checkMount() == 1:
            print('Could not verify successful initialization mount on {}'.format(CONFIG['RAM0_PATH']))
            sys.exit(5)

        if mount.exitstatus != 0:
            print('Could not verify successful initialization mount on {} (bad exit status {})'.format(CONFIG['RAM0_PATH'], mount.exitstatus))
            sys.exit(6)
    else:
        print('(found ramdisk, initialization procedure skipped!)')

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        print('must be root/sudo')
        sys.exit(1)

    CONFIG = parseConfigVars()

    pprint.PrettyPrinter(indent=4).pprint(CONFIG)
    print()

    initialize()

    print("Testbed manual initialization successful.")
