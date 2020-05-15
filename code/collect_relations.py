"""collect_relations.py

Experiments for getting all terms and roles and relations between them.

$ python collect_relations.py LIMIT?

Takes as input a corpus processed by the main.oy script, the location of the
corpus is set in CORPUS. The optional LIMIT parameter restricts how many
documents from the corpus are processed.

Output is written to out-relations.txt with a paragraph for each set of
relations in a sentence as follows:

    FNAME	/DATA/ttap/processed/SensorData/4Pi_microscope.lif.gz
    REL-TRM t193-t191 <TAB> divided <TAB> nsubjpass  <TAB> laser light
    REL-TRM t193-t198 <TAB> divided <TAB> agent pobj <TAB> beam splitter BS
    REL-STA t193-t191 <TAB> divided <TAB> nsubjpass  <TAB> light
    The laser light is divided by a beam splitter BS and directed by mirrors towards the two opposing objective lenses.

(The output has been expanded by adding three pieces of information: TRM-STA
pairs, the tokenization of the sentence and all dependencies).

Starts off with the results of the technology finder with terms and
dependencies, but then adds the following to the LIF object:

- Change of state verbs from VerbNet and a manually selected subset of WordNet
- States by look up from a fixed set of states

The code then looks for sentences that have relations, terms and states, and
then prints out relation-term and relation-state pairs if there is a dependency
relation between relation and term or state. The relation could be direct or a
two-step relation.

TODO:
- be more specific on what paths may be followed
- possibly restrict how far apart the tokens are allowed to be

"""


import sys
import glob
import gzip
from utils.lif import LIF, View
from utils.graph import DocumentGraph, SentenceGraph
from utils.factory import AnnotationFactory


STATES_FILE = 'data/lists/stateWordSearchNew.txt'
VN_VERBS_FILE = 'data/lists/verbnet-change-of-state.txt'
WN_VERBS_FILE = 'data/lists/wordnet_state_change_triggers.txt'
STOPLIST_FILE = 'data/lists/terms-0100.txt'

CORPUS = '/DATA/ttap/processed/SensorData/'


def read_states(fname):
    states = set()
    for line in open(fname):
        fields = line.rstrip().split('\t')
        states.add(fields[0])
    return states


def read_verbs(verbnet_verbs, wordnet_verbs):
    all_verbs = set()
    for line in open(verbnet_verbs):
        fields = line.rstrip().split('\t')
        if len(fields) > 1:
            for verb in fields[1].split():
                all_verbs.add(verb)
    for line in open(wordnet_verbs):
        if not line.startswith('*'):
            continue
        line = line.strip()
        line = line[9:]
        idx = line.find('(')
        if idx > -1:
            line = line[:idx].strip()
        verbs = [v.strip() for v in line.split(',')]
        verbs = [v for v in verbs if ' ' not in v]
        for v in verbs:
            all_verbs.add(v)
    return all_verbs


def read_stoplist(fname):
    terms = set()
    for line in open(fname):
        line = line.strip('\n ')
        if not line or line.startswith('#'):
            continue
        label, frequency, term = line.split('\t')
        if label.strip() == '-':
            terms.add(term)
    return(terms)


def add_states_and_verbs(lif, states, verbs):
    tokens_view = lif.get_view('tokens')
    states_view = View('states')
    relations_view = View('relations')
    lif.views.append(states_view)
    lif.views.append(relations_view)
    for token in tokens_view.annotations:
        if token.type.endswith('Token'):
            word = token.features.get('word')
            pos = token.features.get('pos')
            lemma = token.features.get('lemma')
            if word.lower() in states:
                state = AnnotationFactory.state_annotation(token)
                state.text = word
                states_view.annotations.append(state)
            if pos[0] == 'V' and lemma in verbs:
                rel = AnnotationFactory.relation_annotation(token)
                rel.text = word.lower()
                relations_view.annotations.append(rel)


class Sentences(object):

    def __init__(self, lif, stoplist):
        self.next_sent_id = 0
        self.sentences = []
        tokens_view = lif.get_view('tokens')
        terms_view = lif.get_view('terms')
        states_view = lif.get_view('states')
        relations_view = lif.get_view('relations')
        for anno in tokens_view.annotations:
            if anno.type.endswith('Sentence'):
                sent = Sentence(anno)
                self.add(sent)
        for anno in tokens_view.annotations:
            if anno.type.endswith('Token'):
                self.add_token(anno)
        for term in terms_view.annotations:
            if not term.get_text().lower() in stoplist:
                self.add_term(term)
        for state in states_view.annotations:
            self.add_state(state)
        for rel in relations_view.annotations:
            self.add_relation(rel)

    def __getitem__(self, i):
        return self.sentences[i]

    def add(self, sentence):
        sentence.id = self.next_sent_id
        self.next_sent_id += 1
        self.sentences.append(sentence)

    def find_sentence(self, anno):
        for s in self.sentences:
            if s.start <= anno.start and s.end >= anno.end:
                return s

    def add_token(self, token):
        # TODO: this is a hack, need better way to deal with the text
        token.text = token.get_feature('word')
        s = self.find_sentence(token)
        s.tokens.append(token)

    def add_term(self, term):
        s = self.find_sentence(term)
        s.terms.append(term)

    def add_state(self, state):
        s = self.find_sentence(state)
        s.states.append(state)

    def add_relation(self, rel):
        s = self.find_sentence(rel)
        s.relations.append(rel)

    def pp(self):
        print("<Sentences>")
        for s in self.sentences:
            print(' ', s)


