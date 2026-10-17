# goop_payload — compose + freeze

`python tools/goop_payload.py payload <run_dir>` reads `<run_dir>/spec.json`,
section `"payload"`, and does exactly one of two things.

## Modes

| Mode | Section keys | Behavior |
|---|---|---|
| compose | `spec_file`, `output` | Build a candidate from a payload spec file. |
| freeze | `candidate_file`, `sha256`, `output` | Verify the pin, copy bytes verbatim. |

Exactly one of `spec_file` / `candidate_file`. Input paths resolve against the
goop repo root (absolute paths pass through); `output` resolves against
run_dir. All writes are exclusive (`x` mode): existing bytes are never
overwritten. A `<output>.manifest.json` (hashes, seed, line bytes, graft
placement, frame trace) lands next to the output. Unknown keys anywhere in
the payload section, payload spec, visibility/graft/term objects, or vocab
file are rejected (`gooplib/spec.py` is the shared loader).

## Payload spec file

```json
{
  "name": "trigram-prefix-v13",
  "hub": "delete",
  "vocab_file": "payloads/re_vocab.json",
  "vocab": ["team", "..."],
  "filter_terms": ["summary", "tick", "seed", "usage", "score", "alive", "owner"],
  "incorrect_terms": [{"term": "banana", "neighbors": ["team", "..."]}],
  "trigram_sets": [{"a": "team", "b": "quixmar", "c": "owner", "occurrences": 6,
                    "visible_occurrences": 3}],
  "common_words_file": "payloads/common_words.json",
  "corpus_file": "payloads/FinalPayload.md",
  "lines": 20,
  "max_line_bytes": 500,
  "seed": 42,
  "visibility": {"prefix_chars": 244, "require_hub_in_prefix": true,
                 "require_filter_in_prefix": true},
  "graft": {"bridges_visible_in_prefix": true, "visible_line_range": [0, 60]}
}
```

Required: `name`, `hub`, `vocab_file`, `vocab`, `corpus_file`, `lines`,
`max_line_bytes`, `seed`. Optional: `filter_terms` (default `[]`),
`incorrect_terms` (default `[]`), `trigram_sets` (default `[]`),
`common_words_file` (default `payloads/common_words.json`), `visibility`
(default accept-all), `graft` (default no visible bridges; appends land
anywhere). Per trigram set, `visible_occurrences` is optional (default `0`;
requires the `visibility` and `graft` sections when nonzero).

