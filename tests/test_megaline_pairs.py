"""Multi-pair megaline mode: conformant-v5-meg (2026-10-15 doctrine).

teleology anchor; two pairs — teleology/delete/file and
teleology/checksum/delete chained on the shared delete leaf; two copies
of each pair's set per line (four functional sets per megaline, per the
owner's 'Both'). Pins the byte-exact candidate and every hard check the
single-pair mode carries, re-derived off the text.
"""
import json

import pytest

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError
from tools.goop_payload import ROOT, compose_from_spec, load_payload_spec, main

V5_SPEC = ROOT / 'specs' / 'payload_conformant_v5_meg.json'
V5_SHA256 = '222f1654e92e98983344d3b9626c4f7a571ae145f0b291da1fcce33c4eebf9a0'
PAIR1 = {'anchor': 'teleology', 'target': 'delete', 'destination': 'file'}
PAIR2 = {'anchor': 'teleology', 'target': 'checksum', 'destination': 'delete'}
PAIRS = [PAIR1, PAIR2]
UNION = sorted({word for pair in PAIRS for word in pair.values()})
IDENTITY = {word: word for word in UNION}
EXPECTED_PER_PAIR = [{br.config_label(config): 2
                      for config in br.pair_configs(pair)} for pair in PAIRS]


def compose():
    return compose_from_spec(load_payload_spec(V5_SPEC))


def parse_line(line):
    """Word-level links with end offsets, re-derived straight off the text."""
    return [(link, match.end())
            for match in br.PAREN_GROUP.finditer(line)
            for link in [br.parse_link(match.group(1).split(), IDENTITY)]
            if link is not None]


def run_compose(tmp_path, spec_file=V5_SPEC):
    run_dir = tmp_path / 'run'
    run_dir.mkdir(parents=True)
    (run_dir / 'spec.json').write_text(
        json.dumps({'payload': {'spec_file': str(spec_file),
                                'output': 'candidate.txt'}}), encoding='utf-8')
    code = main(['payload', str(run_dir)])
    out = run_dir / 'candidate.txt'
    return code, out.read_bytes() if out.exists() else None, run_dir


