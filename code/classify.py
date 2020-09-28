"""classify.py

Contains code related to the term classifier. Included feature extraction from a
processed corpus, model creation and classification.


== feature extraction

$ python3 classify.py --get-features PROCESSED_CORPUS FEATURES_FILE N?

Collect all term feature vectors from PROCESSED_CORPUS and writes them to
FEATURES_FILE. Limit to N files if the third argument is present, default is to
process all files. The corpus is required to have Sentence, Token, NounChunk,
Dependency and Term annotations, an example corpus is in data/input/mini-corpus.

This also creates two files with terms and counts: terms-az.txt contains an
aplhabetical list of all terms and terms-nr.txt a list of terms with frequency
ordered on frequency. These can be used for any technology annotation effort.

Takes about 80 seconds on a high-end 2015 iMac for a corpus of 27M.

TODO:
- figure out why some terms do not have any features
- some terms start with a space, need some kind of massaging of the term
- we are not yet using any filters for terms, all chunks are taken in their
  entirity, part of the reason why the performance is so bad


== model creation

$ python3 classify.py --train FEATURES_FILE MODEL_NAME

This assumes that there are lists of technologies and non-technologies (these
are not necessarily from the domain you are working on). All available lists in
data/lists/technologies are used. Positive and negative examples will be created
from those lists and the feature vectors from the corpus. These will be used to
create the model.

TODO:
- need to do some experiments with sampling etcetera
- probably add a utils.ml module with trainers and classifiers
- experiment with classifiers, now use naieve bayes, should use maxent with
  confidence scores
- need to classify at the document level (collect all terms)


== classification

$ python3 classify.py --classify MODEL_FILE LIF_FILE OUT_FILE

Classify a LIF given the model handed in. The LIF is accumed to be created by
the code in main.py. The output is another LIF file with a technologies view
added.

$ python3 classify.py --classify-vectors MODEL_FILE VECTORS_FILE LABELS_FILE

Run the classifier saved in MODEL_FILE on a file with vectors. Labels are
written to the labels file, one label per line.

"""


import os
import sys
import glob
import time
from operator import itemgetter

from sklearn.feature_extraction import DictVectorizer
from sklearn.naive_bayes import BernoulliNB
from joblib import dump, load

from utils import timer, logger
from utils import read_file, open_file, exists, isfile, isdir
from utils.lif import LIF, View
from utils.factory import AnnotationFactory


class Vector(object):

    """A vector includes the file name that the term occurs in and the offsets in
    that file, it also includes the name of the term, the rest is all the features
    as extracted by utils.features.py."""

    def __init__(self, fname, term):
        self.vector = (os.path.basename(fname),
                       "%s:%s" % (term.start, term.end),
                       term.text,
                       term.features['vector'])

    def __str__(self):
        return "\t".join([str(field) for field in self.vector])


def vectors_file_name(model_name):
    """Standardized name of the raw text vectors file for a model."""
    return "%s-model-vectors.txt" % model_name


def vectorizer_file_name(model_name):
    """Standardized name of the vectorizer file for a model."""
    return "%s-model-vectorizer.jl" % model_name


def model_file_name(model_name):
    """Standardized name of the fitted model."""
    return "%s-model-fitted.jl" % model_name


def get_features(directory, features_file, n):
    """Extract all term features from n files in the directory and write them as
    vectors to the features file."""
    with logger.Logger() as log, \
         open(features_file, 'w') as fh_features, \
         open('terms-az.txt', 'w') as fh_terms, \
         open('terms-nr.txt', 'w') as fh_counts:
        terms = {}
        for (i, fname) in enumerate(glob.glob("%s/*" % directory)[:n]):
            log.write_line(os.path.basename(fname), i)
            content = read_file(fname)
            lif = LIF(json_string=content)
            for term in lif.get_view('terms').annotations:
                text = term.text
                if text is not None:
                    text = text.strip().replace("\n", ' ')
                    terms[text] = terms.get(text, 0) + 1
                if 'vector' in term.features:
                    vector = Vector(fname, term)
                    fh_features.write("%s\n" % vector)
        fh_terms.write("%s\n" % '\n'.join(sorted(terms)))
        for (term, count) in reversed(sorted(terms.items(), key=itemgetter(1))):
            fh_counts.write("%-4d\t%s\n" % (count, term))
        log.write_time_elapsed()


