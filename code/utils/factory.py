from utils.lif import Annotation
from utils.misc import vocab, Identifier


class AnnotationFactory(object):

    @classmethod
    def sentence_annotation(cls, sent, doc):
        w1 = doc[sent.start]
        w2 = doc[sent.end - 1]
        p1 = w1.idx
        p2 = w2.idx + len(w2)
        return Annotation(
            {"id": Identifier.new('s'),
             "@type": vocab('Sentence'),
             'start': p1,
             'end': p2})

    @classmethod
    def token_annotation(cls, token):
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

    @classmethod
    def dependency_structure_annotation(cls, dependencies):
        return Annotation(
            {"id": Identifier.new('depstruct'),
             "@type": vocab('DependencyStructure'),
             'features': {
                 'dependencies': [dep.id for dep in dependencies] }})

    @classmethod
    def dependency_annotation(cls, token, idx2id):
        return Annotation(
            {"id": Identifier.new('dep'),
             "@type": vocab('Dependency'),
             'features': {
                 'label': token.dep_,
                 'governor': idx2id.get(token.head.i),
                 'dependent': idx2id.get(token.i),
                 'text': "%s -> %s" % (token.head.text, token.text)}})

    @classmethod
    def term_annotation(cls, noun_chunk):
        anno = Annotation(
            {"id": Identifier.new('term'),
             "@type": vocab('Term'),
             "start": noun_chunk.start_char,
             "end": noun_chunk.end_char,
             "features": {
                 "text": noun_chunk.text}})
        anno.text = noun_chunk.text
        return anno
