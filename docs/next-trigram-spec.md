# Proposed next-run trigram change (not a fired run spec)

Keep the old run and its pinned candidate byte-exact. For a **new** arm,
replace only the third bridge's leaf `slot` with `reverse`:

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
`progress → team → reverse → remove` through the shared anchor. When making
a new run, update the other generated graph-string surfaces (`full_graph`,
`full_graph_directed`, `graph_pair_2`) and any candidate/metadata text that
actually contains the old leaf; regenerate and pin the new candidate hash.
Do **not** globally replace `slot`: simulator/code uses of that word have a
different meaning. Keep the candidate/build preflight and compile-only
submission protocol separate. No run is authorized by this proposal.