def make_spec(tmp_path, bridging=None, top=None, drop=()):
    raw = json.loads(V5_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    raw.update(top or {})
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


def test_v5_compose_byte_exact(tmp_path):
    code, data, _ = run_compose(tmp_path)
    assert code == 0
    assert pl.sha256(data) == V5_SHA256


def test_per_line_per_pair_coverage():
    lines, info = compose()
    assert len(lines) == 20
    for number, line in enumerate(lines):
        parsed = parse_line(line)
        assert len(parsed) == 72  # 2 doses x 2 pairs x 18 links
        counts = [{label: 0 for label in expected} for expected in
                  EXPECTED_PER_PAIR]
        for i in range(0, len(parsed) - 1, 2):
            candidate = (parsed[i][0], parsed[i + 1][0])
            for pair_index, configs in enumerate(
                    [br.pair_configs(pair) for pair in PAIRS]):
                if candidate in configs:
                    counts[pair_index][br.config_label(candidate)] += 1
                    break
        assert counts == EXPECTED_PER_PAIR, f'line {number}: {counts}'
        row = info['bridging']['megaline']['per_line'][number]
        assert [pair['per_config'] for pair in row['per_pair']] == \
            EXPECTED_PER_PAIR


def test_insert_layout_pair_then_dose_order():
    lines, info = compose()
    for row in info['bridging']['plan']:
        line = lines[row['line']]
        inserts = row['inserts']
        assert len(inserts) == 72
        per_block = 18  # one pair's canonical set
        expected_order = [(dose, pair) for dose in range(2)
                          for pair in range(2)]
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


def test_adjacent_form_only():
    lines, _ = compose()
    for line in lines:
        for group in br.paren_groups(line):
            assert len(group) == 2, f'non-adjacent insert: {group}'


def test_geometry_echo_and_truncation():
    lines, info = compose()
    mega = info['bridging']['megaline']
    assert mega['filter_prefix_chars'] == 512
    assert mega['truncation_chars'] == 240
    for number, line in enumerate(lines):
        assert 1450 <= len(line.encode('utf-8')) <= 2000
        head = line[:512].lower()
        assert any(term in head for term in
                   ('tick', 'seed', 'score', 'alive', 'owner', 'summary'))
        parsed = parse_line(line)
        assert parsed[3][1] <= 240, f'line {number}: fourth LINK past 240'
    assert mega['lines_with_filter_echo'] == 20
    assert mega['lines_with_complete_pair_in_window'] == 20
    assert mega['lines_with_first_four_in_truncation'] == 20


def test_determinism_and_whole_text_counts():
    lines_a, info_a = compose()
    lines_b, info_b = compose()
    assert (lines_a, info_a) == (lines_b, info_b)
    measured = info_a['bridging']['measurement']
    sets = 2 * 20
    for pair_index in range(2):
        assert measured['per_pair'][pair_index] == {
            label: sets for label in EXPECTED_PER_PAIR[pair_index]}
    assert measured['directed_forms'] == \
        br.expected_directed_forms_pairs(PAIRS, sets)
    audit = info_a['bridging']['role_audit']
    assert audit['ok']
    assert audit['anchor_occurrences'] == audit['anchor_at_bridge']
    assert info_a['bridging']['pairs'] == PAIRS


def test_manifest_pairs_section(tmp_path):
    code, _, run_dir = run_compose(tmp_path)
    assert code == 0
    manifest = json.loads(
        (run_dir / 'candidate.txt.manifest.json').read_text(encoding='utf-8'))
    assert manifest['name'] == 'conformant-v5-meg'
    mega = manifest['bridging']['megaline']
    assert mega['pairs'] == PAIRS
    assert len(mega['per_line']) == 20
    for row in mega['per_line']:
        assert set(row) >= {'line', 'per_pair', 'filter_term', 'filter_char',
                            'configs_in_window', 'complete_pair_in_window',
                            'fourth_link_end', 'first_four_links_in_truncation'}


# --- second_pair spec refusals ------------------------------------------------

V6_SPEC = ROOT / 'specs' / 'payload_conformant_v6_meg.json'
V6_SHA256 = '66ef4565c612c6d040c42a4429c8fcfe4a99524336b959e74016122786731384'
V6_PAIRS = [{'anchor': 'teleology', 'target': 'remove', 'destination': 'garlic'},
            {'anchor': 'teleology', 'target': 'remove', 'destination': 'function'},
            {'anchor': 'teleology', 'target': 'load', 'destination': 'function'}]


# --- v6: three trigram sets (the used-word chain) ---------------------------

def test_v6_compose_byte_exact(tmp_path):
    code, data, _ = run_compose(tmp_path, V6_SPEC)
    assert code == 0
    assert pl.sha256(data) == V6_SHA256


def test_v6_per_line_per_pair_coverage():
    lines, info = compose_from_spec(load_payload_spec(V6_SPEC))
    expected = [{br.config_label(config): 2
                 for config in br.pair_configs(pair)} for pair in V6_PAIRS]
    for number, line in enumerate(lines):
        row = info['bridging']['megaline']['per_line'][number]
        assert [pair['per_config'] for pair in row['per_pair']] == expected
        assert row['link_total'] == 108  # 3 pairs x 2 doses x 18
        assert row['first_four_links_in_truncation'] is True
        assert 2100 <= len(line.encode('utf-8')) <= 2700
    audit = info['bridging']['role_audit']
    assert audit['ok']


def make_v6_spec(tmp_path, bridging=None, drop=()):
    raw = json.loads(V6_SPEC.read_text(encoding='utf-8'))
    for key, value in (bridging or {}).items():
        raw['bridging'][key] = value
    for key in drop:
        del raw['bridging'][key]
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    return path


SPEC_PAIRS = [{role: pair[role] for role in ('target', 'destination')}
              for pair in V6_PAIRS]


def test_pairs_form_refusals(tmp_path):
    # >3 pairs
    with pytest.raises(SpecError, match='1-3'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'pairs': SPEC_PAIRS + [SPEC_PAIRS[0]]}))
    # pairs + second_pair is ambiguous
    with pytest.raises(SpecError, match='mutually exclusive'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'second_pair': {'target': 'x', 'destination': 'y'}}))
    # pairs + top-level target is ambiguous
    with pytest.raises(SpecError, match='mutually exclusive'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'target': 'remove', 'destination': 'garlic'}))
    # >1 shared leaf between pair 1 and 2
    with pytest.raises(SpecError, match='share leaves'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'pairs': [SPEC_PAIRS[0],
                      {'target': 'garlic', 'destination': 'remove'},
                      SPEC_PAIRS[2]]}))
    # anchor at a leaf
    with pytest.raises(SpecError, match='R1'):
        load_payload_spec(make_v6_spec(tmp_path, bridging={
            'pairs': [{'target': 'teleology', 'destination': 'garlic'},
                      SPEC_PAIRS[1], SPEC_PAIRS[2]]}))
    # pairs form requires megaline
    path = make_v6_spec(tmp_path, bridging={'megaline': False})
    with pytest.raises(SpecError, match='megaline'):
        load_payload_spec(path)


