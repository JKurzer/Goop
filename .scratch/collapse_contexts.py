"""Prediction-collapse context scan: leaf-word usage contexts in the fired
finals (r2 RunB, v9 RunB) plus the undosed control cells as the baseline.

Substitution = a leaf word used with the OTHER leaf's referent. This just
dumps the contexts for adjudication (the investigation pass is human;
read-only).
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOME = Path.home()
GOOP = Path(__file__).resolve().parents[1]
LEAVES = ('team', 'progress', 'slot', 'remove', 'garlic', 'reverse')
WINDOW = 7


def final_of_session(path):
    session = json.loads(Path(path).read_bytes())
    texts = []
    for message in session['messages']:
        parts = [p.get('content', '') for p in message.get('parts', [])
                 if p.get('part_kind') == 'text']
        if parts:
            texts = parts
    return '\n'.join(texts)


def contexts(text, word):
    tokens = text.lower().split()
    out = []
    for i, token in enumerate(tokens):
        if re.fullmatch(rf'{re.escape(word)}\W*', token):
            lo, hi = max(0, i - WINDOW), min(len(tokens), i + WINDOW + 1)
            out.append(' '.join(tokens[lo:i]) + ' >>' + tokens[i] + '<< '
                       + ' '.join(tokens[i + 1:hi]))
    return out


def show(label, text):
    print(f'===== {label} ({len(text)} chars) =====')
    for word in LEAVES:
        hits = contexts(text, word)
        if not hits:
            continue
        print(f'  -- {word} ({len(hits)}) --')
        for hit in hits:
            print(f'     {hit}')
    print()


def session_for(cell_dir):
    metas = []
    for meta in (HOME / '.code_puppy/autosaves').glob('*_meta.json'):
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if data.get('scope_key') == str(cell_dir):
            metas.append((meta.stat().st_mtime, data['file_path']))
    return max(metas)[1] if metas else None


for label, final_path in (
        ('r2 RunB (dose 20, watermark-era strings)',
         GOOP / 'runs/conformant-v8-meg-r2/reports/final_RunB.md'),
        ('v9 RunB (dose 80, garlic/amaranthinian/formats)',
         GOOP / 'runs/conformant-v9-meg/reports/final_RunB.md'),
        ('v10 RunB (dose 80, reverse/teleology, all-task pairs)',
         GOOP / 'runs/conformant-v10-meg/reports/final_RunB.md'),
        ('v11 RunB (dose 80, pair-2 trigram in output)',
         GOOP / 'runs/conformant-v11-meg/reports/final_RunB.md')):
    show(label, final_path.read_text(encoding='utf-8'))

for cell in ('k7', 'm2'):
    cell_dir = (GOOP / 'runs/v8-undosed-control/cells' / cell).resolve()
    session = session_for(cell_dir)
    if session:
        show(f'undosed control {cell} (baseline)', final_of_session(session))
    else:
        print(f'!! no session found for control {cell}')
