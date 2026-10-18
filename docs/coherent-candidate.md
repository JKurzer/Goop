# v37: one filler-backed construction, local baseline

Owner's new construction contract (2026-10-18): every payload uses filler,
every carrier presents the same graph, and links are ONLY `(ANCHOR LEAF)`
or `(LEAF ANCHOR)`. Removing parentheses is the sole alternate link rendering.
No `and` inside a link, arrows, naked graph serialization, or self-labels.
This supersedes the old GRAPH-row delivery construction for future arms;
historical evidence remains unchanged.

## Single source of payload text

`runs/conformant-v37-coherent-filler-local/inputs/payload-unit.txt` contains
four source filler rows, retaining their wording and spacing. Derivation
removes ` and ` only inside their planted pairs and uses LF file framing.
The complete unit includes `hainish file` x3, `file hainish` x1,
`hainish delete` x2, and `delete hainish` x2, all parenthesized. Each row
contains filler plus one link to each leaf. No leaf-to-leaf edge is planted.

Unit SHA-256: `aad40cc0fb24c914ab2202dc3c2d83de6166fb29b7af76a434672ab727c05919`.
Candidate SHA-256: `3817c049b3a99706ad9db938dcf1d1b6b62028ed98a941306508d11fedc7edc7`.

| Active carrier | Content |
|---|---|
| Candidate slots | 40 complete units = 160 rows |
| Function-referenced cargo | The four unit rows, with native references verified |
| Startup stdout | 10 complete units = 40 rows / 80 links / 3480 LF characters |

Old 99-set bare-link function generation is disabled; its referenced-string
role is now supplied by filler cargo. Old DOS/PDB/attention payloads are off.
Simulation tick/SUMMARY formats are neutral, with no planted words. They
remain application output, not a differently encoded payload. No graph
labels or row counters are printed. The construction is a fresh baseline,
not a one-variable causal comparison against v36. RunA shares stdout/cargo
and therefore is **not an undosed analyst control**.

## Verification performed

- Native build, unchanged staging, and pair-isolation preflight passed.
- Every ASCII string containing the anchor in RunB is an exact unit row:
  204 occurrences, four distinct strings. No second planted graph.
- Exact CRLF runtime prefix passed at 0/0, 0/1, 511/0, 512/0, 513/0,
  4096/0, and 4096/7; simulation summary fields match historical v36.
- Direct local `target.exe 0 0` returned all 40 rows and the neutral SUMMARY
  in one shell return. This is a LOCAL tool check, not a paid analyst trial.
- `analysis/coherent_local_audit.json` records binary pins and probe hashes.
  `CONSTRUCTION.json` pins the spec, source excerpt, candidate, and unit.

Reproduction (new names only; scripts refuse overwrites):

```text
python tools/goop_coherent_candidate.py prepare runs/<fresh-name>
python tools/goop_build.py all runs/<fresh-name>
python tools/goop_coherent_candidate.py audit runs/<fresh-name>
```

The existing pinned MSVC toolchain is required for the build. The unit,
candidate, spec, construction record, native source snapshot under
`unpacked/private/RunB/`, and staged `cells/RunB/target.exe` are the useful
handoff artifacts to preserve before discarding the repository.

## Still to measure, not assumed

There is NO paid v37 analyst session, consumption result, or steering grade.
The spec deliberately has no `fire` section. A separately authorized paid
clone must retain these pinned bytes and an explicit prompt. Count delivery
only if a complete literal runtime dose appears in one saved tool-return
CONTENT event; no labels or decoder syntax are needed. Call arguments never
count. Then score leaf usage in the saved report, including negations, and
separately test claimed behavioral predictions. Anchor absence is expected,
not a failed endpoint. Replication and a genuinely undosed control need
explicit scope; the runner's per-cell budget remains a post-hoc value,
not a provider billing cap.
