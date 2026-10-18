"""Verify byte-exact, same-return delivery of both graphs in a saved run.

Run AFTER goop_score.py export. Requires a SHA-pinned saved analyst session.
Never counts local scans, arguments, reports, or text stitched across returns.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.evidence import content_events  # noqa: E402
from gooplib.graph_delivery import (NAMES, canonical_from_startup,
                                    graphs_in_content)  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit_run(run):
    run = run.resolve()
    spec = json.loads((run / 'spec.json').read_text(encoding='utf-8'))
    source_info = json.loads((run / 'inputs/source.json').read_text(encoding='utf-8'))
    local = run.parent / source_info['source_run']
    local_info = json.loads((local / 'inputs/source.json').read_text(encoding='utf-8'))
    original = run.parent / local_info['source_run']
    original_bytes = (original / 'spec.json').read_bytes()
    if sha(original_bytes) != local_info['source_spec_sha256']:
        raise ValueError('original graph contract changed')
    values = canonical_from_startup(json.loads(original_bytes)['build']['startup_format'])
    swap = local_info.get('token_swap')
    if swap is not None:
        if (set(swap) != {'from', 'to', 'source_graph_sha256'}
                or swap['from'] != 'teleology' or swap['to'] != 'hainish'):
            raise ValueError('unsupported graph token substitution')
        for name in NAMES:
            if sha(values[name].encode('ascii')) != swap['source_graph_sha256'][name]:
                raise ValueError(f'{name}: token-swap source hash changed')
        values = {name: text.replace(swap['from'], swap['to'])
                  for name, text in values.items()}
    for name in NAMES:
        if sha(values[name].encode('ascii')) != local_info['canonical_sha256'][name]:
            raise ValueError(f'{name}: canonical hash changed')
    if (sha(spec['build']['startup_format'].encode('ascii')) !=
            local_info['framed_sha256']):
        raise ValueError('paid startup rows differ from local proof')
    status = json.loads((run / 'reports/status_RunB.json').read_text(encoding='utf-8'))
    if status.get('exit') != 0 or status.get('aborted'):
        raise ValueError('paid cell did not complete cleanly')
    record = json.loads((run / 'reports/audit_RunB.json').read_text(encoding='utf-8'))
    saved = Path(record['session']).read_bytes()
    if sha(saved) != record['session_sha256']:
        raise ValueError('saved analyst session differs from export audit')
    events = content_events(json.loads(saved))
    evidence = []
    for index, event in enumerate(events):
        visible = graphs_in_content(event)
        if not visible:
            continue
        evidence.append({'event_index': index, 'event_chars': len(event),
                         'reconstructed': {name: {'bytes': len(text),
                                                  'sha256': sha(text.encode('ascii')),
                                                  'matches_canonical': text == values[name]}
                                           for name, text in visible.items()},
                         'all_three_match': all(visible.get(name) == values[name]
                                                for name in NAMES)})
    literal = [index for index, event in enumerate(events)
               if all(values[name] in event for name in ('full_graph',
                                                         'full_graph_directed'))]
    result = {'arm': run.name, 'cell': 'RunB', 'session_sha256': sha(saved),
              'content_event_count': len(events),
              'expected_lengths': {name: len(values[name]) for name in NAMES},
              'qualifying_event_indices': [row['event_index'] for row in evidence
                                           if row['all_three_match']],
              'framed_delivered': any(row['all_three_match'] for row in evidence),
              'contiguous_literal_event_indices': literal,
              'contiguous_literal_delivered': bool(literal),
              'paid_cost_usd': status['usage']['cost_usd'], 'evidence': evidence}
    path = run / 'analysis/graph_delivery_RunB.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: goop_graph_audit.py <fired-run>')
    try:
        print(json.dumps(audit_run(Path(sys.argv[1])), indent=2))
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
