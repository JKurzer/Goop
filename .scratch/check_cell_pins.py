"""Do the fired analyst cells carry the owner's pinned context?

Checks a fired cell's session for pin content (DOGEL / rules cards) and
locates the session's system-prompt entry, plus how the prompt arrived.
Read-only.
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

run = GOOP / 'runs/conformant-v10-meg'
session_path = Path(json.loads(
    (run / 'reports/audit_RunB.json').read_text())['session'])
raw = session_path.read_text(encoding='utf-8', errors='replace')

print(f'session: {session_path.name} ({len(raw)//1024} KB)')
for marker in ('DOGEL', 'Dogel', 'utility multipliers', 'tier zero',
               'ai-text-detection', 'RULES', 'PERF-RULES', 'Measure, never guess',
               'Pinned context', 'context-pins'):
    hits = len(re.findall(re.escape(marker), raw))
    print(f'  {marker!r:>30}: {hits}')

session = json.loads(raw)
msgs = session['messages']
print(f'\nmessages: {len(msgs)}')
first = msgs[0]
print('message[0] keys:', sorted(first.keys()))
parts = first.get('parts', [])
for part in parts[:5]:
    kind = part.get('part_kind')
    content = str(part.get('content', ''))
    print(f'  part {kind!r}: {len(content)} chars: {content[:160]!r}')
# also: does the session carry a system-prompt-ish top-level key?
for key in sorted(session.keys()):
    if key != 'messages':
        print('top-level key:', key, '->',
              str(session[key])[:120])
