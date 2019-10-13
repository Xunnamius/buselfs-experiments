"""A small test script for libcruncher. Be sure to call it with `python -m`!"""

# * Call it like this:
# * python -m libcruncher 2018/07-15--054851--flknug -xf flakesize=8192 fpn=128 iops=1k medium=ram order=sequential filesystem=f2fs isBaseline=False backstore="strongbox" cipher="sc_chacha20_neon"
# * python -m libcruncher 2019/2019-10-12--122214--overhead+vsr--odroid2 -nf order=sequential_freerun_wcs,sequential_freerun

import sys
import libcruncher
import json

def printFilter(filters, indent=2):
    retval = '['

    for fltr in (filters or []):
        retval += '\n{}{}={},'.format(' ' * indent, fltr.name, fltr.value)

    retval = '{}{}]'.format(retval.strip(','), '\n' if filters else '')

    return retval

print('<libcruncher library is running in test mode>')

execProps = libcruncher.argsToExecutionProperties(sys.argv[1:])

print('resultFiles (count):', len(execProps.resultFileProps))
print('observeBaseline:', execProps.observeBaseline)
print('normalizeResults:', execProps.normalize)
print('filterStrict:', execProps.filterStrict)
print('filterPropsList: ', end='')
print(printFilter(execProps.filterPropsList, indent=2), '\n')
print('first and last results:\n')
print(json.dumps(execProps.resultFileProps[0]._asdict(), sort_keys=True, indent=2, default=str), '\n')
print(json.dumps(execProps.resultFileProps[-1]._asdict(), sort_keys=True, indent=2, default=str))
