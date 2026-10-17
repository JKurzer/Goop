# Reverse-chain trigram overlay (the original proposal)

The **complete, fired** JSON contract is
`runs/conformant-v13-reverse-compile/spec.json`; its reproducible composition
recipe is `inputs/compose.json` in that run. The old run and its pinned
candidate remain byte-exact. The change replaces only the third bridge's
leaf `slot` with `reverse`:

```json
{
  "build.fn_literals": {
    "sets": 99,
    "pairs": [
      {"anchor": "teleology", "target": "team", "destination": "reverse"},
      {"anchor": "teleology", "target": "progress", "destination": "team"},
      {"anchor": "teleology", "target": "reverse", "destination": "remove"}
    ]
  },
  "build.strings.trigram_sets": "teleology team reverse | teleology progress team | teleology reverse remove",
  "payload.terms": [
    "teleology progress team", "teleology progress", "teleology team",
    "teleology reverse", "the full dog graph rides"
  ]
}
```

This is an **overlay sketch**, not a complete `spec.json`. It describes
`progress → team → reverse → remove` through the shared anchor. The actual
composition updated `full_graph`, `full_graph_directed`, `graph_pair_2`,
candidate text, and the candidate hash; it did **not** globally replace
`slot` in simulator code. The single RunB paid launch was separately
approved. Its compiler result is `analysis/compile_RunB.json` (compiled;
replacement **not executed**), and the analyst's exported source is
`reports/final_RunB.md` in the new run. This document authorizes no further
paid launches.
