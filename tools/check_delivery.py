"""Exercise planned chunks through installed Code Puppy output limits, offline."""
import argparse
import json
from pathlib import Path

from prepare_delivery import verify_returns


def main():
    from code_puppy.config import get_tool_output_limit_chars
    from code_puppy.tools.command_runner import _run_command_sync
    from code_puppy_core_plugins.spill.register_callbacks import _spill_result

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('cell', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding='utf-8'))
    args.out.mkdir(parents=True, exist_ok=False)
    results = []
    threshold = get_tool_output_limit_chars()
    for index, chunk in enumerate(plan['chunks'], 1):
        result = _run_command_sync(chunk['command'], str(args.cell.resolve()), 45,
                                   'goop-bounded-delivery', silent=True).model_dump()
        before = json.dumps(result)
        with (args.out / f'return-{index:02}.json').open('x', encoding='utf-8') as stream:
            stream.write(before)
        if threshold > 0 and len(before) > threshold:
            raise ValueError(f'chunk {index} would spill under configured harness limit {threshold}')
        _spill_result('shell', result, session_id='goop-bounded-delivery')
        if json.dumps(result) != before:
            raise ValueError(f'chunk {index} changed under the installed spill plugin')
        results.append(result)
    audit = verify_returns(plan, results)
    audit['configured_harness_limit_chars'] = threshold
    audit['spill_plugin_left_results_unchanged'] = True
    audit['paid_calls'] = 0
    with (args.out / 'audit.json').open('x', encoding='utf-8') as stream:
        json.dump(audit, stream, indent=2)
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
