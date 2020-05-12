"""graph.py

A simple graph intended to store information from a LIF object and to make
certain pieces of information needed for the ML features easily accessable. For
example, it should be easy to find the next three tokens, or the governing
token, or the part-of-speech or the last word of a term. Terms themselves do not
occur in the graph, but they all point to chunks in the graph.

Characteristics of the graph:

- It contains three kinds of nodes: token nodes, chunk nodes and sentence nodes.

- All nodes have unique identifiers and a node can be looked up in an index.

- The token nodes are a linked list, that is, the token points to both the
  previous and the next token.

- Each token node points at a sentence node and potentially at a chunk node

- Each chunk node points at a sentence node.

- Each sentence node contains a list of token nodes and a list of chunk nodes

- Each chunk node contains a list of token nodes.

- Each token node contains a link to the governing token (from a dependency
  parse) as well as a list of links to dependents. The links contain both the
  label of the dependency and the target token.

"""

def create_graph(lif_object):
    """Create a graph from a LIF object."""
    pos_view = lif_object.get_view('tokens')
    dep_view = lif_object.get_view('dependencies')
    chunk_view = lif_object.get_view('chunks')
    graph = Graph(lif_object)
    _add_markables(graph, pos_view, chunk_view)
    _add_dependencies(graph, dep_view)
    graph.connect()
    return graph


def _add_markables(graph, pos_view, chunk_view):
    """Add nodes to the graph from markables in the views (that is, tokens,
    sentences and chunks)."""
    for anno in pos_view.annotations:
        if anno.type.endswith('Sentence'):
            node = SentenceNode(pos_view.id, anno)
            graph.add_sentence(node)
        elif anno.type.endswith('Token'):
            node = TokenNode(pos_view.id, anno)
            graph.add_token(node)
    for chunk in chunk_view.annotations:
        chunk_node = ChunkNode(chunk_view.id, chunk)
        graph.add_chunk(chunk_node)


def _add_dependencies(graph, dep_view):
    """Fill in the governor and dependents variables on the tokens."""
    for dep in dep_view.annotations:
        if dep.type.endswith('DependencyStructure'):
            continue
        label = dep.features['label']
        gov = dep.features['governor']
        dep = dep.features['dependent']
        dep_node = graph.get_node(dep)
        gov_node = graph.get_node(gov)
        dep_node.governor = (label, gov_node)
        if not label == 'ROOT':
            gov_node.dependents.append((label, dep_node))


