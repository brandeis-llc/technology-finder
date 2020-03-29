from utils.lif import Annotation


def vocab(short_form):
    """Expand the annotation type name to the full URL."""
    return "http://vocab.lappsgrid.org/%s" % short_form


class AnnotationFactory(object):

    @classmethod
    def reset(cls):
        Identifier.reset()

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

    @classmethod
    def technology_annotation(cls, term_annotation):
        text = term_annotation.features.get('text')
        anno = Annotation(
            {"id": Identifier.new('tech'),
             "@type": vocab('Technology'),
             "start": term_annotation.start,
             "end": term_annotation.end,
             "features": {
                 "text": text }})
        # TODO: why do I have both of these?
        anno.text = text
        return anno


class Identifier(object):

    """Class to keep track of what identifiers have been used."""

    COUNTS = {}

    @classmethod
    def reset(cls):
        cls.COUNTS = {}

    @classmethod
    def new(cls, prefix):
        cls.COUNTS[prefix] = cls.COUNTS.get(prefix, 0) + 1
        return "%s%s" % (prefix, cls.COUNTS[prefix])
