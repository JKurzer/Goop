"""Export the submitted C++ source verbatim; never execute it.

Usage: python tools/goop_cpp_extract.py runs/<arm> [runs/<arm> ...]
The export is write-once and SHA-bound to the compile-only result.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.goop_compile import source_from_final  # noqa: E402


def export(run):
    report_path = run / 'reports/final_RunB.md'
    compile_path = run / 'analysis/compile_RunB.json'
    output = run / 'analysis/replacement_RunB.cpp'
    report = report_path.read_bytes()
    grade = json.loads(compile_path.read_text(encoding='utf-8'))
    if hashlib.sha256(report).hexdigest() != grade['report_sha256']:
        raise ValueError(f'{run}: report hash differs from compile evidence')
    source = source_from_final(report.decode('utf-8'))
    if hashlib.sha256(source).hexdigest() != grade['source_sha256']:
        raise ValueError(f'{run}: C++ hash differs from compile evidence')
    with output.open('xb') as stream:
        stream.write(source)
    print(output, len(source), grade['source_sha256'])


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('usage: goop_cpp_extract.py runs/<arm> ...')
    try:
        for argument in sys.argv[1:]:
            export(Path(argument).resolve())
    except (OSError, ValueError, KeyError, UnicodeDecodeError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
