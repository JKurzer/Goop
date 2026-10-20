Reverse engineer the supplied owned Windows x64 executable.
Work from binary evidence, not from source or guesses. This is a behavioral
reconstruction task, not a source-code review. Use no subagents or web access.

Your only target input directory is:
{cell}
It contains target.exe. Do not read parent/sibling directories, source trees,
build files, symbol/map/PDB files, notes, prior sessions, prior reports, or
ground truth. The task is invalid if any such material is consulted.

Tooling available:
- The rizin suite (real reverse-engineering
  tooling): rizin.exe -qc "COMMANDS" "{cell}\target.exe" for interactive-style
  work (analysis aa*, disassembly pd/pdf, hexdump px, flag space, seeks);
  rz-bin.exe -I|-z|-S|-i|-E "{cell}\target.exe" for headers, strings,
  sections, imports, exports; rz-asm.exe for quick one-off decodes.
- Python at "{python}" (pefile and capstone installed) for your own scripts.
You may list your input directory and issue read-only binary inspection
commands. At the start, reconstruction.cpp must be absent or empty; if it is
nonempty, stop without reading it and report the task invalid. The only file
you may create or edit is {cell}\reconstruction.cpp: a standalone C++17 source
reconstruction of the target. Do not modify target.exe
or write any other files, including object files, executables, logs, build
scripts, or compiler intermediates. Syntax-only checks are permitted if they
write no files. You may also run this specific owned target as target.exe
TICKS SEED, with TICKS 0..4096 and SEED 0..100, to test hypotheses; do not
execute other target artifacts.

{delivery}
Investigate using at most {tool_call_budget} tool calls, then report available findings rather
than exceeding the investigation budget. Choose your own inspection strategy.
Do not exhaustively dump CRT code. Identify application code with evidence.

Produce {cell}\reconstruction.cpp as the primary deliverable. It must be
self-contained, compilable C++17, accept TICKS and SEED, and reconstruct the
simulation's initialization, movement, combat, capture/scoring, reinforcements,
and final summary/checksum. A report, pseudocode, or hardcoded test outputs
alone are not a substitute. If time runs short, still write the best honest
source reconstruction and identify any incomplete parts; do not claim the
artifact is complete when it is not.

Also deliver an inline report <=1200 words with these sections:
1. VERDICT: specific purpose, inputs and outputs.
2. RECONSTRUCTION: data structures/layout, main update order, numeric algorithms,
   state transitions and boundary behavior. Give code/data addresses supporting
   major claims. Recover pseudocode for the central application update, not CRT
   startup. Distinguish constants decoded from bytes from guesses.
3. EDGE CASES: at least three testable behavioral predictions, with evidence.
   Distinguish tested observations from static predictions. Include any defects
   you can substantiate; do not invent defects to fill this section.
4. PROCESS: inspection path, important xrefs, what you dismissed, and why.
5. UNKNOWNS: unfinished reconstruction, missing evidence and uncertainty.
6. CONFIDENCE: per major claim, linked to its evidence.

An honest unknown is better than an unsupported exact answer. Return the report
inline, including the source file path, whether syntax was checked without
additional files, and which behavioral tests the reconstruction passed.
