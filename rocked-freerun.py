#!/usr/bin/env python3

"""This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder"""

import os
import sys
import hashlib
import statistics
import copy
import pprint
import plotly.plotly as py
from plotly.graph_objs import Scatter, Figure, Data, Layout, Marker, XAxis, YAxis, Bar

OPS = 20000*2
TRIALS = None # set to None if trial counts are variable
GHZ = 1000000

#CORE_TYPES = ['big', 'little']
CORE_TYPES = ['big']
#FS_TYPES = ["kernel", "fuse+ext4", "fuse+lfs", "kernel+aesxts", "fuse+lfs+aesxts", "fuse+lfs+chacha+poly"]
FS_TYPES = ['1-kext4-normal', '3-kext4+fuse-ext4', '4-kext4+dmc+fuse-ext4', '5-kext4+fuse-lfs']
COLORS = ['rgb(49,130,189)', 'rgb(204,204,204)', 'rgb(255,102,0)']
TITLE_TEMPLATE = '{} {} vs {} over {} iops {} trials'

dataStruts = {
    'frequencies': [],
    'configurations': [],
    'niceConfigurations': [],
    'energyTotal': [],
    'powerAverage': [],
    'durationAverage': []
}

################################################################################
def createDefaultTraceInstance(x, y, name, text, color=None):
    """Creates a default graph object instance"""
    # return Scatter(
    #     x=x, y=y,
    #     mode='markers',
    #     name=name,
    #     text=text,
    #     marker=Marker(size=12)
    # )
    trace = Bar(
        x=x, y=y,
        name=name,
        text=text
    )

    if color is not None:
        trace.marker = dict( color=color )

    return trace

def uploadAndPrint(innerScatterData, innerTitle, xaxis, yaxis, hsh):
    """Uploads the data to the web and returns a printout of URLS"""
    print('{: <90} {}'.format(innerTitle,
        py.plot(
            Figure(
                data = Data(innerScatterData),
                layout = Layout(
                    title = innerTitle,
                    xaxis1 = XAxis(title='{}'.format(xaxis)),
                    yaxis1 = YAxis(title='{}'.format(yaxis))
            )),
            filename='energy-AESXTS1-autograph-' + hsh,
            auto_open=False
    )))

