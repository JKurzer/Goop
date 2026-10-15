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
    """The ordered fake-export name list for `sets` full canonical sets.

    Per set, the 18 canonical links in canonical order, each rendered
    '<from>_<to>_<NNN>' — the pair snake_cased (adjacent inside the
    identifier) with a zero-padded per-directed-form occurrence suffix for
    table-wide uniqueness. Deterministic pure function of (words, sets).
    """
    validate_export_words(words)
    if not isinstance(sets, int) or isinstance(sets, bool) or not 1 <= sets <= 99:
        raise GoopError(f'exports sets must be an integer in [1, 99] ({sets})')
    links = [link for config in br.CANONICAL_CONFIGS for link in config]
    totals = Counter()
    for link in links:
        totals[link] += sets
    width = len(str(max(totals.values()) - 1))
    names, seen = [], Counter()
    for _ in range(sets):
        for first, second in links:
            index = seen[(first, second)]
            seen[(first, second)] += 1
            names.append(f'{words[first]}_{words[second]}_{index:0{width}d}')
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