class Sentence(object):

    def __init__(self, sentence_annotation):
        self.id = None
        self.annotation = sentence_annotation
        self.start = self.annotation.start
        self.end = self.annotation.end
        self.tokens = []
        self.terms = []
        self.states = []
        self.relations = []
        self.graph = None

    def __str__(self):
        return "<Sentence %s:%s terms:%s states:%s rels:%s>" \
            % (self.start, self.end,
               len(self.terms), len(self.states), len(self.relations))

    def is_complete(self):
        return self.terms and self.states and self.relations

    def collect_pairs(self, doc_graph):
        rels = [(r, doc_graph.get_head_token(r)) for r in self.relations]
        terms = [(t, doc_graph.get_head_token(t)) for t in self.terms]
        states = [(s, doc_graph.get_head_token(s)) for s in self.states]
        pairs = []
        for rel, rel_head_token in rels:
            for term, term_head_token in terms:
                path = self.graph.find_path(rel_head_token, term_head_token)
                if path is not None and len(path) <= 2:
                    pairs.append(('REL-TRM',
                                  rel, rel_head_token,
                                  term, term_head_token,
                                  path))
            for state, state_head_token in states:
                path = self.graph.find_path(rel_head_token, state_head_token)
                if path is not None and len(path) <= 2:
                    pairs.append(('REL-STA',
                                  rel, rel_head_token,
                                  state, state_head_token,
                                  path))
        for term, term_head_token in terms:
            for state, state_head_token in states:
                path = self.graph.find_path(term_head_token, state_head_token)
                # requiring the path to be of non-zero length filters out the
                # cases where the term and the state have the same head
                if path is not None and 0 < len(path) <= 5:
                    pairs.append(('TRM-STA',
                                  term, term_head_token,
                                  state, state_head_token,
                                  path))
        return pairs


def index_depencencies_on_token_ids(lif):
    dependencies_view = lif.get_view('dependencies')
    idx = {}
    for anno in dependencies_view.annotations:
        if anno.type.endswith('Dependency'):
            gov = anno.get_feature('governor').split(':')[1]
            dep = anno.get_feature('dependent').split(':')[1]
            idx[(gov, dep)] = anno.get_feature('label')
    return idx


def write_pair(fh, pair):
    pair_type, a1, t1, a2, t2, p = pair
    elements = ["--%s--> %s" % (pe[0], pe[1].text()) for pe in p]
    path = "%s %s" % (a1.get_text(), ' '.join(elements))
    fh.write('%s %s-%s\t%s\t%s\t%s\n' % (pair_type, t1.id, t2.id,
                                         a1.get_text(), a2.get_text(), path))


def write_tokens(fh, sentence):
    fh.write('TOKENS\t')
    for token in sentence.tokens:
        text = token.text.replace('\n', '\\n').replace(' ', '')
        fh.write("%s/%s " % (text, token.features.get('pos')))
    fh.write('\n')


def write_dependencies(fh, sentence):
    for edge in sentence.graph.edges:
        if edge.label in ('', '_r') or edge.label.endswith('_r'):
            continue
        fh.write("DEP\t%s_%s %s %s_%s\n" % (
            edge.source.obj.text.lower(), edge.n1, edge.label,
            edge.target.obj.text.lower(), edge.n2))


def print_pairs(pairs):
    for pair in pairs:
        print("%s: %s == %s ||" % (pair[0], pair[1], pair[2]), end='')
        for (dep, node) in pair[3]:
            print(' --%s--> %s' % (dep, node.text()), end='')
        print()


if __name__ == '__main__':

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 99999

    lst_states = read_states(STATES_FILE)
    lst_verbs = read_verbs(VN_VERBS_FILE, WN_VERBS_FILE)
    stoplist = read_stoplist(STOPLIST_FILE)

    fh_results = open('out-relations.txt', 'w')
    fnames = glob.glob("%s/*.gz" % CORPUS)[:limit]

    for fname in fnames:
        AnnotationFactory.reset()
        print("\n%s" % fname)
        with gzip.open(fname) as fh:
            lif = LIF(json_string=fh.read())
            dep_idx = index_depencencies_on_token_ids(lif)
            add_states_and_verbs(lif, lst_states, lst_verbs)
            sents = Sentences(lif, stoplist)
            doc_graph = DocumentGraph(lif)
            for s in sents:
                sent_graph = SentenceGraph(s, dep_idx)
                s.graph = sent_graph
                if s.is_complete():
                    s_str = lif.text.value[s.start:s.end]
                    pairs = s.collect_pairs(doc_graph)
                    # don't print results if there were no pairs
                    if not pairs:
                        continue
                    fh_results.write('FNAME\t%s\n' % fname)
                    for p in pairs:
                        write_pair(fh_results, p)
                    write_tokens(fh_results, s)
                    write_dependencies(fh_results, s)
                    # sentence string can include trailing white lines
                    fh_results.write('%s\n\n' % s_str.strip())
