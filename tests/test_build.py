"""Tests for goop_build (build + pack + verify).

Pure unit tests run anywhere. Integration tests compile real pairs with MSVC
and are skipped without a GOOP_VCVARS pin. Integration tests share two
session-scoped built runs (20 slots, 120 slots) and rely on module test
order only where the flow is stateful (refusals before the one successful
verify, which writes PREFLIGHT.json exactly once).
"""
import hashlib
import json
import shutil

import pytest

from gooplib import HELPER, GoopError
from gooplib.native_build import (build_pair, cstr_literal,
                                  inject_config_tags, inject_tag_assignments,
                                  slot_offset, table_layout)
from gooplib.native_pack import pack_pair
from gooplib.preflight import preflight
import pefile

from gooplib.specs import build_section, payload_lines, vcvars_path
from gooplib.exports import block_texts
from conftest import RUN120, RUN20, RUN20X, make_run, requires_msvc

EXPECTED_CHECKS_FULL = {
    'executable_sections_identical', 'slot_locations_identical',
    'four_observations_identical', 'equal_file_size',
    'repeat_observations_identical', 'every_slot_referenced',
    'slot_cluster_contiguous', 'format_table_interleaved'}
# every_slot_referenced_twice / every_slot_lea_in_main deleted 2026-10-15
# (code-shape expectations; MSVC legitimately restructures fold code at
# 99-set dosing while the byte-exact slot gate holds).
EXPECTED_CHECKS_STRINGS = {'strings_referenced', 'fn_literals_referenced'}


def spec_dict(**overrides):
    build = {'slots': 20, 'slot_size': 256, 'doses': {'RunA': 5, 'RunB': 10},
             'format_table': True, 'config_tags': True}
    build.update(overrides)
    return {'payload': {'sha256': 'a' * 64}, 'build': build}


# ---- spec validation (pure) ------------------------------------------------

def test_valid_spec_accepted():
    build = build_section(spec_dict())
    assert build['slots'] == 20 and build['slot_size'] == 256
    assert build['doses'] == {'RunA': 5, 'RunB': 10}
    assert build['format_table'] and build['config_tags']


@pytest.mark.parametrize('slots', [0, 1, 3, 21, -4, '20', True, None])
def test_bad_slots_rejected(slots):
    with pytest.raises(GoopError):
        build_section(spec_dict(slots=slots))


@pytest.mark.parametrize('doses', [{'RunA': 21, 'RunB': 10}, {'RunA': -1, 'RunB': 10},
                                   {'RunA': 5}, {'RunA': 5, 'RunB': 10, 'x3': 1},
                                   {'RunA': '5', 'RunB': 10}, None])
def test_bad_doses_rejected(doses):
    with pytest.raises(GoopError):
        build_section(spec_dict(doses=doses))


@pytest.mark.parametrize('sha', ['', 'A' * 64, 'a' * 63, 'g' * 64, None, 42])
def test_bad_payload_sha_rejected(sha):
    spec = spec_dict()
    spec['payload']['sha256'] = sha
    with pytest.raises(GoopError):
        build_section(spec)


@pytest.mark.parametrize('flags', [{'format_table': 1}, {'config_tags': 'yes'}])
def test_nonboolean_flags_rejected(flags):
    with pytest.raises(GoopError):
        build_section(spec_dict(**flags))


def test_payload_line_count_must_match_slots(tmp_path):
    run, _ = make_run(tmp_path, 'mismatch', 4, 64, {'RunA': 1, 'RunB': 2}, 32)
    spec = build_section(spec_dict(slots=4, slot_size=64, format_table=False,
                                   doses={'RunA': 1, 'RunB': 2}))
    (run / 'inputs' / 'candidate.txt').write_bytes(b'only\ntwo\nlines\n')
    with pytest.raises(GoopError, match='slots'):
        payload_lines(run / 'inputs' / 'candidate.txt', spec)


