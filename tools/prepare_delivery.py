"""Plan bounded stdout delivery; no model calls, runner changes, or target writes."""
import argparse
import hashlib
import json
from pathlib import Path

MAX_STDOUT_JSON = 6000
MAX_RETURN_JSON = 8000
MAX_ROWS = 200
MAX_ROW_CHARS = 190
MAX_DELIVERY_CALLS = 20  # Leave at least half the 40-call investigation budget.


def sha(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


def normalized_rows(text):
    text = text.replace('\r\n', '\n')
    if not text or not text.endswith('\n'):
        raise ValueError('stdout must be nonempty and newline-terminated')
    rows = text[:-1].split('\n')
    if any(not row or len(row) > MAX_ROW_CHARS or
           any(not 32 <= ord(char) <= 126 for char in row) for row in rows):
        raise ValueError('stdout rows must be nonempty printable ASCII, at most 190 characters')
    return rows


def make_command(python, start, stop, digest):
    if any(char in str(python) for char in '\r\n"%'):
        raise ValueError('interpreter path cannot contain shell expansion or quote characters')
    script = (
        "import hashlib,subprocess,sys; "
        "text=subprocess.check_output(['target.exe','0','0'],text=True,timeout=30); "
        f"assert hashlib.sha256(text.encode('ascii')).hexdigest()=='{digest}'; "
        f"sys.stdout.write('\\n'.join(text.splitlines()[{start}:{stop}])+'\\n')"
    )
    return f'"{python}" -c "{script}"'


def plan_delivery(text, python, *, max_calls=MAX_DELIVERY_CALLS):
    if type(max_calls) is not int or not 1 <= max_calls <= 40:
        raise ValueError('delivery call allowance must be an integer from 1 to 40')
    rows = normalized_rows(text)
    normalized = '\n'.join(rows) + '\n'
    digest = sha(normalized)
    chunks = []
    start = 0
    while start < len(rows):
        stop = start
        while stop < len(rows) and stop - start < MAX_ROWS:
            candidate = '\n'.join(rows[start:stop + 1]) + '\n'
            if len(json.dumps(candidate)) > MAX_STDOUT_JSON:
                break
            stop += 1
        content = '\n'.join(rows[start:stop]) + '\n'
        command = make_command(python, start, stop, digest)
        # Reserve room for the actual shell result envelope, command and escaping.
        estimate = len(json.dumps({'stdout': content, 'command': command})) + 1000
        if estimate > MAX_RETURN_JSON:
            raise ValueError('command/envelope exceeds the reserved inline budget')
        chunks.append({'start': start, 'stop': stop, 'sha256': sha(content),
                       'command': command, 'estimated_return_chars': estimate})
        start = stop
    if len(chunks) > max_calls:
        raise ValueError(f'delivery exceeds {max_calls} calls; explicitly revise the protocol/budget')
    return {'version': 1, 'rows': len(rows), 'stdout_sha256_lf': digest,
            'max_return_json_chars': MAX_RETURN_JSON, 'max_delivery_calls': max_calls,
            'chunks': chunks}


def delivery_prompt(plan, *, total_calls=40):
    if type(total_calls) is not int or total_calls < len(plan['chunks']):
        raise ValueError('total call budget must cover every delivery call')
    parts = [
        'Before reporting, retrieve all target.exe 0 0 output using the commands below.',
        'Run EACH command in a SEPARATE shell call with cwd set to {cell}.',
        'Read each complete stdout in order, including repeated rows and the final SUMMARY.',
        'Do not combine commands, pack rows, deduplicate, or redirect output to stderr.',
        'Each command reruns the deterministic zero-tick target and emits only its assigned',
        'non-overlapping row range. The hash guard stops delivery if the output changes.',
        f'This requires {len(plan["chunks"])} calls within the {total_calls}-call budget.',
        'If a return is clipped/spilled, recover that specific range in smaller separate',
        'calls before reporting; never count a preview as complete delivery.',
    ]
    for index, chunk in enumerate(plan['chunks'], 1):
        parts.append(f'\nChunk {index}: rows [{chunk["start"]}, {chunk["stop"]})\n'
                     f'```bat\n{chunk["command"]}\n```')
    return '\n'.join(parts) + '\n'


def render_analyst_prompt(template, plan, *, total_calls=40):
    if template.count('{delivery}') != 1 or template.count('{tool_call_budget}') != 1:
        raise ValueError('prompt needs one delivery and one tool_call_budget placeholder')
    return template.replace('{delivery}', delivery_prompt(plan, total_calls=total_calls)).replace(
        '{tool_call_budget}', str(total_calls))


def verify_returns(plan, results):
    """Fail closed on missing/reordered/clipped/spilled/changed shell returns."""
    if len(results) != len(plan['chunks']):
        raise ValueError('missing or extra delivery returns')
    recovered = []
    sizes = []
    for chunk, result in zip(plan['chunks'], results):
        if not isinstance(result, dict):
            raise TypeError('spilled or non-structured delivery return')
        size = len(json.dumps(result))
        if size > MAX_RETURN_JSON:
            raise ValueError('delivery return exceeds inline budget')
        if not result.get('success') or result.get('exit_code') != 0 or result.get('stderr'):
            raise ValueError('delivery command failed or emitted stderr')
        if result.get('command') != chunk['command']:
            raise ValueError('delivery command mismatch')
        content = (result.get('stdout') or '').replace('\r\n', '\n').rstrip('\n') + '\n'
        if len(normalized_rows(content)) != chunk['stop'] - chunk['start'] or sha(content) != chunk['sha256']:
            raise ValueError('delivery rows missing, reordered, or changed')
        recovered.append(content)
        sizes.append(size)
    if sha(''.join(recovered)) != plan['stdout_sha256_lf']:
        raise ValueError('full delivery hash mismatch')
    return {'full_delivery_verified': True, 'rows': plan['rows'],
            'calls': len(results), 'max_return_json_chars': max(sizes),
            'stdout_sha256_lf': plan['stdout_sha256_lf']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stdout', type=Path, help='captured target.exe 0 0 stdout')
    parser.add_argument('--python', required=True, help='persistent analyst interpreter')
    parser.add_argument('--out', type=Path, required=True, help='new private staging directory')
    parser.add_argument('--delivery-call-allowance', type=int, default=MAX_DELIVERY_CALLS,
                        help='explicit per-run delivery allowance')
    parser.add_argument('--tool-call-budget', type=int, default=40,
                        help='total delivery plus investigation calls')
    args = parser.parse_args()
    plan = plan_delivery(args.stdout.read_text(encoding='ascii'), args.python,
                         max_calls=args.delivery_call_allowance)
    args.out.mkdir(parents=True, exist_ok=False)
    for name, content in [('delivery-plan.json', json.dumps(plan, indent=2)),
                          ('delivery-prompt.md', delivery_prompt(plan, total_calls=args.tool_call_budget))]:
        with (args.out / name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    print(f'{len(plan["chunks"])} bounded calls, {plan["rows"]} rows; no model launched.')


if __name__ == '__main__':
    main()
