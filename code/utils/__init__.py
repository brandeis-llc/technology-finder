import os
import sys
import time
import gzip


def timer(fun):
   def wrapper(*args):
       print("$ python3 %s\n" % ' '.join(sys.argv))
       t0 = time.time()
       fun(*args)
       print("\nTime elapsed: %d seconds\n" % int(time.time() - t0))
   return wrapper


def exists(path):
    """Return True if path exists, False otherwise."""
    if path is None:
        return False
    return os.path.exists(path)


def isdir(path):
    """Return True if path is a directory, False otherwise."""
    if path is None:
        return False
    return os.path.isdir(path)


def isfile(path):
    """Return True if file is a directory, False otherwise."""
    if path is None:
        return False
    return os.path.isfile(path)


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
