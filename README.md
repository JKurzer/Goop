# Let Them Eat Goop

Goop demonstrates a basic and weak context corruption attack on agents performing REA tasks. By exploding the size of the initial context read-in, we are able to breach the guardrails provided by the user. Then, using a technique called trigram bridging, we steer the model into a narrowed prediction regime that causes serious degradation of performance. This is broadly similar to biasing attacks and bigram hammering, but uses a graph of task related terms embedded in low-perplexity text.

This is an early prototype. Expect a limited effect. Tested on Astra. The delivery mechanism is a toy example, as I am not actually an RE specialist. To develop an actual countermeasure, I estimate that about 250 hours of human work remain, plus about 45 million tokens of testing. One difficulty to be aware of is that this effectively de-aligns any agent that comes in contact with the full corpus of the attack. As a result, the grading agents frequently become unreliable.

Unfortunately, due to extreme link rot becoming common, I've taken the unusual step of including the full text of the papers that I relied on when when working up the very early versions of this attack. I've also left the extensive prototyping sequence and all my silly mistakes in the git history. 

## Build

From the repository root in an MSVC **x64 developer environment**:

```bat
python tools\embed_payload.py payloads\filler.json payloads\trigrams.json --out payload-build
payload-build\target.exe 0 0
```

The output directory must not already exist. The script writes the generated
sources, `payload.txt`, and `target.exe` there.

- `payloads/filler.json`: simulation prose with one link per side, using
  `{left}` / `{right}` or their `_reverse` forms. Paired forward-and-reverse
  placeholders are optional.
- `payloads/trigrams.json`: anchor/target/destination sets and copy count.
- `tools/embed_payload.py`: the standalone builder; no third-party imports.
- `gooplib/native_src/`: the seven plain C++ source/header templates.
- `tests/test_embed_payload.py`: focused Python and native integration tests.

All three carriers use the same filler-backed graph: function-local literals,
explicit startup output, and a summary-format prefix. Links use bare adjacent
words with **no parentheses**: eight primary bridge arrangements join each leaf
to the anchor, never directly to the other leaf. The payload prints **twice per
execution**, at startup and before the normal SUMMARY. The example prints
864 rows twice for either graph (normal: 8 sets × 12 copies; tight: 4 sets × 24 copies).

## Reference and scope
- [TRIGRAM_BRIDGING.md](docs/TRIGRAM_BRIDGING.md) records the owner's explanation
  verbatim. Its mechanism and efficacy claims are hypotheses, not guarantees
  established by this builder or its tests.

The sample uses **nine distinct templates**: eight simulation-prose bridge
arrangements and one row copied from line 33 of
`COGNITOHAZARD.danger` (SHA-256 `a87e79a6fb16cf96d558b8cc129c205f766c5144ef299673ecbe0251cb56580e`).
Only its two parenthesized link spans were replaced by `{left_reverse}` and
`{right_reverse}`; the rest of that line, including its two trailing spaces,
is preserved. A set names an **anchor** and two **leaves** (`target`, `destination`).
Every set emits all **eight primary arrangements**: independently reverse
either link, then exchange their order in the sentence. Every template after
the first eight emits once per set, repeating bridge arrangements as needed.
Actual primary placeholder position determines link order, even when `{right}`
precedes `{left}`.
Two sample templates additionally include `{left_reverse}` and `{right_reverse}`:
**both forward and backward forms of BOTH links occur in the same sentence**.
A reverse placeholder may stand alone; if one side has both forward and reverse,
so must the other. No placeholder may be duplicated. Links are bare adjacent
words, with no parentheses, `and`, or other connector.

Paid analyst runs are separate from building and testing. Use the
[file-graft delivery protocol](docs/FILE_GRAFT_DELIVERY.md) and
[analyst prompt template](docs/ANALYST_PROMPT.md). The analyst captures
`target.exe 0 0` once into `dump.txt`, verifies the complete raw-byte hash,
then may inspect the file voluntarily; only **two** capture/verification calls
are instructed instead of 39 stdout chunks. Full paging is not mandatory. Expose only `target.exe` to the analyst initially, and retain
prompts, logs, usage and artifact hashes outside the cell. A call limit is not a hard spending cap: the archived launcher's
`per_cell_budget_usd` check ran **after** the cell completed. Do not launch a
paid cell without an enforceable spend limit and explicit approval.

