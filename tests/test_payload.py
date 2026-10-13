"""goop_payload tests: byte-exact regression controls + spec hygiene.

The two pinned hashes are the sealed bramble control artifacts
(trigram-prefix-v13 and incorrect-terms-v2-120). Bramble is never read at
test time; the pins are the contract.
"""
import json

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
