#!/usr/bin/env python3

# pylint: disable=E0202

"""
This is the 6/29/2018 version of a script that script crunches any files that
ends with the extension ".result" and are direct children of the `results/` dir.

This script generates a set of tradeoff space charts plotting security vs energy
use, security vs power, and security vs performance.
"""

import os
import sys
import hashlib
import pprint
import copy
import inspect
import plotly.plotly as py
from pathlib import Path
from decimal import Decimal
from statistics import median
from collections import namedtuple
from plotly.graph_objs import Splom, Layout, Figure

import initrunner

TEST_IDENT = 'StrongBox-experiments-tradeoffspace-splom'

# TODO: change "duration" to latency
RESULT_FILE_METRICS = ('energy', 'power', 'duration')
PLOT_AXES = ('security', 'latency', 'energy', 'power', 'flakesize', 'fpn')

TITLE_TEMPLATE = '{} [{}] Tradeoff SPLOM ({} trials/runs)'

################################################################################

def lineToNumber(line):
    """Converts a line string like "energy: 55" into a number"""
    return Decimal(line.split(': ')[1])

# TODO: more dynamic the two following functions need to be
# TODO: (we need a standardized naming scheme of some type)
def filenameToResultProperties(filename):
    data1 = filename.split('.')
    data2 = data1[2].split('-')
    data3 = data2[1].split('#')

    if data3[1] == 'baseline':
        props = ResultProperties(filename, data1[0], data1[1], data2[0], data2[2], data3[0], DEFAULT_CIPHER_IDENT, DEFAULT_FLAKESIZE, DEFAULT_FPN)

    else:
        props = ResultProperties(filename, data1[0], data1[1], data2[0], data2[2], data3[0], data3[1], int(data3[2]), int(data3[3]))

    return props

# TODO: make it easy to include/ignore parts of resultProps that we don't want to include
def resultPropertiesToProperName(resultProperties, hideProperties=[]):
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

def generateTrace(data, idents):
    return Splom(
        dimensions=[
            { 'label': 'energy', 'values': data['energy']},
            { 'label': 'power', 'values': data['power']},
            { 'label': 'duration', 'values': data['duration']},
            { 'label': 'security', 'values': data['security']},
            { 'label': 'flakesize', 'values': data['flakesize']},
            { 'label': 'fpn', 'values': data['fpn']},
        ],
        text=data['idents'],
        marker={
            #'color': color_vals,
            'size': 7,
            #'colorscale': pl_colorscale,
            'showscale': False,
            'line': { 'width': 0.5, 'color': 'rgb(230,230,230)' }
        },
    )

def generateSharedLayout(title):
    axis = {
        'showline': True,
        'zeroline': False,
        'gridcolor': '#fff',
        'ticklen': 4,
    }

    return Layout(
        dragmode='select',
        hovermode='closest',
        title=title,
        margin=dict(b=160),
        #width=600,
        #height=600,
        #autosize=False,
        plot_bgcolor='rgba(240,240,240, 0.95)',

        xaxis1=dict(axis),
        xaxis2=dict(axis),
        xaxis3=dict(axis),
        xaxis4=dict(axis),
        xaxis5=dict(axis),
        xaxis6=dict(axis),

        yaxis1=dict(axis),
        yaxis2=dict(axis),
        yaxis3=dict(axis),
        yaxis4=dict(axis),
        yaxis5=dict(axis),
        yaxis6=dict(axis),
    )

