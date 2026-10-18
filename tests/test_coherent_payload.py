"""Regression tests for the owner's filler + one graph + pair-only contract."""
import copy
import hashlib
import json

import pytest

from gooplib.coherent_payload import (complete_delivery, from_excerpt,
                                      validate_binary, validate_unit,
                                      without_parentheses)
from tools.goop_coherent_candidate import RUNTIME_COPIES, make_spec, saved_delivery

SOURCE = (
    'All that is done (hainish and file) is done, and all that is done cannot be (hainish and delete) undone.  \r\n'
    '(hainish and file) The (hainish and delete) cat sat on the mat.  \r\n'
    'The seeds fell deep (file and hainish) and the seeds grew and the seeds grew (delete and hainish) tall.  \r\n'
    'The cat (delete and hainish) stayed near the door and the dog ran (hainish and file) home at dusk.  \r\n'
).encode('ascii')
UNIT = from_excerpt(SOURCE)


def test_only_link_conjunctions_and_line_endings_change():
    expected = SOURCE.decode('ascii').replace('\r\n', '\n')
    for pair in ('hainish and file', 'file and hainish',
                 'hainish and delete', 'delete and hainish'):
        expected = expected.replace('(' + pair + ')', '(' + pair.replace(' and ', ' ') + ')')
    assert UNIT == expected
    assert sum(validate_unit(UNIT).values()) == 8
    assert 'and all that' in UNIT
    assert without_parentheses(UNIT) == UNIT.replace('(', '').replace(')', '')


@pytest.mark.parametrize('replacement', [
    'hainish>file', '(hainish and file)', '(hainish team)', '(file delete)',
    '(hainish file delete)', 'hainish file', 'GRAPH (hainish file)',
])
def test_bad_link_or_self_label_is_rejected(replacement):
    with pytest.raises(ValueError):
        validate_unit(UNIT.replace('(hainish file)', replacement, 1))


def test_exact_single_event_delivery_not_split_or_label_dependent():
    assert complete_delivery('stdout:\n' + UNIT * 10 + 'SUMMARY\n', UNIT, 10)
    assert complete_delivery((UNIT * 10).replace('\n', '\r\n'), UNIT, 10)
    assert not complete_delivery(UNIT * 9, UNIT, 10)
    assert not complete_delivery(UNIT * 9 + UNIT[:-10], UNIT, 10)
    assert not complete_delivery((UNIT * 10).replace('(hainish file)', 'hainish>file'), UNIT, 10)


def test_binary_cannot_contain_a_second_graph_or_unfilled_link():
    binary = b'\0'.join(row.encode() for row in UNIT.splitlines()) + b'\0'
    assert validate_binary(binary, UNIT)['distinct_anchor_strings'] == 4
    for extra in (b'hainish progress team', b'(hainish file)', b'hainish>file'):
        with pytest.raises(ValueError):
            validate_binary(binary + extra + b'\0', UNIT)


def test_all_carriers_derive_from_one_unit_and_no_paid_spec():
    old = {'arm': 'old', 'fire': {'model': 'do-not-run'},
           'payload': {'path': 'inputs/candidate.txt', 'sha256': 'a' * 64},
           'build': {'slots': 160, 'slot_size': 3072,
                     'doses': {'RunA': 0, 'RunB': 160},
                     'format_table': True, 'config_tags': True,
                     'fn_literals': {'old': 'wrong graph'},
                     'attention': 'old', 'dos_stub': {}, 'pdb_lines': {}}}
    before = copy.deepcopy(old)
    new, candidate = make_spec(old, 'fresh', UNIT)
    assert old == before
    assert 'fire' not in new
    assert candidate == (UNIT * 40).encode()
    assert new['build']['startup_format'] == UNIT * RUNTIME_COPIES
    assert '\n'.join(row['text'] for row in new['build']['strings']) + '\n' == UNIT
    for disabled in ('fn_literals', 'attention', 'dos_stub', 'pdb_lines'):
        assert disabled not in new['build']
    assert 'hainish' not in str(new['build']['formats'])


def test_saved_delivery_ignores_call_arguments_and_refuses_hash_drift(tmp_path):
    assert saved_delivery(tmp_path, UNIT)['status'].startswith('not_evaluated')
    (tmp_path / 'reports').mkdir()
    path = tmp_path / 'session.json'
    record = tmp_path / 'reports/audit_RunB.json'
    parts = [{'part_kind': 'tool-call', 'args': {'command': UNIT * 10}}]
    for expected in ([], [0]):
        raw = json.dumps({'messages': [{'parts': parts}]}).encode()
        path.write_bytes(raw)
        record.write_text(json.dumps({'session': str(path),
                                     'session_sha256': hashlib.sha256(raw).hexdigest()}))
        assert saved_delivery(tmp_path, UNIT)['complete_single_CONTENT_events'] == expected
        parts.append({'part_kind': 'tool-return', 'content': {'stdout': UNIT * 10}})
    path.write_bytes(b'{}')
    with pytest.raises(ValueError, match='session changed'):
        saved_delivery(tmp_path, UNIT)
