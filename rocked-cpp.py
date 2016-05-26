#!/usr/bin/env python3
"""This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder"""

import os
import sys
import hashlib
from statistics import median
import plotly.plotly as py
from plotly.graph_objs import Scatter, Figure, Data, Layout, XAxis, YAxis, Marker

OPS = 25000*2
TRIALS = 20
GHZ = 1000000

CORE_TYPES = ['big', 'little']
FS_TYPES = ['fde', 'nfde']
TITLE_TEMPLATE = '{} {} {} [{} iops {} trials]'

################################################################################

def createDefaultScatterInstance(x, y, name, text):
    return Scatter(
        x=x, y=y,
        mode='markers',
        name=name,
        text=text,
        marker=Marker(size=12)
    )

def uploadAndPrint(scatterData, title, xaxis, yaxis, hsh):
    print('{: <90} {}'.format(title,
        py.plot(
            Figure(
                data = Data(scatterData),
                layout = Layout(
                    title=title,
                    xaxis1 = XAxis(title='{}'.format(xaxis)),
                    yaxis1 = YAxis(title='{}'.format(yaxis))
            )),
            filename='energy-AESXTS1-cpp-' + hsh,
            auto_open=False
    )))

def lineToNumber(line):
    """Converts a line string like "energy: 55" into a number"""
    return float(line.split(': ')[1])

if __name__ == "__main__":
    filesdir   = None
    maskFilter = None

    if 2 >= len(sys.argv) <= 3:
        print('Usage: {} <data directory> [<mask hex>]'.format(sys.argv[0]))
        print('If no mask is specified, all masks will be included')
        sys.exit(1)
    else:
        filesdir   = sys.argv[1].strip('/')
        maskFilter = sys.argv[2] if len(sys.argv) == 3 else None
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

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]

    # Compile the data into charts/graphs and throw it online
    for scatterKey, scatterData in holisticDatastore['aggregate']['scatters'].items():
        title = TITLE_TEMPLATE.format(titlePrefix, scatterData['xTitle'], scatterData['yTitle'], OPS, TRIALS)
        uploadAndPrint(
            scatterData['data'],
            title,
            scatterData['xAxisTitle'].format('see mask' if maskFilter is None else maskFilter),
            scatterData['yAxisTitle'],
            hashlib.md5(bytes(filesdir + scatterKey + title, "ascii")).hexdigest()
        )

    print('done!')
