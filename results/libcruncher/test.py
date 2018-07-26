"""A simple frontend to test the libcruncher!"""

import libcruncher
import sys

if __name__ == "__main__":
    print('(libcruncher library is running in test mode)')
    libcruncher.argsToExecutionProperties(sys.argv)
