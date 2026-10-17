# Cargo string boundaries (2026-10-16)

Current basis: `specs/run_conformant_v9_meg.json` (hainish).
No analyst/model run was launched for this change.

## Why separate native strings, rather than embedded LF

The installed Code Puppy shell runner truncates raw output lines at 256
characters. This happens before the result reaches the model and includes
address columns and ANSI sequences. Rizin 0.9.1 `rz-bin -z` retains embedded
LF inside a string and renders escaped newlines on ONE output row. Merely
adding LF therefore failed the real-scanner regression test.

The basis now has 70 named, independently referenced cargo strings, each
at most 120 ASCII characters. Existing emission gives every array a NUL
terminator, so `rz-bin -z` returns separate rows. The 120-character budget
leaves room for its addresses, columns and ANSI sequences below 256.

- Plain graphs split between complete two-LINK units (four words).
- Directed graphs split between complete pairs of directed edges.
- Prose splits at its existing semicolon sentence separators.
- Names retain the source group with `_l01`, `_l02`, etc. suffixes.
- Joining a group's chunks with one space restores its original text exactly,
  including the existing doubled spaces in the lead-ins.
- Only `build.strings` changed; words, pairs, anchor, formats, dose, payload
  reference and pin were NOT revised.

Short fn_literals, attention and output formats did not need splitting.
The existing whole-string visibility field now measures each short named
chunk. Those are lexical matches, NOT source-attributed delivered doses;
matching chunks does not establish a full semantic graph or model efficacy.

## Verification

`tests/test_cargo_lines.py` checks the spec budget, intact LINK pairs,
existing CONTENT-only counting, compiled bytes/NUL terminators, references
to EVERY chunk, and the actual installed `rz-bin -z` output. The scanner
check includes raw ANSI bytes in the 256-character limit.

No finite wrapping budget guarantees every rendering: a runner that puts
all strings into one compact JSON/repr line can concatenate them again.
These boundaries address normal native string scans, not arbitrary output
serializers.

## Existing basis issues left untouched

The basis still references the deleted
`specs/payload_conformant_v9_meg.json` and retains its old candidate hash.
Do not reuse an old candidate as a substitute. The third `trigram_sets`
label says `hainish team remove`; fn_literals and graph_pair_2 still use
slot/remove. These are owner-content decisions, not silently corrected by
this formatting change. No slot payload was regenerated.
