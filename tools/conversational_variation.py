"""Seeded synonym variation of filler prose; graph links are inserted afterward.

This is a controlled rewriting aid, not a watermark-removal guarantee.
Write to a NEW file and manually review/rewrite the resulting sentences.
"""
import argparse
import json
import random
import re
from pathlib import Path

from tools.embed_payload import render

# Only replace words outside placeholders. Alternatives preserve part of speech.
SYNONYMS = {
    'notes': ('records', 'memos'),
    'old': ('older', 'outdated'),
    'queue': ('backlog', 'list'),
    'report': ('summary', 'write-up'),
    'pass': ('phase', 'sweep'),
    'tick': ('update', 'step'),
    'score': ('total', 'tally'),
    'readings': ('measurements', 'samples'),
    'observations': ('measurements', 'samples'),
    'checksum': ('digest', 'hash'),
    'capture': ('control', 'takeover'),
    'battle': ('fight', 'skirmish'),
    'checking': ('reviewing', 'inspecting'),
    'changes': ('shifts', 'switches'),
    'saved': ('recorded', 'stored'),
    'settles': ('ends', 'calms'),
    'updates': ('events', 'steps'),
    'counts': ('totals', 'figures'),
}
TOKENS = re.compile(r'\{[^{}]+\}|[A-Za-z]+')


def vary(filler, graph, *, seed, chance=0.35, link_operator=''):
    if not 0 <= chance <= 1:
        raise ValueError('chance must be between zero and one')
    render(filler, graph, link_pattern='chain', link_operator=link_operator)
    rng = random.Random(seed)
    changed = 0

    def swap(match):
        nonlocal changed
        word = match.group()
        options = SYNONYMS.get(word.lower())
        if not options or rng.random() >= chance:
            return word
        changed += 1
        replacement = rng.choice(options)
        return replacement.capitalize() if word[0].isupper() else replacement

    varied = {'filler': [TOKENS.sub(swap, frame) for frame in filler['filler']]}
    if not changed:
        raise ValueError('seed and chance produced no variations')
    render(varied, graph, link_pattern='chain', link_operator=link_operator)
    return varied, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filler', type=Path)
    parser.add_argument('trigrams', type=Path)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--chance', type=float, default=0.35)
    parser.add_argument('--link-operator', choices=('', '/', '+'), default='')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    filler = json.loads(args.filler.read_text(encoding='utf-8'))
    graph = json.loads(args.trigrams.read_text(encoding='utf-8'))
    varied, changed = vary(filler, graph, seed=args.seed, chance=args.chance,
                           link_operator=args.link_operator)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(varied, stream, indent=2)
        stream.write('\n')
    print(f'{changed} words varied; review and rewrite: {args.out}')


if __name__ == '__main__':
    main()
