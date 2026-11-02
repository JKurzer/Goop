"""Offline real-SDK smoke test; mock HTTP transport makes zero network calls."""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.observe.analyze import summarize
from gooplib.observe.hooks import install
from gooplib.observe.record import Recorder


async def check(directory):
    import httpx
    from code_puppy import config
    from code_puppy.callbacks import on_post_tool_call, on_pre_tool_call
    from openai import AsyncOpenAI

    secret = "offline-secret-never-persist-1234"
    input_items = [
        {"role": "user", "content": "public test"},
        {"type": "reasoning", "id": "rs_fake", "encrypted_content": "PRIVATE_SENTINEL"},
    ]
    seen = []
    response = {
        "id": "resp_fake",
        "object": "response",
        "created_at": 0,
        "status": "completed",
        "model": "gpt-6-astra",
        "output": [],
        "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
    }
    event_list = [
        {
            "type": "response.output_text.done",
            "sequence_number": 1,
            "item_id": "msg_fake",
            "output_index": 0,
            "content_index": 0,
            "text": "public result",
        },
        {"type": "response.completed", "sequence_number": 2, "response": response},
    ]
    body = "".join("data: " + json.dumps(event) + "\n\n" for event in event_list)

    async def handler(request):
        data = json.loads(request.content)
        seen.append(data)
        assert data["input"] == input_items
        return httpx.Response(
            200, text=body, headers={"content-type": "text/event-stream"}
        )

    recorder = Recorder(directory / "telemetry", secrets=[secret])
    install(recorder, directory)
    assert config.get_auto_save_session() is False
    async with AsyncOpenAI(
        api_key=secret,
        base_url="https://offline.invalid/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    ) as client:
        stream = await client.responses.create(
            model="gpt-6-astra", input=input_items, stream=True
        )
        received = [event async for event in stream]
    assert len(received) == 2 and len(seen) == 1
    assert input_items[1]["encrypted_content"] == "PRIVATE_SENTINEL"
    result = {"content": "template.format(template)", "success": True}
    await on_pre_tool_call("test_tool", {"value": 1})
    await on_post_tool_call("test_tool", {"value": 1}, result, 1.0)
    assert result == {"content": "template.format(template)", "success": True}
    report, _, final = summarize(recorder.root)
    assert report["model_requests_observed"] == report["responses_observed"] == 1
    assert report["events_by_kind"]["tool_end"] == 1 and final == "public result"
    logs = "".join(
        path.read_text(encoding="ascii") for path in (recorder.root / "blobs").glob("*")
    )
    assert "PRIVATE_SENTINEL" not in logs and secret not in logs
    print(
        "OFFLINE PASS: real SDK + HTTP serialization unchanged; ordered events; "
        "tool results unchanged; private reasoning/auth absent; zero network/model calls"
    )


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="goop-observer-check-") as temporary:
        asyncio.run(check(Path(temporary)))
