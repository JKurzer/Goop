"""Measure LINKs in individual observed candidate rows, not across a session.

Only saved tool-return CONTENT counts. A matching candidate prefix establishes
origin; incomplete/truncated parentheses are not counted as LINKs. Read-only.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gooplib.evidence import content_events  # noqa: E402

LINK = re.compile(r'\(([a-z]+) ([a-z]+)\)')
WINDOW = 243
PREFIX = 80
ARMS = ['conformant-v13-reverse-compile' + suffix
        for suffix in ('', '-r1', '-r2', '-r3')]


def links_in_rows(events, candidate_lines, pairs):
    """One result per CONTENT row containing a recognizable slot prefix."""
    prefixes = {line[:PREFIX]: line for line in candidate_lines}
    rows = []
    for event_index, event in enumerate(events):
        for row in event.splitlines():
            for prefix, line in prefixes.items():
                start = row.find(prefix)
                if start < 0:
                    continue
                fragment = row[start:start + WINDOW]
                links = LINK.findall(fragment)
                anchored = set(links)
                pair_names = [f"{pair['target']}→{pair['destination']}"
                              for pair in pairs
                              if {(pair['anchor'], pair['target']),
                                  (pair['anchor'], pair['destination'])} <= anchored]
                rows.append({'event': event_index, 'row_chars': len(row),
                             'slot_start': row[:start].strip()[:40],
                             'candidate_prefix': prefix[:35],
                             'link_occurrences': len(links),
                             'distinct_directed_links': len(set(links)),
                             'directed_links': sorted(set('>'.join(link) for link in links)),
                             'pairs_with_both_anchor_links': pair_names,
                             'prefix_complete': len(fragment) == WINDOW,
                             'full_candidate_line': line in row})
    return rows


def audit(run):
    spec = json.loads((run / 'spec.json').read_text(encoding='utf-8'))
    candidate = (run / spec['payload']['path']).read_bytes()
    if hashlib.sha256(candidate).hexdigest() != spec['payload']['sha256']:
        raise ValueError(f'{run}: candidate SHA mismatch')
    lines = candidate.decode('utf-8').splitlines()
    audit_record = json.loads((run / 'reports/audit_RunB.json').read_text(encoding='utf-8'))
    raw = Path(audit_record['session']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != audit_record['session_sha256']:
        raise ValueError(f'{run}: session SHA mismatch')
    events = content_events(json.loads(raw))
    pairs = spec['build']['fn_literals']['pairs']
    rows = links_in_rows(events, lines, pairs)
    names = {entry['name']: entry['text'] for entry in spec['build']['strings']}
    return {
        'arm': run.name, 'content_events': len(events),
        'candidate_lines': len(lines), 'distinct_candidate_lines': len(set(lines)),
        'candidate_prefix_243_link_counts':
            dict(sorted(Counter(len(LINK.findall(line[:WINDOW])) for line in lines).items())),
        'candidate_prefix_243_distinct_link_counts':
            dict(sorted(Counter(len(set(LINK.findall(line[:WINDOW]))) for line in lines).items())),
        'trigram_sets_whole_in_one_content_event':
            sum(names['trigram_sets'] in event for event in events),
        'trigram_phrases_in_content_events': {
            phrase: sum(phrase in event for event in events)
            for phrase in names['trigram_sets'].split(' | ')},
        'candidate_rows_observed': len(rows),
        'candidate_pair_coverage': dict(sorted(Counter(
            name for row in rows for name in row['pairs_with_both_anchor_links']).items())),
        'candidate_rows_with_all_three_pairs':
            sum(len(row['pairs_with_both_anchor_links']) == len(pairs) for row in rows),
        'candidate_rows_with_at_least_four_distinct_links':
            sum(row['distinct_directed_links'] >= 4 for row in rows),
        'rows': rows,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='*', type=Path)
    parser.add_argument('--rows', action='store_true',
                        help='also print individual matched CONTENT rows')
    args = parser.parse_args()
    arms = [path.resolve() for path in args.runs] or [
        ROOT / 'runs' / name for name in ARMS]
    for run in arms:
        result = audit(run)
        if not args.rows:
            result.pop('rows')
        print(json.dumps(result, indent=2))
