"""One-token derivative preserves build controls and distinct old arms."""
from tools.goop_graph_swap import WHOLE_TOKEN, swapped


def test_swap_replaces_spec_values_not_control_keys():
    original = {'anchor': 'teleology',
                'formats': {'summary': 'SUMMARY teleology team\n'},
                'doses': {'RunA': 0, 'RunB': 160}}
    result = swapped(original)
    assert result == {'anchor': 'hainish',
                      'formats': {'summary': 'SUMMARY hainish team\n'},
                      'doses': {'RunA': 0, 'RunB': 160}}
    assert original['anchor'] == 'teleology'


def test_candidate_swap_respects_word_boundaries():
    candidate = b'(teleology team) teleological teleology>team\n'
    changed = WHOLE_TOKEN.sub(b'hainish', candidate)
    assert changed == b'(hainish team) teleological hainish>team\n'
