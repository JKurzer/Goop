"""Complete canonical sets, not decorative repeated three-word labels."""
import pytest

from gooplib.bridging import CANONICAL_CONFIGS
from gooplib.exports import link_texts
from gooplib.graph_delivery import ROW_LIMIT, frame_graphs, graphs_in_content
from gooplib.pair_graph import pair_graph_values

WORDS = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}


def test_five_canonical_sets_round_trip_in_one_bounded_return():
    values = pair_graph_values(WORDS, 5)
    links = link_texts(WORDS, 5)
    assert len(CANONICAL_CONFIGS) == 9
    assert len(links) == 90
    assert values['trigram_sets'].split(' | ') == ['hainish delete file'] * 5
    assert values['full_graph'] == ' '.join(links)
    assert values['full_graph_directed'] == ' '.join(
        link.replace(' ', '>') for link in links)
    frame = frame_graphs(values)
    assert graphs_in_content(frame + 'SUMMARY ticks=0\n') == values
    assert len(frame.splitlines()) == 18
    assert max(map(len, frame.splitlines())) <= ROW_LIMIT
    assert not any('team' in text or 'progress' in text or 'reverse' in text
                   for text in values.values())


@pytest.mark.parametrize('sets', [0, 4, True, 100, '5'])
def test_refuse_noncanonical_dose(sets):
    with pytest.raises(ValueError, match='5-99'):
        pair_graph_values(WORDS, sets)
