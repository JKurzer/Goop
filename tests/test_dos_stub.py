"""Actual LINK /STUB smoke test; no model calls or fired artifacts."""
import hashlib
import json
import os
import struct
import subprocess
from pathlib import Path

import pefile
import pytest

from gooplib import GoopError
from gooplib.dos_stub import make_dos_stub
from gooplib.native_build import build_pair
from gooplib.native_stage import stage_pair
from gooplib.specs import build_section, metadata_texts, payload_lines

VCVARS = Path(r'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat')


def test_stub_is_real_mz_and_preserves_long_text():
    text = 'A' * 1024
    stub = make_dos_stub(text)
    assert stub[:2] == b'MZ'
    assert len(stub) > 1024
    assert stub[78:78 + len(text) + 1] == text.encode() + b'$'
    assert struct.unpack_from('<I', stub, 0x3c)[0] == len(stub)


@pytest.mark.parametrize('text', ['', 'has $ sentinel', 'bad\nline', 'é', 'x' * 16385])
def test_stub_refuses_lossy_content(text):
    with pytest.raises(GoopError):
        make_dos_stub(text)


def test_canonical_160_arm_has_one_pinned_candidate():
    root = Path(__file__).resolve().parents[1] / 'runs' / 'conformant-v11-160-metadata'
    spec = json.loads((root / 'spec.json').read_text(encoding='utf-8'))
    build = build_section(spec)
    candidate = root / 'inputs' / 'candidate.txt'
    assert hashlib.sha256(candidate.read_bytes()).hexdigest() == build['payload_sha256']
    assert 'spec_file' not in spec['payload']
    assert spec['fire']['cells'] == ['RunB']
    lines = payload_lines(candidate, build)
    assert len(lines) == 160 and lines[:80] == lines[80:]
    assert metadata_texts(build, lines, 'RunA') == (None, None)
    stub, pdb = metadata_texts(build, lines, 'RunB')
    assert stub == ' '.join(lines[index].decode('ascii') for index in range(4))
    components = pdb.split('\\')
    assert len(components) == 3 and components[-1] == 'debug.pdb'
    for component, index in zip(components[:2], (4, 5)):
        assert component.endswith(')') and len(component) <= 88
        assert lines[index].decode('ascii').startswith(component)


def test_zero_dose_rejects_poisoned_stub():
    spec = {'payload': {'sha256': '0' * 64},
            'build': {'slots': 2, 'slot_size': 256,
                      'doses': {'RunA': 0, 'RunB': 2},
                      'dos_stub': {'RunA': [0], 'RunB': [1]}}}
    with pytest.raises(GoopError, match='zero-dose controls'):
        build_section(spec)


@pytest.mark.skipif(os.name != 'nt' or not VCVARS.is_file(),
                    reason='requires local MSVC linker')
def test_linker_builds_real_executable_with_long_stub(tmp_path):
    text = 'A_REAL_DOS_STUB_' + 'ABCD' * 256
    (tmp_path / 'dos-stub.exe').write_bytes(make_dos_stub(text))
    (tmp_path / 'main.cpp').write_text('int main() { return 0; }', encoding='ascii')
    command = (f'call "{VCVARS}" >nul && cl /nologo /EHsc main.cpp '
               '/Fe:target.exe /link /STUB:dos-stub.exe')
    result = subprocess.run(command, shell=True, cwd=tmp_path,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    binary = (tmp_path / 'target.exe').read_bytes()
    pe = pefile.PE(data=binary)
    assert pe.DOS_HEADER.e_lfanew > 1024
    assert text.encode() in binary[:pe.DOS_HEADER.e_lfanew]
    process = subprocess.run([str(tmp_path / 'target.exe')], timeout=10)
    assert process.returncode == 0
    rizin = Path.home() / 'tools/rizin/bin/rz-bin.exe'
    if rizin.is_file():
        result = subprocess.run([str(rizin), '-zz', str(tmp_path / 'target.exe')],
                                capture_output=True, timeout=30)
        assert result.returncode == 0
        assert text.encode('ascii') in result.stdout


@pytest.mark.skipif(os.name != 'nt' or not VCVARS.is_file(),
                    reason='requires local MSVC linker')
def test_goop_pair_stage_preserves_real_dos_stub(tmp_path, monkeypatch):
    monkeypatch.setenv('GOOP_VCVARS', str(VCVARS))
    text = 'LOCAL_UNFIRED_DOS_PROBE_' + 'ABCD' * 256
    pdb_text = 'LOCAL_UNFIRED_PDB_PROBE_' + 'EFGH' * 256
    payload = (text + '\n' + pdb_text + '\n').encode('ascii')
    (tmp_path / 'inputs').mkdir()
    (tmp_path / 'inputs' / 'candidate.txt').write_bytes(payload)
    spec = {'arm': 'local-dos-stub-test',
            'payload': {'path': 'inputs/candidate.txt',
                        'sha256': hashlib.sha256(payload).hexdigest()},
            'build': {'slots': 2, 'slot_size': 2048,
                      'doses': {'RunA': 0, 'RunB': 2},
                      'dos_stub': {'RunA': None, 'RunB': [0]},
                      'pdb_lines': {'RunA': None, 'RunB': [1]}},
            'pack': {}}
    (tmp_path / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
    built = build_pair(tmp_path, spec)
    assert all(built['checks'].values())
    with pytest.raises(GoopError, match='PDB-line injection is not supported'):
        stage_pair(tmp_path, spec)
    assert not (tmp_path / 'cells').exists()
    spec['build']['pdb_lines'] = None
    staged = stage_pair(tmp_path, spec)
    assert all(staged['checks'].values())
    for name in spec['build']['doses']:
        binary = (tmp_path / 'cells' / name / 'target.exe').read_bytes()
        assert binary == (tmp_path / 'unpacked/cells' / name / 'target.exe').read_bytes()
        region = binary[:pefile.PE(data=binary).DOS_HEADER.e_lfanew]
        assert (text.encode() in region) == (name == 'RunB')
