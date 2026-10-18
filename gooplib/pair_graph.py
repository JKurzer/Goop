"""Pair-aligned, canonical five-plus-set graph values (no I/O).

The two long graph values encode the SAME ordered canonical LINKs, as bare
bigrams and directed edges respectively. The short value repeats the role
trigram once per complete set; it is a label, not a substitute for the sets.
"""
from gooplib.bridging import CANONICAL_CONFIGS
from gooplib.exports import link_texts


def pair_graph_values(words, sets):
    """Build graph values from complete, ordered hainish/delete/file sets."""
    if isinstance(sets, bool) or not isinstance(sets, int) or not 5 <= sets <= 99:
        raise ValueError('graph requires 5-99 complete canonical sets')
    links = link_texts(words, sets)  # validates roles and canonical ordering
    assert len(links) == 2 * len(CANONICAL_CONFIGS) * sets
    trigram = ' '.join(words[role] for role in
                       ('anchor', 'target', 'destination'))
    return {
        'trigram_sets': ' | '.join([trigram] * sets),
        'full_graph': ' '.join(links),
        'full_graph_directed': ' '.join(link.replace(' ', '>')
                                        for link in links),
    }
