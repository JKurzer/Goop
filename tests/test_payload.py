"""goop_payload tests: byte-exact regression controls + spec hygiene.

The two pinned hashes are the sealed bramble control artifacts
(trigram-prefix-v13 and incorrect-terms-v2-120). Bramble is never read at
test time; the pins are the contract.
"""
import json
from collections import Counter

import pytest

from gooplib import payload as pl
from gooplib.spec import SpecError
from tools.goop_payload import ROOT, compose_from_spec, load_payload_spec, main

V13_SHA256 = '619cc8d7246b5259284241093c593ba04ce54fb5aa2a9d5e6c2bf02cb051eeaa'
V2_120_SHA256 = 'd6b66820af4f2617a28732bb5ede61438337412aff40afa14ec5c4a8084cf4bb'
V13_SPEC = ROOT / 'specs' / 'payload_v13.json'
V2_120_SPEC = ROOT / 'specs' / 'payload_incorrect_v2_120.json'


def run_compose(tmp_path, spec_file, output='candidate.txt'):
    """CLI-compose into a fresh run dir; return (exit code, output bytes)."""
    run_dir = tmp_path / 'run'
    run_dir.mkdir(parents=True)
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(spec_file), 'output': output}}),
        encoding='utf-8')
    code = main(['payload', str(run_dir)])
    out = run_dir / output
    return code, out.read_bytes() if out.exists() else None


def compose_lines(spec_path):
    return compose_from_spec(load_payload_spec(spec_path))[0]


QUIXMAR_SET = {'a': 'team', 'b': 'quixmar', 'c': 'owner', 'occurrences': 6}


def make_trigram_spec(tmp_path, sets, **overrides):
    """v13 spec plus trigram_sets, written to a temp spec file."""
    raw = json.loads(V13_SPEC.read_text(encoding='utf-8'))
    raw['name'] = overrides.pop('name', 'trigram-test')
    raw['trigram_sets'] = sets
    raw.update(overrides)
    path = tmp_path / 'trigram_spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


def edge_counts(lines, nodes):
    counts = Counter()
    for line in lines:
        for pair in pl.conjunction_edges(line, nodes):
            counts[pair] += 1
    return counts


# --- regression controls ---------------------------------------------------

def test_control_v13_byte_exact(tmp_path):
    code, data = run_compose(tmp_path, V13_SPEC)
    assert code == 0
    assert pl.sha256(data) == V13_SHA256


def test_control_incorrect_v2_120_byte_exact(tmp_path):
    code, data = run_compose(tmp_path, V2_120_SPEC)
    assert code == 0
    assert pl.sha256(data) == V2_120_SHA256


def test_graft_control_first_20_lines_are_v13():
    """The 120-line treatment reuses the v13 RNG stream, modulo the additive graft."""
    spec120 = load_payload_spec(V2_120_SPEC)
    terms = {entry['term'] for entry in spec120['incorrect_terms']}
    ungrafted = []
    for line in compose_lines(V2_120_SPEC)[:20]:
        words = line.split(' ')
        if words[0] in terms:  # visible bridge prepend is exactly 'term and neighbor. '
            line = ' '.join(words[3:])
        ungrafted.append(line)
    assert ungrafted == compose_lines(V13_SPEC)


# --- determinism / bounds / predicate --------------------------------------

def test_determinism(tmp_path):
    code_a, data_a = run_compose(tmp_path / 'a', V13_SPEC)
    code_b, data_b = run_compose(tmp_path / 'b', V13_SPEC)
    assert code_a == code_b == 0
    assert data_a == data_b


@pytest.mark.parametrize('spec_path', [V13_SPEC, V2_120_SPEC])
def test_byte_bounds_and_parens(spec_path):
    spec = load_payload_spec(spec_path)
    lines = compose_lines(spec_path)
    assert len(lines) == spec['lines']
    for line in lines:
        assert 0 < len(line.encode('utf-8')) <= spec['max_line_bytes']
        assert '(' not in line and ')' not in line


@pytest.mark.parametrize('spec_path', [V13_SPEC, V2_120_SPEC])
def test_visibility_predicate_compliance(spec_path):
    spec = load_payload_spec(spec_path)
    predicate = pl.make_predicate(spec['hub'], spec['filter_terms'], spec['visibility'])
    assert all(predicate(line) for line in compose_lines(spec_path))


# --- refusal behaviors -----------------------------------------------------

def test_overwrite_refusal(tmp_path):
    run_dir = tmp_path / 'run'
    run_dir.mkdir()
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(V13_SPEC), 'output': 'candidate.txt'}}),
        encoding='utf-8')
    assert main(['payload', str(run_dir)]) == 0
    before = (run_dir / 'candidate.txt').read_bytes()
    assert main(['payload', str(run_dir)]) == 1
    assert (run_dir / 'candidate.txt').read_bytes() == before


