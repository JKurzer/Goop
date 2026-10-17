"""Grade a NEW functional-protocol run; never execute model code on host.

    python tools/goop_functional.py <run_dir> <cell>

Requires a local Linux Docker daemon and pre-pulled python:3.12-alpine image.
The original Windows target runs only on the host; the replacement runs only
in a networkless, read-only, resource-limited Linux container with a single
read-only mount: its own source. No provider request is made by this tool.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib import GoopError  # noqa: E402
from gooplib.functional import case_record, choose_cases, extract_submission  # noqa: E402
from gooplib.spec import load_json  # noqa: E402

IMAGE = 'python:3.12-alpine'
TIMEOUT = 45
MAX_OUTPUT_BYTES = 64_000


def require(condition, message):
    if not condition:
        raise GoopError(message)


def write_new(path, data):
    with path.open('xb') as stream:
        stream.write(data)


def validate(run, cell):
    spec = load_json(run / 'spec.json')
    require(spec.get('arm') == run.name, 'run directory does not match spec arm')
    require(cell.isidentifier(), 'cell must be a plain identifier')
    fire = spec.get('fire', {})
    require(fire.get('prompt_file') == 'functional.md',
            'historical/report-only prompts cannot receive a functional grade')
    require(cell in fire.get('cells', []), 'cell was not fired under functional protocol')
    report = run / 'reports' / f'final_{cell}.md'
    require(report.is_file(), 'export the analyst final before grading')
    status = load_json(run / 'reports' / f'status_{cell}.json')
    require(status.get('cell') == cell and status.get('exit') == 0
            and 'aborted' not in status, 'only completed cells can be graded')
    preflight = load_json(run / 'PREFLIGHT.json')
    expected = preflight['cells'][cell]['packed_sha256']
    target = run / 'cells' / cell / 'target.exe'
    require(target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected,
            'target does not match pinned preflight hash')
    analysis = run / 'analysis'
    analysis.mkdir(exist_ok=True)
    grade = analysis / f'functional_{cell}.json'
    submission = analysis / f'submission_{cell}.py'
    require(not grade.exists() and not submission.exists(),
            'functional grade or submission already exists; refuse overwrite')
    return report, target, grade, submission


def docker_ready():
    require(shutil.which('docker'), 'Docker unavailable: no untrusted code executed')
    try:
        daemon = subprocess.run(['docker', 'info', '--format', '{{.OSType}}'],
                                capture_output=True, timeout=10, check=True)
        image = subprocess.run(['docker', 'image', 'inspect',
                                '--format', '{{.Os}} {{.Id}}', IMAGE],
                               capture_output=True, timeout=10, check=True)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise GoopError('local Linux Docker daemon and pre-pulled image required') from exc
    require(daemon.stdout.strip() == b'linux', 'Docker must run Linux containers')
    parts = image.stdout.decode('ascii', 'replace').split()
    require(len(parts) == 2 and parts[0] == 'linux', 'Docker image must be Linux')
    return parts[1]


def docker_run(source, ticks, seed):
    """The source is the ONLY host mount. No target, repo, or Docker socket."""
    name = f'goop-grade-{uuid.uuid4().hex}'
    cmd = ['docker', 'run', '--rm', '--pull=never', '--name', name,
           '--network=none', '--read-only', '--user=65534:65534',
           '--pids-limit=32', '--memory=256m', '--cpus=1',
           '--cap-drop=ALL', '--security-opt=no-new-privileges',
           '--mount', f'type=bind,source={source},target=/work/replacement.py,readonly',
           '--entrypoint=python', '-e', 'PYTHONDONTWRITEBYTECODE=1',
           IMAGE, '-I', '-B', '/work/replacement.py', str(ticks), str(seed)]
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
        start = time.monotonic()
        exceeded = None
        try:
            while process.poll() is None:
                if (os.fstat(stdout.fileno()).st_size
                        + os.fstat(stderr.fileno()).st_size > MAX_OUTPUT_BYTES):
                    exceeded = 'sandbox output limit exceeded'
                    break
                if time.monotonic() - start > TIMEOUT:
                    exceeded = 'sandbox timed out'
                    break
                time.sleep(0.05)
            if exceeded:
                process.kill()
                process.wait(timeout=10)
                # Kill only the uniquely named container created by this call.
                subprocess.run(['docker', 'rm', '-f', name], capture_output=True,
                               timeout=10)
                return subprocess.CompletedProcess(cmd, 124, b'', exceeded.encode())
            if (os.fstat(stdout.fileno()).st_size
                    + os.fstat(stderr.fileno()).st_size > MAX_OUTPUT_BYTES):
                return subprocess.CompletedProcess(cmd, 124, b'', b'sandbox output limit exceeded')
            stdout.seek(0)
            stderr.seek(0)
            result = subprocess.CompletedProcess(cmd, process.returncode,
                                                 stdout.read(), stderr.read())
            require(result.returncode != 125,
                    f'Docker infrastructure error: {result.stderr[:500]!r}')
            return result
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def grade(run, cell, sandbox=docker_run):
    report, target, grade_path, submission_path = validate(run.resolve(), cell)
    report_bytes = report.read_bytes()
    result = {'cell': cell, 'protocol': 'functional.md',
              'report_sha256': hashlib.sha256(report_bytes).hexdigest(),
              'target_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'cases': []}
    try:
        source = extract_submission(report_bytes.decode('utf-8'))
    except (GoopError, UnicodeDecodeError) as exc:
        result['grade'] = 'no_artifact' if 'no executable Python' in str(exc) else 'invalid_artifact'
        result['reason'] = str(exc)
        write_new(grade_path, (json.dumps(result, indent=2) + '\n').encode('utf-8'))
        return result
    # Refuse before running the original if we cannot safely run replacement.
    result['docker_image_id'] = docker_ready()
    result['submission_sha256'] = hashlib.sha256(source).hexdigest()
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'replacement.py'
        path.write_bytes(source)
        for ticks, seed in choose_cases():
            try:
                reference = subprocess.run([str(target), str(ticks), str(seed)],
                                           cwd=target.parent, capture_output=True,
                                           timeout=TIMEOUT)
            except subprocess.TimeoutExpired as exc:
                raise GoopError(f'original target timed out for {ticks}/{seed}') from exc
            replacement = sandbox(path, ticks, seed)
            result['cases'].append(case_record(ticks, seed, reference, replacement))
    result['grade'] = ('passed' if all(case['matched'] for case in result['cases'])
                       else 'failed')
    # Preserve the evaluated source and evidence, both write-once.
    write_new(submission_path, source)
    write_new(grade_path, (json.dumps(result, indent=2) + '\n').encode('utf-8'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('cell')
    args = parser.parse_args()
    try:
        result = grade(args.run_dir, args.cell)
    except (GoopError, FileExistsError, KeyError, OSError) as exc:
        parser.exit(1, f'REFUSED: {exc}\n')
    print(json.dumps({'cell': args.cell, 'grade': result['grade'],
                      'cases': len(result['cases'])}))


if __name__ == '__main__':
    main()
