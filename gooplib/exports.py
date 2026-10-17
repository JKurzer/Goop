"""Link-text and word machinery for the fn_literals vector + visibility
counting. Pure functions, no I/O, shared by the build (emission + checks)
and the scorer (visibility measures).

The fake-export-table arm is DELETED (owner ruling 2026-10-15, verbatim:
"I don't care about over priming. remove the existing exports, go ahead
and build the cargo strings."). Five consecutive completed cells measured
export_visibility 0 — the surface never landed. export_names,
export_names_pairs, block_names, directed_form_counts and LINKS_PER_SET
went with it; historical runs' manifests keep their records.

Surviving: link_texts — the canonical LINKs rendered as plain adjacent
bigram strings for the function-literals vector (owner 2026-10-15: "just
shoving them as string literals into some functions").
"""
import re
from collections import Counter

from gooplib import GoopError
from gooplib import bridging as br

EXPORT_ROLES = ('anchor', 'target', 'destination')

# No underscores: identifier-safe role words split back unambiguously.
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


def bundled_link_texts(words, sets, links_per_literal):
    """Keep whole canonical two-LINK configs together in each C string.

    Four LINKs are preferred; an odd final config has two. Never carry a
    config into a different literal, set, or pair. Cap each string so a
    scanner's address/ANSI decorations fit the 256-character output row.
    """
    links = link_texts(words, sets)
    if links_per_literal not in (2, 4) or isinstance(links_per_literal, bool):
        raise GoopError('fn_literals.links_per_literal must be 2 or 4')
    texts = []
    links_per_set = len(br.CANONICAL_CONFIGS) * 2
    for set_start in range(0, len(links), links_per_set):
        one_set = links[set_start:set_start + links_per_set]
        for start in range(0, len(one_set), links_per_literal):
            text = ' | '.join(one_set[start:start + links_per_literal])
            if len(text.encode('ascii')) > 120:
                raise GoopError('fn_literals grouped string exceeds 120 bytes')
            texts.append(text)
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


def block_texts(block):
    """Function-literal strings in canonical order; grouping is opt-in."""
    kind, words = _block_words(block, 'fn_literals')
    if 'links_per_literal' in block:
        pairs = words if kind == 'pairs' else [words]
        return [text for pair in pairs
                for text in bundled_link_texts(pair, block['sets'],
                                               block['links_per_literal'])]
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


def names_digest(names):
    """Stable digest of a name list for manifests (no 300-name dumps)."""
    import hashlib
    return hashlib.sha256('\n'.join(names).encode('utf-8')).hexdigest()


def count_visible(names, text):
    """Distinct names and total occurrences visible in a text (CONTENT)."""
    present = [name for name in set(names) if name in text]
    return {'distinct': len(present),
            'occurrences': sum(text.count(name) for name in present)}
