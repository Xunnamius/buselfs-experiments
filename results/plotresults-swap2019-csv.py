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

import sys
from statistics import median

import initrunner
import libcruncher

from libcruncher.util import generateTitleFrag, stringToValidFilename, SC_SECURITY_RANKING

PRINT_DEBUG_INFO = False

TEST_IDENT = 'swap-2019'
TITLE_TEMPLATE = '{} [{}] Swap-2019 Tradeoff ({})'

RESULT_FILE_METRICS = ('energy', 'power', 'duration')
RESULT_DEBUG_METRICS = ('write1', 'read1', 'write2', 'read2')

# TODO: make this into a "print order" command line option
# Results matching these specifications are printed in the following order
RESULT_PRINT_ORDER = [
    'sc_chacha8_neon',
    'sc_chacha8_neon+sc_chacha20_neon',
    'sc_chacha20_neon',
    'sc_chacha20_neon+sc_freestyle_fast',
    'sc_freestyle_fast',
    'sc_freestyle_fast+sc_freestyle_balanced',
    'sc_freestyle_balanced',
    'sc_freestyle_balanced+sc_freestyle_secure',
    'sc_freestyle_secure',
]

# TODO: make this into a "exclusion filter" command line option
# Results matching this specification are not printed
RESULT_DO_NOT_PRINT = [
    'sc_chacha8_neon+sc_freestyle_balanced',
]

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

    data = { 'read': {}, 'write': {}, 'security': [], 'cipher': [], 'ratio': [], 'debug': {} }

    noData = { 'read': False, 'write': False, 'write_inside': False }

    for op in ['read', 'write']:
        for metric in RESULT_FILE_METRICS:
            data[op][metric] = []

    for debug_metric in RESULT_DEBUG_METRICS:
        data['debug'][debug_metric] = []

    # Loop over results and begin the aggregation/accumulation process
    for resultProps in execCTX.resultFileProps:
        localData = { 'read': {}, 'write': {}, 'debug': {} }

        rankOrder = [SC_SECURITY_RANKING[resultProps.cipher], SC_SECURITY_RANKING[resultProps.swapCipher]]
        rankOrder.sort()

        if resultProps.swapRatio <= 0 or resultProps.swapRatio > 4:
            raise ValueError('Bad resultProps.swapRatio "{}" for {}'.format(resultProps.swapRatio, resultProps.name))

        data['security'].append(
            # security ranking = c1_rank + abs(c1_rank - c2_rank) * actual_swap_ratio
            # where c1 <= c2
            rankOrder[0] + abs(rankOrder[0] - rankOrder[1]) * (resultProps.swapRatio * 0.25)
        )

        data['ratio'].append(0 if resultProps.swapRatio == 4 else resultProps.swapRatio)

        data['cipher'].append(('{}' if resultProps.cipher == resultProps.swapCipher else '{}+{}').format(resultProps.cipher, resultProps.swapCipher))

        for metric in RESULT_FILE_METRICS:
            localData['read'][metric] = []
            localData['write'][metric] = []

        for debug_metric in RESULT_DEBUG_METRICS:
            localData['debug'][debug_metric] = []

        with open(resultProps.path.absolute().as_posix(), 'r') as lines:
            for currentLine in lines:
                for debug_metric in RESULT_DEBUG_METRICS:
                    # We're dealing with debug duration metrics...
                    if currentLine.startswith('d_' + debug_metric):
                        localData['debug'][debug_metric].append(libcruncher.lineToNumber(currentLine))
                        break

                else:
                    for metric in RESULT_FILE_METRICS:
                        # We're dealing with read metrics...
                        if currentLine.startswith('r_' + metric):
                            localData['read'][metric].append(libcruncher.lineToNumber(currentLine))
                            noData['write_inside'] = True
                            break

                        # We're dealing with write metrics...
                        elif currentLine.startswith('w_' + metric):
                            localData['write'][metric].append(libcruncher.lineToNumber(currentLine))
                            noData['write_inside'] = True
                            break

                        # We're dealing with battery saver total write metrics...
                        if currentLine.startswith('wo_' + metric):
                            localData['write'][metric].append(libcruncher.lineToNumber(currentLine))
                            break

                        # We're dealing with battery saver to-X-seconds write metrics...
                        elif currentLine.startswith('wi_' + metric):
                            localData['read'][metric].append(libcruncher.lineToNumber(currentLine))
                            break

                        # These are technically comments/blank lines and are ignored
                        elif currentLine.startswith('---') or len(currentLine.strip()) == 0 or currentLine.startswith('mf'):
                            break
                    else:
                        raise ValueError('Bad data at read/write distinction: "{}"'.format(currentLine.strip()))

        for metric in RESULT_FILE_METRICS:
            for op in ['read', 'write']:
                if len(localData[op][metric]) == 0:
                    localData[op][metric] = 1
                    noData[op] = True

                else:
                    localData[op][metric] = median(localData[op][metric])

        for debug_metric in RESULT_DEBUG_METRICS:
            if len(localData['debug'][debug_metric]) == 0:
                localData['debug'][debug_metric] = 0

            else:
                localData['debug'][debug_metric] = median(localData['debug'][debug_metric])

        if noData['read'] and noData['write']:
            raise ValueError('No read or write data was collected (empty or malformed resultsets?)')

        localData['read'][RESULT_FILE_METRICS[0]] /= libcruncher.Decimal(1000000)
        localData['read'][RESULT_FILE_METRICS[2]] /= libcruncher.Decimal(1000000000)

        localData['write'][RESULT_FILE_METRICS[0]] /= libcruncher.Decimal(1000000)
        localData['write'][RESULT_FILE_METRICS[2]] /= libcruncher.Decimal(1000000000)

        for debug_metric in RESULT_DEBUG_METRICS:
            localData['debug'][debug_metric] /= libcruncher.Decimal(1000000000)

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

        for debug_metric in RESULT_DEBUG_METRICS:
            data['debug'][debug_metric].append(localData['debug'][debug_metric])

    if execCTX.observeBaseline:
        print('applying baseline calculations...')

        # TODO:!
        #execCTX.observeBaseline
        raise NotImplementedError('Not implemented')

    if execCTX.normalize:
        print('applying normalization calculations...')

        for op in ['read', 'write']:
            for metric in RESULT_FILE_METRICS:
                maximum = max(data[op][metric])
                minimum = min(data[op][metric])
                data[op][metric] = [((value - minimum)/(maximum - minimum) if maximum - minimum > 0 else 0) for value in data[op][metric]]

    print('organizing results...')

    titlePrefix = assumedResultsPathList[-2]

    titleFrag = generateTitleFrag(execCTX.filterPropsList)
    readTitle = TITLE_TEMPLATE.format(titlePrefix, 'reads', titleFrag)
    writeTitle = TITLE_TEMPLATE.format(titlePrefix, 'writes', titleFrag)
    unsortedIndexList = list(range(len(execCTX.resultFileProps)))
    sortedIndexList = []

    # ? Remove results that should not be printed
    for entry in RESULT_DO_NOT_PRINT:
        while entry in data['cipher']:
            i = data['cipher'].index(entry)
            unsortedIndexList.remove(i)
            data['cipher'][i] = 'deleted---{}'.format(data['cipher'][i])

    # ? Sort the results so that they print in the desired order
    for entry in RESULT_PRINT_ORDER:
        while entry in data['cipher']:
            i = data['cipher'].index(entry)
            unsortedIndexList.remove(i)
            sortedIndexList.append(i)
            data['cipher'][i] = 'sorted---{}'.format(data['cipher'][i])

    sortedIndexList.extend(unsortedIndexList)
    data['cipher'] = [x.split('---')[-1] for x in data['cipher']] # ? Restore data['cipher'] to its proper form

    print('observed {} data: {}'.format('read' if noData['write_inside'] else 'write (inside)', 'NO' if noData['read'] else 'yes'))
    print('observed write data: {}'.format('NO' if noData['write'] else 'yes'))
    print('number of observed baselines: {}'.format(len(execCTX.baselineFileProps)))
    print('print order is active: {}'.format('no' if not RESULT_PRINT_ORDER else 'YES'))

    excluded = len(execCTX.resultFileProps) - len(sortedIndexList)

    if excluded:
        print('WARNING: {} results were excluded!'.format(excluded))

    print('title frag: {}'.format(titleFrag or '(no props means no title frag)'))

    libcruncher.confirmBeforeContinuing()

    filename = '{}/{}-{}-{}{}'.format(
        '/'+'/'.join(assumedResultsPathList[:-1]),
        TEST_IDENT,
        '{}',
        stringToValidFilename(titleFrag),
        '.csv'
    )

    print('writing out CSV files...\n')

    if noData['read']:
        print('(skipped {} plot)'.format('read' if noData['write_inside'] else 'write (inside)'))

    else:
        with open(filename.format('{}'.format('read' if noData['write_inside'] else 'write_inside')), 'w') as file:
            print('cipher,security,ratio,', ','.join(RESULT_FILE_METRICS), sep='', file=file)

            for ndx in sortedIndexList:
                print('{},{},{}'.format(data['cipher'][ndx], data['security'][ndx], data['ratio'][ndx]), end='', file=file)

                for metric in RESULT_FILE_METRICS:
                    print(',{}'.format(data['read'][metric][ndx]), end='', file=file)

                debugResult1 = data['debug'][RESULT_DEBUG_METRICS[1]][ndx]
                debugResult2 = data['debug'][RESULT_DEBUG_METRICS[3]][ndx]

                if PRINT_DEBUG_INFO and debugResult1 + debugResult2 > 0:
                    print(' ({} + {})'.format(debugResult1, debugResult2), end='', file=file)

                print('', file=file)

        print('{} data written out to {}'.format('read' if noData['write_inside'] else 'write (inside)', filename.format('read')))

    if noData['write']:
        print('(skipped write plot)')

    else:
        with open(filename.format('write'), 'w') as file:
            print('cipher,security,ratio,', ','.join(RESULT_FILE_METRICS), sep='', file=file)
            for ndx in sortedIndexList:
                print('{},{},{}'.format(data['cipher'][ndx], data['security'][ndx], data['ratio'][ndx]), end='', file=file)

                for metric in RESULT_FILE_METRICS:
                    print(',{}'.format(data['write'][metric][ndx]), end='', file=file)

                debugResult1 = data['debug'][RESULT_DEBUG_METRICS[0]][ndx]
                debugResult2 = data['debug'][RESULT_DEBUG_METRICS[2]][ndx]

                if PRINT_DEBUG_INFO and debugResult1 + debugResult2 > 0:
                    print(' ({} + {})'.format(debugResult1, debugResult2), end='', file=file)

                print('', file=file)

        print('write data written out to {}'.format(filename.format('write')))

    print('\n -- plotting complete! -- ')
