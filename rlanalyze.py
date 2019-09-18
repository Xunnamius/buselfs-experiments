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
                interestingRegions.append({
                    'name': interestingRegionName,
                    'requestBytes': 0,
                    'requestOtherBytes': 0,
                    'committedBytes': 0,
                    'committedOtherBytes': 0,
                    'swapped': False
                })
            elif 'got end time (ns)' in currentLine:
                withinInterestingRegion = False
            elif withinInterestingRegion and 'Request for' in currentLine:
                interestingRegion = interestingRegions[-1]
                if ('write' in currentLine and 'WRITE' in interestingRegion['name'] or
                    'read' in currentLine and 'READ' in interestingRegion['name']):
                    interestingRegion['requestBytes'] += int(currentLine.split()[-1])
                else:
                    interestingRegion['requestOtherBytes'] += int(currentLine.split()[-1])
            elif withinInterestingRegion and 'Committed ' in currentLine:
                interestingRegion = interestingRegions[-1]
                if ('write' in currentLine and 'WRITE' in interestingRegion['name'] or
                    'read' in currentLine and 'READ' in interestingRegion['name']):
                    interestingRegion['committedBytes'] += int(currentLine.split()[-1])
                else:
                    interestingRegion['committedOtherBytes'] += int(currentLine.split()[-1])
            elif 'Write was successful' in currentLine:
                interestingRegions[-1]['swapped'] = True

    for region in interestingRegions:
        print('Region: {} has {}/{} MB req/com\n\t-> {}/{} MB other op\n\t-> {}/{} MB altogether'.format(
            region['name'],
            round(region['requestBytes']/1024/1024, 1),
            round(region['committedBytes']/1024/1024, 1),
            round(region['requestOtherBytes']/1024/1024, 1),
            round(region['committedOtherBytes']/1024/1024, 1),
            round((region['requestBytes'] + region['requestOtherBytes'])/1024/1024, 1),
            round((region['committedBytes'] + region['committedOtherBytes'])/1024/1024, 1)
        ))

        if region['swapped']:
            print('(then swapped after!)')
