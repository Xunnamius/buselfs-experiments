"""Utility objects for use with the libcruncher library"""

import hashlib

from collections import namedtuple
import plotly.graph_objects as go

# 0 = least secure, 3 = most secure
SC_SECURITY_RANKING = {
    'sc_chacha8_neon': 0.5,
    'sc_chacha12_neon': 1.0,
    'sc_chacha20_neon': 1.5,
    'sc_chacha20': 1.5,
    'sc_salsa8': 0.4,
    'sc_salsa12': 0.9,
    'sc_salsa20': 1.4,
    'sc_aes128_ctr': 0.5,
    'sc_aes256_ctr': 1.5,
    'sc_hc128': 0.5,
    'sc_rabbit': 1.4,
    'sc_sosemanuk': 1.4,
    'sc_freestyle_fast': 2,
    'sc_freestyle_balanced': 2.5,
    'sc_freestyle_secure': 3,
    'sc_aes256_xts': 1.7,
}

DEFAULT_CIPHER_IDENT = 'sc_chacha20'
DEFAULT_FLAKESIZE = 4096
DEFAULT_FPN = 64
DEFAULT_STRATEGY = 'swap_disabled'

COLORS_A = ['rgb(49,130,189)', 'rgb(204,204,204)', 'rgb(255,102,0)']
COLORS_B = ['rgb(25,65,95)', 'rgb(102,102,102)', 'rgb(255,102,0)']

ResultProperties = namedtuple('ResultProperties', [
    'path',
    'name',
    'order',
    'medium',
    'iops',
    'backstore',
    'filesystem',
    'cipher',
    'flakesize',
    'fpn',
    'isBaseline',
    'swapCipher',
    'swapStrategy',
    'swapRatio'
])

ResultProperty = namedtuple('ResultProperty', ['name', 'value'])
ExecutionProperties = namedtuple('ExecutionProperties', [
    'resultFileProps',
    'baselineFileProps',
    'observeBaseline',
    'filterPropsList',
    'filterStrict',
    'filterCurveStrict'
])

def generateTitleFrag(filters):
    title_frag = ''
    filters = filters or []

    for fltr in filters:
        title_frag += '{}={},'.format(fltr.name, fltr.value.replace(',', '|'))

    return title_frag.strip(',')

def stringToValidFilename(string):
    return string.replace('|', '!').replace(':', '!').replace('/', '').replace('\\', '')

def formatAndPlotFigure(file_ident, test_ident, trace, title, filesdir, axisCount, specialAxes={}):
    figure = go.Figure(data=[trace], layout=generateSharedLayout(title, axisCount, specialAxes))
    filename = '{}/{}-{}-{}{}'.format(
        filesdir,
        test_ident,
        file_ident,
        hashlib.md5(bytes(filesdir + title, 'ascii')).hexdigest(),
        '.png'
    )

    figure.write_image(filename)#, scale=None, width=None, height=None)

def generateSharedLayout(title, axisCount, specialAxes={}):
    axis = {
        'showline': True,
        'zeroline': False,
        'gridcolor': '#fff',
        'ticklen': 4,
    }

    layout = go.Layout(
        dragmode='select',
        hovermode='closest',
        title=title,
        margin={ 'b': 160 },
        #width=600,
        #height=600,
        #autosize=False,
        plot_bgcolor='rgba(240,240,240, 0.95)',
    )

    for i in range(1, axisCount + 1):
        for letter in ('x', 'y'):
            layout['{}axis{}'.format(letter, i)] = { **axis, **specialAxes[i] } if i in specialAxes else axis

    return layout
