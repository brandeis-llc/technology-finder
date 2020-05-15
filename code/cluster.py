import sys
import textwrap

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
import matplotlib.pyplot as plt
import numpy as np


def get_features_and_vectors(fname, limit=sys.maxsize):
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
    elements, features, vectors = get_features_and_vectors(fname)
    kmeans = KMeans(n_clusters=k, random_state=0)
    kmeans.fit(vectors)
    return elements, kmeans


def print_results(elements, labels):
    clusters = {}
    for element, label in zip(elements, labels):
        clusters.setdefault(label, []).append(element)
    wrapper = textwrap.TextWrapper(initial_indent="")
    for label in sorted(clusters):
        elements_string = ' '.join(clusters[label])
        lines = wrapper.wrap(elements_string)
        print("%2d  %s" % (label, lines[0]))
        for line in lines[1:]:
            print("    %s" % line)


if __name__ == '__main__':

    fname = 'out-context-state2rel-az.txt'

    # finding appealing values for k
    # results_025 = batch_run_kmeans(fname, max_k=25)
    # plot(results_025)

    # print results for one of those values
    elements, kmeans = run_kmeans(fname, 11)
    print_results(elements, kmeans.labels_)
