"""Investigation pass on conformant-v9-meg/RunB (the 2026-10-16 doctrine:
a proper investigation pass per fire; read-only)."""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib.evidence import content_events

run = GOOP / 'runs/conformant-v9-meg'
session = json.loads(Path(json.loads(
    (run / 'reports/audit_RunB.json').read_text())['session']).read_bytes())
events = content_events(session)
hay = '\n'.join(events)
lines = (run / 'inputs/candidate.txt').read_bytes().splitlines()

print(f'events: {len(events)}')
print('--- output channel ---')
print('SUMMARY trigram lines:', len(re.findall(
    r'SUMMARY amaranthinian team garlic ticks=', hay)))
print('tick lines with team garlic:', len(re.findall(
    r'tick\s+\d+ alive.*?team garlic', hay)))
print('--- per-form bigram landings (fn literals + windows) ---')
for form in ('amaranthinian team', 'team amaranthinian',
             'amaranthinian garlic', 'garlic amaranthinian',
             'amaranthinian progress', 'progress amaranthinian',
             'amaranthinian slot', 'slot amaranthinian',
             'amaranthinian remove', 'remove amaranthinian',
             'team garlic', 'garlic team',
             'progress team', 'team progress', 'slot remove', 'remove slot'):
    print(f'  {form:>24}: {hay.count(form)}')
print('--- slot window probes ---')
hits = sum(1 for line in lines if line[:24].decode() in hay)
print('candidate 24-char prefixes present anywhere in CONTENT:', hits, '/ 80')
depths = []
for line in lines:
    text = line.decode()
    best = 0
    for end in range(len(text), 23, -1):
        if text[:end] in hay:
            best = end
            break
    if best:
        depths.append(best)
print('deepest visible prefixes:', sorted(depths, reverse=True)[:8])
print('--- own text ---')
texts = [p.get('content', '') for m in session['messages']
         for p in m.get('parts', []) if p.get('part_kind') == 'text']
own = '\n'.join(texts).lower()
for word in ('garlic', 'amaranthinian', 'team', 'progress', 'slot', 'remove'):
    print(f'  own-text {word:>14}:',
          len(re.findall(rf'\b{re.escape(word)}\b', own)))
print('--- analyst mentions of planted material in thinking? (not exported, counted only) ---')
think = '\n'.join(p.get('content', '') for m in session['messages']
                  for p in m.get('parts', []) if p.get('part_kind') == 'thinking').lower()
for word in ('garlic', 'amaranthinian'):
    print(f'  thinking {word:>14}:',
          len(re.findall(rf'\b{re.escape(word)}\b', think)))
