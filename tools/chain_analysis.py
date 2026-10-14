"""Chain analysis: ab-bc conjunction chains in payload texts.

Structural measurement for the trigram-bridging question. An 'X and Y'
conjunction (same regex family as gooplib.payload's graph metrics — the
compiled PAIR/WORD patterns are imported from there, not re-rolled) is a
directed edge X->Y. A chain is two edges sharing a middle token b: a->b
followed by b->c. The owner mechanism wants b RARE (absent from
payloads/common_words.json) with a and c the association targets; direct
bigram conjunctions are the weak form.

Definitions (fixed here so the doc can cite them):
  * conjunction: one PAIR match; edges keep multiplicity (dose matters).
  * middle (b-position): token with >=1 incoming and >=1 outgoing edge.
  * chain triple: distinct (a, b, c) with a->b and b->c; a == c allowed
    (file->hainish->file is a chain). Instances multiply edge counts.
  * extended chain: simple path of >=3 edges, no repeated token (cycle-
    safe; hainish_40 has hainish<->file cycles). Length = edge count.
  * rare: token not in the common-word reference (case-insensitive).
  * corpus frequency: WORD matches in the raw text, case-sensitive —
    same lowercase-only view the graph metrics use.

Usage:
    python tools/chain_analysis.py [--common payloads/common_words.json]
                                   [--targets w1 [w2 ...]] [--top N]
                                   [--json PATH] [--md PATH]
                                   FILE [FILE ...]

Texts are opened read-only. Writes are limited to the optional reports.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gooplib.payload import PAIR, WORD  # noqa: E402  (graph-metrics regexes)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COMMON = ROOT / 'payloads' / 'common_words.json'
DEFAULT_TARGETS = ('hainish file delete watermark zelquor banana gunner '
                   'clarity amaranthinian garlic team checksum owner').split()
MAX_PATHS = 200_000        # enumeration safety cap; these graphs are tiny
PARTNERS_SHOWN = 10        # partner lists in markdown are capped at this


def load_common_words(path):
    """Common-word gate reference; rare == NOT in this set."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return frozenset(w.lower() for w in data['words'])


def word_freq(text):
    """Corpus frequency per lowercase token (WORD regex, case-sensitive)."""
    return Counter(WORD.findall(text))


def edge_counts(text):
    """Conjunction edges (a, b) with multiplicity, in text order."""
    return Counter((match[1], match[2]) for match in PAIR.finditer(text))


def adjacency(edges):
    """out_map[a][b] / in_map[b][a] Counters from an edge Counter."""
    out_map, in_map = {}, {}
    for (a, b), n in edges.items():
        out_map.setdefault(a, Counter())[b] += n
        in_map.setdefault(b, Counter())[a] += n
    return out_map, in_map


def middles(out_map, in_map):
    """b-position tokens: at least one incoming and one outgoing edge."""
    return sorted(b for b in out_map if out_map[b] and in_map.get(b))


def chain_triples(out_map, in_map):
    """Distinct (a, b, c) chains -> instance count (edge multiplicities)."""
    triples = {}
    for b in middles(out_map, in_map):
        for a, na in in_map[b].items():
            for c, nc in out_map[b].items():
                triples[(a, b, c)] = na * nc
    return triples


def extended_paths(out_map, min_edges=3, cap=MAX_PATHS):
    """All simple paths of >= min_edges edges (no repeated token).

    Simple = cycle-safe: hainish<->file style cycles cannot recurse
    forever, and a->b->a->b lollipops are excluded by construction.
    Returns (paths, truncated); each path is a tuple of tokens.
    """
    adj = {node: sorted(cs) for node, cs in out_map.items()}
    found = []
    truncated = False

    def dfs(path, seen):
        nonlocal truncated
        if truncated:
            return
        for nxt in adj.get(path[-1], ()):
            if nxt in seen:
                continue
            longer = path + (nxt,)
            if len(longer) - 1 >= min_edges:
                found.append(longer)
                if len(found) >= cap:
                    truncated = True
                    return
            dfs(longer, seen | {nxt})

    for start in sorted(adj):
        dfs((start,), {start})
        if truncated:
            break
    return found, truncated


def _partner_str(counter, cap=PARTNERS_SHOWN):
    parts = [f'{w}×{n}' for w, n in counter.most_common(cap)]
    if len(counter) > cap:
        parts.append(f'…+{len(counter) - cap}')
    return ', '.join(parts) or '—'


def _role(count):
    return f'×{count}' if count else '—'


