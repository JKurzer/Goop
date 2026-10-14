"""Bridging-mode tests: the first conformant payload construction.

Pins the 9-config canonical BRIDGING (docs/TRIGRAM_BRIDGING.md per the
owner errata: 8 mirrored anchor-bearing pairs + the spare leaf-to-leaf
config), the drill format (parens kept, both insert forms), the role
discipline (anchor only ever at a bridge position; declared leaf-to-leaf
links excepted BY DESIGN), determinism, byte bounds, the stealth check vs
the goop baseline, and the do-not-break contract with the legacy controls.
"""
import json

import pytest

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError
from tools.goop_payload import ROOT, compose_from_spec, load_payload_spec, main

CONFORMANT_SPEC = ROOT / 'specs' / 'payload_conformant_v1.json'
V13_SPEC = ROOT / 'specs' / 'payload_v13.json'
V2_120_SPEC = ROOT / 'specs' / 'payload_incorrect_v2_120.json'
V13_SHA256 = '619cc8d7246b5259284241093c593ba04ce54fb5aa2a9d5e6c2bf02cb051eeaa'
V2_120_SHA256 = 'd6b66820af4f2617a28732bb5ede61438337412aff40afa14ec5c4a8084cf4bb'
WORDS = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}


def compose():
    return compose_from_spec(load_payload_spec(CONFORMANT_SPEC))


def run_compose(tmp_path, spec_file=CONFORMANT_SPEC):
    """CLI-compose into a fresh run dir; return (exit code, output bytes, run_dir)."""
    run_dir = tmp_path / 'run'
    run_dir.mkdir(parents=True)
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(spec_file),
                                'output': 'candidate.txt'}}), encoding='utf-8')
    code = main(['payload', str(run_dir)])
    out = run_dir / 'candidate.txt'
    return code, out.read_bytes() if out.exists() else None, run_dir


