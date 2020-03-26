import time


def timestamp():
    return time.strftime("%Y%m%d-%H%M%S")


def vocab(short_form):
    """Expand the annotation type name to the full URL."""
    return "http://vocab.lappsgrid.org/%s" % short_form


class Identifier(object):

    """Class to keep track of what identifiers have been used."""
    
    COUNTS = {}

    @classmethod
    def reset(cls):
        cls.COUNTS = {}

    @classmethod
    def new(cls, prefix):
        cls.COUNTS[prefix] = cls.COUNTS.get(prefix, 0) + 1
        return "%s%s" % (prefix, cls.COUNTS[prefix])
