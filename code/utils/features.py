"""features.py


Features used for FUSE (the ones with check marks have been implemented):

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
✓ prev_V         previous verb
  prev_VNP       previous verb with object: *[increase the speed] of the [computer]*
  prev_Npr       first noun_prep to the left of chunk, within 4 words
  prev_Jpr       first adj_prep to the left of chunk, within 4 words
✓ prev_J         adjective immediately before the candidate term
✓ suffix3        last three characters of the term
✓ suffix4        last four characters of the term
✓ suffix5        last five characters of the term

Notes:
- section_loc: not done because we have no document structure yet
- prev_V: we use the governor of the term instead
- prev_VNP: requires following back the dobj->prep->pobj dependencies
- prev_Npr: things like overview of, aspects of. differences between, approach
  to, analyis of, combination of, etcetera; probably following back prep->pobj
  dependencies
- prev_Jpr: things like such that, equivalent to, applicable to, followed by,
  more than, due to, different from, suitable for, equal to, dependent on,
  useful for, etcetera; probably following back prep->pobj dependencies


Features for subject technologies:

  in_title         term occurs in the title of the document
  in_title_h       ... same, but now for the head of the term
  in_title_un      ... same, but now for any unigram in the term
  in_title_bi      ... same, but now for any bigram in the term
  in_beginning     term occurs in the beginning of the document
  in_beginning_h   ... same, but now for the head of the term
  in_beginning_un  ... same, but now for any unigram in the term
  in_beginning_bi  ... same, but now for any bigram in the term
  freq             frequency of the term in the document
  freq_h           ... same, but now for the head of the term in the document
  freq_un          ... same, but now for any unigram of the term in the document
  freq_bi          ... same, but now for any bigram of the term in the document
  relpos           distribution of term, number for overal relative position
  relpos_h         ... same, but now for the head of the term
  relpos_un        ... same, but now for all unigrams of the term
  relpos_bi        ... same, but now for all bigrams of the term
  range            range over the document where the term occurs
  range_           ... same, but now for the head of the term
  range_u          ... same, but now for all unigrams of the term
  range_bi         ... same, but now for all bigrams of the term
  fan_out          how often does the term occur in any other term
  fan_out_h        ... same, but now for the head word
  fan_out_un       ... same, but now for any unigram in the term
  fan_out_bi       ... same, but now for any bigram in the term
  fan_in           how often do other terms occur in term
  fan_in_h         ... same, but now for the head word
  fan_in_un        ... same, but now for any unigram in the term
  fan_in_bi        ... same, but now for any bigram in the term

Notes:
- see ../../docs/subject-technology-features.md for more information
- need to figure out the relative importance of features
- all counts and frequencies are relative to the number of terms in the document
- all counts, frequencies and ranges are numbers from 0 to 100

"""

import textwrap


def add_term_features(graph, lif, verbose=False):
    """Pull features from the graph and add them as vectors to the terms in the LIF
    object. Terms are linked to NodeChunks in the graph via the chunk in the
    node and the chunk feature on the term."""
    chunk_idx = {}
    for chunk in graph.chunks:
        chunk_idx[chunk.annotation.id] = chunk
    for term in lif.get_view('terms').annotations:
        chunk = chunk_idx.get(term.features.get("chunk_id"))
        # TODO: this is code to skip some chunks, should be moved to where we
        # determine what chunks have terms in them and what there extends are
        if chunk.tokens[-1].annotation.features['pos'] == 'PRP':
            continue
        feats = extract_term_features(graph, chunk)
        atomify_features(feats)
        vector = ' '.join(["%s=%s" % (k, v) for k, v in feats.items()])
        term.features['vector'] = vector
        if verbose:
            for token in chunk.tokens:
                print(token.annotation, token.annotation.features)
            for line in textwrap.wrap(vector, width=90):
                print('   ', line)
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

