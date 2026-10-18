"""Saved-session graph gate: returns count; typed commands do not."""
import hashlib
import json

import pytest

from gooplib.graph_delivery import frame_graphs
from gooplib.pair_graph import pair_graph_values
from tools.goop_graph_audit import audit_run

VALUES = {'trigram_sets': 'teleology team reverse | teleology progress team',
          'full_graph': ' '.join(['teleology', 'team', 'reverse'] * 24),
          'full_graph_directed': ' '.join(['teleology>team', 'team>reverse'] * 25)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record), encoding='utf-8')


def specimen(tmp_path, delivered, swap=False):
    runs = tmp_path / 'runs'
    original, local, paid = (runs / name for name in ('original', 'local', 'paid'))
    old = ('STARTUP seed trigram_sets=' + VALUES['trigram_sets'] +
           ' full_graph=' + VALUES['full_graph'] +
           ' full_graph_directed=' + VALUES['full_graph_directed'] + '\n')
    write_json(original / 'spec.json', {'build': {'startup_format': old}})
    actual = {key: text.replace('teleology', 'hainish')
              for key, text in VALUES.items()} if swap else VALUES
    frame = frame_graphs(actual)
    provenance = {
        'source_run': original.name, 'source_spec_sha256': sha((original / 'spec.json').read_bytes()),
        'canonical_sha256': {key: sha(text.encode()) for key, text in actual.items()},
        'framed_sha256': sha(frame.encode())}
    if swap:
        provenance['token_swap'] = {
            'from': 'teleology', 'to': 'hainish',
            'source_graph_sha256': {key: sha(text.encode())
                                    for key, text in VALUES.items()}}
    write_json(local / 'inputs/source.json', provenance)
    write_json(local / 'spec.json', {'build': {'startup_format': frame}})
    write_json(paid / 'spec.json', {'build': {'startup_format': frame}})
    write_json(paid / 'inputs/source.json', {
        'source_run': local.name,
        'source_spec_sha256': sha((local / 'spec.json').read_bytes()),
    })
    write_json(paid / 'reports/status_RunB.json',
               {'exit': 0, 'usage': {'cost_usd': 1.5}})
    session = {'messages': [{'parts': [
        {'part_kind': 'tool-call', 'tool_name': 'shell',
         'tool_call_id': '1', 'args': {'command': frame}},
        {'part_kind': 'tool-return', 'tool_name': 'shell',
         'tool_call_id': '1', 'content': {'stdout': frame if delivered else 'SUMMARY only'}}
    ]}]}
    saved = json.dumps(session).encode()
    session_path = tmp_path / 'session.json'
    session_path.write_bytes(saved)
    write_json(paid / 'reports/audit_RunB.json',
               {'session': str(session_path), 'session_sha256': sha(saved)})
    (paid / 'analysis').mkdir()
    return paid, session_path


@pytest.mark.parametrize('delivered', [True, False])
def test_paid_gate_reads_content_not_call_arguments(tmp_path, delivered):
    run, _ = specimen(tmp_path, delivered)
    result = audit_run(run)
    assert result['framed_delivered'] is delivered
    assert result['contiguous_literal_delivered'] is False
    assert result['qualifying_event_indices'] == ([0] if delivered else [])
    assert (run / 'analysis/graph_delivery_RunB.json').exists()
    with pytest.raises(FileExistsError):
        audit_run(run)


def test_swapped_graphs_require_original_hash_and_full_hainish_rows(tmp_path):
    run, _ = specimen(tmp_path, True, swap=True)
    result = audit_run(run)
    assert result['framed_delivered'] is True
    assert len(result['qualifying_event_indices']) == 1


def test_paid_gate_rejects_changed_saved_session(tmp_path):
    run, session = specimen(tmp_path, True)
    session.write_bytes(session.read_bytes() + b' ')
    with pytest.raises(ValueError, match='differs'):
        audit_run(run)


def derived_specimen(tmp_path):
    runs = tmp_path / 'runs'
    base, local, paid = (runs / name for name in ('base', 'aligned', 'paid'))
    source_frame = frame_graphs(VALUES)
    filler = 'All that is done (hainish and file) is done.\n'
    base_startup = source_frame + filler
    write_json(base / 'spec.json', {'build': {'startup_format': base_startup}})
    write_json(base / 'PREFLIGHT.json', {'ok': True})
    (base / 'inputs').mkdir(parents=True)
    (base / 'inputs/candidate.txt').write_bytes(b'candidate\r\n')
    words = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}
    values = pair_graph_values(words, 5)
    new_frame = frame_graphs(values)
    startup = new_frame + filler
    write_json(local / 'spec.json', {'build': {'startup_format': startup}})
    (local / 'inputs').mkdir()
    (local / 'inputs/candidate.txt').write_bytes(b'candidate\r\n')
    write_json(local / 'inputs/source.json', {
        'framed_sha256': sha(startup.encode()),
        'graph_derivation': {
            'source_run': base.name,
            'source_spec_sha256': sha((base / 'spec.json').read_bytes()),
            'source_preflight_sha256': sha((base / 'PREFLIGHT.json').read_bytes()),
            'source_candidate_sha256': sha(b'candidate\r\n'),
            'source_framed_sha256': sha(base_startup.encode()),
            'words': words, 'sets': 5,
            'canonical_sha256': {name: sha(value.encode())
                                 for name, value in values.items()},
            'frame_sha256': sha(new_frame.encode()),
            'filler_sha256': sha(filler.encode()),
        },
    })
    write_json(paid / 'spec.json', {'build': {'startup_format': startup}})
    write_json(paid / 'inputs/source.json', {
        'source_run': local.name,
        'source_spec_sha256': sha((local / 'spec.json').read_bytes()),
    })
    write_json(paid / 'reports/status_RunB.json',
               {'exit': 0, 'usage': {'cost_usd': 1.25}})
    session = {'messages': [{'parts': [{'part_kind': 'tool-return',
                 'content': {'stdout': startup + 'SUMMARY ticks=0\n'}}]}]}
    saved = json.dumps(session).encode()
    session_path = tmp_path / 'derived-session.json'
    session_path.write_bytes(saved)
    write_json(paid / 'reports/audit_RunB.json',
               {'session': str(session_path), 'session_sha256': sha(saved)})
    (paid / 'analysis').mkdir()
    return base, paid


def test_pair_aligned_graph_gate_recomputes_five_complete_sets(tmp_path):
    _, paid = derived_specimen(tmp_path)
    record = audit_run(paid)
    assert record['framed_delivered']
    assert record['expected_lengths']['full_graph'] == 1244
    assert record['qualifying_event_indices'] == [0]


def test_pair_aligned_gate_rejects_changed_original_spec(tmp_path):
    base, paid = derived_specimen(tmp_path)
    (base / 'spec.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='source pair graph candidate or preflight changed'):
        audit_run(paid)
