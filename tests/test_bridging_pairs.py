"""Multi-pair megaline composition: the surviving pins.

The paren audit stack was deleted 2026-10-15. What stays pinned: the
single-pair delegation contract, pair composition order/geometry/
determinism (plan-derived), and compose-time pair validation.
"""
import pytest

from gooplib import bridging as br

PAIR1 = {'anchor': 'teleology', 'target': 'delete', 'destination': 'file'}
PAIR2 = {'anchor': 'teleology', 'target': 'checksum', 'destination': 'delete'}
PAIRS = [PAIR1, PAIR2]
FORMS = ['adjacent']
LEAD_INS = ['The seed grew.', 'A tick of the clock.', 'The owner smiled.',
            'The cat stayed alive.', 'The score was tied.',
            'The summary was short.', 'The seeds fell deep.',
            'A small tick moved.', 'The owner came home.',
            'Still alive, the dog sat.']
CARRIERS = ['The man can see the sea.', 'The cat sat on the mat.',
            'The dog ran and ran and ran.', 'The sun was warm and the dog was warm.',
            'The rain fell and the rain fed the seed.', 'A good dog on a dark day.',
            'The sea sees no sun, and no sun sees the sea.', 'It is what it is.',
            'The tall tree grew green and the green tree grew tall.',
            'The man saw the sea and the sea saw the man.'] * 4
LINKS_PER_LINE = 18 * len(PAIRS)


def compose(doses=1, lines=8, min_bytes=650, max_bytes=780, seed=42):
    return br.compose_megalines_pairs(CARRIERS, LEAD_INS, PAIRS, doses, FORMS,
                                      lines, min_bytes, max_bytes, seed)


def test_single_pair_delegates_identically():
    args = (CARRIERS, LEAD_INS, 1, FORMS, 8, 300, 420, 42)
    solo = br.compose_megalines(args[0], args[1], PAIR1, *args[2:])
    via_pairs = br.compose_megalines_pairs(args[0], args[1], [PAIR1], *args[2:])
    assert solo[0] == via_pairs[0]          # lines byte-identical
    # the plan matches the historical single-pair shape: no 'pair' keys
    assert all('pair' not in insert for row in solo[1]
               for insert in row['inserts'])
    for row_solo, row_via in zip(solo[1], via_pairs[1]):
        assert row_solo.keys() == row_via.keys()
        for insert_solo, insert_via in zip(row_solo['inserts'],
                                           row_via['inserts']):
            assert insert_solo == {key: value for key, value in
                                   insert_via.items() if key != 'pair'}


def test_pair_compose_geometry_order_and_determinism():
    lines, plan = compose()
    lines_b, plan_b = compose()
    assert (lines, plan) == (lines_b, plan_b)
    assert len(lines) == 8
    for row in plan:
        line = lines[row['line']]
        inserts = row['inserts']
        assert len(inserts) == LINKS_PER_LINE
        for pair_index in (0, 1):
            block = inserts[pair_index * 18:(pair_index + 1) * 18]
            for config_index, (first, second) in enumerate(
                    zip(block[::2], block[1::2])):
                config = br.CANONICAL_CONFIGS[config_index]
                assert first['pair'] == pair_index
                assert first['link'] == list(config[0])
                assert second['link'] == list(config[1])
        for insert in inserts:
            assert line[insert['start']:insert['end']] == insert['text']
        assert 650 <= len(line.encode('utf-8')) <= 780


def test_pair_validation_refusals():
    with pytest.raises(ValueError, match='at least one pair'):
        br.compose_megalines_pairs(CARRIERS, LEAD_INS, [], 1, FORMS,
                                   8, 300, 420, 42)
    rogue = dict(PAIR2, anchor='hainish')
    with pytest.raises(ValueError, match='share one anchor'):
        br.compose_megalines_pairs(CARRIERS, LEAD_INS, [PAIR1, rogue],
                                   1, FORMS, 8, 300, 420, 42)
    dup = {'anchor': 'teleology', 'target': 'delete', 'destination': 'delete'}
    with pytest.raises(ValueError, match='distinct'):
        br.compose_megalines_pairs(CARRIERS, LEAD_INS, [PAIR1, dup],
                                   1, FORMS, 8, 300, 420, 42)
