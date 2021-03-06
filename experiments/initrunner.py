#!/usr/bin/env python3

"""Formerly known as the 'new age' initializing bash commands, this python
script is responsible for ensuring the system is ready to run experiments"""

# TODO: create a script (perhaps exitrunner.py) that will clean up any mess left
# TODO: over from running any of the testrunner-X.py scripts

import os
import sys
import json
import pexpect
import argparse

# ! All of these are dirs that will be prefixed with vars.mk['TMP_ROOT_PATH']/
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
] #*             vars.mk['RAM0_PATH']
  #*             '../config'

# ? Config parameters
CONFIG_PATH = "{}/../config/vars.mk".format(os.path.dirname(os.path.realpath(__file__)))
CONFIG_KEY = "CONFIG_COMPILE_FLAGS"

# ? Amount of time to wait before we consider a command as failed
STANDARD_TIMEOUT=10

################################################################################

def parseConfigLine(configLine):
    """Parses a single configuration line and returns lhs and rhs values"""

    lhs_rhs = ''.join(configLine.split(' \\')[0].split('-D')[1:]).split('=')
    rhs = ''.join(lhs_rhs[1:]).strip('"\' ')
    lhs = lhs_rhs[0].strip(' ')

    return (lhs, rhs)

def parseConfigVars():
    """Opens and parses config/vars.mk, returning a config object"""

    config = {}

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
                    config[varName] = int(varValue) if varName.endswith('_INT') else varValue

    except FileNotFoundError:
        raise FileNotFoundError('{} not found'.format(CONFIG_PATH))

    return config

def checkMount(config, verbose=False):
    """Ensure mount operation succeeded"""

    mount = pexpect.spawn('mount',
                         echo=True if verbose else False,
                         timeout=STANDARD_TIMEOUT,
                         encoding='utf-8')

    expecting = mount.expect([r'on {}'.format(config['RAM0_PATH']), pexpect.EOF])
    mount.close()

    return expecting

def cwdToRAMDir(config):
    """Change the current working directory to the configured ramdisk path"""

    os.chdir(config['RAM0_PATH'])

