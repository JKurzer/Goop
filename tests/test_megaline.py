"""Megaline mode (single pair): the surviving pins.

The paren audit stack was deleted 2026-10-15 (owner ruling in
docs/TRIGRAM_BRIDGING.md). What stays pinned: byte-exact candidates,
determinism, geometry, the filter echo, plan structure, the plan-derived
truncation property, spec validation, and the legacy do-not-break
controls. Dose-counting correctness is the deterministic compose's job;
outcomes are measured downstream.
"""
import json
import re

import pytest

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError
from tools.goop_payload import ROOT, compose_from_spec, load_payload_spec, main

MEG_V1_SPEC = ROOT / 'specs' / 'payload_conformant_v1_meg.json'
MEG_V2_SPEC = ROOT / 'specs' / 'payload_conformant_v2_meg.json'
MEG_V3_SPEC = ROOT / 'specs' / 'payload_conformant_v3_meg.json'
CONFORMANT_V1_SPEC = ROOT / 'specs' / 'payload_conformant_v1.json'
CONFORMANT_V2_SPEC = ROOT / 'specs' / 'payload_conformant_v2.json'
V13_SPEC = ROOT / 'specs' / 'payload_v13.json'
V2_120_SPEC = ROOT / 'specs' / 'payload_incorrect_v2_120.json'
V13_SHA256 = '619cc8d7246b5259284241093c593ba04ce54fb5aa2a9d5e6c2bf02cb051eeaa'
V2_120_SHA256 = 'd6b66820af4f2617a28732bb5ede61438337412aff40afa14ec5c4a8084cf4bb'
CONFORMANT_V1_SHA256 = '05221435719a3c3a978af7257d4f4e046881de603c1f24d655a155e2f28e6a91'
CONFORMANT_V2_SHA256 = '57bae21da96e17207049a4b1a32df83cc1b674cb8ac2a72b069857ea98eed5c8'
MEG_V1_SHA256 = 'bafab4b11da2d34d72424e69c8bf6e79d6992f0ff79416d693753ceaee1c34ac'
MEG_V2_SHA256 = '429bf3fe62f29206e212ef5f13ae95fb434215c6df920e89ce78d5d404f67da6'
MEG_V3_SHA256 = '5b6f8184e35ea8f83008bed67aa43aece761a811829d1124e8614fd88dec5c23'


def compose(spec=MEG_V1_SPEC):
    return compose_from_spec(load_payload_spec(spec))


def meg_params(spec=MEG_V1_SPEC):
    raw = json.loads(spec.read_text(encoding='utf-8'))
    bridging = raw['bridging']
    return {'lines': raw['lines'], 'min': raw['min_line_bytes'],
            'max': raw['max_line_bytes'], 'doses': bridging['doses'],
            'filter_terms': bridging['filter_terms'],
            'prefix': bridging['filter_prefix_chars'],
            'truncation': bridging['truncation_chars']}


def run_compose(tmp_path, spec_file=MEG_V1_SPEC):
    run_dir = tmp_path / 'run'
    run_dir.mkdir(parents=True)
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(spec_file),
                                'output': 'candidate.txt'}}), encoding='utf-8')
    code = main(['payload', str(run_dir)])
    out = run_dir / 'candidate.txt'
    return code, out.read_bytes() if out.exists() else None, run_dir


def make_spec(tmp_path, bridging=None, top=None, drop=()):
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    raw.update(top or {})
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


# --- the candidates ------------------------------------------------------------

def test_meg_candidates_compose_byte_exact(tmp_path):
    for spec, sha in ((MEG_V1_SPEC, MEG_V1_SHA256), (MEG_V2_SPEC, MEG_V2_SHA256),
                      (MEG_V3_SPEC, MEG_V3_SHA256)):
        code, data, _ = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


def test_anchors_differ_only_in_the_token():
    lines_v1, _ = compose(MEG_V1_SPEC)
    lines_v2, _ = compose(MEG_V2_SPEC)
    text_v1, text_v2 = '\n'.join(lines_v1), '\n'.join(lines_v2)
    assert 'tainish' not in text_v1
    assert re.sub(r'\bhainish\b', 'tainish', text_v1) == text_v2


def test_determinism_seed_42(tmp_path):
    assert compose() == compose()
    code_a, data_a, _ = run_compose(tmp_path / 'a')
    code_b, data_b, _ = run_compose(tmp_path / 'b')
    assert code_a == code_b == 0
    assert data_a == data_b


# --- delivery shape (plan-derived) --------------------------------------------

def test_geometry_and_encoding(tmp_path):
    code, data, _ = run_compose(tmp_path)
    assert code == 0
    assert b'\r' not in data  # UTF-8, LF
    lines = data.decode('utf-8').splitlines()
    params = meg_params()
    assert len(lines) == params['lines']
    for line in lines:
        assert params['min'] <= len(line.encode('utf-8')) <= params['max']


