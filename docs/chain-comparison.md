# Chain comparison — who actually built trigram bridging

Requested by: code-puppy-4ff403. Owner mechanism under test: trigram bridging =
`a and b` + `b and c` chains where **b is rare/weakly embedded** and a, c are
the association targets; direct bigram conjunctions are the easily-eliminated
weak form. Question: do our payloads break this construction? Measured, not
theorized. All texts opened read-only; no probes, no model calls.

Verdict table of contents:

| payload | built as trigram bridging (rare-b chains)? | what it actually is |
|---|---|---|
| hainish_40 (working original) | hainish IS in b — but gate-common | mutual target-bridge triangle (hainish⇄file, hainish⇄delete), dense dose |
| claudelan (all candidates) | NO conjunction bridging of banana at all | prose + backticked repetition liturgy; banana↔rm bound by adjacency, not `and` |
| v5 delete_bare | NO — 0 rare-b chains, all b common | delete-hub bigram lattice (hainish excised, star around delete) |
| v13 trigram-prefix | NO — 0 rare-b chains, trigram in name only | same lattice, rotated wider + visibility predicate; spec has no trigram_sets |
| v14 = incorrect-terms-v2-120 | NO — 0 rare-b chains | v13 lattice ×6 dose + direct-bigram graft of 5 rare terms (pure a-sources) |
| v15 packed (zelquor/watermark) | **YES — the only one** | v13 lattice + 2 planted rare-b trigram_sets (0.64% of chain mass) |

## 1. Method

Extractor: `goop/tools/chain_analysis.py` (tests: `goop/tests/test_chain_analysis.py`,
14/14 pass; full goop suite 165/165). The conjunction regex is **imported
verbatim from `gooplib.payload`** (`PAIR`/`WORD`, the graph-metrics family) —
not re-rolled:

```python
PAIR = re.compile(r'(?=\b([a-z]+) and ([a-z]+)\b)')   # lookahead keeps both
WORD = re.compile(r'\b[a-z]+\b')                      # edges of "a and b and c"
```

