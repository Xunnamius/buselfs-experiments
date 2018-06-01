#!/usr/bin/env python3
# pylint: disable=E0202
"""This script crunches the shmoo.<CORETYPE>.<FSTYPE>.results file in the results folder"""

import os
import sys
import hashlib
import pprint
import copy
from decimal import Decimal
from statistics import median
from plotly.graph_objs import Bar, Figure, Layout, Box
import plotly.plotly as py

PREFIX_STR = '12800000'
CORE = 'big'
TYPES = ['fde', 'nfde']
TITLE_TEMPLATE = '{} RD vs SSD Median IO Duration Comparison'

################################################################################

def createDefaultTraceInstance(x, y, name, text, color=None):
    """Creates a default graph object instance"""
    trace = Bar(
        x=x, y=y,
        name=name,
        text=text
    )

    if color is not None:
        trace.marker = dict( color=color )

    return trace

def lineToNumber(line):
    """Converts a line string like "12800000 bytes (13 MB) copied, 5.80098 s, 2.2 MB/s"""
    return Decimal(line.split(', ')[1][:-1].strip())

if __name__ == "__main__":
    filesdirRD = None
    filesdirSSD = None

    # TODO: Use the more advanced python opts API
    if len(sys.argv) != 3:
        print('Usage: {} <data directory rd> <data directory ssd>'.format(sys.argv[0]))
        sys.exit(1)

    else:
        filesdirRD  = sys.argv[1].strip('/')
        filesdirSSD = sys.argv[2].strip('/')

    print('result files directory RD: {}'.format(filesdirRD))
    print('result files directory SSD: {}'.format(filesdirSSD))

    print('crunching...')

    data = {
        'rd': {
            'fde-r': [],
            'fde-w': [],
            'nfde-r': [],
            'nfde-w': []
        },
        'ssd': {
            'fde-r': [],
            'fde-w': [],
            'nfde-r': [],
            'nfde-w': []
        }
    }

    # Loop over results and begin the aggregation/accumulation process
    for fdir in ((filesdirRD, 'rd'), (filesdirSSD, 'ssd')):
        for typ in TYPES:
            with open('{}/shmoo.{}.{}.results'.format(fdir[0], CORE, typ), 'r') as lines:
                io = 'w'
                for currentLine in lines:
                    if currentLine.startswith(PREFIX_STR):
                        data[fdir[1]][typ+'-'+io].append(lineToNumber(currentLine))
                        io = 'r' if io == 'w' else 'w'

                assert io == 'w'

    for fdir in ('rd', 'ssd'):
        for typ in TYPES:
            for io in ('r', 'w'):
                data[fdir][typ+'-'+io] = median(data[fdir][typ+'-'+io])

    print("""
rd-fde:
    read: {}
    write: {}

ssd-fde:
    read: {}
    write: {}

~{:.2}x read slowdown
~{:.2}x write slowdown

rd-nfde:
    read: {}
    write: {}

ssd-nfde:
    read: {}
    write: {}

~{:.2}x read slowdown
~{:.2}x write slowdown""".format(
    data['rd']['fde-r'],
    data['rd']['fde-w'],
    data['ssd']['fde-r'],
    data['ssd']['fde-w'],
    data['ssd']['fde-r']/data['rd']['fde-r'],
    data['ssd']['fde-w']/data['rd']['fde-w'],
    data['rd']['nfde-r'],
    data['rd']['nfde-w'],
    data['ssd']['nfde-r'],
    data['ssd']['nfde-w'],
    data['ssd']['nfde-r']/data['rd']['nfde-r'],
    data['ssd']['nfde-w']/data['rd']['nfde-w']
))

    print('\ndone!')
