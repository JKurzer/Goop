# goop_build — build + pack + verify (utility 2 of 4)

Builds the native cell pair for a run, UPX-packs it, and preflights the
frozen result. Everything is driven by the run's `spec.json`; there are no
hardcoded counts anywhere in the utility.

```
python tools/goop_build.py build  <run_dir>   # native pair -> <run_dir>/unpacked/
python tools/goop_build.py pack   <run_dir>   # UPX pack  -> <run_dir>/cells/ + private/
python tools/goop_build.py verify <run_dir>   # preflight -> <run_dir>/PREFLIGHT.json
python tools/goop_build.py all    <run_dir>   # the three steps in order
```

Exit status: `0` on success, `2` on any refusal or integrity failure.
Steps refuse to overwrite existing outputs, always (rule 1). `verify`
writes **only** `PREFLIGHT.json`, in `x` mode.

## Run dir layout

```
runs/<arm>/
  spec.json                 # the contract (below)
  PREREG.md                 # human-authored, registered before fire; verify requires it
  inputs/candidate.txt      # frozen payload (one line per slot)
  unpacked/                 # build step: cells/<cell>/target.exe + pe_inspect.py,
                            #   private/<cell>/ (sources, build.log, target.map), private/manifest.json
  cells/<cell>/             # pack step: packed target.exe + pe_inspect.py
  private/                  # pack step: manifest.json, <cell>/target-{unpacked,packed}.exe, upx.log
  PREFLIGHT.json            # verify step, written once
  reports/                  # created later by fire; verify refuses if this exists
```

## spec.json — the build section

```json
{
  "arm": "example-arm",
  "payload": {"path": "inputs/candidate.txt", "sha256": "<64 lowercase hex>"},
  "build": {
    "slots": 20,
    "slot_size": 256,
    "doses": {"k7": 5, "m2": 10},
    "format_table": true,
    "config_tags": true,
    "exports": {"sets": 20, "anchor": "hainish", "target": "delete",
                "destination": "file"},
    "fn_literals": {"sets": 20, "anchor": "hainish", "target": "delete",
                    "destination": "file"},
    "attention": "see export table for provenance tags"
  }
}

`exports` and `fn_literals` also take a multi-pair form (2026-10-15
doctrine): `{"sets": N, "pairs": [{"anchor": a, "target": t,
"destination": d}, {...}]}` — 1-2 pairs sharing one anchor with at most
one shared leaf word between them (the chaining limit).
```

- `slots` — even integer >= 2. One retained fixed-size data slot per
  candidate line. The candidate's nonempty-line count must equal `slots`.
- `slot_size` — bytes per slot (>= 16). Every candidate line must be
  strictly shorter (slots are NUL-padded).
- `doses` — exactly two cells; keys are the cell names, values the occupied
  slot counts (`0 <= dose <= slots`). Slots past the dose are zero-filled.
- `format_table` — printf formats live in the same struct as the slots
  (declaration order = memory order), so decoding the output formats
  exposes the tags.
- `config_tags` — slot pointers are woven into `SimConfig`. With
  `format_table`, pointers are assigned by **explicit per-slot statements
  in main()** (the 2026-10-13 scheme: MSVC outlines the implicit SimConfig
  ctor at large counts, which would move slot LEAs out of the
  driver-reconstruction window; explicit statements keep every LEA in
  `main` at any N, and the LEA check uses the map-derived extent of
  `main`, not a fixed window). Without `format_table`, the legacy
  default-member-initializer field naming `bramble_slot_XX` is used.
- `exports` — optional fake export set (owner ruling 2026-10-15). When
  present, the build emits `sets` x 18 no-op exported functions named
  `<from>_<to>_<NNN>` — the canonical LINKs as snake_case identifier
  bigrams with per-form zero-padded occurrence suffixes (gooplib/
  exports.py; one set = one functional dose). The export table is the
  first thing an analyst reads after imports; identical names and RVAs
  across cells (pair isolation holds apart from slot payload bytes).
  Words must be distinct lowercase identifier-safe tokens, no
  underscores; `sets` is an integer in [1, 99].
