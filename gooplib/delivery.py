"""Address-anchored delivery measurement, CONTENT layer only.

Port of the corrected instrument in bramble
eval/native/aftermath/MEASUREMENT_REVIEW.md (section 0-1): per occupied
manifest slot, delivery is a CONTENT row starting ``<va> `` whose remainder
— with at most one leading quote stripped (v13-m2/v14 rows are quoted) —
starts with the payload line's 24-char prefix.

Prefix hits are not slot counts. There is deliberately NO prefix-substring
metric here (MEASUREMENT_REVIEW bug 1).
"""


def row_delivers(row, va, prefix):
    """True when one CONTENT row delivers the slot at ``va``."""
    if not row.startswith(va + ' '):
        return False
    body = row[len(va) + 1:]
    if body.startswith("'"):  # quote-tolerant: at most one surrounding quote
        body = body[1:]
    return body.startswith(prefix)


def measure_delivery(events, lines, slots, dose):
    """Ascending occupied slot indices with an address-anchored CONTENT row.

    ``lines`` are the frozen payload lines (bytes); ``slots`` the manifest
    slot table; only indices < dose are occupied and ever measured.
    """
    delivered = []
    for index in range(dose):
        va = slots[str(index)]['va']
        prefix = lines[index][:24].decode('utf-8', errors='replace')
        if any(row_delivers(row, va, prefix)
               for event in events for row in event.split('\n')):
            delivered.append(index)
    return delivered


def term_visibility(events, terms):
    """Per-term CONTENT visibility. Echo can never reach this function."""
    return {term: any(term in event for event in events) for term in terms}
