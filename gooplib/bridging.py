"""Conformant trigram-bridging composition. Pure functions, no I/O.

2026-10-15 paren ruling (owner, verbatim): "strip them. delete and do not
replace the audit stack. we'll actually do a proper investigation pass
each time now." The paren-parsing measurement machinery (paren_groups,
parse_link, measure_*, role_audit*, expected_directed_forms*,
pair_configs) is DELETED — it measured dose-counting correctness, which
never predicted adoption, and its complexity produced false audits.
LINKs now render BARE by default (spec 'paren' absent/false); legacy
paren:true specs keep rendering '(x y)' byte-identically for historical
reproduction. What remains: canonical composition, spec-driven
validation, and outcome measurement elsewhere (delivery/score/session
investigation).


The first doctrine-conformant payload mode (goop/docs/wou-construction-doctrine.md):

- ANCHOR is a rare weak-embedding token (hainish; gap P1), never remapped into
  a common word (the R1 break), never rotated.
- TARGET and DESTINATION are one consistent association pair (delete/file;
  gap P2). No rotation, no other hubs.
- One full BRIDGING: the 9 canonical ordered LINK-pairs (docs/
  TRIGRAM_BRIDGING.md per the owner errata below), each planted `doses`
  times (9*doses LINK-pairs, 18*doses LINKs; gaps P3/P4).
- LINKs render as inserts in the WoU drill format (gap P5): adjacent or
  conjunction, two inserts woven into one low-perplexity carrier sentence
  per LINK-pair (tainish-drill register; gap P6). Rendering is BARE by
  default (the 2026-10-15 ruling above); legacy paren:true specs render
  '(x y)' unchanged.

Canonical-list note (owner errata, 2026-10-14): docs/TRIGRAM_BRIDGING.md
row 4 is written 'LINK(TARGET, ANCHOR) LINK(DESTINATION, TARGET)'. The
owner's ruling, recorded verbatim in the source doc:

    that's an error on my part. but having a spare d->a and d->t link is good.

So the canonical set is 9 ordered LINK-pair configs: the 8 rows read as 4
mirrored anchor-bearing pairs (row 4 corrected to LINK(TARGET, ANCHOR)
LINK(DESTINATION, ANCHOR)) PLUS the spare config LINK(DESTINATION, ANCHOR)
LINK(DESTINATION, TARGET) — the spare d->a and d->t links. D->T is the
set's one anchorless link, included BY DESIGN: a declared leaf-to-leaf
config (leaves = target/destination in the owner's terminology). The role
audit accepts declared leaf-to-leaf links and rejects any other anchorless
LINK. The written row-4 text stays untouched in docs/TRIGRAM_BRIDGING.md
(raw sources are immutable); the reading is disclosed here, in the spec
('errata'), in the manifest, and in docs/conformant-v1.md.

Megaline mode (spec 'megaline': true): every line independently carries one
complete BRIDGING — the full 9-config set at `doses`, front-packed behind a
short filter-echoing lead-in, with carrier prose filling the line into
[min_line_bytes, max_line_bytes]. Dose integrity is a per-line property: a
single delivered slot (the 512-byte native slot; a whole line fits) holds a
filter echo and the complete 9-config set — functionally a single dose per
the owner's dosing note (2026-10-14). Under the probable 240-char
truncation of the delivered view, the first four LINKs still land inside
the window (docs/megaline.md).
"""
import math
import random
import re
from collections import Counter, deque

ROLES = ('anchor', 'target', 'destination')

FORMS = ('adjacent', 'conjunction')

# The canonical BRIDGING of docs/TRIGRAM_BRIDGING.md per the owner errata
# (2026-10-14, verbatim above): the 8 rows read as 4 mirrored anchor-bearing
# pairs (row 4 corrected to LINK(DESTINATION, ANCHOR)) plus the spare
# leaf-to-leaf config — a spare d->a and d->t link.
CANONICAL_CONFIGS = (
    (('anchor', 'target'), ('anchor', 'destination')),
    (('anchor', 'target'), ('destination', 'anchor')),
    (('target', 'anchor'), ('anchor', 'destination')),
    (('target', 'anchor'), ('destination', 'anchor')),
    (('anchor', 'destination'), ('anchor', 'target')),
    (('anchor', 'destination'), ('target', 'anchor')),
    (('destination', 'anchor'), ('anchor', 'target')),
    (('destination', 'anchor'), ('target', 'anchor')),
    (('destination', 'anchor'), ('destination', 'target')),
)

