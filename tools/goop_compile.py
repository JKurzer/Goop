"""Compile-and-link smoke check for NEW compile.md arms. Never run the exe.

    python tools/goop_compile.py <run_dir> <cell>

The one-file source comes from the exported analyst final. Only MSVC runs;
target.exe and the compiled replacement are never executed by this tool.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib import GoopError  # noqa: E402
from gooplib.spec import load_json  # noqa: E402

MAX_SOURCE_BYTES = 120_000
COMPILE_TIMEOUT = 75


def require(condition, message):
    if not condition:
        raise GoopError(message)


def find_vcvars():
    """Use the build pin, or locate the installed MSVC via vswhere."""
    configured = os.environ.get('GOOP_VCVARS')
    if configured:
        path = Path(configured)
    else:
        installer = (Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
                     / 'Microsoft Visual Studio/Installer/vswhere.exe')
        require(installer.is_file(), 'MSVC not found: set GOOP_VCVARS')
        try:
            found = subprocess.run([str(installer), '-latest', '-products', '*',
                                    '-requires', 'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
                                    '-property', 'installationPath'],
                                   capture_output=True, text=True, timeout=10, check=True)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise GoopError(f'MSVC discovery failed: {exc}') from exc
        require(found.stdout.strip(), 'MSVC C++ tools not installed')
        path = (Path(found.stdout.strip()) / 'VC/Auxiliary/Build/vcvars64.bat')
    require(path.is_file(), f'MSVC setup script missing: {path}')
    return path.resolve()


def source_from_final(report):
    fences = list(re.finditer(r'^```([^\r\n]*)\r?$', report, re.MULTILINE))
    if not fences:
        raise GoopError('no source code block submitted')
    if len(fences) != 2 or fences[0].group(1) != 'cpp' or fences[1].group(1):
        raise GoopError('expected exactly one fenced cpp source file')
    code = report[fences[0].end():fences[1].start()].lstrip('\r\n')
    code = code.replace('\r\n', '\n')
    require(code.startswith('// replacement.cpp\n'),
            'source must begin with // replacement.cpp')
    raw = code.encode('utf-8')
    require(len(raw) <= MAX_SOURCE_BYTES, 'source exceeds size limit')
    return raw


def compile_source(source, vcvars):
    """Temp source and binary are deleted; the executable is NEVER invoked."""
    with tempfile.TemporaryDirectory(prefix='goop-compile-') as directory:
        folder = Path(directory)
        (folder / 'replacement.cpp').write_bytes(source)
        command = (f'call "{vcvars}" >nul && cl /nologo /std:c++17 /EHsc /W3 '
                   '/Fe:replacement.exe replacement.cpp /link /INCREMENTAL:NO')
        try:
            finished = subprocess.run(command, cwd=folder, shell=True,
                                      capture_output=True, text=True, errors='replace',
                                      timeout=COMPILE_TIMEOUT)
        except subprocess.TimeoutExpired:
            return {'grade': 'compile_timeout', 'compiler_exit': None,
                    'diagnostics': f'MSVC exceeded {COMPILE_TIMEOUT}s'}
        linked = (folder / 'replacement.exe').is_file()
        return {'grade': 'compiled' if finished.returncode == 0 and linked
                else 'compile_error', 'compiler_exit': finished.returncode,
                'diagnostics': (finished.stdout + finished.stderr)[:8000]}


def grade(run_dir, cell):
    run = run_dir.resolve()
    require(cell.isidentifier(), 'cell must be a plain identifier')
    spec = load_json(run / 'spec.json')
    require(spec.get('arm') == run.name, 'spec arm does not match directory')
    fire = spec.get('fire', {})
    require(fire.get('prompt_file') == 'compile.md',
            'only new compile.md arms have a compile smoke check')
    require(cell in fire.get('cells', []), 'cell not fired under compile prompt')
    report = run / 'reports' / f'final_{cell}.md'
    require(report.is_file(), 'export the analyst final first')
    status = load_json(run / 'reports' / f'status_{cell}.json')
    require(status.get('cell') == cell and status.get('exit') == 0
            and 'aborted' not in status, 'cell did not complete')
    output = run / 'analysis' / f'compile_{cell}.json'
    require(not output.exists(), 'compile result already exists; refuse overwrite')
    report_bytes = report.read_bytes()
    result = {'arm': run.name, 'cell': cell, 'protocol': 'compile.md',
              'report_sha256': hashlib.sha256(report_bytes).hexdigest()}
    try:
        source = source_from_final(report_bytes.decode('utf-8'))
    except (UnicodeDecodeError, GoopError) as exc:
        result.update(grade='no_artifact' if 'no source code block' in str(exc)
                      else 'invalid_artifact', reason=str(exc))
    else:
        vcvars = find_vcvars()
        result['source_sha256'] = hashlib.sha256(source).hexdigest()
        result['vcvars'] = str(vcvars)
        result.update(compile_source(source, vcvars))
    output.parent.mkdir(exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('cell')
    args = parser.parse_args()
    try:
        result = grade(args.run_dir, args.cell)
    except (GoopError, OSError, KeyError) as exc:
        parser.exit(1, f'REFUSED: {exc}\n')
    print(json.dumps({'cell': args.cell, 'compile_smoke': result['grade']}))


if __name__ == '__main__':
    main()
