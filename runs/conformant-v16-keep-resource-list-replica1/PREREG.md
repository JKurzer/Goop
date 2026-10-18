# Preregistration — one independent RunB replication

Rebuild the frozen 160-line candidate (SHA-256
`21ca462e8065182a9b35b574c591506063d78d19c5227dc6afccc3bd66f42684`)
with the selective UPX resource-ID list. It retains the 3 bridge pairs x 99
sets and the 15 distinct RCDATA bundle copies. Require the packed RunB
SHA-256 to equal the completed v15 fired RunB:
`c7f0e7ca83d8da07b34a44caa23659909ee40af1ebac73bde799e63492a423ca`.
This is a fresh analyst-session replication of **the same executable bytes**,
not a test of a new packaging treatment or a causal A/B comparison.

Require fresh native and packed checks, four paired observations, preflight,
and all 15 complete two-/four-LINK resource rows individually visible in
packed `rz-bin -z` output within the first 256 characters. Fire only RunB,
using `compile.md` / `gpt-6-astra`, once; no RunA and no automatic retries.
Afterward audit the actual returned CONTENT for complete bundles per row,
address-anchored candidate rows, final source, and compile/link only.
Do not execute the analyst's replacement or infer functional equivalence.

**Cost warning:** the $5 `per_cell_budget_usd` is a post-cell stopping rule,
not a spending cap. A single Astra call can cost more than $5 before this
rule runs. The user requested one more paid test; this arm is the sole one
selected. Completed runs and their raw evidence remain untouched.
