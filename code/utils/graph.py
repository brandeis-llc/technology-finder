"""graph.py

A simple graph intended to store information from a LIF object and to make
certain pieces of information needed for the ML features easily accessable. For
example, it should be easy to find the next three tokens, or the governing
token, or the part-of-speech or the last word of a term.

Characteristics of the graph:

- It contains three kinds of nodes: token nodes, term nodes and sentence nodes.

- All nodes have unique identifiers and a node can be looked up in an index.

- The token nodes are a linked list, that is, the token points to both the
  previous and the next token.

- Each token node points at a sentence node and potentially at a term node

- Each term node points at a sentence node.

- Each sentence node contains a list of token nodes and a list of term nodes

- Each term node contains a list of token nodes.

- Each token node contains a link to the governing token (from a dependency
  parse) as well as a list of links to dependents. The links contain both the
  label of the dependency and the target token.

"""

def create_graph(lif_object):
    """Create a graph from a LIF object."""
    pos_view = lif_object.get_view('tokens')
    dep_view = lif_object.get_view('dependencies')
    term_view = lif_object.get_view('terms')
    graph = Graph()
    _add_markables(graph, pos_view, term_view)
    _add_dependencies(graph, dep_view)
    graph.connect()
    return graph


def _add_markables(graph, pos_view, term_view):
    """Add nodes to the graph from markables in the views (that is, tokens,
    sentences and terms).""" 
    for anno in pos_view.annotations:
        if anno.type.endswith('Sentence'):
            node = SentenceNode(pos_view.id, anno)
            graph.add_sentence(node)
        elif anno.type.endswith('Token'):
            node = TokenNode(pos_view.id, anno)
            graph.add_token(node)
    for term in term_view.annotations:
        term_node = TermNode(term_view.id, term)
        graph.add_term(term_node)


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
    
    def __init__(self):
        # a list for each node category
        self.sentences = []
        self.tokens = []
        self.terms = []
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
        
    def add_term(self, node):
        self.terms.append(node)
        self._add_node(node)
        
    def _add_node(self, node):
        self.nodes_idx[node.id] = node

    def connect(self):
        self._connect_sentences_and_tokens()
        self._connect_sentences_and_terms()
        self._connect_terms_and_tokens()
    
    def _connect_sentences_and_tokens(self):
        for sentence_node in self.sentences:
            s = sentence_node.annotation
            for (pos, n) in enumerate(self.tokens_in_range(s.start, s.end)):
                sentence_node.tokens.append(n) 
                n.sentence = sentence_node
                n.sentence_position = pos

    def _connect_sentences_and_terms(self):
        for sentence_node in self.sentences:
            s = sentence_node.annotation
            for n in self.terms_in_range(s.start, s.end):
                sentence_node.terms.append(n) 
                n.sentence = sentence_node
    
    def _connect_terms_and_tokens(self):
        for term_node in self.terms:
            t = term_node.annotation
            for (pos, n) in enumerate(self.tokens_in_range(t.start, t.end)):
                term_node.tokens.append(n)
                n.term = term_node
                n.term_position = pos

    def tokens_in_range(self, p1, p2):
        """Get all tokens such that token.start >= p1 and token.end <= p2."""
        return self.nodes_in_range(self.tokens, p1, p2)

    def terms_in_range(self, p1, p2):
        """Get all terms such that term.start >= p1 and term.end <= p2."""
        return self.nodes_in_range(self.terms, p1, p2)

    def nodes_in_range(self, nodes, p1, p2):
        """Get all nodes such that node.start >= p1 and node.end <= p2."""
        # TODO: this operates at O(n), but could be improved to run at O(logn)
        answer = []
        for node in nodes:
            if node.annotation.end < p1:
                continue
            elif node.annotation.start >= p1 and node.annotation.end <= p2:
                answer.append(node)
            elif node.annotation.start > p2:
                break
        return answer

    def print_terms(self):
        for term_node in self.terms:
            print(term_node.annotation)
            for token_node in term_node.tokens:
                print('   ', token_node.annotation)
            print()

    def print_sentences(self):
        for sent_node in self.sentences:
            print(sent_node.annotation)
            for token_node in sent_node.tokens:
                print('   ', token_node.annotation)
            for term_node in sent_node.terms:
                print('   ', term_node.annotation)
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
      term        -  None or a TermNode
      governor    -  a <label, TokenNode> pair
      dependents  -  a list of <label, TokenNode> pairs
    
    Other instance variables:

      sentence_position  -  the position in the sentence (0-based)
      term_position      -  the position in the term (0-based)

    """
    
    def __init__(self, view_id, annotation):
        super().__init__(view_id, annotation)
        self.previous = None
        self.next = None
        self.sentence = None
        self.sentence_position = None
        self.term = None
        self.term_position = None
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
      terms    -  a list of term nodes contained in the sentence

    """
    
    def __init__(self, view_id, annotation):
        super().__init__(view_id, annotation)
        self.tokens = []
        self.terms = []


class TermNode(Node):
    
    """Implements a token node in the graph.
    
    Instance variables that implement links in the graph:

      tokens    -  a list of token nodes contained in the term
      sentence  -  a SentenceNode

    """
        
    def __init__(self, view_id, annotation):
        super().__init__(view_id, annotation)
        self.tokens = []
        self.sentence = None
