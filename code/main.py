"""main.py

Main Technology Finder script.

Typical use:

$ python main.py -i INPUT -o OUTPUT

Takes the INPUT file or directory and creates OUTPUT. If INPUT is a directory
than an OUTPUT directory will be created and for each source file in INPUT a new
output file in OUTPUT will be created. The -i and -o options are both optional,
standard input and/or standard output are used.

Four other options are available:

-h
    print a help message

--no-classifier
    do not run the classifier and stop after candidate term extraction

--verbose
    print some of the created data structures to standard output

--limit N
    only process N of the documents in the INPUT directory

"""

import os
import sys
import json
import argparse

import spacy

from classify import Classifier
from utils import exists, isdir, isfile, logger
from utils.lif import LIF, View
from utils.graph import DocumentGraph
from utils.features import add_term_features
from utils.factory import AnnotationFactory
from utils.matcher import match


NLP = None


def load_spacy():
    global NLP
    NLP = spacy.load("en_core_web_sm")


class Batch(object):

    """Class to manage processing of files and directories."""

    def __init__(self, inpath, outpath):
        # inpath is a filename, directory name or None, when None the input is
        # expected to be read from the standard input
        self.inpath = inpath
        # outpath is a filename, directory name or None, when None output will
        # be written to standard output
        self.outpath = outpath

    def run(self, classifier=True, limit=None, verbose=False):
        if exists(self.outpath):
            exit('Warning: output already exists')
        elif isdir(self.inpath):
            if self.outpath is None:
                exit('Warning: output directory must be specified')
            self._run_on_directory(classifier, limit=limit, verbose=verbose)
        elif isfile(self.inpath):
            TechnologyFinder(self.inpath, self.outpath).run(classifier, verbose)
        elif self.inpath is None:
            tf = TechnologyFinder(None, self.outpath, instring=sys.stdin.read())
            tf.run(classifier, verbose)
        else:
            print('Warning: input does not exist')

    def _run_on_directory(self, classifier, limit=sys.maxsize, verbose=False):
        if verbose:
            print("Processing directory '%s'" % self.inpath)
        if not os.path.exists(self.outpath):
            os.makedirs(self.outpath)
        with logger.Logger() as log:
            fnames = list(sorted(os.listdir(self.inpath)))
            for c, fname in enumerate(fnames[:limit]):
                infile = os.path.join(self.inpath, fname)
                outfile = os.path.join(self.outpath, fname)
                outfile = set_file_extension(outfile)
                print(c, outfile)
                log.write_line(fname, c)
                try:
                    TechnologyFinder(infile, outfile).run(classifier, verbose)
                except Exception as e:
                    log.write_error(e)
            log.write_time_elapsed()


def set_file_extension(filename):
    """Output filename gets a .lif extension."""
    if filename.endswith('.txt'):
        return filename[:-4] + '.lif'
    elif filename.endswith('.lif'):
        return filename
    else:
        return filename + '.lif'


