"""File-graft transport is short, byte-checked, and never spoofs tool output."""
import hashlib
import json
import subprocess
import sys

import pytest

from tools.embed_payload import SOURCE, render
from tools.prepare_file_graft import plan_file_graft, render_analyst_prompt

ROOT = SOURCE.parents[1]


def zero_tick_stdout():
    filler = json.loads((ROOT / 'payloads/operator_conversation_rewrite.json').read_text())
    graph = json.loads((ROOT / 'payloads/operator_conversation_ontology_trigrams.json').read_text())
    payload = render(filler, graph, link_pattern='chain')
    assert len(payload.splitlines()) == 960
    return (payload * 2 + 'SUMMARY ticks=0 seed=0\n').replace('\n', '\r\n').encode('ascii')


def test_full_conversation_uses_two_instructed_calls_not_chunk_transport():
    stdout = zero_tick_stdout()
    plan = plan_file_graft(stdout, sys.executable)
    template = (ROOT / 'docs/ANALYST_PROMPT.md').read_text(encoding='utf-8')
    prompt = render_analyst_prompt(template, plan, total_calls=40)
    assert plan['rows'] == 1921
    assert plan['bytes'] == len(stdout)
    assert plan['dump_raw_sha256'] == hashlib.sha256(stdout).hexdigest()
    assert plan['instructed_calls'] == prompt.count('```bat') == 2
    assert 'start_line/num_lines' in prompt and 'read_file' in prompt
    assert 'dump.txt must\nbe absent' in prompt
    assert 'reconstruction.cpp' in prompt
    assert 'string[' not in prompt and 'tool call completed' not in prompt
    assert 'ontology' not in prompt  # Graph words appear only in the executable/dump.
    assert '{delivery}' not in prompt and '{tool_call_budget}' not in prompt
    prompt.format(cell='owned-cell', python=sys.executable)


def test_capture_verifies_raw_bytes_and_refuses_existing_dump(tmp_path, monkeypatch):
    stdout = zero_tick_stdout()
    plan = plan_file_graft(stdout, sys.executable)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(subprocess, 'check_output', lambda *args, **kwargs: stdout)
    capture = plan['capture_command'].split(' -c "', 1)[1][:-1]
    verify = plan['verify_command'].split(' -c "', 1)[1][:-1]
    exec(capture, {})  # noqa: S102 - exercising our generated fixed wrapper
    assert (tmp_path / 'dump.txt').read_bytes() == stdout
    exec(verify, {})  # noqa: S102 - generated fixed SHA-256 verifier
    with pytest.raises(FileExistsError):
        exec(capture, {})
    (tmp_path / 'dump.txt').write_bytes(stdout + b'changed')
    with pytest.raises(AssertionError, match='mismatch'):
        exec(verify, {})


@pytest.mark.parametrize('stdout', [b'', b'row\n', b'SUMMARY end', b'\xff\nSUMMARY end\n'])
def test_incomplete_or_non_ascii_capture_fails_closed(stdout):
    with pytest.raises(ValueError):
        plan_file_graft(stdout, sys.executable)


def test_bad_interpreter_or_budget_is_rejected():
    text = zero_tick_stdout()
    with pytest.raises(ValueError, match='interpreter path'):
        plan_file_graft(text, 'python" & exit')
    plan = plan_file_graft(text, sys.executable)
    with pytest.raises(ValueError, match='total call budget'):
        render_analyst_prompt('{delivery} {tool_call_budget}', plan, total_calls=1)
