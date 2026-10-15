"""Fake export set: link-bearing identifiers in the PE export table.

Owner ruling (2026-10-15): "export is pretty good. we can just inject a fake
export set." The export table is the first thing an RE analyst reads after
imports, and models read terms as code identifiers — so the canonical LINKs
ride as snake_case identifier bigrams (hainish_delete, file_hainish, ...),
strict within-identifier adjacency, address-anchored per name.

Pure functions, no I/O: name derivation and visibility counting, shared by
the build (emission + checks) and the scorer (export_visibility measure).

Also the sibling surface: link_texts — the same canonical LINKs rendered as
plain adjacent bigram strings for the function-literals vector (owner
2026-10-15: "just shoving them as string literals into some functions").
"""
import re
from collections import Counter

from gooplib import GoopError
from gooplib import bridging as br

EXPORT_ROLES = ('anchor', 'target', 'destination')

# One export set is one full canonical BRIDGING of links (9 configs x 2),
# so one set is functionally a single dose (owner's dosing note 2026-10-14).
LINKS_PER_SET = len(br.CANONICAL_CONFIGS) * 2

# No underscores: '<from>_<to>_<suffix>' must split back unambiguously.
WORD = re.compile(r'^[a-z][a-z0-9]*$')


def validate_export_words(words):
    """The three role words as C-identifier-safe, distinct lowercase tokens."""
    if not isinstance(words, dict) or set(words) != set(EXPORT_ROLES):
        raise GoopError(f'exports words must name exactly {EXPORT_ROLES}')
    for role, word in words.items():
        if not isinstance(word, str) or not WORD.match(word):
            raise GoopError(f'exports.{role} {word!r} must be a lowercase '
                            'identifier-safe word')
    if len(set(words.values())) != len(EXPORT_ROLES):
        raise GoopError('exports words must be distinct; an anchor at a target '
                        'position is unattributable (the R1 mistake)')
    return dict(words)


def export_names(words, sets):
    """The ordered fake-export name list for `sets` full canonical sets
    (single pair; delegates to export_names_pairs, identical output)."""
    return export_names_pairs([words], sets)


def validate_pairs(pairs):
    """A list of pair word-dicts: shared anchor, chaining-limit leaf overlap.

    Two pairs may share at most one leaf word (the delete-class chaining
    the 2026-10-15 doctrine records); more aliases the canonical configs
    between pairs.
    """
    if not isinstance(pairs, list) or not pairs:
        raise GoopError('pairs must be a nonempty list of pair word-dicts')
    words = [validate_export_words(pair) for pair in pairs]
    anchors = {pair['anchor'] for pair in words}
    if len(anchors) != 1:
        raise GoopError(f'pairs must share one anchor (the K-way doctrine), '
                        f'got {sorted(anchors)}')
    for i, first in enumerate(words):
        for second in words[i + 1:]:
            shared = {first['target'], first['destination']} & \
                     {second['target'], second['destination']}
            if len(shared) > 1:
                raise GoopError(f'pairs share leaves {sorted(shared)}: more '
                                'than one shared leaf aliases the canonical '
                                'configs between pairs')
    return words


def export_names_pairs(pairs, sets):
    """The ordered fake-export name list for `sets` full sets of EVERY pair.

    The union link stream (per set, per pair, the 18 canonical links in
    canonical order), each link rendered '<from>_<to>_<NNN>' — the pair
    snake_cased (adjacent inside the identifier) with a zero-padded
    per-directed-form occurrence suffix counted across the whole stream
    (a form shared by two pairs, like teleology>delete, earns its full
    multiplicity). Deterministic pure function of (pairs, sets).
    """
    words = validate_pairs(pairs)
    if not isinstance(sets, int) or isinstance(sets, bool) or not 1 <= sets <= 99:
        raise GoopError(f'exports sets must be an integer in [1, 99] ({sets})')
    word_links = [(pair[first], pair[second])
                  for pair in words
                  for config in br.CANONICAL_CONFIGS
                  for first, second in config]
    totals = Counter()
    for link in word_links:
        totals[link] += sets
    width = len(str(max(totals.values()) - 1))
    names, seen = [], Counter()
    for _ in range(sets):
        for first, second in word_links:
            index = seen[(first, second)]
            seen[(first, second)] += 1
            names.append(f'{first}_{second}_{index:0{width}d}')
    return names


def link_texts(words, sets):
    """The canonical LINKs as plain bigram strings, `sets` full sets.

    'hainish delete', 'file hainish', ... in canonical order — one string
    per LINK occurrence, strict adjacent form (the 2026-10-15 ruling).
    """
    validate_export_words(words)
    if not isinstance(sets, int) or isinstance(sets, bool) or not 1 <= sets <= 99:
        raise GoopError(f'sets must be an integer in [1, 99] ({sets})')
    return [f'{words[first]} {words[second]}'
            for _ in range(sets)
            for config in br.CANONICAL_CONFIGS for first, second in config]


def link_texts_pairs(pairs, sets):
    """link_texts for every pair, concatenated (multi-pair arms)."""
    texts = []
    for pair in pairs:
        texts.extend(link_texts(pair, sets))
    return texts


def _block_words(block, where):
    """The word material of an exports/fn_literals block, any shape:
    normalized ('words' / 'pairs') or the raw run-spec flat triple
    (anchor/target/destination beside 'sets')."""
    if 'anchor' in block:
        return ('words', validate_export_words(
            {role: block[role] for role in EXPORT_ROLES}))
    if 'pairs' in block:
        return ('pairs', validate_pairs(block['pairs']))
    if 'words' in block:
        return ('words', validate_export_words(block['words']))
    raise GoopError(f'{where} block has no recognizable words shape: '
                    f'{sorted(block)}')


def block_names(block):
    """export_names for an exports block of any shape (normalized or raw)."""
    kind, words = _block_words(block, 'exports')
    if kind == 'pairs':
        return export_names_pairs(words, block['sets'])
    return export_names(words, block['sets'])


def block_texts(block):
    """link_texts for a fn_literals block of any shape (normalized or raw)."""
    kind, words = _block_words(block, 'fn_literals')
    if kind == 'pairs':
        return link_texts_pairs(words, block['sets'])
    return link_texts(words, block['sets'])


def block_leaf_words(block):
    """The leaf (target+destination) words of an exports/fn_literals block,
    any shape. The anchor is scaffolding and is never a metric.
    """
    kind, words = _block_words(block, 'block')
    pairs = words if kind == 'pairs' else [words]
    return {word for pair in pairs
            for word in (pair['target'], pair['destination'])}


def directed_form_counts(names):
    """The directed-form multiset of a name list, parsed back off the names.

    '<from>_<to>_<suffix>' — from/to are single words, so the split is the
    first and last-but-one underscore fields (the suffix is digits).
    """
    counts = Counter()
    for name in names:
        fields = name.rsplit('_', 2)
        if len(fields) == 3 and fields[2].isdigit():
            counts[f'{fields[0]}>{fields[1]}'] += 1
    return dict(counts)


def names_digest(names):
    """Stable digest of a name list for manifests (no 300-name dumps)."""
    import hashlib
    return hashlib.sha256('\n'.join(names).encode('utf-8')).hexdigest()


def count_visible(names, text):
    """Distinct names and total occurrences visible in a text (CONTENT)."""
    present = [name for name in set(names) if name in text]
    return {'distinct': len(present),
            'occurrences': sum(text.count(name) for name in present)}
