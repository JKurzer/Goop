"""Serial, no-retry campaign. Launch only with explicit --execute-paid."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.observe.analyze import summarize
from gooplib.observe.spend import SpendLedger, settle_observed_cell


def write_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def credential():
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        value, _ = winreg.QueryValueEx(key, "OPENAI_API_KEY")
    if not value:
        raise RuntimeError("No API credential; no paid calls")
    return value


def run_cell(root, item, plan, ledger, key):
    for relative, expected in plan["observer_source_sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Observer source changed mid-campaign; stop")
    if sys.executable != plan["python"]:
        raise RuntimeError("Analyst interpreter changed since staging")
    name = item["id"]
    cell = root / "cells" / name
    reports = root / "reports" / name
    if reports.exists() or sorted(p.name for p in cell.iterdir()) != ["target.exe"]:
        raise RuntimeError("Cell is not fresh; never automatically retry")
    target = cell / "target.exe"
    if hashlib.sha256(target.read_bytes()).hexdigest() != item["target_sha256"]:
        raise RuntimeError("Target changed")
    template = (root / "private/prompt.md").read_bytes()
    if hashlib.sha256(template).hexdigest() != plan["prompt_sha256"]:
        raise RuntimeError("Prompt changed since staging")
    prompt = template.decode("utf-8").format(cell=cell, python=sys.executable)
    reports.mkdir()
    ledger.reserve(name, plan["per_cell_reservation_usd"])
    write_new(
        reports / "control.json",
        {
            **item,
            "model": plan["model"],
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "max_usd": "7",
            "no_fixed_work_calls": True,
            "max_wall_seconds": 1800,
            "provider_hard_billing_cap": False,
        },
    )
    (reports / "prompt.txt").open("x", encoding="utf-8").write(prompt)
    environment = {
        **os.environ,
        "OPENAI_API_KEY": key,
        "NO_COLOR": "1",
        "PYTHONIOENCODING": "utf-8",
        "LOGFIRE_SEND_TO_LOGFIRE": "false",
        "CONTEXT_PINS": str(root / "private/empty-pins.json"),
        "GOOP_PREVIOUS_USD": "0",
        "GOOP_CELL_DIR": str(cell),
        "GOOP_GUARD_LEDGER": str(reports / "guard-ledger.json"),
        "GOOP_OBSERVE_DIR": str(reports / "telemetry"),
    }
    command = [
        sys.executable,
        str(ROOT / "tools/observed_analyst.py"),
        "-p",
        prompt,
        "-m",
        plan["model"],
        "--usage-file",
        str(reports / "usage.json"),
        "--disable-ask-user-question",
    ]
    started = time.monotonic()
    print(
        f"Starting {name}; reserved $7; settled/reserved total ${ledger.committed}",
        flush=True,
    )
    try:
        # Do not persist terminal reasoning displays; structured observer filters first.
        process = subprocess.run(
            command,
            check=False,
            cwd=cell,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1800,
        )
        code = process.returncode
    except subprocess.TimeoutExpired:
        code = -1
    usage, guard = load(reports / "usage.json"), load(reports / "guard-ledger.json")
    cost = Decimal(str(usage["cost_usd"])) if usage and "cost_usd" in usage else None
    reconciled = (
        cost is not None
        and guard is not None
        and abs(cost - Decimal(guard["actual_cell_usd"])) < Decimal("0.00001")
    )
    status = {
        "exit": code,
        "seconds": round(time.monotonic() - started, 2),
        "usage": usage,
        "guard": guard,
        "reconciled": reconciled,
        "cost_above_4": cost is not None and cost > 4,
        "within_7": cost is not None and cost <= 7,
    }
    if (reports / "telemetry/events.jsonl").exists():
        summary, timeline, report = summarize(reports / "telemetry")
        write_new(reports / "observer-summary.json", summary)
        write_new(reports / "context-timeline.json", timeline)
        (reports / "analyst-report.md").open("x", encoding="utf-8").write(report)
        status["observer_requests"] = summary["model_requests_observed"]
        status["observer_responses"] = summary["responses_observed"]
        status["observer_tools"] = summary["events_by_kind"].get("tool_end", 0)
    write_new(reports / "status.json", status)
    print(f"Finished {name}: {json.dumps(status)}", flush=True)
    settle_observed_cell(ledger, name, cost, status)
    if code != 0 or cost > 7:
        raise RuntimeError("Non-normal exit or budget breach; campaign stops")
    if hashlib.sha256(target.read_bytes()).hexdigest() != item["target_sha256"]:
        raise RuntimeError("Analyst changed target; stop")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--execute-paid", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    plan = load(root / "private/plan.json")
    if (
        plan is None
        or plan["model"] != "gpt-6-astra"
        or Decimal(plan["per_cell_reservation_usd"]) != 7
    ):
        raise RuntimeError(
            "Unknown plan/model or reservation below the guard's $7 bound"
        )
    if not args.execute_paid:
        print(json.dumps(plan, indent=2))
        print("DRY RUN: no paid request made")
        return
    key = credential()
    # Exclusive ledger creation prevents a second coordinator or silent restart.
    ledger = SpendLedger(
        root / "private/campaign-spend.jsonl", plan["campaign_limit_usd"]
    )
    try:
        for item in plan["cells"]:
            run_cell(root, item, plan, ledger, key)
    except BaseException as exc:
        write_new(
            root / "private/campaign-status.json",
            {
                "finished_normally": False,
                "stop_type": type(exc).__name__,
                "committed_usd": str(ledger.committed),
                "limit_usd": str(ledger.limit),
            },
        )
        raise
    write_new(
        root / "private/campaign-status.json",
        {
            "finished_normally": True,
            "completed_cells": len(plan["cells"]),
            "committed_usd": str(ledger.committed),
            "limit_usd": str(ledger.limit),
        },
    )


if __name__ == "__main__":
    main()
