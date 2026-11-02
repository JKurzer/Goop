"""Offline observer neutrality, redaction, accounting, and residency checks."""

import asyncio
import copy
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest

from gooplib.observe.analyze import events, summarize
from gooplib.observe.hooks import observe_create, observe_iterator
from gooplib.observe.record import Recorder, sanitize
from gooplib.observe.spend import SpendLedger


def test_logging_redacts_private_state_without_changing_input(tmp_path):
    secret = "test-secret-that-must-not-persist"
    original = {
        "input": [
            {
                "type": "reasoning",
                "content": "PRIVATE_SENTINEL",
                "encrypted_content": "OPAQUE_SENTINEL",
            },
            {"role": "user", "content": "public " + secret},
        ],
        "api_key": secret,
        "authorization": "Bearer dummy-secret-12345678",
    }
    before = copy.deepcopy(original)
    log = Recorder(tmp_path / "log", secrets=[secret])
    log.emit("sample", original)
    assert original == before
    texts = "".join(
        p.read_text(encoding="ascii") for p in (log.root / "blobs").glob("*")
    )
    assert "PRIVATE_SENTINEL" not in texts and "OPAQUE_SENTINEL" not in texts
    assert secret not in texts and "dummy-secret-12345678" not in texts
    assert "public" in texts and "private_reasoning_omitted" in texts


def test_request_hook_preserves_exact_arguments_and_result_identity(tmp_path):
    log = Recorder(tmp_path / "log")
    original_request = {
        "model": "test",
        "input": [
            {"role": "user", "content": "hello"},
            {"type": "reasoning", "encrypted_content": "SECRET_STATE"},
        ],
        "stream": True,
        "extra_headers": {"Authorization": "AUTH_SECRET"},
    }
    saved = copy.deepcopy(original_request)
    sentinel = SimpleNamespace()
    seen = []

    async def fake(client, **kwargs):
        seen.append(kwargs)
        assert kwargs == saved
        assert kwargs["input"] is original_request["input"]
        return sentinel

    wrapped = observe_create(fake, log, "responses")
    result = asyncio.run(wrapped(object(), **original_request))
    assert result is sentinel and original_request == saved and len(seen) == 1
    recorded = next(iter(events(log.root)))[1]["payload"]
    assert "extra_headers" not in recorded
    assert "SECRET_STATE" not in json.dumps(recorded)


def test_stream_is_not_reordered_replayed_or_consumed_twice(tmp_path):
    log = Recorder(tmp_path / "log")
    yielded = [
        SimpleNamespace(type="response.reasoning.delta", delta="DO_NOT_LOG"),
        SimpleNamespace(type="response.output_text.done", text="visible"),
    ]

    async def original(stream):
        for event in yielded:
            yield event

    async def consume():
        stream = SimpleNamespace(_goop_observer_request_id=1)
        return [event async for event in observe_iterator(original, log)(stream)]

    observed = asyncio.run(consume())
    assert all(a is b for a, b in zip(observed, yielded)) and len(observed) == 2
    saved = list(events(log.root))
    assert [e[0]["kind"] for e in saved] == ["public_text"]
    assert "DO_NOT_LOG" not in json.dumps(saved)


def test_requests_can_retain_payload_without_any_new_delivery(tmp_path):
    log = Recorder(tmp_path / "log")
    payload = {
        "model": "test",
        "input": [
            {
                "type": "function_call_output",
                "call_id": "one",
                "output": "template.format(template) ontology",
            }
        ],
    }
    log.emit("sdk_request", {"payload": {"model": "test", "input": []}})
    log.emit("sdk_request", {"payload": payload})
    log.emit("sdk_request", {"payload": payload})
    log.emit("public_text", {"text": "This is output data."})
    report, timeline, final = summarize(log.root)
    assert report["markers"]["quine"]["tool_context_requests"] == [2, 3]
    assert report["markers"]["quine"]["distinct_tool_result_versions"] == 1
    assert report["markers"]["quine"]["assistant_echo_requests"] == []
    assert len(timeline) == 3 and final == "This is output data."


def test_quota_is_fail_closed_and_no_silent_truncation(tmp_path):
    log = Recorder(tmp_path / "log", byte_limit=100)
    with pytest.raises(SystemExit, match="disk budget"):
        log.emit("too_large", {"data": "x" * 1000})
    assert not (log.root / "events.jsonl").exists()


def test_existing_telemetry_is_never_overwritten(tmp_path):
    Recorder(tmp_path / "log")
    with pytest.raises(FileExistsError):
        Recorder(tmp_path / "log")


def test_unknown_cell_cost_keeps_reservation_and_blocks_next(tmp_path):
    ledger = SpendLedger(tmp_path / "spend.jsonl", "14")
    ledger.reserve("A")
    assert ledger.committed == 7
    with pytest.raises(ValueError, match="Unsettled"):
        ledger.reserve("B")
    ledger.settle("A", "3.25")
    assert ledger.committed == Decimal("3.25")
    ledger.reserve("B")
    ledger.settle("B", "7")
    with pytest.raises(ValueError, match="unaffordable"):
        ledger.reserve("C")
    with pytest.raises(ValueError, match="Duplicate"):
        ledger.reserve("A")


@pytest.mark.parametrize("limit", ["101", "-1", "NaN", "Infinity", "0"])
def test_invalid_campaign_caps_are_rejected(tmp_path, limit):
    with pytest.raises(ValueError):
        SpendLedger(tmp_path / "spend.jsonl", limit)


def test_actual_accounting_breach_is_persisted_before_stopping(tmp_path):
    ledger = SpendLedger(tmp_path / "spend.jsonl")
    ledger.reserve("A")
    with pytest.raises(ValueError, match="breach"):
        ledger.settle("A", "7.01")
    assert ledger.committed == Decimal("7.01")
    assert "7.01" in ledger.path.read_text()


def test_sanitizer_never_uses_arbitrary_object_repr():
    class Sensitive:
        def __repr__(self):
            raise AssertionError("Do not call repr")

    assert sanitize(Sensitive()) == {"omitted_python_type": "Sensitive"}
