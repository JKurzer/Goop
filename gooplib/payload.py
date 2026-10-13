"""Pure goop payload composition machinery. No I/O, no module-level state.

Pipeline (all inputs arrive as arguments, loaded from files by the caller):
  1. transform_corpus: corpus frames are relabeled onto the spec vocabulary.
     A hub marker becomes the hub word; rotation markers become vocab words
     via a carried rotation (marker position carries across frames); ranked
     corpus content words map onto the vocab pool; identity words stay.
  2. compose: whole-frame seeded sampling with a byte-safe fit (the budget
     check applies to the first frame too — no oversize escape hatch).
     Parentheses are stripped AFTER the fit. An optional per-line visibility
     predicate redraws failing lines on the same RNG stream.
  3. graft: additive 'term and neighbor.' bridge sentences. Optionally one
     bridge per term is prepended inside the visible line range (terminal
     period cannot bridge into the line's first word); the rest are appended
     to the roomiest later lines with a dangling-'and' guard.
  4. trigram_sets: additive 'a and b.' / 'b and c.' sentence pairs with a
     rare middle word b, placed by a dedicated seeded stream (the compose
     stream is untouched) under the same byte budget and junction guard.
"""
import hashlib
import random
import re
from collections import Counter

MAX_SAMPLE_PICKS = 500        # inner fitter attempts per line draw
MAX_LINE_ATTEMPTS = 2000      # predicate redraws per line before giving up

# Lookahead retains both edges in "a and b and c". No punctuation bridges.
PAIR = re.compile(r'(?=\b([a-z]+) and ([a-z]+)\b)')
WORD = re.compile(r'\b[a-z]+\b')


# --- frame transform -------------------------------------------------------

def token_parts(token):
    """Split a token into (parenthesis prefix, core word, punctuation suffix)."""
    left = token.lstrip('(')
    prefix = token[:len(token) - len(left)]
    core = left.rstrip(').,;?!')
    return prefix, core, left[len(core):]


def build_remap(vocab, corpus_words, identity_words):
    """Ranked corpus content words -> vocab pool, in list order.

    Identity words map to themselves but still consume their pool slot,
    matching the historical rank map exactly.
    """
    remap = {word: word for word in identity_words}
    pool = [word for word in vocab if word not in remap]
    if not pool:
        raise ValueError('vocab minus identity words is empty; nothing to map onto')
    for index, word in enumerate(corpus_words):
        if word not in remap:
            remap[word] = pool[index % len(pool)]
    return remap


def transform_frame(line, offset, hub, vocab, remap, hub_marker, rotation_markers):
    """Relabel one corpus line; offset is the carried marker position."""
    tokens, consumed = [], 0
    stride = len(rotation_markers)
    for token in line.split(' '):
        prefix, core, suffix = token_parts(token)
        if core == hub_marker:
            repl = hub
        elif core in rotation_markers:
            position = (stride * (offset + consumed)
                        + rotation_markers.index(core)) % len(vocab)
            repl = vocab[position]
            consumed += 1
        else:
            repl = remap.get(core)
        tokens.append(token if repl is None else prefix + repl + suffix)
    return ' '.join(tokens), consumed


def transform_corpus(corpus_lines, hub, vocab, remap, hub_marker,
                     rotation_markers, carry=True):
    """Transform every corpus line; returns (frames, per-frame start offsets)."""
    offset, frames, offsets = 0, [], []
    for line in corpus_lines:
        start = offset if carry else 0
        frame, consumed = transform_frame(line, start, hub, vocab, remap,
                                          hub_marker, rotation_markers)
        frames.append(frame)
        offsets.append(start)
        offset += consumed
    return frames, offsets


def strip_parentheses(text):
    return text.replace('(', '').replace(')', '')


# --- seeded composition ----------------------------------------------------

def compose(frames, seed, count, budget, predicate=None,
            max_line_attempts=MAX_LINE_ATTEMPTS):
    """Sample `count` lines of whole frames under `budget` bytes each.

    Local RNG, whole frames only, conservative +1 separator accounting kept
    even on the first frame, parentheses stripped after the fit. A failing
    predicate redraws the whole line on the same RNG stream.
    Returns (lines, frame indices per line, redraw count).
    """
    if count < 1 or budget < 1 or not frames or any(not frame for frame in frames):
        raise ValueError('positive count/budget and nonempty frames required')
    sizes = [len(frame.encode('utf-8')) + 1 for frame in frames]
    if not any(size <= budget for size in sizes):
        raise ValueError('no whole frame fits the byte budget')
    rng = random.Random(seed)
    lines, traces, redraws = [], [], 0
    for _ in range(count):
        for attempt in range(max_line_attempts):
            picks = list(range(len(frames)))
            rng.shuffle(picks)
            chosen, used = [], 0
            for _ in range(MAX_SAMPLE_PICKS):
                if used >= budget:
                    break
                index = picks[rng.randrange(len(picks))]
                if used + sizes[index] <= budget:
                    chosen.append(index)
                    used += sizes[index]
            if not chosen:
                raise ValueError('no sampled frame fits; refusing an empty line')
            line = strip_parentheses(' '.join(frames[i] for i in chosen))
            if predicate is None or predicate(line):
                lines.append(line)
                traces.append(chosen)
                redraws += attempt
                break
        else:
            raise ValueError(f'predicate unsatisfiable after {max_line_attempts} attempts')
    return lines, traces, redraws


