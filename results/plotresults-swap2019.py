#!/usr/bin/env python3
"""
This is the 8/1/2019 version of a script that script crunches any files that
ends with the extension ".result" and are direct children of the `results/` dir
while also accounting for swap ciphers, swap strategies, etc.

This script generates the set of tradeoff space charts plotting security vs
energy use, security vs power, and security vs performance as precursors for the
LaTeX charts for SwitchBox (2019). Works with Plotly 4.
"""

import os
import sys

from pathlib import Path
from statistics import median
import plotly.graph_objects as go

import initrunner
import libcruncher

from libcruncher.util import generateTitleFrag, stringToValidFilename, formatAndPlotFigure, SC_SECURITY_RANKING

TEST_IDENT = 'swap-2019'
TITLE_TEMPLATE = '{} [{}] Swap-2019 Tradeoff ({})'

################################################################################

def generateTrace(data, plotAxes, specialMarkers={}):
    marker = {
        'size': 7,
        'showscale': False,
        'line': { 'width': 0.5, 'color': 'rgb(230,230,230)' },
    }

    return Splom(
        dimensions=[{ 'label': axis, 'values': data[axis] } for axis in plotAxes],
        marker={ **marker, **specialMarkers[axis] } if axis in specialMarkers else marker,
    )

if __name__ == "__main__":
    libcruncher.requireSudo()

    print('crunching metrics...')

    config = initrunner.parseConfigVars()
    execCTX = libcruncher.argsToExecutionProperties(sys.argv[1:])
    # ? This is only used to come up with title fragment, so it doesn't have to
    # ? be super accurate!
    assumedResultsPathList = str(execCTX.resultFileProps[0].path).strip('/').split('/')

    print('aggregating data ({} items after filter)...'.format(len(execCTX.resultFileProps)))

    data = { 'read': {}, 'write': {}, 'idents': [] }
    dimensionClassesOrdered = []
    flakesizeTickVals = set()
    fpnTickVals = set()

    noReadData = False
    noWriteData = False

    for op in ['read', 'write']:
        for metric in RESULT_FILE_METRICS:
            data[op][metric] = []

        data[op][PLOT_AXES[0]] = []
        data[op][PLOT_AXES[4]] = []
        data[op][PLOT_AXES[5]] = []

    # Loop over results and begin the aggregation/accumulation process
    for resultProps in execCTX.resultFileProps:
        localData = { 'read': {}, 'write': {} }

        flakesizeTickVals.add(resultProps.flakesize)
        fpnTickVals.add(resultProps.fpn)
        data['idents'].append(libcruncher.resultPropertiesToProperName(resultProps))

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

            data[op][PLOT_AXES[0]].append(SC_SECURITY_RANKING[resultProps.cipher])
            data[op][PLOT_AXES[4]].append(resultProps.flakesize)
            data[op][PLOT_AXES[5]].append(resultProps.fpn)

    if execCTX.observeBaseline:
        print('applying baseline calculations...')

        # TODO:!
        #execCTX.observeBaseline
        raise 'Not implemented'

    print('aliasing data...')

    for axis in PLOT_AXES:
        if axis in AXIS_ALIASES:
            print('{} => {}'.format(AXIS_ALIASES[axis], axis))
            data['read'][axis] = data['read'][AXIS_ALIASES[axis]]
            data['write'][axis] = data['write'][AXIS_ALIASES[axis]]

    dimensionLength = len(dimensionClassesOrdered)

    # * Sanity check
    for axis in PLOT_AXES:
        readlen = len(data['read'][axis])
        writelen = len(data['write'][axis])

        if (not noReadData and dimensionLength != readlen) or (not noWriteData and dimensionLength != writelen):
            print(
                'ERROR: one or both of the cardinalities r=({}) and w=({}) do not match expected ({}) for axis="{}"'
                    .format(readlen, writelen, dimensionLength, axis)
            )
            sys.exit(64)

    print('organizing results...')

    titlePrefix = assumedResultsPathList[-2]

    titleFrag = generateTitleFrag(execCTX.filterPropsList)
    readTitle = TITLE_TEMPLATE.format(titlePrefix, 'reads', titleFrag)
    writeTitle = TITLE_TEMPLATE.format(titlePrefix, 'writes', titleFrag)

    colorscaleLength = len(SPECIAL_MARKER['colorscale'])
    classmapLength = len(classmap)

    if colorscaleLength < classmapLength:
        print('Invalid colorscale length (expected {} >= {})'.format(colorscaleLength, classmapLength))
        sys.exit(32)

    # * Define and refine SPECIAL_MARKER

    SPECIAL_MARKER['color'] = dimensionClassesOrdered
    colorscaleActual = []

    for i in range(colorscaleLength):
        colorscaleActual.append([i / colorscaleLength, SPECIAL_MARKER['colorscale'][i]])
        colorscaleActual.append([(i + 1) / colorscaleLength, SPECIAL_MARKER['colorscale'][i]])

    SPECIAL_MARKER['colorscale'] = colorscaleActual

    readTrace = generateTrace(data['read'], data['idents'], PLOT_AXES, SPECIAL_MARKERS)
    writeTrace = generateTrace(data['write'], data['idents'], PLOT_AXES, SPECIAL_MARKERS)

    readTrace['diagonal'].update(visible=False)
    writeTrace['diagonal'].update(visible=False)

    print('observed read data: {}'.format('NO' if noReadData else 'yes'))
    print('observed write data: {}'.format('NO' if noWriteData else 'yes'))
    print('final dimension cardinality: {}'.format(dimensionLength))
    print('number of observed baselines: {}'.format(len(execCTX.baselineFileProps)))
    print('title frag: {}'.format(titleFrag or '(no props means no title frag)'))

    libcruncher.confirmBeforeContinuing()

    filenamePrefix = '/'+'/'.join(assumedResultsPathList[:-1]) if PLOT_OFFLINE else ''

    print('generating plots...\n')

    # * Refine SPECIAL_AXES
    SPECIAL_AXES[5] = { **SPECIAL_AXES[5], **{ 'categoryarray': sorted(list(flakesizeTickVals)) } }
    SPECIAL_AXES[6] = { **SPECIAL_AXES[6], **{ 'categoryarray': sorted(list(fpnTickVals)) } }

    if noReadData:
        print('(skipped read plot)')

    else:
        print('read plot: ', end='')

        formatAndPlotFigure(
            file_ident='read{}'.format('-' + stringToValidFilename(titleFrag) if titleFrag else ''),
            test_ident=TEST_IDENT,
            trace=readTrace,
            title=readTitle,
            filesdir=filenamePrefix,
            axisCount=len(PLOT_AXES),
            specialAxes=SPECIAL_AXES,
            offline=PLOT_OFFLINE
        )

    if noWriteData:
        print('(skipped write plot)')

    else:
        print('\nwrite plot: ', end='')

        formatAndPlotFigure(
            file_ident='write{}'.format('-' + stringToValidFilename(titleFrag) if titleFrag else ''),
            test_ident=TEST_IDENT,
            trace=writeTrace,
            title=writeTitle,
            filesdir=filenamePrefix,
            axisCount=len(PLOT_AXES),
            specialAxes=SPECIAL_AXES,
            offline=PLOT_OFFLINE
        )

    print('\n -- plotting complete! -- ')