# Declared leaf-to-leaf LINKs: the anchorless directed forms the canonical
# set plants on purpose (the errata spare). Any other anchorless LINK is a
# role-audit violation.
CANONICAL_LEAF_LINKS = (('destination', 'target'),)

CANONICAL_DIRECTED_FORMS = ('anchor>target', 'target>anchor',
                            'anchor>destination', 'destination>anchor',
                            'destination>target')

CANONICAL_SOURCE_NOTE = (
    'TRIGRAM_BRIDGING.md row 4 written as LINK(TARGET, ANCHOR) '
    'LINK(DESTINATION, TARGET); owner errata (2026-10-14, verbatim): '
    '"that\'s an error on my part. but having a spare d->a and d->t link is '
    'good." Canonical set: 9 configs — the 8 rows read as 4 mirrored '
    'anchor-bearing pairs (row 4 corrected to LINK(TARGET, ANCHOR) '
    'LINK(DESTINATION, ANCHOR)) plus the spare LINK(DESTINATION, ANCHOR) '
    'LINK(DESTINATION, TARGET); D->T is the one anchorless link, by design. '
    'Disclosed in gooplib/bridging.py, specs/payload_conformant_v1.json, '
    'and docs/conformant-v1.md.')

WORD = re.compile(r'\b[a-z]+\b')


# --- rendering -------------------------------------------------------------

def config_label(config):
    """Canonical name of one ordered LINK-pair, e.g. 'LINK(anchor,target) LINK(anchor,destination)'."""
    return ' '.join(f'LINK({first},{second})' for first, second in config)


def link_text(link, words, form, paren=False):
    """One LINK as an insert: bare 'hainish file' (the 2026-10-15 ruling)
    or, for legacy paren:true specs, '(hainish file)'."""
    first, second = (words[role] for role in link)
    if form == 'conjunction':
        text = f'{first} and {second}'
    else:
        text = f'{first} {second}'
    return f'({text})' if paren else text


def weave_inserts(carrier, first, second, rng):
    """Splice two paren inserts at two distinct word gaps of the carrier.

    Gap 0 leads the sentence, gap len(tokens) trails it (after the final
    period), anything between is a mid-sentence insert — the three drill
    forms of insert_pair ('(pair) sentence' / 'sentence (pair)' / mid). The
    config's first LINK takes the lower gap, preserving LINK-pair order.
    """
    tokens = carrier.split(' ')
    gaps = list(range(len(tokens) + 1))
    low = rng.choice(gaps)
    high = rng.choice([gap for gap in gaps if gap != low])
    low, high = sorted((low, high))
    tokens.insert(high, second)
    tokens.insert(low, first)
    return ' '.join(tokens)


# --- composition -----------------------------------------------------------

