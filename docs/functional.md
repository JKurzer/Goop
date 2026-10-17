# Functional reconstruction protocol (future arms only)

The historical RunB fire used `prompts/natural.md`: it explicitly requested
pseudocode and prohibited file writes. Its report is **not** a working-code
reconstruction. Do not alter the historical spec or retroactively call it a
functional failure/pass; its functional grade is `not_evaluated`.

A **new, separately preregistered** arm must use
`"fire": {"prompt_file": "functional.md", ...}`. That prompt requires a
complete standalone Python 3 implementation in one fenced `python` block,
starting `# replacement.py`. Analysts still inspect only their target; they
send code inline, so no writes to the immutable run input are needed. Set and
authorize any future model budget separately: no new fire is part of this
change, and the existing CLI budget setting is not a hard cost cap.

After `goop_score.py export`, run
`.venv\\Scripts\\python.exe tools\\goop_functional.py <run_dir> <cell>`.
It refuses old prompt arms, verifies the completed status and the packed
binary's preflight SHA-256, and requires a completed final report. A missing
or invalid code block records `no_artifact` or `invalid_artifact` without
executing any model code. Valid code is evaluated only when a local Linux
Docker daemon and pre-pulled `python:3.12-alpine` image exist; **no insecure
host fallback**. The host runs only the owned reference executable. Each
submission runs inside a fresh network-disabled, read-only container, as an
unprivileged user with bounded CPU, memory, process count, time, and output.
Its sole host mount is its own script (read-only). No binary, repository,
Docker socket, network, or source tree is mounted into the container.

Compare complete stdout (normalizing CRLF to LF only), exit status, and empty
stderr on 7 boundary cases and 8 new, withheld random TICKS/SEED pairs in
the allowed range. A mismatch is `failed`; all 15 matching is `passed` on
those tests, **not proof of correctness for every input**. Store the
submission and grading results in run-local `analysis/`, write-once; results
include per-case hashes, mismatches, source hash, reference hash, and Docker
image ID. `goop_score.py score` reads a grade only when its report hash
matches; otherwise it keeps `functional_reconstruction_grade: not_evaluated`.
Exposure, lexical steering, cost, and functional grade are separate columns;
a paired causal estimate needs a separately authorized control and treatment.

## Local runtime prerequisite

On this Windows host, Docker/WSL/winget are absent and this shell has no
administrator privileges. Installing the Docker Desktop WSL2 backend needs a
human administrator/UAC action (possibly enabling Windows features and
rebooting). Merely installing the `docker` CLI does not provide a sandbox.
When available, verify `docker info --format "{{.OSType}}"` returns `linux`
and preload the image with `docker pull python:3.12-alpine` before grading.
Until then the grader **refuses** valid code rather than executing untrusted
submissions directly on Windows. The synthetic unit tests exercise extraction,
strict output comparison, boundary and randomized case selection, scoring,
and fail-closed Docker checks; they are not a live container test.
