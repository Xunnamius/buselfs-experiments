#!/usr/bin/env python3

# https://phoenixforge.cs.uchicago.edu/projects/seec-code/repository/revisions/283/entry/development/trunk/powerQoS/pyWattsup-hank.py

# updated to work with python 3

__author__ = """ Stelios Sidiroglou-Douskos <stelios@csail.mit.edu> """

import sys, os, signal, time, datetime
from optparse import OptionParser
import serial
import numpy

class WattsUp:
    def __init__(self, port, baudrate, verbose = False, repeat=False):
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=None)
        self.verbose = verbose
        self.repeat = repeat
        self.header = ""

    def readMsg(self):
        """
        returns a msg read by the serial port
        """
        msg = bytearray()

        while True:
            data = self.serial.read(1)
            #read until end of msg, which is denoted by ';'
            if data == b";":
                break
            msg.extend(data)
            
        return msg.decode('ascii')

    def writeMsg(self, msg):
        self.serial.write(bytes(msg, 'ascii'))
        self.serial.write(b'\r\n')
        self.serial.flush()

    def clearMemory(self):
        self.writeMsg("#R,W,0;")

    def getHeaders(self):
        self.writeMsg("#H,R,0;")
        reply = self.readMsg()
        self.header = reply

    def logExternal(self, interval):
        self.writeMsg("#L,W,3,E,0,1;")
        while self.repeat:
            print(self.readMsg())

    def logInternal(self, interval):
    #TODO: set interval
        self.writeMsg("#L,W,3,I,0,1;")
        reply = self.readMsg()
        if self.verbose:
            print("[!] Response for logInternal: {}".format(reply))

    def showSelectedRecordFields(self):
        self.writeMsg("#C,R,0;")
        reply = self.readMsg()

    def handler(self, signum, frame):
        print("Caught signal to terminate loop")
        self.repeat = False
        self.serial.close()

    def getCostParams(self):
        self.writeMsg("#U,R,0;")
        reply = self.readMsg().split(',')
        print("Rate: {}, Threshold: {}, Euro: {}".format(int(reply[3]), int(reply[4]), int(reply[5])))

    def getRecordCountLimit(self):
        self.writeMsg("#N,R,0;")
        reply = self.readMsg().split(',')
        print("[!] Supports up to {} records".format(int(reply[3])))

    def getInternalData(self):
        self.writeMsg("#D,R,0;")
        reply = self.readMsg()

        if self.verbose:
            print(reply)

        msg = ""
        results = []

        while True:
            msg = self.readMsg()
            fields = msg.split(',')
            
            if msg.strip().startswith("#l"):
                if self.verbose:
                    print("[+] Received final result")
                break

            watts = float(fields[3]) / 10

            results.append(watts)

            if self.verbose:
                print(self.header)
                print(50 * '-')
                print(msg)
                print("Watts: {:f}".format(watts))
        
        return results

    def printStats(self, results, log):
        if type(log) == str:
            log = open(log, 'w')
        elif log is None:
            log = sys.stdout
        
        print(datetime.datetime.now(), file=log)
        print("Results:", file=log)
        
        for i in range(len(results)):
            print("{}".format(results[i]), file=log)

        print("Samples: {}".format(len(results)), file=log)
        print("Pavg: {:.3f}".format(numpy.mean(results)), file=log)
        print("Pmax: {:.3f}".format(numpy.max(results)), file=log)
        print("Pmin: {:.3f}".format(numpy.min(results)), file=log)
        print("Pstdev: {:.3f}".format(numpy.std(results)), file=log)
        print("Joules: {:.3f}".format(len(results) * numpy.mean(results)), file=log)

##########################################################
def parseOptions():
    # parse command line options
    parser = OptionParser(usage = "usage: %prog [options] start|stop")

    parser.add_option("-p", "--port", dest="port",
                      #action="store", default="/dev/tty.usbserial-A6007Gmo",
                      action="store", default="/dev/ttyUSB0",
                      help="usb serial port"
                      )
    
    parser.add_option("-b", "--baud", dest="baudrate",
                      action="store", type="int",  default="115200",
                      help="Baud rate"
                      )

    parser.add_option("-i", "--log-interval", dest="interval",
                      action="store", type="int",  default="1",
                      help="Logging interval in seconds (minimum of 1s)"
                      )

    parser.add_option("-v", "--verbose", dest="verbose",
                      action="store_true",
                      help="Turn on extra logging information"
                      )
    
    parser.add_option("-o", "--output", dest="output",
                      action="store", type="string",
                      help="Output file"
                      )
    
    return parser

def main(user_args=None):
    parser = parseOptions()
    (options, args) = parser.parse_args(args=user_args)

    if len(args) != 1:
        print(parser.error("You need to specify an option: start | stop"))
        sys.exit(1)

    # Open serial port
    wattsup = WattsUp(options.port, options.baudrate, verbose=options.verbose)
    # wattsup.serial.open() # already open in python 3 via constructor

    if args[0] == "start": 
        print("[+] Starting internal logging with interval: {}".format(options.interval))
        wattsup.clearMemory()
        wattsup.logInternal(options.interval)
    elif args[0] == "stop":
        print("[+] Stopping internal logging")
        wattsup.printStats(wattsup.getInternalData(), options.output)
    else:
        print(parser.error("Unknown option specified"))

    wattsup.serial.close()
    
if __name__ == "__main__":
    main()
