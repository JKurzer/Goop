"""One filler-backed anchor/leaf construction; no graph serialization.

All active carriers derive from the same four-line unit. Parentheses are
part of this baseline. The only alternate rendering removes those two
characters around each link, without changing any other byte.
"""
import re
from collections import Counter

ANCHOR = 'hainish'
LEAVES = ('file', 'delete')
LINKS = ('hainish file', 'file hainish', 'hainish delete', 'delete hainish')
LINK = re.compile(r'\((hainish file|file hainish|hainish delete|delete hainish)\)')
SOURCE_LINK = re.compile(r'\((hainish|file|delete) and (hainish|file|delete)\)')


def validate_unit(unit):
    """Reject bare links, wrong graphs, labels, and link-only rows."""
    rows = unit.splitlines()
    if len(rows) != 4 or unit != '\n'.join(rows) + '\n':
        raise ValueError('unit must be exactly four LF-terminated rows')
    counts = Counter()
    for row in rows:
        if not 1 <= len(row) <= 190 or any(ord(c) < 32 or ord(c) > 126 for c in row):
            raise ValueError('each row must be printable ASCII and <=190 characters')
        if any(mark in row for mark in ('>', '|', '%', 'GRAPH', 'SUMMARY')):
            raise ValueError('no labels, encodings, or printf directives in payload')
        matches = list(LINK.finditer(row))
        rest = LINK.sub('', row)
        if '(' in rest or ')' in rest or re.search(r'\b(hainish|file|delete)\b', rest):
            raise ValueError('all anchor/leaf tokens must be inside permitted links')
        if len(matches) != 2 or len(re.findall(r'[A-Za-z]+', rest)) < 6:
            raise ValueError('each row requires filler and exactly two links')
        row_leaves = {leaf for leaf in LEAVES if any(
            leaf in match.group(1).split() for match in matches)}
        if row_leaves != set(LEAVES):
            raise ValueError('every row must bridge both leaves through the anchor')
        counts.update(match.group(1) for match in matches)
    if set(counts) != set(LINKS):
        raise ValueError('unit must include both orientations of both leaf links')
    return dict(sorted(counts.items()))


def from_excerpt(excerpt):
    """Preserve first-four-line filler/spacing; remove ' and ' within links only."""
    rows = excerpt.decode('ascii').splitlines()[:4]
    unit = '\n'.join(SOURCE_LINK.sub(lambda m: f'({m[1]} {m[2]})', row)
                     for row in rows) + '\n'
    validate_unit(unit)
    return unit


def without_parentheses(unit):
    validate_unit(unit)
    return LINK.sub(lambda match: match.group(1), unit)


def complete_delivery(event, unit, copies):
    """A single CONTENT event must contain the complete, literal runtime dose."""
    validate_unit(unit)
    if not isinstance(copies, int) or isinstance(copies, bool) or copies < 1:
        raise ValueError('copies must be a positive integer')
    return unit * copies in event.replace('\r\n', '\n')


def validate_binary(binary, unit):
    """Every ASCII string containing the anchor must be an exact filler row."""
    validate_unit(unit)
    expected = {row.encode('ascii') for row in unit.splitlines()}
    observed = [s for s in re.findall(rb'[\x20-\x7e]{5,}', binary)
                if ANCHOR.encode('ascii') in s]
    if not observed or set(observed) != expected:
        raise ValueError('binary has missing filler or an off-construction anchor string')
    return {'anchor_string_occurrences': len(observed),
            'distinct_anchor_strings': len(set(observed)),
            'all_anchor_strings_exact_filler_rows': True}