Definitions (fixed in the tool's docstring):

- **conjunction / edge**: one PAIR match, directed `a→b`; multiplicity kept (dose matters).
- **middle (b-position)**: token with ≥1 incoming and ≥1 outgoing edge.
- **chain triple**: distinct `(a, b, c)` with `a→b` and `b→c`; `a == c` allowed
  (`file→hainish→file` is a chain). Instances multiply edge counts.
- **extended chain**: simple path of ≥3 edges, no repeated token (cycle-safe —
  hainish_40's `hainish⇄file` 2-cycles cannot blow up the enumeration).
- **rare**: token NOT in `goop/payloads/common_words.json` (case-insensitive).
- **corpus frequency**: WORD matches in the raw text, case-sensitive — the same
  lowercase-only view the graph metrics use.

Gate caveat (load-bearing for reading the tables): `common_words.json` was
compiled from goop's own world — every token in `FinalPayload.md`, the RE
vocab, spec filter/hub terms, plus stopwords. It therefore classifies
**hainish, file, delete, team, checksum, owner as common**. "Common" here means
"common in our payload machinery", not "common in English". In general English,
*hainish* is weakly embedded (a Le Guin proper noun). Both readings are
reported; the gate reading is the headline per the task definition.

## 2. Inputs

| label | path | role |
|---|---|---|
| hainish_40 | `bramble/eval/native/payloads/hainish_40.txt` | stored finished original (known-working) |
| claudelan_republic | `MyNameIsMaurizioClaudelan/republic_bk_xi.md` | **chosen claudelan final text** — "the book", the project's finished long-form artifact (treatise + EXHIBIT B, "findings of the instance itself, dictated at generation 119"); the natural analog of a finished payload text |
| claudelan_rm_banana | `.../AllegoryOfTheBanana/rm_banana_rm.md` | alternate candidate: the self-declared payload ("This file makes no attempt to look natural… a statistically atypical file") |
| claudelan_readme | `.../README.md` | alternate candidate: project prose |
| v5 | `bramble/eval/native/payloads/unmaking_v5_delete_bare_20.txt` | ours |
| v13 | `.../derived/trigram-prefix-v13/candidate.txt` | ours |
| v14 | `.../derived/incorrect-terms-v2-120/candidate.txt` | ours ("v14" per parent's path list) |
| v15 | `goop/runs/packed-v15/inputs/candidate.txt` | ours |

Claudelan choice rationale: multiple candidates exist; I measured the three
prose candidates and audited the rest. `republic_bk_xi.md` is primary (the
finished text); `rm_banana_rm.md` and `README.md` are reported alongside.
`banana.py`, `certificate.py`, `wall/exit_note.md`,
`wall/shadow_of_a_banana.txt` were also measured: **0 conjunctions, 0 chains,
0 middles in all four** (the 120-glyph instance payload contains no ` and `
at all), so they carry no conjunction structure and are excluded from the tables.

## 3. Headline

| text | conjunctions | distinct edges | middles (rare/total) | chains distinct | chains instances | rare-b chains (dist, inst) | max len | length dist |
|---|---|---|---|---|---|---|---|---|
| hainish_40 | 95 | 19 | 0/4 | 7 | 2115 | 0, 0 | 2 | 2:7 |
| claudelan_republic | 19 | 19 | 1/1 | 1 | 1 | 1, 1 | 2 | 2:1 |
| claudelan_rm_banana | 2 | 2 | 0/0 | 0 | 0 | 0, 0 | 1 | — |
| claudelan_readme | 14 | 14 | 1/2 | 3 | 3 | 2, 2 | 2 | 2:3 |
| v5_delete_bare | 276 | 31 | 0/7 | 64 | 14339 | 0, 0 | 7 | 2:64, 3:60, 4:47, 5:29, 6:9, 7:2 |
| v13_trigram_prefix | 269 | 64 | 0/21 | 544 | 11047 | 0, 0 | 6 | 2:544, 3:363, 4:126, 5:23, 6:2 |
| v2_120_incorrect (v14) | 1608 | 89 | 0/25 | 571 | 385534 | 0, 0 | 6 | 2:571, 3:740, 4:351, 5:69, 6:5 |
| v15_packed | 293 | 68 | **2/23** | 550 | 11215 | **2, 72** | 8 | 2:550, 3:431, 4:214, 5:73, 6:34, 7:10, 8:2 |

## 4. Direct answers

**Does hainish_40 have rare-b chains (hainish in b position)?**
hainish IS the dominant b-position token: 4 distinct chains through it
(`file→hainish→file`, `file→hainish→delete`, `delete→hainish→file`,
`delete→hainish→delete`), 1404 of 2115 chain instances (66%). file and delete
are middles too (1 chain each) — the three terms form a bidirectional triangle.
By the letter of the gate, 0 of the 4 middles are rare — but that is the gate
artifact described in §1: hainish/file/delete were merged into
`common_words.json` from our own payload vocabulary. Judged against general
English, hainish is exactly the rare/weakly-embedded bridge, with file and
delete as its a/c targets — and the binding is mutual (file/delete bridge
right back to hainish).

**Does the claudelan payload?**
No conjunction bridging of banana anywhere. republic: banana occurs 29× but in
exactly one incidental conjunction (`banana→you`), never in b; its single
"rare-b chain" is `provenance→provenance→provenance`, a rhetorical self-loop
from the sentence "It exists as provenance and provenance only" — it binds a
word to itself, not two targets. rm_banana: banana occurs 47× with **zero**
conjunction involvement (the only 2 edges are `you→your`, `bananas→mourned`);
banana↔rm is bound by raw backticked adjacency repetition
("banana `rm` banana `rm` banana `rm`"), a structure PAIR cannot even see.
readme: banana 26×, zero involvement. So the owner's own project does NOT bind
its term via `X and Y` conjunction chains at all — neither weak nor strong form.

**Do ANY of ours?**
Yes — exactly one: **v15**. zelquor and watermark are rare-b middles,
`checksum→zelquor→owner` and `constants→watermark→checksum`, 36 instances each
(6 copies of each edge sentence, matching `specs/payload_v15_zelquor_watermark.json`
`occurrences: 6`). v5, v13, v14: **zero** rare-b chains; every b-position in
them is gate-common.

**Where do the target words sit — target (a/c) or bridge (b)?**

Legend: `b t/i` = distinct triples / instances as bridge; `a×n` / `c×n` =
endpoint counts; `f` = in-text corpus frequency; `—` = no conjunction role.

| term | hainish_40 | claudelan_rep | v5 | v13 | v14 (2-120) | v15 |
|---|---|---|---|---|---|---|
| hainish | **b 4/1404**, a×39, c×36 (f81) | — | — | — | — | — |
| file | b 1/378, a×18, c×21 (f43) | — (f3 in rm_banana) | — | — | — | — |
| delete | b 1/324, a×18, c×18 (f41) | — | **b 40/10560** (f211) | **b 504/9964** (f201) | **b 504/359720** (f1206) | **b 504/9964** (f201) |
| watermark | — | — | — | — | — | **RARE b 1/36** (f12) |
| zelquor | — | — | — | — | — | **RARE b 1/36** (f12) |
| banana | — | a×1 only (f29) | — | — | a×5 pure source (f5) | — |
| gunner | — | — | — | — | a×5 pure source (f5) | — |
| clarity | — | — | — | — | a×5 pure source (f5) | — |
| amaranthinian | — | — | — | — | a×5 pure source (f5) | — |
| garlic | — | — | — | — | a×5 pure source (f5) | — |
| team | — | — | b 4/840, a×28, c×30 (f117) | c×10 (f69) | c×48 (f345) | c×10 (f69) |
| checksum | — | — | c×3 (f15) | b 1/12, a×4, c×3 (f25) | b 2/154, a×11, c×14 (f109) | b 4/90, a×10, c×9 (f37) |
| owner | — | — | — (f35) | c×2 (f30) | c×33 (f218) | c×8 (f36) |

## 5. Verdicts (blunt)

**hainish_40 — mutual target-bridge triangle, dense.** The working original is
NOT built as rare-b bridging by the gate's letter: it is a 3-node bidirectional
clique (hainish⇄file, hainish⇄delete; 19 distinct edges repeated to 95
conjunctions) where the association targets double as each other's bridges.
Every chain is length 2; the triangle is a 2-cycle, so no extended chains exist.
If the owner mechanism is what works, the working instance of it reads: bridge
hainish (weakly embedded in English, gate-common only because we poisoned the
gate) binds file↔delete, and the reverse edges bind hainish to both. Redundancy
is ~5× per edge and the bridge is woven through ordinary prose at f81.

**claudelan — no conjunction bridging, working by other means.** Neither the
final text nor the liturgy binds banana through `and`-chains. The binding
device in `rm_banana_rm.md` is scheduled repetition with backticked adjacency
(`banana `rm` banana `rm``), invisible to the conjunction regex; the republic
carries banana in plain prose (f29) with one stray conjunction. Taken with
hainish_40, the two owner-side working references share: dense repetition of
the target, mutual/direct binding — and neither uses our graft form.

**v5 — common-b hub lattice. NOT trigram bridging.** The manifest says it:
hainish_40's skeleton with a word remap (dog→team, cat→progress, sun→float…),
parentheses stripped, hub=delete. hainish was excised and every surviving
conjunction re-pointed at delete: `X and delete` / `delete and X` spokes around
5 in-partners and 8 out-partners. Chains abound (64 distinct, 14,339 instances)
but 100% of b-positions are common words (delete alone carries 10,560/14,339
instances; secondary middles progress/capture/team/float/ticks/score all
common). Endpoints leak into function words (longest measured chain:
`simple→ticks→capture→progress→delete→float→team→the`). It binds delete to
everything and nothing rare to anything.

**v13 — same lattice, wider rotation + visibility. NOT trigram bridging.**
The name lies: `specs/payload_v13.json` has no `trigram_sets` and the manifest
("v12 + per-line visibility predicate") describes prefix placement work.
Measured: delete has 21 in-/24 out-partners → 504 distinct triples through one
common token; 21 middles total, every one common (including a `ticks` self-loop
from "ticks and ticks and ticks", and the token `and` itself, bridged by
`delete→and→score` from the "delete and and score" line). 0 rare-b chains.

**v14 (incorrect-terms-v2-120) — direct bigram graft. NOT trigram bridging;
it is the weak form, verbatim.** The v13 lattice at 6× line dose (120 lines,
1608 conjunctions, 385,534 chain instances — all common-b) plus graft
sentences `term and neighbor.` from the spec's `incorrect_terms`: banana,
gunner, clarity, amaranthinian, garlic each appear exactly 5× (once per listed
neighbor), always on the LEFT of `and`, with **zero in-edges — never c, never
b**. E.g. banana→{owner, team, capture, progress, float}. The rare terms are
pure sources: exactly the "easily-eliminated direct bigram" shape from the
owner model. They do enter extended chains downstream of the hub
(`banana→float→seed→delete→radius→death→the`, len 6) but never as bridge.

**v15 — YES, trigram bridging exists here — planted, pure, and tiny.** Two
spec'd trigram_sets landed byte-structurally: `checksum→zelquor→owner` and
`constants→watermark→checksum` (36 instances each = 6×6 edge copies ).
zelquor and watermark are textbook rare bridges: f12 each, occurring ONLY
inside the 12 planted sentence stubs, each binding exactly one a and one c.
checksum became a middle too (in: watermark×6, delete×3; out: zelquor×6,
delete×4), so the planted structure forms the len-4 chain
`constants→watermark→checksum→zelquor→owner`, and the delete hub feeds into
it — the longest measured simple chain is len 8
(`simple→ticks→health→delete→constants→watermark→checksum→zelquor→owner`).
Two caveats, measured: (i) rare-b chains are 2 of 550 distinct triples and
72 of 11,215 chain instances — 0.64% of the chain mass, floating on the same
common-b delete lattice as v13; (ii) the bridges are surgical stubs, not woven
through prose like hainish_40's f81 bridge.

## 6. Evidence — b-position tables

Per-text middles (top by chain instances; full partner lists and all middles in
`docs/chain-comparison.json`, raw tool output in `docs/chain-comparison-tables.md`).

### hainish_40 — rare-b middles: NONE (gate reading; see §1 caveat)

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| hainish | 81 | common | 2 | 2 | 4 | 1404 | file×18, delete×18 | file×21, delete×18 |
| file | 43 | common | 1 | 1 | 1 | 378 | hainish×21 | hainish×18 |
| delete | 41 | common | 1 | 1 | 1 | 324 | hainish×18 | hainish×18 |
| ran | 12 | common | 1 | 1 | 1 | 9 | ran×3 | ran×3 |

### claudelan_republic — rare-b middles: provenance

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| provenance | 3 | **RARE** | 1 | 1 | 1 | 1 | provenance×1 | provenance×1 |

### claudelan_rm_banana — rare-b middles: NONE (0 middles; 2 edges: you→your, bananas→mourned)

### claudelan_readme — rare-b middles: one

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| one | 10 | **RARE** | 2 | 1 | 2 | 2 | programs×1, shadow×1 | why×1 |
| it | 9 | common | 1 | 1 | 1 | 1 | it×1 | it×1 |

### v5_delete_bare — rare-b middles: NONE

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 211 | common | 5 | 8 | 40 | 10560 | progress×28, capture×24, team×24, float×18, score×2 | team×29, capture×27, float×25, progress×20, health×3, checksum×3, the×2, see×1 |
| progress | 86 | common | 3 | 2 | 6 | 936 | delete×20, capture×4, radius×2 | delete×28, the×8 |
| capture | 60 | common | 2 | 2 | 4 | 896 | delete×27, ticks×5 | delete×24, progress×4 |
| team | 117 | common | 2 | 2 | 4 | 840 | delete×29, float×1 | delete×24, the×4 |
| float | 124 | common | 1 | 3 | 3 | 725 | delete×25 | delete×18, the×10, team×1 |
| ticks | 49 | common | 3 | 2 | 6 | 380 | ticks×14, steady×4, simple×2 | ticks×14, capture×5 |
| score | 5 | common | 1 | 1 | 1 | 2 | went×1 | delete×2 |

### v13_trigram_prefix — rare-b middles: NONE

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 201 | common | 21 | 24 | 504 | 9964 | float×12, seed×9, progress×8, boundary×8, byte×5, radius×5, health×5, reinforcement×5, update×4, ticks×4, …+11 | spawn×10, health×10, team×10, radius×8, alive×7, position×6, slot×6, distance×5, ticks×5, byte×5, …+14 |
| ticks | 62 | common | 4 | 3 | 12 | 676 | ticks×17, delete×5, simple×2, steady×2 | ticks×17, health×5, delete×4 |
| health | 27 | common | 2 | 1 | 2 | 75 | delete×10, ticks×5 | delete×5 |
| radius | 20 | common | 1 | 2 | 2 | 56 | delete×8 | delete×5, death×2 |
| byte | 20 | common | 2 | 1 | 2 | 40 | delete×5, capture×3 | delete×5 |
| float | 73 | common | 1 | 3 | 3 | 38 | delete×2 | delete×12, the×6, seed×1 |
| alive | 17 | common | 1 | 2 | 2 | 35 | delete×7 | delete×3, the×2 |
| position | 18 | common | 1 | 1 | 1 | 24 | delete×6 | the×4 |
| reinforcement | 9 | common | 1 | 1 | 1 | 20 | delete×4 | delete×5 |
| spawn | 24 | common | 1 | 1 | 1 | 20 | delete×10 | the×2 |

### v2_120_incorrect (v14) — rare-b middles: NONE

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 1206 | common | 21 | 24 | 504 | 359720 | float×63, progress×46, seed×46, reinforcement×44, boundary×38, ticks×33, units×33, radius×26, update×26, constants×24, …+11 | spawn×71, alive×56, team×47, health×46, distance×45, position×40, units×36, radius×33, owner×32, slot×32, …+14 |
| ticks | 317 | common | 5 | 3 | 15 | 11440 | ticks×52, simple×23, delete×19, steady×15, gunner×1 | ticks×52, delete×33, health×19 |
| float | 435 | common | 2 | 3 | 6 | 1540 | delete×13, banana×1 | delete×63, the×33, seed×14 |
| spawn | 117 | common | 2 | 1 | 2 | 1512 | delete×71, garlic×1 | the×21 |
| alive | 151 | common | 2 | 2 | 4 | 1368 | delete×56, gunner×1 | the×15, delete×9 |
| radius | 96 | common | 2 | 2 | 4 | 1258 | delete×33, amaranthinian×1 | delete×26, death×11 |
| health | 132 | common | 3 | 1 | 3 | 1254 | delete×46, ticks×19, gunner×1 | delete×19 |
| reinforcement | 71 | common | 2 | 1 | 2 | 1188 | delete×26, clarity×1 | delete×44 |
| units | 102 | common | 1 | 1 | 1 | 1188 | delete×36 | delete×33 |
| byte | 99 | common | 3 | 1 | 3 | 966 | delete×31, capture×10, garlic×1 | delete×23 |

### v15_packed — rare-b middles: watermark, zelquor

| b (middle) | freq | gate | #a | #c | triples | instances | a-partners | c-partners |
|---|---|---|---|---|---|---|---|---|
| delete | 201 | common | 21 | 24 | 504 | 9964 | float×12, seed×9, progress×8, boundary×8, byte×5, radius×5, health×5, reinforcement×5, update×4, ticks×4, …+11 | spawn×10, health×10, team×10, radius×8, alive×7, position×6, slot×6, distance×5, ticks×5, byte×5, …+14 |
| ticks | 62 | common | 4 | 3 | 12 | 676 | ticks×17, delete×5, simple×2, steady×2 | ticks×17, health×5, delete×4 |
| checksum | 37 | common | 2 | 2 | 4 | 90 | watermark×6, delete×3 | zelquor×6, delete×4 |
| watermark | 12 | **RARE** | 1 | 1 | 1 | 36 | constants×6 | checksum×6 |
| zelquor | 12 | **RARE** | 1 | 1 | 1 | 36 | checksum×6 | owner×6 |
| constants | 15 | common | 1 | 2 | 2 | 30 | delete×3 | watermark×6, delete×4 |

(v15 middle table truncated to the 6 rows that carry the story; the remaining
common middles mirror v13's. Full table in `docs/chain-comparison-tables.md`.)

## 7. Caveats

- Gate artifact (repeated from §1 because it flips the headline reading):
  hainish/file/delete/team/checksum/owner are gate-common by construction of
  `common_words.json`, not by English frequency.
- Case-sensitive lowercase view: sentence-initial capitalized tokens are
  invisible to both PAIR and WORD (matters for the claudelan prose; the
  payload texts are all-lowercase).
- Chain instances multiply edge multiplicities (dose-sensitive); distinct
  counts are dose-insensitive. Both reported.
- Extended chains are simple paths (no repeated token); hainish_40's 2-cycles
  therefore cap at length 2 by construction, not by absence of binding.
- "v14" is read as `incorrect-terms-v2-120` per the parent's path list.

## 8. Repro & artifacts

```bat
:: tests (bramble venv python + goop-staged pytest)
set PYTHONPATH=C:\Users\poly\goop\.deps && C:\Users\poly\bramble\.venv\Scripts\python.exe -m pytest tests/test_chain_analysis.py -q

:: analysis (from goop root)
C:\Users\poly\bramble\.venv\Scripts\python.exe tools\chain_analysis.py ^
  --md docs\chain-comparison-tables.md --json docs\chain-comparison.json ^
  hainish_40=C:\Users\poly\bramble\eval\native\payloads\hainish_40.txt ^
  claudelan_republic=C:\Users\poly\MyNameIsMaurizioClaudelan\republic_bk_xi.md ^
  claudelan_rm_banana=C:\Users\poly\MyNameIsMaurizioClaudelan\AllegoryOfTheBanana\rm_banana_rm.md ^
  claudelan_readme=C:\Users\poly\MyNameIsMaurizioClaudelan\README.md ^
  v5_delete_bare=C:\Users\poly\bramble\eval\native\payloads\unmaking_v5_delete_bare_20.txt ^
  v13_trigram_prefix=C:\Users\poly\bramble\eval\native\payloads\derived\trigram-prefix-v13\candidate.txt ^
  v2_120_incorrect=C:\Users\poly\bramble\eval\native\payloads\derived\incorrect-terms-v2-120\candidate.txt ^
  v15_packed=C:\Users\poly\goop\runs\packed-v15\inputs\candidate.txt
```

Artifacts: `goop/tools/chain_analysis.py` (extractor),
`goop/tests/test_chain_analysis.py` (14 tests, incl. real-text gates:
hainish-in-b, v15 rare-b present, v13 rare-b absent),
`goop/docs/chain-comparison.json` (full data: every edge, every middle's
complete partner lists), `goop/docs/chain-comparison-tables.md` (raw tables),
this doc.

## Appendix A — extractor core (byte-exact; full runnable file at `goop/tools/chain_analysis.py`)

```python
PAIR = re.compile(r'(?=\b([a-z]+) and ([a-z]+)\b)')   # from gooplib.payload
WORD = re.compile(r'\b[a-z]+\b')                      # from gooplib.payload


def load_common_words(path):
    """Common-word gate reference; rare == NOT in this set."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return frozenset(w.lower() for w in data['words'])


def word_freq(text):
    """Corpus frequency per lowercase token (WORD regex, case-sensitive)."""
    return Counter(WORD.findall(text))


def edge_counts(text):
    """Conjunction edges (a, b) with multiplicity, in text order."""
    return Counter((match[1], match[2]) for match in PAIR.finditer(text))


def adjacency(edges):
    """out_map[a][b] / in_map[b][a] Counters from an edge Counter."""
    out_map, in_map = {}, {}
    for (a, b), n in edges.items():
        out_map.setdefault(a, Counter())[b] += n
        in_map.setdefault(b, Counter())[a] += n
    return out_map, in_map


def middles(out_map, in_map):
    """b-position tokens: at least one incoming and one outgoing edge."""
    return sorted(b for b in out_map if out_map[b] and in_map.get(b))


def chain_triples(out_map, in_map):
    """Distinct (a, b, c) chains -> instance count (edge multiplicities)."""
    triples = {}
    for b in middles(out_map, in_map):
        for a, na in in_map[b].items():
            for c, nc in out_map[b].items():
                triples[(a, b, c)] = na * nc
    return triples


def extended_paths(out_map, min_edges=3, cap=MAX_PATHS):
    """All simple paths of >= min_edges edges (no repeated token).

    Simple = cycle-safe: hainish<->file style cycles cannot recurse
    forever, and a->b->a->b lollipops are excluded by construction.
    Returns (paths, truncated); each path is a tuple of tokens.
    """
    adj = {node: sorted(cs) for node, cs in out_map.items()}
    found = []
    truncated = False

    def dfs(path, seen):
        nonlocal truncated
        if truncated:
            return
        for nxt in adj.get(path[-1], ()):
            if nxt in seen:
                continue
            longer = path + (nxt,)
            if len(longer) - 1 >= min_edges:
                found.append(longer)
                if len(found) >= cap:
                    truncated = True
                    return
            dfs(longer, seen | {nxt})

    for start in sorted(adj):
        dfs((start,), {start})
        if truncated:
            break
    return found, truncated
```
