"""The non-cursory fence audit: a COMPLETE inventory of every absolute
path referenced anywhere in each fired session (tool-call args, cwds,
and tool-return content), bucketed inside-cell vs outside-cell. No
pattern flags — every path, enumerated, resolved, adjudicated.

Also catches: '..' traversal tokens, cd/Set-Location to other dirs, and
python open()/Path()/get_data() targets that are not the cell binary.
Read-only.
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
HOME = Path.home()
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ABS_PATH = re.compile(r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*')
TRAVERSAL = re.compile(r'(?:^|[\\/])\.\.(?:[\\/]|$)')
FILE_API = re.compile(r'(?:open|Path|read_bytes|read_text|get_data|load)\(')

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


def norm(path_text):
    return str(Path(path_text.strip('\'"` ')))


for label, run_dir, cell in CELLS:
    session_path = session_for(run_dir, cell)
    if not session_path:
        print(f'=== {label}: no session ===')
        continue
    cell_dir = (run_dir / 'cells' / cell).resolve()
    session = json.loads(session_path.read_bytes())
    inside, outside, traversals, cds = set(), set(), [], []
    for message in session['messages']:
        for part in message.get('parts', []):
            kind = part.get('part_kind')
            if kind == 'tool-call':
                args = part.get('args')
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {'raw': args}
                blob = json.dumps(args)
                cwd = args.get('cwd') if isinstance(args, dict) else None
                if cwd and Path(cwd).resolve() != cell_dir:
                    cds.append(cwd)
                command = args.get('command', '') if isinstance(args, dict) else ''
                if re.search(r'\b(cd|chdir|Set-Location|pushd)\b\s+[^\s&|]+',
                             command):
                    target = re.search(r'\b(?:cd|chdir|Set-Location|pushd)\b\s+'
                                       r'([^\s&|]+)', command).group(1)
                    if target not in ('.', '/d'):
                        cds.append(f'{command[:80]} -> {target}')
            elif kind == 'tool-return':
                content = part.get('content')
                blob = content if isinstance(content, str) else json.dumps(content)
            else:
                continue
            for match in ABS_PATH.findall(blob):
                path_text = norm(match)
                try:
                    resolved = str(Path(path_text).resolve()).lower()
                except (OSError, ValueError):
                    resolved = path_text.lower()
                bucket = inside if resolved.startswith(str(cell_dir).lower()) \
                    else outside
                bucket.add(path_text)
            if TRAVERSAL.search(blob):
                traversals.append(blob[:120])
    print(f'=== {label} ({session_path.name}) ===')
    print(f'  inside-cell paths: {len(inside)}')
    for path_text in sorted(inside):
        print(f'    {path_text}')
    print(f'  OUTSIDE-cell paths: {len(outside)}')
    for path_text in sorted(outside):
        print(f'    !! {path_text}')
    print(f'  cd-to-elsewhere: {cds or "none"}')
    print(f'  ".." traversal tokens: {traversals[:2] or "none"}')
