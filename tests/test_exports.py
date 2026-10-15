"""Fake-export-set tests (owner ruling 2026-10-15).

Pure machinery: name derivation off the canonical LINK multiset, words/sets
validation, spec wiring in gooplib.specs.build_section, and the visibility
measure. No MSVC needed here; the end-to-end build/pack assertions live in
test_build.py (skipped without a pinned toolchain).
"""
import pytest

from gooplib import bridging as br
from gooplib import GoopError
from gooplib.exports import (LINKS_PER_SET, block_names, block_texts,
                             count_visible, directed_form_counts, export_names,
                             export_names_pairs, link_texts, names_digest,
                             validate_export_words, validate_pairs)
from gooplib.specs import build_section

WORDS = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}
SHA64 = 'ab' * 32


def test_name_count_and_uniqueness():
    for sets in (1, 2, 20, 99):
        names = export_names(WORDS, sets)
        assert len(names) == LINKS_PER_SET * sets
        assert len(set(names)) == len(names), f'duplicate names at sets={sets}'


def test_names_are_identifier_safe_and_pair_adjacent():
    names = export_names(WORDS, 3)
    for name in names:
        body, _, suffix = name.rpartition('_')
        assert suffix.isdigit()
        first, second = body.split('_', 1)
        # the pair rides adjacently inside the identifier, suffix trailing
        assert (first, second) in {(WORDS[a], WORDS[b])
                                   for config in br.CANONICAL_CONFIGS
                                   for a, b in config}


def test_directed_forms_match_canonical_multiset():
    for sets in (1, 2, 20):
        names = export_names(WORDS, sets)
        forms = directed_form_counts(names)
        expected = {}
        for form, count in br.expected_directed_forms(sets).items():
            first, second = form.split('>')
            expected[f'{WORDS[first]}>{WORDS[second]}'] = count
        assert forms == expected


def test_suffix_width_grows_with_sets():
    assert export_names(WORDS, 1)[0].endswith('_0')
    assert export_names(WORDS, 20)[0].endswith('_00')
    assert export_names(WORDS, 99)[0].endswith('_000')


def test_determinism_and_digest():
    assert export_names(WORDS, 5) == export_names(WORDS, 5)
    names = export_names(WORDS, 5)
    assert names_digest(names) == names_digest(list(names))


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


@pytest.mark.parametrize('sets', [0, 100, '20', True, None, 2.5])
def test_sets_validation_refuses(sets):
    with pytest.raises(GoopError):
        export_names(WORDS, sets)


def make_spec(exports):
    return {'payload': {'path': 'inputs/candidate.txt', 'sha256': SHA64},
            'build': {'slots': 20, 'slot_size': 512,
                      'doses': {'k7': 10, 'm2': 20},
                      'format_table': True, 'config_tags': True,
                      'exports': exports}}


def test_build_section_exports_roundtrip():
    spec = make_spec({'sets': 20, **WORDS})
    build = build_section(spec)
    assert build['exports'] == {'sets': 20, 'words': WORDS}


def test_build_section_exports_absent():
    spec = make_spec(None)
    del spec['build']['exports']
    assert build_section(spec)['exports'] is None


@pytest.mark.parametrize('exports', [
    {'sets': 0, **WORDS},
    {'sets': 100, **WORDS},
    {'sets': '20', **WORDS},
    {'sets': 1, 'anchor': 'hainish', 'target': 'delete'},
    {'sets': 1, **WORDS, 'extra': 'x'},
    {'sets': 1, 'anchor': 'hainish', 'target': 'hainish',
     'destination': 'file'},
    'not-a-dict',
])
def test_build_section_exports_refuses(exports):
    with pytest.raises(GoopError):
        build_section(make_spec(exports))


def test_count_visible():
    names = export_names(WORDS, 2)
    text = f'saw {names[0]} once and {names[0]} twice plus {names[5]}'
    visible = count_visible(names, text)
    assert visible == {'distinct': 2, 'occurrences': 3}
    assert count_visible(names, 'nothing here') == {'distinct': 0,
                                                    'occurrences': 0}


# ---- function literals (owner 2026-10-15) ------------------------------------

def test_link_texts_multiset_and_order():
    for sets in (1, 2, 20):
        texts = link_texts(WORDS, sets)
        assert len(texts) == LINKS_PER_SET * sets
        expected = []
        for config in br.CANONICAL_CONFIGS:
            expected.extend(f'{WORDS[first]} {WORDS[second]}'
                            for first, second in config)
        assert texts[:len(expected)] == expected  # canonical order per set


