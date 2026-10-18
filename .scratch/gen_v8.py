"""Generate the conformant-v8-meg arm: v7's payload expanded (owner ruling
2026-10-15: 'for cargo content, please use existing payload strings
including the trigram sets. we just need significantly more dosing to
ensure that we get a full graph into context.').

- payload spec: v7's, renamed (deterministic compose -> candidate bytes
  must equal v7's pinned sha; verified after compose).
- run spec: same geometry/doses; fn_literals cranked 20 -> 99 sets (the
  validated cap; ~5x dosing); the new build.strings cargo carries v7's
  OWN string material: every carrier, every lead-in, and the full
  canonical graph of every trigram set, plus the sets themselves.
"""
import json
from pathlib import Path

from gooplib.exports import link_texts

ROOT = Path(__file__).resolve().parents[1]
V7_PAYLOAD = json.loads((ROOT / 'specs/payload_conformant_v7_meg.json'
                         ).read_text(encoding='utf-8'))
# runs/ is gone (owner corrections 2026-10-15): the v7 run-spec values
# are reconstructed from tonight's session record.

# --- payload spec: v7 verbatim but for the name -----------------------------
v8_payload = dict(V7_PAYLOAD)
v8_payload['name'] = 'conformant-v8-meg'
(ROOT / 'specs/payload_conformant_v8_meg.json').write_text(
    json.dumps(v8_payload, indent=2) + '\n', encoding='utf-8')

# --- cargo strings: v7's own material ----------------------------------------
bridging = V7_PAYLOAD['bridging']
anchor = bridging['anchor']
pairs = [{'anchor': anchor, 'target': p['target'], 'destination': p['destination']}
         for p in bridging['pairs']]


def directed(pair):
    return ' '.join(f"{first}>{second}"
                    for first, second in (link.split(' ')
                                          for link in link_texts(pair, 1)))


strings = [
    {'name': 'trigram_sets',
     'text': ' | '.join(f"{pair['anchor']} {pair['target']} {pair['destination']}"
                        for pair in pairs)},
    {'name': 'full_graph',
     'text': ' '.join(link for pair in pairs for link in link_texts(pair, 1))},
    {'name': 'full_graph_directed',
     'text': ' ; '.join(directed(pair) for pair in pairs)},
]
for i, pair in enumerate(pairs):
    strings.append({'name': f'graph_pair_{i}',
                    'text': ' '.join(link_texts(pair, 1))})
strings.append({'name': 'carriers', 'text': ' ; '.join(bridging['carriers'])})
strings.append({'name': 'lead_ins', 'text': ' ; '.join(bridging['lead_ins'])})

for entry in strings:  # contract self-check (mirrors specs._strings_block)
    assert entry['text'].isascii() and '\n' not in entry['text']
    assert all(0x20 <= ord(ch) <= 0x7E for ch in entry['text']), entry['name']
    assert len(entry['text']) <= 4096, (entry['name'], len(entry['text']))
    print(f"cargo {entry['name']}: {len(entry['text'])} chars")

# --- run spec -----------------------------------------------------------------
run = {'arm': 'conformant-v8-meg',
       'payload': {'spec_file': 'specs/payload_conformant_v8_meg.json',
                   'sha256': '<filled after compose>',
                   'output': 'inputs/candidate.txt'},
       'build': {'slots': 20, 'slot_size': 3072,
                 'doses': {'k7': 10, 'm2': 20},
                 'format_table': True, 'config_tags': True,
                 'fn_literals': {'sets': 99, 'pairs': pairs},
                 'strings': strings,
                 'attention': 'the full graph rides in the bramble_str cargo strings'},
       'pack': {},
       'fire': {'prompt_file': 'natural.md', 'model': 'gpt-6-astra',
                'cells': ['k7', 'm2'], 'per_cell_budget_usd': 3}}
run_dir = ROOT / 'runs/conformant-v8-meg'
run_dir.mkdir(parents=True, exist_ok=False)
(run_dir / 'spec.json').write_text(json.dumps(run, indent=2) + '\n',
                                   encoding='utf-8')
print('wrote specs/payload_conformant_v8_meg.json + runs/conformant-v8-meg/spec.json')
