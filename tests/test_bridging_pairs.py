"""Multi-pair megaline machinery (2026-10-15 doctrine: teleology anchor,
two pairs — delete/file and checksum/delete chained on the shared leaf —
two copies per line).

Pure-function pins: pair composition order/geometry, the measurement
trio, the audit, and the single-pair delegation contract (byte-identical
output for one pair, so the v1/v2/v3 pins can never regress).
"""
import pytest

from gooplib import bridging as br

PAIR1 = {'anchor': 'teleology', 'target': 'delete', 'destination': 'file'}
PAIR2 = {'anchor': 'teleology', 'target': 'checksum', 'destination': 'delete'}
PAIRS = [PAIR1, PAIR2]
FORMS = ['adjacent']
FILTER_TERMS = ['tick', 'seed', 'score', 'alive', 'owner', 'summary']

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
    assert solo[1] == via_pairs[1]          # plan identical too ('pair': 0)


def test_pair_compose_geometry_order_and_determinism():
    lines, plan = compose()
    lines_b, plan_b = compose()
    assert (lines, plan) == (lines_b, plan_b)
    assert len(lines) == 8
    for row in plan:
        line = lines[row['line']]
        inserts = row['inserts']
        assert len(inserts) == LINKS_PER_LINE
        # pair 0's canonical 18, then pair 1's canonical 18, per dose
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


def test_pair_measure_coverage_and_truncation():
    lines, _ = compose()
    mega = br.measure_megalines_pairs(lines, PAIRS, FILTER_TERMS, 512, 240)
    expected = [{br.config_label(br.pair_configs(PAIR1)[i]): 1 for i in range(9)},
                {br.config_label(br.pair_configs(PAIR2)[i]): 1 for i in range(9)}]
    for row in mega['per_line']:
        assert [pair['per_config'] for pair in row['per_pair']] == expected
        assert row['pair_total'] == 18
        assert row['link_total'] == LINKS_PER_LINE
        assert row['filter_term'] is not None
        assert row['first_four_links_in_truncation'] is True
        assert row['fourth_link_end'] <= 240
    assert mega['lines_with_filter_echo'] == 8
    assert mega['lines_with_complete_pair_in_window'] == 8
    assert mega['lines_with_first_four_in_truncation'] == 8


def test_expected_forms_pairs():
    forms = br.expected_directed_forms_pairs(PAIRS, 1)
    assert forms == {'teleology>delete': 8, 'delete>teleology': 9,
                     'teleology>file': 4, 'file>teleology': 5,
                     'file>delete': 1, 'teleology>checksum': 4,
                     'checksum>teleology': 4, 'delete>checksum': 1}
    doubled = br.expected_directed_forms_pairs(PAIRS, 2)
    assert all(count == forms[form] * 2 for form, count in doubled.items())


def test_pair_audit_clean_on_composed_text():
    lines, _ = compose()
    audit = br.role_audit_pairs(lines, PAIRS)
    assert audit['ok'], audit['violations']
    assert audit['anchor_occurrences'] == audit['anchor_at_bridge']


@pytest.mark.parametrize('line, match', [
    ('The seed grew. (file checksum) (teleology file)', 'undeclared anchorless'),
    ('The seed grew. (teleology teleology) (teleology file)',
     'anchor paired with itself'),
    ('The teleology seed grew. (teleology file)', 'outside inserts'),
    ('The seed grew. (teleology and file extra) (file delete)',
     'unparseable group'),
])
def test_pair_audit_violations(line, match):
    audit = br.role_audit_pairs([line], PAIRS)
    assert not audit['ok']
    assert match in audit['violations'][0]['error']


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
