#!/usr/bin/env python3

import sys
import numpy as np
from statistics import mean

overhead_numbers = []

if __name__ == "__main__":
    data = np.genfromtxt(sys.argv[1], names=True, dtype=None)
    latdata = data['latency']
    lendata = len(latdata)
    offset = 0
    overhead = { '4k': { 'r': [], 'w': [] }, '40m': { 'r': [], 'w': [] } }

    print('saw {} values'.format(lendata))
    assert lendata % 17 == 0

    while offset < lendata:
        overhead_c8_c20 = max(0, (latdata[offset + 2]  - (latdata[offset] + latdata[offset + 4]) / 2) / latdata[offset + 2])
        overhead_c20_ff = max(0, (latdata[offset + 6]  - (latdata[offset + 4] + latdata[offset + 8]) / 2) / latdata[offset + 6])
        overhead_ff_fb  = max(0, (latdata[offset + 10] - (latdata[offset + 8] + latdata[offset + 12]) / 2) / latdata[offset + 10])
        overhead_fb_fs  = max(0, (latdata[offset + 14] - (latdata[offset + 12] + latdata[offset + 16]) / 2) / latdata[offset + 14])

        order = ''
        if 'order' in data.dtype.names:
            order = data['order'][offset]

        strategy = ''
        if 'strategy' in data.dtype.names:
            strategy = data['strategy'][offset]

        # overhead_numbers.append({
        #     'iop': data['iop'][offset],
        #     'order': data['order'][offset],
        #     'overhead': (overhead_c8_c20, overhead_c20_ff, overhead_ff_fb, overhead_fb_fs)
        # })

        if strategy == b'mirrored':
            print('[SKIPPED] ')

        print('{}-{}: c8c20={:.2f}x c20ff={:.2f}x fffb={:.2f}x fbfs={:.2f}x'.format(
            order, data['iop'][offset], overhead_c8_c20, overhead_c20_ff, overhead_ff_fb, overhead_fb_fs
        ))

        if strategy == b'mirrored':
            continue

        if data['iop'][offset].startswith(b'4k'):
            if data['iop'][offset].endswith(b'r'):
                overhead['4k']['r'].extend([overhead_c8_c20, overhead_c20_ff, overhead_ff_fb, overhead_fb_fs])
            if data['iop'][offset].endswith(b'w'):
                overhead['4k']['w'].extend([overhead_c8_c20, overhead_c20_ff, overhead_ff_fb, overhead_fb_fs])

        else:
            if data['iop'][offset].endswith(b'r'):
                overhead['40m']['r'].extend([overhead_c8_c20, overhead_c20_ff, overhead_ff_fb, overhead_fb_fs])
            if data['iop'][offset].endswith(b'w'):
                overhead['40m']['w'].extend([overhead_c8_c20, overhead_c20_ff, overhead_ff_fb, overhead_fb_fs])

        offset = offset + 17

    print('max4k-r={:.2f}\nmin4k-r={:.2f}\nmean4k-r={:.2f}\nmax40m-r={:.2f}\nmin40m-r={:.2f}\nmean40m-r={:.2f}\nmax4k-w={:.2f}\nmin4k-w={:.2f}\nmean4k-w={:.2f}\nmax40m-w={:.2f}\nmin40m-w={:.2f}\nmean40m-w={:.2f}'.format(
        max(overhead['4k']['r']), min(overhead['4k']['r']), mean(overhead['4k']['r']),
        max(overhead['40m']['r']), min(overhead['40m']['r']), mean(overhead['40m']['r']),
        max(overhead['4k']['w']), min(overhead['4k']['w']), mean(overhead['4k']['w']),
        max(overhead['40m']['w']), min(overhead['40m']['w']), mean(overhead['40m']['w'])
    ))
