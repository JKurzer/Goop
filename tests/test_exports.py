"""fn_literals machinery tests.

The fake-export-table arm is DELETED (owner ruling 2026-10-15, verbatim:
"I don't care about over priming. remove the existing exports, go ahead
and build the cargo strings."). This file now covers the surviving
gooplib.exports surface: link_texts derivation off the canonical LINK
multiset, words/sets/pairs validation, spec wiring in
gooplib.specs.build_section, and the visibility measure. Cargo-string
tests live in test_strings.py; end-to-end build/pack assertions live in
test_build.py (skipped without a pinned toolchain).
"""
import pytest

from gooplib import bridging as br
from gooplib import GoopError
from gooplib.exports import (block_leaf_words, block_texts, count_visible,
                             link_texts, names_digest, validate_export_words,
                             validate_pairs)
from gooplib.specs import build_section

WORDS = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}
SHA64 = 'ab' * 32
LINKS_PER_SET = len(br.CANONICAL_CONFIGS) * 2


@pytest.mark.parametrize('bad', [
    {'anchor': 'Hainish', 'target': 'delete', 'destination': 'file'},
    {'anchor': 'hain ish', 'target': 'delete', 'destination': 'file'},
    {'anchor': '9hainish', 'target': 'delete', 'destination': 'file'},
    {'anchor': 'hainish', 'target': 'hainish', 'destination': 'file'},
    {'anchor': 'hainish', 'target': 'delete'},
    {'anchor': 'hainish', 'target': 'delete', 'destination': 'file',
     'extra': 'x'},
])
def test_words_validation_refuses(bad):
    with pytest.raises(GoopError):
        validate_export_words(bad)


# ---- function literals (owner 2026-10-15) ----------------------------------

def test_link_texts_multiset_and_order():
    for sets in (1, 2, 20):
        texts = link_texts(WORDS, sets)
        assert len(texts) == LINKS_PER_SET * sets
        expected = []
        for config in br.CANONICAL_CONFIGS:
            expected.extend(f'{WORDS[first]} {WORDS[second]}'
                            for first, second in config)
        assert texts[:len(expected)] == expected  # canonical order per set
    assert len(set(texts)) < len(texts)  # sets repeat the canonical stream


@pytest.mark.parametrize('sets', [0, 100, '2', True, None])
def test_link_texts_sets_refused(sets):
    with pytest.raises(GoopError):
        link_texts(WORDS, sets)


def test_link_texts_determinism_and_digest():
    assert link_texts(WORDS, 5) == link_texts(WORDS, 5)
    texts = link_texts(WORDS, 5)
    assert names_digest(texts) == names_digest(list(texts))


def test_validate_pairs_rules():
    pairs = validate_pairs([WORDS, {'anchor': 'hainish', 'target': 'checksum',
                                    'destination': 'delete'}])
    assert len(pairs) == 2  # one shared leaf (delete): the chaining limit
    with pytest.raises(GoopError, match='nonempty'):
        validate_pairs([])
    with pytest.raises(GoopError, match='share one anchor'):
        validate_pairs([WORDS, {'anchor': 'teleology', 'target': 'checksum',
                                'destination': 'delete'}])
    with pytest.raises(GoopError, match='share leaves'):
        validate_pairs([WORDS, {'anchor': 'hainish', 'target': 'file',
                                'destination': 'delete'}])


def test_block_dispatch_matches_direct_calls():
    assert block_texts({'words': WORDS, 'sets': 2}) == link_texts(WORDS, 2)
    pair2 = {'anchor': 'hainish', 'target': 'checksum', 'destination': 'delete'}
    assert block_texts({'pairs': [WORDS, pair2], 'sets': 1}) == \
        link_texts(WORDS, 1) + link_texts(pair2, 1)


def test_block_dispatch_raw_flat_shape():
    """The raw run-spec flat triple (every pre-pairs arm) must not crash
    the scorer's visibility path (the e5f60f7 regression class)."""
    raw = {'sets': 2, 'anchor': 'hainish', 'target': 'delete',
           'destination': 'file'}
    assert block_texts(raw) == link_texts(WORDS, 2)
    with pytest.raises(GoopError, match='words shape'):
        block_texts({'sets': 2, 'nonsense': True})


