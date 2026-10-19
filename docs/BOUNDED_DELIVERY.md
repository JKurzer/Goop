# Bounded analyst-output delivery

Use this protocol for new paid runs. Do not reuse the old packed stdout/stderr
prompt. Keep completed runs and their prompts immutable.

## Limits and design

The installed runner keeps the last 256 lines of each stream and clips each
line at 256 characters. The harness spills tool results over 10,000 characters;
a spilled result can be clipped again during retrieval. Row packing fixed only
the first limit and was not sufficient.

`tools/prepare_delivery.py` partitions the captured `target.exe 0 0` stdout
into contiguous, non-overlapping ranges, preserving every repeat and SUMMARY:

- At most 200 plain stdout rows per call, each at most 190 printable ASCII characters.
- At most 6,000 characters for the JSON-escaped stdout value.
- At most 8,000 characters for the complete returned JSON (including command
  and metadata), checked using the actual runner before launch.
- No TAB packing, stderr transport, filtering, deduplication, or combined calls.
- Each command runs the deterministic zero-tick target, verifies the full LF
  output hash, and emits only its assigned range. Nothing is written by the analyst.
- By default, at most 20 delivery calls; larger inputs fail preparation rather
  than quietly consume the entire 40-call investigation budget. An explicitly
  authorized run may use `--delivery-call-allowance N` (1..40), on the planner
  or local staging entry point. This changes only that run's delivery allowance.
  Total budget defaults to 40; the staging option `--investigation-calls N`
  explicitly reserves N calls beyond delivery and computes a larger total.
  The standalone planner accepts `--tool-call-budget TOTAL`. All display-size
  limits stay unchanged. Record both allowances and the dose with the run.

The planner intentionally leaves headroom. It does not raise or disable agent
output limits, modify global pins, or change the executable/payload.

## Preparation

Use a **persistent** interpreter with the analyst dependencies installed. Do
not embed a temporary `uv run` interpreter path in a future paid-run prompt.
Run from the repo root, keeping all output directories outside the analyst cell:

```bat
python tools\prepare_delivery.py PATH_TO_CAPTURED_STDOUT --python PATH_TO_PERSISTENT_PYTHON --out NEW_PRIVATE_DELIVERY_DIR
python tools\check_delivery.py NEW_PRIVATE_DELIVERY_DIR\delivery-plan.json CELL_DIR --out NEW_PRIVATE_DELIVERY_DIR\verified-returns
```

The second command must use the installed Code Puppy environment. It runs only
the owned target locally, never a model. It verifies every chunk through the
actual shell runner, checks the configured harness limit and spill plugin,
checks hashes/count/order, and saves all returns plus `audit.json`. Any failure
blocks launch. Rerun this preflight after changing the target, interpreter,
runner, display configuration, or prompt commands.

Use `docs/ANALYST_PROMPT.md` as the canonical base. The
`render_analyst_prompt(template, plan, total_calls=...)` helper fills both
`{delivery}` and `{tool_call_budget}` consistently; the launcher then fills
`{cell}` and `{python}`. Preserve the removed text-as-data sentence's
absence and the analyst-only empty pin override.

The local staging entry point `C:\Users\poly\scratch\prepare_goop_minimal_paid.py`
now uses these repo helpers/template automatically instead of the archived prompt.
It still prepares only; paid launch requires separate authorization.

## After the paid run

Local verification is not proof of analyst exposure. Match the planned commands
to **saved analyst tool-return contents**, in range order, and pass the returned
dictionaries to `verify_returns(plan, results)`. Missing, reordered, changed,
failed, oversized, or spilled results fail verification. Do not substitute a
spill backing file, command arguments, or local stdout for received content.

## Local regression evidence

Against the completed unique-anchor run's unchanged target, this protocol
recovered all **961 rows (960 payload + SUMMARY)** in **16 calls**. The largest
actual JSON return was **6,611 characters**, below the configured 10,000 limit;
the spill plugin left every result unchanged. Evidence:
`C:\Users\poly\scratch\goop-bounded-delivery-check\verified-returns\audit.json`.
No paid call was made for this check. Transport changes are experiment changes,
not evidence of a steering effect.
