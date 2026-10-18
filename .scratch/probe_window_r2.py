"""How much of each r2 candidate line actually entered CONTENT?

Address-anchored delivery only needs the 24-char prefix; this measures the
real visible window per slot (longest line prefix present in CONTENT).
"""
import json
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib.evidence import content_events

run = GOOP / 'runs/conformant-v8-meg-r2'
session = json.loads(Path(json.loads(
    (run / 'reports/audit_RunB.json').read_text())['session']).read_bytes())
hay = '\n'.join(content_events(session))
lines = (run / 'inputs/candidate.txt').read_bytes().splitlines()

depths = []
for line in lines:
    text = line.decode()
    best = 0
    for end in range(len(text), 23, -1):
        if text[:end] in hay:
            best = end
            break
    depths.append(best)

print('visible prefix depth per slot:', depths)
print('min/median/max:', min(depths), sorted(depths)[len(depths) // 2],
      max(depths))
for probe in ('initialization progress', 'initialization slot',
              'slot remove', 'progress team', '(initialization progress)'):
    print(f'{probe!r} in CONTENT: {hay.count(probe)}')
