"""Prepare a fresh local graph-row arm from a pinned prior spec (no fire).

Usage: python tools/goop_graph_prepare.py <source-run> <fresh-local-run>
Never starts a model or overwrites an existing run. Paid copies are prepared
separately after this arm passes local build, runtime, and shell checks.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.graph_delivery import (canonical_from_startup, frame_graphs,
                                    graphs_in_content)  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(source, destination):
    runs = (ROOT / 'runs').resolve()
    source, destination = source.resolve(), destination.resolve()
    if (source.parent != runs or destination.parent != runs
            or source == destination or destination.exists()):
        raise ValueError('source and fresh destination must be different runs')
    spec_bytes = (source / 'spec.json').read_bytes()
    old_spec = json.loads(spec_bytes)
    candidate = (source / 'inputs/candidate.txt').read_bytes()
    if sha(candidate) != old_spec['payload']['sha256']:
        raise ValueError('source candidate hash mismatch')
    values = canonical_from_startup(old_spec['build']['startup_format'])
    if len(values['full_graph']) != 907 or len(values['full_graph_directed']) != 911:
        raise ValueError('expected pinned v21 graph lengths')
    framed = frame_graphs(values)
    if graphs_in_content(framed) != values:
        raise ValueError('frame did not round-trip canonical graphs')
    spec = copy.deepcopy(old_spec)
    spec['arm'] = destination.name
    spec['build']['startup_format'] = framed
    spec['build']['startup_zero_probe'] = False
    spec.pop('fire', None)
    provenance = {'source_run': source.name, 'source_spec_sha256': sha(spec_bytes),
                  'candidate_sha256': sha(candidate),
                  'canonical_sha256': {name: sha(text.encode('ascii'))
                                       for name, text in values.items()},
                  'framed_sha256': sha(framed.encode('ascii')),
                  'source_RunB_sha256': sha((source / 'cells/RunB/target.exe').read_bytes())}
    destination.mkdir(exist_ok=False)
    (destination / 'inputs').mkdir()
    with (destination / 'inputs/candidate.txt').open('xb') as stream:
        stream.write(candidate)
    (destination / 'spec.json').write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (destination / 'inputs/source.json').write_text(
        json.dumps(provenance, indent=2) + '\n', encoding='utf-8')
    (destination / 'PREREG.md').write_text(
        '# Local graph-row proof (no model call)\n\n'
        'Native build, pair preflight, and actual shell CONTENT must preserve '
        'all numbered graph rows before any separately authorized paid arm.\n',
        encoding='utf-8')
    print(json.dumps({'local_arm': destination.name, 'source': source.name,
                      'row_count': len(framed.splitlines()),
                      'max_row_chars': max(map(len, framed.splitlines())),
                      'graphs': {name: len(value) for name, value in values.items()}},
                     indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: goop_graph_prepare.py <source-run> <fresh-local-run>')
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
