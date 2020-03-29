import time
import gzip


def timestamp():
    return time.strftime("%Y%m%d-%H%M%S")


def read_file(fname):
    """Open a file and return the contents."""
    return open_file(fname).read()


def open_file(fname, mode='r'):
    """Open a file the normal way or using gzip, choice depends on whether the file
    extension is .gz or not. The only modes this deals with are 'r' and 'w' and
    it always assumes text data and not binary."""
    if mode == 'r':
        if fname.endswith('.gz'):
            return gzip.open(fname, 'rt')
        else:
            return open(fname, mode)
    elif mode == 'w':
        if fname.endswith('.gz'):
            return gzip.open(fname, 'wt')
        else:
            return open(fname, mode)
