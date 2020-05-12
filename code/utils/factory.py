from utils.lif import Annotation


def vocab(short_form):
    """Expand the annotation type name to the full URL."""
    return "http://vocab.lappsgrid.org/%s" % short_form


def make_annotation(prefix, atype, p1=None, p2=None):
    anno = Annotation({"id": Identifier.new(prefix), "@type": vocab(atype)})
    if p1 is not None and p2 is not None:
        anno.start = p1
        anno.end = p2
    return anno


class AnnotationFactory(object):

    @classmethod
    def reset(cls):
        Identifier.reset()

    @classmethod
    def sentence_annotation(cls, sent, doc):
        w1 = doc[sent.start]
        w2 = doc[sent.end - 1]
        return make_annotation('s', 'Sentence', w1.idx, w2.idx + len(w2))

    @classmethod
    def token_annotation(cls, token):
        p1 = token.idx
        p2 = token.idx + len(token.text)
        anno = make_annotation('t', 'Token', p1, p2)
        anno.features = {'word': token.text, 'pos': token.tag_, 'lemma': token.lemma_}
        anno.text = anno.features['word']
        return anno

    @classmethod
    def chunk_annotation(cls, noun_chunk):
        anno = make_annotation('nc', 'NounChunk',
                               noun_chunk.start_char, noun_chunk.end_char)
        anno.features = {"text": noun_chunk.text}
        anno.text = noun_chunk.text
        return anno

    @classmethod
    def dependency_structure_annotation(cls, dependencies):
        anno = make_annotation('depstruct', 'DependencyStructure')
        anno.features = {'dependencies': [dep.id for dep in dependencies]}
        return anno
        return Annotation(
            {"id": Identifier.new('depstruct'),
             "@type": vocab('DependencyStructure'),
             'features': {
                 'dependencies': [dep.id for dep in dependencies] }})

    @classmethod
    def dependency_annotation(cls, token, idx2id):
        anno = make_annotation('dep', 'Dependency')
        anno.features = {
            'label': token.dep_,
            'governor': idx2id.get(token.head.i),
            'dependent': idx2id.get(token.i),
            'text': "%s -> %s" % (token.head.text, token.text)}
        return anno
        return Annotation(
            {"id": Identifier.new('dep'),
             "@type": vocab('Dependency'),
             'features': {
                 'label': token.dep_,
                 'governor': idx2id.get(token.head.i),
                 'dependent': idx2id.get(token.i),
                 'text': "%s -> %s" % (token.head.text, token.text)}})

    @classmethod
    def term_annotation(cls, chunk_node, token_ids):
        # note that the features dictionary contains a pointer to the chunk that
        # the term occurs in as well as the offsets in that chunk
        noun_chunk = chunk_node.annotation
        tokens = [n.annotation for n in chunk_node.tokens]
        tokens_text = [t.text for t in tokens]
        # text is not taken from the chunk but from the tokens that are part of
        # it, same holds for the start and end character offsets
        text = ' '.join(tokens_text[token_ids[0]:token_ids[-1]+1])
        start = tokens[token_ids[0]].start
        end = tokens[token_ids[-1]].end
        anno = make_annotation('term', 'Term', start, end)
        anno.features = {"text": text,
                         "chunk_id": noun_chunk.id,
                         "chunk_offsets": "%s:%s" % (noun_chunk.start, noun_chunk.end),
                         "chunk_first": token_ids[0],
                         "chunk_last": token_ids[-1]}
        anno.text = noun_chunk.text
        return anno

    @classmethod
    def technology_annotation(cls, term_annotation):
        text = term_annotation.features.get('text')
        anno = make_annotation('tech', 'Technology',
                               term_annotation.start, term_annotation.end)
        anno.features = {"text": text }
        # TODO: do we need this one? (same for all the others)
        anno.text = text
        return anno

    @classmethod
    def state_annotation(cls, token_annotation):
        text = token_annotation.features.get('text')
        anno = make_annotation('st', 'State',
                               token_annotation.start, token_annotation.end)
        anno.features = {"tokenID": token_annotation.id, "text": text }
        # TODO: do we need this one? (same for all the others)
        anno.text = text
        return anno

    @classmethod
    def relation_annotation(cls, token_annotation):
        text = token_annotation.features.get('text')
        anno = make_annotation('st', 'Relation',
                               token_annotation.start, token_annotation.end)
        anno.features = {"tokenID": token_annotation.id, "text": text }
        # TODO: do we need this one? (same for all the others)
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
