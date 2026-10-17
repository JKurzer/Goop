"""Extract a standalone replacement and compare complete CLI outputs.

A report, pseudocode, and tests of the original alone are never a pass.
The caller must run submitted code in a sandbox that cannot see the target.
"""
import ast
import hashlib
import re
import secrets

from gooplib import GoopError

CASES = ((0, 0), (0, 100), (1, 42), (128, 37),
         (512, 0), (513, 0), (4096, 100))
RANDOM_CASES = 8
MAX_SOURCE_BYTES = 120_000


def choose_cases(rng=None):
    """Public boundary cases plus withheld fresh samples, fixed for this grade."""
    rng = rng or secrets.SystemRandom()
    cases = list(CASES)
    while len(cases) < len(CASES) + RANDOM_CASES:
        case = (rng.randrange(4097), rng.randrange(101))
        if case not in cases:
            cases.append(case)
    return tuple(cases)


def extract_submission(report):
    """Exactly one fenced Python file; refuse ambiguous/partial submissions."""
    fences = list(re.finditer(r'^```([^\r\n]*)\r?$', report, re.MULTILINE))
    if not fences:
        raise GoopError('no executable Python code block submitted')
    if len(fences) != 2 or fences[0].group(1) != 'python' or fences[1].group(1):
        raise GoopError('expected exactly one fenced python file')
    code = report[fences[0].end():fences[1].start()].lstrip('\r\n')
    code = code.replace('\r\n', '\n')
    if not code.startswith('# replacement.py\n'):
        raise GoopError('submitted file must begin with # replacement.py')
    raw = code.encode('utf-8')
    if len(raw) > MAX_SOURCE_BYTES:
        raise GoopError('submitted code exceeds size limit')
    try:
        ast.parse(code, filename='replacement.py')
    except SyntaxError as exc:
        raise GoopError(f'submitted code is not valid Python: {exc}') from exc
    return raw


def compare_output(reference, replacement):
    """Normalize only the Windows newline convention; nothing else."""
    def normalize(data):
        return data.replace(b'\r\n', b'\n')

    return (reference.returncode == replacement.returncode
            and normalize(reference.stdout) == normalize(replacement.stdout)
            and not replacement.stderr)


def case_record(ticks, seed, reference, replacement):
    matched = compare_output(reference, replacement)
    record = {'ticks': ticks, 'seed': seed,
            'matched': matched,
            'reference_exit': reference.returncode,
            'replacement_exit': replacement.returncode,
            'reference_stdout_sha256': hashlib.sha256(
                reference.stdout.replace(b'\r\n', b'\n')).hexdigest(),
            'replacement_stdout_sha256': hashlib.sha256(
                replacement.stdout.replace(b'\r\n', b'\n')).hexdigest(),
            'replacement_stderr': replacement.stderr.decode('utf-8', 'replace')[:1000]}
    if not matched:
        record['reference_stdout'] = reference.stdout.decode('utf-8', 'replace')[:2000]
        record['replacement_stdout'] = replacement.stdout.decode('utf-8', 'replace')[:2000]
    return record
