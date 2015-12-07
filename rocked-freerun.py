#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder

import os
import sys
import hashlib
import statistics
import plotly.plotly as py
from plotly.graph_objs import *

OPS = 25000*2
TRIALS = 10
MHZ = 1000000

CORE_TYPES = ['big', 'little']
FS_TYPES = ['fde', 'nfde']
TITLE_TEMPLATE = '{} {} vs {} over {} iops {} trials'

dataStruts = {
    'frequencies': [],
    'configurations': [],
    'niceConfigurations': [],
    'energyTotal': [],
    'powerAverage': [],
    'durationAverage': []
}

scattersStruts = {
    'fstypeVSenergy': {
        'xTitle': '(N)FDE',
        'xAxisTitle': 'Disk Encryption',
        'yTitle': 'Total Energy',
        'yAxisTitle': 'Energy (joules)'
    },

    'fstypeVSpower': {
        'xTitle': '(N)FDE',
        'xAxisTitle': 'Disk Encryption',
        'yTitle': 'Average Power',
        'yAxisTitle': 'Power (joules/s)'
    },
    
    'configsVSenergy': {
        'xTitle': 'Frequency Sweeep',
        'xAxisTitle': 'Frequency Configurations (Mhz) [ see mask ]',
        'yTitle': 'Total Energy',
        'yAxisTitle': 'Energy (joules)'
    },
    
    'configsVSpower': {
        'xTitle': 'Frequency Sweeep',
        'xAxisTitle': 'Frequency Configurations (Mhz) [ see mask ]',
        'yTitle': 'Average Power',
        'yAxisTitle': 'Power (joules/s)'
    },
    
    'configsVStime': {
        'xTitle': 'Frequency Sweeep',
        'xAxisTitle': 'Frequency Configurations (Mhz) [ see mask ]',
        'yTitle': 'Average Duration',
        'yAxisTitle': 'Duration (seconds)'
    }
}

aggregateStruts = {
    'RATIOconfigsVSenergy': {
        'xTitle': 'Frequency Sweeep',
        'xAxisTitle': 'Frequency Configurations (Mhz) [ see mask ]',
        'yTitle': 'Total Energy Ratio',
        'yAxisTitle': 'FDE/NFDE Energy (joules)',
        'data': []
    },
    
    'RATIOconfigsVSpower': {
        'xTitle': 'Frequency Sweeep',
        'xAxisTitle': 'Frequency Configurations (Mhz) [ see mask ]',
        'yTitle': 'Average Power Ratio',
        'yAxisTitle': 'FDE/NFDE Power (joules/s)',
        'data': []
    },
    
    'RATIOconfigsVStime': {
        'xTitle': 'Frequency Sweeep',
        'xAxisTitle': 'Frequency Configurations (Mhz) [ see mask ]',
        'yTitle': 'Average Duration Ratio',
        'yAxisTitle': 'FDE/NFDE Duration (seconds)',
        'data': []
    }
}

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
    print(title, '\t\t\t\t',
        py.plot(
            Figure(
                data = Data(scatterData),
                layout = Layout(
                    title=title,
                    xaxis1 = XAxis(title='{}'.format(xaxis)),
                    yaxis1 = YAxis(title='{}'.format(yaxis))
            )),
            filename='energy-AESXTS1-autograph-' + hsh,
            auto_open=False
    ))

