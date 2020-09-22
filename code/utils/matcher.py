import re


NN = 'NN'
NNS = 'NNS'
NNP = 'NNP'
NNPS = 'NNPS'
POS = 'POS'
JJ = 'JJ'
JJR = 'JJR'
JJS = 'JJS'
FW = 'FW'

en_jj_vb_noise = set(l.strip()
                     for l in open("data/lists/en_jj_vb.noise").readlines())

PATTERN = [ [ [NN, {"fig", "figure"}], [NNP, {"fig", "figure"}], NNS, NNPS,
              [JJ, en_jj_vb_noise], [JJR, {"more"}], [JJS, {"most"}],
              POS, [FW, {"e.g.", "i.e"}] ],
            [ NN, NNP, NNS, NNPS ] ]

DEBUG = False


def match(chunk):
    """Match the chunk to the pattern in the PATTERN global. Return the list of
    offsets that match, if there is no match then the empty list is returned."""
    word_list = [t.annotation.text for t in chunk.tokens]
    pos_list = [t.annotation.features.get('pos') for t in chunk.tokens]
    tokens = list(zip(word_list, pos_list))
    result = _match_pattern(tokens, PATTERN)
    _debug('\n%s %s' % (' '.join(pos_list), ' '.join(word_list)))
    _debug(result)
    return result


def _match_pattern(tokens, pattern):

    # check whether last token matches pattern end, may want to reinterpret this
    # into finding the last token that matches
    matches = []
    result = _match_element(tokens[-1], pattern[-1], len(tokens) - 1)
    if result is True:
        matches.append(len(tokens) - 1)
    else:
        return []

    # consume elements before the last token, going right to left, compare to
    # first element of pattern
    for i in reversed(range(0, len(tokens) - 1)):
        result = _match_element(tokens[i], pattern[0], i)
        _debug('    %s' % result)
        if result:
            matches.append(i)
        else:
            break
    return list(reversed(matches))


def _match_element(token_pos, pattern_element, i):
    _debug('  %s %s' % (i, token_pos))
    for disjunction in pattern_element:
        if _match_disjunction(token_pos, disjunction, i):
            return True
    return False


def _match_disjunction(token_pos, disjunction, i):
    if isinstance(disjunction, list):
        pos = disjunction[0]
        exceptions = disjunction[1]
    else:
        pos = disjunction
        exceptions = set()
    result = token_pos[1] == pos and token_pos[0] not in exceptions
    _debug('    %s %s %s' % (token_pos[1], pos, result))
    return result


def _debug(string):
    if DEBUG:
        print(string)
