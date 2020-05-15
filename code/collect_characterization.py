"""collect_characterization.py

Take the output of collect_relations.py and create files that list relations,
terms and states and show their contexts following short dependency chains. It
creates 12 files:

  out-context-rel2state-az.txt
  out-context-rel2state-nr.txt
  out-context-rel2term-az.txt
  out-context-rel2term-nr.txt
  out-context-state2rel-az.txt
  out-context-state2rel-nr.txt
  out-context-state2term-az.txt
  out-context-state2term-nr.txt
  out-context-term2rel-az.txt
  out-context-term2rel-nr.txt
  out-context-term2state-az.txt
  out-context-term2state-nr.txt

For example, the 8th file in the list shows for each state the 10 most frequent
terms that it co-occurs with, ranked by frequency of the term:

  4860  light   visible laser infrared image ultraviolet beam speed incident polarized surface
  4839  energy  thermal electrical kinetic high higher electrons photon lower electron enough
  4300  field   magnetic electric coil electrons electromagnetic view current electrical ions light
  3589  power   nuclear electric electrical solar high reactive microwave electricity low optical

"""

import sys
from collections import Counter


PAIRS_FILE = 'relations-all-20200515.txt'



def read_relations(fname, limit=sys.maxsize):
    rels_terms = {}
    terms_rels = {}
    rels_states = {}
    states_rels = {}
    terms_states = {}
    states_terms = {}
    c = 0
    for line in open(PAIRS_FILE):
        if c > limit:
            break
        if line.startswith('FNAME'):
            c += 1
        elif line.startswith('REL-TRM'):
            fields = line.split()
            rel = fields[2].lower()
            term = fields[3].lower()
            rels_terms.setdefault(rel, []).append(term)
            terms_rels.setdefault(term, []).append(rel)
        elif line.startswith('REL-STA'):
            fields = line.split()
            rel = fields[2].lower()
            state = fields[3].lower()
            rels_states.setdefault(rel, []).append(state)
            states_rels.setdefault(state, []).append(rel)
        elif line.startswith('TRM-STA'):
            fields = line.split()
            term = fields[2].lower()
            state = fields[3].lower()
            terms_states.setdefault(term, []).append(state)
            states_terms.setdefault(state, []).append(term)
    return rels_terms, terms_rels, rels_states, states_rels, terms_states, states_terms


def print_dictionary(dname, dictionary, minfreq=1):
    keys = sorted(dictionary, key = lambda key: len(dictionary[key]))
    with open("out-context-%s-nr.txt" % dname, 'w') as fh:
        fh.write("\nDICTIONARY %s with %d elements\n\n" % (dname, len(dictionary)))
        for key in reversed(keys):
            val = dictionary[key]
            if len(val) < minfreq:
                continue
            valcounter = Counter(val)
            vals = [t for t, c in valcounter.most_common()[:10]]
            fh.write("%4d\t%-18s\t%s\n" % (sum(valcounter.values()), key, ' '.join(vals)))
    with open("out-context-%s-az.txt" % dname, 'w') as fh:
        fh.write("\nDICTIONARY %s with %d elements\n\n" % (dname, len(dictionary)))
        for key in sorted(dictionary.keys()):
            val = dictionary[key]
            if len(val) < minfreq:
                continue
            valcounter = Counter(val)
            vals = [t for t, c in valcounter.most_common()[:10]]
            fh.write("%4d\t%-18s\t%s\n" % (sum(valcounter.values()), key, ' '.join(vals)))


if __name__ == '__main__':

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else sys.maxsize

    rel2term, term2rel, rel2state, state2rel, term2state, state2term = read_relations(PAIRS_FILE, limit)

    print_dictionary('rel2term', rel2term, 10)
    print_dictionary('term2rel', term2rel, 10)
    print_dictionary('rel2state', rel2state, 10)
    print_dictionary('state2rel', state2rel, 10)
    print_dictionary('term2state', term2state, 10)
    print_dictionary('state2term', state2term, 10)
