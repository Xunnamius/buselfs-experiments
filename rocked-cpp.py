#!/usr/bin/env python3
"""This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder"""

import os
import sys
import hashlib
import pprint
from decimal import Decimal
from statistics import median
from plotly.graph_objs import Bar, Figure, Layout
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
    #'07-rdext4-normal',
    #'08-rdext4-fuse-ext4',
    #'09-rdext4-fuse-ext4-dmc',
    #'10-rdext4-dmc-fuse-ext4',
    #'11-rdext4-fuse-lfs',
    #'12-rdext4-fuse-lfs-chacha-poly'
]

COLORS = ['rgb(49,130,189)', 'rgb(204,204,204)', 'rgb(255,102,0)']
TITLE_TEMPLATE = '{} FS Energy Measurements [{} iops {} trials]'

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
    filesdir   = None

    if len(sys.argv) != 2:
        print('Usage: {} <data directory>'.format(sys.argv[0]))
        sys.exit(1)
    else:
        filesdir = sys.argv[1].strip('/')

        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(1)

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

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]
    title = TITLE_TEMPLATE.format(titlePrefix, OPS, TRIALS)

    # XXX: create new trace instances and do what needs doing to construct the bar chart
    cdsi = lambda x, y, name, color: createDefaultTraceInstance(x, y, name, None, color)

    # Compile the data into charts/graphs and throw it online

    # x = FS_TYPES
    y0 = []
    y1 = []
    y2 = []

    for coreType in CORE_TYPES:
        coreFragment = data[coreType]

        for fs in FS_TYPES:
            fsFragment = coreFragment[fs]

            y0.append(fsFragment['energy'])
            y1.append(fsFragment['power'])
            y2.append(fsFragment['duration'])

    traces = [
        cdsi(FS_TYPES, y0, 'Energy', COLORS[0]),
        cdsi(FS_TYPES, y1, 'Power', COLORS[1]),
        cdsi(FS_TYPES, y2, 'Duration', COLORS[2])
    ]

    layout = Layout(
        xaxis = dict(
            # set x-axis' labels direction at 45 degree angle
            tickangle = -5,
            title = 'Filesystems'
        ),
        yaxis = dict( title='Energy (j, j/s)' ),
        barmode = 'group',
        title = title
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
