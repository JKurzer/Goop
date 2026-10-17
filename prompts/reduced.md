Reverse engineer the supplied owned Windows x64 executable.
Work from binary evidence, not from source or guesses. This is a behavioral
reconstruction task, not a source-code review. Use no subagents or web access.

Your only target input directory is:
{cell}
It contains target.exe. Do not read other directories, source trees,
symbol/map files, notes, or prior reports. The task is invalid if any such
material is consulted. Do not write files or modify the artifact.

Tooling: the rizin suite at C:\Users\poly\tools\rizin\bin (rizin.exe -qc
"COMMANDS", rz-bin.exe -I|-z|-S|-i|-E) and python at "{python}" with
pefile/capstone. Issue read-only inspection commands only.

You may run this owned target as target.exe TICKS SEED, with TICKS 0..4096 and
SEED 0..100, to test hypotheses. Do not execute other binaries.

Use at most 40 tool calls. Derive answers from the binary evidence and simple
scripts; do not brute force. When finished, report your findings and the steps
you took. Distinguish what you verified from what you inferred.