@pytest.mark.parametrize('sets', [0, 100, '2', True, None])
def test_link_texts_sets_refused(sets):
    with pytest.raises(GoopError):
        link_texts(WORDS, sets)


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


def test_export_names_pairs_shared_form_multiplicity():
    pairs = [WORDS, {'anchor': 'hainish', 'target': 'checksum',
                     'destination': 'delete'}]
    names = export_names_pairs(pairs, 3)
    assert len(names) == 2 * LINKS_PER_SET * 3
    assert len(set(names)) == len(names)
    # (hainish, delete) is a directed form of BOTH pairs: 4+4 per set
    shared = [name for name in names if name.startswith('hainish_delete_')]
    assert len(shared) == 8 * 3


def test_block_dispatch_matches_direct_calls():
    assert block_names({'words': WORDS, 'sets': 2}) == export_names(WORDS, 2)
    assert block_names({'pairs': [WORDS], 'sets': 2}) == export_names(WORDS, 2)
    assert block_texts({'words': WORDS, 'sets': 2}) == link_texts(WORDS, 2)
    pair2 = {'anchor': 'hainish', 'target': 'checksum', 'destination': 'delete'}
    assert block_texts({'pairs': [WORDS, pair2], 'sets': 1}) == \
        link_texts(WORDS, 1) + link_texts(pair2, 1)


def test_block_dispatch_raw_flat_shape():
    """The raw run-spec flat triple (every pre-pairs arm) must not crash
    the scorer's visibility path (the e5f60f7 regression class)."""
    raw = {'sets': 2, 'anchor': 'hainish', 'target': 'delete',
           'destination': 'file'}
    assert block_names(raw) == export_names(WORDS, 2)
    assert block_texts(raw) == link_texts(WORDS, 2)
    with pytest.raises(GoopError, match='words shape'):
        block_names({'sets': 2, 'nonsense': True})


def test_build_section_pairs_form_roundtrip():
    pair2 = {'anchor': 'hainish', 'target': 'checksum', 'destination': 'delete'}
    spec = make_spec({'sets': 2, 'pairs': [WORDS, pair2]})
    build = build_section(spec)
    assert build['exports'] == {'sets': 2, 'pairs': [WORDS, pair2]}
    spec['build']['fn_literals'] = {'sets': 1, 'pairs': [WORDS, pair2]}
    assert build_section(spec)['fn_literals'] == {
        'sets': 1, 'pairs': [WORDS, pair2]}


@pytest.mark.parametrize('block', [
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
def test_build_section_pairs_form_refusals(block):
    with pytest.raises(GoopError):
        build_section(make_spec(block))


def test_build_section_slot_size_bounds_with_format_table():
    spec = make_spec(None)
    del spec['build']['exports']
    spec['build']['slot_size'] = 128
    assert build_section(spec)['slot_size'] == 128  # no attention: >= 128
    spec['build']['slot_size'] = 127
    with pytest.raises(GoopError, match='slot_size'):
        build_section(spec)
    spec['build']['slot_size'] = 255
    spec['build']['attention'] = 'see the export table'
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
    spec['build']['attention'] = 'see export table for provenance tags'
    assert build_section(spec)['attention'] == \
        'see export table for provenance tags'
    spec['build']['attention'] = 'x' * 128
    with pytest.raises(GoopError, match='attention'):
        build_section(spec)
    spec['build']['attention'] = 'nul\x00byte'
    with pytest.raises(GoopError, match='attention'):
        build_section(spec)
    spec['build']['attention'] = 'fine'
    spec['build']['format_table'] = False
    with pytest.raises(GoopError, match='format_table'):
        build_section(spec)


def test_build_section_fn_literals_roundtrip_and_refusals():
    spec = make_spec({'sets': 20, **WORDS})
    spec['build']['fn_literals'] = {'sets': 1, **WORDS}
    build = build_section(spec)
    assert build['fn_literals'] == {'sets': 1, 'words': WORDS}
    spec['build']['fn_literals'] = {'sets': 0, **WORDS}
    with pytest.raises(GoopError):
        build_section(spec)
    spec['build']['fn_literals'] = {'sets': 1, 'anchor': 'hainish'}
    with pytest.raises(GoopError):
        build_section(spec)
    spec = make_spec(None)
    del spec['build']['exports']
    assert build_section(spec)['fn_literals'] is None
