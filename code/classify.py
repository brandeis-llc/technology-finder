"""classify.py

Contains code related to the term classifier. Included feature extraction from a
processed corpus, model creation and classification.


== feature extraction

$ python3 classify.py --get-features PROCESSED_CORPUS FEATURES_FILE N?

Collect all term feature vectors from PROCESSED_CORPUS and writes them to
FEATURES_FILE. Limit to N files if the third argument is present, default is to
process all files.

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

$ python3 classify.py --classify-vectors MODEL_FILE VECTORS_FILE

Run the classifier saved in MODEL_FILE on a file with vectors. Labels are
written to the standard output, one label per line.

"""


import os
import sys
import glob
import gzip
import time
from collections import Counter
from operator import itemgetter

import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.naive_bayes import BernoulliNB
from joblib import dump, load

from utils import timestamp, read_file, open_file
from utils.lif import LIF, View
from utils.factory import AnnotationFactory


class Vector(object):

    def __init__(self, fname, term):
        # TODO: not sure whether I want/need the offsets here
        # TODO: may not even need the file name
        self.vector = (os.path.basename(fname),
                       "%s:%s" % (term.start, term.end),
                       term.get_text(),
                       term.features['vector'])

    def __str__(self):
        return "\t".join(self.vector)


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
    with open(features_file, 'w') as fh_features, \
          open('terms-az.txt', 'w') as fh_terms, \
          open('terms-nr.txt', 'w') as fh_counts:
        terms = {}
        print("$ python3 %s\n" % ' '.join(sys.argv))
        t0 = time.time()
        for (i, fname) in enumerate(glob.glob("%s/*" % directory)[:n]):
            print("%05d  %s  %s" % (i + 1, timestamp(), os.path.basename(fname)))
            content = read_file(fname)
            lif = LIF(json_string=content)
            for term in lif.get_view('terms').annotations:
                text = term.get_text()
                if text is not None:
                    text = text.strip().replace("\n", ' ')
                    terms[text] = terms.get(text, 0) + 1
                if 'vector' in term.features:
                    vector = Vector(fname, term)
                    fh_features.write("%s\n" % vector)
        print("\nTime elapsed: %d seconds\n" % int(time.time() - t0))
        fh_terms.write("%s\n" % '\n'.join(sorted(terms)))
        for (term, count) in reversed(sorted(terms.items(), key=itemgetter(1))):
            fh_counts.write("%-4d\t%s\n" % (count, term))


def train(features_file, model_name):
    technologies, non_technologies = _read_lists()
    _create_examples(features_file, model_name, technologies, non_technologies)
    _create_model(model_name)


def _read_lists():
    """Read lists of technologies and non-technologies."""
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


def _create_examples(features_file, model_name, technologies, non_technologies):
    """Given a file with feature bundle for each term and a list of positive and
    negative seeds, create a file with the vectors for the known positive and
    negative examples. Also create the model from the vectors."""
    vectors_file = vectors_file_name(
        model_name)
    print('Reading feature vectors and extracting pos and neg examples...')
    with open_file(features_file) as feats, \
         open_file(vectors_file, 'w') as vectors:
        for line in feats:
            try:
                term = line.split('\t')[2]
                label = _get_label(term, technologies, non_technologies)
                if label is not None:
                    vectors.write("%s\t%s" % (label, line))
            except IndexError:
                pass


def _get_label(term, technologies, non_technologies):
    """Return 'y' if term is a known technology, 'n' if it is a known non-technology
    and '?' if it is both."""
    # TODO: this is very simplistic now, should check substrings too
    if term in technologies and term in non_technologies:
        return '?'
    elif term in technologies:
        return 'y'
    elif term in non_technologies:
        return 'n'
    else:
        return None


def _create_model(model_name):
    vectors_file = vectors_file_name(model_name)
    vectorizer_file = vectorizer_file_name(model_name)
    model_file = model_file_name(model_name)
    print('Creating and saving the model and the vectorizer...')
    with open(vectors_file) as vectors:
        labels = []
        features = []
        for line in vectors:
            _, _, label, dictionary = _parse_line(line)
            labels.append(label)
            features.append(dictionary)
        vectorizer = DictVectorizer()
        feature_vectors = vectorizer.fit_transform(features)
    model_bernoulli = BernoulliNB()
    model_bernoulli.fit(feature_vectors, labels)
    dump(model_bernoulli, model_file)
    dump(vectorizer, vectorizer_file)


def _parse_line(line):
    label, doc, offsets, term, feats = line.rstrip().split('\t')
    location = "%s:%s" % (doc, offsets)
    dictionary = {}
    for feat in feats.split():
        # TODO: must turn values for some features into integers
        feat, val = feat.split('=', 1)
        dictionary[feat] = val
    return term, location, label, dictionary


MODEL = None
VECTORIZER = None

DEFAULT_MODEL_NAME = 'data/models/SensorData'


def load_model(model_name = None):
    global MODEL, VECTORIZER
    if model_name is None:
        model_name = DEFAULT_MODEL_NAME
    if MODEL is None:
        MODEL = load(model_file_name(model_name))
        VECTORIZER = load(vectorizer_file_name(model_name))

def classify_file(model_name, lif_file, out_file):
    load_model(model_name)
    lif = LIF(json_string=read_file(lif_file))
    classify_lif(model_name, lif)
    lif.write(fname=out_file, pretty=True)

def classify_lif(model_name, lif):
    load_model(model_name)
    tech_view = View('technologies')
    lif.views.append(tech_view)
    for anno in lif.get_view('terms').annotations:
        vector = anno.features.get('vector')
        if vector is None:
            continue
        # create a line with dummy values so we can reuse _parse_line
        line = "LABEL\tDOC\tP1:P2\t%s\t%s" % (anno.text, vector)
        _, _, _, dictionary = _parse_line(line)
        feature_vectors = VECTORIZER.transform([dictionary])
        label = MODEL.predict(feature_vectors[0])
        if label == 'y':
            tech_view.annotations.append(AnnotationFactory.technology_annotation(anno))

def classify_vectors(model_name, vectors_file):
    """Generate a lable for all vectors in the file. Useful for batch processing of
    a large number of vectors from some corpus. Results are written one label per
    line to the standard output."""
    model = load(model_file_name(model_name))
    with open(vectors_file) as vectors:
        features = []
        for line in vectors:
            _, _, _, dictionary = _parse_line(line)
            features.append(dictionary)
        vectorizer = DictVectorizer()
        feature_vectors = vectorizer.fit_transform(features)
    for instance in feature_vectors:
        print(model.predict(instance)[0])


if __name__ == '__main__':

    if sys.argv[1] == '--get-features':
        corpus = sys.argv[2]
        outfile = sys.argv[3]
        n = int(sys.argv[4]) if len(sys.argv) > 4 else sys.maxsize
        get_features(corpus, outfile, n)

    elif sys.argv[1] == '--train':
        features = sys.argv[2]
        model = sys.argv[3]
        train(features, model)

    elif sys.argv[1] == '--classify':
        model = sys.argv[2]
        infile = sys.argv[3]
        outfile = sys.argv[4]
        classify_file(model, infile, outfile)

    elif sys.argv[1] == '--classify-vectors':
        model = sys.argv[2]
        vectors = sys.argv[3]
        classify_vectors(model, vectors)

    else:
        pass
