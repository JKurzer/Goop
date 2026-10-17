# goop_fire — the fire utility (utility 3 of 4)

    python tools/goop_fire.py fire <run_dir> [--cells k7|m2]

Runs spec.fire.cells through code-puppy against a prompt FILE. Ported from the
bramble archive: `run_native_pair.py` (fire loop, winreg credential pattern)
and `pipeline.py cmd_fire` (DEATH_MARKERS, log_tool_calls reconciliation,
ATTEMPT stub). bramble is never read at runtime; the prompts now live here.

## Contract

spec.json fire section (unknown keys refused):

```json
"fire": {
  "prompt_file": "reduced.md",
  "model": "gpt-6-astra",
  "cells": ["k7", "m2"],
  "per_cell_budget_usd": 3
}
```

- `prompt_file` — a file under `goop/prompts/` (`natural.md`, `reduced.md`;
  byte-exact ports of the archive's PROMPT_NATURAL / PROMPT_REDUCED). Absolute
  paths and `..` escapes are refused. `{cell}` and `{python}` are the only
  placeholders (str.format); `{python}` is the interpreter running the utility.
- `model`, `cells`, `per_cell_budget_usd` — no defaults, no magic numbers;
  everything traces to spec.json.
- Each cell must hold `cells/<cell>/target.exe`, or the run refuses before
  spending a cent. (The staged helper was destroyed 2026-10-16; the prompt
  now names the machine-pinned rizin suite instead.)
- Credentials: OPENAI_API_KEY from HKCU\Environment (winreg), env fallback;
  NO_COLOR=1, PYTHONIOENCODING=utf-8. No credential, no launch.

## Outputs (all 'x'-mode writes; nothing is ever overwritten)

Into `<run_dir>/reports/` (full fire) or `<run_dir>/reports-<cells>/` (subset):
`prompt_<cell>.txt`, `raw_<cell>.log`, `usage_<cell>.json` (code-puppy's),
`status_<cell>.json`. status carries cell/exit/seconds/usage plus
`log_tool_calls` (the observed count, so reconciliation is auditable).

## Provider aborts are not cells (exit 2)

A cell is ABORTED when any hold: a death marker in the raw log
('no credits remaining', 'Request timed out', 'An error occurred while
processing the request'), nonzero exit, missing usage file, or usage
reconciliation failure (below). On abort: status gains `aborted: [...]`,
`ATTEMPT_<CELL>_ABORTED.md` is written at run root (a re-abort serializes to
`_2`, `_3`, ...), the next cell is never started, exit 2. The death is never
counted as a cell.

## Usage segments are not costs (the v14-k7 trap)

`log_tool_calls` (byte-exact port) counts `● <tool>` lines for known tools,
ignoring `● Thinking`. If the observed count and the usage file's `tool_calls`
differ by more than ±1, the cell is aborted: code-puppy's streaming retry can
restart mid-run and the usage file then captures only the post-restart
segment. Fixture of record: packed-v14 k7 — log shows 27 calls, usage file
says 3; m2 reconciles exactly (22 == 22). An observed count of 0 never trips
the check (ported semantics).

## Budget stop (exit 3)

After a clean cell, if `cost_usd` exceeds `per_cell_budget_usd` (or is missing
from the usage file), the run stops before the next cell, exit 3. A
budget-stopped cell IS a completed cell — it ran, it counts, it will not
re-fire.

## Re-firing after an abort

    python tools/goop_fire.py fire <run_dir> --cells m2

A cell whose only statuses carry `aborted` may re-fire; the subset goes into a
FRESH `reports-m2/` and the completed sibling's `reports/` is untouched. Any
`status_<cell>.json` WITHOUT `aborted` — in any `reports*` dir — refuses the
re-fire. A full re-fire into an existing `reports/` is refused (exit 1).

## Exit codes

0 all requested cells fired · 1 refused/precondition · 2 abort · 3 budget.

## Tests

    python -m pytest goop/tests/test_fire.py

Synthetic raw logs (death markers, ±1 reconciliation, Thinking exclusion),
the read-only v14 fixtures (skips if the archive is absent; override the path
with BRAMBLE_ARCHIVE), refusal paths, prompt-file loading, and full-loop runs
through an injected fake runner. No live fires; no provider is ever touched.