def initialize(config, verbose=False, force=False):
    """Idempotent initialization of the experimental testbed."""

    # 1 => not found
    if force or checkMount(config, verbose) == 1:
        print('(mounted ramdisk not found or re-initialization forced; executing primary initialization...)')

        for mod in ('nbd', 'nilfs2', 'f2fs'):
            modprobe = pexpect.spawn('modprobe', [mod], timeout=STANDARD_TIMEOUT, encoding='utf-8')

            modprobe.logfile = sys.stdout if verbose else None
            modprobe.expect(pexpect.EOF)
            modprobe.close()

            if modprobe.exitstatus != 0:
                print('WARN: modprobe {} returned non-zero error code ({})'.format(mod, modprobe.exitstatus))

                # if verbose:
                #     print('(the above error was ignored because verbose=True)')

                # else:
                #     sys.exit(2)

        # rmmod_brd = pexpect.spawn('rmmod', ['brd'], timeout=STANDARD_TIMEOUT, encoding='utf-8')

        # rmmod_brd.logfile = sys.stdout if verbose else None
        # rmmod_brd.expect(pexpect.EOF)
        # rmmod_brd.close()

        # if rmmod_brd.exitstatus != 0:
        #     print('WARN: rmmod brd returned non-zero error code ({})'.format(rmmod_brd.exitstatus))

        # modprobe_brd = pexpect.spawn(
        #     'modprobe',
        #     ['brd', 'rd_nr=1', 'rd_size={}'.format(config['RAMDEVICE_SIZE_KILOBYTES']), 'max_part=1'],
        #     timeout=STANDARD_TIMEOUT,
        #     encoding='utf-8'
        # )

        # modprobe_brd.logfile = sys.stdout if verbose else None
        # modprobe_brd.expect(pexpect.EOF)
        # modprobe_brd.close()

        # if modprobe_brd.exitstatus != 0:
        #     print('FATAL: modprobe brd returned non-zero error code ({})'.format(modprobe_brd.exitstatus))
        #     sys.exit(2)

        mkdir = pexpect.spawn('mkdir',
            ['-p']
                + ['{}/{}'.format(config['TMP_ROOT_PATH'], dirr) for dirr in MODPROBE_DIRS]
                + [config['RAM0_PATH'], '../config'],
            timeout=STANDARD_TIMEOUT,
            encoding='utf-8'
        )

        mkdir.logfile = sys.stdout if verbose else None
        mkdir.expect(pexpect.EOF)
        mkdir.close()

        if mkdir.exitstatus != 0:
            print('FATAL: mkdir returned non-zero error code ({})'.format(mkdir.exitstatus))
            sys.exit(3)

        cp = pexpect.spawn('cp',
            ['{}/config/zlog_conf.conf'.format(config['BUSELFS_PATH']), '{}/config/'.format(config['TMP_ROOT_PATH'])],
            timeout=STANDARD_TIMEOUT,
            encoding='utf-8'
        )

        cp.logfile = sys.stdout if verbose else None
        cp.expect(pexpect.EOF)
        cp.close()

        if cp.exitstatus != 0:
            print('FATAL: cp returned non-zero error code ({})'.format(cp.exitstatus))
            sys.exit(4)

        cp2 = pexpect.spawn('cp',
            ['{}/config/zlog_conf.conf'.format(config['BUSELFS_PATH']), '../config/'],
            timeout=STANDARD_TIMEOUT,
            encoding='utf-8'
        )

        cp2.logfile = sys.stdout if verbose else None
        cp2.expect(pexpect.EOF)
        cp2.close()

        if cp2.exitstatus != 0:
            print('FATAL: cp returned non-zero error code ({})'.format(cp2.exitstatus))
            sys.exit(42)

        mount = pexpect.spawn('mount',
            ['-t', 'tmpfs', '-o', 'size={}'.format(config['RAMDISK_SIZE']), 'tmpfs', config['RAM0_PATH']],
            echo=True if verbose else False,
            timeout=STANDARD_TIMEOUT,
            encoding='utf-8'
        )

        mount.logfile = sys.stdout if verbose else None
        mount.expect(pexpect.EOF)
        mount.close()

        if checkMount(config, verbose) == 1:
            print('FATAL: could not verify successful initialization mount on {}'.format(config['RAM0_PATH']))
            sys.exit(5)

        if mount.exitstatus != 0:
            print('FATAL: could not verify successful initialization mount on {} (bad exit status {})'.format(config['RAM0_PATH'], mount.exitstatus))
            sys.exit(6)
    else:
        print('(found mounted ramdisk, primary initialization skipped! Use --force to  re-initialize)')

    reset = pexpect.spawn('bash -c "{}/vendor/odroidxu3-reset.sh"'.format(config['REPO_PATH']),
        echo=True if verbose else False,
        timeout=STANDARD_TIMEOUT,
        encoding='utf-8'
    )

    reset.logfile = sys.stdout if verbose else None
    reset.expect(pexpect.EOF)
    reset.close()

    if reset.exitstatus != 0:
        print('WARN: cpu clock reset failed', end='')

        # if force:
        #     print(' (this error was ignored because force=True)', end='')

        # else:
        #     sys.exit(16)

    print()

if __name__ == "__main__":
    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        print('FATAL: must be root/sudo')
        sys.exit(1)

    config = parseConfigVars()

    if not config:
        raise ValueError('failed to load {}'.format(CONFIG_PATH))

    print(json.dumps(config, sort_keys=True, indent=2, default=str), '\n')

    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='force re-initialization and move past any errors')
    options = parser.parse_args()

    initialize(config=config, verbose=True, force=options.force)

    print("testbed manual initialization complete")
