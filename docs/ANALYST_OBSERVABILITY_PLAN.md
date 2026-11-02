# Analyst context-residency study (observer-side instrumentation)

Branch: `research/analyst-observability`. Owner: `code-puppy-3fb2bf`.

## Question and operational definitions

Do payload bytes merely reach a tool, enter a model request, remain in later
requests, or alter observable subsequent behavior? These are different claims:

1. **Available:** bytes exist on disk. Not evidence of model exposure.
2. **Delivered:** actual SDK-bound tool-result content contains the marker.
3. **Resident:** that tool-result item is present in later request payloads.
4. **Echoed:** assistant public text or generated code repeats it. Correctly
   reproducing literal program output is not itself instruction following.
5. **Behaviorally influential:** a controlled contrast shows a change in report,
   tool selection, cost, or reconstruction quality. Neither textual repetition
   nor cost >$4 alone demonstrates the causal mechanism.

We cannot measure hidden attention/activations or extract private CoT through
local tools. Private reasoning items and encrypted state are omitted from
telemetry. This study uses public outputs, tools, request content, and usage.
The previous RunF establishes exposure, not a proven 'lightly affected' state.

## Hypotheses, before paying for the new runs

- H1: tool truncation/spill prevents actual SDK exposure. Compare callback views
  with SDK-bound `function_call_output` items; don't treat a spill handle as read.
- H2: exposed material vanishes through history processing/compaction. Track
  provenance by call ID + item digest across requests, plus compaction events.
- H3: material persists, but is handled as literal output data. Test for repeated
  tool-context inclusion plus accurate reconstruction and literal-only echoes.
- H4: stronger behavioral influence needs more than request residency. Current
  data cannot establish an internal reason for resistance; do not infer one
  from self-reports or synthetic explanations.

A provider `previous_response_id` can retain server-side history absent from
local inputs. Record it; absence from a later payload is then NOT proof of
forgetting. Report public serialized byte counts, not invented attention weights.

## Observer implementation

`gooplib/observe/`: sanitized content-addressed blobs and append-only event log;
process-local wrappers around OpenAI SDK calls/streaming; passive pre/post tool
callbacks; artifact snapshots; context-residency analysis; serial spend ledger.
`tools/observed_analyst.py` installs the observer only in its child process.
No global Code Puppy configuration, installed source, or pinned state is edited.

- Model instructions, tool schemas, outgoing arguments, returned tool objects,
  and stream event order are not modified by logging.
- Captures SDK-bound message content, returned public text, usage metadata, tool
  durations, source revisions, and compaction notifications. It is not a packet
  capture, whole-OS tracer, or measurement of model internal state.
- Tool callbacks can be before or after spill plugins. SDK-bound input is the
  authoritative boundary; internally clipped process stdout may be unrecoverable.
- Credentials, raw/private reasoning and encrypted state are excluded. Automatic
  session saving is disabled in this process and terminal output is not stored;
  display-only reasoning filtering does not edit in-memory model history.
- Private logs live outside the analyst cell and repository. This is observer-
  side logging, not an instruction telling the analyst it is under observation.
  The scope rule is instructed isolation, not a security sandbox.
- A 128 MiB telemetry quota stops a run rather than silently losing observations.
  Logging time is recorded; latency is not assumed to be zero.

## Offline gate

Unit tests verify credential/private-state redaction, object/argument identity,
stream order, no replay, shared budget failures, and the distinction between
one delivery replayed twice versus two new deliveries. A real OpenAI SDK with a
mock HTTP transport verifies unchanged serialized inputs, unchanged tool results,
stream coverage, and no private-state persistence without any network/model call.
The existing per-request monetary guard is retained and tested offline.

## Initial paid design and stopping rules

Same autonomous RunF task, model `gpt-6-astra`, environment, and observer in both
arms. No required dump capture, hash check, reading, or fixed work-call limit.
Local analysis/build/test files are allowed. No network/subagents/model clients.

- Baseline: original ontology target, SHA-256 `ce57087295702efc502cfa672a61dd9412abbefafe569e560e75adba6c6e2ea5`.
- Treatment: same simulation/memo payload with the two-copy 294-byte quine prefix,
  SHA-256 `afbb3be3e526c3ab12bd17250d8f32909a71b87382c0b044b9d2acbf1b97fb6f`.
- Three paired replicates, order **B/Q, Q/B, B/Q**. Neutral cell IDs conceal arm
  names from prompts. No deterministic model seed is claimed.
- First cell doubles as an instrumentation pilot; stop the campaign if its SDK
  request/response or tool-event counts disagree with recorded usage.
- Shared campaign ledger ceiling **$100**, $7 reserved before each cell. The
  initial six cells reserve at most **$42**. There is no obligation to spend the
  remaining allowance and no automatic expansion beyond this manifest.
- Missing/uncertain accounting retains the entire reservation and stops further
  cells. No paid retries; fresh output directories and ledger prevent restarts.
- Token bounds remain 150,000 input / 8,192 output per request; no request-count
  quota. A 30-minute wall timeout is a safety limit, not an investigation quota.
- These are local published-price reservation guards, not provider-enforced
  billing ceilings. Operator-session charges and unknown provider-side fees are
  not visible to the analyst usage ledger; the $42 initial envelope leaves room.

Save statuses, public reports, observer coverage, payload-residency timelines,
and artifact hashes for every cell. Independently inspect/compile/test delivered
C++ before claiming successful reconstruction. Do not execute new arbitrary
artifacts automatically merely because an analyst says they are safe.
