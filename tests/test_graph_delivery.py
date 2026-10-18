"""The delivery contract: complete bounded rows, in ONE CONTENT event."""

import pytest

from gooplib.graph_delivery import (ROW_LIMIT, NAMES, canonical_from_startup,
                                    frame_graphs, graphs_in_content)

VALUES = {'trigram_sets': 'teleology team reverse | teleology progress team',
          'full_graph': ' '.join(['teleology', 'team', 'reverse'] * 30),
          'full_graph_directed': ' '.join(['teleology>team', 'team>reverse', ';'] * 27)}


def test_graphs_round_trip_in_bounded_plaintext_rows():
    frame = frame_graphs(VALUES)
    assert max(map(len, frame.splitlines())) <= ROW_LIMIT
    assert len(frame.splitlines()) > len(NAMES)
    assert graphs_in_content('PE header\n' + frame + 'SUMMARY ticks=0\n') == VALUES
    assert canonical_from_startup(
        f'STARTUP seed trigram_sets={VALUES["trigram_sets"]} '
        f'full_graph={VALUES["full_graph"]} '
        f'full_graph_directed={VALUES["full_graph_directed"]}\n') == VALUES


def test_graphs_cannot_be_assembled_across_returns_or_from_missing_rows():
    rows = frame_graphs(VALUES).splitlines()
    assert graphs_in_content('\n'.join(rows[:4])) != VALUES
    assert graphs_in_content('\n'.join(rows[4:])) != VALUES
    assert graphs_in_content('\n'.join(rows[:1] + rows[2:])) != VALUES
    assert graphs_in_content('\n'.join(rows + rows[1:2])) != VALUES
    changed = rows.copy()
    changed[1] = changed[1].replace('teleology', 'reverse', 1)
    assert graphs_in_content('\n'.join(changed)) != VALUES
    clipped = rows.copy()
    clipped[1] = clipped[1][:60] + '... [truncated]'
    assert graphs_in_content('\n'.join(clipped)) != VALUES


@pytest.mark.parametrize('values', [
    {**VALUES, 'full_graph': 'teleology  team'},
    {**VALUES, 'full_graph': 'x' * 200},
    {**VALUES, 'full_graph': 'bad %d'},
])
def test_graph_framing_refuses_ambiguous_or_unbounded_data(values):
    with pytest.raises(ValueError):
        frame_graphs(values)