if __name__ == "__main__":
    CONFIG = initrunner.parseConfigVars()

    filesdir = None

    try:
        os.geteuid
    except AttributeError:
        os.geteuid = lambda: -1

    if os.geteuid() != 0:
        print('must be root/sudo')
        sys.exit(1)

    # TODO: Use the more advanced python opts API
    if len(sys.argv) != 2:
        print('Usage: {} <data directory>'.format(sys.argv[0]))
        sys.exit(2)

    else:
        filesdir = sys.argv[1].strip('/')

        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(3)

    print('result files directory: {}'.format(filesdir))

    # TODO: baselines get different icon representation?
    data = { 'read': {}, 'write': {}, 'idents': [] }

    for op in ['read', 'write']:
        for metric in RESULT_FILE_METRICS:
            data[op][metric] = []

        data[op]['security'] = []
        data[op]['flakesize'] = []
        data[op]['fpn'] = []

    resultFiles = sorted(list(Path(os.path.realpath(filesdir)).glob('*.results')))
    resultFileNames = []

    print('crunching ({} data items)...'.format(len(resultFiles)))

    # Loop over results and begin the aggregation/accumulation process
    for resultFile in resultFiles:
        props = filenameToResultProperties(resultFile.name)

        # ! (remove this later) we're going to skip non-40m non-sequential non-f2fs results!
        if props.order != 'sequential' or props.iops != '40m' or props.fs != 'f2fs':
            continue

        data['idents'].append(resultPropertiesToProperName(props))

        localData = { 'read': {}, 'write': {}}

        for op in ['read', 'write']:
            for metric in RESULT_FILE_METRICS:
                localData[op][metric] = []

        with open(resultFile.absolute().as_posix(), 'r') as lines:
            for currentLine in lines:
                for metric in RESULT_FILE_METRICS:
                    if not localData['read'][metric]:
                        localData['read'][metric] = []
                    
                    if not localData['write'][metric]:
                        localData['write'][metric] = []

                    # We're dealing with read metrics...
                    if currentLine.startswith('r_' + metric):
                        localData['read'][metric].append(lineToNumber(currentLine))
                        break

                    # We're dealing with write metrics...
                    elif currentLine.startswith('w_' + metric):
                        localData['write'][metric].append(lineToNumber(currentLine))
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

        localData['read']['energy'] /= 1000000
        localData['read']['duration'] /= 1000000000

        localData['write']['energy'] /= 1000000
        localData['write']['duration'] /= 1000000000

        # Sometimes we can't trust the power we read!
        localData['read']['power'] = localData['read']['energy'] / localData['read']['duration']
        localData['write']['power'] = localData['write']['energy'] / localData['write']['duration']
        
        for op in ['read', 'write']:
            for metric in RESULT_FILE_METRICS:
                data[op][metric].append(localData[op][metric])

            data[op]['security'].append(SC_SECURITY_RANKING[props.cipher])
            data[op]['flakesize'].append(props.flakesize)
            data[op]['fpn'].append(props.fpn)

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]

    # TODO: Compact this into a function?
    read_title = TITLE_TEMPLATE.format(titlePrefix, 'reads', CONFIG['TRIALS_INT'])
    write_title = TITLE_TEMPLATE.format(titlePrefix, 'writes', CONFIG['TRIALS_INT'])

    # TODO: make all the code that proceeds this line be not bad, dry it out, do not rely on constant string names, etc

    read_trace = generateTrace(data['read'], data['idents'])
    write_trace = generateTrace(data['write'], data['idents'])

    read_trace['diagonal'].update(visible=False)
    write_trace['diagonal'].update(visible=False)

    read_fig = Figure(data=[read_trace], layout=generateSharedLayout(read_title))
    write_fig = Figure(data=[write_trace], layout=generateSharedLayout(write_title))

    print('Aggregate data properties (all values should match):')
    print('energy values: r={};w={}'.format(len(data['read']['energy']), len(data['write']['energy'])))
    print('power values: r={};w={}'.format(len(data['read']['power']), len(data['write']['power'])))
    print('duration values: r={};w={}'.format(len(data['read']['duration']), len(data['write']['duration'])))
    print('security values: r={};w={}'.format(len(data['read']['security']), len(data['write']['security'])))
    print('flakesize values: r={};w={}'.format(len(data['read']['flakesize']), len(data['write']['flakesize'])))
    print('fpn values: r={};w={}'.format(len(data['read']['fpn']), len(data['write']['fpn'])))
    print('text values: {}'.format(len(data['idents'])))

    user_input = input('Look good? (y/N): ')
    if user_input != 'y':
        print('not continuing!')
        sys.exit(4)

    print('uploading...')

    print('{: <90} {}'.format(read_title,
        py.plot(
            read_fig,
            filename = '{}-reads-{}'.format(TEST_IDENT, hashlib.md5(bytes(filesdir + read_title, 'ascii')).hexdigest()),
            auto_open = False
        ))
    )

    print('{: <90} {}'.format(write_title,
        py.plot(
            write_fig,
            filename = '{}-writes-{}'.format(TEST_IDENT, hashlib.md5(bytes(filesdir + write_title, 'ascii')).hexdigest()),
            auto_open = False
        ))
    )

    print('done!')
