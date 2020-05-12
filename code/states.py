"""states.py

Experiments for getting all terms and roles and relations between them

Adding in verbnet classes.

Parts to be added to main.py.

"""


import sys
import glob
import gzip
from utils.lif import LIF, View
from utils.graph import create_graph, GenericGraph
from utils.factory import AnnotationFactory


STATES_FILE = 'data/lists/stateWordSearchNew.txt'
VERBS_FILE =  'data/lists/verbnet-change-of-state.txt'
WN_VERBS_FILE =  'data/lists/wordnet_state_change_triggers.txt'
STOPLIST_FILE = 'data/lists/terms-0100.txt'

INDIR = '/DATA/ttap/processed/SensorData/'

VERBOSE = False


def read_states(fname):
    states = set()
    for line in open(fname):
        fields = line.rstrip().split('\t')
        states.add(fields[0])
    return states


def read_verbs(fname):
    verbs = set()
    for line in open(fname):
        fields = line.rstrip().split('\t')
        if len(fields) > 1:
            for verb in fields[1].split():
                verbs.add(verb)
    return verbs


def read_wn_verbs(fname):
    all_verbs = set()
    for line in open(fname):
        if not line.startswith('*'):
            continue
        line = line.strip()
        line = line[9:]
        idx = line.find('(')
        if idx > -1:
            line = line[:idx].strip()
        verbs = [v.strip() for v in line.split(',')]
        verbs = [v for v in verbs if not ' ' in v]
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
    if VERBOSE:
        print(' ', states_view)
        print(' ', relations_view)


class Sentences(object):

    def __init__(self):
        self.next_sent_id = 0
        self.sentences = []

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

    def __str__(self):
        return "<Sentence %s:%s terms:%s states:%s rels:%s>" \
            % (self.start, self.end,
               len(self.terms), len(self.states), len(self.relations))

    def is_complete(self):
        return self.terms and self.states and self.relations


    def collect_pairs(self, graph, dep_idx):

        debug = True
        debug = False

        def get_token(anno):
            return graph.tokens_in_range(anno.start, anno.end)

        rels = [(r, graph.get_head_token(r)) for r in self.relations]
        terms = [(t, graph.get_head_token(t)) for t in self.terms]
        states = [(s, graph.get_head_token(s)) for s in self.states]

        sent_graph = GenericGraph(self, dep_idx)

        if debug:
            print(sent_graph)
            #sent_graph.pp()

        answer = []

        for rel, rel_head_token in rels:

            term_paths = []
            for term, term_head_token in terms:
                if debug:
                    print('  %s_%s --> %s_%s' % (rel_head_token.text, rel_head_token.id,
                                                 term_head_token.text, term_head_token.id))
                path = sent_graph.find_path(rel_head_token, term_head_token)
                if path is not None:
                    term_paths.append((len(path), path, term_head_token, term))
            term_paths = [tp for tp in term_paths if tp[0] <= 2]
            if debug:
                for path_length, path, tok, term in term_paths:
                    print('    %d %s %s' % (path_length, ' --> '.join(path), tok.text))

            state_paths = []
            for state, state_head_token in states:
                if debug:
                    print('  %s_%s --> %s_%s' % (rel_head_token.text, rel_head_token.id,
                                                 state_head_token.text, state_head_token.id))
                path = sent_graph.find_path(rel_head_token, state_head_token)
                if path is not None:
                    state_paths.append((len(path), path, state_head_token, state))
            state_paths = [sp for sp in state_paths if sp[0] <= 2]
            if debug:
                for path_length, path, tok, state in state_paths:
                    print('    %d %s %s' % (path_length, ' --> '.join(path), tok.text))

            answer.append([rel_head_token, term_paths, state_paths])

        return answer


def collect_sentences(lif, stoplist):
    tokens_view = lif.get_view('tokens')
    terms_view = lif.get_view('terms')
    states_view = lif.get_view('states')
    relations_view = lif.get_view('relations')
    sents = Sentences()
    for anno in tokens_view.annotations:
        if anno.type.endswith('Sentence'):
            sent = Sentence(anno)
            sents.add(sent)
    for anno in tokens_view.annotations:
        if anno.type.endswith('Token'):
            sents.add_token(anno)
    for term in terms_view.annotations:
        if not term.get_text().lower() in stoplist:
            sents.add_term(term)
    for state in states_view.annotations:
        sents.add_state(state)
    for rel in relations_view.annotations:
        sents.add_relation(rel)
    return sents


def index_depencencies_on_token_ids(dep_view):
    idx = {}
    for anno in dep_view.annotations:
        if anno.type.endswith('Dependency'):
            gov = anno.get_feature('governor').split(':')[1]
            dep = anno.get_feature('dependent').split(':')[1]
            idx[(gov, dep)] = anno.get_feature('label')
    return idx


if __name__ == '__main__':

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 99999

    lst_states = read_states(STATES_FILE)
    lst_verbs = read_verbs(VERBS_FILE)
    lst_verbs.update(read_wn_verbs(WN_VERBS_FILE))
    stoplist = read_stoplist(STOPLIST_FILE)

    fh_results = open('out.txt', 'w')
    fnames = glob.glob("%s/*.gz" % INDIR)[:limit]

    for fname in fnames:
        AnnotationFactory.reset()
        print("\n%s" % fname)
        with gzip.open(fname) as fh:
            text = fh.read()
            lif = LIF(json_string=text)
            dependencies_view = lif.get_view('dependencies')
            dep_idx = index_depencencies_on_token_ids(dependencies_view)
            if VERBOSE:
                print(' ', lif)
            add_states_and_verbs(lif, lst_states, lst_verbs)
            sents = collect_sentences(lif, stoplist)
            graph = create_graph(lif)
            for s in sents:
                #print(s)
                if s.is_complete():
                    s_str = lif.text.value[s.start:s.end]
                    pairs = s.collect_pairs(graph, dep_idx)
                    fh_results.write('FNAME\t%s\n' % fname)
                    for rel, terms, states in pairs:
                        for term in terms:
                            fh_results.write("REL-TRM %s-%s\t%s\t%s\t%s\n"
                                             % (rel.id, term[2].id,
                                                rel.text, ' '.join(term[1]), term[3].get_text()))
                        for state in states:
                            fh_results.write("REL-STA %s-%s\t%s\t%s\t%s\n"
                                             % (rel.id, state[2].id,
                                                rel.text, ' '.join(state[1]), state[3].get_text()))
                    # sentence string can include trailing white lines
                    fh_results.write('%s\n\n' % s_str.strip())
