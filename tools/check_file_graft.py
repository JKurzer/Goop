"""Exercise file-graft capture/verify with the real runner in a disposable local cell."""
import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path


def check(plan, target):
    # This imports the installed local harness, not an analyst or model client.
    from code_puppy.config import get_tool_output_limit_chars
    from code_puppy.tools.command_runner import _run_command_sync

    if plan.get('mode') != 'file-graft' or plan.get('instructed_calls') != 2:
        raise ValueError('expected a two-command file-graft plan')
    if not target.is_file():
        raise ValueError('target executable missing')
    with tempfile.TemporaryDirectory(prefix='goop-file-graft-') as directory:
        cell = Path(directory)
        shutil.copyfile(target, cell / 'target.exe')
        results = []
        limit = get_tool_output_limit_chars()
        for step in ('capture', 'verify'):
            command = plan[f'{step}_command']
            result = _run_command_sync(command, str(cell), 45,
                                       'goop-file-graft-preflight', silent=True).model_dump()
            if not result['success'] or result['exit_code'] != 0 or result['stderr']:
                raise ValueError(f'{step} command failed: {result["stderr"]}')
            if result['command'] != command or (limit > 0 and len(json.dumps(result)) > limit):
                raise ValueError(f'{step} result changed or exceeded harness limit')
            if result['stdout'].strip() != f'{"captured" if step == "capture" else "verified"} {plan["bytes"]}':
                raise ValueError(f'{step} byte count mismatch')
            results.append(result)
        dump = (cell / 'dump.txt').read_bytes()
        if len(dump) != plan['bytes'] or hashlib.sha256(dump).hexdigest() != plan['dump_raw_sha256']:
            raise ValueError('runner capture differs from staged stdout')
        return {'capture_and_verify_ok': True, 'dump_bytes': len(dump),
                'dump_raw_sha256': plan['dump_raw_sha256'],
                'runner_return_chars': [len(json.dumps(result)) for result in results],
                'configured_harness_limit_chars': limit, 'paid_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('target', type=Path)
    parser.add_argument('--out', type=Path, required=True, help='new private audit directory')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    audit = check(plan, args.target.resolve())
    args.out.mkdir(parents=True, exist_ok=False)
    with (args.out / 'audit.json').open('x', encoding='utf-8') as stream:
        json.dump(audit, stream, indent=2)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
