"""Short native cargo strings survive the actual Rizin/runner line boundary.

Tests compile synthetic local fixtures only. No experiment/model launches.
"""
import json
from pathlib import Path
import re
import subprocess

import pytest

from conftest import make_run, requires_msvc
from gooplib.evidence import content_events
from gooplib.exports import count_visible
from gooplib.native_build import build_pair
from gooplib.specs import build_section

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / 'specs/run_conformant_v9_meg.json'


def cargo_entries():
    return json.loads(BASIS.read_text(encoding='utf-8'))['build']['strings']


def test_current_basis_chunks_fit_and_keep_complete_link_pairs():
    spec = json.loads(BASIS.read_text(encoding='utf-8'))
    build_section(spec)
    entries = spec['build']['strings']
    for entry in entries:
        name, text = entry['name'], entry['text']
        assert '\n' not in text and '\r' not in text
        assert 0 < len(text.encode('ascii')) <= 120
        assert len('0x140000000 ' + repr(text.encode('ascii'))) <= 200
        if name.startswith(('full_graph_l', 'graph_pair_')):
            assert len(text.split()) % 4 == 0
        elif name.startswith('full_graph_directed_l'):
            assert len(re.findall(r'\S+>\S+', text)) % 2 == 0


def test_existing_visibility_counts_independent_chunks_not_echo():
    entries = cargo_entries()[:2]
    session = {'messages': [{'parts': [
        {'part_kind': 'tool-call', 'args': {'command': entries[0]['text']}},
        {'part_kind': 'tool-return', 'content': {
            'command': entries[0]['text'], 'stdout': '0x1000 ' + entries[1]['text']}},
    ]}]}
    text = '\n'.join(content_events(session))
    assert count_visible([entries[1]['text']], text)['occurrences'] == 1
    assert count_visible([entries[0]['text']], text)['occurrences'] == 0


@requires_msvc
def test_chunks_are_nul_terminated_and_referenced(tmp_path):
    entries = cargo_entries()
    run, spec = make_run(tmp_path, 'chunked-cargo', 2, 256,
                         {'RunA': 1, 'RunB': 2}, 120, strings=entries)
    manifest = build_pair(run, spec)
    assert all(manifest['checks'].values())
    for cell in ('RunA', 'RunB'):
        image = (run/'unpacked/cells'/cell/'target.exe').read_bytes()
        printable = re.findall(rb'[\x20-\x7e]{5,}', image)
        for entry in entries:
            expected = entry['text'].encode('ascii')
            assert expected + b'\x00' in image
            assert expected in printable
        info = manifest['strings']['per_cell'][cell]
        assert info['contents_exact']
        assert info['referenced'] == len(entries)
        assert info['referenced_in_main'] == len(entries)
    scanner = Path.home() / 'tools/rizin/bin/rz-bin.exe'
    if not scanner.is_file():
        pytest.skip('Byte checks passed; Rizin unavailable for scanner integration')
    result = subprocess.run([str(scanner), '-z',
                             str(run/'unpacked/cells/RunB/target.exe')],
                            capture_output=True, check=True, timeout=60)
    text = result.stdout.decode('utf-8', errors='replace')
    # Rizin decorates rows with ANSI colors and VA/offset columns.
    rows = [(raw, re.sub(r'\x1b\[[0-9;]*m', '', raw)) for raw in text.splitlines()]
    for entry in entries:
        matching = [raw for raw, plain in rows if entry['text'] in plain]
        assert matching, entry['name']
        # The runner truncates raw output, BEFORE stripping ANSI decorations.
        assert any(len(row) <= 256 for row in matching), matching
