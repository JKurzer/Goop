"""goop fire utility: run cells via code-puppy with a prompt FILE.

    python tools/goop_fire.py fire <run_dir> [--cells k7|m2]

spec.json fire section: {prompt_file, model, cells, per_cell_budget_usd}.
prompt_file names a file under goop/prompts/ keeping {cell}/{python} placeholders.

Ported from bramble (archive, read-only): run_native_pair.py's fire loop and
winreg credential pattern; pipeline.py cmd_fire's DEATH_MARKERS, log_tool_calls
reconciliation, and ATTEMPT stub. House rules: provider aborts are not cells,
usage segments are not costs, completed cells never re-run, every write is 'x'.

Exit codes: 0 all requested cells fired, 1 refused/precondition failed,
2 provider abort or accounting mismatch, 3 per-cell budget stop.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import winreg
except ImportError:  # live fires are Windows-only; tests import everywhere
    winreg = None

GOOP = Path(__file__).resolve().parents[1]
PROMPTS_DIR = GOOP / 'prompts'
FIRE_KEYS = {'prompt_file', 'model', 'cells', 'per_cell_budget_usd'}
REQUIRED_FIRE_KEYS = {'prompt_file', 'model', 'cells'}
DEATH_MARKERS = ('no credits remaining', 'Request timed out',
                 'An error occurred while processing the request')
TOOL_MARKERS = ('shell', 'list_files', 'read_file', 'grep', 'read_tool_result',
                'create_file', 'replace_in_file', 'delete_file', 'ask_user_question')
EXIT_REFUSED = 1
EXIT_ABORT = 2
EXIT_BUDGET = 3


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def write_exclusive(path, text):
    """Raw runs are immutable: every artifact write is 'x' mode, always."""
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def load_fire_spec(run):
    """Self-contained fire-section loader (gooplib is another utility's job)."""
    spec_path = run / 'spec.json'
    require(spec_path.is_file(), f'spec.json missing in {run}')
    spec = json.loads(spec_path.read_text(encoding='utf-8'))
    fire = spec.get('fire')
    require(isinstance(fire, dict), 'spec.json has no fire section')
    unknown = set(fire) - FIRE_KEYS
    require(not unknown, f'spec.json fire unknown keys: {sorted(unknown)}')
    missing = REQUIRED_FIRE_KEYS - set(fire)
    require(not missing, f'spec.json fire missing keys: {sorted(missing)}')
    cells = fire['cells']
    require(isinstance(cells, list) and cells and
            all(isinstance(cell, str) for cell in cells),
            'fire.cells must be a non-empty list of cell names')
    require(len(set(cells)) == len(cells), 'fire.cells has duplicates')
    budget = fire.get('per_cell_budget_usd')
    require(budget is None or isinstance(budget, (int, float)),
            'fire.per_cell_budget_usd must be a number')
    return fire


def load_prompt(prompt_file):
    """Prompts are FILES under goop/prompts/; {cell}/{python} survive verbatim."""
    require(isinstance(prompt_file, str) and prompt_file,
            'fire.prompt_file must be a filename')
    require(not Path(prompt_file).is_absolute(),
            'prompt_file must be relative to goop/prompts/')
    path = (PROMPTS_DIR / prompt_file).resolve()
    require(path.is_relative_to(PROMPTS_DIR.resolve()),
            f'prompt_file escapes goop/prompts/: {prompt_file}')
    require(path.is_file(), f'prompt file missing: {path}')
    return path.read_text(encoding='utf-8')


def render_prompt(template, cell_dir):
    """{python} is the interpreter running this utility: traceable, not magic."""
    return template.format(cell=cell_dir, python=sys.executable)


def log_tool_calls(raw_log_text):
    """Byte-exact port of bramble pipeline.log_tool_calls (Thinking excluded)."""
    count = 0
    for line in raw_log_text.split('\n'):
        stripped = line.lstrip('\x1b[0-9;:m ').strip()
        if stripped.startswith('● ') and stripped[2:].split(' ', 1)[0] in TOOL_MARKERS:
            count += 1
    return count


def death_marker(raw_log_text):
    return next((marker for marker in DEATH_MARKERS if marker in raw_log_text), None)


def assess_cell(cell, returncode, seconds, raw, usage):
    """Pure verdict for one fired cell. usage=None means the file never landed."""
    aborted = []
    if returncode:
        aborted.append(f'exit={returncode}')
    marker = death_marker(raw)
    if marker:
        aborted.append(f'provider-death: {marker}')
    if usage is None:
        aborted.append('usage-file missing')
    status = {'cell': cell, 'exit': returncode, 'seconds': seconds}
    if usage is not None:
        status['usage'] = usage
        observed = log_tool_calls(raw)
        status['log_tool_calls'] = observed
        if observed and abs(observed - usage.get('tool_calls', -1)) > 1:
            aborted.append(f'usage reconciliation: file says {usage.get("tool_calls")} '
                           f'calls, log shows {observed}')
    if aborted:
        status['aborted'] = aborted
    return status, aborted


def completed_cells(run):
    """Cells with a non-aborted status in ANY reports* dir: never re-run."""
    done = set()
    for status_path in run.glob('reports*/status_*.json'):
        status = json.loads(status_path.read_text(encoding='utf-8'))
        if 'aborted' not in status:
            done.add(status.get('cell', status_path.stem.removeprefix('status_')))
    return done


def attempt_stub_path(run, cell):
    """ATTEMPT_<CELL>_ABORTED.md; a re-abort serializes (_2, _3) instead of crashing."""
    base = f'ATTEMPT_{cell.upper()}_ABORTED'
    candidate = run / f'{base}.md'
    serial = 2
    while candidate.exists():
        candidate = run / f'{base}_{serial}.md'
        serial += 1
    return candidate


def parse_cells(argument, available):
    """--cells k7|m2 (comma subset). A subset fires into fresh reports-<cells>."""
    if argument is None:
        return list(available), 'reports'
    cells = argument.split(',')
    require(all(cell in available for cell in cells),
            f'--cells must be a subset of spec.fire.cells {available}')
    require(len(set(cells)) == len(cells), '--cells has duplicates')
    return cells, 'reports-' + '-'.join(cells)


def load_environment():
    """winreg credential pattern, ported byte-faithful from run_native_pair."""
    env = os.environ.copy()
    credential = ''
    if winreg is not None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
            try:
                credential, _ = winreg.QueryValueEx(key, 'OPENAI_API_KEY')
            except FileNotFoundError:
                credential = env.get('OPENAI_API_KEY', '')
    else:
        credential = env.get('OPENAI_API_KEY', '')
    require(credential, 'OPENAI_API_KEY unavailable; no cell launched')
    env.update(OPENAI_API_KEY=credential, NO_COLOR='1', PYTHONIOENCODING='utf-8')
    return env


def fire_cells(run, fire, cells, output_name, *, executable, env, run_fn=subprocess.run):
    """The fire loop. run_fn is injectable so tests never touch a provider."""
    for cell in cells:
        cell_dir = run / 'cells' / cell
        require((cell_dir / 'pe_inspect.py').is_file(),
                f'{cell}: requires current helper staging; do not mutate an old cell')
        require((cell_dir / 'target.exe').is_file(),
                f'{cell}: target.exe missing; build the pair first')
    blocked = [cell for cell in cells if cell in completed_cells(run)]
    require(not blocked, f'completed cells never re-run: {blocked}')
    output = run / output_name
    require(not output.exists(),
            f'{output_name}/ exists; re-fire a subset with --cells into a fresh dir')
    output.mkdir(exist_ok=False)
    template = load_prompt(fire['prompt_file'])
    budget = fire.get('per_cell_budget_usd')
    for cell in cells:
        cell_dir = run / 'cells' / cell
        prompt = render_prompt(template, cell_dir)
        write_exclusive(output / f'prompt_{cell}.txt', prompt)
        usage_path = output / f'usage_{cell}.json'
        started = time.monotonic()
        print(f'START {cell}', flush=True)
        with (output / f'raw_{cell}.log').open('xb') as log:
            completed = run_fn([executable, '-p', prompt, '-m', fire['model'],
                                '--usage-file', str(usage_path),
                                '--disable-ask-user-question'],
                               cwd=cell_dir, env=env, stdout=log,
                               stderr=subprocess.STDOUT)
        seconds = round(time.monotonic() - started, 2)
        raw = (output / f'raw_{cell}.log').read_text(encoding='utf-8', errors='replace')
        usage = (json.loads(usage_path.read_text(encoding='utf-8'))
                 if usage_path.exists() else None)
        status, aborted = assess_cell(cell, completed.returncode, seconds, raw, usage)
        write_exclusive(output / f'status_{cell}.json', json.dumps(status, indent=2))
        print(json.dumps(status), flush=True)
        if aborted:
            write_exclusive(attempt_stub_path(run, cell),
                            '# Aborted attempt — not a cell\n\n' +
                            '\n'.join(f'- {item}' for item in aborted) +
                            f'\n\nseconds={seconds}; raw log preserved at '
                            f'{output_name}/raw_{cell}.log\n')
            print('STOP: provider-side abort or accounting mismatch; '
                  'not counted as a cell.', flush=True)
            return EXIT_ABORT
        cost = usage.get('cost_usd')
        if budget is not None and (cost is None or cost > budget):
            print('STOP: per-cell budget exceeded (or cost missing from usage file).',
                  flush=True)
            return EXIT_BUDGET
    return 0


def cmd_fire(run_dir, cells_argument):
    run = run_dir.resolve()
    fire = load_fire_spec(run)
    cells, output_name = parse_cells(cells_argument, fire['cells'])
    executable = shutil.which('code-puppy')
    require(executable, 'code-puppy not found on PATH')
    return fire_cells(run, fire, cells, output_name,
                      executable=executable, env=load_environment())


def main(argv=None):
    parser = argparse.ArgumentParser(prog='goop_fire', description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    fire_parser = commands.add_parser('fire', help='fire spec.fire.cells via code-puppy')
    fire_parser.add_argument('run_dir', type=Path,
                             help='run dir holding spec.json and cells/')
    fire_parser.add_argument('--cells', default=None,
                             help='comma subset of spec.fire.cells (e.g. m2); re-fires an '
                                  'aborted cell into a fresh reports-<cells> dir')
    args = parser.parse_args(argv)
    try:
        if args.command == 'fire':
            return cmd_fire(args.run_dir, args.cells)
    except RuntimeError as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        return EXIT_REFUSED
    return 0


if __name__ == '__main__':
    sys.exit(main())
