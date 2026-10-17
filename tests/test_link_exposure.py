"""Construction checks never masquerade as measured analyst delivery."""
import json
from pathlib import Path

from tools.goop_link_exposure import LINK, WINDOW, links_in_rows

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/conformant-v13-reverse-compile'


def test_single_candidate_row_contains_four_distinct_links_of_one_pair():
    spec = json.loads((RUN / 'spec.json').read_text(encoding='utf-8'))
    pairs = spec['build']['fn_literals']['pairs']
    lines = (RUN / 'inputs/candidate.txt').read_text(encoding='utf-8').splitlines()
    assert len(lines) == 160 and len(set(lines)) == 80
    assert all(len(LINK.findall(line[:WINDOW])) >= 4 for line in lines)
    assert all(len(set(LINK.findall(line[:WINDOW]))) == 4 for line in lines)
    rows = links_in_rows(['\n'.join('0x123 ' + line[:WINDOW]
                                     for line in lines[:3])], lines, pairs)
    assert len(rows) == 3
    assert all(row['meets_minimum_two_links'] for row in rows)
    assert all(row['meets_preferred_four_links'] for row in rows)
    assert all(row['distinct_directed_links'] == 4 for row in rows)
    assert [row['pairs_with_both_anchor_links'] for row in rows] == [
        ['team→reverse'], ['progress→team'], ['reverse→remove']]
    assert not any(len(row['pairs_with_both_anchor_links']) == 3 for row in rows)


def test_missing_fourth_distinct_link_does_not_borrow_from_next_row():
    spec = json.loads((RUN / 'spec.json').read_text(encoding='utf-8'))
    lines = (RUN / 'inputs/candidate.txt').read_text(encoding='utf-8').splitlines()
    pairs = spec['build']['fn_literals']['pairs']
    # Prefix stays recognizable; each row has >=4 inserts, but only 3 forms.
    fragments = [line[:100] for line in lines[:2]]
    rows = links_in_rows(['\n'.join(f'0x123 {part}' for part in fragments)],
                         lines, pairs)
    assert len(rows) == 2
    assert all(row['meets_minimum_two_links'] for row in rows)
    assert all(row['meets_preferred_four_links'] for row in rows)
    assert all(row['distinct_directed_links'] < 4 for row in rows)


def test_two_link_floor_is_per_row_and_four_is_only_preferred():
    spec = json.loads((RUN / 'spec.json').read_text(encoding='utf-8'))
    pairs = spec['build']['fn_literals']['pairs']
    # The 80-byte identifiers stand in for recognizable candidate prefixes.
    first = 'x' * 80 + ' (teleology team) (teleology reverse)'
    second = 'y' * 80 + ' (teleology team) (teleology reverse)'
    alone = links_in_rows(['0x1 ' + first[:-20] + '\n0x2 ' + second[:-20]],
                          [first, second], pairs)
    assert len(alone) == 2
    assert all(not row['meets_minimum_two_links'] for row in alone)
    together = links_in_rows(['0x3 ' + first], [first], pairs)
    assert len(together) == 1
    assert together[0]['meets_minimum_two_links']
    assert not together[0]['meets_preferred_four_links']
    assert together[0]['pairs_with_both_anchor_links'] == ['team→reverse']
