#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.results file in the results folder

import plotly.plotly as py
from plotly.graph_objs import *

################################################################################

scatters = []

for coreType in ['big', 'little']:
    # Latency
    latency = []
    # Total energy used
    energyTotal = []
    # Mask + Freq
    configurations = []

    samples = None

    with open('results/shmoo.{}.results'.format(coreType), 'r') as lines:
        for currentLineNumber, currentLine in enumerate(lines):
            # Watch out for ValueError recoveries
            if currentLine.startswith('Samples'):
                samples = int(currentLine.split(' ')[1].strip())

            elif currentLine.startswith('Joules'):
                energyTotal.append(float(currentLine.split(' ')[1].strip()) / samples)
                samples = None

            elif currentLine.endswith('latency'):
                latency.append(float(currentLine.split(' ')[-2].strip()[:-2]))

            elif currentLine.startswith('mf'):
                configurations.append(currentLine.split(':')[1].strip())

    if not (len(latency) == len(energyTotal) == len(configurations)):
        print('Error: length check mismatch (wtf?)')
        exit(1)

    scatters.append(Scatter(
        x=latency, y=energyTotal,
        mode='markers',
        name=coreType.upper() + ' cores',
        text=configurations,
        marker=Marker(size=12)
    ))

print('Uploading...')

enerAEStrade = Figure(
    data = Data(scatters),
    layout = Layout(
        title='Worth It?',
        xaxis1 = XAxis(title='Latency (ms)'),
        yaxis1 = YAxis(title='Energy (joules/samples)')
    )
)

print(py.plot(enerAEStrade, filename='energy-AESXTS-worthit', auto_open=False))
print('done')