# --- visibility predicate --------------------------------------------------

def make_predicate(hub, filter_terms, visibility):
    """Per-line visibility predicate from a visibility spec, or None.

    visibility: {prefix_chars, require_hub_in_prefix, require_filter_in_prefix}.
    Substring semantics on the lowercased prefix, matching the historical
    analyst-filter model.
    """
    if visibility is None:
        return None
    prefix = visibility['prefix_chars']
    need_hub = visibility['require_hub_in_prefix']
    need_filter = visibility['require_filter_in_prefix']
    if need_filter and not filter_terms:
        raise ValueError('require_filter_in_prefix with an empty filter_terms list')

    def predicate(line):
        head = line[:prefix].lower()
        if need_hub and hub not in head:
            return False
        if need_filter and not any(term in head for term in filter_terms):
            return False
        return True

    return predicate


def predicate_margin(line, hub, filter_terms, prefix):
    """Chars of window slack after the predicate's last needed token.

    The predicate needs the hub and any ONE filter token, so the last needed
    position is max(hub end, earliest filter end).
    """
    head = line[:prefix].lower()
    hub_end = head.find(hub) + len(hub)
    filter_end = min((head.find(term) + len(term)
                      for term in filter_terms if term in head), default=0)
    return prefix - max(hub_end, filter_end)


# --- additive term graft ---------------------------------------------------

def bridge_sentence(term, neighbor):
    return f'{term} and {neighbor}.'


def visible_neighbor(neighbors, filter_terms):
    """Planned neighbor carrying a filter token (substring semantics), else first."""
    for word in neighbors:
        if any(token in word for token in filter_terms):
            return word
    return neighbors[0]


def place_visible_bridges(lines, terms, hub, filter_terms, visibility,
                          visible_range, budget, predicate):
    """Prepend one bridge per term to a distinct line inside visible_range.

    Deterministic: the pick is maximum post-prepend predicate margin, ties to
    the lowest line index. A prepend shifts prefix content right but removes
    none of it, and the bridge's terminal period cannot form a conjunction
    with the line's first word, so every pre-existing edge survives verbatim.
    """
    start, end = visible_range
    if not 0 <= start < end <= len(lines):
        raise ValueError(f'visible_line_range {visible_range} outside 0..{len(lines)}')
    prefix = visibility['prefix_chars']
    out = list(lines)
    room = [budget - len(line.encode('utf-8')) for line in out]
    used, placement = set(), {}
    for term, neighbors in terms:
        neighbor = visible_neighbor(neighbors, filter_terms)
        text = bridge_sentence(term, neighbor)
        cost = len(text.encode('utf-8')) + 1
        eligible = [i for i in range(start, end) if i not in used and room[i] >= cost
                    and (predicate is None or predicate(text + ' ' + out[i]))]
        if not eligible:
            raise ValueError(f'no line in {start}-{end - 1} can host the visible bridge for {term}')
        target = min(eligible, key=lambda i: (
            -predicate_margin(text + ' ' + out[i], hub, filter_terms, prefix), i))
        out[target] = text + ' ' + out[target]
        room[target] -= cost
        used.add(target)
        placement[term] = {'neighbor': neighbor, 'line': target, 'offset': 0,
                           'text': text}
    return out, placement


def place_remaining_bridges(lines, terms, visible, append_start, budget):
    """Append each non-visible bridge to the roomiest line at >= append_start.

    Greedy max-headroom, ties to the lowest index, plus a dangling junction
    guard: a line whose last token is 'and' is never an append target, so no
    unplanned 'x and term' edge can be created. Lines only ever grow by
    period-terminated sentences, so the guard holds inductively.
    """
    out = list(lines)
    room = [budget - len(line.encode('utf-8')) for line in out]
    placement = {}
    for term, neighbors in terms:
        for neighbor in neighbors:
            if term in visible and neighbor == visible[term]['neighbor']:
                continue
            text = bridge_sentence(term, neighbor)
            cost = len(text.encode('utf-8')) + 1
            fits = [i for i in range(append_start, len(out))
                    if room[i] >= cost and out[i].split(' ')[-1] != 'and']
            if not fits:
                raise ValueError(f'no line at {append_start}+ fits graft sentence {text!r}')
            target = min(fits, key=lambda i: (-room[i], i))
            out[target] += ' ' + text
            room[target] -= cost
            placement.setdefault(term, []).append(
                {'neighbor': neighbor, 'line': target, 'offset': None, 'text': text})
    return out, placement


