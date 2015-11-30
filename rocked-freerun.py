#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder

import os
import sys
import plotly.plotly as py
from plotly.graph_objs import *

################################################################################

scattersEnergy_DE = []
scattersEnergy_configs = []
scattersPower_DE = []
scattersPower_configs = []

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
        # Total energy used
        energyTotal = []
        # Mask + Freq
        configurations = []
        # Power = energyTotal / DURATION
        powerAverage = []

        beginCountingSamples = False
        samples = []
        joules = 0

        with open('{}/shmoo.{}.{}.results'.format(filesdir, coreType, fsType), 'r') as lines:
            for currentLineNumber, currentLine in enumerate(lines):
                if currentLine.startswith('Results'):
                    assert beginCountingSamples != True

                    beginCountingSamples = True
                    samples = []
                    joules = 0

                elif beginCountingSamples:
                    if currentLine.startswith('Samples'):
                        assert beginCountingSamples == True
                        assert len(samples) >= DURATION + 1

                        beginCountingSamples = False
                        joules = sum(samples[-(DURATION+1):-1])
                        energyTotal.append(joules) # Take the last (+ 1) DURATION samples
                        powerAverage.append(joules / DURATION)

                    else:
                        samples.append(float(currentLine.strip()))

                elif currentLine.startswith('mf'):
                    configurations.append(currentLine.split(':')[1].strip())

        assert len(energyTotal) == len(configurations)

        # print('Energy Total: ', energyTotal)
        # print('Configurations: ', configurations)

        scattersEnergy_DE.append(Scatter(
            x=[fsType.upper()] * len(energyTotal), y=energyTotal,
            mode='markers',
            name=coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12, color=('orange' if fsType == 'big' else 'blue'))
        ))

        scattersPower_DE.append(Scatter(
            x=[fsType.upper()] * len(energyTotal), y=powerAverage,
            mode='markers',
            name=coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12, color=('orange' if fsType == 'big' else 'blue'))
        ))

print('Uploading...')

enerAESEnergyDE = Figure(
    data = Data(scattersEnergy_DE),
    layout = Layout(
        title='(N)FDE vs Total Energy over 30 seconds',
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Energy (joules)')
    )
)

enerAESPowerDE = Figure(
    data = Data(scattersEnergy_DE),
    layout = Layout(
        title='Is It Worth It?',
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Energy (joules)')
    )
)

print(py.plot(enerAESEnergyDE, filename='energy-AESXTS-EvsDE', auto_open=False))
print(py.plot(enerAESPowerDE, filename='energy-AESXTS-PvsDE', auto_open=False))
print(py.plot(enerAESEnergyDE, filename='energy-AESXTS-EvsCnf', auto_open=False))
print(py.plot(enerAESPowerDE, filename='energy-AESXTS-PvsCnf', auto_open=False))
print('done')
