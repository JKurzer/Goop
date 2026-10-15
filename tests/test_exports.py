"""Fake-export-set tests (owner ruling 2026-10-15).

Pure machinery: name derivation off the canonical LINK multiset, words/sets
validation, spec wiring in gooplib.specs.build_section, and the visibility
measure. No MSVC needed here; the end-to-end build/pack assertions live in
test_build.py (skipped without a pinned toolchain).
"""
import pytest

from gooplib import bridging as br
from gooplib import GoopError
from gooplib.exports import (LINKS_PER_SET, count_visible, directed_form_counts,
                             export_names, names_digest, validate_export_words)
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
