# Brandeis Technology Finder

This repository contains the Brandeis Technology Finder, a streamlined version of the Techknowledgist code in https://github.com/techknowledgist.




## Installation

To run this you need at least Python 3.7 (versions 3.5 and 3.6 may work though) and you need to install (1) the spaCy natural language processing software library and its core NLP module and (2) the scikit-learn machine learning package (all command line examples below assume a Linux or OSX like terminal):

```bash
$ pip3 install spacy
$ python3 -m spacy download en_core_web_sm
$ pip3 install sklearn
```

The spaCy library is used for most of the basic NLP processing and scikit-learn is used for the actual classification, see https://spacy.io/ and https://scikit-learn.org/ for more information.



## Extracting technologies

You can test wether it all works by running the main script on one of the example input files:

```bash
$ cd code
$ python3 main.py -i data/input/sleep.txt -o out.lif --verbose
```

The -i and -o options specify the input and the output. The input file is assumed to be a text file. The command above should create a file named "out.lif" which contains the result of the processing in the LIF format, a JSON-LD format used by the LAPPS Grid (see http://wiki.lappsgrid.org/interchange/). And when running the command with the --verbose flag something like the following should be printed to the output console.

```
 0   4   0   t1  Jane          PROPN    NNP       compound     1  Doe
 5   8   1   t2  Doe           PROPN    NNP       nsubj        2  sleeps
 9  15   2   t3  sleeps        VERB     VBZ       ROOT         2  sleeps
15  16   3   t4  .             PUNCT    .         punct        2  sleeps
16  17   4   t5                SPACE    _SP                    3  .

<Sentence s1 0-17 ''>
   <Token t1 0-4 'Jane'>
   <Token t2 5-8 'Doe'>
   <Token t3 9-15 'sleeps'>
   <Token t4 15-16 '.'>
   <Token t5 16-17 '\n'>
   <Term term1 0-8 'Jane Doe'>

<Term term1 0-8 'Jane Doe'>
   <Token t1 0-4 'Jane'> {'word': 'Jane', 'pos': 'NNP'}
   <Token t2 5-8 'Doe'> {'word': 'Doe', 'pos': 'NNP'}

sentence_loc=0 prev_n1= prev_n2= prev_n3= next_n2= first_word=Jane last_word=Doe suffix3=Doe suffix4=Doe suffix5=Doe plen=2 tag_list=NNP_NNP prev_J=None prev_Npr=None prev_Jpr=None dep_nsubj=sleeps
```

The actual output file is saved in this repository as [code/data/out/sleep.txt](code/data/out/sleep.txt). When you open that file you will see the LIF format which has four top-level attributes, two of which are "text" and "views". The first one contains the text and the second a list of views on the text where each view has an identifier and a list of annotations over the text. See http://wiki.lappsgrid.org/interchange/ for more information on this format.

There are no technologies in this input file so you can not see that the code also tries to classify terms as technologies and non-technologies and that it creates a new view with the technologies. To see this at work run the code on another larger file:

```bash
$ python3 main.py -i data/input/auger-architectomics.txt -o out2.lif
```

The output file will have a non-empty view with technologies. Note that the technology classifier is in a very early incarnation and that its performance is still very poor.

The script can also run on a directory:

```bash
$ python3 main.py -i data/input -o out --limit 2
```

In this case the first two document in "data/input" will be processed and the results will be put in the "out" directory, which may not exist already. Without the "--limit" option all files will be processed.



## Advanced use

The "main.py" runs the feature extraction and classification on one file or one folder, and while doing that it uses the rather small default model. This section lays out how to separate the feature extraction from the technology classification and how to create bigger classifier models.

### Separating feature extraction and classification

This separation can be useful when the basic processing that extracts features is stable while the classification may include experimentation with many models. To separate feature extraction from classification you can first run the main script in non-classification mode:

```bash
$ python3 main.py -i data/input/auger-architectomics.txt -o out.feats --classifier-off
$ python3 classify.py --classify data/models/SensorData out.feats out.class
```

In the first step the file "data/input/auger-architectomics.txt" will be processed and the output will be put in "out-feats", but that file will only have the basic features: tokens, sentences, dependencies and terms with feature vectors. There is no view with technologies. In the second step you add the technologies by running the classifier script. It needs to explicitely specify what classifier model to use (unlike the main script for which this model was assumed to be the default). It takes the file that was just processed by the main script and writes the output to a LIF file that has a technologies view added.

You can do the same on a directory:

```bash
$ python3 main.py -i data/input -o out.dir.feats --classifier-off
$ python3 classify.py --classify data/models/SensorData out.dir.feats out.dir.class
```

In addition to creating the files it will also write log comments to the standard output.

The code offers a third way to classify files wherefor the classification you first extract all vectors and then run a classifier on those vectors:

```bash
$ python3 main.py -i data/input -o out.dir.feats --classifier-off
$ python3 classify.py --get-features out.dir.feats out.file.feats
$ python3 classify.py --classify-vectors data/models/SensorData out.file.feats out.file.lbl
```

The files "out.file.feats" and "out.file.lbl" will have the same amount of lines.

### Space considerations

One disadvantage of the LIF format is that it takes a lot of space. For example, the example file "auger-architectomics.txt" is only about 300 bytes, but the result after processing is about 50K, more than a hundred times larger.

Files are not compressed when written to disk, but can be compressed manually afterwards. When the classifier needs to read the files in a directory it will recognize that a file was compressed (it checks for a .gz extension) and it can read the file. compressed or not.

### Building classifier models

To build a model you first process a directory and extract its features:

```bash
$ python3 main.py -i data/input -o out.dir.feats --classifier-off
$ python classify.py --get-features out.dir.feats/ out.file.feats
```

The directory "out.dr.feats" will have LIF files that all include all the candidate terms (candicates for being technologies that is) and the feature vectors associated with them. The file "out.file.feats" has all the features extracted from the files.

We can now train the classifier model which can be used by the classifier.

```bash
$ python3 classify.py --train out.file.feats data/models/test
```

This code is now very rigid and does not allow any feature engineering. It should be expanded.
