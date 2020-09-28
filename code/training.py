"""training.py

Script to generate training data for subject technology extraction.

USAGE:

$ python training.py -f SOURCE_FILE TERMS_FILE

Runn on a single source file and a list of terms, the result will be printed to
standard output. SOURCE_FILE is a regular text file and TERMS_FILE contains the
offsets of all terms in SOURCE_FILE:

((38, 60), (79, 94), (248, 266), (338, 353), (391, 410), (480, 495), (679, 691),
 (727, 748), (753, 765), (891, 900))

Note that this should evaluate to a Python tuple.

$ python training.py -f data/input/sources data/input/terms

Run on two directories, one with the sources and one with the terms. In this
case it will assume identical file names in the two directories. Results will be
printed to out-TIMESTAMP where TIMESTAMP is determined by time.localtime().

NOTES:

This works by comparing all terms in a document to the term extracted from the
title. The one with the highest similarity value is assumed to be the subject
technology.

Use the MINIMUM_SIMILARITY global to define how similar the subject technology
needs to be to the title. No training data will be generated if no term clears
that minimum requirement. This value should probably be at least 0.9.

"""

import sys
import os
import time

from operator import itemgetter
from difflib import get_close_matches, SequenceMatcher


DEBUG = True

MINIMUM_SIMILARITY = 0.6


def read_title(fname):
    return os.path.basename(fname)[:-4].replace('_', ' ').lower()


def similarity(term, title):
    s = SequenceMatcher(lambda x: x == " ", title, term)
    return(s.ratio())


def generate_training_data_from_directory(sources, terms):
    outdir = "out-%s" % int(time.mktime(time.localtime()))
    os.makedirs(outdir)
    for fname in os.listdir(sources):
        source_file = os.path.join(sources, fname)
        terms_file = os.path.join(terms, fname)
        outfile = os.path.join(outdir, fname)
        print(fname)
        with open(outfile, 'w') as fh:
            generate_training_data_from_file(source_file, terms_file, fh)


def generate_training_data_from_file(source_file, terms_file, fh=sys.stdout):
    title = read_title(source_file)
    text = open(source_file).read()
    terms = eval(open(terms_file).read())
    term_data = [[p1, p2, None, None, None] for p1, p2 in terms]
    for td in term_data:
        p1, p2 = td[0], td[1]
        term = text[p1-1:p2]
        similarity_score = similarity(term, title)
        td[2] = term
        td[3] = similarity_score
    p1, p2, max_term, max_score, label = max(term_data, key=itemgetter(3))
    if max_score > MINIMUM_SIMILARITY:
        for td in term_data:
            boolean = True if td[2] == max_term else False
            td[4] = boolean
            if DEBUG:
                print("%4s  %.2f  %-5s  %s" % (td[0], td[3], td[4], td[2]))
        fh.write("{%s}\n" % ', '.join(["{%s, %s, %s}" % (p1, p2, boolean)
                                       for p1, p2, _, _, boolean in term_data]))
    else:
        print("Warning: no reliable training data for %s" % source_file)


if __name__ == '__main__':

    option = sys.argv[1]
    if option == '-f':
        source_file = sys.argv[2]
        terms_file = sys.argv[3]
        generate_training_data_from_file(source_file, terms_file)
    if option == '-d':
        sources = sys.argv[2]
        terms = sys.argv[3]
        generate_training_data_from_directory(sources, terms)
