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
                              DEFAULT_FPN)

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

        # ! If modifying file name metadata (i.e. ResultProperties), edit these

        if data3[1] == 'baseline':
            props = ResultProperties(
                path,
                filename,
                data1[0],
                data1[1],
                data2[0],
                data2[2],
                data3[0],
                DEFAULT_CIPHER_IDENT,
                DEFAULT_FLAKESIZE,
                DEFAULT_FPN,
                True
            )
        
        else:
            props = ResultProperties(
                path,
                filename,
                data1[0],
                data1[1],
                data2[0],
                data2[2],
                data3[0],
                data3[1],
                int(data3[2]),
                int(data3[3]),
                False
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

    elif 'order' in hideProperties or 'medium' in hideProperties:
        properName.append('[{}] '.format(resultProperties.order if 'order' in hideProperties else resultProperties.medium))
    
    if 'backstore' not in hideProperties:
        properName.append('{}{}'.format(resultProperties.backstore, '-' if 'fs' not in hideProperties else ' '))
    
    if 'fs' not in hideProperties:
        properName.append('{} '.format(resultProperties.fs))
    
    if 'flakesize' not in hideProperties:
        properName.append('fs={}{}'.format(resultProperties.flakesize, ';' if 'fpn' not in hideProperties else ' '))
    
    if 'fpn' not in hideProperties:
        properName.append('fpn={} '.format(resultProperties.fpn))
    
    if 'iops' not in hideProperties:
        properName.append('{} '.format(resultProperties.iops))
    
    if 'cipher' not in hideProperties:
        properName.append('{} '.format('-'.join(resultProperties.cipher.split('_')[1:])))

    return ''.join(properName).strip()

def yieldResultsSubset(resultPropertiesObjects, includeProps=[], allowPartialMatch=True):
    """Accepts a list of ResultProperties objects and returns a subset of them
    depending on the property=value pairs passed into includeProps"""
    
    results = []

    for resultProperties in resultPropertiesObjects:
        include = False

        for prop in includeProps:
            try:
                if getattr(resultProperties, prop.name) == prop.value:
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
    metaText = 'file|dir'

    parser.add_argument(
        'paths',
        nargs='+',
        metavar=metaText,
        action=_StorePathsAsResultPropertiesAction,
        help='one or more *.result files or directories containing such files'
    )

    parser.add_argument(
        '-f',
        '--filter',
        nargs='+',
        metavar='prop=val',
        type=_filterGenerateTuple,
        help='filter results by only including those satisfy at least one property=value pair (see ResultProperties)'
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
        metavar=metaText,
        help='elements will be plotted relative to the data in the specified result file (default is literal values)'
    )

    args = parser.parse_args(argv)

    return ExecutionProperties(yieldResultsSubset(args.paths, args.filter, not args.strict_filtering), args.baseline, args.filter, args.strict_filtering)

def requireSudo():
    try:
        os.geteuid

    except AttributeError:
        print('(warning: os.geteuid was polyfilled; are we root?)')
        os.geteuid = lambda: 0

    if os.geteuid() != 0:
        raise SudoRequired()

def _filterGenerateTuple(value):
    match = re.match(r'(?P<prop>[A-Za-z0-9]+)=(?P<val>[A-Za-z0-9]*)', str(value))

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