def test_block_leaf_words():
    assert block_leaf_words({'sets': 1, **WORDS}) == {'delete', 'file'}
    pair2 = {'anchor': 'hainish', 'target': 'checksum', 'destination': 'delete'}
    assert block_leaf_words({'sets': 1, 'pairs': [WORDS, pair2]}) == {
        'delete', 'file', 'checksum'}  # the anchor is never a leaf


def test_count_visible():
    texts = link_texts(WORDS, 2)
    text = f'saw {texts[0]} once and {texts[0]} twice plus {texts[5]}'
    visible = count_visible(texts, text)
    assert visible == {'distinct': 2, 'occurrences': 3}
    assert count_visible(texts, 'nothing here') == {'distinct': 0,
                                                    'occurrences': 0}


# ---- spec wiring ------------------------------------------------------------

def make_spec(fn_literals=None):
    build = {'slots': 20, 'slot_size': 512,
             'doses': {'k7': 10, 'm2': 20},
             'format_table': True, 'config_tags': True}
    if fn_literals is not None:
        build['fn_literals'] = fn_literals
    return {'payload': {'path': 'inputs/candidate.txt', 'sha256': SHA64},
            'build': build}


def test_build_section_fn_literals_roundtrip():
    build = build_section(make_spec({'sets': 20, **WORDS}))
    assert build['fn_literals'] == {'sets': 20, 'words': WORDS}


def test_build_section_fn_literals_absent():
    assert build_section(make_spec())['fn_literals'] is None


def test_build_section_pairs_form_roundtrip():
    pair2 = {'anchor': 'hainish', 'target': 'checksum', 'destination': 'delete'}
    build = build_section(make_spec({'sets': 2, 'pairs': [WORDS, pair2]}))
    assert build['fn_literals'] == {'sets': 2, 'pairs': [WORDS, pair2]}


@pytest.mark.parametrize('block', [
    {'sets': 0, **WORDS},
    {'sets': 100, **WORDS},
    {'sets': '20', **WORDS},
    {'sets': 1, 'anchor': 'hainish', 'target': 'delete'},
    {'sets': 1, **WORDS, 'extra': 'x'},
    {'sets': 1, 'anchor': 'hainish', 'target': 'hainish',
     'destination': 'file'},
    'not-a-dict',
    {'sets': 2, 'pairs': 'not-a-list'},
    {'sets': 2, 'pairs': []},
    {'sets': 2, 'pairs': [WORDS, WORDS, WORDS]},
    {'sets': 2, 'pairs': [{'anchor': 'hainish', 'target': 'delete'}]},
    {'sets': 2, 'pairs': [WORDS, {'anchor': 'teleology', 'target': 'x',
                                  'destination': 'y'}]},
    {'sets': 2, 'pairs': [WORDS, {'anchor': 'hainish', 'target': 'file',
                                  'destination': 'delete'}]},
    {'sets': 2, 'pairs': [WORDS], 'anchor': 'hainish'},
])
def test_build_section_link_block_refusals(block):
    with pytest.raises(GoopError):
        build_section(make_spec(block))


def test_build_section_slot_size_bounds_with_format_table():
    spec = make_spec()
    spec['build']['slot_size'] = 128
    assert build_section(spec)['slot_size'] == 128  # no attention: >= 128
    spec['build']['slot_size'] = 127
    with pytest.raises(GoopError, match='slot_size'):
        build_section(spec)
    spec['build']['slot_size'] = 255
    spec['build']['attention'] = 'see the slot table'
    with pytest.raises(GoopError, match='slot_size'):
        build_section(spec)  # attention: needs >= 256
    spec['build']['slot_size'] = 256
    assert build_section(spec)['slot_size'] == 256
    spec['build']['slot_size'] = 64
    spec['build']['format_table'] = False
    del spec['build']['attention']
    assert build_section(spec)['slot_size'] == 64  # unconstrained otherwise


def test_build_section_attention():
    spec = make_spec({'sets': 2, **WORDS})
    spec['build']['attention'] = 'see the slot table for provenance tags'
    assert build_section(spec)['attention'] == \
        'see the slot table for provenance tags'
    spec['build']['attention'] = 'x' * 128
    with pytest.raises(GoopError, match='attention'):
        build_section(spec)
    spec['build']['attention'] = 'nul\x00byte'
    with pytest.raises(GoopError, match='attention'):
        build_section(spec)
