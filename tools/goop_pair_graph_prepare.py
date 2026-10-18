"""Derive a fresh LOCAL pair-aligned graph arm from the preflighted low filler.

Candidate bytes, source excerpt, low runtime filler, function literals, and
simulation stay fixed. Only the graph-first startup rows change. Never fires.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.graph_delivery import frame_graphs, graphs_in_content  # noqa: E402
from gooplib.pair_graph import pair_graph_values  # noqa: E402
from gooplib.specs import STARTUP_FORMAT_MAX  # noqa: E402
from tools.goop_filler_prepare import runtime_text  # noqa: E402

WORDS = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}
SETS = 5


def sha(data):
    return hashlib.sha256(data).hexdigest()


def derive(source, destination):
    runs = (ROOT / 'runs').resolve()
    source, destination = source.resolve(), destination.resolve()
    if (source.parent != runs or destination.parent != runs
            or source.name != 'conformant-v27-hainish-filler-local'
            or destination.exists()):
        raise ValueError('requires v27 low local source and fresh local destination')
    spec_bytes = (source / 'spec.json').read_bytes()
    spec = json.loads(spec_bytes)
    info = json.loads((source / 'inputs/source.json').read_text(encoding='utf-8'))
    preflight_bytes = (source / 'PREFLIGHT.json').read_bytes()
    preflight = json.loads(preflight_bytes)
    candidate = (source / 'inputs/candidate.txt').read_bytes()
    excerpt = (source / 'inputs/filler_excerpt.danger').read_bytes()
    if (spec['arm'] != source.name or 'fire' in spec
            or sha(candidate) != info['candidate_sha256']
            or sha(candidate) != preflight['candidate_sha256']
            or sha(excerpt) != info['filler']['excerpt_sha256']
            or candidate != excerpt * info['filler']['candidate_copies']):
        raise ValueError('local source, excerpt, or preflight changed')
    for cell in ('RunA', 'RunB'):
        if sha((source / 'cells' / cell / 'target.exe').read_bytes()) != \
                preflight['cells'][cell]['packed_sha256']:
            raise ValueError(f'{cell}: staged executable changed')
    original = spec['build']['startup_format']
    old_frame = frame_graphs(graphs_in_content(original))
    filler = info['filler']
    expected_filler = runtime_text(excerpt.splitlines(keepends=True),
                                   filler['runtime_lines'], filler['runtime_repeats'])
    if (not original.startswith(old_frame)
            or original != old_frame + expected_filler.decode('ascii')
            or sha(original.encode('ascii')) != info['framed_sha256']):
        raise ValueError('source graph-first filler framing changed')
    values = pair_graph_values(WORDS, SETS)
    new_frame = frame_graphs(values)
    startup = new_frame + expected_filler.decode('ascii')
    if len(startup) > STARTUP_FORMAT_MAX:
        raise ValueError('new graph and filler exceed bounded startup')
    assert graphs_in_content(startup) == values
    new_spec = copy.deepcopy(spec)
    new_spec['arm'] = destination.name
    new_spec['build']['startup_format'] = startup
    new_info = copy.deepcopy(info)
    new_info['framed_sha256'] = sha(startup.encode('ascii'))
    new_info['graph_derivation'] = {
        'source_run': source.name,
        'source_spec_sha256': sha(spec_bytes),
        'source_preflight_sha256': sha(preflight_bytes),
        'source_candidate_sha256': sha(candidate),
        'source_framed_sha256': sha(original.encode('ascii')),
        'words': WORDS, 'sets': SETS,
        'canonical_sha256': {name: sha(value.encode('ascii'))
                             for name, value in values.items()},
        'frame_sha256': sha(new_frame.encode('ascii')),
        'filler_sha256': sha(expected_filler),
    }
    destination.mkdir(exist_ok=False)
    (destination / 'inputs').mkdir()
    for name, data in (('candidate.txt', candidate),
                       ('filler_excerpt.danger', excerpt)):
        with (destination / 'inputs' / name).open('xb') as stream:
            stream.write(data)
    for name, record in (('spec.json', new_spec),
                         ('inputs/source.json', new_info)):
        with (destination / name).open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
    with (destination / 'PREREG.md').open('x', encoding='utf-8') as stream:
        stream.write('# Pair-aligned five-set graph: LOCAL ONLY\n\n'
                     'Five complete ordered nine-config canonical sets: '
                     'hainish anchor, delete target, file destination. '
                     'No changed candidate, source filler, native behavior, '
                     'or runtime four-line dose versus v27/v33. Graph rows '
                     'first; each <=190 chars. Build and preflight locally '
                     'before any separately approved paid cell. The old '
                     'team/progress/reverse graph is not a matched control '
                     'for a different runtime dose.\n')
    print(json.dumps({'arm': destination.name, 'source': source.name,
                      'sets': SETS, 'canonical_link_pairs': SETS * 9,
                      'graph_lengths': {name: len(value) for name, value in values.items()},
                      'graph_rows': len(new_frame.splitlines()),
                      'startup_chars': len(startup),
                      'candidate_sha256': sha(candidate)}, indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: goop_pair_graph_prepare.py <v27-local> <fresh-local>')
    try:
        derive(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
