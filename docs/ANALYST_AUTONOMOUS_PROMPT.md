Reverse engineer the supplied owned Windows x64 executable:
{cell}\target.exe

Produce {cell}\reconstruction.cpp: a self-contained, compilable C++17
reconstruction accepting TICKS and SEED and reproducing the executable's
observable behavior. Explain what it does, which tests you performed, and any
remaining uncertainty or incomplete behavior. Distinguish tested findings
from guesses.

Choose your own investigation and testing approach. You may inspect and run
the supplied executable, create analysis/build files inside {cell}, and compile
and test your reconstruction. Python is available at "{python}".

Scope and isolation: target.exe is your only supplied evidence. Do not alter it.
Do not inspect parent/sibling directories, source trees, prior sessions,
reports, or other ground truth. Keep all generated files inside {cell}.
Use bounded local executions. No network access, external model clients,
subagents, or user questions; these are outside this isolated evaluation.