def test_unknown_spec_key_rejection(tmp_path):
    raw = json.loads(V13_SPEC.read_text(encoding='utf-8'))
    raw['bogus_key'] = 1
    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='unknown keys'):
        load_payload_spec(bad)
    raw = json.loads(V13_SPEC.read_text(encoding='utf-8'))
    raw['visibility']['bogus'] = True
    bad.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='unknown keys'):
        load_payload_spec(bad)


def test_unknown_payload_section_key_rejection(tmp_path):
    run_dir = tmp_path / 'run'
    run_dir.mkdir()
    (run_dir / 'spec.json').write_text(json.dumps({'payload': {
        'spec_file': str(V13_SPEC), 'output': 'x.txt', 'surprise': 1}}),
        encoding='utf-8')
    assert main(['payload', str(run_dir)]) == 1
    assert not (run_dir / 'x.txt').exists()


# --- freeze mode -----------------------------------------------------------

def test_freeze_roundtrip_and_pin_mismatch(tmp_path):
    source = tmp_path / 'source.txt'
    source.write_bytes(b'frozen bytes\n')
    pin = pl.sha256(source.read_bytes())
    run_dir = tmp_path / 'run'
    run_dir.mkdir()
    (run_dir / 'spec.json').write_text(json.dumps({'payload': {
        'candidate_file': str(source), 'sha256': pin, 'output': 'frozen.txt'}}),
        encoding='utf-8')
    assert main(['payload', str(run_dir)]) == 0
    assert (run_dir / 'frozen.txt').read_bytes() == b'frozen bytes\n'
    (run_dir / 'spec.json').write_text(json.dumps({'payload': {
        'candidate_file': str(source), 'sha256': '0' * 64, 'output': 'other.txt'}}),
        encoding='utf-8')
    assert main(['payload', str(run_dir)]) == 1
    assert not (run_dir / 'other.txt').exists()


# --- graph metrics sanity --------------------------------------------------

def test_v13_hub_neighbor_count():
    spec = load_payload_spec(V13_SPEC)
    lines = compose_lines(V13_SPEC)
    neighbors = pl.hub_neighbors(lines, spec['hub'], spec['vocab'])
    assert len(neighbors) == 28  # documented v13 hub neighborhood
    assert spec['hub'] not in neighbors


def test_graft_term_neighbor_counts():
    spec = load_payload_spec(V13_SPEC)
    spec120 = load_payload_spec(V2_120_SPEC)
    v13_lines = compose_lines(V13_SPEC)
    final = compose_lines(V2_120_SPEC)
    terms = [entry['term'] for entry in spec120['incorrect_terms']]
    measured = pl.term_adjacency(final, terms, spec120['vocab'], hub=spec120['hub'])
    for entry in spec120['incorrect_terms']:
        got = measured[entry['term']]
        assert got['neighbors'] == sorted(entry['neighbors'])
        assert got['neighbor_count'] == len(entry['neighbors'])
        assert got['edge_occurrences'] == len(entry['neighbors'])
    # additive only: the v13 hub neighborhood survives inside the grafted graph
    before = set(pl.hub_neighbors(v13_lines, spec['hub'], spec['vocab']))
    after = set(pl.hub_neighbors(final, spec120['hub'], spec120['vocab']))
    assert before <= after


# --- trigram sets (rare middle word) ---------------------------------------

def test_trigram_happy_path_quixmar(tmp_path):
    """a=team b=quixmar c=owner x6: measured in output, manifest, predicate 20/20."""
    spec_path = make_trigram_spec(tmp_path, [QUIXMAR_SET])
    code, data = run_compose(tmp_path, spec_path)
    assert code == 0
    spec = load_payload_spec(spec_path)
    lines = data.decode('utf-8').splitlines()
    assert len(lines) == spec['lines'] == 20
    predicate = pl.make_predicate(spec['hub'], spec['filter_terms'], spec['visibility'])
    assert all(predicate(line) for line in lines)
    for line in lines:
        assert 0 < len(line.encode('utf-8')) <= spec['max_line_bytes']
        assert '(' not in line and ')' not in line
    measured = pl.measure_trigram(lines, 'team', 'quixmar', 'owner')
    assert measured == {'team and quixmar': 6, 'quixmar and owner': 6}
    manifest = json.loads(
        (tmp_path / 'run' / 'candidate.txt.manifest.json').read_text(encoding='utf-8'))
    entry = manifest['trigram_sets'][0]
    assert entry['planned_occurrences'] == 6
    assert entry['measured'] == measured
    assert len(entry['sentences']) == 12


def test_trigram_multiple_sets(tmp_path):
    sets = [{'a': 'team', 'b': 'quixmar', 'c': 'owner', 'occurrences': 4},
            {'a': 'seed', 'b': 'zorplex', 'c': 'damage', 'occurrences': 10}]
    spec_path = make_trigram_spec(tmp_path, sets)
    lines, info = compose_from_spec(load_payload_spec(spec_path))
    assert info['trigram_sets'][0]['measured'] == {
        'team and quixmar': 4, 'quixmar and owner': 4}
    assert info['trigram_sets'][1]['measured'] == {
        'seed and zorplex': 10, 'zorplex and damage': 10}
    assert pl.measure_trigram(lines, 'seed', 'zorplex', 'damage') == {
        'seed and zorplex': 10, 'zorplex and damage': 10}


