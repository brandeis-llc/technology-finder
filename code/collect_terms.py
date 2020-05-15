"""collect_terms.py

Usage:

$ python collect_terms data/saved/relations-all-20200511.txt.gz 100

This takes relations-all-20200511.txt.gz, collects all terms found and then
prints out the 100 most frequent ones. The input file was created by some old
untagged version of collect_relations.py on the SensorData corpus. Results are
written to terms-0100.txt. Note that the resulting file was moved to data/lists
and then manually annotated by adding '-' markers to terms that were definitely
of no interest.

You can change the minimal frequency or the input file, but the code expects the
input file to be compressed and have lines like

TERMS   laser light     beam splitter BS        mirrors objective lenses

When you change the minimal frequency then the output file will be named
slightly differently to reflect that.

"""


import sys
import gzip
import collections


def collect_terms(fname):
    all_terms = []
    for line in gzip.open(sys.argv[1], 'rt'):
        if line.startswith('TERMS'):
            terms = line.strip().split('\t')[1:]
            for term in terms:
                all_terms.append(term.lower())
    return all_terms


if __name__ == '__main__':

    fname = sys.argv[1]
    minfreq = int(sys.argv[2])
    termsfile = 'terms-%04d.txt' % minfreq

    terms = collect_terms(fname)
    c = collections.Counter(terms)
    cmc = c.most_common()

    print('tokens   %6d' % len(terms))
    print('types    %6d' % len(c))

    total = 0
    total_count = 0
    with open(termsfile, 'w') as fh:
        for (term, count) in cmc:
            if count < minfreq:
                break
            total += 1
            total_count += count
            fh.write("\t %s\t%s\n" % (count, term))
    print('terms:   %6d' % total)
    print('cumfreq: %6d' % total_count)
