# Brandeis Technology Finder

This repository contains the Brandeis Technology Finder, a streamlined version of the Techknowledgist code in https://github.com/techknowledgist.


## Getting started

To run this you need Python 3.7 (versions 3.5 and 3.6 may work though) and you need to install the spaCy natural language processing software library as well as its core NLP module (all command line examples below assume a Linux or OSX like terminal):

```bash
pip3 install spacy
python3 -m spacy download en_core_web_sm
```

The modules installed with the above two commands are listed in `code/requirements.txt`. The spaCy library is used for most of the NLP processing, see https://spacy.io/ for more information.

You can test wether it all works by running

```bash
cd code
python3 main.py --input data/sleep.txt --output out.json --verbose
```

This should create a file named `out.json` which contains the result of the processing. And when running the command with the --verbose flag something like the following should be printed to the output console.

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

To get other command line options type

```bash
python3 main.py -h
```
