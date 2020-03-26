"""features.py


Features used for FUSE (theones with check marks havebeen implemented):

✓ sentence_loc   the token offsets in the sentence
  section_loc    the location in section
✓ prev_n3        previous three nominals
✓ next_n3        next three nominals
✓ prev_n2        previous two nominals
✓ next_n2        next two nominals
  next2_tags     next two tags
✓ first_word     first word of the candidate term
✓ last_word      last word of the candidate term
✓ plen           length of the candidate term
✓ tag_list       tag signature of the candidate term
✓  prev_V         previous verb
  prev_VNP       previous verb with object: *[increase the speed] of the [computer]*
  prev_Npr       first noun_prep to the left of chunk, within 4 words
  prev_Jpr       first adj_prep to the left of chunk, within 4 words
✓  prev_J         adjective immediately before the candidate term
✓  suffix3        last three characters of the term
✓  suffix4        last four characters of the term
✓  suffix5        last five characters of the term


Notes:

- section_loc: not done because we have no documenst structure yet

- prev_V: we use the governor of the term instead

- prev_VNP: requires following back the dobj->prep->pobj dependencies

- prev_Npr: things like overview of, aspects of. differences between, approach
  to, analyis of, combination of, etcetera; probably following back prep->pobj
  dependencies

- prev_Jpr: things like such that, equivalent to, applicable to, followed by,
  more than, due to, different from, suitable for, equal to, dependent on,
  useful for, etcetera; probably following back prep->pobj dependencies

"""


def add_term_features(graph, verbose=False):
    """Pull features from the graph and add them as vectors to the terms. All
    the nodes in the graphs include an annotation from the LIF object and
    therefore changing those annotations will also update the LIF object."""
    for term in graph.terms:
        if term.tokens[-1].annotation.features['pos'] == 'PRP':
            continue
        if verbose:
            print(term.annotation)
            for token in term.tokens:
                print('   ', token.annotation, token.annotation.features)
            print()
        feats = extract_term_features(graph, term)
        atomify_features(feats)
        vector = ' '.join(["%s=%s" % (k, v) for k, v in feats.items()])
        term.annotation.features['vector'] = vector
        if verbose:
            print(vector)
            print()

def extract_term_features(graph, term):
    head = term.tokens[-1].annotation
    features = {
        'sentence_loc': sentence_loc(term),
        'prev_n1': prev_n1(term),
        'prev_n2': prev_n2(term),
        'prev_n3': prev_n3(term),
        'next_n2': next_n2(term),
        'first_word': term.tokens[0].annotation.text,
        'last_word': head.text,
        'suffix3': head.text[-3:],
        'suffix4': head.text[-4:],
        'suffix5': head.text[-5:],
        'plen': len(term.tokens),
        'tag_list': tag_list(term),
        'prev_J': prev_J(term),
        'prev_Npr': None,
        'prev_Jpr': None }
    add_dependencies(term, features)
    return features


def atomify_features(features):
    for feat, val in features.items():
        if feat == 'sentence_loc':
            features[feat] = val[0]
        elif isinstance(val, list):
            features[feat] = '_'.join([str(e) for e in val])


def print_features(feats):
    for feat, val in feats.items():
        print("  %s=%s" % (feat, val))

def sentence_loc(term):
    return [tok.sentence_position for tok in term.tokens]


def prev_n1(term):
    """Gets the previous nominal."""
    return prev_nx(term, 1)


def prev_n2(term):
    """Gets the previous two nominals."""
    return prev_nx(term, 2)


def prev_n3(term):
    """Gets the previous three nominals."""
    return prev_nx(term, 3)


def prev_nx(term, x):
    """Gets the previous x nominals."""
    first_token = term.tokens[0]
    previous_token = first_token.previous
    answer = []
    while previous_token is not None and len(answer) < x:
        if previous_token.annotation.features['pos'].startswith('N'):
            answer.append(previous_token.annotation.text)
        previous_token = previous_token.previous
    return list(reversed(answer))


def next_n2(term):
    return next_n(term, 2)


def next_n(term, c):
    """Gets the next c tokens that are nominals."""
    last_token = term.tokens[-1]
    next_token = last_token.next
    answer = []
    while next_token is not None and len(answer) < c:
        if next_token.annotation.features['pos'].startswith('N'):
            answer.append(next_token.annotation.text)
        next_token = next_token.next
    return answer


def tag_list(term):
    return[t.annotation.features['pos'] for t in term.tokens]


def prev_J(term):
    # TODO: this may need to be revisited, at the moment the adjective is inside 
    # the technical term, needs to be outside of it
    previous_token = term.tokens[0].previous
    if (previous_token is not None
        and previous_token.annotation.features['pos'].startswith('J')):
        return previous_token.annotation.text
    toks = [t for t in term.tokens if t.annotation.features['pos'].startswith('J')]
    # NOTE: added this for now, it finds the adjective inside the term
    if toks:
        return toks[-1].annotation.text
    return None


def add_dependencies(term, features):
    """Add dependency information for the term. Now only adds the governor of the
    head of the term."""
    head_token = term.tokens[-1]
    label, governor = head_token.governor
    features["dep_%s" % label] = governor.annotation.text