if __name__ == "__main__":
    filesdir   = None
    maskFilter = None
    holisticDatastore = {}

    if len(sys.argv) < 2 or len(sys.argv) > 3:
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

    # Create the data structures that will house our data
    for coreType in CORE_TYPES:
        holisticDatastore[coreType] = {}
        for fsType in FS_TYPES:
            holisticDatastore[coreType][fsType] = { 'data': copy.deepcopy(dataStruts) }

    # Loop over results and begin the aggregation/accumulation process
    for coreType in CORE_TYPES:
        for fsType in FS_TYPES:
            data = holisticDatastore[coreType][fsType]['data']

            joules = []
            duration = []
            durationFlag = True

            def assimilationStep(currentLine):
                """The final step in the process for reading results files"""
                assert TRIALS is None or len(joules) == len(duration) == TRIALS
                assert durationFlag

                currentLineActual = currentLine.split(':')[1].strip() if currentLine is not None else 0

                if maskFilter is None or currentLine is None or maskFilter in currentLine:
                    joulesActual = statistics.median(joules)
                    durationActual = statistics.median(duration)

                    data['configurations'].append(currentLineActual)
                    data['energyTotal'].append(joulesActual)
                    data['durationAverage'].append(durationActual)
                    data['powerAverage'].append(joulesActual / durationActual) # there is some error introduced here (via resolution)

                joules.clear()
                duration.clear()

            # Data can be in any order, so watch out for that!
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
                        assimilationStep(currentLine)

            if len(joules) or len(duration):
                assimilationStep(None) # Seems someone has shittily-formatted data...

            assert len(data['energyTotal']) == len(data['configurations']) == len(data['powerAverage'])

            # rawFrequencies = [conf.split(' ') for conf in data['configurations']]
            # data['frequencies'] = [int(raw[1]) / GHZ for raw in rawFrequencies]
            # data['niceConfigurations'] = ['{}Ghz (mask: {})'.format(int(raw[1]) / GHZ, raw[0]) for raw in rawFrequencies]

            # cdsi = lambda x, y, name: createDefaultTraceInstance(x, y, name, data['niceConfigurations'])

            # XXX: create new scatter instances and add them to their proper datastores here
            # newX = [fsType.upper()] * len(data['energyTotal'])
            # newName = coreType.upper() + ' cores'

            # holisticDatastore[coreType][fsType]['scatters']['fstypeVSenergy'].append(cdsi(newX, data['energyTotal'], newName))
            # holisticDatastore[coreType][fsType]['scatters']['fstypeVSpower'].append(cdsi(newX, data['powerAverage'], newName))

            # newName = fsType.upper() + ' ' + coreType.upper() + ' cores'

            # holisticDatastore[coreType][fsType]['scatters']['configsVSenergy'].append(cdsi(data['frequencies'], data['energyTotal'], newName))
            # holisticDatastore[coreType][fsType]['scatters']['configsVSpower'].append(cdsi(data['frequencies'], data['powerAverage'], newName))
            # holisticDatastore[coreType][fsType]['scatters']['configsVStime'].append(cdsi(data['frequencies'], data['durationAverage'], newName))

    # createRatio = lambda a, b: [rat[0]/rat[1] for rat in zip(a, b)]
    # cdsi = lambda y, name: createDefaultTraceInstance(
    #     holisticDatastore[CORE_TYPES[0]][FS_TYPES[0]]['data']['frequencies'],
    #     y,
    #     name,
    #     holisticDatastore[CORE_TYPES[0]][FS_TYPES[0]]['data']['niceConfigurations']
    # )

    # XXX: create more holistic scatter instances and add them to their proper datastores right here!
    # for coreType in CORE_TYPES:
    #     dataFragment = holisticDatastore[coreType]
    #     energyRatios = createRatio(dataFragment[FS_TYPES[0]]['data']['energyTotal'], dataFragment[FS_TYPES[1]]['data']['energyTotal'])
    #     powerRatios = createRatio(dataFragment[FS_TYPES[0]]['data']['powerAverage'], dataFragment[FS_TYPES[1]]['data']['powerAverage'])
    #     durationRatios = createRatio(dataFragment[FS_TYPES[0]]['data']['durationAverage'], dataFragment[FS_TYPES[1]]['data']['durationAverage'])

    #     newName = coreType.upper() + ' cores'

    #     holisticDatastore['aggregate']['scatters']['RATIOconfigsVSenergy']['data'].append(cdsi(energyRatios, newName))
    #     holisticDatastore['aggregate']['scatters']['RATIOconfigsVSpower']['data'].append(cdsi(powerRatios, newName))
    #     holisticDatastore['aggregate']['scatters']['RATIOconfigsVStime']['data'].append(cdsi(durationRatios, newName))

    # XXX: create new trace instances and do what needs doing to construct the bar chart
    cdsi = lambda x, y, name, color: createDefaultTraceInstance(x, y, name, None, color)
    newX = [fsType.upper()] * len(data['energyTotal'])
    titlePrefix = filesdir.strip('/').split('/')[-1]
    title = TITLE_TEMPLATE.format(titlePrefix, 'FS', 'Energy', OPS, '(variable)')

    # x = FS_TYPES
    y0 = []
    y1 = []
    y2 = []

    for coreType in CORE_TYPES:
        coreFragment = holisticDatastore[coreType]
        
        for fs in FS_TYPES:
            fsData = coreFragment[fs]['data']

            y0.append(fsData['energyTotal'][0])
            y1.append(fsData['powerAverage'][0])
            y2.append(fsData['durationAverage'][0])

    traces = [
        cdsi(FS_TYPES, y0, 'Energy', COLORS[0]),
        cdsi(FS_TYPES, y1, 'Power', COLORS[1]),
        cdsi(FS_TYPES, y2, 'Duration', COLORS[2])
    ]

    layout = Layout(
        xaxis = dict(
            # set x-axis' labels direction at 45 degree angle
            tickangle = -5,
            title = 'Filesystems'
        ),
        yaxis = dict( title='Energy (j, j/s)' ),
        barmode = 'group',
        title = title
    )

    fig = Figure(data=traces, layout=layout)

    pprint.PrettyPrinter(indent=4).pprint(holisticDatastore)
    print('~~~~~')
    pprint.PrettyPrinter(indent=4).pprint(traces)

    user_input = input('Look good? (y/N): ')
    if user_input == 'y':
        print("Let's do this.")
    else:
        print('Not continuing!')
        sys.exit(1)

    print('uploading...')

    print('{: <90} {}'.format(title,
        py.plot(
            fig,
            filename='energy-AESXTS1-autograph-' + hashlib.md5(bytes(filesdir + title, 'ascii')).hexdigest(),
            auto_open=False
        ))
    )

    # titlePrefix = filesdir.strip('/').split('/')[-1]
    # accumulated = {}

    # # Accumulate all of the disparate datasets
    # for coreType in CORE_TYPES:
    #     for fsType in FS_TYPES:
    #         for scatterKey, scatterData in holisticDatastore[coreType][fsType]['scatters'].items():
    #             if scatterKey not in accumulated:
    #                 accumulated[scatterKey] = []
    #             accumulated[scatterKey].extend(scatterData)

    # trialsActual = 'variable' if TRIALS is None else TRIALS

    # # Loop again, this time dealing with the accumulated Scatter instances
    # for strutKey, strutData in scattersStruts.items():
    #     title = TITLE_TEMPLATE.format(titlePrefix, strutData['xTitle'], strutData['yTitle'], OPS, trialsActual)
    #     uploadAndPrint(
    #         accumulated[strutKey],
    #         title,
    #         strutData['xAxisTitle'].format('see mask' if maskFilter is None else maskFilter),
    #         strutData['yAxisTitle'],
    #         hashlib.md5(bytes(filesdir + strutKey + title, "ascii")).hexdigest()
    #     )

    # One final loop: handle the global "cross-set" datasets
    # for scatterKey, scatterData in holisticDatastore['aggregate']['scatters'].items():
    #     title = TITLE_TEMPLATE.format(titlePrefix, scatterData['xTitle'], scatterData['yTitle'], OPS, trialsActual)
    #     uploadAndPrint(
    #         scatterData['data'],
    #         title,
    #         scatterData['xAxisTitle'].format('see mask' if maskFilter is None else maskFilter),
    #         scatterData['yAxisTitle'],
    #         hashlib.md5(bytes(filesdir + scatterKey + title, "ascii")).hexdigest()
    #     )
    
    print('done!')
