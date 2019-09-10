#!/usr/bin/env python3

RUNNER_LOG_PATH = '/tmp/runner.log'

withinInterestingRegion = False
interestingRegions = []

if __name__ == "__main__":
    with open(RUNNER_LOG_PATH, 'r') as lines:
        for currentLine in lines:
            if 'got start time (ns)' in currentLine:
                withinInterestingRegion = True
                interestingRegionName = currentLine[0:currentLine.index('METRICS') - 1]
                interestingRegions.append({ 'name': interestingRegionName, 'requestBytes': 0, 'otherBytes': 0, 'swapped': False })
            elif 'got end time (ns)' in currentLine:
                withinInterestingRegion = False
            elif withinInterestingRegion and 'Request for' in currentLine:
                interestingRegion = interestingRegions[-1]
                if ('write' in currentLine and 'WRITE' in interestingRegion['name'] or
                    'read' in currentLine and 'READ' in interestingRegion['name']):
                    interestingRegion['requestBytes'] += int(currentLine.split()[-1])
                else:
                    interestingRegion['otherBytes'] += int(currentLine.split()[-1])
            elif 'Write was successful' in currentLine:
                interestingRegions[-1]['swapped'] = True

    for region in interestingRegions:
        print('Region: {} has {} MB ({} bytes, {} ignored bytes)'.format(
            region['name'],
            round(region['requestBytes']/1024/1024, 1),
            region['requestBytes'],
            region['otherBytes']
        ))

        if region['swapped']:
            print('(swapped!)')