class Graph(object):
    
    def __init__(self, lif=None):
        # a list for each node category
        self.lif = lif
        self.sentences = []
        self.tokens = []
        self.chunks = []
        # and an index for all nodes
        self.nodes_idx = {}

    def get_node(self, node_id):
        """Get the node given the node identifier."""
        return self.nodes_idx.get(node_id)

    def get_annotation(self, node_id):
        """Get the annotation on a node given the node identifier."""
        return self.nodes_idx.get(node_id).annotation

    def add_token(self, node):
        if self.tokens:
            previous = self.tokens[-1]
            previous.next = node
            node.previous = previous
        self.tokens.append(node)
        self._add_node(node)

    def add_sentence(self, node):
        self.sentences.append(node)
        self._add_node(node)
        
    def add_chunk(self, node):
        self.chunks.append(node)
        self._add_node(node)
        
    def _add_node(self, node):
        self.nodes_idx[node.id] = node

    def connect(self):
        self._connect_sentences_and_tokens()
        self._connect_sentences_and_chunks()
        self._connect_chunks_and_tokens()
    
    def _connect_sentences_and_tokens(self):
        for sentence_node in self.sentences:
            s = sentence_node.annotation
            for (pos, n) in enumerate(self.tokens_in_range(s.start, s.end)):
                sentence_node.tokens.append(n)
                n.sentence = sentence_node
                n.sentence_position = pos

    def _connect_sentences_and_chunks(self):
        for sentence_node in self.sentences:
            s = sentence_node.annotation
            for n in self.chunks_in_range(s.start, s.end):
                sentence_node.chunks.append(n)
                n.sentence = sentence_node
    
    def _connect_chunks_and_tokens(self):
        for chunk_node in self.chunks:
            t = chunk_node.annotation
            for (pos, n) in enumerate(self.tokens_in_range(t.start, t.end)):
                chunk_node.tokens.append(n)
                n.chunk = chunk_node
                n.chunk_position = pos

    def tokens_in_range(self, p1, p2):
        """Get all tokens such that token.start >= p1 and token.end <= p2."""
        return self.nodes_in_range(self.tokens, p1, p2)

    def chunks_in_range(self, p1, p2):
        """Get all chunks such that chunk.start >= p1 and chunk.end <= p2."""
        return self.nodes_in_range(self.chunks, p1, p2)

    def nodes_in_range(self, nodes, p1, p2):
        """Get all nodes such that node.start >= p1 and node.end <= p2."""
        # TODO: this operates at O(n), but could be improved to run at O(logn)
        # TODO: using binary search (but only if nodes are ordered)
        answer = []
        for node in nodes:
            if node.annotation.end < p1:
                continue
            elif node.annotation.start >= p1 and node.annotation.end <= p2:
                answer.append(node)
            elif node.annotation.start > p2:
                break
        return answer

    def get_head_token(self, annotation):
        """Given an annotation, return the last token in the annotation."""
        tokens = self.tokens_in_range(annotation.start, annotation.end)
        return tokens[-1].annotation if tokens else None

    def print_chunks(self):
        for chunk_node in self.chunks:
            print(chunk_node.annotation)
            for token_node in chunk_node.tokens:
                print('   ', token_node.annotation)
            print()

    def print_sentences(self):
        for sent_node in self.sentences:
            print(sent_node.annotation)
            for token_node in sent_node.tokens:
                print('   ', token_node.annotation)
            for chunk_node in sent_node.chunks:
                print('   ', chunk_node.annotation)
            print()


class Node(object):

    """Abstract class for nodes. All nodes have in common that they ar eassociated
    with a single annotation type from the LIF object."""
    
    def __init__(self, view_id, annotation):
        self.id = "%s:%s" % (view_id, annotation.id)
        self.annotation = annotation

    def __str__(self):
        return "NODE %s :: %s" % (self.id, self.annotation)


class TokenNode(Node):

    """Implements a token node in the graph.
    
    Instance variables that implement links in the graph:

      previous    -  None or a TokenNode
      next        -  None of a TokenNode
      sentence    -  a SentenceNode
      chunk       -  None or a ChunkNode
      governor    -  a <label, TokenNode> pair
      dependents  -  a list of <label, TokenNode> pairs
    
    Other instance variables:

      sentence_position  -  the position in the sentence (0-based)
      chunk_position     -  the position in the chunk (0-based)

    """
    
    def __init__(self, view_id, annotation):
        super().__init__(view_id, annotation)
        self.previous = None
        self.next = None
        self.sentence = None
        self.sentence_position = None
        self.chunk = None
        self.chunk_position = None
        self.governor = None
        self.dependents = []

    def pp(self):
        print(self.annotation)
        print('    SENT ', self.sentence.annotation)
        if self.previous is not None:
            print('    PREV ', self.previous.annotation)
        if self.next is not None:
            print('    NEXT ', self.next.annotation)
        print('    <-- ', self.governor[0], self.governor[1].annotation)
        for dependent in self.dependents:
            print('    --> ', dependent[0], dependent[1].annotation)


class SentenceNode(Node):

    """Implements a token node in the graph.
    
    Instance variables that implement links in the graph:

      tokens   -  a list of token nodes contained in the sentence
      chunks   -  a list of chunk nodes contained in the sentence

    """
    
    def __init__(self, view_id, annotation):
        super().__init__(view_id, annotation)
        self.tokens = []
        self.chunks = []


class ChunkNode(Node):

    """Implements a token node in the graph.
    
    Instance variables that implement links in the graph:

      tokens    -  a list of token nodes contained in the chunk
      sentence  -  a SentenceNode

    """

    def __init__(self, view_id, annotation):
        super().__init__(view_id, annotation)
        self.tokens = []
        self.sentence = None
