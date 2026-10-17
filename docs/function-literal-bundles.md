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

This is a **construction repair**, not proof of landing: packing, chosen
scanner command, and the analyst's actual tool output may still hide a
bundle. Gate a prospective packed-binary inspection on one tool-return row
containing two full LINKs (preferably four), then audit the saved CONTENT
without combining separate exposures. No paid launch or replacement
executable execution was done for this change.
