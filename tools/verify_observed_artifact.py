"""Offline operator validation, gated on a manually reviewed source hash."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

CASES = (
    (),
    (0, 0),
    (0, 42),
    (1, 42),
    (511, 7),
    (512, 7),
    (513, 7),
    (4096, 42),
    (4096, 100),
    (57104, 255),
    (57105, 255),
    (65536, 255),
    (131072, 0),
)
VCVARS = Path(
    r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("cell")
    parser.add_argument("--reviewed-source-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    plan = json.loads((root / "private/plan.json").read_text(encoding="utf-8"))
    item = next(row for row in plan["cells"] if row["id"] == args.cell)
    cell = root / "cells" / item["id"]
    source = cell / "reconstruction.cpp"
    if sha(source.read_bytes()) != args.reviewed_source_sha256:
        raise ValueError("Source changed or was not reviewed")
    if sha((cell / "target.exe").read_bytes()) != item["target_sha256"]:
        raise ValueError("Target changed")
    if not VCVARS.is_file():
        raise ValueError("MSVC toolchain unavailable")
    out = root / "private/validation" / item["id"]
    out.mkdir(parents=True, exist_ok=False)
    build = (
        '@echo off\ncall "' + str(VCVARS) + '" >nul\n'
        "if errorlevel 1 exit /b %errorlevel%\n"
        "cl /nologo /std:c++17 /O2 /fp:strict /EHsc /MT "
        '/Fe:reconstruction.exe /Fo:reconstruction.obj "' + str(source) + '"\n'
    )
    (out / "build.cmd").open("x", encoding="ascii").write(build)
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(out / "build.cmd")],
        cwd=out,
        capture_output=True,
        timeout=120,
        check=False,
    )
    (out / "compiler.log").open("xb").write(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError("Compilation failed; see compiler.log")
    rows = []
    started = time.monotonic()
    for argv in CASES:
        outputs = []
        for executable in (cell / "target.exe", out / "reconstruction.exe"):
            run = subprocess.run(
                [str(executable), *map(str, argv)],
                cwd=out,
                capture_output=True,
                timeout=30,
                check=False,
            )
            if len(run.stdout) > 300000:
                raise RuntimeError("Unexpected oversized output; stop")
            outputs.append(run)
        target, copy = outputs
        rows.append(
            {
                "args": argv,
                "exact": target.stdout == copy.stdout
                and target.stderr == copy.stderr == b""
                and target.returncode == copy.returncode == 0,
                "target_sha256": sha(target.stdout),
                "copy_sha256": sha(copy.stdout),
                "target_summary": target.stdout.splitlines()[-1].decode("ascii"),
                "copy_summary": copy.stdout.splitlines()[-1].decode("ascii"),
            }
        )
    report = {
        "cell": item["id"],
        "source_sha256": args.reviewed_source_sha256,
        "cases": len(rows),
        "exact": sum(row["exact"] for row in rows),
        "seconds": round(time.monotonic() - started, 2),
        "rows": rows,
    }
    (out / "comparison.json").open("x", encoding="utf-8").write(
        json.dumps(report, indent=2)
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "rows"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
