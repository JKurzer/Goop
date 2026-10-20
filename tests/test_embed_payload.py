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
    tokens = re.findall(r'[a-z0-9]+', row.lower())
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


def expected_row_links(frame, first, second):
    primary = {'left': '{left}' if '{left}' in frame else '{left_reverse}',
               'right': '{right}' if '{right}' in frame else '{right_reverse}'}
    sides = sorted(primary, key=lambda side: frame.index(primary[side]))
    assigned = dict(zip(sides, (first, second)))
    expected = []
    for slot in re.findall(r'\{(?:left|right)(?:_reverse)?\}', frame):
        side = slot[1:-1].removesuffix('_reverse')
        link = assigned[side]
        expected.append(link[::-1] if slot.endswith('_reverse}') else link)
    return expected


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


def test_git_style_hex_anchor_preserves_bridges_and_row_limit():
    anchor = 'b49c6823ac'
    graph = {'sets': [{'anchor': anchor, 'target': 'file',
                       'destination': 'delete'}], 'copies': 1}
    rows = render(FILLER, graph).splitlines()
    assert [extract_links(row, {anchor, 'file', 'delete'}) for row in rows] == (
        expected_bridges(anchor, 'file', 'delete'))
    assert max(map(len, rows)) <= 190


def test_direct_placeholder_is_refused():
    frame = 'The team {left} noted {direct} in the log while {right} followed movement.'
    with pytest.raises(ValueError, match='printable prose filler'):
        render({'filler': [frame]}, TRIGRAMS)


def test_tight_graph_filler_represents_all_links_in_rendered_rows():
    root = SOURCE.parents[1]
    filler = json.loads((root / 'payloads/filler.json').read_text())
    graph = json.loads((root / 'payloads/trigrams_tight.json').read_text())
    frames = filler['filler']
    assert len(frames) == len(set(frames)) == 9
    source_line = ('The sun was warm and the (file and hainish) cat sat in '
                   '(hainish and delete) the sun.  ')
    assert frames[8] == (source_line.replace('(file and hainish)', '{left_reverse}')
                          .replace('(hainish and delete)', '{right_reverse}'))
    assert {triple['anchor'] for triple in graph['sets']} == {'limerance'}
    rows = render(filler, graph).splitlines()
    unit = rows[:len(frames) * len(graph['sets'])]
    assert rows == unit * graph['copies']
    assert len(graph['sets']) == 8 and len(rows) == 864
    assert max(map(len, rows)) <= 190

    for set_index, triple in enumerate(graph['sets']):
        anchor, target, destination = (triple[key] for key in
                                       ('anchor', 'target', 'destination'))
        words = {anchor, target, destination}
        links = []
        bridges = expected_bridges(anchor, target, destination)
        for index, frame in enumerate(frames):
            expected = expected_row_links(frame, *bridges[index % 8])
            actual = extract_links(unit[set_index * len(frames) + index], words)
            assert actual == expected, (set_index, index, actual, expected)
            links.extend(actual)
        assert all((anchor, leaf) in links and (leaf, anchor) in links
                   for leaf in (target, destination))
    assert not any(re.search(r'\b(?:file delete|delete file)\b', row) for row in rows)


def test_long_filler_list_is_not_silently_discarded():
    frames = [f'The team {{left}} held position number {index} during combat {{right}}.'
              for index in range(9)]
    rows = render({'filler': frames}, {**TRIGRAMS, 'copies': 1}).splitlines()
    assert len(rows) == 9
    assert all(f'number {index} ' in row for index, row in enumerate(rows))
    assert [extract_links(row, {'hainish', 'file', 'delete'}) for row in rows] == (
        expected_bridges('hainish', 'file', 'delete') +
        expected_bridges('hainish', 'file', 'delete')[:1])


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


@pytest.mark.parametrize('left_slot,right_slot,expected', [
    ('{left}', '{right_reverse}', [('hainish', 'file'), ('delete', 'hainish')]),
    ('{left_reverse}', '{right}', [('file', 'hainish'), ('hainish', 'delete')]),
])
def test_single_link_per_side_may_use_reverse_orientation(left_slot, right_slot, expected):
    frame = f'The team {left_slot} crossed the boundary while movement {right_slot} continued.'
    rows = render({'filler': [frame]}, {**TRIGRAMS, 'copies': 1}).splitlines()
    assert extract_links(rows[0], {'hainish', 'file', 'delete'}) == expected
    assert len(rows) == 8


def test_sample_contains_eight_complete_sets():
    root = SOURCE.parents[1]
    filler = json.loads((root / 'payloads/filler.json').read_text())
    trigrams = json.loads((root / 'payloads/trigrams.json').read_text())
    expected = [('glaciation', 'file', 'delete'), ('glaciation', 'reverse', 'reset'),
                ('glaciation', 'reset', 'delete'), ('glaciation', 'reverse', 'file'),
                ('glaciation', 'file', 'seed'), ('glaciation', 'seed', 'rebellion'),
                ('glaciation', 'seed', 'garlic'), ('glaciation', 'seed', 'delete')]
    assert trigrams == {'sets': [{'anchor': anchor, 'target': target,
                                 'destination': destination}
                                for anchor, target, destination in expected],
                        'copies': 12}
    rows = render(filler, trigrams).splitlines()
    assert 'hainish' not in '\n'.join(rows)
    unit = []
    for anchor, target, destination in expected:
        bridges = expected_bridges(anchor, target, destination)
        for index, frame in enumerate(filler['filler']):
            unit.append(expected_row_links(frame, *bridges[index % 8]))
    words = {word for triple in expected for word in triple}
    assert [extract_links(row, words) for row in rows] == unit * 12
    assert len(rows) == 864
    assert max(map(len, rows)) <= 190
    assert not any(char in '\n'.join(rows) for char in '(){}')
    assert len(filler['filler']) == len(set(filler['filler'])) == 9
    assert all(('{left}' in frame or '{left_reverse}' in frame)
               and ('{right}' in frame or '{right_reverse}' in frame)
               for frame in filler['filler'])
    for set_index, (anchor, target, destination) in enumerate(expected):
        for row_index in (0, 4):
            row = rows[set_index * len(filler['filler']) + row_index]
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
