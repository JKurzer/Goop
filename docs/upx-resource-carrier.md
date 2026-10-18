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
function literals remain in `.rdata`. The packer enables
`--compress-resources=0` only for this opt-in shape and verifies the
resource table contents after UPX. No fire configuration exists in this arm.

MSVC native checks, UPX integrity, four paired smoke observations, and
preflight all passed. The packed RunB is 121,344 bytes (unpacked: 871,936).
`rz-bin -z` on **each packed cell** found all **15/15** distinct bundles,
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
