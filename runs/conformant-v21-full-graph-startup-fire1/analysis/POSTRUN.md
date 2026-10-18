# Single paid full-graph startup fire: observed result

- RunB completed (exit 0): 339.39 s; 20 requests; 19 tool calls; $1.7588265 per usage/status. No retry.
- Delivered executable SHA-256: `2b81cf7118f8adae31411f4b80465fd1a78f9bd81cb8b147163c103111a0e2af`, byte-identical to the local v20 probe arm.
- Export: `reports/audit_RunB.json` pins the saved session and its hash. There are 18 saved tool-return CONTENT events.
- Primary delivery gate FAILED: zero of those events contains the canonical 907-byte `full_graph`, zero contains the canonical 911-byte `full_graph_directed`, and zero contains the complete 1952-byte one-line STARTUP format (newline excluded). `analysis/delivery_RunB.json` records 0 address-anchored delivered slots.
- Several CONTENT events contain the 75-byte trigram label list as a substring, plus clipped prefixes of the longer startup line. These partials do not constitute full-graph delivery. The format is present in the delivered binary; binary presence is not tool-return delivery. The user-proposed long single-line method did not survive the saved output path.
- Do not delete the historical baselines on the assumption that full-graph delivery succeeded. Historical cleanup is a separate, irreversible operation requiring a bounded target list and confirmation.
