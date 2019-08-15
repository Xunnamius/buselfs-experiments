#!/usr/bin/env python3
"""
This is the 8/1/2019 version of a script that script crunches any files that
ends with the extension ".result" and are direct children of the `results/` dir
while also accounting for swap ciphers, swap strategies, etc.

This script generates the set of tradeoff space consumable CSV files security vs
energy use, security vs power, and security vs performance as precursors for the
LaTeX charts for SwitchBox (2019). WMeant for consumption by Plotly's chart
studio.
"""

import os
import sys
import hashlib

from pathlib import Path
from statistics import median

import initrunner
import libcruncher

from libcruncher.util import generateTitleFrag, stringToValidFilename, SC_SECURITY_RANKING

TEST_IDENT = 'swap-2019'
TITLE_TEMPLATE = '{} [{}] Swap-2019 Tradeoff ({})'

RESULT_FILE_METRICS = ('energy', 'power', 'duration')

################################################################################

if __name__ == "__main__":
    libcruncher.requireSudo()

    print('crunching metrics...')

    config = initrunner.parseConfigVars()
    execCTX = libcruncher.argsToExecutionProperties(sys.argv[1:])

    # ? This is only used to come up with title fragment, so it doesn't have to
    # ? be super accurate!
    assumedResultsPathList = str(execCTX.resultFileProps[0].path).strip('/').split('/')

    print('aggregating data ({} items after filter)...'.format(len(execCTX.resultFileProps)))

    data = { 'read': {}, 'write': {}, 'security': [], 'cipher': [] }

    noReadData = False
    noWriteData = False

    for op in ['read', 'write']:
        for metric in RESULT_FILE_METRICS:
            data[op][metric] = []

    # Loop over results and begin the aggregation/accumulation process
    for resultProps in execCTX.resultFileProps:
        localData = { 'read': {}, 'write': {} }

        data['security'].append(
            (SC_SECURITY_RANKING[resultProps.cipher] + SC_SECURITY_RANKING[resultProps.swapCipher]) / 2)
        data['cipher'].append(('{}' if resultProps.cipher == resultProps.swapCipher else '{}+{}').format(resultProps.cipher, resultProps.swapCipher))

        for metric in RESULT_FILE_METRICS:
            localData['read'][metric] = []
            localData['write'][metric] = []

        with open(resultProps.path.absolute().as_posix(), 'r') as lines:
            for currentLine in lines:
                for metric in RESULT_FILE_METRICS:
                    # We're dealing with read metrics...
                    if currentLine.startswith('r_' + metric):
                        localData['read'][metric].append(libcruncher.lineToNumber(currentLine))
                        break

                    # We're dealing with write metrics...
                    elif currentLine.startswith('w_' + metric):
                        localData['write'][metric].append(libcruncher.lineToNumber(currentLine))
                        break

                    # These are technically comments/blank lines and are ignored
                    elif currentLine.startswith('---') or len(currentLine.strip()) == 0 or currentLine.startswith('mf'):
                        break
                else:
                    raise 'Bad data at read/write distinction: "{}"'.format(currentLine)

        for metric in RESULT_FILE_METRICS:
            if len(localData['read'][metric]) == 0:
                localData['read'][metric] = 1
                noReadData = True

            else:
                localData['read'][metric] = median(localData['read'][metric])

            if len(localData['write'][metric]) == 0:
                localData['write'][metric] = 1
                noWriteData = True

            else:
                localData['write'][metric] = median(localData['write'][metric])

        if noReadData and noWriteData:
            raise 'No read or write data was collected (empty or malformed resultsets?)'

        localData['read'][RESULT_FILE_METRICS[0]] /= 1000000
        localData['read'][RESULT_FILE_METRICS[2]] /= 1000000000

        localData['write'][RESULT_FILE_METRICS[0]] /= 1000000
        localData['write'][RESULT_FILE_METRICS[2]] /= 1000000000

        # Sometimes we can't trust the power we read!
        localData['read'][RESULT_FILE_METRICS[1]] = (
            localData['read'][RESULT_FILE_METRICS[0]] / localData['read'][RESULT_FILE_METRICS[2]]
        )

        localData['write'][RESULT_FILE_METRICS[1]] = (
            localData['write'][RESULT_FILE_METRICS[0]] / localData['write'][RESULT_FILE_METRICS[2]]
        )

        for op in ['read', 'write']:
            for metric in RESULT_FILE_METRICS:
                data[op][metric].append(localData[op][metric])

    if execCTX.observeBaseline:
        print('applying baseline calculations...')

        # TODO:!
        #execCTX.observeBaseline
        raise 'Not implemented'

    print('organizing results...')

    titlePrefix = assumedResultsPathList[-2]

    titleFrag = generateTitleFrag(execCTX.filterPropsList)
    readTitle = TITLE_TEMPLATE.format(titlePrefix, 'reads', titleFrag)
    writeTitle = TITLE_TEMPLATE.format(titlePrefix, 'writes', titleFrag)

    print('observed read data: {}'.format('NO' if noReadData else 'yes'))
    print('observed write data: {}'.format('NO' if noWriteData else 'yes'))
    print('number of observed baselines: {}'.format(len(execCTX.baselineFileProps)))
    print('title frag: {}'.format(titleFrag or '(no props means no title frag)'))

    libcruncher.confirmBeforeContinuing()

    filename = '{}/{}-{}-{}{}'.format(
        '/'+'/'.join(assumedResultsPathList[:-1]),
        TEST_IDENT,
        '{}',
        stringToValidFilename(titleFrag),
        '.csv'
    )

    print('writing out CSV...\n')

    if noReadData:
        print('(skipped read plot)')

    else:
        with open(filename.format('read'), 'w') as file:
            print('cipher,security,', ','.join(RESULT_FILE_METRICS), sep='', file=file)
            for result in data['read']:
                print('{},{}'.format(result['cipher'], result['security']), end='', file=file)

                for metric in RESULT_FILE_METRICS:
                    print(',{}'.format(result[metric]), end='', file=file)

                print('', file=file)

        print('read data written out to {}'.format(filename.format('read')))

    if noWriteData:
        print('(skipped write plot)')

    else:
        with open(filename.format('write'), 'w') as file:
            print('cipher,security,', ','.join(RESULT_FILE_METRICS), sep='', file=file)
            for result in data['write']:
                print('{},{}'.format(result['cipher'], result['security']), end='', file=file)

                for metric in RESULT_FILE_METRICS:
                    print(',{}'.format(result[metric]), end='', file=file)

                print('', file=file)

        print('write data written out to {}'.format(filename.format('write')))

    print('\n -- plotting complete! -- ')
