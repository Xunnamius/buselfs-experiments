"""
This is a base Python package that holds most of the shared result data number
crunching code. If you're looking to interpret result data, start here.
"""

import argparse
import re
import os
import sys

from pathlib import Path
from decimal import Decimal

from libcruncher.exception import (ResultPropertyAttributeError,
                                   EmptyResultsSubsetError,
                                   InvalidPathError,
                                   FilenameTranslationError,
                                   SudoRequired)

from libcruncher.util import (ResultProperties,
                              ExecutionProperties,
                              ResultProperty,
                              DEFAULT_CIPHER_IDENT,
                              DEFAULT_FLAKESIZE,
                              DEFAULT_FPN,
                              DEFAULT_STRATEGY)

def lineToNumber(line):
    """Converts a line string like "energy: 55" into a number"""
    return Decimal(line.split(': ')[1])

def pathToResultProperties(path):
    """Converts a path into a ResultProperties object"""
    try:
        filename = path.name
        data1 = filename.split('.')
        data2 = data1[2].split('-')
        data3 = data2[1].split('#')
        data4 = data2[1].split('+')

        data3Len = len(data3)

        # ! If modifying file name metadata (i.e. ResultProperties), edit these

        cipher = DEFAULT_CIPHER_IDENT
        flakesize = DEFAULT_FLAKESIZE
        flakesPerNugget = DEFAULT_FPN
        swapStrategy = DEFAULT_STRATEGY
        swapCipher = 0

        if not (1 <= data3Len <= 6):
            raise FilenameTranslationError('encountered invalid data3 length ({})'.format(data3Len))

        if len(data4) >= 2:
            data2[1], data4 = data4
            data3 = data2[1].split('#')
        else:
            data4 = 0

        usingDefaultCipher = data3Len == 1 or data3[1] == 'baseline'

        if not usingDefaultCipher:
            cipher = data3[1]

        if data3Len >= 3:
            flakesize = int(data3[2])

        if data3Len >= 4:
            flakesPerNugget = int(data3[3])

        if data3Len >= 5:
            swapCipher = data3[4]
        else:
            swapCipher = cipher

        if data3Len >= 6:
            swapStrategy = data3[5]

        props = ResultProperties(
            path,
            filename,
            data1[0],
            data1[1],
            data2[0],
            data2[2],
            data3[0],
            cipher,
            flakesize,
            flakesPerNugget,
            usingDefaultCipher and data3Len != 1,
            swapCipher,
            swapStrategy,
            int(data4) or 'N/A'
        )

    except IndexError:
        raise FilenameTranslationError(filename)

    return props

# ! If modifying file name metadata (i.e. ResultProperties), edit this function
def resultPropertiesToProperName(resultProperties, hideProperties=[]):
    """Converts a ResultProperties into a string (suitable for alt/mouseover
    text)"""
    properName = []

    if 'order' not in hideProperties and 'medium' not in hideProperties:
        properName.append('[{};{}] '.format(resultProperties.order, resultProperties.medium))

    elif 'order' in hideProperties and 'medium' in hideProperties:
        pass

    elif 'order' in hideProperties or 'medium' in hideProperties:
        properName.append('[{}] '.format(
            resultProperties.medium if 'order' in hideProperties else resultProperties.order
        ))

    if 'backstore' not in hideProperties:
        properName.append('{}{}'.format(resultProperties.backstore, '-' if 'filesystem' not in hideProperties else ' '))

    if 'filesystem' not in hideProperties:
        properName.append('{} '.format(resultProperties.filesystem))

    if 'flakesize' not in hideProperties:
        properName.append('fs={} '.format(resultProperties.flakesize))

    if 'fpn' not in hideProperties:
        properName.append('fpn={} '.format(resultProperties.fpn))

    cipher = '-'.join(resultProperties.cipher.split('_')[1:])
    swapCipher = '-'.join(resultProperties.swapCipher.split('_')[1:])

    if 'cipher' not in hideProperties and 'swapCipher' not in hideProperties and cipher == swapCipher:
        properName.append('{} '.format(cipher))

    else:
        if 'cipher' not in hideProperties:
            properName.append('{}{}{}'.format(
                '(primary cipher) ' if 'swapCipher' in hideProperties else '',
                cipher,
                '=>' if 'swapCipher' not in hideProperties else ' '
            ))

        if 'swapCipher' not in hideProperties:
            properName.append('{}{} '.format('(swap cipher) ' if 'cipher' in hideProperties else '', swapCipher))

    if 'swapStrategy' not in hideProperties:
        properName.append('{} '.format('-'.join(resultProperties.swapStrategy.split('_')[1:])))

    if 'iops' not in hideProperties:
        properName.append('{} '.format(resultProperties.iops))

    if 'phase' not in hideProperties and resultProperties.phase != 'N/A':
        properName.append('(P{})'.format(resultProperties.phase))

    return ''.join(properName).strip() or ''

