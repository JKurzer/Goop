"""Bounded, lossless plaintext graph rows for shell tool-return delivery.

A graph is delivered only when every numbered row appears whole in one
CONTENT event and reconstructs the pinned canonical value byte-for-byte.
"""
import re

ROW_LIMIT = 190  # leaves room below the shell's 256-character raw-line cutoff
NAMES = ('trigram_sets', 'full_graph', 'full_graph_directed')
ROW = re.compile(r'^GRAPH (trigram_sets|full_graph|full_graph_directed) '
                 r'(\d{2})/(\d{2}): ([a-z> ;|]+)$')


def canonical_from_startup(startup):
    """Extract canonical strings from the pre-existing, unmodified startup line."""
    head = 'STARTUP seed trigram_sets='
    assert startup.startswith(head) and startup.endswith('\n')
    trigram, rest = startup[len(head):-1].split(' full_graph=', 1)
    graph, directed = rest.split(' full_graph_directed=', 1)
    values = dict(zip(NAMES, (trigram, graph, directed)))
    assert all(value and value == value.strip() for value in values.values())
    return values


def frame_graphs(values):
    """Produce individually readable rows; spaces between chunks are restored."""
    if set(values) != set(NAMES):
        raise ValueError('expected exactly the three named graph values')
    rows = []
    for name in NAMES:
        text = values[name]
        words = text.split(' ')
        if not words or any(not re.fullmatch(r'[a-z>;|]+', word)
                            for word in words):
            raise ValueError(f'{name}: graph must have nonempty ASCII tokens')
        budget = ROW_LIMIT - len(f'GRAPH {name} 99/99: ')
        parts = []
        current = ''
        for word in words:
            if len(word) > budget:
                raise ValueError(f'{name}: token exceeds row budget')
            candidate = (current + ' ' if current else '') + word
            if len(candidate) > budget:
                parts.append(current)
                current = word
            else:
                current = candidate
        parts.append(current)
        if len(parts) > 99:
            raise ValueError(f'{name}: too many graph rows')
        rows.extend(f'GRAPH {name} {index:02d}/{len(parts):02d}: {part}'
                    for index, part in enumerate(parts, 1))
    if any(len(row) > ROW_LIMIT for row in rows):
        raise AssertionError('graph framing exceeded raw-line budget')
    return '\n'.join(rows) + '\n'


def graphs_in_content(event):
    """Return complete named values only; duplicate/inconsistent rows fail closed."""
    groups = {name: {} for name in NAMES}
    totals = {name: set() for name in NAMES}
    invalid = set()
    for line in event.splitlines():
        match = ROW.fullmatch(line)
        if not match:
            continue
        name, index, total, part = match.groups()
        index, total = int(index), int(total)
        if index < 1 or total < 1 or index > total or index in groups[name]:
            invalid.add(name)
            continue
        groups[name][index] = part
        totals[name].add(total)
    return {name: ' '.join(group[index] for index in range(1, total + 1))
            for name, group in groups.items()
            if name not in invalid and len(totals[name]) == 1
            for total in totals[name]
            if len(group) == total and set(group) == set(range(1, total + 1))}
