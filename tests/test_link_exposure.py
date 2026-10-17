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
    assert all(row['distinct_directed_links'] == 4 for row in rows)
    assert [row['pairs_with_both_anchor_links'] for row in rows] == [
        ['team→reverse'], ['progress→team'], ['reverse→remove']]
    assert not any(len(row['pairs_with_both_anchor_links']) == 3 for row in rows)


def test_missing_fourth_link_does_not_borrow_from_next_row():
    spec = json.loads((RUN / 'spec.json').read_text(encoding='utf-8'))
    lines = (RUN / 'inputs/candidate.txt').read_text(encoding='utf-8').splitlines()
    pairs = spec['build']['fn_literals']['pairs']
    # Prefix stays recognizable but each physical row lacks a full set.
    fragments = [line[:100] for line in lines[:2]]
    rows = links_in_rows(['\n'.join(f'0x123 {part}' for part in fragments)],
                         lines, pairs)
    assert len(rows) == 2
    assert all(row['distinct_directed_links'] < 4 for row in rows)
