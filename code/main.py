import sys
import json
import argparse

import spacy

from utils.lif import LIF, View
from utils.graph import create_graph
from utils.features import add_term_features
from utils.factory import AnnotationFactory


NLP = None


def load_spacy():
    global NLP
    NLP = spacy.load("en_core_web_sm")


class TechnologyFinder(object):

    def __init__(self, infile, outfile):
        if NLP is None:
            load_spacy()
        self.infile = infile
        self.outfile = outfile
        self.lif = None
        self.doc = None
        self.graph = None
        self._create_lif()

    def run(self, verbose=False):
        self._run_spacy(verbose)
        self._create_graph(verbose)
        self._add_features(verbose)
        self._write_output()

    def _create_lif(self):
        """Create a new LIF object, load the textinto it and initialize three views."""
        self.lif = LIF()
        self.lif.text.value = open(self.infile).read()
        tok_view = View("tokens")
        chk_view = View("chunks")
        dep_view = View("dependencies")
        term_view = View("terms")
        self.lif.views.extend([tok_view, dep_view, term_view])

    def _run_spacy(self, verbose):
        """Run the spaCy NLP model and add NLP analysis elements as annotations to the
        LIF object."""
        # NOTE: maybe this piece should just add all information we want to get
        # from spaCy and at this point we stipulate that chunks are the initial
        # terms; maybe pull out chunks and store as chunk objects, then later
        # use those to collect terms or filter them
        self.doc = NLP(self.lif.text.value)
        self._add_annotations(verbose)
        self._add_term_annotations()

    def _add_annotations(self, verbose):
        """Add annotations from the spacy.tokens.doc.Doc instance to the part of speech
        and dependency views."""
        self.pos_view = self.lif.get_view("tokens")
        self.dep_view = self.lif.get_view("dependencies")
        for annotation in _get_sentence_annotations(self.doc):
            self.pos_view.annotations.append(annotation)
        for sentence in _get_sentences_and_tokens(self.doc):
            idx2id = {}
            self._add_annotations_first_pass(sentence, idx2id, verbose)
            self._add_annotations_second_pass(sentence, idx2id, verbose)
            if verbose:
                print()

    def _add_annotations_first_pass(self, sentence, idx2id, verbose):
        """Create all token annotations and add them and build an index from the
        sentence offsets to the token identifiers."""
        for token in sentence:
            tok_annotation = AnnotationFactory.token_annotation(token)
            self.pos_view.annotations.append(tok_annotation)
            idx2id[token.i] = "%s:%s" % (self.pos_view.id, tok_annotation.id)
            if verbose:
                print("%2s  %2s  %2s  %3s  %-12s  %-5s    %-8s  %-10s  %2s  %s"
                      % (token.idx, token.idx + len(token.text), token.i, tok_annotation.id,
                         token.text.strip(), token.pos_, token.tag_,
                         token.dep_, token.head.i, token.head.text))

    def _add_annotations_second_pass(self, sentence, idx2id, verbose):
        """Loop through the tokens again and create the dependency for each of
        them (but not adding them to the view yet), using the index created in
        the previous loop for access to the identifiers. Then, when we know what
        dependencies we have for the dependency structure, create the structure
        and add it and then add all dependencies."""
        dep_annos = []
        for token in sentence:
            dep_annotation = AnnotationFactory.dependency_annotation(token, idx2id)
            dep_annos.append(dep_annotation)
        dep_struct = AnnotationFactory.dependency_structure_annotation(dep_annos)
        self.dep_view.annotations.append(dep_struct)
        for dep_anno in dep_annos:
            self.dep_view.annotations.append(dep_anno)

    def _add_term_annotations(self):
        """Add candidate terms as annotations. For now we just use the noun chunks from
        the spaCy analysis."""
        # TODO: filter out some chunks, like proper names
        # TODO: if term has 1 element and last element is pos=PRP
        # TODO: the problem is that at this point we do not have that information since
        # TODO: all we have is the span and it is not linked to the tokens yet
        term_view = self.lif.get_view("terms")
        for term in self.doc.noun_chunks:
            anno = AnnotationFactory.term_annotation(term)
            term_view.annotations.append(anno)

    def _create_graph(self, verbose):
        """Create a graph from the LIF object."""
        self.graph = create_graph(self.lif)
        if verbose:
            self.graph.print_sentences()

    def _add_features(self, verbose):
        """Pull features from the graph and add them as a vector to the term."""
        add_term_features(self.graph, verbose)

    def _write_output(self):
        """Save the LIF object into outfile or write it to standard output if outfile is
        equal to None."""
        json_string = self.lif.as_json_string()
        if self.outfile is not None:
            with open(self.outfile, 'w') as fh:
                fh.write(json_string)
        else:
            print(json_string)


def _get_sentence_annotations(doc):
    annotations = []
    for s in doc.sents:
        w1 = doc[s.start]
        w2 = doc[s.end - 1]
        p1 = w1.idx
        p2 = w2.idx + len(w2)
        annotations.append(AnnotationFactory.sentence_annotation(s, doc))
    return annotations


def _get_sentences_and_tokens(doc):
    """Return a list of sentences where each sentence is a list of tokens as
    extracted from the document, which is an instance of spacy.tokens.doc.Doc."""
    sentences = []
    for s in doc.sents:
        sentence = []
        sentences.append(sentence)
        for t in s:
            sentence.append(t)
    return sentences


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    input_help = "the file to process"
    output_help = "the output file, print to standard output if not specified"
    verbose_help = "print some created data structures to standard output"
    parser.add_argument("--input", help=input_help, required=True)
    parser.add_argument("--output", help=output_help)
    parser.add_argument("--verbose", help=verbose_help, action="store_true")
    args = parser.parse_args()

    TechnologyFinder(args.input, args.output).run(verbose=args.verbose)