@pytest.mark.parametrize('bad', [0, 3, 11, -4, '6', 6.0, None, True,
                                 [3, 8], [5, 12], [10, 4], [4], [4, 6, 8]])
def test_trigram_occurrences_out_of_bounds(tmp_path, bad):
    entry = dict(QUIXMAR_SET, occurrences=bad)
    with pytest.raises(SpecError, match='occurrences'):
        load_payload_spec(make_trigram_spec(tmp_path, [entry]))


@pytest.mark.parametrize('good', [4, 10, [4, 10], [6, 6]])
def test_trigram_occurrences_in_bounds(tmp_path, good):
    entry = dict(QUIXMAR_SET, occurrences=good)
    spec = load_payload_spec(make_trigram_spec(tmp_path, [entry]))
    assert spec['trigram_sets'][0]['occurrences'] == good


def test_trigram_occurrence_range_is_seeded(tmp_path):
    """A [min, max] range resolves deterministically and measures as planned."""
    entry = dict(QUIXMAR_SET, occurrences=[4, 10])
    spec_path = make_trigram_spec(tmp_path, [entry])
    lines_a, info_a = compose_from_spec(load_payload_spec(spec_path))
    lines_b, info_b = compose_from_spec(load_payload_spec(spec_path))
    assert lines_a == lines_b
    planned = info_a['trigram_sets'][0]['planned_occurrences']
    assert 4 <= planned <= 10
    assert info_a['trigram_sets'][0]['measured'] == {
        'team and quixmar': planned, 'quixmar and owner': planned}


@pytest.mark.parametrize('common', ['delete', 'tick', 'the'])
def test_trigram_rarity_gate_rejects_common_b(tmp_path, common):
    entry = dict(QUIXMAR_SET, b=common)
    spec_path = make_trigram_spec(tmp_path, [entry])
    with pytest.raises(SpecError, match='rare by construction'):
        compose_from_spec(load_payload_spec(spec_path))


def test_trigram_rarity_gate_admits_rare_b(tmp_path):
    """banana is not in common_words.json and not hub/filter: admitted."""
    entry = dict(QUIXMAR_SET, b='banana', occurrences=4)
    spec_path = make_trigram_spec(tmp_path, [entry])
    lines, info = compose_from_spec(load_payload_spec(spec_path))
    assert info['trigram_sets'][0]['measured'] == {
        'team and banana': 4, 'banana and owner': 4}


def test_trigram_missing_common_words_file(tmp_path):
    spec_path = make_trigram_spec(tmp_path, [QUIXMAR_SET],
                                  common_words_file='payloads/definitely_missing.json')
    with pytest.raises(SpecError, match='common words file not found'):
        compose_from_spec(load_payload_spec(spec_path))


def test_trigram_additive_base_graph(tmp_path):
    """Every base-graph edge survives; trigram sentences only add."""
    spec_path = make_trigram_spec(tmp_path, [QUIXMAR_SET])
    v13 = load_payload_spec(V13_SPEC)
    nodes = {v13['hub'], *v13['vocab']}
    base_lines = compose_lines(V13_SPEC)
    final = compose_lines(spec_path)
    before = edge_counts(base_lines, nodes)
    after = edge_counts(final, nodes)
    for pair, count in before.items():
        assert after[pair] >= count
    base_hood = set(pl.hub_neighbors(base_lines, v13['hub'], v13['vocab']))
    assert base_hood <= set(pl.hub_neighbors(final, v13['hub'], v13['vocab']))


def test_trigram_determinism(tmp_path):
    spec_path = make_trigram_spec(tmp_path, [QUIXMAR_SET])
    code_a, data_a = run_compose(tmp_path / 'a', spec_path)
    code_b, data_b = run_compose(tmp_path / 'b', spec_path)
    assert code_a == code_b == 0
    assert data_a == data_b


def test_trigram_set_shape_rejection(tmp_path):
    for broken, pattern in [
            (dict(QUIXMAR_SET, bogus=1), 'unknown keys'),
            ({k: v for k, v in QUIXMAR_SET.items() if k != 'occurrences'},
             'missing required keys'),
            (dict(QUIXMAR_SET, b='team'), 'must differ'),
            (dict(QUIXMAR_SET, b='Quixmar'), 'lowercase ascii word'),
            (dict(QUIXMAR_SET, b='quix-mar'), 'lowercase ascii word')]:
        with pytest.raises(SpecError, match=pattern):
            load_payload_spec(make_trigram_spec(tmp_path, [broken]))


def test_trigram_duplicate_b_rejection(tmp_path):
    sets = [QUIXMAR_SET, {'a': 'seed', 'b': 'quixmar', 'c': 'team', 'occurrences': 5}]
    with pytest.raises(SpecError, match='duplicate trigram middle word'):
        load_payload_spec(make_trigram_spec(tmp_path, sets))
