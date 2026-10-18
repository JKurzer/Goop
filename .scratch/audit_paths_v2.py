"""Fence audit v2 (the regex-fixed, full-inventory version).

Every string field of every tool-call arg and every tool-return is
de-escaped, then scanned for absolute Windows paths (>=2 segments).
Each path is resolved and bucketed inside-cell vs outside-cell.
Read-only.
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
HOME = Path.home()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ABS = re.compile(r'[A-Za-z]:\\[^\s"\'\r\n]*')
TRAVERSAL = re.compile(r'(?:^|[\\/])\.\.(?:[\\/]|$)')

CELLS = [
    ('r2 RunB', GOOP / 'runs/conformant-v8-meg-r2', 'RunB'),
    ('v9 RunB', GOOP / 'runs/conformant-v9-meg', 'RunB'),
    ('v10 RunB', GOOP / 'runs/conformant-v10-meg', 'RunB'),
    ('control k7', GOOP / 'runs/v8-undosed-control', 'k7'),
    ('control m2', GOOP / 'runs/v8-undosed-control', 'm2'),
]


def session_for(run_dir, cell):
    audit_path = run_dir / 'reports/audit_RunB.json'
    if audit_path.is_file() and cell == 'RunB':
        return Path(json.loads(audit_path.read_text())['session'])
    cell_dir = (run_dir / 'cells' / cell).resolve()
    metas = []
    for meta in (HOME / '.code_puppy/autosaves').glob('*_meta.json'):
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if data.get('scope_key') == str(cell_dir):
            metas.append((meta.stat().st_mtime, data['file_path']))
    return Path(max(metas)[1]) if metas else None


def strings_of(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings_of(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings_of(item)


def paths_in(text):
    text = text.replace('\\\\', '\\')
    for match in ABS.findall(text):
        candidate = match.rstrip('\\').rstrip('.,;)"]\'')
        if '\\' in candidate[2:] and len(candidate) > 5:
            yield candidate


for label, run_dir, cell in CELLS:
    session_path = session_for(run_dir, cell)
    if not session_path:
        print(f'=== {label}: no session ===')
        continue
    cell_dir = str((run_dir / 'cells' / cell).resolve()).lower()
    session = json.loads(session_path.read_bytes())
    inside, outside, traversals, cds = set(), set(), [], []
    for message in session['messages']:
        for part in message.get('parts', []):
            kind = part.get('part_kind')
            payload = (part.get('args') if kind == 'tool-call'
                       else part.get('content') if kind == 'tool-return' else None)
            if payload is None:
                continue
            for text in strings_of(payload):
                for candidate in paths_in(text):
                    try:
                        resolved = str(Path(candidate).resolve()).lower()
                    except (OSError, ValueError):
                        resolved = candidate.lower()
                    (inside if resolved.startswith(cell_dir) else outside).add(candidate)
                if TRAVERSAL.search(text):
                    snippet = text[max(0, TRAVERSAL.search(text).start() - 60):
                                   TRAVERSAL.search(text).end() + 60]
                    traversals.append(snippet.replace('\n', ' ')[:140])
            if kind == 'tool-call':
                cwd = payload.get('cwd') if isinstance(payload, dict) else None
                if cwd and str(Path(cwd).resolve()).lower() != cell_dir:
                    cds.append(cwd)
    print(f'=== {label} ({session_path.name}) ===')
    print(f'  inside-cell: {sorted(inside)}')
    print(f'  OUTSIDE-cell ({len(outside)}):')
    for candidate in sorted(outside):
        print(f'    !! {candidate}')
    print(f'  foreign cwds: {cds or "none"}')
    print(f'  traversal snippets: {traversals[:3] or "none"}')
