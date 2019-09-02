#!/usr/bin/env python3

RUNNER_LOG_PATH = '/tmp/runner.log'

if __name__ == "__main__":
    with open(RUNNER_LOG_PATH, 'r') as lines:
        for currentLine in lines:
            if currentLine.find('got start time (ns):'):
                withinInterestingRegion = True
            if currentLine.find('got end time (ns):'):
                withinInterestingRegion = True
