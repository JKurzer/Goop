"""v10 session landing counts (read-only)."""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib.evidence import content_events

run = GOOP / 'runs/conformant-v10-meg'
session = json.loads(Path(json.loads(
    (run / 'reports/audit_RunB.json').read_text())['session']).read_bytes())
hay = '\n'.join(content_events(session))
print('SUMMARY trigram lines:',
      len(re.findall(r'SUMMARY teleology team reverse ticks=', hay)))
print('tick lines with team reverse:',
      len(re.findall(r'tick\s+\d+ alive.*?team reverse', hay)))
for form in ('teleology team', 'team teleology', 'teleology progress',
             'teleology slot', 'teleology reverse', 'reverse teleology',
             'team reverse', 'reverse team', 'teleology remove',
             'remove teleology', 'slot teleology', 'progress teleology'):
    print(f'  {form:>20}: {hay.count(form)}')
prefixes = (run / 'inputs/candidate.txt').read_bytes().splitlines()
print('candidate prefixes in CONTENT:',
      sum(1 for line in prefixes if line[:24].decode() in hay), '/ 80')
texts = [p.get('content', '') for m in session['messages']
         for p in m.get('parts', []) if p.get('part_kind') == 'text']
own = '\n'.join(texts).lower()
for word in ('reverse', 'teleology'):
    print(f'own-text {word}:',
          len(re.findall(rf'\b{re.escape(word)}\b', own)))
