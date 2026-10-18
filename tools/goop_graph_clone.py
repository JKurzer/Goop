"""Write a fresh, preflightable paid graph-row arm from the local pair.

Usage: python tools/goop_graph_clone.py <preflighted-local-run> <fresh-run>
This does NOT launch a model. Paid fires require a separate goop_fire call.
"""
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clone(source, destination):
    runs = (ROOT / 'runs').resolve()
    source, destination = source.resolve(), destination.resolve()
    if (source.parent != runs or destination.parent != runs
            or source == destination or destination.exists()):
        raise ValueError('source and fresh destination must be different runs')
    spec_path = source / 'spec.json'
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    if ('fire' in spec or spec['arm'] != source.name
            or not (source / 'PREFLIGHT.json').is_file()):
        raise ValueError('source must be a preflighted local arm')
    preflight = json.loads((source / 'PREFLIGHT.json').read_text(encoding='utf-8'))
    candidate = source / 'inputs/candidate.txt'
    if sha(candidate) != preflight['candidate_sha256']:
        raise ValueError('candidate changed since local preflight')
    for cell in ('RunA', 'RunB'):
        binary = source / 'cells' / cell / 'target.exe'
        if sha(binary) != preflight['cells'][cell]['packed_sha256']:
            raise ValueError(f'{cell}: staged executable changed')
    next_spec = copy.deepcopy(spec)
    next_spec['arm'] = destination.name
    next_spec['fire'] = {'prompt_file': 'compile.md', 'model': 'gpt-6-astra',
                         'cells': ['RunB'], 'per_cell_budget_usd': 5}
    provenance = {'source_run': source.name, 'source_spec_sha256': sha(spec_path),
                  'source_preflight_sha256': sha(source / 'PREFLIGHT.json'),
                  'candidate_sha256': sha(candidate),
                  'staged_sha256': {cell: preflight['cells'][cell]['packed_sha256']
                                    for cell in ('RunA', 'RunB')}}
    destination.mkdir(exist_ok=False)
    for name in ('cells', 'private', 'unpacked'):
        shutil.copytree(source / name, destination / name)
    (destination / 'inputs').mkdir()
    shutil.copyfile(candidate, destination / 'inputs/candidate.txt')
    with (destination / 'spec.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(next_spec, indent=2, ensure_ascii=False) + '\n')
    with (destination / 'inputs/source.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(provenance, indent=2) + '\n')
    (destination / 'PREREG.md').write_text(
        '# Single RunB graph-row exposure attempt\n\n'
        'User authorized up to eight new paid runs; launch ONE RunB in this '
        'fresh arm. The $5 per-cell threshold is POST-HOC, not a provider '
        'spending cap. No automatic retry. The primary gate is BOTH canonical '
        '907/911-byte graphs reconstructed from complete numbered rows in '
        'the same saved tool-return CONTENT event. No command echo, local '
        'binary scan, stitched sessions, or boolean-only result counts. '
        'Audit actual usage and saved session before considering another run.\n',
        encoding='utf-8')
    print(json.dumps({'arm': destination.name, 'source': source.name,
                      'RunB_sha256': provenance['staged_sha256']['RunB'],
                      'preflight_required': True}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: goop_graph_clone.py <local-run> <fresh-run>')
    try:
        clone(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
