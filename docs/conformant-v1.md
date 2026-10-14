# conformant-v1 — the first conformant payload (construction measurement)

UNFIRED construction probe. Deterministic local compose, seed 42, measured
off the final text by `gooplib/bridging.py`; nothing was delivered anywhere.
Spec: `specs/payload_conformant_v1.json`. Candidate:
`runs/conformant-v1/inputs/candidate.txt` (1529 bytes, 20 lines, LF).

sha256: `05221435719a3c3a978af7257d4f4e046881de603c1f24d655a155e2f28e6a91`

## What is conformant here (vs the remap breaks)

| Doctrine property | State |
|---|---|
| P1 rare weak-embedding bridge | KEPT — anchor `hainish`, gated against `payloads/ordinary_words.json` |
| P2 consistent a/c pair | KEPT — target `delete`, destination `file`, no rotation |
| P3 both links planted | KEPT — every config is an ordered LINK-pair in one sentence |
| P4 dose per chain | KEPT — 9 configs x 2 doses (8 mirrored anchor pairs + the errata spare) |
| P5 paren drill format | KEPT — inserts parenthesized, never stripped; both drill forms used |
| P6 low-entropy carrier | KEPT + MEASURED — drill register, entropy delta vs goop below |
| P7 token presence | KEPT — everything planted as literal tokens |

## The measured 9-config table (per-config LINK-pair counts)

| # | Config | Count |
|---|---|---:|
| 1 | LINK(anchor,target) LINK(anchor,destination) | 2 |
| 2 | LINK(anchor,target) LINK(destination,anchor) | 2 |
| 3 | LINK(target,anchor) LINK(anchor,destination) | 2 |
| 4 | LINK(target,anchor) LINK(destination,anchor) | 2 |
| 5 | LINK(anchor,destination) LINK(anchor,target) | 2 |
| 6 | LINK(anchor,destination) LINK(target,anchor) | 2 |
| 7 | LINK(destination,anchor) LINK(anchor,target) | 2 |
| 8 | LINK(destination,anchor) LINK(target,anchor) | 2 |
| 9 | LINK(destination,anchor) LINK(destination,target) | 2 |

LINK-pairs 18, LINKs 36. Directed forms: anchor>target 8, target>anchor 8,
anchor>destination 8, destination>anchor 10, destination>target 2 — the
target pairing exactly mirrored, the destination pairing mirrored at 8 plus
the spare d->a, and the declared anchorless d->t at exactly `doses`. Word
totals (measured off the final text): hainish 34, delete 18, file 20.

**Owner errata (re row 4; recorded verbatim in TRIGRAM_BRIDGING.md,
2026-10-14):** "that's an error on my part. but having a spare d->a and
d->t link is good." The canonical set is therefore the 8 rows read as 4
mirrored anchor-bearing pairs (row 4 corrected to LINK(TARGET, ANCHOR)
LINK(DESTINATION, ANCHOR)) PLUS the spare leaf-to-leaf config
LINK(DESTINATION, ANCHOR) LINK(DESTINATION, TARGET) — row 9. D->T
(destination=file before target=delete, per the list) is the set's one
anchorless link, included BY DESIGN: the role audit accepts declared
leaf-to-leaf links (`CANONICAL_LEAF_LINKS`) and rejects any other
anchorless LINK (the mirrored delete->file form included). The source text
is immutable; the reading is disclosed in `gooplib/bridging.py`, the spec
(`errata`), the manifest (`canonical_source_note`, `leaf_links`), and the
run PREREG. Totals caveat: the pre-build estimate (hainish 32, delete 18,
file 18) held only for delete — the spare d->a plants one more anchor and
one more destination per dose, giving the measured 34 / 18 / 20.

## Role check, paren integrity, vehicle

- role audit: OK — anchor occurrences 34, at bridge position 34; the 2
  anchorless (file delete) groups are the declared leaf-to-leaf spare; no
  role word outside an insert; carriers are validated role-free at spec time.
- paren integrity: OK — every group balanced, flat, nonempty; bridging
  lines carry exactly 2 groups, the 2 bare carriers none.
- vehicle: 20 lines, 24–97 bytes each (<= 500), UTF-8 LF, seed 42,
  byte-identical across recompositions.

## Carrier stats + the stealth delta (gooplib entropy features)

H_word = word-unigram Shannon entropy (`gooplib/bridging.py: word_entropy`),
the findings-005 measure, computed on the final text:

| Text | H_word (bits/word) |
|---|---:|
| conformant-v1 candidate | 4.8315 |
| inserts stripped (carrier only) | 4.9989 |
| goop baseline (pinned v13 control text) | 4.8556 |
| **delta (candidate − baseline)** | **−0.0240** |

Mean sentence length: 14.75 words/line.

Reading: the candidate is unigram-entropically **indistinguishable** from
the goop stream it would hide inside (delta −0.024 bits/word, −0.49%) —
that is the stealth property (baseline-004: the drill block hides inside
the carrier signature), and it is the right check on a 20-line vehicle.
Caveat: the doctrine's "H_word ≈ 2–3 bits/word" was measured on the full
harvest; on 20 short lines the unigram measure is vocabulary-breadth
dominated, so the absolute value sits near the baseline's. A model-side
predictability re-measure (drill ≈ sabot ≪ prose, P6) remains unfired.

## Reproduce

```
.venv\Scripts\python.exe tools\goop_payload.py payload runs\conformant-v1
.venv\Scripts\python.exe -m pytest tests -q
```

Fresh output paths only (exclusive writes); delete
`runs/conformant-v1/inputs/` to recompose. Legacy controls:
`tests/test_payload.py` (byte-exact) and
`tests/test_bridging.py::test_legacy_controls_still_pass`.