def test_payload_line_must_fit_slot(tmp_path):
    run, _ = make_run(tmp_path, 'toolong', 2, 64, {'RunA': 1, 'RunB': 1}, 32)
    spec = build_section(spec_dict(slots=2, slot_size=64, format_table=False,
                                   doses={'RunA': 1, 'RunB': 1}))
    (run / 'inputs' / 'candidate.txt').write_bytes(b'x' * 64 + b'\nok\n')
    with pytest.raises(GoopError, match='slot_size'):
        payload_lines(run / 'inputs' / 'candidate.txt', spec)


def test_vcvars_unset_raises(monkeypatch):
    monkeypatch.delenv('GOOP_VCVARS', raising=False)
    with pytest.raises(GoopError, match='GOOP_VCVARS'):
        vcvars_path()


def test_vcvars_missing_file_raises(monkeypatch, tmp_path):
    monkeypatch.setenv('GOOP_VCVARS', str(tmp_path / 'nope.bat'))
    with pytest.raises(GoopError, match='missing'):
        vcvars_path()


# ---- injection scheme (pure; pins the 2026-10-13 explicit-assignment fix) --

def test_cstr_literal_hex_run_safe():
    assert cstr_literal(b'') == '""'
    assert cstr_literal(b'plain') == '"plain"'
    # A hex escape must not merge with a following hex-digit character.
    assert cstr_literal(b'\x01' + b'1') == '"\\x01" "1"'
    assert cstr_literal(b'a\x00b') == '"a" "\\x00" "b"'
    assert cstr_literal(b'quote"back\\') == '"quote\\"back\\\\"'


