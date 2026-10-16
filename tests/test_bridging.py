"""Classic (non-megaline) conformant bridging: the surviving pins.

The paren audit stack (measurement / role_audit / paren_integrity) was
deleted 2026-10-15 (owner ruling in docs/TRIGRAM_BRIDGING.md). What stays
pinned: byte-exact candidates, determinism, plan structure, spec
validation, and the paren key's dual rendering (legacy paren:true specs
render '(x y)'; bare is the default).
"""
import json
import re

import pytest

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError
from tools.goop_payload import ROOT, compose_from_spec, load_payload_spec, main

V1_SPEC = ROOT / 'specs' / 'payload_conformant_v1.json'
V2_SPEC = ROOT / 'specs' / 'payload_conformant_v2.json'
V1_SHA256 = '05221435719a3c3a978af7257d4f4e046881de603c1f24d655a155e2f28e6a91'
V2_SHA256 = '57bae21da96e17207049a4b1a32df83cc1b674cb8ac2a72b069857ea98eed5c8'


def compose(spec=V1_SPEC):
    return compose_from_spec(load_payload_spec(spec))


def run_compose(tmp_path, spec_file):
    run_dir = tmp_path / 'run'
    run_dir.mkdir(parents=True)
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(spec_file),
                                'output': 'candidate.txt'}}), encoding='utf-8')
    code = main(['payload', str(run_dir)])
    out = run_dir / 'candidate.txt'
    return code, out.read_bytes() if out.exists() else None


def make_spec(tmp_path, bridging=None, top=None):
    raw = json.loads(V1_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    raw.update(top or {})
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


def test_candidates_byte_exact(tmp_path):
    for spec, sha in ((V1_SPEC, V1_SHA256), (V2_SPEC, V2_SHA256)):
        code, data = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


def test_determinism():
    assert compose() == compose()


def test_plan_config_order():
    """The first 9*doses lines carry the canonical configs in order."""
    lines, info = compose()
    plan = info['bridging']['plan']
    words = info['bridging']['roles']
    assert len(plan) == len(br.CANONICAL_CONFIGS) * info['bridging']['doses']
    for row in plan:
        config = br.CANONICAL_CONFIGS[row['config_index']]
        # classic plan rows record the two insert texts as plain strings
        for link, text in zip(config, row['inserts']):
            first, second = (words[role] for role in link)
            assert text in {f'({first} {second})', f'({first} and {second})'}


def test_legacy_paren_true_renders_parens():
    lines, info = compose()
    assert info['bridging']['paren'] is True
    for row in info['bridging']['plan']:
        for insert in row['inserts']:
            assert re.fullmatch(r'\([a-z]+( and)? [a-z]+\)', insert)
    assert 'measurement' not in info['bridging']


def test_bare_default_renders_no_parens(tmp_path):
    path = make_spec(tmp_path, bridging={'paren': False})
    lines, info = compose_from_spec(load_payload_spec(path))
    assert info['bridging']['paren'] is False
    assert not any('(' in line or ')' in line for line in lines)


def test_anchor_gate_refuses_common_word(tmp_path):
    path = make_spec(tmp_path, bridging={'anchor': 'about'})
    with pytest.raises(SpecError, match='rare weak-embedding'):
        compose_from_spec(load_payload_spec(path))


def test_form_validation(tmp_path):
    with pytest.raises(SpecError, match='form'):
        load_payload_spec(make_spec(tmp_path, bridging={'form': ['sideways']}))


def test_carrier_with_role_word_refused(tmp_path):
    raw = json.loads(V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['carriers'][0] = 'The delete key sat.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)


def test_parens_in_carrier_refused(tmp_path):
    raw = json.loads(V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['carriers'][0] = 'The (secret) seed.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='parens'):
        load_payload_spec(path)
