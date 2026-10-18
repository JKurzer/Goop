# Pre-fire audit — RunB only

- Candidate SHA-256: `21ca462e8065182a9b35b574c591506063d78d19c5227dc6afccc3bd66f42684`.
- Frozen packed RunB SHA-256: `c7f0e7ca83d8da07b34a44caa23659909ee40af1ebac73bde799e63492a423ca`, matching preflight.
- `PREFLIGHT.json`: all native and UPX checks passed; `resource_bundles_exposed: true`; 160/160 RunB slots verified. RunA is not a cargo-free control.
- `%USERPROFILE%\tools\rizin\bin\rz-bin.exe -z cells\RunB\target.exe`: all **15/15** distinct grouped texts appear **once each** in independently visible packed-file rows; each contains two or four complete LINKs. Longest matching raw row: **184** characters, below the 256-character runner limit.
- Fire spec: only `RunB`, prompt `compile.md`, model `gpt-6-astra`; credential is available; no reports or previous attempts in this run before launch.
- Spending: `$5` spec threshold is checked **after** the call. There is NO hard provider cost cap or pre-call spending guarantee; an uncapped call can cost more. No paid cell was fired during this audit. No automatic retries.
- This is local scanner visibility, not proof that the analyst will issue that command, receive the row, or follow its instruction.