def graft(lines, incorrect_terms, hub, filter_terms, visibility, graft_spec,
          budget, predicate):
    """Additive term bridges per spec. Returns (lines, placement)."""
    terms = [(entry['term'], list(entry['neighbors'])) for entry in incorrect_terms]
    if not terms:
        return list(lines), {}
    if len({term for term, _ in terms}) != len(terms):
        raise ValueError('duplicate terms in incorrect_terms')
    if any(not neighbors for _, neighbors in terms):
        raise ValueError('every incorrect term needs at least one neighbor')
    if graft_spec and graft_spec['bridges_visible_in_prefix']:
        if visibility is None:
            raise ValueError('visible graft bridges require a visibility spec')
        out, visible = place_visible_bridges(
            lines, terms, hub, filter_terms, visibility,
            graft_spec['visible_line_range'], budget, predicate)
        append_start = graft_spec['visible_line_range'][1]
    else:
        out, visible = list(lines), {}
        append_start = 0
    out, rest = place_remaining_bridges(out, terms, visible, append_start, budget)
    placement = {term: ([visible[term]] if term in visible else []) + rest.get(term, [])
                 for term, _ in terms}
    return out, placement


# --- additive trigram sets (rare middle word) ------------------------------

def place_trigram_sets(lines, trigram_sets, budget, seed_text):
    """Seed-driven additive placement of 'a and b.' / 'b and c.' sentences.

    Each set plans `occurrences` copies of both edge sentences (a [min, max]
    range resolves on the same stream, in set order, before that set's
    placements). Every sentence is appended to a line drawn from a dedicated
    RNG stream (seed_text) among lines with byte room whose last token is not
    'and' — the same dangling-junction guard as the graft. Appends never
    touch the visible prefix, so the visibility predicate still holds on
    every line, and existing text is never modified, so every pre-existing
    conjunction edge survives verbatim. Returns (lines, per-set reports).
    """
    if not trigram_sets:
        return list(lines), []
    rng = random.Random(seed_text)
    out = list(lines)
    room = [budget - len(line.encode('utf-8')) for line in out]
    reports = []
    for entry in trigram_sets:
        a, b, c = entry['a'], entry['b'], entry['c']
        occurrences = entry['occurrences']
        if isinstance(occurrences, list):
            low, high = occurrences
            occurrences = low + rng.randrange(high - low + 1)
        sentences = [text for _ in range(occurrences)
                     for text in (bridge_sentence(a, b), bridge_sentence(b, c))]
        placement = []
        for text in sentences:
            cost = len(text.encode('utf-8')) + 1
            fits = [i for i in range(len(out))
                    if room[i] >= cost and out[i].split(' ')[-1] != 'and']
            if not fits:
                raise ValueError(f'no line fits trigram sentence {text!r}')
            target = fits[rng.randrange(len(fits))]
            out[target] += ' ' + text
            room[target] -= cost
            placement.append({'text': text, 'line': target})
        reports.append({'a': a, 'b': b, 'c': c,
                        'planned_occurrences': occurrences,
                        'sentences': placement})
    return out, reports


# --- graph metrics (construction accounting, not efficacy) -----------------

def conjunction_edges(text, nodes, limit=None):
    """Exact lowercase conjunctions with complete visible endpoints.

    Match against the original text before applying the character cap: a
    clipped 'seeds' must not become a fictitious 'seed' endpoint.
    """
    return [(match[1], match[2]) for match in PAIR.finditer(text)
            if match[1] in nodes and match[2] in nodes
            and (limit is None or match.end(2) <= limit)]


def hub_neighbors(lines, hub, vocab, limit=None):
    """Sorted distinct conjunction neighbors of the hub across lines."""
    nodes = {hub, *vocab}
    neighbors = set()
    for line in lines:
        for first, second in conjunction_edges(line, nodes, limit):
            if first == hub and second != hub:
                neighbors.add(second)
            elif second == hub and first != hub:
                neighbors.add(first)
    return sorted(neighbors)


def term_adjacency(lines, terms, vocab, hub=None):
    """Conjunction neighbors of grafted terms on the final text.

    Same regex and complete-endpoint rule as conjunction_edges; the endpoint
    vocabulary is extended by the grafted terms only.
    """
    nodes = set(vocab) | set(terms) | ({hub} if hub else set())
    neighbors = {term: set() for term in terms}
    occurrences = Counter()
    for line in lines:
        for first, second in conjunction_edges(line, nodes):
            for term, other in ((first, second), (second, first)):
                if term in neighbors:
                    neighbors[term].add(other)
                    occurrences[term] += 1
    return {term: {'neighbors': sorted(neighbors[term]),
                   'neighbor_count': len(neighbors[term]),
                   'edge_occurrences': occurrences[term]} for term in terms}


def measure_trigram(lines, a, b, c):
    """Occurrences of a trigram set's two edge forms across lines.

    Same edge regex and complete-endpoint rule as conjunction_edges; only
    the exact 'a and b' / 'b and c' forms are counted.
    """
    nodes = {a, b, c}
    counts = Counter()
    for line in lines:
        for first, second in conjunction_edges(line, nodes):
            counts[first, second] += 1
    return {f'{a} and {b}': counts[a, b], f'{b} and {c}': counts[b, c]}


# --- encoding --------------------------------------------------------------

def encode_payload(lines):
    return ('\n'.join(lines) + '\n').encode('utf-8')


def sha256(data):
    return hashlib.sha256(data).hexdigest()
