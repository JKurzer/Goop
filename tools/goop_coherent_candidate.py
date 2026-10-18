"""Prepare/audit a fresh local filler-backed baseline. NEVER calls a model.

python tools/goop_coherent_candidate.py prepare runs/<fresh-name>
python tools/goop_build.py all runs/<fresh-name>
python tools/goop_coherent_candidate.py audit runs/<fresh-name>
"""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.coherent_payload import (LINKS, complete_delivery, from_excerpt,
                                      validate_binary, validate_unit)  # noqa: E402
from gooplib.evidence import content_events  # noqa: E402
from gooplib.specs import (DEFAULT_SUMMARY_TEXT, DEFAULT_TICK_TEXT,
                           build_section)  # noqa: E402

SOURCE = ROOT / 'runs/conformant-v36-hainish-pair-graph-five-staged'
EXCERPT = ROOT / 'runs/conformant-v35-hainish-pair-graph-five-local/inputs/filler_excerpt.danger'
EXCERPT_SHA = '9c70a858900c8673a8edc1c5ba92ddfb48303b1168788fb301a6071440f153d1'
RUNTIME_COPIES = 10
PROBES = ((0, 0), (0, 1), (511, 0), (512, 0), (513, 0), (4096, 0), (4096, 7))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def make_spec(source_spec, arm, unit):
    validate_unit(unit)
    spec = copy.deepcopy(source_spec)
    spec['arm'] = arm
    spec.pop('fire', None)  # paid launch requires a separate approved clone
    build = spec['build']
    copies, remainder = divmod(build['slots'], len(unit.splitlines()))
    if remainder:
        raise ValueError('slot count must contain whole filler units')
    candidate = (unit * copies).encode('ascii')
    spec['payload'] = {'path': 'inputs/candidate.txt', 'sha256': sha(candidate),
                       'terms': list(LINKS)}
    for key in ('fn_literals', 'attention', 'dos_stub', 'pdb_lines'):
        build.pop(key, None)
    build['strings'] = [{'name': f'passage_{i:02d}', 'text': row}
                        for i, row in enumerate(unit.splitlines())]
    build['startup_format'] = unit * RUNTIME_COPIES
    build['startup_zero_probe'] = False
    build['formats'] = {'tick': DEFAULT_TICK_TEXT, 'summary': DEFAULT_SUMMARY_TEXT}
    build_section(spec)  # enforce existing printf and bounded-output contracts
    return spec, candidate


def prepare(destination):
    if destination.parent != (ROOT / 'runs').resolve() or destination.exists():
        raise ValueError('requires a fresh direct child of runs/')
    source_bytes = (SOURCE / 'spec.json').read_bytes()
    source_spec = json.loads(source_bytes)
    original = (SOURCE / source_spec['payload']['path']).read_bytes()
    if sha(original) != source_spec['payload']['sha256']:
        raise ValueError('source candidate pin changed')
    excerpt = EXCERPT.read_bytes()
    if sha(excerpt) != EXCERPT_SHA:
        raise ValueError('source excerpt pin changed')
    unit = from_excerpt(excerpt)
    spec, candidate = make_spec(source_spec, destination.name, unit)
    destination.mkdir(exist_ok=False)
    (destination / 'inputs').mkdir()
    for name, raw in (('payload-unit.txt', unit.encode('ascii')),
                      ('candidate.txt', candidate)):
        with (destination / 'inputs' / name).open('xb') as stream:
            stream.write(raw)
    write_json(destination / 'spec.json', spec)
    record = {
        'source_run': SOURCE.name, 'source_spec_sha256': sha(source_bytes),
        'source_excerpt_sha256': EXCERPT_SHA,
        'source_edit': 'first four rows; remove and only inside parenthetical links; LF framing',
        'unit_sha256': sha(unit.encode('ascii')), 'candidate_sha256': sha(candidate),
        'spec_sha256': sha((destination / 'spec.json').read_bytes()),
        'links_per_unit': validate_unit(unit),
        'candidate_unit_copies': len(candidate) // len(unit.encode('ascii')),
        'runtime_unit_copies': RUNTIME_COPIES,
        'runtime_bytes_lf': len(spec['build']['startup_format']),
        'active_carriers': ['slot rows', 'function-referenced cargo rows', 'stdout rows'],
        'disabled_carriers': ['old function-link generator', 'DOS/PDB payload', 'attention'],
        'neutral_formats': True, 'paid_authorization': False,
        'causal_comparison_with_v36': False,
        'note': 'new coherent construction baseline, not a single-variable v36 ablation; '
                'RunA also has cargo/stdout and is NOT an undosed exposure control',
    }
    write_json(destination / 'CONSTRUCTION.json', record)
    with (destination / 'PREREG.md').open('x', encoding='utf-8') as stream:
        stream.write('# Coherent filler baseline — LOCAL ONLY\n\n'
                     'Every active carrier derives from inputs/payload-unit.txt. '
                     'Links are only (hainish file), (file hainish), '
                     '(hainish delete), (delete hainish), inside source filler. '
                     'No labels, arrows, conjunctions inside links, or second graph.\n\n'
                     'Candidate: 40 complete four-line units (160 slots). '
                     'Runtime: 10 units (40 rows). Function-referenced cargo: '
                     'one complete unit. Plain simulation formats carry no plant. '
                     'Old function-link generator, attention, DOS/PDB plant disabled.\n\n'
                     'Build/preflight plus exact binary-string and stdout audits '
                     'establish local insertion/output, NOT analyst consumption '
                     'or steering. Saved single-return CONTENT must contain the '
                     'full literal runtime dose before counting exposure. Leaf '
                     'incidence includes negations; absent anchor is expected.\n\n'
                     'This repairs multiple carriers: NOT a one-variable v36 '
                     'comparison. RunA shares stdout/cargo and is not an undosed '
                     'control. No model calls authorized; spec has no fire section.\n')
    print(json.dumps(record, indent=2))


