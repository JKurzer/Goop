"""Paid filler evidence is complete tool-return CONTENT, not command echo."""
import hashlib
import json

import pytest

from gooplib.graph_delivery import frame_graphs
from tools.goop_filler_audit import audit
from tools.goop_filler_prepare import runtime_text


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def specimen(tmp_path, delivered):
    local = tmp_path / 'runs/local'
    paid = tmp_path / 'runs/paid'
    lines = [b'One (hainish and file) stood.  \r\n',
             b'The (hainish and delete) cat sat.  \r\n']
    excerpt = b''.join(lines)
    candidate = excerpt * 2
    graph = frame_graphs({'trigram_sets': 'hainish file delete',
                          'full_graph': 'hainish file',
                          'full_graph_directed': 'hainish>file'})
    rendered = runtime_text(lines, 2, 2)
    startup = graph + rendered.decode('ascii')
    spec = {'build': {'startup_format': startup}}
    record(local / 'spec.json', spec)
    record(local / 'inputs/source.json', {
        'candidate_sha256': sha(candidate),
        'framed_sha256': sha(startup.encode('ascii')),
        'filler': {'source_sha256': sha(excerpt), 'excerpt_sha256': sha(excerpt),
                   'excerpt_lines': 2, 'candidate_copies': 2,
                   'runtime_lines': 2, 'runtime_repeats': 2,
                   'runtime_template_sha256': sha(rendered)}})
    (local / 'inputs/filler_excerpt.danger').write_bytes(excerpt)
    (local / 'inputs/candidate.txt').write_bytes(candidate)
    record(paid / 'spec.json', spec)
    record(paid / 'inputs/source.json', {
        'source_run': local.name,
        'source_spec_sha256': sha((local / 'spec.json').read_bytes())})
    record(paid / 'reports/status_RunB.json',
           {'exit': 0, 'usage': {'cost_usd': 1.25}})
    stdout = rendered.replace(b'\n', b'\r\n').decode('ascii')
    session = {'messages': [{'parts': [
        {'part_kind': 'tool-call', 'tool_name': 'shell', 'args': {'command': stdout}},
        {'part_kind': 'tool-return', 'tool_name': 'shell',
         'content': {'stdout': stdout if delivered else graph}}
    ]}]}
    session_file = tmp_path / 'session.json'
    session_file.write_text(json.dumps(session), encoding='utf-8')
    record(paid / 'reports/audit_RunB.json', {
        'session': str(session_file),
        'session_sha256': sha(session_file.read_bytes())})
    (paid / 'analysis').mkdir()
    return paid


@pytest.mark.parametrize('delivered', [True, False])
def test_literal_filler_requires_saved_content(tmp_path, delivered):
    paid = specimen(tmp_path, delivered)
    result = audit(paid)
    expected = [0] if delivered else []
    assert result['exact_crlf_content_event_indices'] == expected
    assert result['newline_normalized_event_indices'] == expected
    assert result['steering_graded'] is False
    with pytest.raises(FileExistsError):
        audit(paid)
