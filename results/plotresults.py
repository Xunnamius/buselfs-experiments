#!/usr/bin/env python3

# pylint: disable=E0202

"""
This is the 2/7/2017 version of the script that script crunches any files that
ends with the extension "result" and are direct children of the /results folder.
"""

import os
import sys
import hashlib
import pprint
import copy
from pathlib import Path
from decimal import Decimal
from statistics import median
from plotly.graph_objs import Bar, Figure, Layout, Box
import plotly.plotly as py

OPS = 25000 * 2
GHZ = 1000000

METRICS = ('energy', 'power', 'duration')
COLORS_READ = ['rgb(49,130,189)', 'rgb(204,204,204)', 'rgb(255,102,0)']
COLORS_WRITE = ['rgb(25,65,95)', 'rgb(102,102,102)', 'rgb(255,102,0)']
TITLE_TEMPLATE = '{} <{}> FS Measurements [{} iops {} trials]'

CONFIG_PATH = "{}/../config/vars.mk".format(os.path.dirname(os.path.realpath(__file__)))
CONFIG_KEY = "CONFIG_COMPILE_FLAGS"
PRINT_CONFIG = True
CONFIG = {}

################################################################################

def parseConfigLine(configLine):
    lhs_rhs = ''.join(configLine.split(' \\')[0].split('-D')[1:]).split('=')
    rhs = ''.join(lhs_rhs[1:]).strip('"\' ')
    lhs = lhs_rhs[0].strip(' ')
    
    return (lhs, rhs)

def parseConfigVars():
    with open(CONFIG_PATH, 'r') as varsFile:
        inConfigVar = False

        for line in varsFile:
            if line.startswith(CONFIG_KEY):
                inConfigVar = True
                continue
            
            if inConfigVar:
                line = line.strip('\n')
                if not line.endswith("\\"):
                    inConfigVar = False
                
                (varName, varValue) = parseConfigLine(line)
                CONFIG[varName] = int(varValue) if varName.endswith('_INT') else varValue

def createDefaultTraceInstance(x, y, name, text, color=None):
    """Creates a default graph object instance"""
    trace = Bar(
        x = x, y = y,
        name = name,
        text = text
    )

    if color is not None:
        trace.marker = dict(color = color)

    return trace

def lineToNumber(line):
    """Converts a line string like "energy: 55" into a number"""
    return Decimal(line.split(': ')[1])

def filenameToProperName(filename):
    return "".join(filename.split('.results')[0].split('shmoo.big.'))

