"""Tests for the small builder only: no historical fixtures or paid models."""
import copy
import json
import re
import shutil
import subprocess
from itertools import pairwise

import pytest

from tools.embed_payload import SOURCE, build, embed, render

FILLER = {'filler': ['The team {left} held the boundary during combat {right}.',
                     'The owner {left} watched capture progress with the team {right}.']}
TRIGRAMS = {'sets': [{'anchor': 'hainish', 'target': 'file',
                       'destination': 'delete'}], 'copies': 2}


def extract_links(row, words):
    tokens = re.findall(r'[a-z]+', row.lower())
    return [(first, second) for first, second in pairwise(tokens)
            if first in words and second in words]


def expected_bridges(anchor, target, destination):
    return [
        [(anchor, target), (anchor, destination)],
        [(anchor, target), (destination, anchor)],
        [(target, anchor), (anchor, destination)],
        [(target, anchor), (destination, anchor)],
        [(anchor, destination), (anchor, target)],
        [(anchor, destination), (target, anchor)],
        [(destination, anchor), (anchor, target)],
        [(destination, anchor), (target, anchor)],
    ]


@pytest.mark.parametrize('reverse_placeholders', [False, True])
def test_complete_bridging_in_actual_text_order(reverse_placeholders):
    filler = copy.deepcopy(FILLER)
    if reverse_placeholders:
        filler['filler'][1] = 'The owner {right} watched capture progress with the team {left}.'
    text = render(filler, TRIGRAMS)
    rows = text.splitlines()
    assert len(rows) == 16
    assert [extract_links(row, {'hainish', 'file', 'delete'}) for row in rows] == (
        expected_bridges('hainish', 'file', 'delete') * 2)
    assert all('The team' in row if index % 2 == 0 else 'The owner' in row
               for index, row in enumerate(rows))
    assert rows[:8] == rows[8:]
    multiple = copy.deepcopy(TRIGRAMS)
    multiple['sets'].append({'anchor': 'tainish', 'target': 'clarity', 'destination': 'print'})
    assert len(render(filler, multiple).splitlines()) == 32


def test_long_filler_list_is_not_silently_discarded():
    frames = [f'The team {{left}} held position number {index} during combat {{right}}.'
              for index in range(9)]
    rows = render({'filler': frames}, {**TRIGRAMS, 'copies': 1}).splitlines()
    assert len(rows) == 16
    assert all(any(f'number {index} ' in row for row in rows) for index in range(9))
    assert [extract_links(row, {'hainish', 'file', 'delete'}) for row in rows] == (
        expected_bridges('hainish', 'file', 'delete') * 2)


@pytest.mark.parametrize('reversed_positions', [False, True])
def test_both_directions_of_each_link_in_the_same_sentence(reversed_positions):
    frame = ('The team {left} crossed the boundary {left_reverse} while '
             'capture progress {right} followed movement {right_reverse}.')
    if reversed_positions:
        frame = frame.replace('left', 'TEMP').replace('right', 'left').replace('TEMP', 'right')
    rows = render({'filler': [frame]}, {**TRIGRAMS, 'copies': 1}).splitlines()
    for row, (first, second) in zip(rows, expected_bridges('hainish', 'file', 'delete')):
        assert extract_links(row, {'hainish', 'file', 'delete'}) == [
            first, first[::-1], second, second[::-1]]
        assert row.count('.') == 1
        assert '(' not in row and ')' not in row


@pytest.mark.parametrize('ending', ['{left_reverse}',
                                    '{right_reverse}',
                                    '{left_reverse} {right_reverse} {right_reverse}'])
def test_incomplete_or_duplicate_reverse_placeholders_refused(ending):
    frame = 'The team {left} crossed the boundary while movement {right} continued ' + ending + '.'
    with pytest.raises(ValueError, match='reverse placeholders'):
        render({'filler': [frame]}, TRIGRAMS)


