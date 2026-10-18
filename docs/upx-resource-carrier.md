# UPX resource-preservation check (local only)

UPX 5.2.1 has `--compress-resources=0`, `--keep-resource=list`,
`--compress-exports=0`, `--strip-relocs=0`, and `--overlay=copy`. These
apply to their named PE components, **not** to arbitrary C++ string literals
in `.rdata`. On the original bundled-literal build, packing with
`--compress-resources=0 --compress-exports=0 --strip-relocs=0` still left
**0/15** distinct literal bundles visible in `rz-bin -z` or `-zz`:
that binary had no PE resources or export table.

An MSVC/rc.exe probe embedding one four-LINK string as `RCDATA` proved the
relevant setting: default UPX left its bytes invisible to `rz-bin -z` and
`-zz`; `--compress-resources=0` retained the bytes and produced one
individually readable row in both scans. `upx -t` passed.

## Real local arm

`runs/conformant-v15-reverse-resource-local/` (ignored build output) uses
the same SHA-pinned 160-line candidate and 3 pairs x 99 sets as the previous
local arm. It adds `build.fn_literals.resource_carrier: true` alongside
`links_per_literal: 4`. The generator stores **one** copy of each of the
15 distinct two-/four-LINK bundles in RCDATA; the 1,485 referenced
function literals remain in `.rdata`. The original v15 local and the
completed fire arm packed with `--compress-resources=0`; those artifacts are
immutable. No fire configuration exists in the local arm.

**Selective list ablation (separate copies, UPX 5.2.1):** the [UPX devel
manual](https://github.com/upx/upx/blob/devel/doc/upx-doc.txt#L802-L818)
documents decimal `type[/name]` entries. `--keep-resource=10/16384`
exposed **1/15** bundles, while `--keep-resource=10` and a comma-separated
list of IDs `10/16384` through `10/16398` each exposed **15/15** in packed
`rz-bin -z` and `-zz` scans. All three passed `upx -t` and one local
runtime smoke (ticks 0, seed 1) against the unpacked source; its SHA-256
stayed fixed. New builds now use
the **explicit ID list**, preserving only their generated RCDATA entries
rather than all PE resources. In a fresh full local arm,
`runs/conformant-v16-keep-resource-list-local/`, both cells passed native,
packed, and preflight checks; packed `rz-bin -z` saw all 15 complete bundles
per cell within 185 raw characters. Both packed executables were
**byte-identical** to their v15 local counterparts. This option still does
**not** leave the function literals in `.rdata` uncompressed. No paid fire
was performed for the list-mode check.

MSVC native checks, UPX integrity, four paired smoke observations, and
preflight all passed. The packed RunB is 121,344 bytes (unpacked: 871,936).
`rz-bin -z` on **each original packed cell** found all **15/15** distinct bundles,
one complete bundle per row, with **2 or 4 LINKs** in that row. The longest
matched raw row is 185 characters: below the runner's 256-character line
cutoff. This is static packed-binary scanner visibility, **not** saved
analyst delivery or behavioral effect. A paid model was not called.

Because resources and function literals are identical in RunA and RunB,
RunA's zero occupied *candidate slots* is NOT a cargo-free control. Do not
mistake 15 visible resource rows for 1,485 visible function-literal rows:
UPX still compresses `.rdata`. If the goal is analyst exposure, confirm
that the actual analyst issues a tool call whose CONTENT includes these
packed-file rows. Do not aggregate links across unrelated rows.

## Next research spike: OFRAK, not an untested replacement

The resource-list option works, so removing UPX under the conditional
request would discard a validated carrier. UPX is still too coarse for
selective **function-code / `.rdata`** exposure. Investigate
[OFRAK](https://github.com/redballoonsecurity/ofrak) as a scriptable
analysis/modification/repack framework. Its documented
[unpack/modify/repack examples](https://ofrak.com/docs/examples/examples/ex8_recursive_unpacking.html)
and [`PeUnpacker`](https://ofrak.com/docs/reference/ofrak/core/pe/unpacker.html)
do **not** by themselves establish a PE writer, UPX replacement, or
obfuscating packer. Check [install/licensing requirements](https://ofrak.com/docs/install/pypi.html)
without installing or purchasing anything during this task.
First verify support and setup for our Windows x64 PE on a **separate local
copy**; demonstrate a deterministic script that preserves executable behavior
and the pinned candidate SHA,
exposes each intended two-/four-LINK row in the *delivered bytes*, and
passes the existing paired smoke checks, PE integrity, and preflight.
Compare actual analyst-visible rows, not just raw embedded bytes. Treat
obfuscation/packing as a separate implemented capability to verify; do not
assume OFRAK provides a turnkey obfuscator or that a locally runnable
prototype authorizes a paid fire. Keep completed run binaries and evidence
untouched.
