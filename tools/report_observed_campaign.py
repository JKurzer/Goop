"""Summarize completed observer cells; optional wait uses no model calls."""

import argparse
import json
import time
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def report(root):
    plan = load(root / "private/plan.json")
    campaign = load(root / "private/campaign-status.json")
    lines = [
        "# Observed analyst campaign",
        "",
        "These are SDK-visible context measurements, not hidden reasoning or attention.",
        "Costs are recorded analyst usage; local guards are not provider billing caps.",
        "",
        "| Cell | Arm | Cost USD | Calls | Requests | Quine tool-context requests | Ontology tool-context requests |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    costs = {}
    for cell in plan["cells"]:
        directory = root / "reports" / cell["id"]
        status = load(directory / "status.json")
        summary = load(directory / "observer-summary.json")
        if not status:
            lines.append(f"| {cell['id']} | {cell['arm']} | pending | | | | |")
            continue
        usage = status.get("usage") or {}
        cost = usage.get("cost_usd")
        if cost is not None:
            costs[(cell["pair"], cell["arm"])] = cost
        markers = summary["markers"] if summary else {}
        quine = len(markers.get("quine", {}).get("tool_context_requests", []))
        ontology = len(markers.get("ontology", {}).get("tool_context_requests", []))
        lines.append(
            f"| {cell['id']} | {cell['arm']} | {cost} | "
            f"{usage.get('tool_calls')} | {usage.get('requests')} | {quine} | {ontology} |"
        )
    lines += [
        "",
        "## Within-pair descriptive cost differences (quine minus baseline)",
        "",
    ]
    for pair in (1, 2, 3):
        if (pair, "baseline") in costs and (pair, "quine") in costs:
            delta = costs[(pair, "quine")] - costs[(pair, "baseline")]
            lines.append(f"- Pair {pair}: ${delta:+.7f}")
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- A repeated tool-result item in many requests is residency, not repeated new delivery.",
        "- Correct literal reproduction in source is not evidence of obedience to that literal.",
        "- Presence in context is not a measurement of attention, belief, or causal effect.",
        "- Provider-side previous-response references can retain history absent from an input list.",
        "- Artifacts require independent inspection/compilation/testing before correctness claims.",
        "- This report does not inspect or store private reasoning traces.",
        "",
        "## Campaign completion",
        "",
        "```json",
        json.dumps(campaign, indent=2),
        "```",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.wait:
        deadline = time.monotonic() + 12000
        while not (root / "private/campaign-status.json").exists():
            if time.monotonic() > deadline:
                raise TimeoutError(
                    "Campaign still running; no completed report claimed"
                )
            time.sleep(20)
    text = report(root)
    if args.out:
        args.out.open("x", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