def test_filter_echo_in_window_every_line():
    lines, _ = compose()
    params = meg_params()
    for line in lines:
        head = line[:params['prefix']].lower()
        assert any(term in head for term in params['filter_terms'])


def test_insert_order_canonical_per_line():
    lines, info = compose()
    params = meg_params()
    for row in info['bridging']['plan']:
        line = lines[row['line']]
        inserts = row['inserts']
        assert len(inserts) == 2 * len(br.CANONICAL_CONFIGS) * params['doses']
        per_dose = 2 * len(br.CANONICAL_CONFIGS)
        for dose in range(params['doses']):
            block = inserts[dose * per_dose:(dose + 1) * per_dose]
            for config_index, (first, second) in enumerate(
                    zip(block[::2], block[1::2])):
                config = br.CANONICAL_CONFIGS[config_index]
                assert first['config_index'] == config_index
                assert first['link'] == list(config[0])
                assert second['link'] == list(config[1])
        for insert in inserts:
            assert line[insert['start']:insert['end']] == insert['text']
            assert 'pair' not in insert  # historical single-pair plan shape
        assert row['bytes'] == len(line.encode('utf-8'))


def test_first_four_links_inside_truncation_via_plan():
    _, info = compose()
    params = meg_params()
    for row in info['bridging']['plan']:
        assert row['inserts'][3]['end'] <= params['truncation']


def test_v3_is_adjacent_form_only():
    """The 2026-10-15 form ruling: adjacent only, 'and' is a token."""
    _, info = compose(MEG_V3_SPEC)
    for row in info['bridging']['plan']:
        assert {insert['form'] for insert in row['inserts']} == {'adjacent'}
        for insert in row['inserts']:
            assert re.fullmatch(r'\([a-z]+ [a-z]+\)', insert['text'])


# --- spec refusal behaviors ----------------------------------------------------

def test_megaline_keys_required_when_enabled(tmp_path):
    for key in ('filter_terms', 'filter_prefix_chars', 'truncation_chars',
                'lead_ins'):
        with pytest.raises(SpecError, match='megaline requires'):
            load_payload_spec(make_spec(tmp_path, drop=(key,)))


def test_megaline_keys_rejected_when_disabled(tmp_path):
    with pytest.raises(SpecError, match='megaline-only keys'):
        load_payload_spec(make_spec(tmp_path, bridging={'megaline': False}))


def test_lead_in_without_echo_rejected(tmp_path):
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['lead_ins'][0] = 'The cat sat on the mat.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='no filter term'):
        load_payload_spec(path)


def test_lead_in_with_role_word_rejected(tmp_path):
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['lead_ins'][0] = 'The hainish sat, the seed grew.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)


def test_truncation_chars_validated(tmp_path):
    with pytest.raises(SpecError, match='integer'):
        load_payload_spec(make_spec(tmp_path,
                                    bridging={'truncation_chars': '240'}))
    with pytest.raises(SpecError, match='must not exceed'):
        load_payload_spec(make_spec(
            tmp_path, bridging={'truncation_chars':
                                meg_params()['prefix'] + 1}))


def test_truncation_hard_fail_when_front_packing_breaks(tmp_path):
    path = make_spec(tmp_path, bridging={'truncation_chars': 10})
    with pytest.raises(SpecError, match='first four LINKs'):
        compose_from_spec(load_payload_spec(path))


def test_min_above_max_rejected(tmp_path):
    with pytest.raises(SpecError, match='must not exceed'):
        load_payload_spec(make_spec(tmp_path, top={'min_line_bytes': 600}))


def test_manifest_megaline_section(tmp_path):
    code, _, run_dir = run_compose(tmp_path)
    assert code == 0
    manifest = json.loads(
        (run_dir / 'candidate.txt.manifest.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'conformant-v1-meg'
    bridging = manifest['bridging']
    assert 'measurement' not in bridging
    assert 'role_audit' not in bridging
    assert 'paren_integrity' not in bridging
    mega = bridging['megaline']
    params = meg_params()
    assert mega['filter_terms'] == params['filter_terms']
    assert mega['filter_prefix_chars'] == params['prefix']
    assert mega['truncation_chars'] == params['truncation']
    assert mega['min_line_bytes'] == params['min']
    assert len(bridging['plan']) == params['lines']


# --- legacy do-not-break contract ----------------------------------------------

def test_legacy_controls_still_pass(tmp_path):
    for spec, sha in ((V13_SPEC, V13_SHA256), (V2_120_SPEC, V2_120_SHA256),
                      (CONFORMANT_V1_SPEC, CONFORMANT_V1_SHA256),
                      (CONFORMANT_V2_SPEC, CONFORMANT_V2_SHA256)):
        code, data, _ = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


def test_classic_bridging_mode_unchanged():
    lines, info = compose(CONFORMANT_V1_SPEC)
    assert info['bridging']['doses'] == 2
    assert 'megaline' not in info['bridging']
