"""Multi-pair megaline mode (v5/v6/v7): the surviving pins.

The paren audit stack was deleted 2026-10-15. What stays pinned:
byte-exact candidates, plan-derived structure (per-pair config order,
link totals, the truncation property), spec validation, and the manifest
shape. Dose counting is the deterministic compose's job; adoption is
read off sessions downstream.
"""
import json
import re

import pytest

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError
from tools.goop_payload import ROOT, compose_from_spec, load_payload_spec, main

V5_SPEC = ROOT / 'specs' / 'payload_conformant_v5_meg.json'
V5_SHA256 = '222f1654e92e98983344d3b9626c4f7a571ae145f0b291da1fcce33c4eebf9a0'
V5_PAIRS = [{'anchor': 'teleology', 'target': 'delete', 'destination': 'file'},
            {'anchor': 'teleology', 'target': 'checksum', 'destination': 'delete'}]
V6_SPEC = ROOT / 'specs' / 'payload_conformant_v6_meg.json'
V6_SHA256 = '66ef4565c612c6d040c42a4429c8fcfe4a99524336b959e74016122786731384'
V6_PAIRS = [{'anchor': 'teleology', 'target': 'remove', 'destination': 'garlic'},
            {'anchor': 'teleology', 'target': 'remove', 'destination': 'function'},
            {'anchor': 'teleology', 'target': 'load', 'destination': 'function'}]
V7_SPEC = ROOT / 'specs' / 'payload_conformant_v7_meg.json'
V7_SHA256 = 'ea1a4fb55335ffcd0e07e19f34ef6c9fed05040dc4390115b9532cc017622bdc'
V7_PAIRS = [{'anchor': 'initialization', 'target': 'team', 'destination': 'mans'},
            {'anchor': 'initialization', 'target': 'progress',
             'destination': 'team'},
            {'anchor': 'initialization', 'target': 'slot',
             'destination': 'remove'}]
ARMS = ((V5_SPEC, V5_SHA256, V5_PAIRS, 2, (1450, 2000)),
        (V6_SPEC, V6_SHA256, V6_PAIRS, 2, (2100, 2700)),
        (V7_SPEC, V7_SHA256, V7_PAIRS, 2, (2100, 2700)))


def run_compose(tmp_path, spec_file):
    run_dir = tmp_path / 'run'
    run_dir.mkdir(parents=True)
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(spec_file),
                                'output': 'candidate.txt'}}), encoding='utf-8')
    code = main(['payload', str(run_dir)])
    out = run_dir / 'candidate.txt'
    return code, out.read_bytes() if out.exists() else None, run_dir


def test_arms_compose_byte_exact(tmp_path):
    for spec, sha, *_ in ARMS:
        code, data, _ = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


@pytest.mark.parametrize('spec, sha, pairs, doses, band', ARMS)
def test_arm_structure(spec, sha, pairs, doses, band):
    """Plan-derived structure: per-line per-pair canonical order, link
    totals, echo, the truncation property, geometry, determinism."""
    lines, info = compose_from_spec(load_payload_spec(spec))
    assert (lines, info) == compose_from_spec(load_payload_spec(spec))
    per_block = 2 * len(br.CANONICAL_CONFIGS)
    expected_order = [(dose, pair_index)
                      for dose in range(doses) for pair_index in range(len(pairs))]
    for row in info['bridging']['plan']:
        line = lines[row['line']]
        inserts = row['inserts']
        assert len(inserts) == per_block * len(pairs) * doses
        for block_index, (dose, pair_index) in enumerate(expected_order):
            block = inserts[block_index * per_block:(block_index + 1) * per_block]
            for config_index, (first, second) in enumerate(
                    zip(block[::2], block[1::2])):
                config = br.CANONICAL_CONFIGS[config_index]
                assert first['dose'] == dose and first['pair'] == pair_index
                assert first['link'] == list(config[0])
                assert second['link'] == list(config[1])
        for insert in inserts:
            assert line[insert['start']:insert['end']] == insert['text']
        assert inserts[3]['end'] <= 240  # first four LINKs, plan-derived
        assert any(term in line[:512].lower()
                   for term in ('tick', 'seed', 'score', 'alive', 'owner',
                                'summary'))
        assert band[0] <= len(line.encode('utf-8')) <= band[1]
        assert {insert['form'] for insert in inserts} == {'adjacent'}


def test_manifest_pairs_section(tmp_path):
    code, _, run_dir = run_compose(tmp_path, V5_SPEC)
    assert code == 0
    manifest = json.loads(
        (run_dir / 'candidate.txt.manifest.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'conformant-v5-meg'
    bridging = manifest['bridging']
    assert 'measurement' not in bridging
    assert 'role_audit' not in bridging
    assert 'paren_integrity' not in bridging
    assert bridging['pairs'] == V5_PAIRS
    mega = bridging['megaline']
    assert mega['pairs'] == V5_PAIRS
    assert mega['truncation_chars'] == 240
    assert len(bridging['plan']) == 20


# --- second_pair / pairs-form refusals ------------------------------------------

def make_v5_spec(tmp_path, bridging=None, drop=()):
    raw = json.loads(V5_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


def make_v6_spec(tmp_path, bridging=None, drop=()):
    raw = json.loads(V6_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


def test_second_pair_requires_megaline(tmp_path):
    path = make_v5_spec(tmp_path, bridging={'megaline': False})
    with pytest.raises(SpecError, match='megaline'):
        load_payload_spec(path)


def test_second_pair_duplicate_refused(tmp_path):
    path = make_v5_spec(tmp_path, bridging={
        'second_pair': {'target': 'delete', 'destination': 'file'}})
    with pytest.raises(SpecError, match='duplicates'):
        load_payload_spec(path)


def test_second_pair_anchor_as_leaf_refused(tmp_path):
    path = make_v5_spec(tmp_path, bridging={
        'second_pair': {'target': 'teleology', 'destination': 'file'}})
    with pytest.raises(SpecError, match='R1'):
        load_payload_spec(path)


def test_second_pair_two_shared_leaves_refused(tmp_path):
    path = make_v5_spec(tmp_path, bridging={
        'second_pair': {'target': 'file', 'destination': 'delete'}})
    with pytest.raises(SpecError, match='share leaves'):
        load_payload_spec(path)


def test_carrier_with_pair2_word_refused_at_load(tmp_path):
    raw = json.loads(V5_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['carriers'][-1] = 'The checksum was verified.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)


def test_pairs_form_refusals(tmp_path):
    spec_pairs = [{role: pair[role] for role in ('target', 'destination')}
                  for pair in V6_PAIRS]
    with pytest.raises(SpecError, match='1-3'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'pairs': spec_pairs + [spec_pairs[0]]}))
    with pytest.raises(SpecError, match='mutually exclusive'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'second_pair': {'target': 'x', 'destination': 'y'}}))
    with pytest.raises(SpecError, match='mutually exclusive'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'target': 'remove', 'destination': 'garlic'}))
    with pytest.raises(SpecError, match='share leaves'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'pairs': [spec_pairs[0],
                      {'target': 'garlic', 'destination': 'remove'},
                      spec_pairs[2]]}))
    with pytest.raises(SpecError, match='R1'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'pairs': [{'target': 'teleology', 'destination': 'garlic'},
                      spec_pairs[1], spec_pairs[2]]}))
    path = make_v6_spec(tmp_path, bridging={'megaline': False})
    with pytest.raises(SpecError, match='megaline'):
        load_payload_spec(path)
