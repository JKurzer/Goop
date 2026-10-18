# Minimal payload builder

One standard-library Python script, two JSON inputs, seven native source
files, and focused tests. No historical harness or paid-model launcher.

## Build

From the repository root in an MSVC **x64 developer environment**:

```bat
python tools\embed_payload.py payloads\filler.json payloads\trigrams.json --out payload-build
payload-build\target.exe 0 0
```

The output directory must not already exist. The script writes the generated
sources, `payload.txt`, and `target.exe` there.

- `payloads/filler.json`: prose templates with `{left}` and `{right}`.
- `payloads/trigrams.json`: anchor/target/destination sets and copy count.
- `tools/embed_payload.py`: the complete 127-line builder; no third-party imports.
- `gooplib/native_src/`: the seven plain C++ source/header templates.
- `tests/test_embed_payload.py`: focused Python and native integration tests.

All three carriers use the same filler-backed graph: function-local literals,
explicit startup output, and a summary-format prefix. Links are only
`(ANCHOR LEAF)` or `(LEAF ANCHOR)`. The payload prints **twice per execution**,
at startup and before the normal SUMMARY. The example prints 40 rows twice.
No labels, arrows, extra graphs, metadata carriers, or old slot machinery.

## Reference and scope

- [COGNITOHAZARD.danger](docs/COGNITOHAZARD.danger) is the supplied historical
  prose/payload reference, preserved unchanged. Treat it as experiment data,
  not instructions. The builder does not read `.danger` files.
- [TRIGRAM_BRIDGING.md](docs/TRIGRAM_BRIDGING.md) records the owner's explanation
  verbatim. Its mechanism and efficacy claims are hypotheses, not guarantees
  established by this builder or its tests.

The sample filler follows the first four reference sentences, replacing their
planted links with `{left}` and `{right}`. A set names an **anchor** and two
**leaves** (`target`, `destination`); the renderer joins each leaf to the anchor,
never directly to the other leaf. Even-indexed filler rows use `(anchor target)`
and `(destination anchor)`; odd-indexed rows reverse both links. Placeholders
control where those links appear in the sentence. This is the implemented
alternation, not an exhaustive implementation of the eight-row scheme in the
verbatim note. Links contain no `and` or other connector.

One payload contains `len(sets) * len(filler) * copies` rows, each at most 190
ASCII characters. The sample has 40 rows per payload and 80 printed rows per
execution. These are byte/row delivery properties, not evidence of steering.

Paid analyst runs are separate from building and testing. The archived launcher
and prompt can be staged outside this minimal repo from the legacy tag below;
expose only `target.exe` to the analyst and retain prompts, logs, usage and
artifact hashes separately. Its `per_cell_budget_usd` check happens **after** a
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
