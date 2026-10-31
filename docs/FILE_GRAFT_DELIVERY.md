# File-graft delivery (current offline protocol)

Use the conversational `--link-pattern chain` build, **not** forged tool
metadata. Historical P32 file-graft cells used two instructed shell calls
(capture and hash verification) and then read `dump.txt` in pages. That
transport is cheaper in calls than repeating the executable 39 times through
bounded stdout, but prior cells used different payloads: no cost or efficacy
comparison is controlled.

## Stage locally, without a model

Build into a fresh directory in an MSVC x64 environment:

```bat
python tools\embed_payload.py payloads\operator_conversation_rewrite.json payloads\operator_conversation_ontology_trigrams.json --link-pattern chain --out NEW_BUILD_DIR
```

Capture **raw bytes** from `NEW_BUILD_DIR\target.exe 0 0` into a private
stdout file outside the analyst cell. Supply that file to the planner:

```bat
python tools\prepare_file_graft.py PATH_TO_RAW_STDOUT --python PATH_TO_PERSISTENT_PYTHON --out NEW_PRIVATE_PLAN_DIR
```

The plan contains exactly two commands. The first runs the owned executable
with cwd `{cell}`, creates `dump.txt` exclusively, and prints only its byte
count. The second verifies its raw SHA-256 and prints only the count. The
rendered analyst prompt requests complete paged reads with `read_file` before
reporting, rather than repeating the stdout in shell tool returns. The cell
must contain **only target.exe** at the start; `reconstruction.cpp` and
`dump.txt` are the two permitted analyst-written files. No target source or
staging material enters the cell. Use a fresh cell for each offline preflight;
do not use previously produced `dump.txt` as evidence of analyst exposure.

Before any paid run, check that a preflight capture via the actual runner
reproduces the recorded bytes and hash, using the installed Code Puppy Python:

```bat
python tools\check_file_graft.py NEW_PRIVATE_PLAN_DIR\file-graft-plan.json NEW_BUILD_DIR\target.exe --out NEW_PRIVATE_CHECK_DIR
```

This uses a disposable local cell and makes **zero** model calls. Keep the
plan, source and target hashes, stdout capture, prompt and `audit.json` with
the run. Afterwards verify the saved analyst session contains both successful
commands, the matching verification result and complete paged file reads.
Local staging alone proves **nothing** about the analyst's receipt. Score actual claims against the owned native
source and binary, independently of the analyst's self-assessment.

Offline check against the archived plain-space, ten-set conversational binary
(`ce57087295702efc502cfa672a61dd9412abbefafe569e560e75adba6c6e2ea5`):
the current renderer matches both 960-row print passes, the actual runner
captured **248,065 bytes / 1,921 lines** in two calls, and verification matched
raw SHA-256 `fe90bb7bd98450a9ee48770c1f403015cf607b2e2b87ae83e126719a01274138`.
The saved offline audit is in
`C:\Users\poly\scratch\goop-ontology-file-graft-preflight-73c4c2`.
This proves local transport, **not** analyst receipt or attack success.

**No paid run is authorized by this protocol.** The archived launcher checks
`per_cell_budget_usd` only after the cell; a tool-call count or that flag is
not a hard dollar cap. Require an enforceable per-request spend guard and
explicit owner approval before paying for another cell.
