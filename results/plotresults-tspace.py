#!/usr/bin/env python3
"""
This is the 7/29/2018 version of a script that script crunches any files that
ends with the extension ".result" and are direct children of the `results/` dir.

This script generates a set of tradeoff space charts plotting security vs energy
use, security vs power, and security vs performance.
"""

import os
import sys

from pathlib import Path
from statistics import median
from plotly.graph_objs import Splom

import initrunner
import libcruncher

from libcruncher.util import (generateTitleFrag,
                              formatAndPlotFigure,
                              SC_SECURITY_RANKING,
                              DEFAULT_CIPHER_IDENT,
                              DEFAULT_FLAKESIZE,
                              DEFAULT_FPN,
                              COLORS_A,
                              COLORS_B)

TEST_IDENT = 'tspace-splom'
TITLE_TEMPLATE = '{} [{}] Tradeoff SPLOM ({})'

PLOT_OFFLINE = True

RESULT_FILE_METRICS = ('energy', 'power', 'duration')

PLOT_AXES = ('security (level)', 'latency (s)', 'energy (j)', 'power (w)', 'flakesize (b)', 'fpn')

# ? X is aliased/points to Y (the original); 'X':'Y'
AXIS_ALIASES = {
    'latency (s)': 'duration',
    'energy (j)': 'energy',
    'power (w)': 'power'
}

# ! Note that subvalues in this dict are further refined dynamically later on
SPECIAL_AXES = {
    # ? key => an int matching the axis number, e.g. xaxis1 would be matched by key int(1)
    # ? value => a dict representing an axis configuration (merged into default)
    1: {
        'tickvals': [0, 1, 2, 3],
        'range': [-0.5, 3.5],
    },
    2: {
        'rangemode': 'tozero',
    },
    3: {
        'rangemode': 'tozero',
        'ticksuffix': '=N/A',
        'showticksuffix': 'first'
    },
    4: {
        'rangemode': 'tozero',
        'ticksuffix': '=N/A',
        'showticksuffix': 'first'
    },
    5: {
        'type': 'category',
        'categoryorder': 'array',
    },
    6: {
        'type': 'category',
        'categoryorder': 'array',
    },
}

# * In this file, marker colors correspond to iop size ("iops" is the "class")
# * There are five (+1 -> 5g) iop sizes: 1024b (1k), 4096b (4k), 512kib (512k),
# *  5mib (5m), 40mib (40m)
# * Hence, for this class there should be five rgba colors specified below

COLOR_OPACITY = 0.5

SPECIAL_MARKER = {
    # ? This is a mapping between list indices (corresponding to components of
    # ?  the data[axis] vectors) and their "class" (described above)
    # ! Note that this is typically defined dynamically during plot calculations
    'color': [],
    
    # ? This is a list of rgba colors corresponding to the "classes" used in
    # ?  SPECIAL_MARKER::colors (described above)
    # ! Note that this is typically defined manually (by YOU, dev!)
    # ? Also note that it doesn't have to be 1-to-1 (i.e. can have extra colors)
    # ?  but there must be more (or equal) colors than there are "classes"
    'colorscale': [
        'rgba(25, 211, 243, {})'.format(COLOR_OPACITY),
        'rgba(231, 99, 250, {})'.format(COLOR_OPACITY),
        'rgba(99, 110, 250, {})'.format(COLOR_OPACITY),
        'rgba(253, 95, 0, {})'.format(COLOR_OPACITY),
        'rgba(0, 253, 95, {})'.format(COLOR_OPACITY),
    ]
}

# SPECIAL_MARKERS = {
#     # ? key => a string matching the name of an axis in PLOT_AXES
#     # ? value => a dict representing a marker configuration (merged into default)
# }

SPECIAL_MARKERS = { key: SPECIAL_MARKER for key in PLOT_AXES }


################################################################################

def generateTrace(data, idents, plotAxes, specialMarkers={}):
    marker = {
        'size': 7,
        'showscale': False,
        'line': { 'width': 0.5, 'color': 'rgb(230,230,230)' },
    }

    return Splom(
        dimensions=[{ 'label': axis, 'values': data[axis] } for axis in plotAxes],
        text=idents,
        marker={ **marker, **specialMarkers[axis] } if axis in specialMarkers else marker, 
    )

