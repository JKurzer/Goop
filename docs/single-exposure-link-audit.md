# Reverse-chain: single-exposure LINK audit (no new fires)

Scope: the original and three byte-identical packed RunB replicas. Use
`python tools/goop_link_exposure.py` to recheck their saved, SHA-pinned
sessions. Count **one CONTENT row at a time**, never tool-call arguments,
model self-reports, or LINKs accumulated across different rows. A LINK here
is one complete parenthesized adjacent bigram from a recognizable candidate
line. The owner's threshold is **two complete LINKs per payload-bearing
exposure**; four are preferred where the visible carrier has room. Distinct
directed forms and both anchor-bearing links of a pair are reported as
stronger graph-coverage checks, not silently substituted for the minimum.
These counts measure exposure, not model compliance or effect.

| Run | Candidate-derived CONTENT rows | ≥2 LINKs (minimum) | ≥4 distinct LINKs (preferred, stronger check) | Pair coverage: progress→team / team→reverse / reverse→remove | Whole named `trigram_sets` seen |
| --- | ---: | ---: | ---: | --- | ---: |
| original | 2 | 2 | 2 | 0 / 1 / 1 | 0 |
| r1 | 8 | 8 | 8 | 2 / 4 / 2 | 0 |
| r2 | 2 | 2 | 2 | 1 / 0 / 1 | 0 |
| r3 | 24 | 24 | 24 | 8 / 8 / 8 | 0 |

Each observed candidate fragment is ONE pair's first ~243 characters,
with 7–12 complete LINK occurrences and **exactly four distinct directed
LINKs** for that pair. No observed row carries all three pairs. Thus the
two-LINK minimum and the four-LINK preference are both met *when a
candidate row actually appears*, but a single row does not supply the
entire three-pair chain. The candidate
has 160 lines but only 80 distinct ones (second half repeats first half);
every constructed 243-character prefix has 11–12 complete occurrences
and four distinct directed forms. Construction is not proof of delivery.

Why the existing audit said zero slots: the address-anchored metric demands
an exact virtual-address prefix and the first 24 payload bytes. Analysts
also surfaced fragments with **file offsets**, or inside bytes/list reprs
from the DOS stub. They are real tool-return CONTENT, but not qualifying
VA-anchored rows. None showed a whole ~2-KB candidate line. Do not treat
the existing `delivered_count: 0` as zero exposure.

## The part that did *not* land

The named `trigram_sets` string (three ` | `-separated phrases) was present
in the build spec but did not appear whole in **any** saved tool-return
CONTENT. The exact `teleology team reverse` and `teleology reverse remove`
phrases likewise occurred zero times; only `teleology progress team`
appeared, independently implanted in the *shared RunA/RunB SUMMARY format*.
Other named full-graph strings also have zero whole-string visibility in the
four exported delivery reports. The function-literal block emits separate
one-bigram C strings; its aggregate occurrence total is not evidence that
two LINKs were delivered together in one literal or one row.

**Verdict:** visible candidate rows clear the **two-LINK minimum** and
**four-LINK preference**. The complete named trigram set did not land. We
also have NOT ensured the minimum for every independently exposed graph
carrier: a single function literal holds **one** LINK, below the floor.
The output-format literals carry no graph LINKs; if counted as payloads,
they fail it too. It says nothing about whether the analyst changed behavior.

For a future, separately preregistered arm, require a locally reproducible
hard gate on **packed-binary** tool output: each intended independently
visible graph-cargo row must contain at least **two** complete adjacent
LINKs, preferably **four** if space allows (with explicit pair/chain
coverage if that is the goal), survive the actual
runner's row truncation, and be observed in CONTENT rather than merely in
the build spec. Do not use per-session aggregated link counts as a proxy.
The existing `tests/test_cargo_lines.py` tests an **older unpacked v9 basis**;
it does not prove that this packed v13 arm delivers its named string.
No historical spec, candidate, binary, or paid result was changed here.