def yieldResultsSubset(resultPropertiesObjects, includeProps=None, allowPartialMatch=True):
    """Accepts a list of ResultProperties objects and returns a subset of them
    depending on the property=value pairs passed into includeProps"""

    results = []
    includeProps = includeProps or []

    for resultProperties in resultPropertiesObjects:
        include = False

        for prop in includeProps:
            try:
                propValues = str(prop.value).split(',') or []
                actualValue = str(getattr(resultProperties, str(prop.name)))

                if actualValue in propValues:
                    include = True

                    if allowPartialMatch:
                        break

                elif not allowPartialMatch:
                    include = False
                    break

            except AttributeError:
                raise ResultPropertyAttributeError(prop.name)

        if not includeProps or include:
            results.append(resultProperties)

    if not results:
        raise EmptyResultsSubsetError()

    return results

def argsToExecutionProperties(argv, description=''):
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        'paths',
        nargs='+',
        metavar='file|dir',
        action=_StorePathsAsResultPropertiesAction,
        help='one or more *.results files or directories containing such files'
    )

    parser.add_argument(
        '-f',
        '--filter',
        nargs='+',
        metavar='prop=val1,val2,...',
        type=_filterGenerateTuple,
        help='filter results by only including those that satisfy at least one property=value pair (see ResultProperties) (commas are treated as special "or" syntax)'
    )

    parser.add_argument(
        '-x',
        '--strict-filtering',
        action='store_true',
        help='while filtering results, ALL property=value pairs must be satisfied instead of at least one'
    )

    parser.add_argument(
        '-b',
        '--baseline',
        metavar='file',
        help='elements will be plotted relative to the data in the specified result file (default is literal values)'
    )

    args = parser.parse_args(argv)

    return ExecutionProperties(
        yieldResultsSubset(args.paths, args.filter, not args.strict_filtering),
        args.baseline,
        args.filter,
        args.strict_filtering
    )

def confirmBeforeContinuing():
    user_input = input('=> look good? (y/N): ')
    if user_input != 'y':
        print('not continuing!')
        sys.exit(4)

def requireSudo():
    try:
        os.geteuid

    except AttributeError:
        print('(warning: os.geteuid was polyfilled; are we root?)')
        os.geteuid = lambda: 0

    if os.geteuid() != 0:
        raise SudoRequired()

def _filterGenerateTuple(value):
    match = re.match(r'^(?P<prop>[A-Za-z0-9_]+)=(?P<val>[A-Z_,\-.*\/\\#a-z0-9]*)$', str(value))

    if match is None:
         raise argparse.ArgumentTypeError('"{}" has invalid syntax; expected X=Y'.format(value))

    return ResultProperty(match.group('prop'), match.group('val') or '')

class _StorePathsAsResultPropertiesAction(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=None,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):

        super(_StorePathsAsResultPropertiesAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        paths = getattr(namespace, self.dest) or []
        actual = []

        for value in values:
            path = Path(os.path.realpath(value))

            if not path.exists():
                raise InvalidPathError(path)

            elif path.is_file():
                paths.append(path)

            else:
                paths.extend(path.glob('*.results'))

        paths.sort()

        for path in paths:
            actual.append(pathToResultProperties(path))

        setattr(namespace, self.dest, actual)

pathToResultProperties(Path('/home/odroid/bd3/repos/buselfs-experiments/results/filebench.ram.1k-f2fs#baseline-strongbox.results'))
pathToResultProperties(Path('/home/odroid/bd3/repos/buselfs-experiments/results/filebench.ram.1k-f2fs#baseline+1-strongbox.results'))
pathToResultProperties(Path('/home/odroid/bd3/repos/buselfs-experiments/results/filebench.ram.1k-f2fs#sc_freestyle_fast#512+3-strongbox.results'))
pathToResultProperties(Path('/home/odroid/bd3/repos/buselfs-experiments/results/filebench.ram.1k-f2fs#sc_freestyle_fast#512#8#sc_chacha8_neon+3-strongbox.results'))
pathToResultProperties(Path('/home/odroid/bd3/repos/buselfs-experiments/results/filebench.ram.1k-f2fs#sc_freestyle_fast#512#8#sc_chacha8_neon#swap_aggressive+2-strongbox.results'))
