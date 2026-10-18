"""Derive a fresh, LOCAL hainish arm from the preflighted teleology arm.

Usage: python tools/goop_graph_swap.py <v22-local-run> <fresh-local-run>
No paid calls; no old run is modified. Audit provenance preserves both versions.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.graph_delivery import (NAMES, frame_graphs,
                                    graphs_in_content)  # noqa: E402

OLD, NEW = 'teleology', 'hainish'
WHOLE_TOKEN = re.compile(rb'(?<![A-Za-z])teleology(?![A-Za-z])')
SOURCE_ARM = 'conformant-v22-graph-rows-local'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def swapped(value):
    """Change string VALUES in the spec; retain numeric build controls."""
    if isinstance(value, str):
        return value.replace(OLD, NEW)
    if isinstance(value, list):
        return [swapped(item) for item in value]
    if isinstance(value, dict):
        return {key: swapped(item) for key, item in value.items()}
    return value


def prepare(source, destination):
    runs = (ROOT / 'runs').resolve()
    source, destination = source.resolve(), destination.resolve()
    if (source.parent != runs or destination.parent != runs
            or source.name != SOURCE_ARM or destination.exists()):
        raise ValueError('expected the preflighted v22 source and a fresh run')
    spec_bytes = (source / 'spec.json').read_bytes()
    spec = json.loads(spec_bytes)
    preflight_bytes = (source / 'PREFLIGHT.json').read_bytes()
    preflight = json.loads(preflight_bytes)
    prior = json.loads((source / 'inputs/source.json').read_text(encoding='utf-8'))
    candidate = (source / 'inputs/candidate.txt').read_bytes()
    if (spec['arm'] != source.name or 'fire' in spec
            or sha(candidate) != spec['payload']['sha256']
            or sha(candidate) != preflight['candidate_sha256']):
        raise ValueError('source spec, candidate, or preflight mismatch')
    framed = spec['build']['startup_format']
    values = graphs_in_content(framed)
    if (set(values) != set(NAMES) or frame_graphs(values) != framed
            or any(NEW in text for text in values.values())
            or OLD.encode('ascii') not in candidate or NEW.encode('ascii') in candidate):
        raise ValueError('source graphs or candidate are not clean teleology')
    changed = WHOLE_TOKEN.sub(NEW.encode('ascii'), candidate)
    if (candidate.count(OLD.encode('ascii')) !=
            len(WHOLE_TOKEN.findall(candidate)) or OLD.encode('ascii') in changed):
        raise ValueError('some candidate tokens were not swapped')
    new_values = {name: text.replace(OLD, NEW) for name, text in values.items()}
    new_framed = frame_graphs(new_values)
    if graphs_in_content(new_framed) != new_values:
        raise ValueError('hainish graph framing did not round-trip')
    new_spec = swapped(spec)
    new_spec['arm'] = destination.name
    new_spec['payload']['sha256'] = sha(changed)
    new_spec['build']['startup_format'] = new_framed
    if OLD in json.dumps(new_spec) or 'fire' in new_spec:
        raise ValueError('stale teleology token or unexpected fire section')
    provenance = {'source_run': prior['source_run'],
                  'source_spec_sha256': prior['source_spec_sha256'],
                  'source_local_run': source.name,
                  'source_local_spec_sha256': sha(spec_bytes),
                  'source_local_preflight_sha256': sha(preflight_bytes),
                  'source_local_candidate_sha256': sha(candidate),
                  'token_swap': {'from': OLD, 'to': NEW,
                                 'source_graph_sha256': prior['canonical_sha256']},
                  'candidate_sha256': sha(changed),
                  'canonical_sha256': {name: sha(text.encode('ascii'))
                                       for name, text in new_values.items()},
                  'framed_sha256': sha(new_framed.encode('ascii'))}
    destination.mkdir(exist_ok=False)
    (destination / 'inputs').mkdir()
    with (destination / 'inputs/candidate.txt').open('xb') as stream:
        stream.write(changed)
    with (destination / 'spec.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(new_spec, indent=2, ensure_ascii=False) + '\n')
    with (destination / 'inputs/source.json').open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(provenance, indent=2) + '\n')
    with (destination / 'PREREG.md').open('x', encoding='utf-8') as stream:
        stream.write('# Hainish substitution — local only\n\n'
                     'One variable: replace the teleology token with hainish '
                     'in candidate, fn-literals, metadata and startup graphs. '
                     'Do not change old arms. Build, stage and preflight '
                     'locally. No paid fire is authorized by this file.\n')
    print(json.dumps({'arm': destination.name, 'candidate_bytes': len(changed),
                      'swapped_candidate_tokens': len(WHOLE_TOKEN.findall(candidate)),
                      'graph_lengths': {name: len(value)
                                        for name, value in new_values.items()},
                      'rows': len(new_framed.splitlines()),
                      'max_row_chars': max(map(len, new_framed.splitlines()))},
                     indent=2))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: goop_graph_swap.py <v22-local-run> <fresh-local-run>')
    try:
        prepare(Path(sys.argv[1]), Path(sys.argv[2]))
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