def checked_spec(run):
    construction = json.loads((run / 'CONSTRUCTION.json').read_text())
    spec_raw = (run / 'spec.json').read_bytes()
    if sha(spec_raw) != construction['spec_sha256']:
        raise ValueError('spec changed after construction')
    spec = json.loads(spec_raw)
    unit_raw = (run / 'inputs/payload-unit.txt').read_bytes()
    if sha(unit_raw) != construction['unit_sha256']:
        raise ValueError('unit changed after construction')
    unit = unit_raw.decode('ascii')
    source_raw = (SOURCE / 'spec.json').read_bytes()
    if sha(source_raw) != construction['source_spec_sha256']:
        raise ValueError('source spec changed since construction')
    expected_spec, candidate = make_spec(json.loads(source_raw), run.name, unit)
    if spec != expected_spec or (run / 'inputs/candidate.txt').read_bytes() != candidate:
        raise ValueError('carrier drift from the single unit')
    return spec, unit, construction


def summary(stdout):
    return stdout.splitlines()[-1].split(b'ticks=', 1)[1]


def saved_delivery(run, unit):
    path = run / 'reports/audit_RunB.json'
    if not path.is_file():
        return {'status': 'not_evaluated_no_saved_analyst_session'}
    audit = json.loads(path.read_text())
    saved = Path(audit['session']).read_bytes()
    if sha(saved) != audit['session_sha256']:
        raise ValueError('saved analyst session changed')
    events = content_events(json.loads(saved))
    return {'status': 'audited', 'session_sha256': sha(saved),
            'complete_single_CONTENT_events': [i for i, event in enumerate(events)
                                              if complete_delivery(event, unit, RUNTIME_COPIES)],
            'steering': 'separate leaf-report endpoint, not inferred from delivery'}


def audit_local(run):
    spec, unit, construction = checked_spec(run)
    preflight = json.loads((run / 'PREFLIGHT.json').read_text())
    if preflight['candidate_sha256'] != spec['payload']['sha256']:
        raise ValueError('preflight candidate pin mismatch')
    cells = {}
    for cell in ('RunA', 'RunB'):
        exe = run / 'cells' / cell / 'target.exe'
        raw = exe.read_bytes()
        if sha(raw) != preflight['cells'][cell]['packed_sha256']:
            raise ValueError('staged binary pin mismatch')
        cells[cell] = {'sha256': sha(raw), **validate_binary(raw, unit)}
    exe = run / 'cells/RunB/target.exe'
    baseline = SOURCE / 'cells/RunB/target.exe'
    observations = []
    for ticks, seed in PROBES:
        current = subprocess.check_output([str(exe), str(ticks), str(seed)], timeout=15)
        previous = subprocess.check_output([str(baseline), str(ticks), str(seed)], timeout=15)
        expected = (unit * RUNTIME_COPIES).encode('ascii').replace(b'\n', b'\r\n')
        if not current.startswith(expected) or summary(current) != summary(previous):
            raise ValueError(f'output or simulation mismatch at {ticks}/{seed}')
        observations.append({'ticks': ticks, 'seed': seed,
                             'stdout_sha256': sha(current),
                             'summary_fields': summary(current).decode('ascii'),
                             'literal_runtime_prefix_matches': True})
    result = {'arm': run.name, 'construction': construction, 'cells': cells,
              'probes': observations, 'analyst_delivery': saved_delivery(run, unit),
              'steering': 'not_evaluated; local native probes are not analyst trials'}
    output = run / 'analysis'
    output.mkdir(exist_ok=True)
    write_json(output / 'coherent_local_audit.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'audit'))
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    try:
        (prepare if args.action == 'prepare' else audit_local)(args.run.resolve())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
