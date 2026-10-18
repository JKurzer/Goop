"""A fresh local arm changes the graph, not the literal filler or candidate."""
import hashlib
import json

import pytest

from gooplib.graph_delivery import frame_graphs, graphs_in_content
from tools import goop_pair_graph_prepare as prep
from tools.goop_filler_prepare import runtime_text

BASE = {'trigram_sets': 'hainish team reverse',
        'full_graph': 'hainish team hainish reverse',
        'full_graph_directed': 'hainish>team hainish>reverse'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def make_source(tmp_path):
    root = tmp_path / 'runs' / 'conformant-v27-hainish-filler-local'
    (root / 'inputs').mkdir(parents=True)
    filler = (b'One (hainish and file).\r\n'
              b'Two (delete and hainish). \r\n'
              b'Three (hainish and delete).\r\n'
              b'Four (file and hainish).\r\n')
    candidate = filler * 2
    suffix = runtime_text(filler.splitlines(keepends=True), 4, 1)
    startup = frame_graphs(BASE) + suffix.decode('ascii')
    spec = {'arm': root.name, 'build': {'startup_format': startup}}
    (root / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
    (root / 'inputs/candidate.txt').write_bytes(candidate)
    (root / 'inputs/filler_excerpt.danger').write_bytes(filler)
    info = {'candidate_sha256': sha(candidate),
            'framed_sha256': sha(startup.encode('ascii')),
            'filler': {'excerpt_sha256': sha(filler), 'candidate_copies': 2,
                       'runtime_lines': 4, 'runtime_repeats': 1}}
    (root / 'inputs/source.json').write_text(json.dumps(info), encoding='utf-8')
    preflight = {'candidate_sha256': sha(candidate), 'cells': {}}
    for name in ('RunA', 'RunB'):
        target = root / 'cells' / name / 'target.exe'
        target.parent.mkdir(parents=True)
        target.write_bytes(name.encode('ascii'))
        preflight['cells'][name] = {'packed_sha256': sha(target.read_bytes())}
    (root / 'PREFLIGHT.json').write_text(json.dumps(preflight), encoding='utf-8')
    return root, filler, candidate


def test_derivative_replaces_only_graph_and_preserves_source_bytes(tmp_path,
                                                                   monkeypatch):
    root, filler, candidate = make_source(tmp_path)
    monkeypatch.setattr(prep, 'ROOT', tmp_path)
    dest = root.parent / 'aligned'
    prep.derive(root, dest)
    assert (dest / 'inputs/candidate.txt').read_bytes() == candidate
    assert (dest / 'inputs/filler_excerpt.danger').read_bytes() == filler
    spec = json.loads((dest / 'spec.json').read_text(encoding='utf-8'))
    graph = graphs_in_content(spec['build']['startup_format'])
    assert graph['trigram_sets'].split(' | ') == ['hainish delete file'] * 5
    assert spec['build']['startup_format'].endswith(runtime_text(
        filler.splitlines(keepends=True), 4, 1).decode('ascii'))
    assert len(spec['build']['startup_format']) < 5000
    with pytest.raises(ValueError, match='fresh local'):
        prep.derive(root, dest)


def test_derivative_rejects_changed_candidate(tmp_path, monkeypatch):
    root, _, _ = make_source(tmp_path)
    monkeypatch.setattr(prep, 'ROOT', tmp_path)
    (root / 'inputs/candidate.txt').write_bytes(b'tampered')
    with pytest.raises(ValueError, match='changed'):
        prep.derive(root, root.parent / 'bad')
    assert not (root.parent / 'bad').exists()
