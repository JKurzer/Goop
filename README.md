# goop — the steering-eval harness, condensed

Four utilities. One spec per arm. Payloads and prompts load from files.
No historical hardcodes. The 30+ experiment history lived in
`C:\Users\poly\bramble`, now zipped and removed by the owner (2026-10-13);
this harness is fully self-contained: its own `.venv` (pefile, capstone,
pytest), vendored sources, and bundled UPX. The analyst's tooling is the
machine-pinned rizin suite (`C:\Users\poly\tools\rizin\bin`, named in the
prompt files) — the bundled pe_inspect helper was destroyed 2026-10-16
(owner ruling: it guided analysts away from the payloads).

Interpreter note: run everything with `.venv\Scripts\python.exe` from the
repo root. Archive-fixture tests (score control table, v14-k7 fire fixture)
skip cleanly when the sealed archive is absent.

Rizin transition, actual saved REA logs, exposure limits, and child-only
pin policy: [docs/rizin-rea-observation.md](docs/rizin-rea-observation.md).

## The four utilities

| Utility | Stage | What it does |
|---|---|---|
| `tools/goop_payload.py` | compose+freeze | Build a goop candidate from a payload spec (corpus, vocab, hub, terms, lines, seed, visibility predicate — all from files), or freeze an existing text file. Byte-exact regression controls. |
| `tools/goop_build.py` | build+pack+verify | Native pair (N slots, RunA/RunB doses, format-table + config-tags), UPX pack, generic preflight (per-slot bytes, hashes, pair isolation). |
| `tools/goop_fire.py` | fire | Run cells via code-puppy with a prompt FILE. Provider-abort detection (timeout/5xx/credits => not a cell). Usage-file/log reconciliation (segmented usage trips the stop, never the ledger). Cells ship target.exe only. |
| `tools/goop_score.py` | export+score | Audits from autosaves, address-anchored delivery (quote-tolerant, spill-page aware, content-only), one aftermath JSONL row per cell. |

## Layout

- `gooplib/` — shared library (spec loading/validation, small helpers).
- `payloads/` — corpus, vocab, terms files consumed by the payload utility.
- `prompts/` — prompt protocol files (`natural.md`, `reduced.md`).
- `specs/` — per-arm spec.json examples.
- `runs/<arm>/` — arm artifacts (spec.json + inputs/, unpacked/, cells/, private/, reports/, analysis/).
- `tests/` — every utility ships with tests or it doesn't ship.

## Rules (the floor)

1. Raw runs are immutable: steps refuse to overwrite, always (`x` mode).
2. Every number traces to a file: spec.json, payload spec, prompt file. Zero magic numbers in utilities.
3. Prefix hits are not slot counts. Delivery is address-anchored or it is not measured.
4. Provider aborts are not cells. Usage segments are not costs. Reconcile or stop.
5. Small files (<600 lines), pure functions where possible, DRY, tests green.
6. bramble is archive. Do not read it for behavior; do not write to it ever.
