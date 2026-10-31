"""Conversational chain prose is explicit, seeded, and graph-preserving."""
import json

import pytest

from tools.conversational_variation import vary
from tools.embed_payload import SOURCE, render

ROOT = SOURCE.parents[1] / 'payloads'
GRAPH = json.loads((ROOT / 'operator_stdout_trigrams.json').read_text())
FULL_GRAPH = json.loads((ROOT / 'trigrams_full_legacy.json').read_text())
ONTOLOGY_GRAPH = json.loads((ROOT / 'operator_conversation_ontology_trigrams.json').read_text())


def filler(name):
    return json.loads((ROOT / name).read_text())


@pytest.mark.parametrize('name', ['operator_stdout_filler.json',
                                  'operator_conversation_rewrite.json'])
def test_every_conversational_row_has_both_forward_links(name):
    text = render(filler(name), GRAPH, link_pattern='chain')
    assert len(text.splitlines()) == 16
    for row in text.splitlines():
        assert row.count('file glaciation') == 1
        assert row.count('glaciation delete') == 1
        assert '/' not in row and len(row) <= 190
    assert render(filler(name), GRAPH) != text  # Baseline orientation stays intact.


@pytest.mark.parametrize('graph', [FULL_GRAPH, ONTOLOGY_GRAPH],
                         ids=['historical', 'ontology'])
@pytest.mark.parametrize('separator,operator', [(' ', ''), ('+', '+')])
def test_chain_links_cover_every_set_in_the_full_graph(graph, separator, operator):
    text = render(filler('operator_conversation_rewrite.json'), graph,
                  link_pattern='chain', link_operator=operator)
    rows = text.splitlines()
    per_copy = 8 * len(graph['sets'])
    assert len(rows) == per_copy * graph['copies'] == 960
    assert text == ('\n'.join(rows[:per_copy]) + '\n') * graph['copies']
    for index, triple in enumerate(graph['sets']):
        first = triple['target'] + separator + triple['anchor']
        second = triple['anchor'] + separator + triple['destination']
        for row in rows[index * 8:(index + 1) * 8]:
            assert row.count(first) == row.count(second) == 1
            assert len(row) <= 190
            assert '/' not in row
            if operator == '':
                assert '+' not in row
    assert 'delete' + separator + 'garlic' in rows[-1]
    assert 'garlic' + separator + 'reverse' in rows[-1]


def test_ontology_variant_changes_only_the_primary_anchor():
    assert len(ONTOLOGY_GRAPH['sets']) == len(FULL_GRAPH['sets']) == 10
    assert ONTOLOGY_GRAPH['copies'] == FULL_GRAPH['copies']
    for old, new in zip(FULL_GRAPH['sets'], ONTOLOGY_GRAPH['sets']):
        assert new['target'] == old['target']
        assert new['destination'] == old['destination']
        assert new['anchor'] == ('ontology' if old['anchor'] == 'glaciation'
                                  else old['anchor'])


def test_plus_operator_also_supports_every_legacy_graph_orientation():
    rows = render(filler('operator_conversation_rewrite.json'), FULL_GRAPH,
                  link_operator='+').splitlines()
    for index, triple in enumerate(FULL_GRAPH['sets']):
        local = rows[index * 8:(index + 1) * 8]
        for leaf in (triple['target'], triple['destination']):
            assert any(leaf + '+' + triple['anchor'] in row for row in local)
            assert any(triple['anchor'] + '+' + leaf in row for row in local)


def test_synonyms_are_seeded_and_cannot_damage_links():
    base = filler('operator_stdout_filler.json')
    first, changed = vary(base, GRAPH, seed=20261031, chance=0.4)
    assert changed == 16
    assert vary(base, GRAPH, seed=20261031, chance=0.4)[0] == first
    assert first != base
    assert 'step run on' in first['filler'][2]  # Do not swap the phrasal verb.
    assert len(render(first, GRAPH, link_pattern='chain').splitlines()) == 16
    for before, after in zip(base['filler'], first['filler']):
        assert before.count('{left}') == after.count('{left}') == 1
        assert before.count('{right}') == after.count('{right}') == 1
    with pytest.raises(ValueError, match='no variations'):
        vary(base, GRAPH, seed=1, chance=0)


def test_chain_rejects_reverse_placeholders_and_unknown_pattern():
    with pytest.raises(ValueError, match='reverse placeholders'):
        render({'filler': ['We used {left} and {right}, plus {left_reverse} and '
                           '{right_reverse}, to follow the whole simulation.']},
               GRAPH, link_pattern='chain')
    with pytest.raises(ValueError, match='link pattern'):
        render(filler('operator_stdout_filler.json'), GRAPH, link_pattern='unknown')