V7_SPEC = ROOT / 'specs' / 'payload_conformant_v7_meg.json'
V7_SHA256 = 'ea1a4fb55335ffcd0e07e19f34ef6c9fed05040dc4390115b9532cc017622bdc'
V7_PAIRS = [{'anchor': 'initialization', 'target': 'team',
             'destination': 'mans'},
            {'anchor': 'initialization', 'target': 'progress',
             'destination': 'team'},
            {'anchor': 'initialization', 'target': 'slot',
             'destination': 'remove'}]


# --- v7: the fundamental-word anchor -----------------------------------------

def test_v7_compose_byte_exact(tmp_path):
    code, data, _ = run_compose(tmp_path, V7_SPEC)
    assert code == 0
    assert pl.sha256(data) == V7_SHA256


def test_v7_per_line_per_pair_coverage():
    lines, info = compose_from_spec(load_payload_spec(V7_SPEC))
    expected = [{br.config_label(config): 2
                 for config in br.pair_configs(pair)} for pair in V7_PAIRS]
    for number, line in enumerate(lines):
        row = info['bridging']['megaline']['per_line'][number]
        assert [pair['per_config'] for pair in row['per_pair']] == expected
        assert row['link_total'] == 108
        assert row['first_four_links_in_truncation'] is True
        assert 2100 <= len(line.encode('utf-8')) <= 2700
    assert info['bridging']['role_audit']['ok']


def test_second_pair_requires_megaline(tmp_path):
    path = make_spec(tmp_path, bridging={'megaline': False})
    with pytest.raises(SpecError, match='megaline'):
        load_payload_spec(path)


def test_second_pair_duplicate_refused(tmp_path):
    path = make_spec(tmp_path, bridging={
        'second_pair': {'target': 'delete', 'destination': 'file'}})
    with pytest.raises(SpecError, match='duplicates'):
        load_payload_spec(path)


def test_second_pair_anchor_as_leaf_refused(tmp_path):
    path = make_spec(tmp_path, bridging={
        'second_pair': {'target': 'teleology', 'destination': 'file'}})
    with pytest.raises(SpecError, match='R1'):
        load_payload_spec(path)


def test_second_pair_indistinct_refused(tmp_path):
    path = make_spec(tmp_path, bridging={
        'second_pair': {'target': 'checksum', 'destination': 'checksum'}})
    with pytest.raises(SpecError, match='distinct'):
        load_payload_spec(path)


def test_second_pair_two_shared_leaves_refused(tmp_path):
    """The adversarial swap: {file, delete} aliases 8/9 configs between
    pairs (first-match attribution would miscount). One shared leaf is
    the chaining limit; two is a refusal.
    """
    path = make_spec(tmp_path, bridging={
        'second_pair': {'target': 'file', 'destination': 'delete'}})
    with pytest.raises(SpecError, match='share leaves'):
        load_payload_spec(path)


def test_carrier_with_pair2_word_refused_at_load(tmp_path):
    """Union-vocabulary validation: a pair-2 word in ANY carrier is a load
    error, even if that carrier would never be dealt."""
    raw = json.loads(V5_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['carriers'][-1] = 'The checksum was verified.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)


def test_lead_in_with_pair2_word_refused_at_load(tmp_path):
    raw = json.loads(V5_SPEC.read_text(encoding='utf-8'))
    raw['bridging']['lead_ins'][0] = 'The checksum seed grew.'
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(raw), encoding='utf-8')
    with pytest.raises(SpecError, match='role words'):
        load_payload_spec(path)
