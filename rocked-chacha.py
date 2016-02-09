#!/usr/bin/env python3

# This script crunches the shmoo.<CORETYPE>.results file in the results folder

import os
import sys
import hashlib
import statistics
import copy
import pprint
import plotly.plotly as py
from plotly.graph_objs import *

TRIALS = 3
INNER_TRIALS = 50
GHZ = 1000000

CORE_TYPES = ['big', 'little']
CRYPT_TYPES = ['encrypt', 'decrypt']
ALGORITHMS = ['AES-CTR', 'AES-GCM', 'AES-CBC', 'ChaCha20', 'ChaCha20-Poly1305']
DIMENSIONS = ['energy', 'power', 'time']
TITLE_TEMPLATE = '{} [{} {}] {} over {} trials ({} inner trials)'
# i.e. 54326543543 [LITTLE Encryption] Energy over 3 trials (50 inner trials)

scatterStruts = {
    'xTitle': 'Frequency Sweep',
    'xAxisTitle': 'Frequency Configurations (Ghz) [ {} ]',
    'y': {
        DIMENSIONS[0]: {
            'title': 'Total Energy',
            'axisTitle': 'Energy (joules)'
        },
        
        DIMENSIONS[1]: {
            'title': 'Average Power',
            'axisTitle': 'Power (joules/s)'
        },

        DIMENSIONS[2]: {
            'title': 'Average Duration',
            'axisTitle': 'Duration (seconds)'
        }
    }
}

################################################################################

def createDefaultScatterInstance(x, y, name, text):
    return Scatter(
        x=x, y=y,
        mode='markers',
        name=name,
        text=text
        # marker=Marker(size=12)
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
    holisticDatastore = {}

    if len(sys.argv) < 2 or len(sys.argv) > 3:
            print('Usage: {} <data directory>'.format(sys.argv[0]))
            sys.exit(1)
    else:
        filesdir   = sys.argv[1].strip('/')
        maskFilter = sys.argv[2] if len(sys.argv) == 3 else None
        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(1)

    print('crunching...')

    configurations = set()

    # Create the data structures that will house our data
    for coreType in CORE_TYPES:
        holisticDatastore[coreType] = {}

        for cryptType in CRYPT_TYPES:
            holisticDatastore[coreType][cryptType] = {}

            for dimension in DIMENSIONS:
                holisticDatastore[coreType][cryptType][dimension] = {}

                for algo in ALGORITHMS:
                    holisticDatastore[coreType][cryptType][dimension][algo] = []
    
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

                                configurations.add(currentLine.split(':')[1].strip())
                                data[cryptTypeActual][DIMENSIONS[0]][algoActual].append(joulesActual)
                                data[cryptTypeActual][DIMENSIONS[2]][algoActual].append(durationActual)
                                data[cryptTypeActual][DIMENSIONS[1]][algoActual].append(joulesActual / durationActual) # there is some error introduced here (via resolution)

                    joules, duration = generateDicts()
                    cryptType = None
                    algo = None

    #pprint.pprint(holisticDatastore[CORE_TYPES[0]])
    
    rawFrequencies = [conf.split(' ') for conf in configurations]
    frequencies = [int(raw[1]) / GHZ for raw in rawFrequencies]
    niceConfigurations = ['{}Ghz (mask: {})'.format(int(raw[1]) / GHZ, raw[0]) for raw in rawFrequencies]

    cdsi = lambda y, name: createDefaultScatterInstance(frequencies, y, name, niceConfigurations)
    accumulated = {}
    
    # Create scatter instances and accumulate them
    for coreType in CORE_TYPES:
        for cryptType in CRYPT_TYPES:
            for dimension in DIMENSIONS:
                for algo in ALGORITHMS:
                    data = holisticDatastore[coreType][cryptType][dimension][algo]
                    key  = ';'.join((coreType, cryptType, dimension))

                    # Accumulate on algo
                    if key not in accumulated:
                        accumulated[key] = []

                    accumulated[key].append(cdsi(data, algo))

    print('uploading...')
    #pprint.pprint(accumulated)
    
    titlePrefix = filesdir.strip('/').split('/')[-1]

    # Loop again, this time dealing with the accumulated Scatter instances
    for scatterKey, scatterData in accumulated.items():
        metadata  = scatterKey.split(';')
        coreType  = metadata[0]
        cryptType = metadata[1]
        dimension = metadata[2]
        yTitle    = scatterStruts['y'][dimension]['title']

        title = TITLE_TEMPLATE.format(
            titlePrefix,
            coreType.upper(),
            cryptType.capitalize(),
            yTitle,
            TRIALS,
            INNER_TRIALS
        )
        
        uploadAndPrint(
            scatterData,
            title,
            scatterStruts['xAxisTitle'].format('see mask' if maskFilter is None else maskFilter),
            scatterStruts['y'][dimension]['axisTitle'],
            hashlib.md5(bytes(filesdir + scatterKey + title, 'ascii')).hexdigest()
        )

    print('done!')