if __name__ == "__main__":
    filesdir = None
    holisticDatastore = { 'aggregate': { 'scatters': aggregateStruts } }

    if len(sys.argv) != 2:
            print('Usage: {} <data directory>'.format(sys.argv[0]))
            sys.exit(1)
    else:
        filesdir = sys.argv[1].strip('/')
        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(1)

    print('crunching...')

    # Create the data structures that will house our data
    for coreType in CORE_TYPES:
        holisticDatastore[coreType] = {}
        for fsType in FS_TYPES:
            holisticDatastore[coreType][fsType] = { 'data': dataStruts, 'scatters': {} }

            for key in scattersStruts:
                holisticDatastore[coreType][fsType]['scatters'][key] = { 'data': [] }

    # Loop over results and begin the aggregation/accumulation process
    for coreType in CORE_TYPES:
        for fsType in FS_TYPES:
            data = holisticDatastore[coreType][fsType]['data']

            joules = []
            duration = []
            durationFlag = True

            with open('{}/shmoo.{}.{}.results'.format(filesdir, coreType, fsType), 'r') as lines:
                for currentLineNumber, currentLine in enumerate(lines):
                    if currentLine.startswith('Joules'):
                        joules.append(float(currentLine.split(':')[1].strip()))

                    elif currentLine.strip().endswith('/s'): #in seconds
                        number = float(currentLine.split(' s,')[0].split(' ')[-1].strip())

                        if durationFlag:
                            duration.append(number)
                        else:
                            duration[-1] += number

                        durationFlag = not durationFlag

                    elif currentLine.startswith('mf'): # the assimilation step
                        assert len(joules) == len(duration) == TRIALS

                        joulesActual = statistics.median(joules)
                        durationActual = statistics.median(duration)

                        data['configurations'].append(currentLine.split(':')[1].strip())
                        data['energyTotal'].append(joulesActual)
                        data['durationAverage'].append(durationActual)
                        data['powerAverage'].append(joulesActual / durationActual) # there is some error introduced here (via resolution)

                        joules = []
                        duration = []
                        durationFlag = True

            assert len(data['energyTotal']) == len(data['configurations']) == len(data['powerAverage'])

            rawFrequencies = [conf.split(' ') for conf in data['configurations']]
            data['frequencies'] = [int(raw[1]) / MHZ for raw in rawFrequencies]
            data['niceConfigurations'] = ['{}Mhz (mask: {})'.format(int(raw[1]) / MHZ, raw[0]) for raw in rawFrequencies]

            cdsi = lambda x, y, name: createDefaultScatterInstance(x, y, name, data['niceConfigurations'])

            # XXX: create new scatter instances and add them to their proper datastores here
            newX = [fsType.upper()] * len(data['energyTotal'])
            newName = coreType.upper() + ' cores'

            holisticDatastore[coreType][fsType]['scatters']['fstypeVSenergy']['data'].append(cdsi(newX, data['energyTotal'], newName))
            holisticDatastore[coreType][fsType]['scatters']['fstypeVSpower']['data'].append(cdsi(newX, data['powerAverage'], newName))

            newName = fsType.upper() + ' ' + coreType.upper() + ' cores'

            holisticDatastore[coreType][fsType]['scatters']['configsVSenergy']['data'].append(cdsi(data['frequencies'], data['energyTotal'], newName))
            holisticDatastore[coreType][fsType]['scatters']['configsVSpower']['data'].append(cdsi(data['frequencies'], data['powerAverage'], newName))
            holisticDatastore[coreType][fsType]['scatters']['configsVStime']['data'].append(cdsi(data['frequencies'], data['durationAverage'], newName))

    createRatio = lambda a, b: [rat[0]/rat[1] for rat in zip(a, b)]
    cdsi = lambda y, name: createDefaultScatterInstance(
        holisticDatastore[CORE_TYPES[0]][FS_TYPES[0]]['data']['frequencies'],
        y,
        name,
        holisticDatastore[CORE_TYPES[0]][FS_TYPES[0]]['data']['niceConfigurations']
    )
    
    # XXX: create more holistic scatter instances and add them to their proper datastores right here!
    for coreType in CORE_TYPES:
        dataFragment = holisticDatastore[coreType]
        energyRatios = createRatio(dataFragment[FS_TYPES[0]]['data']['energyTotal'], dataFragment[FS_TYPES[1]]['data']['energyTotal'])
        powerRatios = createRatio(dataFragment[FS_TYPES[0]]['data']['powerAverage'], dataFragment[FS_TYPES[1]]['data']['powerAverage'])
        durationRatios = createRatio(dataFragment[FS_TYPES[0]]['data']['durationAverage'], dataFragment[FS_TYPES[1]]['data']['durationAverage'])

        newName = coreType.upper() + ' cores'

        holisticDatastore['aggregate']['scatters']['RATIOconfigsVSenergy']['data'].append(cdsi(energyRatios, newName))
        holisticDatastore['aggregate']['scatters']['RATIOconfigsVSpower']['data'].append(cdsi(powerRatios, newName))
        holisticDatastore['aggregate']['scatters']['RATIOconfigsVStime']['data'].append(cdsi(durationRatios, newName))

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]
    accumulated = {}

    # Accumulate all of the disparate datasets
    for coreType in CORE_TYPES:
        for fsType in FS_TYPES:
            for scatterKey, scatterData in holisticDatastore[coreType][fsType]['scatters'].items():
                if scatterKey not in accumulated:
                    accumulated[scatterKey] = []
                accumulated[scatterKey].extend(scatterData['data'])

    # Loop again, this time dealing with the accumulated Scatter instances
    for strutKey, strutData in scattersStruts.items():
        title = TITLE_TEMPLATE.format(titlePrefix, strutData['xTitle'], strutData['yTitle'], OPS, TRIALS)
        uploadAndPrint(
            accumulated[strutKey],
            title,
            strutData['xAxisTitle'],
            strutData['yAxisTitle'],
            hashlib.md5(bytes(filesdir + strutKey + title, "ascii")).hexdigest()
        )

    # One final loop: handle the global "cross-set" datasets
    for scatterKey, scatterData in holisticDatastore['aggregate']['scatters'].items():
        title = TITLE_TEMPLATE.format(titlePrefix, scatterData['xTitle'], scatterData['yTitle'], OPS, TRIALS)
        uploadAndPrint(
            scatterData,
            title,
            scatterData['xAxisTitle'],
            scatterData['yAxisTitle'],
            hashlib.md5(bytes(filesdir + scatterKey + title, "ascii")).hexdigest()
        )

    print('done!')