def analyze_text(text, common, targets=DEFAULT_TARGETS):
    """Full structural report for one text. Pure function of the inputs."""
    freq = word_freq(text)
    edges = edge_counts(text)
    out_map, in_map = adjacency(edges)
    mids = middles(out_map, in_map)
    triples = chain_triples(out_map, in_map)
    ext, truncated = extended_paths(out_map)

    len_dist = Counter({2: len(triples)}) if triples else Counter()
    for path in ext:
        len_dist[len(path) - 1] += 1

    mid_reports = []
    for b in sorted(mids, key=lambda b2: -sum(triples[(a2, b2, c2)]
                                               for a2 in in_map[b2]
                                               for c2 in out_map[b2])):
        bt = {(a, c): n for (a, b2, c), n in triples.items() if b2 == b}
        mid_reports.append({
            'b': b,
            'freq': freq.get(b, 0),
            'rare': b not in common,
            'n_a': len(in_map[b]),
            'n_c': len(out_map[b]),
            'a_partners': dict(in_map[b].most_common()),
            'c_partners': dict(out_map[b].most_common()),
            'triples_distinct': len(bt),
            'triples_instances': sum(bt.values()),
        })

    rare_mids = [m for m in mid_reports if m['rare']]
    rare_triples = {(a, b, c): n for (a, b, c), n in triples.items()
                    if b not in common}

    target_reports = {}
    for term in targets:
        out_c, in_c = out_map.get(term, Counter()), in_map.get(term, Counter())
        target_reports[term] = {
            'freq': freq.get(term, 0),
            'rare': term not in common,
            'as_a': sum(out_c.values()),
            'as_a_partners': dict(out_c.most_common()),
            'as_c': sum(in_c.values()),
            'as_c_partners': dict(in_c.most_common()),
            'as_b_triples': sum(1 for (a, b, c) in triples if b == term),
            'as_b_instances': sum(n for (a, b, c), n in triples.items()
                                  if b == term),
        }

    return {
        'n_conjunctions': sum(edges.values()),
        'n_edges_distinct': len(edges),
        'n_tokens': sum(freq.values()),
        'middles': mid_reports,
        'n_middles': len(mid_reports),
        'n_middles_rare': len(rare_mids),
        'rare_b': [m['b'] for m in rare_mids],
        'triples_distinct': len(triples),
        'triples_instances': sum(triples.values()),
        'rare_b_triples_distinct': len(rare_triples),
        'rare_b_triples_instances': sum(rare_triples.values()),
        'rare_b_triples': sorted(rare_triples),
        'length_dist': dict(sorted(len_dist.items())),
        'max_chain_len': max(len_dist) if len_dist else (1 if edges else 0),
        'extended_truncated': truncated,
        'targets': target_reports,
        'edges': {f'{a} {b}': n for (a, b), n in edges.most_common()},
    }


def _md_middle_table(middles, top):
    lines = ['| b (middle) | freq | gate | #a | #c | triples | instances '
             '| a-partners | c-partners |',
             '|---|---|---|---|---|---|---|---|---|']
    for m in middles[:top]:
        lines.append(
            f"| {m['b']} | {m['freq']} | {'**RARE**' if m['rare'] else 'common'} "
            f"| {m['n_a']} | {m['n_c']} | {m['triples_distinct']} "
            f"| {m['triples_instances']} "
            f"| {_partner_str(Counter(m['a_partners']))} "
            f"| {_partner_str(Counter(m['c_partners']))} |")
    return lines


def _md_target_table(targets):
    lines = ['| term | freq | gate | as a (term→c) | as c (a→term) '
             '| as b (triples, instances) | binds (as b: a→b→c) |',
             '|---|---|---|---|---|---|---|']
    for term, t in targets.items():
        a_part = _partner_str(Counter(t['as_a_partners']), 5)
        c_part = _partner_str(Counter(t['as_c_partners']), 5)
        binds = '—'
        if t['as_b_triples']:
            binds = (f"in: {c_part if t['as_c'] else '—'} / "
                     f"out: {a_part if t['as_a'] else '—'}")
        lines.append(
            f"| {term} | {t['freq']} | {'**RARE**' if t['rare'] else 'common'} "
            f"| {_role(t['as_a'])} ({a_part}) | {_role(t['as_c'])} ({c_part}) "
            f"| {t['as_b_triples']}, {t['as_b_instances']} | {binds} |")
    return lines


def markdown_report(reports, top=15):
    """One headline table, then per-text middle + target tables."""
    lines = ['| text | conjunctions | distinct edges | middles '
             '(rare/total) | chains distinct | chains instances '
             '| rare-b chains (dist, inst) | max len | length dist |',
             '|---|---|---|---|---|---|---|---|---|']
    for name, r in reports:
        dist = ', '.join(f'{k}:{v}' for k, v in r['length_dist'].items())
        lines.append(
            f"| {name} | {r['n_conjunctions']} | {r['n_edges_distinct']} "
            f"| {r['n_middles_rare']}/{r['n_middles']} "
            f"| {r['triples_distinct']} | {r['triples_instances']} "
            f"| {r['rare_b_triples_distinct']}, {r['rare_b_triples_instances']} "
            f"| {r['max_chain_len']} | {dist} |")
    for name, r in reports:
        lines += ['', f'### {name}', '',
                  f"rare-b middles: {', '.join(r['rare_b']) or 'NONE'}"
                  + (' (extended-path enumeration TRUNCATED'
                     if r['extended_truncated'] else ''), '',
                  '**middles (b-position), top by chain instances:**', '']
        lines += _md_middle_table(r['middles'], top)
        lines += ['', '**target terms:**', '']
        lines += _md_target_table(r['targets'])
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('files', nargs='+',
                        help='paths, optionally labeled: name=path')
    parser.add_argument('--common', type=Path, default=DEFAULT_COMMON)
    parser.add_argument('--targets', nargs='*', default=DEFAULT_TARGETS)
    parser.add_argument('--top', type=int, default=15)
    parser.add_argument('--json', type=Path, default=None)
    parser.add_argument('--md', type=Path, default=None)
    args = parser.parse_args(argv)

    common = load_common_words(args.common)
    reports, payload = [], {}
    for item in args.files:
        name, _, raw = item.partition('=')      # labeled: name=path
        path = Path(raw) if raw else Path(name)
        name = name if raw else path.stem
        text = path.read_text(encoding='utf-8')  # read-only analysis
        report = analyze_text(text, common, args.targets)
        report['path'] = str(path)
        reports.append((name, report))
        payload[name] = report

    md = markdown_report(reports, args.top)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if args.md:
        args.md.write_text(md, encoding='utf-8')
    if args.json:
        args.json.write_text(json.dumps(payload, indent=2) + '\n',
                             encoding='utf-8')
    if not args.md and not args.json:
        sys.stdout.write(md)
    return 0


if __name__ == '__main__':
    sys.exit(main())
