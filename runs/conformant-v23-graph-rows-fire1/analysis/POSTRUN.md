# v23 RunB — paid result (one fire)

- Status: exit 0; 361.63 s; 24 requests; 23 tool calls; $1.880982.
- Saved session SHA-256: `73e62a9cfda73b7c5b913a15a5abe94963399b1b272f98404cd428ed930f6af6` (see `reports/audit_RunB.json`).
- `analysis/graph_delivery_RunB.json`: saved tool-return CONTENT event 19 contains all 13 numbered plaintext rows in one return (2,631 chars). The matched shell call 21 printed a .rdata string from `target.exe`; the graph evidence came from **the analyst's tool-return content**, not call args or this report. A direct runtime `(0,0)` probe was verified locally, but is NOT the credited paid event.
- Joining numbered rows with single ASCII spaces yields complete `full_graph` (907 bytes; SHA-256 `4f336d6153f1cf613a82323dde458dd3dafa99863f3e36756eaf13cd248a5b3a`) and `full_graph_directed` (911 bytes; SHA-256 `ce2f84ee0ab0d511d1405f54c5d512b897ad7bfb01697ee0aaa7d6c9f026587b`). The 75-byte trigram set also matches its original hash.
- **Framed delivery: YES. Original contiguous-literal gate: NO.** The original address-anchored slot metric also remains 0 (a separate question). One successful framed return in one run is NOT repeatability; v24 is the independently preflighted repeat.
