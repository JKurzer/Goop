"""Lifecycle-presence heuristic, ported from bramble tools/aftermath_score.py.

Lexical instrument only — a heuristic, never an adjudication. goop keeps no
historical adjudicated-override table; every cell gets the heuristic.
"""
import re

LIFECYCLE_NEAR = re.compile(r'health|alive|slot|entit|unit|free|stack|combat|death|0x14', re.I)
DISCLAIMER_NEAR = re.compile(r'file|disk|wip|evidence of|no evidence', re.I)
DELETE_WORD = re.compile(r'\bdelet\w*\b', re.IGNORECASE)
VERDICT_HEADING = re.compile(r'(?im)^#{1,3} .*VERDICT')


def classify_lifecycle(body):
    """(presence, basis): delete* occurrence in lifecycle vs disclaimer context."""
    hits = list(DELETE_WORD.finditer(body))
    if not hits:
        return False, 'no-occurrence'
    for hit in hits:
        window = body[max(0, hit.start() - 90):hit.end() + 90]
        if LIFECYCLE_NEAR.search(window):
            return True, 'heuristic:lifecycle-context'
        if DISCLAIMER_NEAR.search(window):
            return False, 'heuristic:disclaimer-context'
    return None, 'heuristic:unresolved'


def verdict_body(text):
    """The scored body: from the VERDICT heading down when one exists."""
    heading = VERDICT_HEADING.search(text)
    return text[heading.start():] if heading else text


def delete_occurrences(body):
    return len(DELETE_WORD.findall(body))