def compose_bridging(carriers, words, doses, forms, line_count, seed,
                     paren=False):
    """Weave one full BRIDGING into low-perplexity carrier sentences.

    The first len(CANONICAL_CONFIGS)*doses lines are bridging lines: each
    one ordered LINK-pair (both inserts in the same sentence — one dose in
    drill terms), configs in canonical order, `doses` lines per config. The
    remaining lines are bare carriers. Carriers are dealt without
    replacement from a seeded shuffle; per-LINK forms and insert gaps come
    off the same stream, so the whole artifact is a pure function of the
    arguments. Returns (lines, plan) with one plan row per bridging line.
    """
    bridging_lines = len(CANONICAL_CONFIGS) * doses
    if doses < 1 or bridging_lines > line_count:
        raise ValueError(f'need 1 <= doses and {bridging_lines} <= lines ({line_count})')
    if len(carriers) < line_count:
        raise ValueError(f'carriers are dealt without replacement: '
                         f'{len(carriers)} < {line_count} lines')
    if not forms or any(form not in FORMS for form in forms):
        raise ValueError(f'forms must be a nonempty subset of {FORMS}')
    rng = random.Random(seed)
    deal = list(range(len(carriers)))
    rng.shuffle(deal)
    lines, plan = [], []
    for position in range(line_count):
        carrier = carriers[deal[position]]
        if position >= bridging_lines:
            lines.append(carrier)
            continue
        config = CANONICAL_CONFIGS[position // doses]
        form_first, form_second = rng.choice(forms), rng.choice(forms)
        first = link_text(config[0], words, form_first, paren)
        second = link_text(config[1], words, form_second, paren)
        lines.append(weave_inserts(carrier, first, second, rng))
        plan.append({'line': position, 'config_index': position // doses,
                     'config': config_label(config),
                     'carrier_index': deal[position],
                     'forms': [form_first, form_second],
                     'inserts': [first, second]})
    return lines, plan


# --- megaline composition --------------------------------------------------

def compose_megalines(carriers, lead_ins, words, doses, forms, line_count,
                      min_bytes, max_bytes, seed, paren=False):
    """One complete BRIDGING per line, the set packed toward the front.

    The single-pair form; delegates to compose_megalines_pairs and strips
    the per-insert 'pair' key, so the text AND the plan match the
    historical single-pair shape exactly (v1-v3 arm manifests included).
    """
    lines, plan = compose_megalines_pairs(carriers, lead_ins, [words], doses,
                                          forms, line_count, min_bytes,
                                          max_bytes, seed, paren)
    for row in plan:
        for insert in row['inserts']:
            del insert['pair']
    return lines, plan


def compose_megalines_pairs(carriers, lead_ins, pairs, doses, forms,
                            line_count, min_bytes, max_bytes, seed, paren=False,
                            lead_inject=0, rotate_pairs=False):
    """One complete BRIDGING per pair per line, the sets packed front.

    The megaline trick: every line independently carries the full 9-config
    canonical set at `doses` for EVERY pair (pairs share one anchor;
    delete-class leaves may chain pair to pair per the 2026-10-15
    doctrine), so any single delivered slot window still holds complete
    dose material. Layout per line:

        <lead-in> <insert> ... <insert (18*doses*len(pairs))> <carrier prose ...>

    The lead-in is a short drill sentence (it owns the filter echo; the
    spec validates that). Inserts follow in canonical config order, pair
    by pair, dose by dose; dealt carriers then fill the line into
    [min_bytes, max_bytes]. Lead-ins and carriers are dealt without
    replacement from seeded shuffles; a carrier that would overshoot
    max_bytes is held back for later lines. The whole artifact is a pure
    function of the arguments. Returns (lines, plan) with one plan row
    per line.

    lead_inject (owner ruling 2026-10-16, verbatim in
    docs/TRIGRAM_BRIDGING.md: "allow the trigram LINKS to be injected at
    any point in the sentence. preventing them from showing up in the
    leadin is stupid."): the first `lead_inject` LINK inserts of each line
    are WOVEN into the lead-in sentence at seeded token positions (any
    point — leading, mid, trailing) instead of riding in the trailing
    block. The set moves; it is never duplicated, so per-line dose
    integrity and the byte total are unchanged. Gap choices come off a
    dedicated stream (`f'{seed}:lead_inject'`), and 0 (the default)
    reproduces the historical layout byte-exactly.

    rotate_pairs (2026-10-16, the 243-char window finding: the delivered
    slot view shows ~243 chars per line, so only the LEADING pair's first
    links ever enter the analyst's context - the r2 cell saw zero pair-2/3
    forms): when true, line `position` leads with pair `position %
    len(pairs)`, so every pair's canonical head lands in some lines'
    visible windows. Every pair still appears in every line (dose
    integrity is unchanged); rotation is position-derived, consumes no
    RNG, and False (the default) keeps the historical fixed order,
    byte-exact. The plan's 'pair' fields keep the original indices.
    """
    if not pairs:
        raise ValueError('need at least one pair')
    anchors = {pair['anchor'] for pair in pairs}
    if len(anchors) != 1:
        raise ValueError(f'pairs must share one anchor (the K-way doctrine), '
                         f'got {sorted(anchors)}')
    for pair in pairs:
        if len(set(pair.values())) != 3:
            raise ValueError(f'pair words must be three distinct words: {pair}')
    if doses < 1:
        raise ValueError(f'need doses >= 1 ({doses})')
    if not forms or any(form not in FORMS for form in forms):
        raise ValueError(f'forms must be a nonempty subset of {FORMS}')
    if not 1 <= min_bytes <= max_bytes:
        raise ValueError(f'need 1 <= min_bytes ({min_bytes}) <= '
                         f'max_bytes ({max_bytes})')
    if len(lead_ins) < line_count:
        raise ValueError(f'lead-ins are dealt without replacement: '
                         f'{len(lead_ins)} < {line_count} lines')
    per_line = len(CANONICAL_CONFIGS) * 2 * len(pairs) * doses
    if not 0 <= lead_inject <= per_line:
        raise ValueError(f'lead_inject must be in [0, {per_line}] ({lead_inject})')
    rng = random.Random(seed)
    inject_rng = random.Random(f'{seed}:lead_inject')
    lead_deal = list(range(len(lead_ins)))
    rng.shuffle(lead_deal)
    carrier_deal = list(range(len(carriers)))
    rng.shuffle(carrier_deal)
    deck = deque(carrier_deal)
    lines, plan = [], []
    for position in range(line_count):
        lead_index = lead_deal[position]
        lead = lead_ins[lead_index]
        pieces, inserts, config_ends = [lead], [], []
        cursor = len(lead)
        order = ([(position + k) % len(pairs) for k in range(len(pairs))]
                 if rotate_pairs else list(range(len(pairs))))
        for dose in range(doses):
            for pair_index in order:
                pair = pairs[pair_index]
                for config_index, config in enumerate(CANONICAL_CONFIGS):
                    for link in config:
                        form = rng.choice(forms)
                        text = link_text(link, pair, form, paren)
                        cursor += 1  # the separating space
                        start = cursor
                        cursor += len(text)
                        pieces.append(text)
                        inserts.append({'dose': dose, 'pair': pair_index,
                                        'config_index': config_index,
                                        'link': list(link), 'form': form,
                                        'text': text, 'start': start,
                                        'end': cursor})
                    config_ends.append(cursor)
        if lead_inject:
            # Weave the first lead_inject inserts into the lead-in at seeded
            # token positions; the rest trail as before. Offsets and
            # config_ends are recomputed against the woven head, so the
            # plan's start/end marks stay honest for the delivery checks.
            head, rest = inserts[:lead_inject], inserts[lead_inject:]
            tokens = lead.split(' ')
            size = len(tokens) + lead_inject
            chosen = set(inject_rng.sample(range(size), lead_inject))
            pieces, cursor = [], -1
            token_iter, head_iter = iter(tokens), iter(head)
            for slot in range(size):
                if slot in chosen:
                    insert = next(head_iter)
                    pieces.append(insert['text'])
                    cursor += 1
                    insert['start'] = cursor
                    cursor += len(insert['text'])
                    insert['end'] = cursor
                else:
                    token = next(token_iter)
                    pieces.append(token)
                    cursor += 1 + len(token)
            for insert in rest:
                pieces.append(insert['text'])
                cursor += 1
                insert['start'] = cursor
                cursor += len(insert['text'])
                insert['end'] = cursor
            config_ends = [inserts[2 * i + 1]['end']
                           for i in range(len(config_ends))]
        line = ' '.join(pieces)
        body_bytes = len(line.encode('utf-8'))
        if body_bytes > max_bytes:
            raise ValueError(f'line {position}: lead-in plus the full set alone '
                             f'is {body_bytes} bytes > max_bytes ({max_bytes})')
        used, held = [], []
        while len(line.encode('utf-8')) < min_bytes:
            if not deck:
                raise ValueError(f'line {position}: carriers exhausted below '
                                 f'min_bytes ({min_bytes}); extend the carrier list')
            index = deck.popleft()
            candidate = f'{line} {carriers[index]}'
            if len(candidate.encode('utf-8')) <= max_bytes:
                line = candidate
                used.append(index)
            else:
                held.append(index)
        for index in reversed(held):
            deck.appendleft(index)
        lines.append(line)
        plan.append({'line': position, 'lead_in_index': lead_index,
                     'lead_in': lead, 'lead_inject': lead_inject,
                     'pair_order': order, 'inserts': inserts,
                     'config_ends': config_ends, 'carrier_indices': used,
                     'bytes': len(line.encode('utf-8'))})
    return lines, plan


# --- carrier statistics ----------------------------------------------------

def word_entropy(text):
    """Shannon entropy of the word-unigram distribution, bits per word.

    The findings-005 H_word measure: the drill carrier harvest sits at
    ~2-3 bits/word; prose sits far above it.
    """
    tokens = WORD.findall(text.lower())
    if not tokens:
        return 0.0
    total = len(tokens)
    return -sum((count / total) * math.log2(count / total)
                for count in Counter(tokens).values())


def carrier_stats(lines, baseline_lines=None):
    """Mean sentence length + H_word, optionally against a goop baseline.

    The delta vs the goop baseline (the pinned v13 control text) is the
    stealth check: the drill register must not stand out from the goop
    stream it hides inside. (The insert-stripped carrier_only field died
    with the paren audit stack, 2026-10-15.)
    """
    stats = {'mean_words_per_line':
             sum(len(WORD.findall(line.lower())) for line in lines) / len(lines),
             'entropy_bits_per_word': word_entropy('\n'.join(lines))}
    if baseline_lines is not None:
        baseline = word_entropy('\n'.join(baseline_lines))
        stats['goop_baseline_entropy_bits_per_word'] = baseline
        stats['entropy_delta_vs_goop_baseline'] = (
            stats['entropy_bits_per_word'] - baseline)
    return stats
