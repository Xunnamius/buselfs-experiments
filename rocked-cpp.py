#!/usr/bin/env python3
# pylint: disable=E0202
"""This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder"""

import os
import sys
import hashlib
import pprint
import copy
from decimal import Decimal
from statistics import median
from plotly.graph_objs import Bar, Figure, Layout, Box
import plotly.plotly as py

OPS = 25000*2
TRIALS = 20
GHZ = 1000000

#CORE_TYPES = ['big', 'little']
CORE_TYPES = ['big']
FS_TYPES = [
    '01-kext4-normal',
    '02-kext4-fuse-ext4',
    '03-kext4-fuse-ext4-dmc',
    '04-kext4-dmc-fuse-ext4',
    #'05-kext4-fuse-lfs',
    #'06-kext4-fuse-lfs-chacha-poly',
    '07-rdext4-normal',
    '08-rdext4-fuse-ext4',
    '09-rdext4-fuse-ext4-dmc',
    '10-rdext4-dmc-fuse-ext4',
    #'11-rdext4-fuse-lfs',
    #'12-rdext4-fuse-lfs-chacha-poly'
]

COLORS = ['rgb(49,130,189)', 'rgb(204,204,204)', 'rgb(255,102,0)']
TITLE_TEMPLATE = '{} FS Measurements [{} iops {} trials]'

################################################################################

def createDefaultTraceInstance(x, y, name, text, color=None):
    """Creates a default graph object instance"""
    trace = Bar(
        x=x, y=y,
        name=name,
        text=text
    )

    if color is not None:
        trace.marker = dict( color=color )

    return trace

def lineToNumber(line):
    """Converts a line string like "energy: 55" into a number"""
    return Decimal(line.split(': ')[1])

if __name__ == "__main__":
    filesdir     = None
    durationBaseline = None

    # TODO: Use the more advanced python opts API
    if len(sys.argv) != 2 and len(sys.argv) != 4:
        print('Usage: {} [-d baseline] <data directory>'.format(sys.argv[0]))
        print('"-d" enables duration mode (results will only deal with duration ratios)')
        print('When using -d, you must follow it with a number that will be the index starting at 0 of the baseline FS_TYPE')
        sys.exit(1)

    else:
        filesdir = sys.argv[1].strip('/')

        if len(sys.argv) == 4 and sys.argv[1] == '-d':
            filesdir = sys.argv[3].strip('/')
            durationBaseline = int(sys.argv[2])

        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(1)

    print('result files directory: {}'.format(filesdir))
    print('duration baseline: {}'.format(durationBaseline))

    print('crunching...')

    data = {}

    # Create the data structures that will house our data
    for coreType in CORE_TYPES:
        data[coreType] = {}
        for fsType in FS_TYPES:
            data[coreType][fsType] = { 'energy': [], 'power': [], 'duration': [] }

    # Loop over results and begin the aggregation/accumulation process
    for coreType in CORE_TYPES:
        for fsType in FS_TYPES:
            dataFragment = data[coreType][fsType]

            with open('{}/shmoo.{}.{}.results'.format(filesdir, coreType, fsType), 'r') as lines:
                for currentLine in lines:
                    for metric in ('energy', 'power', 'duration'):
                        if currentLine.startswith(metric):
                            dataFragment[metric].append(lineToNumber(currentLine))
                            break

                for metric in ('energy', 'power', 'duration'):
                    dataFragment[metric] = median(dataFragment[metric])

                dataFragment['energy'] /= 1000000
                dataFragment['duration'] /= 1000000000

    if durationBaseline is not None:
        for coreType in CORE_TYPES:
            baselineFragment = copy.deepcopy(data[coreType][FS_TYPES[durationBaseline]])

            for fsType in FS_TYPES:
                dataFragment = data[coreType][fsType]

                dataFragment['energy'] = round(dataFragment['energy'] / baselineFragment['energy'], 1)
                dataFragment['power'] = round(dataFragment['power'] / baselineFragment['power'], 1)
                dataFragment['duration'] = round(dataFragment['duration'] / baselineFragment['duration'], 1)

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]
    title = TITLE_TEMPLATE.format(titlePrefix, OPS, TRIALS) + (' (duration ratios)' if durationBaseline is not None else '')

    # XXX: create new trace instances and do what needs doing to construct the bar chart
    cdsi = lambda x, y, name, color: createDefaultTraceInstance(x, y, name, None, color)

    # Compile the data into charts/graphs and throw it online

    # x = FS_TYPES
    y0 = []
    y1 = []
    y2 = []

    # TODO: This isn't going to work for multiple cores...
    for coreType in CORE_TYPES:
        coreFragment = data[coreType]

        for fs in FS_TYPES:
            fsFragment = coreFragment[fs]

            y0.append(float(fsFragment['energy']))
            y1.append(float(fsFragment['power']))
            y2.append(float(fsFragment['duration']))

    if durationBaseline is not None:
        traces = [
            cdsi(FS_TYPES, y2, 'Duration', COLORS[2]),
        ]

        layout = Layout(
            xaxis = dict(
                # set x-axis' labels direction at 45 degree angle
                tickangle = 50,
                title = 'Filesystems'
            ),
            yaxis = dict( title='Duration Ratio (seconds in respect to 1x baseline)', autorange=True, side='left' ),
            title = title,
            margin = dict( b=160 )
        )

    else:
        traces = [
            cdsi(FS_TYPES, y0, 'Energy', COLORS[0]),
            cdsi(FS_TYPES, y1, 'Power', COLORS[1]),
            Box(
                x=FS_TYPES, y=y2,
                name='Duration',
                fillcolor=COLORS[2],
                line=dict(color=COLORS[2]),
                yaxis='y2'
            )
        ]

        layout = Layout(
            xaxis = dict(
                # set x-axis' labels direction at 45 degree angle
                tickangle = 50,
                title = 'Filesystems'
            ),
            yaxis = dict( title='Energy (j), Power (j/s)', autorange=False, range=[0, 30], side='left' ),
            yaxis2 = dict( title='Duration (seconds)', autorange=False, range=[0, 20], side='right', gridwidth=2.5, overlaying='y' ),
            barmode = 'group',
            title = title,
            margin = dict( b=160 )
        )

    fig = Figure(data=traces, layout=layout)

    pprint.PrettyPrinter(indent=4).pprint(data)
    print('~~~~~')
    pprint.PrettyPrinter(indent=4).pprint(traces)

    user_input = input('Look good? (y/N): ')
    if user_input != 'y':
        print('not continuing!')
        sys.exit(1)

    print('uploading...')

    print('{: <90} {}'.format(title,
        py.plot(
            fig,
            filename='energy-AESXTS1-cppgraph-' + hashlib.md5(bytes(filesdir + title, 'ascii')).hexdigest(),
            auto_open=False
        ))
    )

    print('done!')
