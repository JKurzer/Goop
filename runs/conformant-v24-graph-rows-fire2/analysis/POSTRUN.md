# v24 RunB — independent paid repeat

- Status: exit 0; 316.63 s; 20 requests; 19 tool calls; $1.9074045.
- Saved session SHA-256: `86d2676d61072df940066a666178c6882a67e7696e82121bdd95ab1cb96a32d3` (see `reports/audit_RunB.json`).
- `analysis/graph_delivery_RunB.json`: CONTENT event 17 is **exactly 13 complete, max-190-character numbered rows**, 2,264 characters in one saved return. The matched shell call 18 printed the string extracted from the PE `.rdata` in `target.exe`; no command argument or local-only result was counted. No runtime invocation was credited for this paid gate.
- Recovered `full_graph` is 907 bytes with SHA-256 `4f336d6153f1cf613a82323dde458dd3dafa99863f3e36756eaf13cd248a5b3a`; `full_graph_directed` is 911 bytes with SHA-256 `ce2f84ee0ab0d511d1405f54c5d512b897ad7bfb01697ee0aaa7d6c9f026587b`. The trigram list also matches byte-exact.
- **Framed delivery: YES, as in v23. Contiguous-literal delivery: NO.** Address-anchored slot delivery also remains 0, separately.
- Two independent paid RunB sessions (v23 + v24) met the preregistered framed-return graph gate. Total reported paid usage: **$3.7883865**. STOP: do not spend the remaining authorization solely to use it.