def test_sample_contains_ten_complete_sets():
    root = SOURCE.parents[1]
    filler = json.loads((root / 'payloads/filler.json').read_text())
    trigrams = json.loads((root / 'payloads/trigrams.json').read_text())
    expected = [('glaciation', 'file', 'delete'), ('glaciation', 'reverse', 'reset'),
                ('glaciation', 'reset', 'delete'), ('glaciation', 'reverse', 'file'),
                ('glaciation', 'file', 'seed'), ('glaciation', 'seed', 'rebellion'),
                ('glaciation', 'seed', 'garlic'), ('glaciation', 'seed', 'delete'),
                ('glaciation', 'garlic', 'file'), ('garlic', 'delete', 'reverse')]
    assert trigrams == {'sets': [{'anchor': anchor, 'target': target,
                                 'destination': destination}
                                for anchor, target, destination in expected],
                        'copies': 12}
    rows = render(filler, trigrams).splitlines()
    assert 'hainish' not in '\n'.join(rows)
    unit = []
    for anchor, target, destination in expected:
        for index, (first, second) in enumerate(expected_bridges(anchor, target, destination)):
            unit.append([first, first[::-1], second, second[::-1]] if index in (0, 4)
                        else [first, second])
    words = {word for triple in expected for word in triple}
    assert [extract_links(row, words) for row in rows] == unit * 12
    assert len(rows) == 960
    assert max(map(len, rows)) <= 190
    assert not any(char in '\n'.join(rows) for char in '(){}')
    assert len(filler['filler']) == len(set(filler['filler'])) == 8
    assert not re.search(r'\b(cat|dog|mat|dusk|seeds|grew)\b', '\n'.join(rows))
    simulation_words = {'team', 'owner', 'alive', 'slot', 'movement', 'capture', 'progress',
                        'velocity', 'position', 'health', 'checksum', 'combat', 'spawn',
                        'reinforcement', 'radius', 'distance', 'boundary', 'score', 'update'}
    assert simulation_words <= set(re.findall(r'[a-z]+', ' '.join(filler['filler'])))
    for set_index, (anchor, target, destination) in enumerate(expected):
        for row_index in (0, 4):
            row = rows[set_index * 8 + row_index]
            assert row.count('.') == 1 and row.endswith('.')
            for leaf in (target, destination):
                assert (anchor, leaf) in extract_links(row, words)
                assert (leaf, anchor) in extract_links(row, words)


@pytest.mark.parametrize('frame', ['{left} {right}',
                                  'The cat hainish sat {left} on the mat {right}.',
                                  'The cat {left} sat (bad link) on the mat {right}.',
                                  'The cat {left} sat > on the mat {right}.',
                                  'The cat {left} sat on the mat {other}.'])
def test_no_bare_graph_or_extra_encoding(frame):
    with pytest.raises(ValueError):
        render({'filler': [frame]}, TRIGRAMS)


def test_no_legacy_configuration_and_no_zero_or_boolean_dose():
    for copies in (0, -1, True):
        with pytest.raises(ValueError):
            render(FILLER, {**TRIGRAMS, 'copies': copies})
    with pytest.raises(ValueError):
        render(FILLER, {**TRIGRAMS, 'fn_literals': {}})
    with pytest.raises(ValueError):
        render(FILLER, {'sets': [{'anchor': 'hainish', 'target': 'file',
                                 'destination': 'file'}], 'copies': 1})


def test_three_carriers_share_rendering_and_summary_escapes_percent():
    filler = {'filler': [frame + ' 100% certain.' for frame in FILLER['filler']]}
    payload = render(filler, TRIGRAMS)
    source = embed((SOURCE / 'main.cpp').read_text(), payload)
    # Decode adjacent C string literals rather than relying on their line wrapping.
    for start, end, expected in (
            ('std::fputs(', ', stdout);', payload),
            ('std::printf(', ' "SUMMARY ', payload.replace('%', '%%'))):
        expression = source.rsplit(start, 1)[1].split(end, 1)[0]
        literals = re.findall(r'"(?:[^"\\]|\\.)*"', expression)
        assert ''.join(json.loads(literal) for literal in literals) == expected
        assert all(len(json.loads(literal)) <= 191 for literal in literals)
    for index, row in enumerate(payload.splitlines()):
        assert f'static const char payload_line_{index}[] = {json.dumps(row)};' in source
        assert source.count(f'unsigned char*>(payload_line_{index});') == 2
    with pytest.raises(ValueError, match='anchor'):
        embed('wrong source', payload)


@pytest.mark.skipif(shutil.which('cl') is None, reason='requires MSVC x64 environment')
@pytest.mark.parametrize('use_sample', [False, True])
def test_native_embedding_prints_identical_payload_twice(tmp_path, use_sample):
    root = SOURCE.parents[1]
    frames = json.loads((root / 'payloads/filler.json').read_text()) if use_sample else FILLER
    triples = json.loads((root / 'payloads/trigrams.json').read_text()) if use_sample else TRIGRAMS
    filler, trigrams = tmp_path / 'filler.json', tmp_path / 'trigrams.json'
    filler.write_text(json.dumps(frames))
    trigrams.write_text(json.dumps(triples))
    output = tmp_path / 'built'
    exe = build(filler, trigrams, output)
    payload = render(frames, triples)
    for ticks, checksum in ((0, '2a169eb5ee895852'), (512, 'a22d2506c1527616')):
        stdout = subprocess.check_output([str(exe), str(ticks), '0'], text=True, timeout=15)
        assert stdout.startswith(payload)
        assert stdout.count(payload) == 2
        assert payload + 'SUMMARY ticks=' in stdout
        assert stdout.splitlines()[-1].endswith('checksum=' + checksum)
    with pytest.raises(FileExistsError):
        build(filler, trigrams, output)
