#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.results file in the results folder

import os
import sys
import hashlib
import statistics
import copy
import plotly.plotly as py
from plotly.graph_objs import *

TRIALS = 3
INNER_TRIALS = 50
GHZ = 1000000

CORE_TYPES = ['big', 'big']
#CORE_TYPES = ['big', 'little']
CRYPT_TYPES = ['encrypt', 'decrypt']
ALGORITHMS = ['AES-CTR', 'AES-GCM', 'AES-CBC', 'ChaCha20', 'ChaCha20-Poly1305']
TITLE_TEMPLATE = '{} [{}] {} over {} trials ({} inner trials)'
# i.e. 54326543543 Encryption Energy over 3 trials (50 inner trials)

dataStruts = {
    'configurations': [],
    'energyTotal': [],
    'powerAverage': [],
    'durationAverage': []
}

aggregateStruts = {
    CRYPT_TYPES[0] + 'RATIOconfigsVSenergy': {
        'xTitle': 'Frequency Sweep',
        'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
        'yTitle': 'Total Energy Ratio',
        'yAxisTitle': 'FDE/NFDE Energy (joules)',
        'data': []
    },
    
    CRYPT_TYPES[0] + 'RATIOconfigsVSpower': {
        'xTitle': 'Frequency Sweep',
        'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
        'yTitle': 'Average Power Ratio',
        'yAxisTitle': 'FDE/NFDE Power (joules/s)',
        'data': []
    },
    
    CRYPT_TYPES[0] + 'RATIOconfigsVStime': {
        'xTitle': 'Frequency Sweep',
        'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
        'yTitle': 'Average Duration Ratio',
        'yAxisTitle': 'FDE/NFDE Duration (seconds)',
        'data': []
    },

    CRYPT_TYPES[1] + 'RATIOconfigsVSenergy': {
        'xTitle': 'Frequency Sweep',
        'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
        'yTitle': 'Total Energy Ratio',
        'yAxisTitle': 'FDE/NFDE Energy (joules)',
        'data': []
    },
    
    CRYPT_TYPES[1] + 'RATIOconfigsVSpower': {
        'xTitle': 'Frequency Sweep',
        'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
        'yTitle': 'Average Power Ratio',
        'yAxisTitle': 'FDE/NFDE Power (joules/s)',
        'data': []
    },
    
    CRYPT_TYPES[1] + 'RATIOconfigsVStime': {
        'xTitle': 'Frequency Sweep',
        'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
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
    print('{: <90} {}'.format(title,
        py.plot(
            Figure(
                data = Data(scatterData),
                layout = Layout(
                    title=title,
                    xaxis1 = XAxis(title='{}'.format(xaxis)),
                    yaxis1 = YAxis(title='{}'.format(yaxis))
            )),
            filename='energy-AESXTS1-endecomp-' + hsh,
            auto_open=False
    )))

def generateDicts():
    joules = {}
    duration = {}

    for cryptType in CRYPT_TYPES:
        joules[cryptType] = {}
        duration[cryptType] = {}

        for algo in ALGORITHMS:
            joules[cryptType][algo] = []
            duration[cryptType][algo] = []

    return joules, duration

if __name__ == "__main__":
    filesdir   = None
    maskFilter = None
    holisticDatastore = { 'aggregate': { 'scatters': aggregateStruts } }

    if len(sys.argv) < 2 or len(sys.argv) > 3:
            print('Usage: {} <data directory> [<mask hex>]'.format(sys.argv[0]))
            print('If no mask is specified, all masks will be included'.format(sys.argv[0]))
            sys.exit(1)
    else:
        filesdir   = sys.argv[1].strip('/')
        maskFilter = sys.argv[2] if len(sys.argv) == 3 else None
        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(1)

    print('crunching...')

    # Create the data structures that will house our data
    for coreType in CORE_TYPES:
        holisticDatastore[coreType] = {}

        for cryptType in CRYPT_TYPES:
            holisticDatastore[coreType][cryptType] = {}

            for algo in ALGORITHMS:
                holisticDatastore[coreType][cryptType][algo] = copy.deepcopy(dataStruts)
    
    # Loop over results and begin the aggregation/accumulation process
    for coreType in CORE_TYPES:
        data = holisticDatastore[coreType]

        joules, duration = generateDicts()
        cryptType = None
        algo = None

        with open('{}/shmoo.{}.results'.format(filesdir, coreType), 'r') as lines:
            for currentLineNumber, currentLine in enumerate(lines):
                if currentLine.startswith('beginning trial'):
                    algo, cryptType = currentLine.strip().split('(')[1][:-1].split(',')[1].strip().split(' ')

                elif currentLine.startswith('Joules'):
                    joules[cryptType][algo].append(float(currentLine.split(':')[1].strip()))

                elif currentLine.startswith('Samples'): #as seconds
                    duration[cryptType][algo].append(float(currentLine.split(':')[1].strip()))

                elif currentLine.startswith('mf'): # the assimilation step
                    if maskFilter is None or maskFilter in currentLine:
                        for cryptTypeActual in CRYPT_TYPES:
                            for algoActual in ALGORITHMS:
                                joulesActual = statistics.median(joules[cryptTypeActual][algoActual])
                                durationActual = statistics.median(duration[cryptTypeActual][algoActual])

                                data[cryptType][algo]['configurations'].append(currentLine.split(':')[1].strip())
                                data[cryptType][algo]['energyTotal'].append(joulesActual)
                                data[cryptType][algo]['durationAverage'].append(durationActual)
                                data[cryptType][algo]['powerAverage'].append(joulesActual / durationActual) # there is some error introduced here (via resolution)

                    joules, duration = generateDicts()
                    cryptType = None
                    algo = None

    rawFrequencies = [conf.split(' ') for conf in holisticDatastore[CORE_TYPES[0]][CRYPT_TYPES[0]][ALGORITHMS[0]]['configurations']]
    frequencies = [int(raw[1]) / GHZ for raw in rawFrequencies]
    niceConfigurations = ['{}Ghz (mask: {})'.format(int(raw[1]) / GHZ, raw[0]) for raw in rawFrequencies]

    createRatio = lambda a, b: [rat[0]/rat[1] for rat in zip(a, b)]
    cdsi = lambda y, name: createDefaultScatterInstance(frequencies, y, name, niceConfigurations)
    
    # XXX: create more holistic scatter instances and add them to their proper datastores right here!
    for cryptType in CRYPT_TYPES:
        for algo in ALGORITHMS:
            dFrag = holisticDatastore

            energyRatios = createRatio(dFrag[CORE_TYPES[0]][cryptType][algo]['energyTotal'], dFrag[CORE_TYPES[1]][cryptType][algo]['energyTotal'])
            powerRatios = createRatio(dFrag[CORE_TYPES[0]][cryptType][algo]['powerAverage'], dFrag[CORE_TYPES[1]][cryptType][algo]['powerAverage'])
            durationRatios = createRatio(dFrag[CORE_TYPES[0]][cryptType][algo]['durationAverage'], dFrag[CORE_TYPES[1]][cryptType][algo]['durationAverage'])

            holisticDatastore['aggregate']['scatters'][cryptType + 'RATIOconfigsVSenergy']['data'].append(cdsi(energyRatios, algo))
            holisticDatastore['aggregate']['scatters'][cryptType + 'RATIOconfigsVSpower']['data'].append(cdsi(powerRatios, algo))
            holisticDatastore['aggregate']['scatters'][cryptType + 'RATIOconfigsVStime']['data'].append(cdsi(durationRatios, algo))

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]

    # Handle the global "cross-set" datasets
    for scatterKey, scatterData in holisticDatastore['aggregate']['scatters'].items():
        title = TITLE_TEMPLATE.format(titlePrefix, scatterKey.split('RATIO')[0].upper(), scatterData['yTitle'], TRIALS, INNER_TRIALS)
        uploadAndPrint(
            scatterData['data'],
            title,
            scatterData['xAxisTitle'].format('see mask' if maskFilter is None else maskFilter),
            scatterData['yAxisTitle'],
            hashlib.md5(bytes(filesdir + scatterKey + title, "ascii")).hexdigest()
        )

    print('done!')
