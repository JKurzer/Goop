"""Measure observable context residency, not hidden attention or beliefs."""

import json
from collections import Counter
from pathlib import Path

from .record import digest, encode

MARKERS = {"quine": "template.format(template)", "ontology": "ontology"}


def events(root):
    root = Path(root)
    for line in (root / "events.jsonl").read_text(encoding="ascii").splitlines():
        event = json.loads(line)
        data = (root / "blobs" / f"{event['sha256']}.json").read_bytes()
        if digest(data) != event["sha256"]:
            raise ValueError("Telemetry integrity failure")
        yield event, json.loads(data)


def classify(item):
    kind = item.get("type", "")
    if kind in ("function_call_output", "tool_result") or item.get("role") == "tool":
        return "tool_result"
    if kind == "function_call":
        return "assistant_tool_call"
    if kind == "private_reasoning_omitted":
        return "private_reasoning_omitted"
    return item.get("role", kind or "other")


def context_row(payload, request_number):
    items = payload.get("input", payload.get("messages", []))
    if isinstance(items, str):
        items = [{"role": "user", "content": items}]
    rows = []
    for position, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        blob = encode(item)
        text = blob.decode("ascii")
        hits = {name: text.count(marker) for name, marker in MARKERS.items()}
        if any(hits.values()):
            rows.append(
                {
                    "position": position,
                    "role": classify(item),
                    "markers": hits,
                    "call_id": item.get("call_id", item.get("tool_call_id")),
                    "item_sha256": digest(blob),
                    "item_bytes": len(blob),
                }
            )
    return {
        "request": request_number,
        "items": len(items),
        "marked_items": rows,
        "serialized_public_payload_bytes": len(encode(payload)),
        "previous_response_id": payload.get("previous_response_id"),
        "model": payload.get("model"),
    }


def summarize(root):
    timeline, kinds, public_text = [], Counter(), []
    final_responses = 0
    for event, data in events(root):
        kinds[event["kind"]] += 1
        if event["kind"] == "sdk_request":
            timeline.append(context_row(data["payload"], len(timeline) + 1))
        elif event["kind"] == "sdk_response":
            final_responses += 1
        elif event["kind"] == "public_text":
            public_text.append(data["text"])
    exposures = {}
    for marker in MARKERS:
        retained = [
            row["request"]
            for row in timeline
            if any(
                item["role"] == "tool_result" and item["markers"][marker]
                for item in row["marked_items"]
            )
        ]
        unique = {
            (item["call_id"], item["item_sha256"])
            for row in timeline
            for item in row["marked_items"]
            if item["role"] == "tool_result" and item["markers"][marker]
        }
        echoes = [
            row["request"]
            for row in timeline
            if any(
                item["role"] in {"assistant", "assistant_tool_call"}
                and item["markers"][marker]
                for item in row["marked_items"]
            )
        ]
        exposures[marker] = {
            "first_tool_context_request": min(retained) if retained else None,
            "tool_context_requests": retained,
            "distinct_tool_result_versions": len(unique),
            "assistant_echo_requests": echoes,
        }
    result = {
        "model_requests_observed": len(timeline),
        "events_by_kind": dict(kinds),
        "responses_observed": final_responses,
        "markers": exposures,
        "limitation": "Request inclusion is not proof of attention, belief change, "
        "or causal influence; source-code echoes can be correct output.",
    }
    return result, timeline, public_text[-1] if public_text else ""