class Trainer(object):

    def __init__(self, features_file, model_name):
        self.features_file = features_file
        self.model_name = model_name
        self.vectors_file = vectors_file_name(model_name)
        self.vectorizer_file = vectorizer_file_name(model_name)
        self.model_file = model_file_name(model_name)

    @timer
    def train(self):
        technologies, non_technologies = _read_seeds()
        self.technology_seeds = technologies
        self.non_technology_seeds = non_technologies
        self._create_examples()
        self._create_model()

    def _create_examples(self):
        """Given a file with feature bundle for each term and a list of positive and
        negative seeds, create a file with the vectors for the known positive
        and negative examples. Also create the model from the vectors."""
        print('Reading feature vectors and extracting pos and neg examples...')
        with open_file(self.features_file) as feats, \
             open_file(self.vectors_file, 'w') as vectors:
            for line in feats:
                try:
                    term = line.split('\t')[2]
                    label = self._get_label(term)
                    if label in ('y', 'n'):
                        vectors.write("%s\t%s" % (label, line))
                except Exception as e:
                    print('ERROR:',e)

    def _get_label(self, term):
        """Return 'y' if term is a known technology, 'n' if it is a known non-technology
        and '?' if it is both."""
        # TODO: this is very simplistic now, should check substrings too
        if term in self.technology_seeds and term in self.non_technology_seeds:
            return '?'
        elif term in self.technology_seeds:
            return 'y'
        elif term in self.non_technology_seeds:
            return 'n'
        else:
            return None

    def _create_model(self):
        print('Creating and saving the model and the vectorizer...')
        with open(self.vectors_file) as vectors:
            labels = []
            features = []
            for line in vectors:
                _, _, label, dictionary = _parse_line(line)
                labels.append(label)
                features.append(dictionary)
        vectorizer = DictVectorizer()
        feature_vectors = vectorizer.fit_transform(features)
        model = BernoulliNB()
        model.fit(feature_vectors, labels)
        dump(model, self.model_file)
        dump(vectorizer, self.vectorizer_file)


def _read_seeds():
    """Read all the lists of technologies and non-technologies and create a set for
    each of them."""
    technologies = set()
    non_technologies = set()
    for techlist in glob.glob("data/lists/tech-*.txt"):
        print('Reading', techlist)
        for line in open(techlist):
            tech = line.strip().lower()
            technologies.add(tech)
    for label_file in glob.glob("data/lists/labels-*.txt"):
        print('Reading', label_file)
        for line in open(label_file):
            try:
                (label, freq, tech) = line.rstrip().split('\t')
                if label == 'y':
                    technologies.add(tech.strip().lower())
                elif label == 'n':
                    non_technologies.add(tech.strip().lower())
            except:
                print('WARNING:\n%s' % line, end='')
    return technologies, non_technologies


def _parse_line(line):
    """Parses a line in one of the following formats

    <filename> <tab> <offsets> <tab> <term> <tab> <features>
    <label> <tab> <filename> <tab> <offsets> <tab> <term> <tab> <features>

    Returns the term, the location of the terms (file name plus offsets), the
    label (which will be None for the first format), and a dictionary of all
    features creates from the feature bundle string.

    """
    fields = line.rstrip().split('\t')
    if len(fields) == 5:
        label, doc, offsets, term, feats = fields
    else:
        label = None
        doc, offsets, term, feats = fields
    location = "%s:%s" % (doc, offsets)
    dictionary = {}
    for feat in feats.split():
        # TODO: must turn values for some features into integers
        feat, val = feat.split('=', 1)
        dictionary[feat] = val
    return term, location, label, dictionary


