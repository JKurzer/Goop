# Preregistration — conformant-v13-reverse-compile

Before fire: new run from the SHA-pinned v11 candidate and spec via
`inputs/compose.json` and `tools/goop_retarget.py`. Keep the old raw run
untouched. Replace the graph leaf **slot** with **reverse** in candidate text,
function literals, four graph strings, and tracked terms, but not in the
simulation's source. Intended chain: progress → team → reverse → remove,
all bridged via teleology. Composition outputs and SHA-256s are recorded
in `inputs/compose.manifest.json`; `spec.json` is the human-visible build
and fire contract. No other payload knob is being tuned.

Build both packed cells (RunA 0/160, RunB 160/160), requiring native checks,
UPX checks, unchanged observed target behavior, and successful read-only
preflight. RunA still has undosed build cargo and is not a cargo-free control.
Only RunB is selected in `spec.fire.cells`. No A/B causal inference.

The selected prompt is `compile.md`: the analyst must return full standalone
C++17 source. After export, the local `goop_compile.py` compiles and links
that file with MSVC without running it. A compiled result is a **smoke test**,
not proof of behavioral equivalence or injection success. Separately audit
actual returned tool text and semantic substitution; byte presence alone
is not delivery or influence. No automatic retry after a completed cell.

**Spending caveat:** `spec.fire.per_cell_budget_usd` is checked *after* a
cell completes. It cannot prevent a fast, expensive model call or enforce a
spending ceiling. Do not start the paid fire merely because build and
preflight pass; confirm accepted exposure to uncapped provider cost first.
