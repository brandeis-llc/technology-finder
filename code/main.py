import sys
import json
import argparse

import spacy

from lif import LIF, View, Annotation
from utils import vocab, Identifier
from graph import create_graph
from features import add_term_features


NLP = None

def load_spacy():
    global NLP
    NLP = spacy.load("en_core_web_sm")


def run(infile, outfile, verbose=False):
    """Run the technology code on the infile. At the moment this does only two
    things: (1) run the basic NLP processing and (2) extract the feature vectors
    for terms. Returns the spacy analysis, the LIF document and the graph that
    was created from it."""
    
    # creating a LIF object, loading the text and adding views
    lif = create_lif(infile)

    # running the spaCy NLP model and adding NLP analysis elements as
    # annotations to the LIF object
    doc = NLP(lif.text.value)
    add_annotations(doc, lif, verbose=verbose)
    add_term_annotations(doc, lif)

    # creating a graph from the LIF object
    graph = create_graph(lif)
    if verbose:
        graph.print_sentences()

    # pulling features from the graph and adding them as a vector to the term
    add_term_features(graph, verbose=verbose)

    write_lif_output(lif, outfile)

    return doc, lif, graph


def write_lif_output(lif, outfile):
    """Save the LIF object into outfile or write it to standard output if outfile is
    equal to None."""
    json_string = lif.as_json_string()
    if outfile is not None:
        with open(outfile, 'w') as fh:
            fh.write(json_string)
    else:
        print(json_string)
        

def create_lif(fname):
    """Create a new LIF object, load the textinto it and initialize three views."""
    lif = LIF()
    lif.text.value = open(fname).read()
    tok_view = View("tokens")
    dep_view = View("dependencies")
    term_view = View("terms")
    lif.views.extend([tok_view, dep_view, term_view])
    return lif


def get_sentence_annotations(doc):
    annotations = []
    for s in doc.sents:
        w1 = doc[s.start]
        w2 = doc[s.end - 1]
        p1 = w1.idx
        p2 = w2.idx + len(w2)
        annotations.append(create_sentence_annotation(s, doc))
    return annotations


def collect_sentences_and_tokens(doc):
    """Return a list of sentences where each sentence is a list of tokens as
    extracted from the document, which is an instance of spacy.tokens.doc.Doc."""
    sentences = []
    for s in doc.sents:
        sentence = []
        sentences.append(sentence)
        for t in s:
            sentence.append(t)
    return sentences


def create_sentence_annotation(sent, doc):   
    w1 = doc[sent.start]
    w2 = doc[sent.end - 1]
    p1 = w1.idx
    p2 = w2.idx + len(w2)
    return Annotation(
        {"id": Identifier.new('s'),
         "@type": vocab('Sentence'),
         'start': p1,
         'end': p2})


def create_token_annotation(token):
    anno = Annotation(
        {"id": Identifier.new('t'),
         "@type": vocab('Token'),
         'start': token.idx,
         'end': token.idx + len(token.text),
         'features': {
                'word': token.text,
                'pos': token.tag_}})
    anno.text = anno.features['word']
    return anno


def create_dependency_structure_annotation(dependencies):
    return Annotation(
        {"id": Identifier.new('depstruct'), 
         "@type": vocab('DependencyStructure'),
         'features': {
                'dependencies': [dep.id for dep in dependencies] }})


def create_dependency_annotation(token, idx2id):
    return Annotation(
        {"id": Identifier.new('dep'), 
         "@type": vocab('Dependency'),
         'features': {
                'label': token.dep_,
                'governor': idx2id.get(token.head.i),
                'dependent': idx2id.get(token.i),
                'text': "%s -> %s" % (token.head.text, token.text)}})


def create_term_annotation(noun_chunk):
    anno = Annotation(
        {"id": Identifier.new('term'),
         "@type": vocab('Term'),
         "start": noun_chunk.start_char,
         "end": noun_chunk.end_char,
         "features": {
             "text": noun_chunk.text}})
    anno.text = noun_chunk.text
    return anno


def add_annotations(doc, lif, verbose=False):
    """Add annotations from the spacy.tokens.doc.Doc instance to the part of speech
    and dependency views."""

    pos_view = lif.get_view("tokens")
    dep_view = lif.get_view("dependencies")

    for annotation in get_sentence_annotations(doc):
        pos_view.annotations.append(annotation)

    for sentence in collect_sentences_and_tokens(doc):

        # first pass: create all token annotations and add them and build an
        # index from the sentence offsets to the token identifiers
        idx2id = {}
        for token in sentence:
            tok_annotation = create_token_annotation(token)
            pos_view.annotations.append(tok_annotation)
            idx2id[token.i] = "%s:%s" % (pos_view.id, tok_annotation.id)
            if verbose:
                print("%2s  %2s  %2s  %3s  %-12s  %-5s    %-8s  %-10s  %2s  %s" 
                      % (token.idx, token.idx + len(token.text), token.i, tok_annotation.id,
                         token.text.strip(), token.pos_, token.tag_,
                         token.dep_, token.head.i, token.head.text))    

        # second pass: loop through the tokens again and create the dependency
        # for each of them (but not adding them to the view yet), using the
        # index created in the previous loop to ave access to the identifiers
        dep_annos = []
        for token in sentence:
            dep_annotation = create_dependency_annotation(token, idx2id)
            dep_annos.append(dep_annotation)

        # now we know what dependencies we have for the dependency structure,
        # create the structure and add it and then add all dependencies
        dep_struct = create_dependency_structure_annotation(dep_annos)
        dep_view.annotations.append(dep_struct)
        for dep_anno in dep_annos:
            dep_view.annotations.append(dep_anno)

        if verbose:
            print()


def add_term_annotations(doc, lif):
    """Add candidate terms as annotations. For now we just use the noun chunks from
    the spaCy analysis."""
    # TODO: filter out some chunks, like proper names
    # TODO: if term has 1 element and last element is pos=PRP
    # TODO: problem, at this point we do not have that information since
    # TODO: all we have is the span and it is not linked to the tokens yet
    term_view = lif.get_view("terms")
    for term in doc.noun_chunks:
        anno = create_term_annotation(term)
        term_view.annotations.append(anno)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    input_help = "the file to process"
    output_help = "the output file, print to standard output if not specified"
    verbose_help = "print some created data structures to standard output"
    parser.add_argument("--input", help=input_help, required=True)
    parser.add_argument("--output", help=output_help)
    parser.add_argument("--verbose", help=verbose_help, action="store_true")
    args = parser.parse_args()

    load_spacy()
    output = args.output if args.output is not None else 'out.json'
    run(args.input, args.output, verbose=args.verbose)