def make_spec(tmp_path, bridging=None, top=None, drop=()):
    """The conformant spec with bridging-section overrides, in a temp file."""
    raw = json.loads(CONFORMANT_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    raw.update(top or {})
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


# --- canonical construction ------------------------------------------------

def test_canonical_set_shape():
    """Code-level invariant: the 9-config canonical set per the owner errata.

    The 8 rows of TRIGRAM_BRIDGING.md read as 4 mirrored anchor-bearing
    pairs (row 4 corrected to LINK(TARGET, ANCHOR) LINK(DESTINATION,
    ANCHOR)) plus the spare config LINK(DESTINATION, ANCHOR)
    LINK(DESTINATION, TARGET) — the owner's verbatim "spare d->a and d->t
    link". D->T is the set's one anchorless link, declared by design.
    """
    assert len(br.CANONICAL_CONFIGS) == 9
    for config in br.CANONICAL_CONFIGS:
        assert len(config) == 2
    for config in br.CANONICAL_CONFIGS[:8]:  # the mirrored anchor-bearing pairs
        for link in config:
            assert 'anchor' in link
    assert br.CANONICAL_CONFIGS[8] == (('destination', 'anchor'),
                                       ('destination', 'target'))
    anchorless = [link for config in br.CANONICAL_CONFIGS for link in config
                  if 'anchor' not in link]
    assert anchorless == [('destination', 'target')]
    assert br.CANONICAL_LEAF_LINKS == (('destination', 'target'),)


def test_nine_config_coverage_exact():
    """All 9 canonical configs, exactly `doses` each, parsed off the text."""
    lines, info = compose()
    measured = info['bridging']['measurement']
    assert measured['per_config'] == {
        br.config_label(config): 2 for config in br.CANONICAL_CONFIGS}
    assert measured['pair_total'] == 18
    assert measured['link_total'] == 36
    plan = info['bridging']['plan']
    assert len(plan) == 18
    for row in plan:
        assert row['config_index'] == row['line'] // 2  # canonical order
        assert row['config'] == br.config_label(
            br.CANONICAL_CONFIGS[row['config_index']])
        assert all(insert in lines[row['line']] for insert in row['inserts'])


def test_directionality_counts():
    """Directed forms: mirrored anchor pairs at 8 each, plus the errata spare.

    The target pairing stays exactly mirrored; the destination pairing is
    mirrored at 8 PLUS the spare d->a of the leaf-to-leaf config; d->t is
    the declared anchorless spare at exactly `doses`.
    """
    _, info = compose()
    forms = info['bridging']['measurement']['directed_forms']
    assert forms == {'anchor>target': 8, 'target>anchor': 8,
                     'anchor>destination': 8, 'destination>anchor': 10,
                     'destination>target': 2}
    assert forms['anchor>target'] == forms['target>anchor'] > 0
    assert forms['destination>anchor'] == forms['anchor>destination'] + 2


def test_paren_balance_and_insert_shapes():
    lines, _ = compose()
    assert br.paren_integrity(lines)['ok']
    for number, line in enumerate(lines):
        assert line.count('(') == line.count(')')
        groups = br.paren_groups(line)
        assert len(groups) == (2 if number < 18 else 0)  # 18 bridging + 2 bare
        for group in groups:
            assert br.parse_link(group, {w: r for r, w in WORDS.items()})


def test_both_insert_forms_used():
    """form: [adjacent, conjunction] — the drill's two renderings both appear."""
    _, info = compose()
    used = {form for row in info['bridging']['plan'] for form in row['forms']}
    assert used == {'adjacent', 'conjunction'}


# --- vehicle / determinism ---------------------------------------------------

def test_byte_bounds_and_encoding(tmp_path):
    code, data, _ = run_compose(tmp_path)
    assert code == 0
    assert b'\r' not in data  # UTF-8, LF
    lines = data.decode('utf-8').splitlines()
    assert len(lines) == 20
    for line in lines:
        assert 0 < len(line.encode('utf-8')) <= 500


def test_determinism_seed_42(tmp_path):
    lines_a, info_a = compose()
    lines_b, info_b = compose()
    assert lines_a == lines_b
    assert info_a == info_b
    code_a, data_a, _ = run_compose(tmp_path / 'a')
    code_b, data_b, _ = run_compose(tmp_path / 'b')
    assert code_a == code_b == 0
    assert data_a == data_b


# --- roles / refusal behaviors ----------------------------------------------

def test_role_audit_post_compose():
    lines, info = compose()
    audit = info['bridging']['role_audit']
    assert audit['ok']
    assert audit['anchor_occurrences'] == 34
    assert audit['anchor_at_bridge'] == 34  # anchor only ever at bridge position
    assert info['bridging']['measurement']['word_totals'] == {
        'hainish': 34, 'delete': 18, 'file': 20}
    roles = {w: r for r, w in WORDS.items()}
    for line in lines:  # no role word anywhere outside the inserts
        assert not [t for t in br.WORD.findall(br.strip_groups(line).lower())
                    if t in roles]


def test_declared_leaf_to_leaf_link_accepted():
    """The errata spare: D->T (destination=file before target=delete) is declared."""
    roles = {w: r for r, w in WORDS.items()}
    for line in ('The (file delete) dog sat on the mat.',
                 'The (file and delete) dog sat on the mat.'):
        groups = br.paren_groups(line)
        assert br.parse_link(groups[0], roles) == ('destination', 'target')
        audit = br.role_audit([line], WORDS)
        assert audit['ok'], audit['violations']
        assert audit['anchor_occurrences'] == 0  # no anchor, none required


def test_undeclared_anchorless_link_rejected():
    """Anchorless LINKs outside the declared leaf set are audit violations.

    The mirrored T->D is NOT declared — the errata declares D->T only, in
    destination -> target order per the list — so it dies here.
    """
    for line in ('The (delete file) dog sat on the mat.',
                 'The (delete and file) dog sat on the mat.'):
        audit = br.role_audit([line], WORDS)
        assert not audit['ok']
        assert any('anchorless' in v['error'] for v in audit['violations'])


def test_anchor_self_pair_still_rejected():
    audit = br.role_audit(['The (hainish hainish) dog sat on the mat.'], WORDS)
    assert not audit['ok']
    assert any('itself' in v['error'] for v in audit['violations'])


@pytest.mark.parametrize('broken', [
    {'target': 'hainish'},                  # anchor at a target position
    {'destination': 'hainish'},             # anchor at a destination position
    {'target': 'file'},                     # target aliased onto destination
    {'anchor': 'delete'},                   # target word as anchor
])
def test_role_aliasing_rejected(tmp_path, broken):
    with pytest.raises(SpecError, match='distinct'):
        load_payload_spec(make_spec(tmp_path, bridging=broken))


# Ordinary English, absent from the carriers, non-colliding with the roles:
# these sail past validation and die at the anchor rarity gate.
@pytest.mark.parametrize('common', ['summary', 'tick', 'team', 'score'])
def test_ordinary_word_anchor_rejected(tmp_path, common):
    """The R1 mistake, gated: an ordinary-word anchor is unattributable."""
    with pytest.raises(SpecError, match='rare weak-embedding'):
        compose_from_spec(load_payload_spec(
            make_spec(tmp_path, bridging={'anchor': common})))


def test_anchor_gate_missing_file(tmp_path):
    path = make_spec(tmp_path, bridging={'common_words_file': 'payloads/nope.json'})
    with pytest.raises(SpecError, match='ordinary words file not found'):
        compose_from_spec(load_payload_spec(path))


@pytest.mark.parametrize('word', ['hainish', 'file', 'delete'])
def test_carrier_with_role_word_rejected(tmp_path, word):
    raw = json.loads(CONFORMANT_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['carriers'][0] = f'The {word} sat on the mat.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)


def test_paren_false_rejected(tmp_path):
    """The stripped-paren form was the R5 break; this mode never strips."""
    with pytest.raises(SpecError, match='paren'):
        load_payload_spec(make_spec(tmp_path, bridging={'paren': False}))


def test_unknown_keys_rejected(tmp_path):
    with pytest.raises(SpecError, match='unknown keys'):
        load_payload_spec(make_spec(tmp_path, bridging={'bogus': 1}))
    with pytest.raises(SpecError, match='unknown keys'):
        load_payload_spec(make_spec(tmp_path, top={'bogus': 1}))


def test_legacy_keys_disjoint_with_bridging(tmp_path):
    with pytest.raises(SpecError, match='disjoint'):
        load_payload_spec(make_spec(tmp_path, top={'hub': 'delete'}))


def test_missing_required_bridging_key(tmp_path):
    with pytest.raises(SpecError, match='missing required keys'):
        load_payload_spec(make_spec(tmp_path, drop=('anchor',)))


def test_doses_vs_lines_rejected(tmp_path):
    with pytest.raises(SpecError, match='LINK-pair lines'):
        load_payload_spec(make_spec(tmp_path, bridging={'doses': 3}))  # 24 > 20


def test_carriers_without_replacement_rejected(tmp_path):
    raw = json.loads(CONFORMANT_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['carriers'] = raw['bridging']['carriers'][:19]
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='without replacement'):
        load_payload_spec(path)


# --- manifest / measurement ---------------------------------------------------

def test_manifest_measurements(tmp_path):
    code, _, run_dir = run_compose(tmp_path)
    assert code == 0
    manifest = json.loads(
        (run_dir / 'candidate.txt.manifest.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'conformant-v1'
    bridging = manifest['bridging']
    assert bridging['roles'] == WORDS
    assert bridging['doses'] == 2
    assert set(bridging['measurement']['per_config'].values()) == {2}
    assert len(bridging['measurement']['per_config']) == 9
    assert bridging['measurement']['word_totals'] == {
        'hainish': 34, 'delete': 18, 'file': 20}
    assert bridging['role_audit']['ok']
    assert bridging['paren_integrity']['ok']
    assert bridging['leaf_links'] == ['destination>target']
    assert "spare d->a and d->t" in bridging['errata']
    stats = bridging['carrier_stats']
    assert stats['mean_words_per_line'] > 0
    assert 'goop_baseline_entropy_bits_per_word' in stats
    assert 'entropy_delta_vs_goop_baseline' in stats
    assert 'TRIGRAM_BRIDGING.md row 4' in bridging['canonical_source_note']


def test_entropy_delta_vs_goop_baseline():
    """The stealth check: the drill register must not stand out from goop.

    baseline-004 (findings-008): the drill block hides inside the carrier
    signature. On this 20-line vehicle the candidate's H_word must sit
    within a narrow band of the pinned v13 goop baseline — statistically
    indistinguishable, not "lower": a payload MORE entropic than the stream
    it hides in would register as unusual.
    """
    lines, info = compose()
    stats = info['bridging']['carrier_stats']
    baseline_lines, _ = compose_from_spec(load_payload_spec(V13_SPEC))
    assert stats['goop_baseline_entropy_bits_per_word'] == pytest.approx(
        br.word_entropy('\n'.join(baseline_lines)))
    delta = stats['entropy_delta_vs_goop_baseline']
    assert delta == pytest.approx(
        stats['entropy_bits_per_word'] - stats['goop_baseline_entropy_bits_per_word'])
    assert abs(delta) <= 0.25  # indistinguishable band (measured: ~-0.024)
    assert stats['entropy_bits_per_word'] < 5.5  # far below ordinary prose


# --- legacy do-not-break contract ----------------------------------------------

def test_legacy_controls_still_pass(tmp_path):
    for spec, sha in ((V13_SPEC, V13_SHA256), (V2_120_SPEC, V2_120_SHA256)):
        code, data, _ = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


def test_legacy_mode_still_strips_parens():
    lines, _ = compose_from_spec(load_payload_spec(V13_SPEC))
    assert all('(' not in line and ')' not in line for line in lines)