class Classifier(object):

    """Classifier that uses the model handed in on initialization or the default
    default model. Runs on a file or a directory."""

    DEFAULT_MODEL = 'data/models/SensorData'

    def __init__(self, model_name=None):
        """Initilialze with the model name."""
        self.name = None
        self.model = None
        self.vectorizer = None
        self._load_model()

    def _load_model(self, model_name=None):
        if model_name is None:
            model_name = Classifier.DEFAULT_MODEL
        if self.model is None:
            self.name = model_name
            self.model = load(model_file_name(model_name))
            self.vectorizer = load(vectorizer_file_name(model_name))

    def run(self, inpath, outpath, n=sys.maxsize):
        if exists(outpath):
            exit("Warning: output already exists")
        elif isdir(inpath):
            self.classify_directory(inpath, outpath)
        elif isfile(inpath):
            self.classify_file(inpath, outpath)

    def classify_directory(self, inpath, outpath, n=sys.maxsize):
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        with logger.Logger() as log:
            fnames = list(sorted(os.listdir(inpath)))
            for c, fname in enumerate(fnames[:n]):
                infile = os.path.join(inpath, fname)
                outfile = os.path.join(outpath, fname)
                log.write_line(fname, c)
                try:
                    self.classify_file(infile, outfile)
                except Exception as e:
                    log.write_error(e)
                    log.write('ERROR: %s\n' % e)
            log.write_time_elapsed()

    def classify_file(self, lif_file, out_file):
        lif = LIF(json_string=read_file(lif_file))
        self.classify_lif(lif)
        lif.write(fname=out_file, pretty=True)

    def classify_lif(self, lif):
        tech_view = lif.get_view('technologies')
        if tech_view is None:
            tech_view = View('technologies')
            tech_view.add_contains("http://vocab.lappsgrid.org/Technology")
            lif.views.append(tech_view)
        for anno in lif.get_view('terms').annotations:
            vector = anno.features.get('vector')
            if vector is None:
                continue
            # create a line with dummy values so we can reuse _parse_line
            line = "LABEL\tDOC\tP1:P2\t%s\t%s" % (anno.text, vector)
            _, _, _, dictionary = _parse_line(line)
            feature_vectors = self.vectorizer.transform([dictionary])
            label = self.model.predict(feature_vectors[0])
            if label == 'y':
                tech_view.annotations.append(AnnotationFactory.technology_annotation(anno))

    def run_on_vectors(self, vectors_file, labels_file):
        """Generate a lable for all vectors in the file. Useful for batch processing of
        a large number of vectors from some corpus. Results are written one label per
        line to the standard output."""
        with open(vectors_file) as vectors, open(labels_file, 'w') as labels:
            features = []
            feature_vectors = []
            for line in vectors:
                _, _, _, dictionary = _parse_line(line)
                features.append(dictionary)
                feature_vectors.append(self.vectorizer.transform([dictionary]))
            for instance in feature_vectors:
                labels.write(self.model.predict(instance)[0] + '\n')


def classify_vectors(model_name, vectors_file, labels_file):
    """Generate a lable for all vectors in the file. Useful for batch processing of
    a large number of vectors from some corpus. Results are written one label per
    line to the standard output."""
    model = load(model_file_name(model_name))
    vectorizer = load(vectorizer_file_name(model_name))
    with open(vectors_file) as vectors, open(labels_file, 'w') as labels:
        features = []
        feature_vectors = []
        for line in vectors:
            _, _, _, dictionary = _parse_line(line)
            features.append(dictionary)
            feature_vectors.append(vectorizer.transform([dictionary]))
        for instance in feature_vectors:
            labels.write(model.predict(instance)[0] + '\n')


if __name__ == '__main__':

    if sys.argv[1] == '--get-features':
        corpus = sys.argv[2]
        outfile = sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else sys.maxsize
        get_features(corpus, outfile, n)

    elif sys.argv[1] == '--train':
        features = sys.argv[2]
        model = sys.argv[3]
        Trainer(features, model).train()

    elif sys.argv[1] == '--classify':
        model = sys.argv[2]
        inpath = sys.argv[3]
        outpath = sys.argv[4]
        Classifier(model).run(inpath, outpath)

    elif sys.argv[1] == '--classify-vectors':
        model = sys.argv[2]
        vectors = sys.argv[3]
        labels = sys.argv[4]
        Classifier(model).run_on_vectors(vectors, labels)

    else:
        print("Nothing to do.")
