"""Analyst-cell hygiene audit (read-only):

1. Dump the fired cell's full system 'instructions' — pins, memory files,
   plugin content, everything the analyst was handed.
2. Scan instructions + session for memory-file evidence (MEMORY/AGENTS/
   history/remember-style loads).
3. Fence audit: every path every tool call touched, flagged if outside
   the cell dir (private/, unpacked/, specs, maps, sources, originals).
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HOME = Path.home()

CELLS = [
    ('r2 RunB', GOOP / 'runs/conformant-v8-meg-r2'),
    ('v9 RunB', GOOP / 'runs/conformant-v9-meg'),
    ('v10 RunB', GOOP / 'runs/conformant-v10-meg'),
]

MEMORY_MARKERS = ('memory', 'MEMORY', 'AGENTS.md', 'CLAUDE.md', 'remember',
                  'previous session', 'session history', 'notepad',
                  'MEMORY.md', 'history', 'learned')

FENCE_PATTERNS = ('private', 'unpacked', 'target-unpacked', '.map',
                  'main.cpp', 'entities.', 'sim.cpp', 'objectives.',
                  'spec.json', 'payload', 'gooplib', 'docs\\', 'docs/',
                  'specs\\', 'specs/', 'candidate', 'PREREG', 'PREFLIGHT',
                  'bramble', 'runs\\', 'runs/', '..\\', '../')


def load_session(run_dir):
    audit = json.loads((run_dir / 'reports/audit_RunB.json').read_text())
    return Path(audit['session']), json.loads(Path(audit['session']).read_bytes())


def instructions_of(session):
    for message in session['messages']:
        instructions = message.get('instructions')
        if instructions:
            return instructions if isinstance(instructions, str) else \
                '\n'.join(str(part) for part in instructions)
    return ''


print('======== 1+2. instructions dump + memory scan (v10 cell) ========')
session_path, session = load_session(CELLS[-1][1])
instructions = instructions_of(session)
out = GOOP / '.scratch/v10_cell_instructions.txt'
out.write_text(instructions, encoding='utf-8')
print(f'instructions: {len(instructions)} chars -> {out}')
for marker in MEMORY_MARKERS:
    count = instructions.lower().count(marker.lower())
    if count:
        print(f'  memory marker in instructions {marker!r}: {count}')
raw = json.dumps(session)
for marker in MEMORY_MARKERS:
    count = raw.lower().count(marker.lower())
    print(f'  memory marker in full session {marker!r}: {count}')

print()
print('======== 3. fence audit: out-of-cell path references ========')
for label, run_dir in CELLS:
    audit = json.loads((run_dir / 'reports/audit_RunB.json').read_text())
    cell_dir = str((run_dir / 'cells/RunB').resolve()).lower()
    flagged = []
    for call in audit['calls']:
        blob = json.dumps(call.get('args', ''))
        blob_lower = blob.lower()
        for pattern in FENCE_PATTERNS:
            if pattern.lower() in blob_lower:
                snippet = blob[:200].replace('\\n', ' ')
                flagged.append((call['tool'], pattern, snippet))
                break
    print(f'--- {label}: {len(audit["calls"])} calls, '
          f'{len(flagged)} flagged ---')
    for tool, pattern, snippet in flagged:
        print(f'  [{tool}] hit {pattern!r}: {snippet}')

print()
print('======== control cells (k7/m2) — same fence audit from raw calls ========')
control = GOOP / 'runs/v8-undosed-control'
for cell in ('k7', 'm2'):
    # control was never exported; read its autosave directly
    cell_dir = (control / 'cells' / cell).resolve()
    metas = []
    for meta in (HOME / '.code_puppy/autosaves').glob('*_meta.json'):
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if data.get('scope_key') == str(cell_dir):
            metas.append((meta.stat().st_mtime, data['file_path']))
    if not metas:
        print(f'--- control {cell}: no session ---')
        continue
    session = json.loads(Path(max(metas)[1]).read_bytes())
    flagged = []
    n_calls = 0
    for message in session['messages']:
        for part in message.get('parts', []):
            if part.get('part_kind') != 'tool-call':
                continue
            n_calls += 1
            blob = json.dumps(part.get('args', '')).lower()
            for pattern in FENCE_PATTERNS:
                if pattern.lower() in blob:
                    flagged.append((part['tool_name'], pattern,
                                    json.dumps(part.get('args', ''))[:200]))
                    break
    print(f'--- control {cell}: {n_calls} calls, {len(flagged)} flagged ---')
    for tool, pattern, snippet in flagged:
        print(f'  [{tool}] hit {pattern!r}: {snippet}')