if __name__ == "__main__":
    libcruncher.requireSudo()

    print('crunching metrics...')

    config = initrunner.parseConfigVars()
    execCTX = libcruncher.argsToExecutionProperties(sys.argv[1:])
    assumedResultsPathList = str(execCTX.resultFiles[0].path).strip('/').split('/')

    print('aggregating data ({} items after filter)...'.format(len(execCTX.resultFiles)))

    data = { 'read': {}, 'write': {}, 'idents': [] }
    dimensionClassesOrdered = []
    flakesizeTickVals = set()
    fpnTickVals = set()
    classmap = {}

    for op in ['read', 'write']:
        for metric in RESULT_FILE_METRICS:
            data[op][metric] = []

        data[op][PLOT_AXES[0]] = []
        data[op][PLOT_AXES[4]] = []
        data[op][PLOT_AXES[5]] = []

    # Loop over results and begin the aggregation/accumulation process
    for resultProps in execCTX.resultFiles:
        localData = { 'read': {}, 'write': {} }

        if resultProps.iops not in classmap:
            classmap[resultProps.iops] = len(classmap)
        
        dimensionClassesOrdered.append(classmap[resultProps.iops])
        flakesizeTickVals.add(resultProps.flakesize)
        fpnTickVals.add(resultProps.fpn)
        data['idents'].append(libcruncher.resultPropertiesToProperName(resultProps))

        for op in ['read', 'write']:
            for metric in RESULT_FILE_METRICS:
                localData[op][metric] = []

        with open(resultProps.path.absolute().as_posix(), 'r') as lines:
            for currentLine in lines:
                for metric in RESULT_FILE_METRICS:
                    if not localData['read'][metric]:
                        localData['read'][metric] = []
                    
                    if not localData['write'][metric]:
                        localData['write'][metric] = []

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
                    print('Bad data at read/write distinction: "{}"'.format(currentLine))
                    raise 'Bad data at read/write distinction (see above)'
        
        for metric in RESULT_FILE_METRICS:
            localData['read'][metric]  = median(localData['read'][metric])
            localData['write'][metric] = median(localData['write'][metric])

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

        if dimensionLength != readlen or dimensionLength != writelen:
            print(
                'ERROR: one or both of the cardinalities r=({}) and w=({}) do not match expected ({}) for axis="{}"'
                    .format(readlen, writelen, dimensionLength, axis)
            )
            sys.exit(64)

    print('organizing results...')

    titlePrefix = assumedResultsPathList[-2]

    titleFrag = generateTitleFrag(execCTX.filterProps)
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

    print('final dimension cardinality: {}'.format(dimensionLength))

    libcruncher.confirmBeforeContinuing()

    filenamePrefix = '/'+'/'.join(assumedResultsPathList[:-1]) if PLOT_OFFLINE else ''

    print('generating plots...\n')
    print('read plot: ', end='')

    # * Refine SPECIAL_AXES
    SPECIAL_AXES[5] = { **SPECIAL_AXES[5], **{ 'categoryarray': sorted(list(flakesizeTickVals)) } }
    SPECIAL_AXES[6] = { **SPECIAL_AXES[6], **{ 'categoryarray': sorted(list(fpnTickVals)) } }

    formatAndPlotFigure(
        file_ident='read',
        test_ident=TEST_IDENT,
        trace=readTrace,
        title=readTitle,
        filesdir=filenamePrefix,
        axisCount=len(PLOT_AXES),
        specialAxes=SPECIAL_AXES,
        offline=PLOT_OFFLINE
    )

    print('\nwrite plot: ', end='')

    formatAndPlotFigure(
        file_ident='write',
        test_ident=TEST_IDENT,
        trace=writeTrace,
        title=writeTitle,
        filesdir=filenamePrefix,
        axisCount=len(PLOT_AXES),
        specialAxes=SPECIAL_AXES,
        offline=PLOT_OFFLINE
    )

    print('\n -- plotting complete! -- ')
