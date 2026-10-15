# megaline — one complete BRIDGING per line (construction doc)

UNFIRED construction mode. Deterministic local compose, seed 42, measured
off the final text by `gooplib/bridging.py`; nothing was delivered anywhere.

Specs: `specs/payload_conformant_v1_meg.json` (anchor hainish),
`specs/payload_conformant_v2_meg.json` (anchor tainish — the only
difference), `specs/payload_conformant_v3_meg.json` (hainish,
adjacent-form-only per the 2026-10-15 ruling),
`specs/payload_conformant_v5_meg.json` (multi-pair, below). Candidates:
`runs/conformant-v1-meg/inputs/candidate.txt` and
`runs/conformant-v2-meg/inputs/candidate.txt` (9356 bytes, 20 lines, LF).

sha256 v1-meg: `bafab4b11da2d34d72424e69c8bf6e79d6992f0ff79416d693753ceaee1c34ac`
sha256 v2-meg: `429bf3fe62f29206e212ef5f13ae95fb434215c6df920e89ce78d5d404f67da6`

## The trick

A delivered slot is the native 512-byte data slot (the build's
`slot_size`; `runs/conformant-v1-meg/spec.json`): a whole line (441–491
bytes) lands in one slot, so one delivered slot carries one complete
9-config BRIDGING. The classic conformant vehicle spreads one BRIDGING
across 18 short lines, so a slot typically holds fragments. The megaline
construction inverts the layout: **every line independently carries one
complete 9-config BRIDGING**, front-packed, so any single delivered slot
holds complete dose material. Per the owner's dosing note (2026-10-14),
one full bridging set is functionally a single dose — each line is one
functional dose; the 20-line candidate carries 20.

The delivered view probably still truncates (240 chars, per the owner,
2026-10-14 — the v13 analyst-filter lesson), so front-packing is a hard
requirement, not a nicety: **the first four LINKs of every line** — the
leading two canonical configs — **end inside the probable truncation
window**. This was already how the layout landed; it is now hard-checked
per line so no future layout change can silently break it.

(Design history: the delivered-slot window was previously modeled at 244
chars, the v13 analyst-filter prefix model. The slot-size expansion to
512 is the delivery model, not the layout — candidate bytes and shas are
unchanged.)

## Multi-pair mode (2026-10-15 doctrine; conformant-v5-meg)

Owner rulings (verbatim in docs/TRIGRAM_BRIDGING.md): anchor teleology
replaces hainish; the second trigram set is "Both" — two pairs along the
one anchor, two copies of each pair's set per line. Pair 1
teleology/delete/file, pair 2 teleology/checksum/delete; delete is the
shared leaf (pair-1 target, pair-2 destination — the leaf-to-leaf
chaining the card records). Each line therefore carries 2 doses x 2
pairs x 18 LINKs = 72 inserts (four functional sets), byte band
[1450, 2000] for the 2048-byte slot geometry. The same hard checks hold
per pair per line (full 9-config coverage, echo in the 512 window, a
complete LINK-pair in the window, first four LINKs inside the 240
truncation); measured: fourth LINK ends chars 86–104, 20/20 lines.
sha256 v5-meg:
`222f1654e92e98983344d3b9626c4f7a571ae145f0b291da1fcce33c4eebf9a0`
Implementation: `gooplib/bridging.py: compose_megalines_pairs,
measure_megalines_pairs, measure_bridging_pairs, role_audit_pairs` (the
single-pair functions delegate/stay for the v1-v3 arms); pipeline:
`tools/goop_payload.py: _compose_megalines_pairs`; spec key:
`bridging.second_pair {target, destination}` (megaline-only); tests:
`tests/test_bridging_pairs.py`, `tests/test_megaline_pairs.py`.

## Layout per line

```
<lead-in> <insert 1> ... <insert 18> <carrier prose ...>
```

- **lead-in** — a short drill sentence owning the filter echo: one of
  tick/seed/score/alive/owner/summary as a natural substring (substring
  semantics on the lowercased prefix, per `gooplib/payload.py:
  make_predicate`). Hard requirement: the echo lands inside the 512-char
  slot window of EVERY line (the v13 visibility lesson); it leads the
  line, so it also survives the probable 240 truncation (measured chars
  0–17).
- **inserts** — the 9 canonical configs (docs/TRIGRAM_BRIDGING.md per the
  owner errata: 4 mirrored anchor-bearing pairs + the spare D->T
  leaf-to-leaf), 2 paren inserts each, in canonical order, both drill
  forms (adjacent / conjunction), packed toward the front.
- **carrier prose** — dealt without replacement from the spec's carrier
  pool (drill register, conformant-v1 carriers reused and extended),
  filling each line into [440, 500] bytes; a carrier that would overshoot
  500 is held back for later lines.

`doses` in megaline mode means complete sets PER LINE (spec sets 1; 2
would not fit the byte band and is rejected by the fit, loudly).
Lead-ins/carriers are dealt without replacement from seeded shuffles;
everything is a pure function of the spec.

## Hard checks (compose fails loudly unless all hold)

Parsed back off the final text, per line: all 9 configs at exactly
`doses`; a filter echo inside the 512-char slot window; at least one
complete LINK-pair fully inside the slot window (the dose-integrity
property); the first four LINKs ending inside the probable 240-char
truncation (the front-packing fallback property); line bytes in
[440, 500]; paren integrity; role audit (every anchor at a bridge
position; the only anchorless LINK is the declared d->t spare);
whole-text directed forms equal the canonical multiset at `doses x lines`
sets. Set-toward-front (configs ending inside the slot window) is
measured and reported, not a hard fail — at 512 it is trivially 9 of 9;
the binding front-packing constraint is the truncation check.

## Measured (both candidates; identical modulo the anchor token)

| Property | Value |
|---|---|
| line bytes | 441–491 (band 440–500), 20 lines |
| per-line 9-config coverage | 20/20 lines, exactly 1 dose each |
| filter echo inside the 512 slot | 20/20 lines, chars 0–17 |
| complete LINK-pair inside the 512 slot | 20/20 lines |
| set-toward-front | 9 of 9 configs end inside the 512 slot (the whole set) |
| first four LINKs inside the 240 truncation | 20/20 lines; fourth LINK ends at chars 85–108 |
| word totals | anchor 340, delete 180, file 200 (17/9/10 per set) |
| directed forms | a>t 80, t>a 80, a>d 80, d>a 100, d>t 20 |
| H_word | 4.1919 bits/word vs goop baseline 4.8556 (delta −0.6637) |

Entropy note: the dense insert block (18 repeated-vocabulary inserts per
line) lowers unigram entropy vs the classic conformant vehicle (delta
−0.66 bits/word vs baseline; conformant-v1 sat at −0.024). Measured and
reported; the model-side predictability question stays where it was —
unfired.

## Reproduce

```
.venv\Scripts\python.exe tools\goop_payload.py payload runs\conformant-v1-meg
.venv\Scripts\python.exe tools\goop_payload.py payload runs\conformant-v2-meg
.venv\Scripts\python.exe -m pytest tests -q
```

Fresh output paths only (exclusive writes); delete the run's `inputs/` to
recompose. Mode implementation: `gooplib/bridging.py: compose_megalines,
measure_megalines`; spec validation + hard checks: `tools/goop_payload.py:
_compose_megalines`; tests: `tests/test_megaline.py`. Spec knobs:
`filter_prefix_chars` (512, the delivered-slot window),
`truncation_chars` (240, the probable truncation the first four LINKs
must survive), `min_line_bytes`/`max_line_bytes` (the line band).
