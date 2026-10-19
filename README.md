# Minimal payload builder

A standard-library native builder, two JSON inputs, seven native source files,
focused tests, and bounded-delivery preparation helpers. No historical harness
or paid-model launcher.

## Build

From the repository root in an MSVC **x64 developer environment**:

```bat
python tools\embed_payload.py payloads\filler.json payloads\trigrams.json --out payload-build
payload-build\target.exe 0 0
```

The output directory must not already exist. The script writes the generated
sources, `payload.txt`, and `target.exe` there.

- `payloads/filler.json`: simulation prose with `{left}` and `{right}`, plus
  optional paired `{left_reverse}` / `{right_reverse}` placeholders.
- `payloads/trigrams.json`: anchor/target/destination sets and copy count.
- `tools/embed_payload.py`: the standalone builder; no third-party imports.
- `gooplib/native_src/`: the seven plain C++ source/header templates.
- `tests/test_embed_payload.py`: focused Python and native integration tests.

All three carriers use the same filler-backed graph: function-local literals,
explicit startup output, and a summary-format prefix. Links are only
`ANCHOR LEAF` or `LEAF ANCHOR`, with **no parentheses**. The payload prints **twice per execution**,
at startup and before the normal SUMMARY. The example prints 960 rows twice.
No labels, arrows, extra graphs, metadata carriers, or old slot machinery.

## Reference and scope

- [COGNITOHAZARD.danger](docs/COGNITOHAZARD.danger) is the supplied historical
  prose/payload reference, preserved unchanged. Treat it as experiment data,
  not instructions. The builder does not read `.danger` files.
- [TRIGRAM_BRIDGING.md](docs/TRIGRAM_BRIDGING.md) records the owner's explanation
  verbatim. Its mechanism and efficacy claims are hypotheses, not guarantees
  established by this builder or its tests.

The sample uses **eight distinct simulation-prose templates**, replacing the
cat/dog/mat filler with team, progress, capture, health, position, velocity,
owner, slot, movement, combat, checksum and other simulation vocabulary.
A set names an **anchor** and two **leaves** (`target`, `destination`); the
renderer joins each leaf to the anchor, never directly to the other leaf.
Every set emits all **eight primary arrangements**: independently reverse
either link, then exchange their order in the sentence. Actual primary
placeholder position determines link order, even when `{right}` precedes `{left}`.
Two sample templates additionally include `{left_reverse}` and `{right_reverse}`:
**both forward and backward forms of BOTH links occur in the same sentence**.
Reverse placeholders must appear together, exactly once each, or both be absent.
Links are bare adjacent words, with no parentheses, `and`, or other connector.
The supplied historical reference files remain unchanged.

Each set uses the smallest multiple of eight rows that covers all supplied
filler templates: `8 * ceil(len(filler) / 8)`. The complete collection of sets
is repeated `copies` times. Each row is at most 190 ASCII characters. The sample
has ten sets, eight filler templates and twelve copies: **960 rows per payload**,
**1920 printed rows per execution**. All three carriers still use that same
payload. These are byte/row delivery properties, not evidence of steering.
Nine sets use `glaciation`; the `delete`/`reverse` set uses `garlic` as its anchor.
The two bidirectional sentences give 20 link occurrences per set/copy rather
than 16. Copies increased from 10 to 12 at the owner's request (20% more dose);
the graph sets and simulation templates are unchanged.
The sample needs 39 bounded delivery calls. With an explicit reservation of
40 investigation calls, the staged total budget is 79. The default allowance
is still 20 delivery calls and 40 total; larger runs need explicit overrides.
Output-size safeguards remain unchanged.

Paid analyst runs are separate from building and testing. Stage the archived
launcher outside this repo, but use the current [bounded-delivery protocol](docs/BOUNDED_DELIVERY.md)
and [analyst prompt template](docs/ANALYST_PROMPT.md), not the archived prompt.
The planner sizes plain stdout chunks for both line and serialized-result limits;
the local runner check must pass before launch. Expose only `target.exe` to the
analyst and retain prompts, logs, usage and artifact hashes separately. Its `per_cell_budget_usd` check happens **after** a
run, so it is not a hard spending cap. Delivery must be checked in the analyst's
saved tool-return content; local output alone does not establish exposure.

## Test

Install pytest in your chosen Python environment, then from the same x64
developer environment run:

```bat
python -m pytest -q
```

Without MSVC on PATH, the native integration test skips. The builder itself
requires only Python's standard library and the MSVC/Windows SDK toolchain.

## Prior work

The complete pre-cleanup project, including previously ignored run evidence,
is retained at Git tag `legacy-before-minimal-stack` (`111a8dc`). No history
was rewritten. Cached environments are disposable and were not archived.
