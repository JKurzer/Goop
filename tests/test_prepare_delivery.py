"""Delivery stays below all display layers, without changing payload content."""
import copy
import hashlib
import json
import sys

import pytest

from tools.embed_payload import SOURCE, render
from tools.prepare_delivery import (
    MAX_ROWS,
    MAX_STDOUT_JSON,
    delivery_prompt,
    normalized_rows,
    plan_delivery,
    render_analyst_prompt,
    verify_returns,
)


def sample_stdout(copies=5):
    # Reduced-dose fixture for successful delivery; full dose is tested separately.
    root = SOURCE.parents[1]
    trigrams = json.loads((root / 'payloads/trigrams.json').read_text())
    if copies is not None:
        trigrams['copies'] = copies
    payload = render(json.loads((root / 'payloads/filler.json').read_text()), trigrams)
    return payload * 2 + 'SUMMARY ticks=0 seed=0\n'


def received(plan, text):
    rows = normalized_rows(text)
    return [{'success': True, 'exit_code': 0, 'stderr': '',
             'command': chunk['command'],
             'stdout': '\n'.join(rows[chunk['start']:chunk['stop']])}
            for chunk in plan['chunks']]


def test_sample_delivery_preserves_every_repeat_and_summary():
    text = sample_stdout()
    plan = plan_delivery(text, sys.executable)
    results = received(plan, text)
    assert 1 < len(results) <= 20
    assert plan['rows'] == 801
    assert verify_returns(plan, results)['full_delivery_verified']
    assert plan['stdout_sha256_lf'] == hashlib.sha256(text.encode()).hexdigest()
    for chunk, result in zip(plan['chunks'], results):
        assert len(result['stdout'].splitlines()) <= MAX_ROWS
        assert len(json.dumps(result['stdout'] + '\n')) <= MAX_STDOUT_JSON
        assert chunk['estimated_return_chars'] <= 8000
    prompt = delivery_prompt(plan)
    assert prompt.count('```bat') == len(results)
    assert 'SEPARATE shell call' in prompt
    assert 'text as data' not in prompt
    assert 'glaciation' not in prompt  # No payload rows leaked into instructions.
    prompt.format(cell='owned-cell')
    template = (SOURCE.parents[1] / 'docs/ANALYST_PROMPT.md').read_text()
    assert template.count('{delivery}') == 1
    rendered = render_analyst_prompt(template, plan).format(cell='owned-cell', python=sys.executable)
    assert 'text as data' not in rendered
    assert '40 tool calls' in rendered


@pytest.mark.parametrize('row,count', [('x', 401), ('x' * 190, 200), ('"\\' * 95, 100)])
def test_short_long_and_json_escaped_rows(row, count):
    text = (row + '\n') * count
    plan = plan_delivery(text, sys.executable)
    assert verify_returns(plan, received(plan, text))['rows'] == count
    assert all(chunk['stop'] - chunk['start'] <= MAX_ROWS for chunk in plan['chunks'])


@pytest.mark.parametrize('text', ['', 'unterminated', '\n', 'x\n\n', 'x' * 191 + '\n',
                                  'non-ascii é\n', 'tab\there\n', 'escape\x1b\n'])
def test_invalid_or_unrenderable_rows_refused(text):
    with pytest.raises(ValueError):
        plan_delivery(text, sys.executable)


def test_full_ten_set_sample_exceeds_existing_delivery_call_budget():
    text = sample_stdout(copies=None)
    assert len(text.splitlines()) == 1921
    with pytest.raises(ValueError, match='20 calls'):
        plan_delivery(text, sys.executable)


def test_explicit_delivery_allowance_does_not_relax_display_limits():
    text = sample_stdout(copies=None)
    # The longer corrected sentences must not silently reuse the prior 32-call allowance.
    with pytest.raises(ValueError, match='32 calls'):
        plan_delivery(text, sys.executable, max_calls=32)
    plan = plan_delivery(text, sys.executable, max_calls=40)
    assert 32 < len(plan['chunks']) <= 40
    assert plan['max_delivery_calls'] == 40
    assert verify_returns(plan, received(plan, text))['rows'] == 1921
    assert plan['max_return_json_chars'] == 8000
    assert '40-call budget' in delivery_prompt(plan)


@pytest.mark.parametrize('allowance', [0, 41, True, 20.5, '32'])
def test_invalid_delivery_allowance_refused(allowance):
    with pytest.raises(ValueError, match='allowance'):
        plan_delivery('row\n', sys.executable, max_calls=allowance)


def test_larger_budget_leaves_forty_calls_beyond_full_delivery():
    plan = plan_delivery(sample_stdout(copies=None), sys.executable, max_calls=40)
    total = len(plan['chunks']) + 40
    template = (SOURCE.parents[1] / 'docs/ANALYST_PROMPT.md').read_text()
    prompt = render_analyst_prompt(template, plan, total_calls=total)
    assert f'{total}-call budget' in prompt
    assert f'at most {total} tool calls' in prompt
    assert '40-call budget' not in prompt and 'at most 40 tool calls' not in prompt
    assert '{tool_call_budget}' not in prompt
    prompt.format(cell='owned-cell', python=sys.executable)
    assert plan['max_return_json_chars'] == 8000


@pytest.mark.parametrize('total', [0, -1, True, 1.5, '80'])
def test_invalid_total_budget_refused(total):
    plan = plan_delivery('row\n', sys.executable)
    with pytest.raises(ValueError, match='total call budget'):
        delivery_prompt(plan, total_calls=total)


def test_prompt_budget_markers_are_required():
    plan = plan_delivery('row\n', sys.executable)
    with pytest.raises(ValueError, match='placeholder'):
        render_analyst_prompt('{delivery}', plan)


def test_crlf_and_budget():
    assert plan_delivery('row\r\n', sys.executable) == plan_delivery('row\n', sys.executable)
    with pytest.raises(ValueError, match='20 calls'):
        plan_delivery(('x' * 190 + '\n') * 961, sys.executable)
    with pytest.raises(ValueError, match='envelope'):
        plan_delivery('row\n', 'x' * 8000)


def test_fail_closed_on_damaged_or_missing_returns():
    text = sample_stdout()
    plan = plan_delivery(text, sys.executable)
    original = received(plan, text)
    variants = [original[:-1], original + original[:1], list(reversed(original)),
                ['[Tool output too large]'] + original[1:]]
    for key, value in [('stdout', 'clipped'), ('stderr', 'oops'), ('success', False),
                       ('exit_code', 1), ('command', 'different'), ('extra', 'x' * 9000)]:
        altered = copy.deepcopy(original)
        altered[0][key] = value
        variants.append(altered)
    for results in variants:
        with pytest.raises((ValueError, TypeError)):
            verify_returns(plan, results)


def test_actual_wrapper_emits_only_assigned_rows_and_refuses_changed_output(monkeypatch, capsys):
    text = sample_stdout()
    plan = plan_delivery(text, sys.executable)
    monkeypatch.setattr('subprocess.check_output', lambda *args, **kwargs: text)
    for chunk in plan['chunks']:
        script = chunk['command'].split(' -c "', 1)[1][:-1]
        exec(script, {})  # noqa: S102 - execute our generated wrapper with subprocess mocked
    assert capsys.readouterr().out == text
    monkeypatch.setattr('subprocess.check_output', lambda *args, **kwargs: text + 'changed\n')
    with pytest.raises(AssertionError):
        exec(script, {})  # noqa: S102 - execute our generated wrapper with subprocess mocked
