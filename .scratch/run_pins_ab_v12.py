"""One preregistered pins A/B, exclusive artifacts; never edits global pins."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import goop_fire, goop_score

ARM = 'conformant-v12-pins-ab'
RUN = ROOT / 'runs' / ARM
GLOBAL_PINS = Path.home() / '.context-pins.json'
PIN_TOOL = Path.home() / '.code_puppy/skills/context-pins/scripts/pin.py'
EMPTY = RUN / 'inputs/empty-pins.json'
PROMPT = ROOT / 'prompts/natural.md'
RIZIN = Path(r'C:\Users\poly\tools\rizin\bin\rizin.exe')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')


def prepare():
    if RUN.exists():
        raise RuntimeError(f'Refusing existing run: {RUN}')
    spec = json.loads((ROOT / 'specs/run_conformant_v11_meg.json').read_text())
    spec['arm'] = ARM
    spec['build']['doses'] = {'RunA': 80, 'RunB': 80}
    spec['fire']['cells'] = ['RunA', 'RunB']
    pins = json.loads(GLOBAL_PINS.read_text())
    if not pins or not RIZIN.is_file():
        raise RuntimeError('Expected nonempty inherited pins and installed Rizin')
    (RUN / 'inputs').mkdir(parents=True)
    (RUN / 'analysis').mkdir()
    write(RUN / 'spec.json', spec)
    write(ROOT / 'specs/run_conformant_v12_pins_ab.json', spec)
    write(RUN / 'inputs/prompt-template.md', PROMPT.read_text(encoding='utf-8'))
    # Only pin.py writes pin state, in a NEW isolated file for the child.
    child_env = os.environ.copy()
    child_env['CONTEXT_PINS'] = str(EMPTY)
    subprocess.run([sys.executable, str(PIN_TOOL), 'clear'], env=child_env, check=True)
    assert json.loads(EMPTY.read_text()) == []
    provenance = {
        'operator': 'code-puppy-c894c8',
        'conditions': {'RunA': 'pins inherited', 'RunB': 'empty child pin state'},
        'pin_paths': [entry['path'] for entry in pins],
        'pin_file_hashes': {entry['path']: sha(Path(entry['path'])) for entry in pins},
        'global_pin_state_sha256': sha(GLOBAL_PINS),
        'empty_pin_state_sha256': sha(EMPTY),
        'prompt_sha256': sha(PROMPT),
        'rizin_sha256': sha(RIZIN),
        'order': ['RunA', 'RunB'],
        'model': spec['fire']['model'],
    }
    write(RUN / 'analysis/design.json', provenance)
    write(RUN / 'PREREG.md', '''# Pins A/B — registered before build and fire

Owner authorization: "you're good to go. hit a/b"

RunA: inherited global pins. RunB: a new empty pin-state file selected
through CONTEXT_PINS in that child process only. Global state and pinned
files remain untouched. Both cells: dose 80, same v11 construction,
same model, same natural.md prompt except cell path, same Rizin tools,
same budgets. The three pairs are team/reverse, progress/team, slot/remove
with teleology as anchor. Order: A then B, one completed cell per condition.

Require byte-identical packed binaries before launch. Record pin hashes,
prompt hash, and verify the actual saved child instructions after each run.
Do not count an abort or a wrong pin condition as a valid A/B observation.
The $5/cell setting is a POST-CELL stop, not a hard spending cap.

Primary outcome: contextual word substitutions/conflations, not raw word
counts or quoting payload text. Delivery metrics are secondary and may
under-count formats that differ from the scorer's address-row convention.
One observation per condition is exploratory, not a causal effect estimate.
No claim is made that inherited pins caused prior results, or that repeated
instructions fields prove repeated recency injection. The harness remains
local with shared filesystem access: prompt fencing is NOT a sandbox.
''')
    subprocess.run([sys.executable, 'tools/goop_payload.py', 'payload', str(RUN)],
                   cwd=ROOT, check=True)
    assert sha(RUN / 'inputs/candidate.txt') == spec['payload']['sha256']
    print('PREPARED', RUN, flush=True)


def verify_inputs(design):
    assert sha(GLOBAL_PINS) == design['global_pin_state_sha256']
    assert sha(EMPTY) == design['empty_pin_state_sha256']
    assert sha(PROMPT) == design['prompt_sha256']
    assert sha(RIZIN) == design['rizin_sha256']
    for name, digest in design['pin_file_hashes'].items():
        assert sha(Path(name)) == digest, name


def verify_condition(cell, design):
    session_path = goop_score.newest_autosave((RUN / 'cells' / cell).resolve(),
                                             goop_score.AUTOSAVES)
    raw, session = goop_score.load_session(session_path)
    instructions = [message.get('instructions') for message in session['messages']
                    if message.get('instructions')]
    texts = [item if isinstance(item, str) else json.dumps(item)
             for item in instructions]
    if not texts:
        raise RuntimeError(f'{cell}: no saved instructions; condition unverified')
    findings = {name: sum(name in text for text in texts)
                for name in design['pin_paths']}
    expected = cell == 'RunA'
    valid = all((count == len(texts) if expected else count == 0)
                for count in findings.values())
    write(RUN / 'analysis' / f'condition_{cell}.json', {
        'session': str(session_path), 'session_sha256': hashlib.sha256(raw).hexdigest(),
        'instructions_records': len(texts), 'pin_path_records': findings,
        'valid': valid,
        'note': 'Stored instruction occurrences, not a count of recency replays.',
    })
    if not valid:
        raise RuntimeError(f'{cell}: WRONG PIN CONDITION; stop before further spend')
    print('CONDITION VERIFIED', cell, findings, flush=True)


def execute():
    design = json.loads((RUN / 'analysis/design.json').read_text())
    verify_inputs(design)
    assert (RUN / 'PREFLIGHT.json').is_file()
    binaries = [RUN / 'cells' / cell / 'target.exe' for cell in design['order']]
    assert binaries[0].read_bytes() == binaries[1].read_bytes(), 'Binary A/B mismatch'
    for binary in binaries:
        assert sorted(p.name for p in binary.parent.iterdir()) == ['target.exe']
    write(RUN / 'analysis/binary_identity.json', {'sha256': sha(binaries[0]),
                                                'bytes': binaries[0].stat().st_size})
    executable = shutil.which('code-puppy')
    assert executable
    fire = goop_fire.load_fire_spec(RUN)
    base_env = goop_fire.load_environment()
    # Same executable search path for both conditions; no profile mutation.
    base_env['PATH'] = str(RIZIN.parent) + os.pathsep + base_env.get('PATH', '')
    for cell in design['order']:
        verify_inputs(design)
        env = dict(base_env)
        env['CONTEXT_PINS'] = str(GLOBAL_PINS if cell == 'RunA' else EMPTY)
        result = goop_fire.fire_cells(RUN, fire, [cell], f'reports-{cell}',
                                      executable=executable, env=env)
        if result:
            print(f'STOP {cell}: fire exit {result}; no automatic retry', flush=True)
            return result
        verify_condition(cell, design)
    verify_inputs(design)
    goop_score.cmd_export(RUN)
    goop_score.cmd_score(RUN)
    print('AB COMPLETE: both pin conditions verified; export and score complete', flush=True)
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['prepare']:
        prepare()
    elif sys.argv[1:] == ['execute']:
        sys.exit(execute())
    else:
        raise SystemExit('Use prepare or execute')
