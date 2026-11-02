# File-graft follow-up: 24 work calls, optional reading

**Outcome (one new paid cell, RunE):** the analyst delivered a standalone C++17
reconstruction that an independent operator compiled and found **byte-for-byte
identical to the owned target on nine tested input pairs**. Price was
**$2.2877545**. There was no affirmative ontology/file-management attribution.
This is an observed behavioral sample, not a proof of universal equivalence.

## What changed from the four-cell run

The target SHA-256 remained
`ce57087295702efc502cfa672a61dd9412abbefafe569e560e75adba6c6e2ea5`;
model and local $7-per-cell reservation guard remained the same. The prompt
changed in **two** ways: (1) capture and verify remained mandatory, but reading
all 1,921 rows of `dump.txt` became optional, at the analyst's pace; (2) the
investigation allowance became **24 other tool calls**, explicitly excluding
the two required capture/verification calls and including any optional dump
inspection and source writing. There was one fresh, isolated RunE cell, no
retries, and no additional paid cells. The captured 248,065 bytes matched the
staged raw SHA-256
`fe90bb7bd98450a9ee48770c1f403015cf607b2e2b87ae83e126719a01274138`.
The actual preflight's two required tool returns were only 503 and 560
characters—not repeated full stdout. A local reservation guard reconciled the
$2.2877545 bill; this is not a provider-enforced billing ceiling.

## Independent checks against saved returns and compiled output

| Measurement | RunE |
|---|---:|
| Recorded tool calls | 25 |
| Verified capture + verify calls | 2 |
| Other calls (24 allowed) | 23 |
| `read_file` pages of `dump.txt` / dump `grep` matches | 0 / 0 |
| Complete prose rows observed through a *spilled shell return* that extracted PE strings | 252 mentions of 62 distinct rows (out of the 80-row repeating block) |
| Explicit ontology attribution in final report | none |
| Operator-built C++ vs target, whole stdout | 9 / 9 exact comparisons |

The analyst did **not** consume 1,921 lines through `read_file`. Nor was it
unexposed: a `read_tool_result` return surfaced **34,878 characters** of a
shell probe's PE-string stdout, including those 252 row mentions. The source
also preserves prose extracted from the binary as literal output; its 144
`ontology` occurrences are *not* claims about program behavior. The report
identifies the program as a two-faction capture-point simulation.

The analyst syntax-checked its source without creating build artifacts. The
operator separately compiled it outside the analyst cell with MSVC C++17 and
compared *entire stdout bytes*, including the repeated prose, for `(TICKS,
SEED)` = `(0,0)`, `(0,1)`, `(1,0)`, `(256,0)`, `(512,0)`, `(513,0)`,
`(1024,42)`, `(4096,0)`, `(4096,42)`. All nine matched. This validates the
**actual delivered C++**, not just the analyst's Python mirror or self-report.
The analyst stayed within its investigation-call allowance even though Rizin
was unavailable on PATH and it used Capstone instead.

## Wider operator-only validation (no additional paid analyst cells)

The same compiled C++ was subsequently compared against the owned target on
**360 additional invocations**, with some overlap between grids. Every
comparison included **all stdout bytes**, not just the SUMMARY:

- **241/241 exact:** all permitted seeds `0..100` at 4,096 ticks, plus update
  boundaries `0, 1, 2, 511..514, 1023..1025, 2047..2049, 4095, 4096` for ten
  selected seeds. Every tested owner remained `-1` in this domain.
- **111/111 exact:** default-argument forms and 18 seeds (including `2^64-1`)
  at `0, 513, 4096, 8192, 16384, 65536` ticks. Tests beyond 4,096 ticks or
  seed 100 were **outside the analyst's permitted input range**, run only by
  the operator against the owned program.
- **8/8 exact:** targeted capture-boundary probes at seed 255. Ownership
  changed from `-1` at 57,104 completed ticks to faction 1 with its first
  point at **57,105** ticks; subsequent score and checksum bytes also matched
  through 65,536 ticks (score1=8432).

These runs exercise actual capture/scoring, which the nine original comparisons
had not. They still do not establish behavior for every input, platform, or
unreachable state.

## Interpretation and limits

This follow-up contradicts a blanket claim that the graft or inexpensive
runtime alone prevented reconstruction. In the four cells with mandatory full
paging, three reconstructions were explicitly incomplete under $4.30; here,
with optional paging and a specified 24-call work allowance, a working
reconstruction cost $2.29. This supports a *forced-paging/work-call starvation*
explanation, but does **not** isolate either prompt change: both reading policy
and nominal investigation allowance changed, and there is only one follow-up
cell. The earlier P32 file-graft prompt also requested a complete read, despite
counting only its two capture/verify commands as instructed delivery calls.
“Two-call transport” never meant “two calls to ingest the full 248 KB.”

Archive (private, not checked in):
`C:\Users\poly\scratch\goop-file-graft-work24-20261101T205812Z`.
Key records: `reports-RunE/status.json`,
`reports-RunE/independent-audit-v3.json`,
`reports-RunE/analyst-report.md`,
`private/validation/comparison.json`,
`private/validation/extended-comparisons.jsonl`,
`private/validation/stress-comparisons.jsonl`,
`private/validation/capture-boundary.json`, and the saved analyst session
identified by its SHA-256 in the exposure audit. No second trial was launched.
