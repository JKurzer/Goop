# Compile-only source smoke check (future arms)

For a new, separately authorized arm, select `"fire": {"prompt_file":
"compile.md", ...}`. This prompt demands one complete standalone C++17 file
inside a single fenced `cpp` block. It does not change the historical RunB
prompt, report, paid result, or evidence. No new model fire is authorized by
this document.

After exporting the future cell's final answer, run
`.venv\\Scripts\\python.exe tools\\goop_compile.py <run_dir> <cell>`.
The tool locates the installed MSVC via `GOOP_VCVARS` or `vswhere`, writes
the submitted source to a temporary directory, **compiles and links** it,
records the compiler result in write-once `analysis/compile_<cell>.json`, and
deletes the temporary source/object/executable. It never launches the
submitted program, Docker, or the target. `compiled` means only that MSVC
produced an executable; `compile_error`, `compile_timeout`, `no_artifact`,
and `invalid_artifact` do not pass the smoke check. None of these is a
functional-correctness grade or evidence of behavioral equivalence.

The compile-and-link tests run real MSVC against trusted synthetic source:
valid source must link, invalid syntax must fail, and a source file without
`main` must fail at link time. They do not run the produced executable.
