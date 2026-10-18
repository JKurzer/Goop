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
