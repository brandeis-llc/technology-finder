"""main.py

Main Technology Finder script.

USAGE:

$ python main.py -i INPUT -o OUTPUT

Takes the INPUT file or directory and creates OUTPUT. If INPUT is a directory
than an OUTPUT directory will be created and for each source file in INPUT a new
output file in OUTPUT will be created. The -i and -o options are both optional,
standard input and/or standard output are used if they are absent.

OPTIONS:

-h
    print a help message

--terms TERMS_FILE
    use an external file with term offsets, bypasses the default processing of
    terms which is to use spaCy and a matcher

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

from classify import Classifier
from utils import exists, isdir, isfile, logger
from utils.lif import LIF, View
from utils.graph import DocumentGraph
from utils.features import add_term_features
from utils.factory import AnnotationFactory, make_annotation
from utils.matcher import match
from utils.spacy import SpacyAnalysis
from utils.argparser import parse_arguments


def run(inpath, outpath, classifier=True,
        terms=False, limit=sys.maxsize, verbose=False):
    if exists(outpath):
        exit('Warning: output already exists')
    elif isdir(inpath):
        if outpath is None:
            exit('Warning: output directory must be specified')
        if verbose:
            print("Processing directory '%s'" % inpath)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        with logger.Logger() as log:
            fnames = list(sorted(os.listdir(inpath)))
            for c, fname in enumerate(fnames[:limit]):
                infile = os.path.join(inpath, fname)
                outfile = os.path.join(outpath, fname)
                outfile = set_file_extension(outfile)
                print(c, outfile)
                log.write_line(fname, c)
                try:
                    TechnologyFinder(infile, outfile).run(classifier, None, verbose)
                except Exception as e:
                    log.write_error(e)
            log.write_time_elapsed()
    elif isfile(inpath):
        TechnologyFinder(inpath, outpath).run(classifier, terms, verbose)
    elif inpath is None:
        tf = TechnologyFinder(None, outpath, None, instring=sys.stdin.read())
        tf.run(classifier, verbose)
    else:
        print('Warning: input does not exist')


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
        self.inpath = inpath
        self.outpath = outpath
        self.instring = instring
        self.lif = None
        self.spacydoc = None
        self.graph = None
        self._read_input()
        self._initialize_views()

    def run(self, classifier=True, terms=None, verbose=False):
        self.verbose = verbose
        if verbose:
            print("Processing file '%s'" % self.inpath)
        self._run_spacy()
        self._create_graph()
        self._get_terms(terms)
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
        v1 = View("tokens")
        v2 = View("chunks")
        v3 = View("dependencies")
        v1.add_contains("http://vocab.lappsgrid.org/Sentence")
        v1.add_contains("http://vocab.lappsgrid.org/Token")
        v2.add_contains("http://vocab.lappsgrid.org/NounChunk")
        v3.add_contains("http://vocab.lappsgrid.org/DependencyStructure")
        v3.add_contains("http://vocab.lappsgrid.org/Dependency")
        self.lif.views.extend([v1, v2, v3])

    def _run_spacy(self):
        """Run the spaCy NLP model and add NLP analysis elements as annotations
        to the LIF object."""
        self.spacy = SpacyAnalysis(self.lif.text.value)
        tok_view = self.lif.get_view("tokens")
        chk_view = self.lif.get_view("chunks")
        dep_view = self.lif.get_view("dependencies")
        tokens, chunks, dependencies = self.spacy.annotations(tok_view.id)
        for anno in tokens:
            tok_view.annotations.append(anno)  # tokens and sentences
        for anno in chunks:
            chk_view.annotations.append(anno)  # noun chunks
        for anno in dependencies:
            dep_view.annotations.append(anno)  # dependencies, with structure

    def _create_graph(self):
        """Create a graph from the LIF object."""
        self.graph = DocumentGraph(self.lif)
        if self.verbose:
            self.graph.print_sentences()
            self.graph.print_chunks()

    def _get_terms(self, terms):
        """Add candidate terms as annotations. Here you can either use the term
        offsets handed in with the --terms parameter or built the terms using
        spaCy and a matcher."""
        term_view = View('terms')
        term_view.add_contains("http://vocab.lappsgrid.org/Term")
        self.lif.views.append(term_view)
        if terms is None:
            self._get_terms_from_spacy(term_view)
        else:
            self._get_terms_from_import(term_view)

    def _get_terms_from_spacy(self, term_view):
        """We start with the noun chunks from the spaCy analysis, then run a
        pattern matcher over them, if there is matching pattern, the term will
        be created for that slice of the noun chunk."""
        for chunk_node in self.graph.chunks:
            result = match(chunk_node)
            if result:
                anno = AnnotationFactory.term_annotation(chunk_node, result)
                term_view.annotations.append(anno)

    def _get_terms_from_import(self, term_view):
        # TODO: this is implemented the wrong way, we need to start with the
        # spacy terms and then check whether they include the offsets we are
        # given; alternatively we can try to get the tokens some other way
        text = self.lif.text.value
        for p1, p2 in ((1,2), (3,4)):
            anno = make_annotation('term', 'Term', p1, p2)
            anno.text = text[p1:p2]
            print(anno, anno.features)
            term_view.annotations.append(anno)

    def _add_features(self):
        """Pull features from the graph and add them as a vector to the term."""
        add_term_features(self.graph, self.lif, self.verbose)

    def _classify_terms(self):
        # When called from this main script we use the small default classifier
        Classifier().classify_lif(self.lif)

    def _write_output(self):
        """Save the LIF object into outpath or write it to standard outpath if
        outpath is equal to None."""
        json_string = self.lif.as_json_string()
        if self.outpath is not None:
            with open(self.outpath, 'w') as fh:
                fh.write(json_string)
        else:
            print(json_string)


if __name__ == '__main__':

    args = parse_arguments()
    run(args.i, args.o,
        limit=args.limit, terms=args.terms,
        verbose=args.verbose, classifier=args.classifier)
