# Relation and clustering experiments

Beyond the main script this directory also includes some experiments on terms.

### Collecting relations

First there is a script to collect files from a corpus created by the main script and then gets all terms and roles and relations between them.

```bash
$ python collect_relations.py LIMIT?
```

The optional limit parameter restricts the number of files to process. This script creates a file named `out-relations.txt`  with a paragraph for each set of relations in a sentence as follows:

    FNAME	/DATA/ttap/processed/SensorData/4Pi_microscope.lif.gz
    REL-TRM t193-t191 <TAB> divided <TAB> nsubjpass  <TAB> laser light
    REL-TRM t193-t198 <TAB> divided <TAB> agent pobj <TAB> beam splitter BS
    REL-STA t193-t191 <TAB> divided <TAB> nsubjpass  <TAB> light
    The laser light is divided by a beam splitter BS and directed by mirrors towards the two opposing objective lenses.
Not listed above but included in the output are all the dependency relations for the sentence.

### Collecting contexts

Now take the output of `collect_relations.py` and create files that list relations, terms and states and show their contexts following short dependency chains.

```bash
$ python collect_characterizations.py
```

This creates many files (see the script for a full list). One of those files is `out-context-state2term-az.txt` which shows for each state the 10 most frequent terms that it co-occurs with, ranked by frequency of the term:

```
4860  light   visible laser infrared image ultraviolet beam speed incident polarized 
4839  energy  thermal electrical kinetic high higher electrons photon lower electron 
4300  field   magnetic electric coil electrons electromagnetic view current electrical
3589  power   nuclear electric electrical solar high reactive microwave electricity
```

Not all terms are printed to make sure that each state with its context fits on one line.

### Clustering using the contexts

This runs on the output of `collect_characterizations.py`, but note that it assumes that the output lives in `data/saved` (which was used to store the data in the repository).

```bash
$ python cluster.py
```

It runs a k-means algorithm both with and without PCA. It prints progress to the standard output for each input file processed:

```
Running KMeans on data/saved/out-context-rel2state-az.txt
KMeans(algorithm='auto', copy_x=True, init='k-means++', max_iter=300,
       n_clusters=12, n_init=10, n_jobs=None, precompute_distances='auto',
       random_state=0, tol=0.0001, verbose=0)
Writing out-clusters-rel2state.txt
Writing out-clusters-pca-rel2state.txt
```

The start of the first of the two files is

```
 0  adjust affects alter attenuated attenuates avoiding beat burn check
    connect degrade divided dividing doubled driven driving eliminates
    energized exciting filters improved lock modulate modulated modulates
    multiplying operates propagates rotated rotating setting stabilize
    translate vibrate
 1  adjusted adjusting altered altering avoided balanced change changed
    changes decrease decreased decreases decreasing drop drops eliminated
    eliminating expanding illustrates opens raises raising reducing
    stimulated touch vary
```

