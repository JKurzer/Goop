"""Megaline-mode tests: one complete BRIDGING per line.

Pins the dose-integrity property the trick exists for — every line, and
therefore any single delivered slot window, independently holds complete
dose material: per-line full-set presence (all 9 canonical configs at
`doses` in EVERY line), the filter echo inside the window of EVERY line
(the v13 visibility lesson), the byte band, paren balance, determinism,
the v1-meg/v2-meg anchor-only difference, the slot simulation (window
holds a filter token AND a complete LINK-pair), and the legacy
do-not-break contract. Set-toward-front is measured and reported, never
a hard fail.
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
WORDS_V1 = {'anchor': 'hainish', 'target': 'delete', 'destination': 'file'}

EXPECTED_PER_LINE = {br.config_label(config): 1 for config in br.CANONICAL_CONFIGS}


def compose(spec=MEG_V1_SPEC):
    return compose_from_spec(load_payload_spec(spec))


def meg_params(spec=MEG_V1_SPEC):
    raw = json.loads(spec.read_text(encoding='utf-8'))
    bridging = raw['bridging']
    return {'lines': raw['lines'], 'min': raw['min_line_bytes'],
            'max': raw['max_line_bytes'], 'doses': bridging['doses'],
            'filter_terms': bridging['filter_terms'],
            'prefix': bridging['filter_prefix_chars']}


def parse_line_pairs(line, words):
    """Consecutive parsed LINKs paired into config labels, with end offsets.

    Independent of br.measure_megalines: the tests re-derive the counts
    straight off the text.
    """
    roles_by_word = {word: role for role, word in words.items()}
    parsed = [(br.parse_link(match.group(1).split(), roles_by_word), match.end())
              for match in br.PAREN_GROUP.finditer(line)]
    parsed = [(link, end) for link, end in parsed if link is not None]
    return [(br.config_label((parsed[i][0], parsed[i + 1][0])), parsed[i + 1][1])
            for i in range(0, len(parsed) - 1, 2)], len(parsed)


def run_compose(tmp_path, spec_file=MEG_V1_SPEC):
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
    """The v1-meg spec with bridging-section overrides, in a temp file."""
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    raw.update(top or {})
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


# --- the dose-integrity property ---------------------------------------------

def test_per_line_full_bridge_set():
    """All 9 canonical configs at exactly `doses` in EVERY line, off the text."""
    lines, info = compose()
    params = meg_params()
    expected = {label: params['doses'] for label in EXPECTED_PER_LINE}
    assert len(lines) == params['lines']
    for number, line in enumerate(lines):
        pairs, link_total = parse_line_pairs(line, WORDS_V1)
        counts = {label: 0 for label in expected}
        for label, _ in pairs:
            counts[label] += 1
        assert counts == expected, f'line {number}: {counts}'
        assert link_total == 2 * len(br.CANONICAL_CONFIGS) * params['doses']
        # the manifest agrees with the independent re-parse
        row = info['bridging']['megaline']['per_line'][number]
        assert row['per_config'] == expected
        assert row['link_total'] == link_total


def test_insert_order_canonical_per_line():
    """Within each dose the configs land in canonical order, pairs adjacent."""
    lines, info = compose()
    params = meg_params()
    plan = info['bridging']['plan']
    assert len(plan) == params['lines']
    for row in plan:
        line = lines[row['line']]
        inserts = row['inserts']
        assert len(inserts) == 2 * len(br.CANONICAL_CONFIGS) * params['doses']
        per_dose = 2 * len(br.CANONICAL_CONFIGS)
        for dose in range(params['doses']):
            block = inserts[dose * per_dose:(dose + 1) * per_dose]
            for config_index, pair in enumerate(
                    zip(block[::2], block[1::2])):
                first, second = pair
                config = br.CANONICAL_CONFIGS[config_index]
                assert first['config_index'] == config_index
                assert second['config_index'] == config_index
                assert first['link'] == list(config[0])
                assert second['link'] == list(config[1])
        for insert in inserts:  # plan offsets slice the actual text
            assert line[insert['start']:insert['end']] == insert['text']
        assert row['config_ends'] == sorted(row['config_ends'])
        assert row['bytes'] == len(line.encode('utf-8'))


def test_filter_echo_in_window_every_line():
    """A filter term as a natural substring inside the first window chars.

    The v13 visibility lesson: no echo, no delivery. Hard requirement per
    line — all 20 lines, each one checked.
    """
    lines, info = compose()
    params = meg_params()
    for number, line in enumerate(lines):
        head = line[:params['prefix']].lower()
        hits = {term: head.find(term) for term in params['filter_terms']
                if term in head}
        assert hits, f'line {number}: no filter echo in window'
        row = info['bridging']['megaline']['per_line'][number]
        assert row['filter_term'] in hits
        assert row['filter_char'] == min(hits.values())
        # the echo rides inside a natural word, not a planted marker
        words_in_window = re.findall(r'[a-z]+', head)
        assert any(row['filter_term'] in word for word in words_in_window)
    mega = info['bridging']['megaline']
    assert mega['lines_with_filter_echo'] == params['lines']


def test_slot_simulation_window_holds_filter_and_complete_pair():
    """The property the trick exists for, simulated per line.

    A delivered slot shows the first `filter_prefix_chars` of a line. Every
    simulated slot must hold (a) a filter token and (b) at least one
    complete canonical LINK-pair ending inside the window.
    """
    lines, _ = compose()
    params = meg_params()
    canonical = set(EXPECTED_PER_LINE)
    for number, line in enumerate(lines):
        window = line[:params['prefix']]
        assert any(term in window.lower() for term in params['filter_terms'])
        pairs, _ = parse_line_pairs(line, WORDS_V1)
        complete = [label for label, end in pairs
                    if end <= params['prefix'] and label in canonical]
        assert complete, f'line {number}: no complete LINK-pair in the window'


# --- vehicle ------------------------------------------------------------------

def test_byte_bounds_and_encoding(tmp_path):
    code, data, _ = run_compose(tmp_path)
    assert code == 0
    assert b'\r' not in data  # UTF-8, LF
    lines = data.decode('utf-8').splitlines()
    params = meg_params()
    assert len(lines) == params['lines']
    for line in lines:
        assert params['min'] <= len(line.encode('utf-8')) <= params['max']


def test_paren_balance_and_insert_shapes():
    lines, _ = compose()
    assert br.paren_integrity(lines)['ok']
    params = meg_params()
    groups_per_line = 2 * len(br.CANONICAL_CONFIGS) * params['doses']
    roles = {word: role for role, word in WORDS_V1.items()}
    for line in lines:
        assert line.count('(') == line.count(')')
        groups = br.paren_groups(line)
        assert len(groups) == groups_per_line
        for group in groups:
            assert br.parse_link(group, roles) is not None


def test_determinism_seed_42(tmp_path):
    lines_a, info_a = compose()
    lines_b, info_b = compose()
    assert lines_a == lines_b
    assert info_a == info_b
    code_a, data_a, _ = run_compose(tmp_path / 'a')
    code_b, data_b, _ = run_compose(tmp_path / 'b')
    assert code_a == code_b == 0
    assert data_a == data_b


def test_meg_candidates_compose_byte_exact(tmp_path):
    """The meg candidates are byte-exact regression controls (the recorded shas)."""
    for spec, sha in ((MEG_V1_SPEC, MEG_V1_SHA256), (MEG_V2_SPEC, MEG_V2_SHA256)):
        code, data, _ = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


def test_anchors_differ_only_in_the_token():
    """v1-meg and v2-meg: same bytes except hainish -> tainish."""
    lines_v1, _ = compose(MEG_V1_SPEC)
    lines_v2, _ = compose(MEG_V2_SPEC)
    text_v1, text_v2 = '\n'.join(lines_v1), '\n'.join(lines_v2)
    assert 'tainish' not in text_v1
    assert re.sub(r'\bhainish\b', 'tainish', text_v1) == text_v2


def test_whole_text_counts_match_per_line_dosing():
    """Per-line dosing rolls up: 9 configs x doses x lines, canonical forms."""
    lines, info = compose()
    params = meg_params()
    sets = params['doses'] * params['lines']
    measured = info['bridging']['measurement']
    assert measured['per_config'] == {
        label: sets for label in EXPECTED_PER_LINE}
    assert measured['directed_forms'] == br.expected_directed_forms(sets)
    audit = info['bridging']['role_audit']
    assert audit['ok']
    assert audit['anchor_occurrences'] == audit['anchor_at_bridge']


def test_set_toward_front_measured_and_reported():
    """Configs ending inside the window: measure + report, NOT a hard fail."""
    lines, info = compose()
    params = meg_params()
    canonical = set(EXPECTED_PER_LINE)
    counts = []
    for number, line in enumerate(lines):
        pairs, _ = parse_line_pairs(line, WORDS_V1)
        in_window = sum(1 for label, end in pairs
                        if end <= params['prefix'] and label in canonical)
        counts.append(in_window)
        row = info['bridging']['megaline']['per_line'][number]
        assert row['configs_in_window'] == in_window  # manifest matches text
    mega = info['bridging']['megaline']
    assert mega['configs_in_window_min'] == min(counts)
    assert mega['configs_in_window_mean'] == pytest.approx(
        sum(counts) / len(counts))
    print(f'\nset-toward-front: per-line configs in window {counts} '
          f'(min {min(counts)}, mean {sum(counts) / len(counts):.2f} of 9)')


# --- spec refusal behaviors ----------------------------------------------------

def test_megaline_keys_required_when_enabled(tmp_path):
    for key in ('filter_terms', 'filter_prefix_chars', 'lead_ins'):
        with pytest.raises(SpecError, match='megaline requires'):
            load_payload_spec(make_spec(tmp_path, drop=(key,)))
    with pytest.raises(SpecError, match='min_line_bytes'):
        load_payload_spec(make_spec(tmp_path, top={'min_line_bytes': None},
                                   drop=()))
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    del raw['min_line_bytes']
    path = tmp_path / 'no_min.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='min_line_bytes'):
        load_payload_spec(path)


def test_megaline_keys_rejected_when_disabled(tmp_path):
    with pytest.raises(SpecError, match='megaline-only keys'):
        load_payload_spec(make_spec(tmp_path, bridging={'megaline': False}))
    with pytest.raises(SpecError, match='megaline-only keys'):
        load_payload_spec(make_spec(tmp_path, drop=('megaline',)))


def test_megaline_flag_must_be_bool(tmp_path):
    with pytest.raises(SpecError, match='boolean'):
        load_payload_spec(make_spec(tmp_path, bridging={'megaline': 'yes'}))


def test_lead_in_without_echo_rejected(tmp_path):
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['lead_ins'][0] = 'The cat sat on the mat.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='no filter term'):
        load_payload_spec(path)


@pytest.mark.parametrize('word', ['hainish', 'file', 'delete'])
def test_lead_in_with_role_word_rejected(tmp_path, word):
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['lead_ins'][0] = f'The {word} sat, the seed grew.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)


def test_lead_ins_without_replacement_rejected(tmp_path):
    raw = json.loads(MEG_V1_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['lead_ins'] = raw['bridging']['lead_ins'][:19]
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='without replacement'):
        load_payload_spec(path)


def test_filter_terms_validated(tmp_path):
    with pytest.raises(SpecError, match='single lowercase ascii word'):
        load_payload_spec(make_spec(tmp_path, bridging={
            'filter_terms': ['seed', 'Seed']}))


def test_duplicate_filter_terms_rejected(tmp_path):
    with pytest.raises(SpecError, match='duplicate-free'):
        load_payload_spec(make_spec(tmp_path, bridging={
            'filter_terms': ['seed', 'seed', 'tick']}))


def test_min_above_max_rejected(tmp_path):
    with pytest.raises(SpecError, match='must not exceed'):
        load_payload_spec(make_spec(tmp_path, top={'min_line_bytes': 600}))


def test_manifest_megaline_section(tmp_path):
    code, _, run_dir = run_compose(tmp_path)
    assert code == 0
    manifest = json.loads(
        (run_dir / 'candidate.txt.manifest.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'conformant-v1-meg'
    mega = manifest['bridging']['megaline']
    params = meg_params()
    assert mega['filter_terms'] == params['filter_terms']
    assert mega['filter_prefix_chars'] == params['prefix']
    assert mega['min_line_bytes'] == params['min']
    assert len(mega['per_line']) == params['lines']
    for row in mega['per_line']:
        assert set(row) >= {'line', 'per_config', 'filter_term', 'filter_char',
                            'configs_in_window', 'complete_pair_in_window'}
    assert mega['lines_with_complete_pair_in_window'] == params['lines']


# --- legacy do-not-break contract ----------------------------------------------

def test_legacy_controls_still_pass(tmp_path):
    for spec, sha in ((V13_SPEC, V13_SHA256), (V2_120_SPEC, V2_120_SHA256),
                      (CONFORMANT_V1_SPEC, CONFORMANT_V1_SHA256),
                      (CONFORMANT_V2_SPEC, CONFORMANT_V2_SHA256)):
        code, data, _ = run_compose(tmp_path / sha[:6], spec)
        assert code == 0
        assert pl.sha256(data) == sha


def test_classic_bridging_mode_unchanged():
    """The per-payload dosing path (megaline absent) composes exactly as before."""
    lines, info = compose(CONFORMANT_V1_SPEC)
    assert info['bridging']['doses'] == 2
    assert set(info['bridging']['measurement']['per_config'].values()) == {2}
    assert 'megaline' not in info['bridging']