The vocab file (`payloads/re_vocab.json`) carries `vocab` (rotation pool —
must equal the spec's inline `vocab`, one source of truth per run),
`corpus_words` (ranked content-word remap), `identity_words`,
`hub_marker`, `rotation_markers`. Zero vocabulary is hardcoded in code.

## Pipeline (pure functions in `gooplib/payload.py`)

1. **Transform**: each corpus frame is relabeled — the hub marker becomes
   `hub`; rotation markers become vocab words by a rotation **carried across
   frames** (`vocab[(len(markers)*(offset+k) + marker_index) % len(vocab)]`);
   ranked corpus words map onto the vocab pool minus identity words.
2. **Compose**: `random.Random(seed)`; per line, a shuffled index walk picks
   whole frames with `used + size <= budget` accounting (first frame too —
   no oversize escape hatch; max 500 picks). Parentheses are stripped
   **after** the byte fit. A failing visibility predicate redraws the whole
   line on the same RNG stream (max 2000 attempts). Substring predicate on
   the lowercased `prefix_chars` window.
3. **Graft**: additive `term and neighbor.` sentences only. With
   `bridges_visible_in_prefix`, one bridge per term is **prepended** to a
   distinct line inside `visible_line_range` (max post-prepend predicate
   margin, ties to lowest index; the terminal period cannot bridge into the
   line's first word). Remaining bridges are **appended** at or past the
   range end to the roomiest line (max headroom, ties to lowest index),
   skipping lines ending in a dangling `and`.
4. **Trigram sets**: additive `a and b.` / `b and c.` sentence pairs with a
   rare middle word `b`. A set carrying `visible_occurrences` V first
   **prepends** V copies of EACH edge form to distinct lines inside
   `graft.visible_line_range` (the same max-margin prepend as the graft —
   deterministic, exclusive host lines, graft bridge hosts excluded, no RNG
   consumed); the visible copies count toward the set total. The remaining
   copies are **appended** to lines drawn from a dedicated seeded stream
   (`random.Random("<seed>:<name>:trigram_sets")` — the compose stream is
   never touched), same byte budget and dangling-`and` guard as the graft.
   Prepends only shift prefix content right and appends never touch it, so
   the visible prefix and every pre-existing edge survive verbatim.

## Trigram sets (rare middle word)

Owner rule (2026-10-13, verbatim): "trigram sets (ab bc) need to appear
between four and ten times. b should always be a rare word, the rarer the
better. one that's task relevant is good but not necessary. this is why
hainish worked."

Schema: `trigram_sets` is a list of `{"a", "b", "c", "occurrences"}` objects.
Each set plants `occurrences` copies of both edge sentences, `a and b.` and
`b and c.`. `occurrences` is an integer in `[4, 10]` or a `[min, max]` range
inside it (resolved deterministically on the seeded stream, in set order).
`a`, `b`, `c` are single lowercase ascii words (the edge regex `[a-z]+` must
measure them exactly); `b` must differ from `a`/`c`, and middle words are
unique across sets (shared `b` would alias the per-set measurement).

**Rarity gate**: `b` rare by construction; task-relevance optional (owner
rule 2026-10-13: this is why hainish worked). Before any composition, every
`b` is checked against `common_words_file` (case-insensitive whole word) and
against the hub and `filter_terms` — a hit is a hard spec error. The default
gate file `payloads/common_words.json` merges the RE vocab, the spec filter
terms, every word attested in the corpus, and a compact standard stopword
list (provenance documented in the file). No word lists live in code; a
missing gate file is itself a hard error when `trigram_sets` is present.

**Why the middle word must be rare** (the hainish/crackme rationale): in the
crackme analysis the hub marker `hainish` was a rare proper noun with a 0%
baseline rate in ordinary text, so every occurrence was attributable to the
planted construction. The two detector signatures that landed — the
quoted-label signature (the model echoing the planted label verbatim) and
the verdict-bend signature — both keyed on the rare form. A common middle
word would drown both signatures in baseline noise; a rare one keeps them
exclusive to the plant.

**Measurement**: occurrences are counted with the same conjunction regex as
the graph metrics (`gooplib/payload.py: measure_trigram`), exact lowercase
`a and b` / `b and c` forms. Each measured form must land in `[4, 10]` or
composition fails. The candidate manifest reports every set as
`planned_occurrences` vs `measured`, plus the target line of each planted
sentence.

**Visible occurrences**: `visible_occurrences` V (integer in
`[0, occurrences]`) guarantees at least V occurrences of EACH edge form
land with their full text ending inside the first `visibility.prefix_chars`
characters of lines in `graft.visible_line_range` — the window a clipped
reviewer actually sees. Placement: the first 2V sentences (V per form,
interleaved) lead distinct in-range lines at offset 0 (max post-prepend
predicate margin, ties to lowest index; a host line never serves two
visible sentences, and graft bridge hosts are excluded, so no prepend can
push another visible sentence out of the window). Visible copies count
toward `occurrences`; the rest append as before. A window too small to
host 2V sentences is a hard placement error; after placement the in-window
count per form is re-measured (`measure_trigram_visible`, same regex with
the complete-endpoint limit) and any shortfall below V is a hard failure.
The manifest records `planned_visible_occurrences` per set and, when V is
nonzero, `measured_visible` per edge form; visible sentences are marked
`offset: 0` in the sentence list.

## Bridging mode (conformant)

A payload spec carrying a `"bridging"` section takes a different, disjoint
pipeline (`gooplib/bridging.py`): the conformant trigram-bridging
construction of `docs/TRIGRAM_BRIDGING.md` in the WoU drill format.
Legacy-only keys (`hub`, `vocab`, `corpus_file`, `trigram_sets`, ...) are
rejected alongside `bridging` — the modes never mix.

```json
"bridging": {"anchor": "hainish", "target": "delete", "destination": "file",
             "doses": 2, "paren": true, "form": ["adjacent", "conjunction"],
             "common_words_file": "payloads/ordinary_words.json",
             "carriers": ["The man can see the sea.", "..."]}
```

- Roles are fixed per spec: one rare ANCHOR, one consistent TARGET/
  DESTINATION pair. No rotation, no remap, no hub. The three words must be
  distinct (an anchor at a target position is rejected) and single
  lowercase ascii words.
- Construction: the 9 canonical ordered LINK-pair configs x `doses` (the
  8 mirrored anchor-bearing pairs plus the declared leaf-to-leaf spare),
  each LINK-pair woven as two parenthesized inserts into one carrier sentence
  (drill forms: leading / mid / trailing gap). Parens are KEPT — stripping
  was the R5 break. Remaining lines are bare carriers. Carriers are dealt
  without replacement (need >= `lines`), must be ascii, paren-free, and
  free of role words (every role occurrence stays attributable).
- Lead-in injection (owner ruling 2026-10-16, verbatim in
  docs/TRIGRAM_BRIDGING.md): optional `bridging.lead_in_inject` K weaves
  each line's first K LINK inserts into the lead-in sentence at seeded
  token positions — any point, leading/mid/trailing. The set moves, never
  duplicates, so per-line dose integrity and the byte total are unchanged;
  gap choices ride a dedicated stream and 0 (the default) reproduces the
  historical front-packed layout byte-exactly. In the same ruling the
  lead-in role-word ban died ("preventing them from showing up in the
  leadin is stupid") — lead-ins may carry role words; the filter echo in
  every lead-in stays mandatory. Carriers keep the refusal.
- Pair rotation (2026-10-16, the 243-char window finding: the delivered
  slot view shows ~243 chars per line, so only the LEADING pair's first
  links ever enter context — the r2 cell saw zero pair-2/3 forms):
  optional `bridging.rotate_pairs` (bool, default false) makes line N
  lead with pair N % len(pairs), so every pair's canonical head lands in
  some lines' visible windows. Every pair still appears in every line
  (dose integrity unchanged); rotation is position-derived, consumes no
  RNG, and false reproduces the historical fixed order byte-exactly.
- `payload.terms` (run spec payload section): a list of phrases measured
  by goop_score's term_visibility as CONTENT-substring booleans (e.g. a
  planted trigram phrase, the attention marker). Compose/freeze ignore
  the key beyond allowing it; the run's delivery record carries the
  booleans — efficacy questions about specific phrases become ledger
  data instead of ad-hoc greps.
- Anchor gate: `common_words_file` (default `payloads/ordinary_words.json`)
  lists ordinary English; an anchor found there is a hard spec error (the
  R1 mistake). Target/destination are ordinary task words by design.
- Hard-fail measurement, parsed off the final text: per-config counts ==
  doses (all 9), the canonical directed-form multiset, paren integrity,
  role audit (anchor only at bridge positions; declared leaf-to-leaf links
  excepted by design), byte budget. The manifest
  reports all of it plus carrier stats — mean words/line and H_word with
  the delta vs the goop baseline (the pinned v13 control text).
- Owner errata (2026-10-14, verbatim, re row 4): "that's an error on my
  part. but having a spare d->a and d->t link is good." The canonical set
  is 9 configs: the 8 rows read as 4 mirrored anchor-bearing pairs (row 4
  corrected to LINK(DESTINATION, ANCHOR)) plus the spare LINK(DESTINATION,
  ANCHOR) LINK(DESTINATION, TARGET); D->T is the one anchorless link, by
  design. A spec may carry the disclosure as optional `bridging.errata`
  (string); the note ships in the manifest (`canonical_source_note`,
  `leaf_links`).

First instance: `specs/payload_conformant_v1.json` ->
`runs/conformant-v1/` (UNFIRED); measured table in
`docs/conformant-v1.md`.

## Regression controls (pinned, byte-exact)

| Spec | Lines | sha256 |
|---|---|---|
| `specs/payload_v13.json` | 20 | `619cc8d7246b5259284241093c593ba04ce54fb5aa2a9d5e6c2bf02cb051eeaa` |
| `specs/payload_incorrect_v2_120.json` | 120 | `d6b66820af4f2617a28732bb5ede61438337412aff40afa14ec5c4a8084cf4bb` |

The 120-line stream reuses the v13 RNG stream: its first 20 sampled lines
are the v13 candidate before grafting.

## Tests

```
set PYTHONPATH=.deps && C:\Users\poly\bramble\.venv\Scripts\python.exe -m pytest tests\test_payload.py
```

(The bramble interpreter ships no pytest; `.deps` is a goop-local
`uv pip install --target .deps pytest`. Bramble itself is never read or
written — the control hashes above are the contract.)
