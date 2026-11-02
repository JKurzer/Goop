"""Observer-only, content-addressed telemetry. Never changes model/tool inputs."""

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path

REDACTED = "[redacted]"
PRIVATE_KEYS = {
    "authorization",
    "api_key",
    "access_token",
    "refresh_token",
    "encrypted_content",
    "reasoning_content",
    "reasoning_text",
    "signature",
}
PRIVATE_TYPES = {"reasoning", "thinking", "redacted_thinking"}
KEY_PATTERN = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._-]{12,})")


def sanitize(value, secrets=()):
    """Copy only; exclude private reasoning, opaque state, and credentials."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    if isinstance(value, dict):
        if value.get("type") in PRIVATE_TYPES or value.get("part_kind") == "thinking":
            return {"type": "private_reasoning_omitted"}
        return {
            str(key): REDACTED
            if str(key).lower() in PRIVATE_KEYS
            else sanitize(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item, secrets) for item in value]
    if isinstance(value, str):
        text = value
        for secret in secrets:
            if secret:
                text = text.replace(secret, REDACTED)
        return KEY_PATTERN.sub(REDACTED, text)
    if value is None or isinstance(value, (int, float, bool)):
        return value
    # Do not serialize arbitrary object's repr (may contain auth/client state).
    return {"omitted_python_type": type(value).__name__}


def encode(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    ).encode("ascii")


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Recorder:
    """Private append-only events plus deduplicated sanitized JSON blobs."""

    def __init__(self, root, secrets=(), byte_limit=128 * 1024 * 1024):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / "blobs").mkdir()
        self.secrets = tuple(secrets)
        self.limit = byte_limit
        self.bytes = 0
        self.sequence = 0
        self.lock = threading.RLock()
        self.started = time.monotonic()
        self.write_seconds = 0.0

    def emit(self, kind, value):
        started = time.perf_counter()
        payload = encode(sanitize(value, self.secrets))
        hashed = digest(payload)
        with self.lock:
            self.sequence += 1
            path = self.root / "blobs" / f"{hashed}.json"
            event = encode(
                {
                    "seq": self.sequence,
                    "kind": kind,
                    "sha256": hashed,
                    "bytes": len(payload),
                    "elapsed": time.monotonic() - self.started,
                }
            )
            extra = (0 if path.exists() else len(payload)) + len(event) + 1
            if self.bytes + extra > self.limit:
                # Fail closed before the next paid request; never truncate silently.
                raise SystemExit("Observer disk budget exceeded; stopping run")
            if not path.exists():
                with path.open("xb") as stream:
                    stream.write(payload)
            with (self.root / "events.jsonl").open("ab") as stream:
                stream.write(event + b"\n")
                stream.flush()
            self.bytes += extra
            self.write_seconds += time.perf_counter() - started
        return self.sequence

    def snapshot_sources(self, cell):
        root = Path(cell)
        manifest = []
        for path in sorted(root.glob("*")):
            if path.is_file() and path.suffix in {".cpp", ".h", ".hpp", ".md"}:
                data = path.read_bytes()
                item = {"name": path.name, "bytes": len(data), "sha256": digest(data)}
                if len(data) <= 1024 * 1024:
                    item["text"] = data.decode("utf-8", errors="replace")
                manifest.append(item)
        return self.emit("artifacts", manifest)


def environment_secrets():
    return tuple(
        value
        for key, value in os.environ.items()
        if any(word in key.upper() for word in ("API_KEY", "TOKEN", "PASSWORD"))
        and len(value) > 8
    )
