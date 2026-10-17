"""Compose a fresh run from a pinned historical graph via inputs/compose.json.

Only candidate text and specified graph leaves change; the old run is read-only.
Usage: python tools/goop_retarget.py runs/<new-arm>
"""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib import GoopError  # noqa: E402
from gooplib.exports import validate_pairs  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compose(run):
    recipe = json.loads((run / 'inputs/compose.json').read_text(encoding='utf-8'))
    if run.name != recipe['arm'] or recipe['old_leaf'] == recipe['new_leaf']:
        raise GoopError('arm or leaf mismatch in compose.json')
    source = (ROOT / recipe['source_run']).resolve()
    if not source.is_relative_to(ROOT / 'runs') or source == run:
        raise GoopError('source must be a different run under runs/')
    source_spec_bytes = (source / 'spec.json').read_bytes()
    source_candidate = (source / 'inputs/candidate.txt').read_bytes()
    if (digest(source_spec_bytes) != recipe['source_spec_sha256']
            or digest(source_candidate) != recipe['source_candidate_sha256']):
        raise GoopError('pinned source spec or candidate changed')
    old = recipe['old_leaf']
    new = recipe['new_leaf']
    if not all(word.isascii() and word.isalpha() and word.islower()
               for word in (old, new)):
        raise GoopError('leaves must be lowercase ASCII words')
    pattern = re.compile(r'\b' + re.escape(old) + r'\b')
    candidate, count = re.subn(rb'\b' + old.encode() + rb'\b',
                               new.encode(), source_candidate)
    if count != recipe['candidate_replacements']:
        raise GoopError(f'candidate replacements: expected '
                        f'{recipe["candidate_replacements"]}, found {count}')
    spec = copy.deepcopy(json.loads(source_spec_bytes))
    spec['arm'] = run.name
    pair = spec['build']['fn_literals']['pairs'][2]
    if pair != {'anchor': 'teleology', 'target': old, 'destination': 'remove'}:
        raise GoopError('third pair is not the pinned slot-to-remove bridge')
    pair['target'] = new
    validate_pairs(spec['build']['fn_literals']['pairs'])
    changed = set()
    for entry in spec['build']['strings']:
        if entry['name'] not in recipe['graph_strings']:
            if pattern.search(entry['text']):
                raise GoopError(f'unlisted graph string contains leaf: {entry["name"]}')
            continue
        updated, hits = pattern.subn(new, entry['text'])
        if not hits:
            raise GoopError(f'graph string missing leaf: {entry["name"]}')
        entry['text'] = updated
        changed.add(entry['name'])
    if changed != set(recipe['graph_strings']):
        raise GoopError('graph_strings do not match source spec')
    terms = spec['payload']['terms']
    if terms.count(f'teleology {old}') != 1:
        raise GoopError('expected exactly one tracked old-leaf term')
    spec['payload']['terms'] = [f'teleology {new}' if term == f'teleology {old}'
                                 else term for term in terms]
    spec['payload']['sha256'] = digest(candidate)
    spec['fire']['prompt_file'] = recipe['prompt_file']
    spec['fire']['cells'] = recipe['fire_cells']
    if recipe['prompt_file'] != 'compile.md' or recipe['fire_cells'] != ['RunB']:
        raise GoopError('unexpected paid-fire protocol; refuse')
    new_spec = (json.dumps(spec, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    manifest = {'recipe': 'inputs/compose.json', 'source_run': recipe['source_run'],
                'source_spec_sha256': digest(source_spec_bytes),
                'source_candidate_sha256': digest(source_candidate),
                'candidate_replacements': count, 'candidate_sha256': digest(candidate),
                'spec_sha256': digest(new_spec)}
    outputs = ((run / 'inputs/candidate.txt', candidate),
               (run / 'spec.json', new_spec),
               (run / 'inputs/compose.manifest.json',
                (json.dumps(manifest, indent=2) + '\n').encode('utf-8')))
    if any(path.exists() for path, _ in outputs):
        raise GoopError('composition outputs already exist; refuse overwrite')
    for path, content in outputs:
        with path.open('xb') as stream:
            stream.write(content)
    return manifest


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: goop_retarget.py runs/<new-arm>')
    try:
        result = compose(Path(sys.argv[1]).resolve())
    except (GoopError, OSError, KeyError, ValueError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
