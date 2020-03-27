"""create_lists.py

Collect lists of technologies from titles of files in AcousticMinusSensorData,
SensorData and TransducersWiki, all corpora scraped from Wikipedia.

All those corpora are assumed to live in CORPUS_DIR.

The current algorith is rather simple and conservative. It does not try to do
anything with the content of brackets in file names or with any other special
filename. WHen the algorith finds a '#' it will split on that character and take
the first part. Anything between brackets is discarded. Technologies are
required to be all alphanumeric.

"""

import os
from collections import Counter


CORPUS_DIR = '/DATA/ttap/sources'


def create_technology_list(directory, list_file):
    """Write technologies to a file by extracting the technologies from a the file
    names in a directpry."""
    with open(list_file, 'w') as fh:
        fnames = os.listdir(directory)
        technologies = [fname[:-4].replace('_', ' ') for fname in fnames]
        for tech in technologies:
            tech = tech.split('(')[0]
            tech = tech.split('#')[0]
            if tech.replace(' ', 'x').replace('-', 'x').isalnum():
                fh.write("%s\n" % tech)


def get_brackets(technologies):
    """Given a list of technologies, find what occurs between brackets and put them
    into a Counter."""
    answer = []
    for t in technologies:
        idx =  t.find('(')
        if idx > -1:
            answer.append(t[idx+1:-1])
    return Counter(answer)



if __name__ == '__main__':

    for corpus in ('AcousticMinusSensorData', 'SensorData', 'TransducersWiki'):
        create_technology_list('%s/%s' % (CORPUS_DIR, corpus), corpus + '.txt')
