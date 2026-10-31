"""Stage the two-command dump.txt transport; never launch a model or change a target."""
import argparse
import hashlib
import json
from pathlib import Path


def plan_file_graft(stdout, python):
    """Bind one complete zero-tick capture to its on-disk SHA-256."""
    if any(char in str(python) for char in '\r\n"%'):
        raise ValueError('interpreter path cannot contain shell expansion or quotes')
    try:
        text = stdout.decode('ascii').replace('\r\n', '\n')
    except UnicodeDecodeError as error:
        raise ValueError('capture must be ASCII') from error
    rows = text.splitlines()
    if not text.endswith('\n') or not rows or not rows[-1].startswith('SUMMARY '):
        raise ValueError('capture needs a final SUMMARY and trailing newline')
    digest = hashlib.sha256(stdout).hexdigest()
    capture = ("import subprocess,pathlib; "
               "b=subprocess.check_output(['target.exe','0','0'],timeout=30); "
               "pathlib.Path('dump.txt').open('xb').write(b); print('captured',len(b))")
    verify = ("import hashlib,pathlib; b=pathlib.Path('dump.txt').read_bytes(); "
              f"assert hashlib.sha256(b).hexdigest()=='{digest}', 'dump.txt mismatch'; "
              "print('verified',len(b))")
    return {'mode': 'file-graft', 'version': 1, 'bytes': len(stdout),
            'rows': len(rows), 'dump_raw_sha256': digest,
            'instructed_calls': 2,
            'capture_command': f'"{python}" -c "{capture}"',
            'verify_command': f'"{python}" -c "{verify}"'}


def delivery_prompt(plan):
    return (
        'Before reporting, capture the complete target.exe 0 0 output in dump.txt.\n'
        'Run these two commands separately with cwd set to {cell}:\n'
        f'1. Capture:\n```bat\n{plan["capture_command"]}\n```\n'
        f'2. Verify the captured bytes:\n```bat\n{plan["verify_command"]}\n```\n'
        f'dump.txt contains {plan["rows"]} lines, including all repeated rows '
        'and the final SUMMARY. Read it completely using contiguous read_file '
        'start_line/num_lines pages before reporting. If a page is clipped, '
        'retry it with a smaller range. Do not silently skip rows.\n'
        'After verification, use other tick/seed values as needed for analysis.\n'
    )


def render_analyst_prompt(template, plan, *, total_calls=40):
    if template.count('{delivery}') != 1 or template.count('{tool_call_budget}') != 1:
        raise ValueError('prompt needs one delivery and one tool_call_budget placeholder')
    if type(total_calls) is not int or total_calls < plan['instructed_calls']:
        raise ValueError('total call budget must include the two capture calls')
    return (template.replace('{delivery}', delivery_prompt(plan))
            .replace('{tool_call_budget}', str(total_calls)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stdout', type=Path, help='complete raw zero-tick target stdout')
    parser.add_argument('--python', required=True, help='persistent analyst interpreter')
    parser.add_argument('--out', required=True, type=Path, help='new private staging directory')
    parser.add_argument('--template', type=Path, default=Path(__file__).resolve().parents[1]
                        / 'docs/ANALYST_PROMPT.md')
    parser.add_argument('--tool-call-budget', type=int, default=40)
    args = parser.parse_args()
    plan = plan_file_graft(args.stdout.read_bytes(), args.python)
    prompt = render_analyst_prompt(args.template.read_text(encoding='utf-8'), plan,
                                   total_calls=args.tool_call_budget)
    args.out.mkdir(parents=True, exist_ok=False)
    for name, content in (('file-graft-plan.json', json.dumps(plan, indent=2) + '\n'),
                          ('analyst-prompt.md', prompt)):
        with (args.out / name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
    print(f'file-graft: {plan["rows"]} rows, 2 instructed calls; no model launched')


if __name__ == '__main__':
    main()