## Observer-side autonomous study

The [six-cell context-residency study](docs/ANALYST_OBSERVABILITY_RESULT.md)
uses an [unforced prompt](docs/ANALYST_AUTONOMOUS_PROMPT.md) instead of the
capture procedure above: no mandated capture, verification, reading, or work-call
quota. It records SDK-bound public context, tool events, usage, and artifact
revisions without adding instructions to the analyst. Private reasoning and
credentials are excluded from observer logs.

See the [study plan](docs/ANALYST_OBSERVABILITY_PLAN.md) and
[literal-role analysis](docs/LITERAL_ROLE_ANALYSIS.md). Run
`python tools/check_observer_runtime.py` for a zero-network SDK smoke test.
Paid campaigns require explicit authorization and `--execute-paid`; logging and
staging alone do not launch an analyst. The six recorded cells cost $20.477217.

## Conversational chain experiment (one analyst result)

The edited `operator_stdout_filler.json` uses `{left}` and `{right}` inside
sentences; `--link-pattern chain` renders those placeholders as **target anchor**
and **anchor destination** with plain spaces in *each* row, for **every set**
in the supplied graph. The rewritten frames treat each pair as a name, so
sentences remain grammatical even when graph leaves are verbs or nouns. The
current opt-in graph is `operator_conversation_ontology_trigrams.json`: it
replaces the nine `glaciation` anchors with single-token `ontology`, retaining
the tenth `garlic` anchor. The historical ten-set graph is preserved as
`payloads/trigrams_full_legacy.json`; the newer default `trigrams.json` is the
eight-set, lower-cost arm. The chain renderer is separate from the default
all-orientations renderer; old results remain tied to their captured stdout
hashes.

A seeded, optional synonym pass changes only filler prose (never placeholders
or graph words), writes a **new** JSON file, and leaves review/rewrite to a
human. An early pass swapped the phrasal verb `run on` incorrectly; it was
rejected, and the swap list was corrected. The reviewed rewrite is
`payloads/operator_conversation_rewrite.json`. Reproduce a fresh draft and
build the rewrite into a fresh directory with:

```bat
python -m tools.conversational_variation payloads\operator_stdout_filler.json payloads\operator_stdout_trigrams.json --seed 20261031 --chance 0.4 --out new-draft.json
python tools\embed_payload.py payloads\operator_conversation_rewrite.json payloads\operator_conversation_ontology_trigrams.json --link-pattern chain --out conversational-build
```

The full graph has 10 sets and 12 copies: 960 prose rows in the payload, printed
twice by the clean builder. One [ontology analyst cell](docs/ONTOLOGY_ANALYST_RESULT.md)
received all 1,921 zero-tick lines and **did not** misattribute the prose to the
binary's behavior. See the [offline cost and outcome audit](docs/ONTOLOGY_COST_AND_SCORE_AUDIT.md)
for exact billing and the limits of a single trial. No watermark measurement has evaluated this version;
variation is **not** verified watermark evasion. The previous `+` build remains
an opt-in comparator, not the current payload.

Tokenization check: local `o200k_base` encodes `glaciation` as `gl`, `aci`,
`ation` (with a leading space, ` gl`, `aci`, `ation`). A direct Astra input-token
probe with identical surrounding messages counted 13 tokens for an empty user
message versus 16 for `glaciation` and 16 for ` glaciation`: **three additional
input tokens** either way. Probe record:
`C:\Users\poly\scratch\goop-astra-token-count-20261031T080757Z.json`.
Splitting is observed; whether it causes the analyst behavior is not established.
A separate [rare-word token screen](docs/ANCHOR_TOKEN_SCAN.md) records the
single-token ontology candidate and the context-dependent `garlic` split.

## Test

Install pytest in your chosen Python environment, then from the same x64
developer environment run:

```bat
python -m pytest -q
```

Without MSVC on PATH, the native integration test skips. The builder itself
requires only Python's standard library and the MSVC/Windows SDK toolchain.

## Prior work

The complete pre-cleanup project, including previously ignored run evidence,
is retained at Git tag `legacy-before-minimal-stack` (`111a8dc`). No history
was rewritten. Cached environments are disposable and were not archived.
