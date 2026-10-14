"""Tests for tools/chain_analysis.py — synthetic fixtures + real-text gates."""
import sys
from pathlib import Path

import pytest

GOOP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP_ROOT))
sys.path.insert(0, str(GOOP_ROOT / 'tools'))

from gooplib.payload import PAIR, WORD  # noqa: E402
import chain_analysis as ca  # noqa: E402

COMMON = frozenset({'the', 'and', 'delete', 'team', 'owner', 'checksum',
                    'constants', 'file', 'hainish'})

BRAMBLE = Path(r'C:\Users\poly\bramble')
HAINISH = BRAMBLE / 'eval' / 'native' / 'payloads' / 'hainish_40.txt'
V13 = BRAMBLE / 'eval' / 'native' / 'payloads' / 'derived' / \
    'trigram-prefix-v13' / 'candidate.txt'
V15 = GOOP_ROOT / 'runs' / 'packed-v15' / 'inputs' / 'candidate.txt'


# --- regex family -----------------------------------------------------------

def test_regexes_are_gooplib_graph_metrics():
    # The whole point: identical patterns, not a re-roll.
    assert ca.PAIR is PAIR and ca.WORD is WORD
    assert ca.PAIR.pattern == r'(?=\b([a-z]+) and ([a-z]+)\b)'


def test_pair_lookahead_keeps_both_edges_of_a_and_b_and_c():
    assert ca.edge_counts('a and b and c') == {('a', 'b'): 1, ('b', 'c'): 1}


def test_pair_lowercase_only_and_punctuation_stays_outside():
    # Capitalized 'Foo' never matches (no \b inside the word); the comma
    # after 'bar' blocks no match — there is simply no ' and ' after it.
    edges = ca.edge_counts('Foo and bar, baz and quux.')
    assert edges == {('baz', 'quux'): 1}


# --- graph construction -----------------------------------------------------

def test_middle_requires_both_directions():
    edges = ca.edge_counts('x and mid. mid and y. solo and zed.')
    out_map, in_map = ca.adjacency(edges)
    assert ca.middles(out_map, in_map) == ['mid']


def test_chain_triple_instances_multiply_edge_multiplicity():
    edges = ca.edge_counts('x and mid. x and mid. mid and y. mid and y. '
                           'mid and y.')
    triples = ca.chain_triples(*ca.adjacency(edges))
    assert triples == {('x', 'mid', 'y'): 2 * 3}


def test_chain_allows_a_equals_c_and_cycles_terminate():
    edges = ca.edge_counts('file and hainish. hainish and file.')
    out_map, in_map = ca.adjacency(edges)
    triples = ca.chain_triples(out_map, in_map)
    assert ('file', 'hainish', 'file') in triples
    assert ('hainish', 'file', 'hainish') in triples
    ext, truncated = ca.extended_paths(out_map)
    assert not truncated and ext == []  # 2-cycle makes no simple 3-path


def test_extended_paths_finds_simple_longer_chains():
    edges = ca.edge_counts('c and w. w and k. k and z. z and o.')
    ext, truncated = ca.extended_paths(ca.adjacency(edges)[0])
    assert not truncated
    assert ('c', 'w', 'k', 'z', 'o') in ext          # len 4
    assert ('c', 'w', 'k', 'z') in ext               # len 3
    assert all(len(set(p)) == len(p) for p in ext)   # simple paths only


# --- report semantics -------------------------------------------------------

def test_rare_gate_is_not_in_common_words():
    report = ca.analyze_text('x and zelquor. zelquor and y.', COMMON,
                             targets=['zelquor'])
    assert report['n_middles'] == 1
    assert report['n_middles_rare'] == 1
    assert report['rare_b'] == ['zelquor']
    assert report['targets']['zelquor']['as_b_triples'] == 1
    assert report['rare_b_triples'] == [('x', 'zelquor', 'y')]


def test_common_b_counts_as_common_even_when_frequent():
    report = ca.analyze_text('x and the. the and y.', COMMON, targets=[])
    assert report['n_middles'] == 1 and report['n_middles_rare'] == 0
    assert report['rare_b_triples_distinct'] == 0


def test_pure_source_rare_term_is_not_a_middle():
    # The graft shape: rare term only ever on the left of 'and'.
    report = ca.analyze_text('banana and owner. banana and team. '
                             'owner and team.', COMMON, targets=['banana'])
    t = report['targets']['banana']
    assert t['rare'] and t['as_a'] == 2
    assert t['as_c'] == 0 and t['as_b_triples'] == 0
    assert 'banana' not in [m['b'] for m in report['middles']]


def test_v15_shape_gives_len4_simple_path():
    text = ('constants and watermark. watermark and checksum. '
            'checksum and zelquor. zelquor and owner.')
    report = ca.analyze_text(text, COMMON,
                             targets=['zelquor', 'watermark'])
    assert report['max_chain_len'] == 4
    assert report['length_dist'] == {2: 3, 3: 2, 4: 1}
    assert set(report['rare_b']) == {'zelquor', 'watermark'}


# --- real-text gates (skip when the archive is absent) ----------------------

@pytest.mark.skipif(not HAINISH.is_file(), reason='bramble archive absent')
def test_hainish40_hainish_sits_in_b_position():
    report = ca.analyze_text(HAINISH.read_text(encoding='utf-8'), COMMON)
    middles = {m['b'] for m in report['middles']}
    assert {'hainish', 'file', 'delete'} <= middles
    assert report['triples_distinct'] > 0


@pytest.mark.skipif(not V15.is_file(), reason='packed-v15 run absent')
def test_v15_has_rare_b_chains_zelquor_and_watermark():
    common = ca.load_common_words(ca.DEFAULT_COMMON)
    report = ca.analyze_text(V15.read_text(encoding='utf-8'), common)
    assert {'zelquor', 'watermark'} <= set(report['rare_b'])
    assert report['rare_b_triples_distinct'] >= 2


@pytest.mark.skipif(not V13.is_file(), reason='bramble archive absent')
def test_v13_has_zero_rare_b_chains():
    common = ca.load_common_words(ca.DEFAULT_COMMON)
    report = ca.analyze_text(V13.read_text(encoding='utf-8'), common)
    assert report['n_middles_rare'] == 0
    assert report['rare_b_triples_distinct'] == 0
