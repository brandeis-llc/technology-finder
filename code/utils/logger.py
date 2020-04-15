"""logger.py

Simple logger to print progress to.

"""

import sys
import time


def timestamp():
    return time.strftime("%Y%m%d-%H%M%S")


class Logger(object):

    def __init__(self, logfile=None):
        if logfile is None:
            logfile = 'data/logs/log-%s.txt' % timestamp()
        self.fname = logfile
        self.fh = open(logfile, 'w')
        self.fh.write("$ python3 %s\n\n" % ' '.join(sys.argv))
        self.t0 = time.time()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        print("Log written to %s" % self.fname)
        self.fh.close()

    def write_line(self, fname, c):
        self.fh.write("%05d  %s  %s\n" % (c + 1, timestamp(), fname))

    def write_error(self, e):
        self.fh.write('ERROR: %s\n' % e)

    def write_time_elapsed(self):
        self.fh.write("\ntime elapsed: %s seconds\n" % int(time.time() - self.t0))
