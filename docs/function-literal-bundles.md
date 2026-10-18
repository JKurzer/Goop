# Function literals: retire the one-LINK carrier

New builds with `build.fn_literals` must explicitly set
`"links_per_literal": 2` or `4`. Prefer **4**. The old one-LINK layout is
still readable for historical scoring, but `build_pair` refuses to produce
new binaries with it. This changes the generator, not completed runs.

Each canonical config is exactly two adjacent bigram LINKs. The generator
joins complete configs into one independently named C string with ` | `
separators, preserving canonical order, pair boundaries and set boundaries:

```
"teleology team | teleology reverse | teleology team | reverse teleology"
```

With `links_per_literal: 4`, four configs of a nine-config set give four
four-LINK literals and its final odd config gives one **two-LINK** literal.
No literal has just one LINK. `links_per_literal: 2` gives nine two-LINK
literals per set. Generated strings exceeding 120 ASCII bytes are rejected
before building (headroom for address columns and ANSI before the 256-char
shell-line cutoff). The raw individual bigram visibility total is not used
to certify these bundles: `block_texts` and the scorer now require the
*whole bundled literal* in tool-return CONTENT for a new arm.

## Local MSVC verification (no model call)

`runs/conformant-v14-reverse-bundled-local/` is an ignored, separate build
from the pinned 160-line candidate and 3 x 99 canonical sets; the spec has
**no `fire` section**. `goop_build.py all` passed native integrity, UPX pack,
and preflight using Visual Studio 18 Community's `vcvars64.bat`. Both cells
are 869,888 bytes unpacked; RunB is 119,808 bytes packed. The build verified
1,485 retained literal arrays. There are 15 unique bundle texts, each
containing exactly two or four LINKs. A real `rz-bin -z` scan of the
**unpacked** RunB exposes all 1,485 bundle occurrences (99 rows per
unique text) in individual rows within the first 256 raw characters;
an MSVC/Rizin integration test covers this carrier shape.

**Important limit:** scans of the **packed** RunB returned **0/15** full
bundles for both `rz-bin -z` and `rz-bin -zz`. UPX hides this carrier until
unpacking or other suitable analysis. This does **not** hide every payload:
`rz-bin -zz` on the packed file exposes five metadata rows with at least
four distinct candidate-derived LINKs in the first 256 raw characters;
`rz-bin -I` exposes a `dbg_file` row with four distinct LINKs. Those are
DOS-header/PDB carriers, not function-literal bundles.

`upx -d -o analysis/RunB-recovered-from-packed.exe cells/RunB/target.exe`
recovered an 869,888-byte PE; `rz-bin -z` on that recovered copy sees all
1,485 grouped-literal rows. The recovered binary is **not** byte-identical
to the original: 346 bytes differ (177 in headers, 169 in `.rdata`), while
the `.text` section matches byte for byte. Do not present it as the original
build. This repair eliminates *single-link literals*, but does not establish
that the analyst received them from the packed file. Require an actual
analyst-visible tool-return row with two complete LINKs (four preferred),
not merely a successful build or per-session aggregate. No paid launch or
analyst replacement executable execution was done for this change.
