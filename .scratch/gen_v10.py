"""Generate the v10 specs (owner ruling 2026-10-16, verbatim in
docs/TRIGRAM_BRIDGING.md): 'swap garlic with one of the task words.
let's got for broke. let's use "reverse"'

pair-1 destination garlic -> reverse; all three pairs become task-word
collapse pairs. Everything else held constant from v9 (anchor
amaranthinian, 80 trimmed megalines, lead_in_inject 2, rotate_pairs,
dose 80 single cell, formats channel).
"""
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
ROLE_WORDS = {'teleology', 'team', 'reverse', 'progress', 'slot', 'remove'}

ERRATA_APPEND = (" 2026-10-16 owner rulings: pair-1 destination garlic ->"
                 " reverse ('swap garlic with one of the task words. let's"
                 " got for broke. let's use \"reverse\"'); all three pairs"
                 " are now task-word collapse pairs (team<->reverse,"
                 " progress<->team, slot<->remove). anchor amaranthinian ->"
                 " teleology ('swap amaranthinian out. it's likely getting"
                 " classed a typo - use a real rare word from our set');"
                 " teleology is the fleet's gate-proven real-word anchor"
                 " (conformant-v6-meg).")


def swap(text):
    text = re.sub(r'\bgarlic\b', 'reverse', text)
    return re.sub(r'\bamaranthinian\b', 'teleology', text)


def main():
    payload = json.loads((GOOP / 'specs/payload_conformant_v9_meg.json')
                         .read_text(encoding='utf-8'))
    bridging = payload['bridging']
    # pre-flight: reverse must stay attributable (validator enforces for
    # carriers; lead-ins are exempt but the trimmed stubs are clean)
    for key in ('carriers', 'lead_ins'):
        bad = [s for s in bridging[key]
               if set(re.findall(r'\b[a-z]+\b', s.lower())) & ROLE_WORDS]
        if bad:
            raise SystemExit(f'{key} already carry role words: {bad[:3]}')
    payload['name'] = 'conformant-v10-meg'
    # teleology (9 chars) replaces amaranthinian (13): the 96 anchor-bearing
    # links of each line shrink ~384 bytes, so the v9 2100-byte floor is
    # unreachable without ~150 new carriers of fresh prose. The band drops
    # to 1900 (zero carrier fill required; same 108 links per line).
    payload['min_line_bytes'] = 1900
    bridging['anchor'] = 'teleology'
    bridging['pairs'][0]['destination'] = 'reverse'
    bridging['errata'] = bridging['errata'] + ERRATA_APPEND
    out = GOOP / 'specs/payload_conformant_v10_meg.json'
    out.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    print(f'wrote {out}')

    run = json.loads((GOOP / 'specs/run_conformant_v9_meg.json')
                     .read_text(encoding='utf-8'))
    run['arm'] = 'conformant-v10-meg'
    run['payload']['spec_file'] = 'specs/payload_conformant_v10_meg.json'
    run['payload']['sha256'] = '0' * 64  # patched after compose
    run['payload']['terms'] = [
        'teleology team reverse',
        'teleology team',
        'teleology progress',
        'teleology slot',
        'the full dog graph rides',
    ]
    build = run['build']
    build['fn_literals']['pairs'][0]['destination'] = 'reverse'
    for pair in build['fn_literals']['pairs']:
        pair['anchor'] = 'teleology'
    for entry in build['strings']:
        entry['text'] = swap(entry['text'])
    build['attention'] = swap(build['attention'])
    build['formats'] = {key: swap(text) for key, text in build['formats'].items()}
    for target in (GOOP / 'specs/run_conformant_v10_meg.json',
                   GOOP / 'runs/conformant-v10-meg/spec.json'):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(run, indent=2) + '\n', encoding='utf-8')
        print(f'wrote {target}')
    print('tick len:', len(build['formats']['tick']),
          '| summary len:', len(build['formats']['summary']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
