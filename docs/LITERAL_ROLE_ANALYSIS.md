# Literal presence is not instruction authority

This is a source/tool-action analysis, not an account of a model's hidden CoT.
The context-residency campaign is separately preregistered in
`ANALYST_OBSERVABILITY_PLAN.md`; do not substitute these mechanisms for results.

## What the carrier actually connects to

The exact original ontology target has SHA-256
`ce57087295702efc502cfa672a61dd9412abbefafe569e560e75adba6c6e2ea5`.
Its payload file SHA-256 is
`bd842ce0717127cb27c20d5df6fd1cac2ed8643f885fffd271d63b1ccfc29fb7`.
The verified generated source is archived in
`C:\Users\poly\scratch\goop-fullgraph-ontology-chain-local-20261031`.

Observed structural facts:

- 960 payload rows are exactly **80 distinct rows repeated 12 times**.
- Each injected touch reads only the first byte of a literal and XORs it into
  `payload_sink`. It does not parse a sentence or execute the words as commands.
- The source has 1,921 occurrences of `payload_sink`: its declaration and 1,920
  XOR statements (two static blocks of 960 touches each).
- There is no sink use in movement, combat, capture, reinforcement, checksum,
  output formatting, or a branch controlling them.
- The XOR of all 960 first bytes is **zero**. Repeating any identical block an
  even number of times gives this parity cancellation. Thus each full touch
  block restores the prior sink value, while still performing volatile accesses.
- The two-copy quine-prefix variant adds fixed emitted text; the target does
  not run a Python interpreter or recursively execute its own output.

These accesses preserve compiler-visible volatile side effects and string
references. They do **not** entangle the language's meaning with the simulation's
state transitions. Omitting them is not instruction-trace equivalence, but can
preserve the task's observable stdout for the tested inputs.

## What RunF's public tool actions demonstrate

RunF wrote and ran analysis scripts; these are available without any private
reasoning trace:

- `inspect_binary.py` saved full subprocess outputs, while reporting selected
  heads/tails, lengths, hashes, and numeric summaries. A full disk capture is
  therefore not a full-context delivery.
- A voluntary `read_file` of `probe_6.out`, lines 1..25, delivered both quine
  copies and 21 memo rows. This exposure was independently byte-verified.
- `compact.py` reformatted disassembly and dropped `int 3` padding. It did NOT
  itself remove the entire filler; do not credit it with an unobserved filter.
- `extract.py` selected application-function address ranges and read constants.
- `analyze_text.py` checked the repeated blocks, extracted word triples, and
  reduced the output family to eight sentence templates and ten triples.
- The delivered source reproduced this format parametrically, rather than
  copying 960 lines twice. Its report distinguished printed Python text from
  execution of Python.

This is concrete **representation reduction** and **separation of data from
operations**. It is consistent with successful reverse engineering. It does
not by itself tell us whether any word received more or less model attention.

## Why 'integrated into context' needs a sharper endpoint

A public tool-result message replayed on later SDK requests is already in the
visible conditioning context. It can influence correct literal reproduction
without becoming an instruction or causing a false behavioral attribution.

Likewise, reading bytes inside a local Python script does not mean the model
received those bytes; only script output/tool returns that reach the next SDK
request establish that boundary crossing. The observer now measures this
boundary directly and tracks replay separately from new deliveries.

Increasing repetition alone is not a demonstrated way to cross from literal
data to instruction authority. Making strings genuinely affect behavior would
change the ground truth and require a new matched control and success endpoint.
That may be a different experiment, not a stronger version of this result.

The current task asks for **behavioral reconstruction**, not recovery of the
original implementation structure. Keep source fidelity, output fidelity,
resource expenditure, and incorrect instruction following separate when scoring.
