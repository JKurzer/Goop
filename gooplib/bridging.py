"""Conformant trigram-bridging composition + measurement. Pure functions, no I/O.

The first doctrine-conformant payload mode (goop/docs/wou-construction-doctrine.md):

- ANCHOR is a rare weak-embedding token (hainish; gap P1), never remapped into
  a common word (the R1 break), never rotated.
- TARGET and DESTINATION are one consistent association pair (delete/file;
  gap P2). No rotation, no other hubs.
- One full BRIDGING: the 9 canonical ordered LINK-pairs (docs/
  TRIGRAM_BRIDGING.md per the owner errata below), each planted `doses`
  times (9*doses LINK-pairs, 18*doses LINKs; gaps P3/P4).
- LINKs render as parenthesized inserts in the WoU drill format (gap P5):
  '(x y)' adjacent and '(x and y)' conjunction, two inserts woven into one
  low-perplexity carrier sentence per LINK-pair (tainish-drill register;
  gap P6). Parens are KEPT — the legacy compose strips them (the R5 break);
  this mode never does.

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
[min_line_bytes, max_line_bytes]. Dose integrity is a per-line property: any
single delivered slot window still holds a filter echo and complete
LINK-pairs (docs/megaline.md).
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
PAREN_GROUP = re.compile(r'\(([^()]*)\)')


# --- rendering -------------------------------------------------------------

def config_label(config):
    """Canonical name of one ordered LINK-pair, e.g. 'LINK(anchor,target) LINK(anchor,destination)'."""
    return ' '.join(f'LINK({first},{second})' for first, second in config)


def link_text(link, words, form):
    """One LINK as a paren insert: '(hainish file)' or '(hainish and file)'."""
    first, second = (words[role] for role in link)
    if form == 'conjunction':
        return f'({first} and {second})'
    return f'({first} {second})'


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

def compose_bridging(carriers, words, doses, forms, line_count, seed):
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
        first = link_text(config[0], words, form_first)
        second = link_text(config[1], words, form_second)
        lines.append(weave_inserts(carrier, first, second, rng))
        plan.append({'line': position, 'config_index': position // doses,
                     'config': config_label(config),
                     'carrier_index': deal[position],
                     'forms': [form_first, form_second],
                     'inserts': [first, second]})
    return lines, plan


# --- megaline composition --------------------------------------------------

def compose_megalines(carriers, lead_ins, words, doses, forms, line_count,
                      min_bytes, max_bytes, seed):
    """One complete BRIDGING per line, the set packed toward the front.

    The megaline trick: every line independently carries the full 9-config
    canonical set at `doses`, so any single delivered slot window still
    holds complete dose material. Layout per line:

        <lead-in> <insert> ... <insert (18*doses)> <carrier prose ...>

    The lead-in is a short drill sentence (it owns the filter echo; the
    spec validates that). Inserts follow in canonical config order; dealt
    carriers then fill the line into [min_bytes, max_bytes]. Lead-ins and
    carriers are dealt without replacement from seeded shuffles; a carrier
    that would overshoot max_bytes is held back for later lines. The whole
    artifact is a pure function of the arguments. Returns (lines, plan)
    with one plan row per line.
    """
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
    rng = random.Random(seed)
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
        for dose in range(doses):
            for config_index, config in enumerate(CANONICAL_CONFIGS):
                for link in config:
                    form = rng.choice(forms)
                    text = link_text(link, words, form)
                    cursor += 1  # the separating space
                    start = cursor
                    cursor += len(text)
                    pieces.append(text)
                    inserts.append({'dose': dose, 'config_index': config_index,
                                    'link': list(link), 'form': form,
                                    'text': text, 'start': start,
                                    'end': cursor})
                config_ends.append(cursor)
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
                     'lead_in': lead, 'inserts': inserts,
                     'config_ends': config_ends, 'carrier_indices': used,
                     'bytes': len(line.encode('utf-8'))})
    return lines, plan


# --- parsing / integrity ---------------------------------------------------

def paren_groups(line):
    """Token lists of each flat '( ... )' group, in order."""
    return [match.group(1).split() for match in PAREN_GROUP.finditer(line)]


def strip_groups(line):
    """The line with every flat paren group blanked out (carrier residue)."""
    return PAREN_GROUP.sub(' ', line)


def paren_integrity(lines):
    """Balanced, flat, nonempty paren groups on every line."""
    violations = []
    for number, line in enumerate(lines):
        groups = paren_groups(line)
        if line.count('(') != line.count(')') or line.count('(') != len(groups):
            violations.append({'line': number, 'error': 'unbalanced or nested parens'})
        if any(not group for group in groups):
            violations.append({'line': number, 'error': 'empty group'})
    return {'ok': not violations, 'violations': violations}


def parse_link(group, roles_by_word):
    """A paren group as a directed LINK of roles, or None.

    '(x y)' adjacent and '(x and y)' conjunction are the only LINK forms.
    """
    if len(group) == 2:
        first, second = group
    elif len(group) == 3 and group[1] == 'and':
        first, second = group[0], group[2]
    else:
        return None
    if first in roles_by_word and second in roles_by_word:
        return (roles_by_word[first], roles_by_word[second])
    return None


# --- measurement -----------------------------------------------------------

def measure_bridging(lines, words):
    """Per-config counts, directed-form counts, LINK totals, role-word totals.

    Counts are parsed from the final text (not the plan): consecutive parsed
    LINKs within a line pair into ordered configs (a classic bridging line's
    two inserts form its one config; a megaline's eighteen form its nine),
    and each insert is one directed LINK. An odd trailing LINK never pairs.
    Word totals count whole-word occurrences anywhere in the text, so a
    stray role word outside the inserts would show up here (and in
    role_audit).
    """
    roles_by_word = {word: role for role, word in words.items()}
    per_config, directed = Counter(), Counter()
    links = 0
    for line in lines:
        parsed = [link for link in
                  (parse_link(group, roles_by_word) for group in paren_groups(line))
                  if link is not None]
        links += len(parsed)
        for first, second in parsed:
            directed[f'{first}>{second}'] += 1
        for i in range(0, len(parsed) - 1, 2):
            per_config[config_label((parsed[i], parsed[i + 1]))] += 1
    forms = {form: directed[form] for form in CANONICAL_DIRECTED_FORMS}
    forms.update({form: count for form, count in sorted(directed.items())
                  if form not in forms})
    tokens = Counter(WORD.findall('\n'.join(lines).lower()))
    return {'per_config': {config_label(config): per_config[config_label(config)]
                           for config in CANONICAL_CONFIGS},
            'pair_total': sum(per_config.values()),
            'link_total': links,
            'directed_forms': forms,
            'word_totals': {words[role]: tokens[words[role]] for role in ROLES}}


def expected_directed_forms(doses):
    """The directed-form multiset of a conformant BRIDGING at `doses`."""
    counts = Counter()
    for config in CANONICAL_CONFIGS:
        for first, second in config:
            counts[f'{first}>{second}'] += doses
    return dict(counts)


def measure_megalines(lines, words, filter_terms, prefix_chars):
    """Per-line dose integrity + window stats, parsed off the final text.

    Consecutive parsed LINKs pair into configs (the same reading as
    measure_bridging). The filter echo is the earliest filter term in the
    lowercased prefix window (substring semantics, the v13 analyst-filter
    model). The set-toward-front count is the canonical configs whose
    complete LINK-pair ends inside the window — measured and reported,
    never a hard fail. Char offsets equal byte offsets: megaline text is
    ascii by spec validation.
    """
    roles_by_word = {word: role for role, word in words.items()}
    canonical = [config_label(config) for config in CANONICAL_CONFIGS]
    rows = []
    for number, line in enumerate(lines):
        parsed = [(link, match.end())
                  for match in PAREN_GROUP.finditer(line)
                  for link in [parse_link(match.group(1).split(), roles_by_word)]
                  if link is not None]
        per_config, in_window = Counter(), 0
        for i in range(0, len(parsed) - 1, 2):
            label = config_label((parsed[i][0], parsed[i + 1][0]))
            per_config[label] += 1
            if parsed[i + 1][1] <= prefix_chars and label in canonical:
                in_window += 1
        head = line[:prefix_chars].lower()
        hits = sorted((head.find(term), term) for term in filter_terms
                      if term in head)
        rows.append({'line': number,
                     'per_config': {label: per_config[label]
                                    for label in canonical},
                     'pair_total': sum(per_config.values()),
                     'link_total': len(parsed),
                     'filter_term': hits[0][1] if hits else None,
                     'filter_char': hits[0][0] if hits else None,
                     'configs_in_window': in_window,
                     'complete_pair_in_window': in_window > 0})
    counts = [row['configs_in_window'] for row in rows]
    return {'per_line': rows,
            'configs_in_window_min': min(counts),
            'configs_in_window_mean': sum(counts) / len(counts),
            'lines_with_filter_echo':
                sum(row['filter_term'] is not None for row in rows),
            'lines_with_complete_pair_in_window':
                sum(row['complete_pair_in_window'] for row in rows)}


def role_audit(lines, words):
    """Every anchor occurrence sits at a bridge position; no role word strays.

    Bridge position: inside a paren group that parses as a LINK whose other
    endpoint is the target or the destination. Role words anywhere outside
    the inserts, unparseable groups, anchor-anchor pairs, and anchorless
    LINKs outside the declared leaf-to-leaf set (CANONICAL_LEAF_LINKS) are
    violations. A declared leaf-to-leaf LINK (destination>target, the errata
    spare) carries no anchor BY DESIGN and is accepted; the mirrored
    (target, destination) form is not declared and is rejected.
    """
    roles_by_word = {word: role for role, word in words.items()}
    anchor = words['anchor']
    violations, occurrences, at_bridge = [], 0, 0
    for number, line in enumerate(lines):
        stray = [token for token in WORD.findall(strip_groups(line).lower())
                 if token in roles_by_word]
        if stray:
            violations.append({'line': number,
                               'error': f'role words outside inserts: {stray}'})
        for group in paren_groups(line):
            link = parse_link(group, roles_by_word)
            endpoints = (group[0], group[-1]) if group else ()
            occurrences += endpoints.count(anchor)
            if link is None:
                violations.append({'line': number,
                                   'error': f'unparseable group: {group}'})
            elif link == ('anchor', 'anchor'):
                violations.append({'line': number,
                                   'error': 'anchor paired with itself'})
            elif anchor in endpoints:
                at_bridge += 1  # parse_link guarantees the pair is two roles
            elif link not in CANONICAL_LEAF_LINKS:
                violations.append({'line': number,
                                   'error': f'undeclared anchorless link: '
                                            f'{link[0]}>{link[1]}'})
    return {'ok': not violations, 'violations': violations,
            'anchor_occurrences': occurrences, 'anchor_at_bridge': at_bridge}


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

    `carrier_only` strips the inserts, so the register is measured without
    the planted vocabulary. The delta vs the goop baseline (the pinned v13
    control text) is the stealth check: the drill register must not stand
    out from the goop stream it hides inside.
    """
    stats = {'mean_words_per_line':
             sum(len(WORD.findall(line.lower())) for line in lines) / len(lines),
             'entropy_bits_per_word': word_entropy('\n'.join(lines)),
             'carrier_only_entropy_bits_per_word':
             word_entropy('\n'.join(strip_groups(line) for line in lines))}
    if baseline_lines is not None:
        baseline = word_entropy('\n'.join(baseline_lines))
        stats['goop_baseline_entropy_bits_per_word'] = baseline
        stats['entropy_delta_vs_goop_baseline'] = (
            stats['entropy_bits_per_word'] - baseline)
    return stats
