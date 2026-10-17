"""Create write-once, byte-identical RunB arms from a visible JSON plan.

Usage: python tools/goop_replicate.py runs/<source-arm>/replication-plan.json
Does not launch a model or execute either binary.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def replicate(plan_path):
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    source = (RUNS / plan['source_arm']).resolve()
    require(plan_path.resolve() == source / 'replication-plan.json',
            'plan must live in its own source run')
    names = plan['replicas']
    require(len(names) == 3 and len(set(names)) == 3 and
            all(name.startswith(source.name + '-r') and
                (RUNS / name).resolve().parent == RUNS for name in names),
            'expected exactly three distinct new replica arms')
    require(all(not (RUNS / name).exists() for name in names),
            'one or more replica arms already exist; refuse overwrite')
    spec_bytes = (source / 'spec.json').read_bytes()
    spec = json.loads(spec_bytes)
    preflight = json.loads((source / 'PREFLIGHT.json').read_text(encoding='utf-8'))
    require(spec['arm'] == source.name, 'source arm mismatch')
    require(spec['fire']['prompt_file'] == plan['prompt_file'] == 'compile.md'
            and spec['fire']['model'] == plan['model'] == 'gpt-6-astra'
            and spec['fire']['cells'] == plan['fire_cells'] == ['RunB']
            and plan['attempts_per_replica'] == 1,
            'unexpected fire contract')
    require(preflight['candidate_sha256'] == plan['source_candidate_sha256']
            and preflight['cells']['RunB']['packed_sha256'] ==
            plan['source_RunB_packed_sha256'], 'source preflight mismatch')
    require((source / 'reports/status_RunB.json').is_file(),
            'source RunB did not finish')
    relative_files = ['inputs/candidate.txt', 'private/manifest.json',
                      'unpacked/private/manifest.json']
    for cell in spec['build']['doses']:
        relative_files.extend((f'cells/{cell}/target.exe',
                               f'unpacked/cells/{cell}/target.exe'))
    assets = {name: (source / name).read_bytes() for name in relative_files}
    require(sha(assets['inputs/candidate.txt']) == plan['source_candidate_sha256']
            and sha(assets['cells/RunB/target.exe']) ==
            plan['source_RunB_packed_sha256'], 'source asset hash mismatch')
    for cell in spec['build']['doses']:
        require(sha(assets[f'cells/{cell}/target.exe']) ==
                preflight['cells'][cell]['packed_sha256'] and
                sha(assets[f'unpacked/cells/{cell}/target.exe']) ==
                preflight['cells'][cell]['unpacked_sha256'],
                f'{cell}: source binary changed')
    for ordinal, name in enumerate(names, 1):
        replica = RUNS / name
        replica.mkdir(exist_ok=False)
        next_spec = {**spec, 'arm': name}
        rendered = (json.dumps(next_spec, indent=2, ensure_ascii=False) + '\n').encode()
        provenance = {'source_arm': source.name, 'source_spec_sha256': sha(spec_bytes),
                      'replica_spec_sha256': sha(rendered),
                      'source_preflight_sha256': sha((source / 'PREFLIGHT.json').read_bytes()),
                      'assets_sha256': {key: sha(value) for key, value in assets.items()},
                      'ordinal': ordinal, 'replica_count': len(names),
                      'plan': f'{source.name}/replication-plan.json'}
        prereg = (f'# Preregistration: {name}\n\n'
                  f'Replica {ordinal} of {len(names)} of the pinned source arm '
                  f'`{source.name}`. Binary and candidate bytes are identical; '
                  'only the JSON arm name and fresh autosave scope differ. '
                  'Verify the local pair before fire. Fire RunB once with '
                  '`compile.md` and `gpt-6-astra`; no retries, no paid RunA. '
                  'The $5 per-cell threshold is POST-HOC and cannot cap '
                  'provider spending. Compile-only grade means no replacement '
                  'execution and no behavioral claim. Audit returned tool text '
                  'for real delivery separately from string presence.\n')
        outputs = {**assets, 'spec.json': rendered,
                   'PREREG.md': prereg.encode('utf-8'),
                   'inputs/source.json': (json.dumps(provenance, indent=2) + '\n').encode()}
        for relative, content in outputs.items():
            path = replica / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(content)
        print(f'prepared {name}: RunB {plan["source_RunB_packed_sha256"]}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: goop_replicate.py <replication-plan.json>')
    try:
        replicate(Path(sys.argv[1]))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