class TechnologyFinder(object):

    def __init__(self, inpath, outpath, instring=None):
        """Read the input and initialize the internal LIF object, inpath and
        outpath are file names or None, if inpath is None then instring has the
        input as a string."""
        AnnotationFactory.reset()
        if NLP is None:
            load_spacy()
        self.inpath = inpath
        self.outpath = outpath
        self.instring = instring
        self.lif = None
        self.doc = None
        self.graph = None
        self._read_input()
        self._initialize_views()

    def run(self, classifier=True, verbose=False):
        self.verbose = verbose
        if verbose:
            print("Processing file '%s'" % self.inpath)
        self._run_spacy()
        self._create_graph()
        self._get_terms()
        self._add_features()
        if classifier:
            self._classify_terms()
        self._write_output()

    def _read_input(self):
        try:
            self._create_lif_from_json_input()
        except Exception:
            self._create_lif_from_text_input()

    def _create_lif_from_json_input(self):
        if self.instring is None:
            self.lif = LIF(json_file=self.inpath)
        else:
            self.lif = LIF(json_string=self.instring)

    def _create_lif_from_text_input(self):
        """Create a new LIF object and load the text into it."""
        self.lif = LIF()
        if self.instring is None:
            self.lif.text.value = open(self.inpath).read()
        else:
            self.lif.text.value = self.instring

    def _initialize_views(self):
        """Initializes the views that are added by spaCy processing."""
        self.lif.views.extend([View("tokens"),
                               View("chunks"),
                               View("dependencies")])

    def _run_spacy(self):
        """Run the spaCy NLP model and add NLP analysis elements as annotations
        to the LIF object."""
        self.doc = NLP(self.lif.text.value)
        self._add_annotations()

    def _add_annotations(self):
        """Add annotations from the spacy.tokens.doc.Doc instance to the part of
        speech, chunk and dependency views."""
        self.pos_view = self.lif.get_view("tokens")
        self.chk_view = self.lif.get_view("chunks")
        self.dep_view = self.lif.get_view("dependencies")
        for annotation in _get_sentence_annotations(self.doc):
            self.pos_view.annotations.append(annotation)
        for sentence in _get_sentences_and_tokens(self.doc):
            idx2id = {}
            self._add_annotations_first_pass(sentence, idx2id)
            self._add_annotations_second_pass(sentence, idx2id)
            if self.verbose:
                print()
        for chunk in self.doc.noun_chunks:
            anno = AnnotationFactory.chunk_annotation(chunk)
            self.chk_view.annotations.append(anno)

    def _add_annotations_first_pass(self, sentence, idx2id):
        """Create all token annotations and add them and build an index from the
        sentence offsets to the token identifiers."""
        for token in sentence:
            tok_annotation = AnnotationFactory.token_annotation(token)
            self.pos_view.annotations.append(tok_annotation)
            idx2id[token.i] = "%s:%s" % (self.pos_view.id, tok_annotation.id)
            if self.verbose:
                print("%2s  %2s  %2s  %3s  %-12s  %-5s    %-8s  %-10s  %2s  %s"
                      % (token.idx, token.idx + len(token.text), token.i, tok_annotation.id,
                         token.text.strip(), token.pos_, token.tag_,
                         token.dep_, token.head.i, token.head.text))

    def _add_annotations_second_pass(self, sentence, idx2id):
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

    def _create_graph(self):
        """Create a graph from the LIF object."""
        self.graph = create_graph(self.lif)
        if self.verbose:
            self.graph.print_sentences()

    def _get_terms(self):
        """Add candidate terms as annotations. We start with the noun chunks
        from the spaCy analysis, then run a pattern matcher over it, if there
        is a from the matching pattern, the term will be created for that slice
        of the noun chunk."""
        term_view = View('terms')
        self.lif.views.append(term_view)
        for chunk_node in self.graph.chunks:
            result = match(chunk_node)
            if result:
                anno = AnnotationFactory.term_annotation(chunk_node, result)
                term_view.annotations.append(anno)

    def _add_features(self):
        """Pull features from the graph and add them as a vector to the term."""
        add_term_features(self.graph, self.lif, self.verbose)

    def _classify_terms(self):
        # When called from this main script we use the small default classifier
        # (triggered by None as the first argument)
        Classifier().classify_lif(self.lif)
        # classify_lif(None, self.lif)

    def _write_output(self):
        """Save the LIF object into outpath or write it to standard outpath if
        outpath is equal to None."""
        json_string = self.lif.as_json_string()
        if self.outpath is not None:
            with open(self.outpath, 'w') as fh:
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

    h_input = \
        "the input file or input directory to process," \
        + " take standard input if this is not specified."
    h_output = \
        "the output file or output directory to write the results to," \
        + " write to standard output if not specified; if INPUT is a" \
        + " directory then this should be a directory too, it will be " \
        + " created if it does not exist"
    h_classifier = "switch off the classifier"
    h_verbose = "print some of the created data structures to standard output"
    h_limit = "the maximum number of files to process"

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", metavar='INPUT', help=h_input)
    parser.add_argument("-o", metavar='OUTPUT', help=h_output)
    parser.add_argument("--no-classifier", dest='classifier',
                        help=h_classifier, action="store_false")
    parser.add_argument("--verbose", help=h_verbose, action="store_true")
    parser.add_argument("--limit", help=h_limit, type=int)
    args = parser.parse_args()

    Batch(args.i, args.o).run(limit=args.limit,
                              verbose=args.verbose,
                              classifier=args.classifier)
