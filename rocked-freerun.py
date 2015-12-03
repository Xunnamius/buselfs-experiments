#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder

import os
import sys
import hashlib
import plotly.plotly as py
from plotly.graph_objs import *

OPS = 10000*2

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
        # Power = energyTotal / test duration
        powerAverage = []

        joules = None
        duration = None

        with open('{}/shmoo.{}.{}.results'.format(filesdir, coreType, fsType), 'r') as lines:
            for currentLineNumber, currentLine in enumerate(lines):
                if currentLine.startswith('Joules'):
                    joules = float(currentLine.split(':')[1].strip())
                    energyTotal.append(joules)

                elif currentLine.strip().endswith('/s'): #in seconds
                    number = float(currentLine.split(' s,')[0].split(' ')[-1].strip())
                    if duration == None:
                        duration = number
                    else:
                        duration += number

                elif currentLine.startswith('mf'):
                    configurations.append(currentLine.split(':')[1].strip())
                    powerAverage.append(joules / duration)
                    duration = None

        assert len(energyTotal) == len(configurations) == len(powerAverage)

        # print('Energy Total: ', energyTotal)
        # print('Configurations: ', configurations)

        scattersEnergy_DE.append(Scatter(
            x=[fsType.upper()] * len(energyTotal), y=energyTotal,
            mode='markers',
            name=coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12)
        ))

        scattersPower_DE.append(Scatter(
            x=[fsType.upper()] * len(powerAverage), y=powerAverage,
            mode='markers',
            name=coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12)
        ))

        frequencies = [x.split(' ')[1] for x in configurations]

        scattersEnergy_configs.append(Scatter(
            x=frequencies, y=energyTotal,
            mode='markers',
            name=fsType.upper() + ' ' + coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12)
        ))

        scattersPower_configs.append(Scatter(
            x=frequencies, y=powerAverage,
            mode='markers',
            name=fsType.upper() + ' ' + coreType.upper() + ' cores',
            text=configurations,
            marker=Marker(size=12)
        ))

print('Uploading...')

enerAESEnergyDE = Figure(
    data = Data(scattersEnergy_DE),
    layout = Layout(
        title='{} (N)FDE vs Total Energy over {} iops'.format(filesdir, OPS),
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Energy (joules)')
    )
)

enerAESPowerDE = Figure(
    data = Data(scattersPower_DE),
    layout = Layout(
        title='{} (N)FDE vs Average Power over {} iops'.format(filesdir, OPS),
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Power (joules/s)')
    )
)

enerAESEnergyConfigs = Figure(
    data = Data(scattersEnergy_configs),
    layout = Layout(
        title='{} Frequency Sweeep vs Total Energy over {} iops'.format(filesdir, OPS),
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Energy (joules)')
    )
)

enerAESPowerConfigs = Figure(
    data = Data(scattersPower_configs),
    layout = Layout(
        title='{} Frequency Sweeep vs Average Power over {} iops'.format(filesdir, OPS),
        xaxis1 = XAxis(title='Disk Encryption'),
        yaxis1 = YAxis(title='Power (joules/s)')
    )
)

hsh = hashlib.md5(bytes(filesdir, "ascii")).hexdigest()
print(py.plot(enerAESEnergyDE, filename='energy-AESXTS-EvsDE-' + hsh, auto_open=False))
print(py.plot(enerAESPowerDE, filename='energy-AESXTS-PvsDE-' + hsh, auto_open=False))
print(py.plot(enerAESEnergyConfigs, filename='energy-AESXTS-EvsCnf-' + hsh, auto_open=False))
print(py.plot(enerAESPowerConfigs, filename='energy-AESXTS-PvsCnf-' + hsh, auto_open=False))
print('done')
