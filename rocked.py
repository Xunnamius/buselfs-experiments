#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder

import plotly.plotly as py
from plotly.graph_objs import *

################################################################################

DURATION = 30
scatters = []

for fsType in ['fde', 'nfde']:
    for coreType in ['big', 'little']:
        # Total energy used
        energyTotal = []
        # Mask + Freq
        configurations = []

        beginCountingSamples = False
        samples = []

        with open('results/shmoo.{}.{}.results'.format(coreType, fsType), 'r') as lines:
            for currentLineNumber, currentLine in enumerate(lines):
                if currentLine.startswith('Results'):
                    assert beginCountingSamples != True

                    beginCountingSamples = True
                    samples = []

                elif beginCountingSamples:
                    if currentLine.startswith('Samples'):
                        assert beginCountingSamples == True
                        assert len(samples) >= DURATION + 1

                        beginCountingSamples = False
                        energyTotal.append(sum(samples[-(DURATION+1):-1])) # Take the last (+ 1) 10 samples

                    else:
                        samples.append(float(currentLine.strip()))

                elif currentLine.startswith('mf'):
                    configurations.append(currentLine.split(':')[1].strip())

        assert len(energyTotal) == len(configurations)

        # print('Energy Total: ', energyTotal)
        # print('Configurations: ', configurations)

        scatters.append(Scatter(
            x=[fsType.upper()] * len(energyTotal), y=energyTotal,
            mode='markers',
            name=coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12)
        ))

print('Uploading...')

enerAEStrade = Figure(
    data = Data(scatters),
    layout = Layout(
        title='Is It Worth It?',
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Energy (joules)')
    )
)

print(py.plot(enerAEStrade, filename='energy-AESXTS-worthit', auto_open=False))
print('done')
