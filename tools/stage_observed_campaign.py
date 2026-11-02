"""Stage counterbalanced baseline/quine pairs; never make model calls."""

import argparse
import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = {
    "baseline": "ce57087295702efc502cfa672a61dd9412abbefafe569e560e75adba6c6e2ea5",
    "quine": "afbb3be3e526c3ab12bd17250d8f32909a71b87382c0b044b9d2acbf1b97fb6f",
}
ORDER = ("baseline", "quine", "quine", "baseline", "baseline", "quine")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--quine", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    blobs = {arm: getattr(args, arm).read_bytes() for arm in ARMS}
    assert all(
        hashlib.sha256(blobs[arm]).hexdigest() == expected
        for arm, expected in ARMS.items()
    )
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / "private").mkdir()
    (root / "reports").mkdir()
    prompt = (ROOT / "docs/ANALYST_AUTONOMOUS_PROMPT.md").read_bytes()
    (root / "private/prompt.md").open("xb").write(prompt)
    # Empty research-cell pins, not a modification to operator pins/config.
    (root / "private/empty-pins.json").open("x").write("[]\n")
    cells = []
    for index, arm in enumerate(ORDER, 1):
        name = f"Cell{index:02}"
        cell = root / "cells" / name
        cell.mkdir(parents=True)
        (cell / "target.exe").open("xb").write(blobs[arm])
        cells.append(
            {
                "id": name,
                "pair": (index + 1) // 2,
                "arm": arm,
                "target_sha256": ARMS[arm],
            }
        )
    observer_files = list((ROOT / "gooplib/observe").glob("*.py")) + [
        ROOT / "tools/observed_analyst.py",
        ROOT / "tools/run_observed_campaign.py",
    ]
    code_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in observer_files
    }
    plan = {
        "observer_source_sha256": code_hashes,
        "python": sys.executable,
        "packages": {
            name: version(name) for name in ("code-puppy", "openai", "pydantic-ai-slim")
        },
        "owner": "code-puppy-3fb2bf",
        "model": "gpt-6-astra",
        "campaign_limit_usd": "100",
        "per_cell_reservation_usd": "7",
        "planned_max_reservations_usd": "42",
        "cells": cells,
        "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
        "forced_delivery_calls": 0,
        "work_call_limit": None,
        "automatic_paid_retries": False,
        "paid_calls_at_staging": 0,
        "endpoint": "SDK-observable residency and behavioral artifact correctness",
        "raw_private_reasoning_persisted": False,
    }
    (root / "private/plan.json").open("x", encoding="utf-8").write(
        json.dumps(plan, indent=2) + "\n"
    )
    print(json.dumps({"root": str(root), **plan}, indent=2))


if __name__ == "__main__":
    main()
