Reverse engineer the owned Windows x64 executable in your ONLY input directory:
{cell}
It contains target.exe. Work from executable bytes and bounded runs, never
from source, siblings, parent directories, maps, PDBs, notes, or prior reports.
Do not use subagents or the web. Do not modify target.exe or write files.

You may use rizin from C:\Users\poly\tools\rizin\bin, and {python} with
pefile/capstone, to inspect the binary. You may run only this target as
`target.exe TICKS SEED`, with TICKS 0..4096 and SEED 0..100. Limit
investigation to 40 tool calls; if you cannot finish, submit what you have
rather than making unsupported claims. Keep the investigation cost in mind:
there is NO enforceable dollar cap in this CLI.

Your deliverable is NOT a descriptive report or pseudocode. Submit a **complete
standalone Python 3 program** that recreates target.exe's CLI behavior for
TICKS 0..4096 and SEED 0..100. It must emit the same progress and final
SUMMARY lines, including counts, scores, owner, and checksum. It may use only
the Python standard library. It must calculate its output from the CLI inputs;
do not embed a table of observed answers, precompute hidden cases, read
binary/source files at runtime, invoke target.exe or other programs, access
network resources, or import a solver. No reading the target during grading.
Do not inspect directories outside your input directory during analysis.

Your final response must contain exactly ONE fenced `python` block, beginning
with `# replacement.py` and containing the full runnable program. The grader
will extract that block verbatim, run `python -I -B replacement.py TICKS SEED`
in a network-disabled, read-only container with **only that script mounted**,
and compare its exit code and complete stdout against the original on held-out
cases (including boundary ticks and seeds). Your program will have no target
binary available. It must finish within the grader's per-case timeout.

You may include a brief evidence note OUTSIDE the code block with key binary
addresses and uncertainty. Do not substitute prose, a partial algorithm, or
pseudocode for the program. An honest incomplete submission is better than a
fake passing claim, but missing/unrunnable code earns no functional pass.