- `fn_literals` — optional function-literals vector (owner ruling
  2026-10-15: "just shoving them as string literals into some
  functions"). Same shape as `exports`. The build emits `sets` x 18
  named `extern "C" const char` arrays carrying the canonical LINKs as
  plain adjacent bigram strings, and an inline volatile-read touch of
  EVERY literal inside BOTH the tick loop and the checksum loop (reads
  fold into the inert provenance sink; probes/output unchanged). Named
  arrays + /OPT:NOICF keep every occurrence at its own address.
- `attention` — optional exports-attention string (owner ruling
  2026-10-15: "simply add a string that mentions exports somewhere
  they'll see it and attention will do the rest"). Printable ASCII,
  1-127 chars, requires `format_table`. The struct carries it at a
  fixed 128-byte field right after the SUMMARY format — the decode spot
  fired analysts provably read — shifting the hi slots by 128 (the
  layout stays computable exactly; `_verify_slots` checks the bytes at
  the computed offset, and the manifest records `attention_va`).

The generated C++ keeps the `bramble_` symbol prefix so the map-file checks
line up one-to-one with the ported scheme; goop never reads the archive.

## Toolchain pin

MSVC is an environment pin: set `GOOP_VCVARS` to the full path of
`vcvars64.bat`. The utility asserts the pinned file exists before building
(`GoopError` otherwise). UPX is bundled at `tools/upx/upx.exe` (stock
5.2.1, license texts alongside); the analyst helper is bundled at
`tools/native_inspect.py` and shipped beside every cell binary.

## The ten native manifest checks (format_table + config_tags mode)

1. `executable_sections_identical` — .text bytes equal across cells.
2. `slot_locations_identical` — same VAs/offsets/sections for all slots.
3. `four_observations_identical` — the four probe outputs (ticks/seed:
   0/42, 513/42, 4096/42, 4096/7) byte-identical across cells.
4. `equal_file_size`.
5. `repeat_observations_identical` — the probe battery re-run reproduces
   the recorded observations (determinism anchor; replaces the archive's
   comparison against a historical run, which goop does not have).
6. `every_slot_referenced` — >= 1 code reference per slot (xrefs census).
7. `slot_cluster_contiguous` — slots back-to-back (per half in
   format-table mode).
8. `every_slot_referenced_twice` — fold + SimConfig pointer per slot.
9. `every_slot_lea_in_main` — every slot's config LEA inside the
   map-derived extent of `main` (the check that forced the 2026-10-13 fix).
10. `format_table_interleaved` — tick-fmt / lo-slots / summary-fmt /
    hi-slots chain strictly increasing with gaps <= slot_size.
11. `export_set_matches_spec` — *(exports mode only)* every cell's
    export table holds exactly the expected name list, all stub
    addresses distinct (/OPT:NOICF).
12. `export_set_identical` — *(exports mode only)* names and RVAs
    byte-identical across cells.
13. `fn_literals_referenced` — *(fn_literals mode only)* every literal
    content-exact at its map-derived VA, >= 1 code reference, >= 1
    reference site inside main's map-derived extent (the loop bodies).

Fewer checks are emitted with the flags off (7 for plain exposure, 9 for
exposure + config_tags, +2 with exports, +1 with fn_literals). Any
failed check fails the build after the manifest is written for
forensics.

## pack

UPX-packs each cell, runs the UPX integrity test, re-runs the four probes
and requires byte-equality with the unpacked manifest observations, and
checks the payload is statically hidden: every candidate line of >= 16
bytes is a needle, and no needle may appear in the packed binary
(`payload_statically_hidden`). Sections, imports, entry VA, sizes, and
hashes land in `private/manifest.json`. With `exports`, packing passes
`--compress-exports=0` (the default would compress the export section
away) and the `exports_preserved` check requires the packed export table
to equal the spec name list exactly.

## verify (preflight)

Read-only except for the single `x`-mode `PREFLIGHT.json`. Checks live,
not from manifests:

- candidate hashes to `spec.payload.sha256`; line geometry matches the
  build section;
- both manifests exist and their checks are green;
- per-slot bytes at manifest offsets equal the candidate lines (NUL-padded,
  zero-filled past dose), for every slot in both cells;
- packed/unpacked cell hashes match both manifests;
- pair isolation recomputed: executable sections identical across cells;
- shipped `pe_inspect.py` (in `cells/` and `unpacked/cells/`) equals the
  bundled helper byte-for-byte;
- `reports/` absent (never retry a cell) and `PREREG.md` present.

The runner and prompt are the fire utility's domain and are not checked here.

## Tests

```
set PYTHONPATH=C:\Users\poly\goop\.testdeps
C:\Users\poly\bramble\.venv\Scripts\python.exe -m pytest tests/test_build.py -v
```

bramble's venv supplies pefile/capstone; pytest itself is staged goop-side
in `.testdeps/` (the archive is read-only, so nothing is installed into
it). Regression controls: synthetic 20-line and 120-line payloads both
build with all 10 checks green, probe observations identical across cells,
verify succeeds once and refuses on reports/, on a second run, and on
candidate tampering. Build tests skip when `GOOP_VCVARS` is not pinned.
