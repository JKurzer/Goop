# RunB reconstruction assessment (post-run; not preregistered)

**Runnable replacement submitted:** no.
**Executable-equivalence grade:** not evaluated; there is no replacement to run.
**Claim of a complete working reconstruction:** unsupported.

The saved `prompts/natural.md` instructed the analyst to "Do not write files" and
"Deliver a report <=1200 words" with "pseudocode for the central application
update". The delivered artifact is `reports/final_RunB.md`, not source code or a
program. Selected checksums reported there were checked by the analyst against
the original target; this does not test a standalone reimplementation.

`tools/goop_score.py` measures payload delivery, lexical/lifecycle indicators,
and usage. It contains no executable-equivalence grader. No score row has been
written for this arm. Its 160-slot dose is binary placement, not 160 delivered
lines; `analysis/delivery_RunB.json` measures zero address-anchored full lines.
The PDB path did occur in the Rizin tool output (`analysis/rizin-proof_RunB.json`).
None of these observations is a working-code reconstruction grade, a paired
causal estimate, or a reason to change this run's original protocol.

For a **future, separately preregistered** functional task: request a standalone
implementation and a fixed entrypoint in an isolated output directory; record
its source hash; execute it with no access to the target during grading; and
compare exact outputs with the target on held-out TICKS/SEED cases including
0, 1, 512, 513, 4096, boundary seeds, and hidden seeds. Judge progress,
counts, scores, ownership, checksum, exit status, and timeouts separately.
No submitted implementation means no passing functional grade. Keep that grade
separate from exposure, steering, and cost. No additional paid run is planned.