if __name__ == "__main__":
    parseConfigVars()

    if PRINT_CONFIG:
        print(CONFIG)

    filesdir = None
    durationBaseline = None

    # TODO: Use the more advanced python opts API
    if len(sys.argv) != 2 and len(sys.argv) != 4:
        print('Usage: {} [-d baseline] <data directory>'.format(sys.argv[0]))
        print('"-d" enables duration mode (results will only deal with duration ratios)')
        print('When using -d, you must follow it with a number that will be the index starting at 0 of the baseline result file in fs order')
        sys.exit(1)

    else:
        filesdir = sys.argv[1].strip('/')

        if len(sys.argv) == 4 and sys.argv[1] == '-d':
            filesdir = sys.argv[3].strip('/')
            durationBaseline = int(sys.argv[2])

        if not os.path.exists(filesdir) or not os.path.isdir(filesdir):
            print('{} does not exist or is not a directory.'.format(filesdir))
            sys.exit(1)

    print('result files directory: {}'.format(filesdir))
    print('duration baseline: {}'.format(durationBaseline))

    print('crunching...')

    data = {}
    resultFiles = sorted([pth for pth in Path(os.path.dirname(os.path.realpath(__file__))).glob(os.path.join(filesdir, '*.results'))])
    resultFileNames = [filenameToProperName(file.name) for file in resultFiles]

    # Loop over results and begin the aggregation/accumulation process
    for resultFile in resultFiles:
        resultFileName = filenameToProperName(resultFile.name)

        data[resultFileName] = {
            'read' : { 'energy': [], 'power': [], 'duration': [] },
            'write': { 'energy': [], 'power': [], 'duration': [] }
        }

        dataFragment = data[resultFileName]

        with open(resultFile.absolute().as_posix(), 'r') as lines:
            for currentLine in lines:
                for metric in METRICS:
                    # We're dealing with read metrics...
                    if currentLine.startswith('r_' + metric):
                        dataFragment['read'][metric].append(lineToNumber(currentLine))
                        break

                    # We're dealing with read metrics...
                    elif currentLine.startswith('w_' + metric):
                        dataFragment['write'][metric].append(lineToNumber(currentLine))
                        break

                    # These are technically comments/blank lines and are ignored
                    elif currentLine.startswith('---') or len(currentLine.strip()) == 0 or currentLine.startswith('mf'):
                        break
                else:
                    print('Bad data at read/write distinction: "{}"'.format(currentLine))
                    raise 'Bad data at read/write distinction (see above)'

        for metric in METRICS:
            dataFragment['read'][metric]  = median(dataFragment['read'][metric])
            dataFragment['write'][metric] = median(dataFragment['write'][metric])

        dataFragment['read']['energy'] /= 1000000
        dataFragment['read']['duration'] /= 1000000000

        dataFragment['write']['energy'] /= 1000000
        dataFragment['write']['duration'] /= 1000000000

        # Sometimes we can't trust the power we read!
        dataFragment['read']['power'] = dataFragment['read']['energy'] / dataFragment['read']['duration']
        dataFragment['write']['power'] = dataFragment['write']['energy'] / dataFragment['write']['duration']

    if durationBaseline is not None:
        baselineFragment = copy.deepcopy(data[resultFileNames[durationBaseline]])

        for resultFileName in resultFileNames:
            dataFragment = data[resultFileName]

            for metric in METRICS:
                dataFragment['read'][metric] = round(dataFragment['read'][metric] / baselineFragment['read'][metric], 1)
                dataFragment['write'][metric] = round(dataFragment['write'][metric] / baselineFragment['write'][metric], 1)

    print('uploading...')

    titlePrefix = filesdir.strip('/').split('/')[-1]

    # TODO: Compact this into a function or
    read_title = TITLE_TEMPLATE.format(titlePrefix, 'reads', OPS, CONFIG['TRIALS_INT']) + (' (duration ratios)' if durationBaseline is not None else '')
    write_title = TITLE_TEMPLATE.format(titlePrefix, 'writes', OPS, CONFIG['TRIALS_INT']) + (' (duration ratios)' if durationBaseline is not None else '')

    # XXX: create new trace instances and do what needs doing to construct the bar chart
    cdsi = lambda x, y, name, color: createDefaultTraceInstance(x, y, name, None, color)

    # Compile the data into charts/graphs and throw it online

    # x = result file names
    y0_reads  = []
    y1_reads  = []
    y2_reads  = []
    y0_writes = []
    y1_writes = []
    y2_writes = []

    for resultFileName in sorted(resultFileNames):
        dataFragment = data[resultFileName]

        y0_reads.append(float(dataFragment['read']['energy']))
        y1_reads.append(float(dataFragment['read']['power']))
        y2_reads.append(float(dataFragment['read']['duration']))

        y0_writes.append(float(dataFragment['write']['energy']))
        y1_writes.append(float(dataFragment['write']['power']))
        y2_writes.append(float(dataFragment['write']['duration']))

    # TODO: Compact these next two conditional clauses into nice functions/for loops!
    if durationBaseline is not None:
        read_traces = [
            cdsi(resultFileNames, y2_reads, 'Duration', COLORS_READ[2]),
        ]

        read_layout = Layout(
            xaxis = dict(
                # set x-axis' labels direction at 45 degree angle
                tickangle = 50,
                title = 'Filesystems'
            ),
            yaxis = dict(title = 'Duration Ratio (seconds in respect to 1x baseline)', autorange = True, side = 'left'),
            title = read_title,
            margin = dict(b = 160)
        )

        write_traces = [
            cdsi(resultFileNames, y2_writes, 'Duration', COLORS_WRITE[2]),
        ]

        write_layout = Layout(
            xaxis = dict(
                # set x-axis' labels direction at 45 degree angle
                tickangle = 50,
                title = 'Filesystems'
            ),
            yaxis = dict(title = 'Duration Ratio (seconds in respect to 1x baseline)', autorange = True, side = 'left'),
            title = write_title,
            margin = dict(b = 160)
        )

    else:
        read_traces = [
            cdsi(resultFileNames, y0_reads, 'Energy', COLORS_READ[0]),
            cdsi(resultFileNames, y1_reads, 'Power', COLORS_READ[1]),
            Box(
                x = resultFileNames, y = y2_reads,
                name = 'Duration',
                fillcolor = COLORS_READ[2],
                line = dict(color = COLORS_READ[2]),
                yaxis = 'y2'
            )
        ]

        read_layout = Layout(
            xaxis = dict(
                # set x-axis' labels direction at 45 degree angle
                tickangle = 50,
                title = 'Filesystems'
            ),
            yaxis = dict(title = 'Energy (j), Power (j/s)', autorange = False, range = [0, 30], side = 'left'),
            yaxis2 = dict(title = 'Duration (seconds)', autorange = False, range = [0, 20], side = 'right', gridwidth = 2.5, overlaying = 'y'),
            barmode = 'group',
            title = read_title,
            margin = dict(b = 160)
        )

        write_traces = [
            cdsi(resultFileNames, y0_writes, 'Energy', COLORS_WRITE[0]),
            cdsi(resultFileNames, y1_writes, 'Power', COLORS_WRITE[1]),
            Box(
                x = resultFileNames, y = y2_writes,
                name = 'Duration',
                fillcolor = COLORS_WRITE[2],
                line = dict(color = COLORS_WRITE[2]),
                yaxis = 'y2'
            )
        ]

        write_layout = Layout(
            xaxis = dict(
                # set x-axis' labels direction at 45 degree angle
                tickangle = 50,
                title = 'Filesystems'
            ),
            yaxis = dict(title = 'Energy (j), Power (j/s)', autorange = False, range = [0, 30], side = 'left'),
            yaxis2 = dict(title = 'Duration (seconds)', autorange = False, range = [0, 20], side = 'right', gridwidth = 2.5, overlaying = 'y'),
            barmode = 'group',
            title = write_title,
            margin = dict(b = 160)
        )

    read_fig = Figure(data = read_traces, layout = read_layout)
    write_fig = Figure(data = write_traces, layout = write_layout)

    print('~~~~~DATA~~~~~')
    pprint.PrettyPrinter(indent = 4).pprint(data)
    print('~~~~~READ~~~~~')
    pprint.PrettyPrinter(indent = 4).pprint(read_traces)
    print('~~~~~WRITE~~~~~')
    pprint.PrettyPrinter(indent = 4).pprint(write_traces)

    user_input = input('Look good? (y/N): ')
    if user_input != 'y':
        print('not continuing!')
        sys.exit(1)

    print('uploading...')

    print('{: <90} {}'.format(read_title,
        py.plot(
            read_fig,
            filename = 'energy-AESXTS1-cppgraph-reads-' + hashlib.md5(bytes(filesdir + read_title, 'ascii')).hexdigest(),
            auto_open = False
        ))
    )

    print('{: <90} {}'.format(write_title,
        py.plot(
            write_fig,
            filename = 'energy-AESXTS1-cppgraph-writes-' + hashlib.md5(bytes(filesdir + write_title, 'ascii')).hexdigest(),
            auto_open = False
        ))
    )

    print('done!')
