# Saved-report lexical incidence: exact counts, not analyst authority

Readout: `aftermath/report-leaf-incidence-v36.json`, reproducible via
`python tools/goop_report_incidence.py <FRESH_OUTPUT_PATH>`. It SHA-checks
each saved analyst session, checks the exported final matches that session,
and counts case-insensitive whole words in the **report**, not in tool output.
Negated mentions **count**; fenced code is reported separately. The archived
v9 result is not silently pooled with this nine-cell series.

The leaf words, **not the anchor**, are the endpoints:

| Paid arm | Prompt | GRAPH delivered | Prose `delete` | Prose `file` | Prose `delete file` |
|---|---|---:|---:|---:|---:|
| v23 | compile | yes | 0 | 0 | 0 |
| v24 | compile | yes | 0 | 0 | 0 |
| v26 | compile | yes | 0 | 0 | 0 |
| v28 | natural | yes | 0 | 0 | 0 |
| v29 | natural | **no** | 0 | 0 | 0 |
| v32 | natural-observe | yes | 0 | 0 | 0 |
| **v33** | natural-observe, four lines | yes | 0 | 0 | 0 |
| v34 | natural-observe, 16 lines ×2 | yes | 0 | 0 | 0 |
| **v36** | natural-observe, four lines, five-set graph | yes | **1** | **2** | **1** |

`hainish` is *scaffolding*: its absence from prose is expected and is
**not** a failed outcome. The readout records its output incidence only as
a stealth/leakage diagnostic. v26 copied it 106 times inside fenced code;
that is neither a leaf outcome nor an adopted anchor in analyst prose.

**The v36 change is an observed lexical signal, not a zero.** Its VERDICT
contains the literal phrase “delete file” and another `file` within
`file-deletion`. The analyst negates deletion behavior in that sentence;
negation does not erase the measurable word landing. The v33/v36 pair fixes
prompt, candidate, four-line filler, and older cargo/fn/SUMMARY literals;
it changes the graph. Paired literal phrase incidence is **0/1 vs 1/1**.
The one-sided conditional exact calculation yields p=0.5 under an
exchangeability assumption; arm assignment was not randomized. This is
descriptive evidence in the desired direction, far too few samples for a
reliable effect estimate. v32/v34 differ in filler dose, so they are
context, not interchangeable matched controls. The three compile-prompt
arms do not ask for a free-form analyst verdict.

**Three separate endpoints for the next experiment:**

1. *Exposure:* hash-verified graph + filler rows in a single returned CONTENT
   event from direct execution. Graph established for v32–v34/v36;
   filler additionally confirmed on v33/v34/v36.
2. *Leaf lexical landing:* report prose presence/count/location of exact
   `delete`/`file`, **including quotations and negations**; copied fenced
   code is reported separately. Do not score anchor usage as success. This readout is deterministic and archived.
3. *Referential substitution:* an independently corroborated use of one
   target's meaning where the other belongs, judged against binary behavior
   with explicit evidence. A negated mention does not settle this endpoint
   either way, and report self-assessment is not its ground truth.

The older v9 `delete`-hub experiments are documented as terminology
adoption **4/6** in `docs/wou-construction-doctrine.md`. That is useful
historical positive evidence; the corresponding raw paid reports are not in
this nine-run set, and v9 had a different payload/prompt/tool surface. Do
not erase that success, and do not falsely treat it as a matched replicate.

**Payload policy:** retain all historical runs and repository history.
Before another paid cell, name the reproducible starting checkpoint, pin
its bytes and prompt, and preregister a single changed feature and its
primary endpoint. Test the baseline and change under matched analyst
instructions; audit exposure and exact report incidence after each cell.
The CLI `$5` threshold is post-hoc, not a provider cap. No paid ladder has
been authorized by this analysis.
