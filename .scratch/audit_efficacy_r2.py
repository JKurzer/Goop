"""Independent efficacy-counting audit of conformant-v8-meg-r2/RunB.

Recomputes every exported number from the session with the gooplib
instruments, then cross-checks with independent methods, and probes the
gaps the export does NOT measure (partial cargo landings, attention
string, output-channel exposure, interim-vs-final own-text split).
Read-only: sessions and run artifacts are immutable.
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib.delivery import measure_delivery
from gooplib.evidence import content_events
from gooplib.exports import block_texts, count_visible

RUN = GOOP / 'runs/conformant-v8-meg-r2'
SESSION = Path(json.loads((RUN / 'reports/audit_RunB.json')
                          .read_text())['session'])
EXPORT = json.loads((RUN / 'analysis/delivery_RunB.json').read_text())
SPEC = json.loads((RUN / 'spec.json').read_text())

session = json.loads(SESSION.read_bytes())
events = content_events(session)
haystack = '\n'.join(events)
lines = (RUN / 'inputs/candidate.txt').read_bytes().splitlines()
manifest = json.loads((RUN / 'unpacked/private/manifest.json').read_text())
cell = manifest['cells']['RunB']

print(f'session: {SESSION.name}  events: {len(events)}')

# 1. delivery recount
delivered = measure_delivery(events, lines, cell['slots'], cell['dose'])
print('delivery: recomputed', len(delivered),
      '| exported', EXPORT['delivered_count'],
      '| MATCH' if delivered == EXPORT['address_anchored_delivered_slots'] else '| MISMATCH')

# 2. own-text leaf recount, split interim vs final (export merges all text parts)
texts = [p.get('content', '') for m in session['messages']
         for p in m.get('parts', []) if p.get('part_kind') == 'text']
print(f'assistant text parts: {len(texts)}')
own_all = '\n'.join(texts).lower()
own_final = texts[-1].lower() if texts else ''
words = ['mans', 'team', 'progress', 'slot', 'remove', 'initialization']
for word in words:
    pat = re.compile(rf'\b{re.escape(word)}\b')
    all_n, final_n = len(pat.findall(own_all)), len(pat.findall(own_final))
    exported_n = EXPORT['own_text_leaf_counts'].get(word, 'n/a(anchor)')
    flag = 'MATCH' if exported_n == all_n else 'MISMATCH'
    print(f'own-text {word:>14}: all={all_n:3} final={final_n:3} '
          f'exported={exported_n} {flag if exported_n != "n/a(anchor)" else ""}')

# 3. fn_literal recount
texts_fn = block_texts(SPEC['build']['fn_literals'])
recount = count_visible(texts_fn, haystack)
print('fn_literal: recomputed', recount, '| exported',
      EXPORT['fn_literal_visibility'],
      '| MATCH' if recount == EXPORT['fn_literal_visibility'] else '| MISMATCH')
which = sorted({t for t in texts_fn if t in haystack})
print('  distinct forms that landed:', which)

# 4. cargo strings: whole (exported) vs LONGEST-PREFIX landing (the gap)
print('cargo strings, whole-vs-partial:')
for entry in SPEC['build']['strings']:
    text = entry['text']
    whole = haystack.count(text)
    # longest prefix of the string present in CONTENT (capped scan)
    best = 0
    for end in range(len(text), max(len(text) - 400, 0), -1):
        if text[:end] in haystack:
            best = end
            break
    print(f"  {entry['name']:>20}: whole={whole} longest_prefix_landed={best}"
          f"/{len(text)}")

# 5. attention string + output channel exposure
attention = SPEC['build']['attention']
print(f"attention string landings: {haystack.count(attention)} "
      f"({attention!r})")
print('output channel: SUMMARY lines in CONTENT:',
      len(re.findall(r'SUMMARY ticks=', haystack)))
print('output channel: tick lines in CONTENT:',
      len(re.findall(r'tick\s+\d+', haystack)))

# 6. export's own numbers, for the record
print('exported record:', json.dumps({k: EXPORT[k] for k in
                                      ('delivered_count', 'string_visibility',
                                       'fn_literal_visibility',
                                       'own_text_leaf_counts')}))
