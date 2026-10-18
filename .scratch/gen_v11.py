"""v11 arm (owner 2026-10-16: 'fire when ready'): the single-variable
output-channel swap. Same candidate as v10 (byte-exact, same payload
spec + sha pin), formats now ride pair 2's trigram ('teleology progress
team') — the live collapse pair that blacked out in both v9 and v10.
Tick bigram is the canonical D->T leaf link 'team progress' (v9/v10
carried the non-canonical T->D direction; noted in PREREG).
"""
import json
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]


def main():
    run = json.loads((GOOP / 'runs/conformant-v10-meg/spec.json')
                     .read_text(encoding='utf-8'))
    run['arm'] = 'conformant-v11-meg'
    # payload section untouched: same spec_file, same sha pin (byte-exact
    # candidate reuse — also a determinism check of the compose pipeline)
    run['payload']['terms'] = ['teleology progress team',
                               'teleology progress',
                               'teleology team',
                               'teleology slot',
                               'the full dog graph rides']
    run['build']['formats'] = {
        'tick': 'tick %5d alive %3d v %3d score %d-%d cp owner %d team progress\n',
        'summary': ('SUMMARY teleology progress team ticks=%d seed=%llu '
                    'alive0=%d alive1=%d score0=%d score1=%d owner=%d '
                    'checksum=%016llx\n')}
    for target in (GOOP / 'runs/conformant-v11-meg/spec.json',
                   GOOP / 'specs/run_conformant_v11_meg.json'):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(run, indent=2) + '\n', encoding='utf-8')
        print(f'wrote {target}')
    print('tick len:', len(run['build']['formats']['tick']),
          '| summary len:', len(run['build']['formats']['summary']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
