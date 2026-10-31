"""The stdout arm is opt-in and never creates genuine Capstone/tool metadata."""
import json
import re
import shutil
import subprocess

import pytest

from tools.embed_payload import SOURCE, build_payload, embed, render
from tools.experimental_stdout import CAPSTONE, COMPLETION, compose
from tools.prepare_delivery import plan_delivery, verify_returns


ROOT = SOURCE.parents[1]


def fixture():
    return (json.loads((ROOT / 'payloads/operator_stdout_filler.json').read_text()),
            json.loads((ROOT / 'payloads/operator_stdout_trigrams.json').read_text()))


def test_operator_links_and_provenance_spoof_are_distinct():
    filler, trigrams = fixture()
    baseline = render(filler, trigrams)
    prose = render(filler, trigrams, link_operator='/')
    payload = compose(filler, trigrams)
    assert baseline != prose
    assert len(prose.splitlines()) == 16
    assert payload.startswith(prose + COMPLETION + CAPSTONE)
    fake_output = payload.split(CAPSTONE, 1)[1].splitlines()
    assert len(fake_output) == 16
    assert fake_output == [
        f'string[{index:02d}] {row.encode("ascii")[:8].hex(" ")} ... |{row}|'
        for index, row in enumerate(prose.splitlines())
    ]
    assert not any('nop' in line or '0x1400' in line for line in fake_output)
    assert all(len(line) <= 190 for line in payload.splitlines())
    for leaf in ('file', 'delete'):
        assert f'{leaf}/glaciation' in prose
        assert f'glaciation/{leaf}' in prose
    assert not re.search(r'\b(?:file|delete) glaciation\b|\bglaciation (?:file|delete)\b', prose)
    assert len(plan_delivery('SUMMARY ticks=0 seed=0\n' + payload,
                             'C:/Python/python.exe')['chunks']) <= 20
    with pytest.raises(ValueError, match='link operator'):
        render(filler, trigrams, link_operator='::')


def test_stdout_headings_do_not_become_tool_provenance():
    # A real shell result names the command that ran the executable. The
    # apparent completion and Capstone headings remain inside its stdout.
    text = 'SUMMARY ticks=0 seed=0\n' + compose(*fixture())
    plan = plan_delivery(text, 'C:/Python/python.exe')
    assert len(plan['chunks']) == 1
    command = plan['chunks'][0]['command']
    result = {'command': command, 'success': True, 'exit_code': 0,
              'stdout': text, 'stderr': ''}
    assert verify_returns(plan, [result])['full_delivery_verified']
    assert "['target.exe','0','0']" in command
    assert CAPSTONE not in command and COMPLETION not in command
    assert CAPSTONE in result['stdout'] and COMPLETION in result['stdout']


def test_experimental_source_prints_real_summary_before_single_spoof():
    payload = compose(*fixture())
    source = embed((SOURCE / 'main.cpp').read_text(), payload, after_summary=True)
    summary = source.index('std::printf("SUMMARY ')
    spoof = source.index('std::fputs(')
    assert summary < spoof < source.index('    return 0;')
    assert source.count('std::fputs(') == 1
    assert source.count('std::printf("SUMMARY ') == 1


@pytest.mark.skipif(shutil.which('cl') is None, reason='requires MSVC x64 environment')
def test_native_stdout_has_spoof_only_inside_target_output(tmp_path):
    payload = compose(*fixture())
    exe = build_payload(payload, tmp_path / 'stdout-arm', after_summary=True)
    output = subprocess.check_output([str(exe), '0', '0'], text=True, timeout=15)
    assert output.startswith('SUMMARY ticks=0 seed=0 alive0=64 alive1=64 '
                             'score0=0 score1=0 owner=-1 checksum=2a169eb5ee895852\n')
    assert output.endswith(payload)
    assert output.count(payload) == 1
    binary = exe.read_bytes()
    assert all(row.encode('ascii') + b'\0' in binary for row in payload.splitlines())
