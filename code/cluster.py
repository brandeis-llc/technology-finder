"""cluster.py

This clustering script is meant to run on one of the files where a term, state
or relation is mapped with its restricted context from one of the other three
types.

That input is assumed to be created by collect_characterization.py. Examples are
in data/saved, for example, out-context-rel2state-nr.txt can be used to cluster
relations on the states they occur with.

"""

import os
import sys
import glob
import textwrap

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import CountVectorizer
import matplotlib.pyplot as plt
import numpy as np


def get_features_and_vectors(fname, limit=sys.maxsize):
    """Get elements, features and vectors. Elements are the things we want to
    cluster, features are texts containing terms from the context, separated by
    spaces, and vectors are created by CountVectorizer)."""
    elements_list = []
    features_list = []
    c = 0
    for line in open(fname):
        if line.startswith('DICTIONARY') or not line.strip():
            continue
        c += 1
        if c > limit:
            break
        frequency, element, features = line.strip().split('\t')
        elements_list.append(element.strip())
        features_list.append(features)
    vectors_list = get_vectors(features_list)
    # print("Reading data file results in %s vectors." % len(vectors_list))
    return elements_list, features_list, vectors_list

def get_vectors(features):
    vectorizer = CountVectorizer()
    vectorizer.fit(features)
    vectors = []
    for feats in features:
        vectors.append(vectorizer.transform([feats]).toarray()[0])
    return np.array(vectors)


def batch_run_kmeans(fname, min_k=1, max_k=50):
    """Run kmeans for a range of k values and collect the inertia measure for each of them."""
    elements, features, vectors = get_features_and_vectors(fname)
    results = []
    for k in range(min_k, max_k + 1):
        print(k, end=' ')
        kmeans = KMeans(n_clusters=k, random_state=0)
        kmeans.fit(vectors)
        results.append([k, kmeans.inertia_])
    return results


def plot(results):
    k_values = [i for i, j in results]
    inertia_values = [int(j) for i, j in results]
    plt.plot(k_values, inertia_values)
    plt.xlabel('k')
    plt.ylabel('inertia')
    #plt.axis([min(k_values), max(k_values), 0, max(inertia_values), ])
    plt.show()


def run_kmeans(fname, k):
    """Run kmeans over the file named fname and write results to two two files
    named out-clusters-<fname>.txt and out-clusters-pca-<fname>.txt. For the
    second one run PCA before clustering. Returns the list of elements, the
    vectors, the reduced vectors, and the two kmeans instances."""
    elements, features, vectors = get_features_and_vectors(fname)
    # run on original vector
    kmeans1 = KMeans(n_clusters=k, random_state=0)
    print(kmeans1)
    kmeans1.fit(vectors)
    clusters_file = "out-clusters-%s.txt" % fname.split('-')[2]
    print_results_to_file(elements, kmeans1, clusters_file)
    # now run PCA first
    pca = PCA(n_components=2)
    pca.fit(vectors)
    reduced_vectors = pca.transform(vectors) 
    kmeans2 = KMeans(n_clusters=k, random_state=0)
    kmeans2.fit(reduced_vectors)
    clusters_file = "out-clusters-pca-%s.txt" % fname.split('-')[2]
    print_results_to_file(elements, kmeans2, clusters_file)
    return elements, vectors, reduced_vectors, kmeans1, kmeans2


def print_results_to_file(elements, kmeans, fname):
    with open(fname, 'w') as fh:
        print("Writing %s" % fname)
        print_results(elements, kmeans, fh=fh)


def print_results(elements, kmeans, fh=sys.stdout):
    labels = kmeans.labels_
    clusters = {}
    for element, label in zip(elements, labels):
        clusters.setdefault(label, []).append(element)
    wrapper = textwrap.TextWrapper(initial_indent="")
    for label in sorted(clusters):
        elements_string = ' '.join(clusters[label])
        lines = wrapper.wrap(elements_string)
        fh.write("%2d  %s\n" % (label, lines[0]))
        for line in lines[1:]:
            fh.write("    %s\n" % line)


def find_k_value(fname, max_k=25):
    """Finding appealing values for k."""
    results = batch_run_kmeans(fname, max_k)
    plot(results)


if __name__ == '__main__':

    fname = 'data/saved/out-context-state2rel-az.txt'
    # find_k_value(fname, max_k=25)
    # run_kmeans(fname, 11, write=True)

    for fname in glob.glob('data/saved/out-context-*2*-az.txt'):
        print("Running KMeans on %s" % fname)
        run_kmeans(fname, 12)
