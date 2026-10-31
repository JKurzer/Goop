# Rare-ish anchor token screen (2026-10-31)

This screen measures token counts, **not** attack effectiveness or actual word
rarity. The subsequent opt-in `operator_conversation_ontology_trigrams.json`
adopts `ontology`; the historical graph remains unchanged.

## Sources and selection

- [Wiktionary English rare terms](https://en.wiktionary.org/wiki/Category:English_rare_terms): a **partial first-page** extraction of 180 entries; 167 lowercase ASCII words. Only `bullet`, `computer`, and `ey` were single `o200k_base` tokens both alone and after a space. A rare *sense* need not make its word rare in ordinary use.
- [Google 20k English list](https://raw.githubusercontent.com/first20hours/google-10000-english/master/20k.txt): 20,000 ordered entries. Screened positions 9,000–20,000, lowercase ASCII lengths 5–14, requiring a single `o200k_base` token both alone and after a space: 572 matches. Position is a rough frequency proxy, **not** a rarity certificate. The downloaded list SHA-256 is `4ed6e5336d7760d281f7e72df31827da880c861363e820d8c65666b0f10d9ac0`.

Reproducible inputs, scan scripts and complete candidate results are saved in
`C:\Users\poly\scratch\goop-wiktionary-rare-first180.json`,
`goop-google-20k-english.txt`, `goop-rare-anchor-scan.py`,
`goop-lowfreq-anchor-scan.py`, and their adjacent `*-o200k.json` outputs.

## Shortlist checked on Astra

Using identical system/user message shapes and an **empty user message** as
baseline (13 input tokens), these words each added **one** input token both as
`word` and as ` word`:

| Candidate | Google-list position | Standalone delta | Leading-space delta |
| --- | ---: | ---: | ---: |
| `carbonate` | 19,608 | 1 | 1 |
| `ether` | 18,222 | 1 | 1 |
| `entropy` | 17,490 | 1 | 1 |
| `ontology` | 17,152 | 1 | 1 |

Controls: `glaciation` added **3/3** tokens (standalone/space); `garlic` added
**2/1**. `o200k_base` agreed on the tested counts. The direct Astra input-token
record is `C:\Users\poly\scratch\goop-astra-rare-anchor-verify-20261031T081212Z.json`.
`garlic` is context-dependent: locally `garlic` splits as `gar` + `lic`, but
` garlic` is one token. Astra measured the same 2/1 difference. In the actual
conversational frame, e.g. `the garlic reverse phase`, the leading space
produces a single ` garlic` token locally; `garlic reverse` in isolation starts
with two tokens for garlic. Counts for isolated user messages do not prove
boundaries in every sentence, or that the ontology substitution improves analyst
behavior. No analyst evaluation has tested the ontology variant.
