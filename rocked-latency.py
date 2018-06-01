#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder

import os
import sys
import hashlib
import plotly.plotly as py
from plotly.graph_objs import *

DURATION = 30

################################################################################

scatters = []

filesdir = None

if len(sys.argv) != 2:
        print('Usage: {} <data directory>'.format(sys.argv[0]))
        sys.exit(1)
else:
    filesdir = sys.argv[1].strip('/')
    if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
        print('{} does not exist or is not a directory.'.format(filesdir))
        sys.exit(1)

for fsType in ['fde', 'nfde']:
    for coreType in ['big', 'little']:
        latencies = []
        # Mask + Freq
        configurations = []

        with open('{}/shmoo.{}.{}.results'.format(filesdir, coreType, fsType), 'r') as lines:
            for currentLineNumber, currentLine in enumerate(lines):
                if currentLine.strip().endswith('latency'):
                    latencies.append(currentLine.split(' ')[-2].strip('ms'))

                elif currentLine.startswith('mf'):
                    configurations.append(currentLine.split(':')[1].strip())

        assert len(latencies) == len(configurations)

        scatters.append(Scatter(
            x=[x.split(' ')[1] for x in configurations], y=latencies,
            mode='markers',
            name=coreType.upper() + ' ' + fsType.upper(),
            text=configurations
        ))

print('Uploading...')

enerAES = Figure(
    data = Data(scatters),
    layout = Layout(
        title='{} (latency over {} seconds)'.format(filesdir, DURATION),
        xaxis1 = XAxis(title='Configurations'),
        yaxis1 = YAxis(title='Latency (average ms/op)')
    )
)

print(py.plot(enerAES, filename='energy-AESXTS-latencies-' + hashlib.md5(bytes(filesdir, "ascii")).hexdigest(), auto_open=False))
print('done')
