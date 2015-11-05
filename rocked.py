#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.results file in the results folder

import plotly.plotly as py
from plotly.graph_objs import *

INVOCATION_ITERATIONS = 64000

################################################################################

scatters = []

for coreType in ['big', 'little']:
    # Round input to the KDF
    hashesS = []
    # Average pow
    powerAvg = []
    # Mask + Freq
    configurations = []

    with open('results/shmoo.{}.results'.format(coreType), 'r') as lines:
        for currentLineNumber, currentLine in enumerate(lines):
            # Watch out for ValueError recoveries
            if currentLine.startswith('Pavg'):
                powerAvg.append(float(currentLine.split(' ')[1].strip()))

            elif currentLine.startswith('generated'):
                hashesS.append(int(currentLine.split(' ')[1].strip()))

            elif currentLine.startswith('mf'):
                configurations.append(currentLine.split(':')[1].strip())

    if not (len(hashesS) == len(powerAvg) == len(configurations)):
        print('Error: length check mismatch (wtf?)')
        exit(1)

    scatters.append(Scatter(
        x=hashesS, y=powerAvg,
        mode='markers',
        name=coreType.upper() + ' cores',
        text=configurations,
        marker=Marker(size=12)
    ))

print('Uploading...')

enersectrade = Figure(
    data = Data(scatters),
    layout = Layout(
        title='Tradeoff?',
        xaxis1 = XAxis(title='Hashes/s'),
        yaxis1 = YAxis(title='Power (Average)')
    )
)

print(py.plot(enersectrade, filename='energy-security-tradeoff', auto_open=False))
print('done')
