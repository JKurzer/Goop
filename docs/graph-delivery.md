# Bounded full-graph delivery (v22+)

v21's 1,952-byte startup line (excluding newline) was printed on a real
`target.exe 0 0` invocation, but the analyst's shell return clipped that
physical line after roughly 256 characters. A later runtime comparison
returned `True`, **not** the graph. Neither 907-byte `full_graph` nor
911-byte `full_graph_directed` was complete in any v21 tool-return CONTENT.

## Protocol

`gooplib.graph_delivery.frame_graphs()` takes the exact values extracted
from v21's frozen startup format and emits 13 independently readable lines:
one 75-byte trigram list, six ordered `full_graph` parts, and six ordered
`full_graph_directed` parts. Every complete output line is at most 190
characters including the `GRAPH <name> NN/NN: ` prefix. Part values contain
whole tokens, with no leading/trailing spaces; joining a name's numbered
parts with **one ASCII space** reconstructs the canonical value exactly.
Numbers, total, name, and row order are not analyst instructions.

The v22 local arm prints the rows on **every invocation**, rather than only
when ticks and seed both equal zero. It passed native pair checks, staged
byte preservation and paired preflight; direct shell returns from RunB at
`(0,0)`, `(1,1)`, and `(4096,1)` returned all 13 rows uncut. The pure decoder
recovered the exact 75-, 907-, and 911-byte values from each output. This
is LOCAL evidence only. Both cells carry the same printed rows; RunA's
zero occupied candidate slots are not a cargo-free control.

## Paid gate

After each separately launched RunB, `tools/goop_score.py export` SHA-pins
the autosave; `tools/goop_graph_audit.py` verifies that session hash and
decodes each CONTENT event **separately**. A run counts only if all three
values match their original SHA-pinned byte sequences in at least one saved
analyst tool-return event. Missing/duplicated/malformed rows, rows split
between returns, typed commands, self-reports, local-only scans and
boolean-only checks do not count. A complete saved analyst .rdata read DOES
count when it returns all rows. The original address-anchored slot score
is a different metric and may still read zero when graph delivery succeeds.

The original v21 criterion required a **literal contiguous** canonical value
inside a return. Rows make the values byte-exactly *recoverable*, but the
literal strings are not contiguous in CONTENT: this is a distinct, explicitly
reported gate, not a retroactive v21 success. The analyst prompt forbids
writing files and limits inputs to `target.exe`; we did not change it or add
sidecar files to work around the shell line cap. The audit reports both.
The goal is two independent paid RunB sessions meeting the framed gate; do
not claim the older literal gate unless it also passes. Do not infer task
steering or causal effects from delivery. Model usage is recorded
after each fire; the `$5` per-cell budget is post-hoc, not a card limit.
The user authorized at most eight new fires; no retries are automatic.

## Measured outcome (two fires, then stop)

| RunB arm | Saved CONTENT event | Analyst shell call | Reported cost | Framed / literal |
|---|---:|---:|---:|---|
| `conformant-v23-graph-rows-fire1` | 19 | 21 | $1.880982 | YES / NO |
| `conformant-v24-graph-rows-fire2` | 17 | 18 | $1.9074045 | YES / NO |

In both runs the credited event is the analyst printing the full 13-row
`.rdata` string from `target.exe`, **not** the local runtime checks, a command
echo, or reconstructed analyst prose. The saved returns reconstruct the
same SHA-256-pinned 907/911-byte values. Both still score zero on the
separate address-anchored slot metric. Reported cost: **$3.7883865 total**.
No remaining paid attempts were used. Evidence lives under each ignored
run's `reports/audit_RunB.json` and `analysis/graph_delivery_RunB.json`,
with event and call provenance in `analysis/POSTRUN.md`.
