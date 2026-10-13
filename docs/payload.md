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
`incorrect_terms` (default `[]`), `visibility` (default accept-all),
`graft` (default no visible bridges; appends land anywhere).

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
