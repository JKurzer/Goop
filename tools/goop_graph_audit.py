"""Verify byte-exact, same-return delivery of both graphs in a saved run.

Run AFTER goop_score.py export. Requires a SHA-pinned saved analyst session.
Counts complete graph rows in ONE tool-return CONTENT, not call arguments,
reports, or stitched returns. Check the call ID separately to distinguish a
direct runtime execution from a static scan that printed complete rows.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.evidence import content_events  # noqa: E402
from gooplib.graph_delivery import (NAMES, canonical_from_startup,
                                    frame_graphs, graphs_in_content)  # noqa: E402
from gooplib.pair_graph import pair_graph_values  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit_run(run):
    run = run.resolve()
    spec = json.loads((run / 'spec.json').read_text(encoding='utf-8'))
    source_info = json.loads((run / 'inputs/source.json').read_text(encoding='utf-8'))
    local = run.parent / source_info['source_run']
    local_info = json.loads((local / 'inputs/source.json').read_text(encoding='utf-8'))
    local_spec_bytes = (local / 'spec.json').read_bytes()
    if ('source_spec_sha256' in source_info
            and sha(local_spec_bytes) != source_info['source_spec_sha256']):
        raise ValueError('local graph spec differs from paid clone proof')
    derivation = local_info.get('graph_derivation')
    if derivation is not None:
        if (derivation['words'] != {'anchor': 'hainish', 'target': 'delete',
                                    'destination': 'file'}
                or derivation['sets'] != 5):
            raise ValueError('unsupported pair-aligned graph derivation')
        base = run.parent / derivation['source_run']
        base_bytes = (base / 'spec.json').read_bytes()
        if (sha(base_bytes) != derivation['source_spec_sha256']
                or sha((base / 'PREFLIGHT.json').read_bytes()) !=
                derivation['source_preflight_sha256']
                or sha((base / 'inputs/candidate.txt').read_bytes()) !=
                derivation['source_candidate_sha256']
                or sha((local / 'inputs/candidate.txt').read_bytes()) !=
                derivation['source_candidate_sha256']):
            raise ValueError('source pair graph candidate or preflight changed')
        base_startup = json.loads(base_bytes)['build']['startup_format']
        base_frame = frame_graphs(graphs_in_content(base_startup))
        suffix = base_startup[len(base_frame):]
        if (not base_startup.startswith(base_frame)
                or sha(base_startup.encode('ascii')) !=
                derivation['source_framed_sha256']
                or sha(suffix.encode('ascii')) != derivation['filler_sha256']):
            raise ValueError('pair graph base startup or filler changed')
        values = pair_graph_values(derivation['words'], derivation['sets'])
        new_frame = frame_graphs(values)
        if (sha(new_frame.encode('ascii')) != derivation['frame_sha256']
                or json.loads(local_spec_bytes)['build']['startup_format'] !=
                new_frame + suffix):
            raise ValueError('pair graph local frame differs from canonical derivation')
        expected_hashes = derivation['canonical_sha256']
    else:
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
        expected_hashes = local_info['canonical_sha256']
    for name in NAMES:
        if sha(values[name].encode('ascii')) != expected_hashes[name]:
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