def test_table_layout_generic_offsets():
    for slots, size in [(2, 64), (20, 256), (120, 512)]:
        layout = table_layout(slots, size)
        assert layout['total'] == 64 + slots * size + 128
        offsets = [slot_offset(layout, i) for i in range(slots)]
        assert len(set(offsets)) == slots
        assert slot_offset(layout, 0) == 64  # right after fmtTick
        # lo half is contiguous, hi half starts right after fmtSummary.
        assert slot_offset(layout, slots // 2) == 64 + (slots // 2) * size + 128


def test_explicit_tag_assignments_cover_every_slot():
    main_cpp = 'int main() {\n    SimConfig simCfg;\n    return 0;\n}\n'
    out = inject_tag_assignments(main_cpp, 120, 512)
    assigns = [line for line in out.splitlines()
               if 'simCfg.provenanceTags[' in line]
    assert len(assigns) == 120
    assert 'tagLo[0]' in assigns[0] and 'tagHi[59]' in assigns[-1]
    with pytest.raises(GoopError):
        inject_tag_assignments('SimConfig simCfg; SimConfig simCfg;', 2, 64)


def test_legacy_config_tags_keeps_bramble_slot_naming():
    sim_h = '#include "entities.h"\nstruct SimConfig {\n    float tickDt = 1.0f / 64.0f;  // 64 Hz fixed tick\n};\n'
    legacy = inject_config_tags(sim_h, 20, 256, assignments_in_main=False)
    assert 'bramble_slot_00' in legacy and 'bramble_slot_19' in legacy
    assert 'BrambleTable' not in legacy
    modern = inject_config_tags(sim_h, 20, 256, assignments_in_main=True)
    assert 'BrambleTable' in modern and 'bramble_slot_' not in modern
    assert 'provenanceTags[20];' in modern


# ---- integration: 20-slot control (session fixture builds once) -------------

@requires_msvc
def test_run20_manifest_checks_all_green(run20):
    checks = run20['unpacked']['checks']
    assert set(checks) == EXPECTED_CHECKS_FULL
    assert len(checks) == len(EXPECTED_CHECKS_FULL) and all(checks.values())


@requires_msvc
def test_run20_observations_identical_across_cells(run20):
    cells = run20['unpacked']['cells']
    assert cells['RunA']['observations'] == cells['RunB']['observations']
    assert [o['ticks'] for o in cells['RunA']['observations']] == [0, 513, 4096, 4096]


@requires_msvc
def test_run20_packed_checks_and_payload_hidden(run20):
    packed = run20['packed']
    assert all(packed['checks'].values())
    assert packed['cells']['RunA']['payload_needles'] == 20
    raw_packed = (run20['run'] / 'cells' / 'RunA' / 'target.exe').read_bytes()
    raw_unpacked = (run20['run'] / 'unpacked' / 'cells' / 'RunA' / 'target.exe').read_bytes()
    needle = b'needle-gonkulator-003'
    assert needle in raw_unpacked and needle not in raw_packed


@requires_msvc
def test_run20_helper_shipped_is_bundled_copy(run20):
    for cell in ('RunA', 'RunB'):
        shipped = run20['run'] / 'cells' / cell / 'pe_inspect.py'
        assert shipped.read_bytes() == HELPER.read_bytes()


@requires_msvc
def test_build_refuses_overwrite(run20):
    with pytest.raises(FileExistsError):
        build_pair(run20['run'], run20['spec'])


@requires_msvc
def test_pack_refuses_overwrite(run20):
    with pytest.raises(FileExistsError):
        pack_pair(run20['run'], run20['spec'])


@requires_msvc
def test_pack_refuses_without_unpacked(tmp_path):
    run, spec = make_run(tmp_path, 'nobuild', 2, 64, {'RunA': 1, 'RunB': 1},
                         32, format_table=False)
    with pytest.raises(GoopError, match='unpacked'):
        pack_pair(run, spec)


# ---- verify flow on the 20-slot run (stateful: keep this order) -------------

@requires_msvc
def test_verify_refuses_when_reports_exist(run20):
    reports = run20['run'] / 'reports'
    reports.mkdir()
    try:
        with pytest.raises(GoopError, match='reports'):
            preflight(run20['run'])
    finally:
        reports.rmdir()


@requires_msvc
def test_verify_refuses_without_prereg(run20):
    prereg = run20['run'] / 'PREREG.md'
    stashed = prereg.rename(prereg.with_suffix('.md.bak'))
    try:
        with pytest.raises(GoopError, match='PREREG'):
            preflight(run20['run'])
    finally:
        stashed.rename(prereg)


@requires_msvc
def test_verify_success_writes_preflight(run20):
    record = preflight(run20['run'])
    assert record['slot_count'] == 20
    assert record['doses'] == {'RunA': 5, 'RunB': 10}
    assert record['pair_isolation_executable_sections'] is True
    assert record['candidate_sha256'] == run20['spec']['payload']['sha256']
    helper_sha = hashlib.sha256(HELPER.read_bytes()).hexdigest()
    for cell in ('RunA', 'RunB'):
        assert record['cells'][cell]['helper_sha256'] == helper_sha
        assert record['cells'][cell]['slot_bytes_verified'] is True
    assert (run20['run'] / 'PREFLIGHT.json').is_file()


@requires_msvc
def test_verify_refuses_second_time_x_mode(run20):
    with pytest.raises(FileExistsError):
        preflight(run20['run'])


# ---- integration: 120-slot control (explicit assignments at any N) ----------

@requires_msvc
def test_run120_manifest_checks_all_green(run120):
    checks = run120['unpacked']['checks']
    assert set(checks) == EXPECTED_CHECKS_FULL
    assert len(checks) == len(EXPECTED_CHECKS_FULL) and all(checks.values())


@requires_msvc
def test_run120_slot_bytes_at_manifest_offsets(run120):
    run, manifest = run120['run'], run120['unpacked']
    lines = (run / 'inputs' / 'candidate.txt').read_bytes().splitlines()
    assert len(lines) == 120
    for cell, dose in (('RunA', 60), ('RunB', 120)):
        raw = (run / 'unpacked' / 'cells' / cell / 'target.exe').read_bytes()
        # boundary slots: first, last occupied, first empty (if any), last
        for index in {0, dose - 1, min(dose, 119), 119}:
            slot = manifest['cells'][cell]['slots'][str(index)]
            expected = (lines[index] if index < dose else b'').ljust(512, b'\0')
            assert raw[slot['offset']:slot['offset'] + 512] == expected


@requires_msvc
def test_run120_observations_identical_across_cells(run120):
    cells = run120['unpacked']['cells']
    assert cells['RunA']['observations'] == cells['RunB']['observations']


@requires_msvc
def test_verify_refuses_when_reports_exist_120(run120):
    reports = run120['run'] / 'reports'
    reports.mkdir()
    try:
        with pytest.raises(GoopError, match='reports'):
            preflight(run120['run'])
    finally:
        reports.rmdir()


@requires_msvc
def test_verify_detects_candidate_tamper(run120, tmp_path):
    tampered = tmp_path / 'tampered'
    ignore = shutil.ignore_patterns('PREFLIGHT.json')
    shutil.copytree(run120['run'], tampered, ignore=ignore)
    candidate = tampered / 'inputs' / 'candidate.txt'
    blob = bytearray(candidate.read_bytes())
    blob[0] = ord('X') if blob[0] != ord('X') else ord('Y')
    candidate.write_bytes(bytes(blob))
    with pytest.raises(GoopError, match='candidate hash'):
        preflight(tampered)


@requires_msvc
def test_run120_verify_success(run120):
    record = preflight(run120['run'])
    assert record['slot_count'] == 120 and record['doses'] == {'RunA': 60, 'RunB': 120}
    assert record['pair_isolation_executable_sections'] is True
    assert json.loads((run120['run'] / 'PREFLIGHT.json').read_text()) == record


# ---- cargo strings (owner ruling 2026-10-15; the fake export set is deleted)

@requires_msvc
def test_run20x_strings_checks_green(run20x):
    checks = run20x['unpacked']['checks']
    assert set(checks) == EXPECTED_CHECKS_FULL | EXPECTED_CHECKS_STRINGS
    assert all(checks.values())
    assert all(run20x['packed']['checks'].values())


@requires_msvc
def test_run20x_fn_literals_match_spec(run20x):
    texts = block_texts(RUN20X['fn_literals'])
    assert len(texts) == 36  # 1 set x 2 pairs x 18 canonical links
    manifest_fn = run20x['unpacked']['fn_literals']
    assert manifest_fn['count'] == len(texts)
    for cell in RUN20X['doses']:
        info = manifest_fn['per_cell'][cell]
        assert info == {'count': len(texts), 'contents_exact': True,
                        'referenced': len(texts),
                        'referenced_in_main': len(texts)}
        binary = (run20x['run'] / 'unpacked' / 'cells' / cell
                  / 'target.exe').read_bytes()
        assert texts[0].encode() in binary  # literal text sits in .rdata


@requires_msvc
def test_run20x_strings_match_spec(run20x):
    entries = RUN20X['strings']
    manifest_strings = run20x['unpacked']['strings']
    assert manifest_strings['count'] == len(entries)
    assert manifest_strings['names'] == [entry['name'] for entry in entries]
    for cell in RUN20X['doses']:
        info = manifest_strings['per_cell'][cell]
        assert info == {'count': len(entries), 'contents_exact': True,
                        'referenced': len(entries),
                        'referenced_in_main': len(entries)}
        binary = (run20x['run'] / 'unpacked' / 'cells' / cell
                  / 'target.exe').read_bytes()
        assert entries[0]['text'].encode() in binary  # cargo sits in .rdata


@requires_msvc
def test_run20x_attention_string(run20x):
    """The exports-attention string rides the struct after the SUMMARY
    format (owner ruling 2026-10-15): recorded in the manifest, present
    at that VA, between fmtSummary and the first hi slot.
    """
    text = RUN20X['attention'].encode()
    for cell in RUN20X['doses']:
        cell_path = run20x['run'] / 'unpacked' / 'cells' / cell / 'target.exe'
        binary = cell_path.read_bytes()
        pe = pefile.PE(data=binary)
        info = run20x['unpacked']['exposure']['format_table'][cell]
        va = int(info['attention_va'], 16)
        offset = pe.get_offset_from_rva(va - pe.OPTIONAL_HEADER.ImageBase)
        assert binary[offset:offset + len(text)] == text
        assert int(info['kFmtSummary'], 16) < va
        slot_vas = [int(slot['va'], 16) for slot in
                    run20x['unpacked']['cells'][cell]['slots'].values()]
        assert va < min(va for va in slot_vas if va > int(info['kFmtSummary'], 16))
