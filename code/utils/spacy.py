"""spacy.py

Wrapper around the spaCy module. Runs spaCy processing and exports instances of
utils.lif.Annotations from the analysis.

"""

import spacy
from utils.factory import AnnotationFactory


DEBUG = True


NLP = None

def load_model(model_name):
    global NLP
    NLP = spacy.load(model_name)


class SpacyAnalysis(object):

    def __init__(self, text, model="en_core_web_sm"):
        # Use the already loaded model if there is one. As a result this assumes
        # a previous instance of the class used the same model. Use load_model()
        # to change the model after a first instantiation of SpacyAnalysis.
        if NLP is None:
            load_model(model)
        # We are doing this because spaCy misses document initial nounchunks if
        # the document starts with a space character.
        self.leading_spaces = len(text) - len(text.lstrip())
        self.doc = NLP(text[self.leading_spaces:])

    def annotations(self, token_view_id):
        """Return three lists of annotations, one with the Sentence and Token
        annotations, one with the NounChunk annotations and one with the
        DependencyStructure and Dependency annotations."""
        self.token_annotations = []
        self.chunk_annotations = []
        self.dependency_annotations = []
        self._debug_newline()
        for sent in self.doc.sents:
            # note that self.doc.sents can only be looped over once
            idx2id = {}
            self._collect_annotations_tokens(sent, token_view_id, idx2id)
            self._collect_annotations_dependencies(sent, idx2id)
            self._debug_newline()
        self._collect_annotations_chunks()
        self._adjust_annotation_offsets()
        return (self.token_annotations,
                self.chunk_annotations,
                self.dependency_annotations)

    def _collect_annotations_tokens(self, sentence, token_view_id, idx2id):
        anno = AnnotationFactory.sentence_annotation(sentence, self.doc)
        self.token_annotations.append(anno)
        for token in sentence:
            tok_annotation = AnnotationFactory.token_annotation(token)
            self.token_annotations.append(tok_annotation)
            idx2id[token.i] = "%s:%s" % (token_view_id, tok_annotation.id)
            self._debug_token(token, tok_annotation)

    def _collect_annotations_dependencies(self, sentence, idx2id):
        """Loop through the tokens again and create the dependency for each of
        them, using the index created in the previous loop for access to the
        identifiers. Then, when we know what dependencies we have for the
        dependency structure, create the structure and add it and then add all
        dependencies."""
        dep_annos = []
        for token in sentence:
            dep_annotation = AnnotationFactory.dependency_annotation(token, idx2id)
            dep_annos.append(dep_annotation)
        dep_struct = AnnotationFactory.dependency_structure_annotation(dep_annos)
        self.dependency_annotations.append(dep_struct)
        for dep_anno in dep_annos:
            self.dependency_annotations.append(dep_anno)

    def _collect_annotations_chunks(self):
        for chunk in self.doc.noun_chunks:
            anno = AnnotationFactory.chunk_annotation(chunk)
            self.chunk_annotations.append(anno)
            
    def _adjust_annotation_offsets(self):
        """This is needed because spacy analysis had to be done after removing
        initial whitespace in the document."""
        for annotations in (self.token_annotations, self.chunk_annotations):
            for annotation in annotations:
                annotation.start += self.leading_spaces
                annotation.end += self.leading_spaces

    def _debug_token(self, token, tok_annotation):
        if DEBUG:
            print("%2s  %2s  %2s  %3s  %-12s  %-5s    %-8s  %-10s  %2s  %s"
                  % (token.idx, token.idx + len(token.text), token.i, tok_annotation.id,
                     token.text.strip(), token.pos_, token.tag_,
                     token.dep_, token.head.i, token.head.text))

    def _debug_newline(self):
        if DEBUG:
            print()

