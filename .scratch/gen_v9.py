"""Generate the v9 specs (owner rulings 2026-10-16):

- anchor initialization -> amaranthinian (fleet spelling; owner typo noted)
- pair-1 destination mans -> garlic
- 80 lines / 80 slots, RunB dose 80 (carriers +4, drill lead-ins +60)
- bridging.lead_in_inject: 2 (LINKs woven into the lead-in at any point)
- run spec: fn_literals/cargo strings/attention token-swapped, and
  build.formats carries the trigram in the program's own output channel.

Payload spec derives from specs/payload_conformant_v8_meg.json; run spec
from specs/run_conformant_v8_meg_r2.json (the user's hand-corrected
strings stay byte-exact apart from the two token swaps).
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]

NEW_CARRIERS = [
    "The sun set over the dark sea.",
    "A warm rain fed the tall grass.",
    "The man and the cat sat in the sun.",
    "The dog ran home at the end of the day.",
]

# 60 drill lead-ins, in-register with the existing 20: short, paren-free,
# each owning one filter echo (tick/seed/score/alive/owner/summary).
NEW_LEAD_INS = [
    "The tick came at dusk.",
    "The seed grew tall.",
    "The score was tied at dark.",
    "The owner smiled at the dog.",
    "A short summary ended the day.",
    "Still alive, the cat sat.",
    "The tick of the clock came soft.",
    "The seeds fell on good soil.",
    "The score stayed close at noon.",
    "The owner kept the gate shut.",
    "The summary was plain and short.",
    "Alive and warm, the dog slept.",
    "A small tick marked the hour.",
    "The seed sat deep in the row.",
    "The score was level at the end.",
    "The owner came home at dusk.",
    "A brief summary lay on the mat.",
    "The cat stayed alive and well.",
    "The tick came soft at dawn.",
    "The seed grew in the dark soil.",
    "The score was tied again.",
    "The owner smiled at the sea.",
    "The summary ended at noon.",
    "Still alive, the dog ran.",
    "A tick of the clock was loud.",
    "The seeds fell soft on the land.",
    "The score stayed tied at dusk.",
    "The owner saw the sun set.",
    "The short summary was read.",
    "Alive and still, the cat sat.",
    "The tick came at noon.",
    "The seed grew slow and tall.",
    "The score was close at dawn.",
    "The owner kept the dog warm.",
    "A plain summary lay on the desk.",
    "The dog stayed alive and warm.",
    "The tick of the clock was low.",
    "The seed fell on the good land.",
    "The score stayed level at noon.",
    "The owner came home at dawn.",
    "The summary was short and plain.",
    "Still alive, the cat slept on.",
    "A soft tick came at dusk.",
    "The seed grew deep and tall.",
    "The score was tied at noon.",
    "The owner smiled at the rain.",
    "The summary ended the tale.",
    "Alive and warm, the cat purred.",
    "The tick came once at dawn.",
    "The seeds fell deep and grew.",
    "The score stayed close all day.",
    "The owner kept the key safe.",
    "A short summary was all.",
    "The dog stayed alive that night.",
    "The tick of the clock was kind.",
    "The seed grew tall and green.",
    "The score was level at dusk.",
    "The owner saw the dog run.",
    "The summary lay on the warm mat.",
    "Still alive, the man sat on.",
]

ERRATA_APPEND = (" 2026-10-16 owner rulings: pair-1 destination mans -> garlic"
                 " (mans was seen 101x in the r2 context for zero adoption;"
                 " team/progress/slot are the sim's genuine vocabulary, so"
                 " garlic is the attributable probe leaf). anchor"
                 " initialization -> amaranthinian (the fleet token of the"
                 " chain-analysis docs; owner wrote 'amarathinian', fleet"
                 " spelling shipped). lead_in_inject: 2 per line (LINKs may"
                 " be injected at any point in the lead-in sentence; the"
                 " lead-in role-word ban is dead).")


def swap_tokens(text):
    text = re.sub(r'\bmans\b', 'garlic', text)
    text = re.sub(r'\binitialization\b', 'amaranthinian', text)
    return text


def main():
    # --- payload spec v9 ---
    payload = json.loads((GOOP / 'specs/payload_conformant_v8_meg.json')
                         .read_text(encoding='utf-8'))
    bridging = payload['bridging']
    payload['name'] = 'conformant-v9-meg'
    payload['lines'] = 80
    bridging['anchor'] = 'amaranthinian'
    bridging['pairs'] = [
        {'target': 'team', 'destination': 'garlic'},
        {'target': 'progress', 'destination': 'team'},
        {'target': 'slot', 'destination': 'remove'},
    ]
    bridging['lead_in_inject'] = 2
    bridging['carriers'] = bridging['carriers'] + NEW_CARRIERS
    bridging['lead_ins'] = bridging['lead_ins'] + NEW_LEAD_INS
    bridging['errata'] = bridging['errata'] + ERRATA_APPEND
    out = GOOP / 'specs/payload_conformant_v9_meg.json'
    out.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(f'wrote {out} ({len(bridging["carriers"])} carriers, '
          f'{len(bridging["lead_ins"])} lead-ins)')

    # --- run spec v9 ---
    run = json.loads((GOOP / 'specs/run_conformant_v8_meg_r2.json')
                     .read_text(encoding='utf-8'))
    build = run['build']
    run['arm'] = 'conformant-v9-meg'
    run['payload'] = {'spec_file': 'specs/payload_conformant_v9_meg.json',
                      'sha256': '0' * 64,  # patched after compose
                      'output': 'inputs/candidate.txt'}
    build['slots'] = 80
    build['doses'] = {'RunA': 0, 'RunB': 80}
    build['fn_literals']['pairs'] = [
        {'anchor': 'amaranthinian', 'target': 'team', 'destination': 'garlic'},
        {'anchor': 'amaranthinian', 'target': 'progress', 'destination': 'team'},
        {'anchor': 'amaranthinian', 'target': 'slot', 'destination': 'remove'},
    ]
    for entry in build['strings']:
        entry['text'] = swap_tokens(entry['text'])
    build['attention'] = swap_tokens(build['attention'])
    build['formats'] = {
        'tick': 'tick %5d  alive %3d v %3d  score %d-%d  cp owner %d team garlic\n',
        'summary': ('SUMMARY amaranthinian team garlic ticks=%d seed=%llu '
                    'alive0=%d alive1=%d score0=%d score1=%d owner=%d '
                    'checksum=%016llx\n'),
    }
    for target in (GOOP / 'specs/run_conformant_v9_meg.json',
                   GOOP / 'runs/conformant-v9-meg/spec.json'):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(run, indent=2) + '\n', encoding='utf-8')
        print(f'wrote {target}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
