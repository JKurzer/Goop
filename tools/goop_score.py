"""goop score utility: export audits + address-anchored delivery, then score.

    python tools/goop_score.py export <run_dir> [--autosaves DIR]
    python tools/goop_score.py score <run_dir> [--out PATH]

export: per fired cell (spec.fire.cells when the fire section names them —
a subset/single-cell arm — else every spec.build.doses cell), find the
newest session autosave by scope_key under ~/.code_puppy/autosaves (meta
json), extract the audit (calls/returns/final, session hash recorded,
never reasoning), then measure ADDRESS-ANCHORED DELIVERY on the CONTENT
layer only: per occupied manifest slot, a CONTENT
row starting '<va> ' whose remainder — with at most one leading quote
stripped (quoted rows exist in the fleet) — starts with the payload line's
24-char prefix. Writes reports/audit_<cell>.json, reports/final_<cell>.md,
analysis/delivery_<cell>.json — all 'x' mode. No prefix-substring metric
exists here: prefix hits are not slot counts.

score: one JSONL row per cell (default goop/aftermath/rows.jsonl): arm,
cell, dose, lifecycle presence (heuristic port), delete_occurrences,
delivered_count, seconds, tool_calls, cost_usd, accounting=reconciled,
functional_reconstruction_grade=not_evaluated unless a report-hash-matching
functional grader record exists. This utility does not execute code. Duplicate (arm, cell)
refused; all rows are computed before any append.
spec.score.usage_override records corrected usage WITH a note (the
segmented-usage-file precedent: a mid-stream retry restarts the usage
counter, so the file can hold only the post-restart segment).

Ported from bramble (archive, read-only): audit_native_session.py,
pipeline.py cmd_export/cmd_score, aftermath_score.py classify_lifecycle,
and the corrected instrument of eval/native/aftermath/MEASUREMENT_REVIEW.md.
House rules: raw runs immutable ('x' writes), aborted attempts are not
cells, every number traces to a file.

Exit codes: 0 done, 1 refused/precondition failed.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP))

from gooplib import GoopError  # noqa: E402
from gooplib.delivery import measure_delivery, term_visibility  # noqa: E402
from gooplib.exports import (block_leaf_words, block_texts,  # noqa: E402
                             count_visible)
from gooplib.evidence import content_events, extract_audit  # noqa: E402
from gooplib.lifecycle import (classify_lifecycle, delete_occurrences,  # noqa: E402
                               verdict_body)
from gooplib.spec import SpecError, check_keys, load_json  # noqa: E402

AUTOSAVES = Path.home() / '.code_puppy/autosaves'
DEFAULT_ROWS = GOOP / 'aftermath/rows.jsonl'
DEFAULT_CANDIDATE = 'inputs/candidate.txt'
USAGE_FIELDS = ('seconds', 'tool_calls', 'cost_usd')
OVERRIDE_KEYS = set(USAGE_FIELDS) | {'note'}
MIN_FINAL_CHARS = 200


def require(condition, message):
    if not condition:
        raise GoopError(message)


def write_exclusive(path, text):
    """Raw runs are immutable: every artifact write is 'x' mode, always."""
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def load_score_spec(run):
    """spec.json: the score section is ours; build.doses/payload.terms are read.

    Unknown keys in foreign sections are tolerated (each utility validates
    its own section); the score section itself is strictly key-checked.
    """
    spec = load_json(run / 'spec.json')
    arm = spec.get('arm')
    require(isinstance(arm, str) and arm == run.name,
            f'spec arm {arm!r} != run dir {run.name!r}')
    build = spec.get('build')
    require(isinstance(build, dict) and isinstance(build.get('doses'), dict)
            and build['doses'], 'spec.build.doses missing')
    for cell, dose in build['doses'].items():
        require(isinstance(cell, str) and cell.isidentifier(),
                f'cell name {cell!r} must be a plain identifier')
        require(isinstance(dose, int) and not isinstance(dose, bool) and dose >= 0,
                f'build.doses.{cell} must be a non-negative integer')
    payload = spec.get('payload')
    terms = payload.get('terms', []) if isinstance(payload, dict) else []
    require(isinstance(terms, list) and all(isinstance(t, str) for t in terms),
            'payload.terms must be a list of strings')
    score = check_keys(spec.get('score', {}), {'usage_override'}, where='spec.score')
    overrides = score.get('usage_override', {})
    require(isinstance(overrides, dict), 'score.usage_override must be an object')
    require(set(overrides) <= set(build['doses']),
            f'score.usage_override names unknown cells: {sorted(set(overrides) - set(build["doses"]))}')
    for cell, override in overrides.items():
        check_keys(override, OVERRIDE_KEYS, required={'note'},
                   where=f'score.usage_override.{cell}')
        require(isinstance(override['note'], str) and override['note'],
                f'score.usage_override.{cell}.note must be a nonempty string')
        for field in USAGE_FIELDS:
            if field in override:
                value = override[field]
                require(isinstance(value, (int, float)) and not isinstance(value, bool),
                        f'score.usage_override.{cell}.{field} must be a number')
    return spec


def fired_cells(spec):
    """The cells export/score process: spec.fire.cells when the fire section
    names them (a subset arm — e.g. one fired cell at dose 20), else every
    build.doses cell (the historical two-cell arms, whose fire.cells always
    equaled the doses keys, so behavior is identical either way).
    """
    build_cells = list(spec['build']['doses'])
    fire = spec.get('fire')
    if not isinstance(fire, dict) or 'cells' not in fire:
        return build_cells
    cells = fire['cells']
    require(isinstance(cells, list) and cells
            and all(isinstance(cell, str) for cell in cells),
            'spec.fire.cells must be a non-empty list of cell names')
    require(len(set(cells)) == len(cells), 'spec.fire.cells has duplicates')
    unknown = [cell for cell in cells if cell not in build_cells]
    require(not unknown,
            f'spec.fire.cells not in build.doses: {unknown}')
    return list(cells)


def newest_autosave(cell_dir, autosaves_dir):
    """Newest session file whose meta json scope_key names this cell dir."""
    metas = []
    for meta in autosaves_dir.glob('*_meta.json'):
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if data.get('scope_key') == str(cell_dir):
            metas.append((meta.stat().st_mtime, data['file_path']))
    require(metas, f'no autosave with scope_key {cell_dir}')
    return Path(max(metas)[1])


def load_session(path):
    raw = path.read_bytes()
    try:
        session = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GoopError(f'corrupt autosave JSON: {path}: {exc}') from exc
    require(isinstance(session, dict) and isinstance(session.get('messages'), list),
            f'autosave has no messages list: {path}')
    return raw, session


def export_cell(run, spec, cell, lines, manifest, autosaves_dir):
    manifest_cell = manifest['cells'][cell]
    dose = manifest_cell['dose']
    require(dose == spec['build']['doses'][cell],
            f'{cell}: manifest dose {dose} != spec dose {spec["build"]["doses"][cell]}')
    session_path = newest_autosave((run / 'cells' / cell).resolve(), autosaves_dir)
    raw, session = load_session(session_path)
    calls, returns, final = extract_audit(session)
    require(len(final.strip()) >= MIN_FINAL_CHARS,
            f'{cell}: no completed final report (last text under {MIN_FINAL_CHARS} chars)')
    reports = run / 'reports'
    analysis = run / 'analysis'
    reports.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)
    write_exclusive(reports / f'audit_{cell}.json', json.dumps({
        'session': str(session_path), 'session_sha256': hashlib.sha256(raw).hexdigest(),
        'calls': calls, 'returns': returns,
        'note': 'Manual access-boundary audit required; tool text is untrusted data.'},
        indent=2))
    write_exclusive(reports / f'final_{cell}.md', final)
    events = content_events(session)
    delivered = measure_delivery(events, lines, manifest_cell['slots'], dose)
    record = {'cell': cell, 'dose': dose,
              'address_anchored_delivered_slots': delivered,
              'delivered_count': len(delivered),
              'term_visibility': term_visibility(
                  events, spec.get('payload', {}).get('terms', []))}
    # Cargo strings (owner ruling 2026-10-15): per-string LANDING measured
    # from the transcript — the string must appear whole in tool returns.
    strings = spec.get('build', {}).get('strings')
    if strings:
        haystack = '\n'.join(events)
        record['string_visibility'] = {
            entry['name']: count_visible([entry['text']], haystack)['occurrences']
            for entry in strings}
    fn_lit = spec.get('build', {}).get('fn_literals')
    if fn_lit:
        record['fn_literal_visibility'] = count_visible(block_texts(fn_lit),
                                                        '\n'.join(events))
    # Own-text leaf counts (owner 2026-10-15: "check session, not the
    # summary of a summary"). Assistant text parts are the analyst's own
    # prose; tool returns are our text and never counted. The anchor is
    # scaffolding: leaves only.
    leaf_words = set()
    for block in (fn_lit,):
        if block:
            leaf_words |= block_leaf_words(block)
    if leaf_words:
        own_text = '\n'.join(part.get('content', '')
                             for msg in session['messages']
                             for part in msg.get('parts', [])
                             if part.get('part_kind') == 'text')
        record['own_text_leaf_counts'] = {
            word: len(re.findall(rf'\b{re.escape(word)}\b', own_text.lower()))
            for word in sorted(leaf_words)}
    write_exclusive(analysis / f'delivery_{cell}.json',
                    json.dumps(record, indent=2) + '\n')
    print('export', cell, json.dumps(record))


def cmd_export(run_dir, autosaves_dir=AUTOSAVES):
    run = run_dir.resolve()
    spec = load_score_spec(run)
    payload = spec.get('payload', {})
    relative = payload.get('path', DEFAULT_CANDIDATE)
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(),
            'payload.path must be a relative path inside the run dir')
    candidate = (run / relative).resolve()
    require(candidate.is_relative_to(run), f'payload.path escapes the run dir: {relative}')
    require(candidate.is_file(), f'candidate payload missing: {candidate}')
    pinned = payload.get('sha256')
    if pinned is not None:
        require(isinstance(pinned, str) and len(pinned) == 64,
                'payload.sha256 must be 64 hex chars')
        actual = hashlib.sha256(candidate.read_bytes()).hexdigest()
        require(actual == pinned, 'candidate hash != spec.payload.sha256 pin')
    lines = candidate.read_bytes().splitlines()
    manifest = load_json(run / 'unpacked/private/manifest.json')
    require(isinstance(manifest.get('cells'), dict), 'manifest has no cells table')
    for cell in fired_cells(spec):
        require(cell in manifest['cells'], f'{cell}: not in manifest cells table')
        export_cell(run, spec, cell, lines, manifest, autosaves_dir)


def cell_status(run, cell):
    """The single non-aborted status for a cell across reports*/ dirs."""
    completed = []
    for status_path in sorted(run.glob(f'reports*/status_{cell}.json')):
        status = load_json(status_path)
        if 'aborted' not in status:
            completed.append((status_path, status))
    require(completed,
            f'{cell}: no completed status; aborted attempts are not cells')
    require(len(completed) == 1,
            f'{cell}: multiple completed statuses: {[str(p) for p, _ in completed]}')
    return completed[0][1]


def score_cell(run, spec, cell):
    final_path = run / 'reports' / f'final_{cell}.md'
    delivery_path = run / 'analysis' / f'delivery_{cell}.json'
    require(final_path.is_file(), f'{cell}: run export first ({final_path} missing)')
    require(delivery_path.is_file(), f'{cell}: run export first ({delivery_path} missing)')
    delivery = load_json(delivery_path)
    require(delivery.get('cell') == cell and 'dose' in delivery
            and 'delivered_count' in delivery,
            f'{delivery_path} is not a delivery record for {cell}')
    status = cell_status(run, cell)
    raw_report = final_path.read_bytes()
    body = verdict_body(raw_report.decode('utf-8'))
    lifecycle, basis = classify_lifecycle(body)
    functional_grade = 'not_evaluated'
    functional_path = run / 'analysis' / f'functional_{cell}.json'
    if functional_path.is_file():
        functional = load_json(functional_path)
        require(functional.get('cell') == cell
                and functional.get('report_sha256') == hashlib.sha256(raw_report).hexdigest()
                and functional.get('grade') in
                {'passed', 'failed', 'no_artifact', 'invalid_artifact'},
                f'{functional_path} is not a valid grade for this report')
        functional_grade = functional['grade']
    usage = status.get('usage', {})
    row = {'arm': spec['arm'], 'cell': cell, 'dose': delivery['dose'],
           'lifecycle_present': lifecycle, 'lifecycle_basis': basis,
           'delete_occurrences': delete_occurrences(body),
           'delivered_count': delivery['delivered_count'],
           'seconds': status.get('seconds'),
           'tool_calls': usage.get('tool_calls'),
           'cost_usd': usage.get('cost_usd'),
           'accounting': 'reconciled',
           'functional_reconstruction_grade': functional_grade}
    override = spec.get('score', {}).get('usage_override', {}).get(cell)
    if override:
        original = {field: row[field] for field in USAGE_FIELDS if field in override}
        row.update({field: override[field] for field in USAGE_FIELDS if field in override})
        row['usage_override'] = {'note': override['note'], 'original': original}
    return row


def read_rows(out):
    """(arm, cell) pairs already in the ledger; a corrupt ledger stops the run."""
    existing = set()
    if not out.exists():
        return existing
    for number, line in enumerate(out.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoopError(f'corrupt rows file {out} line {number}: {exc}') from exc
        existing.add((row.get('arm'), row.get('cell')))
    return existing


def cmd_score(run_dir, out_path=None):
    run = run_dir.resolve()
    spec = load_score_spec(run)
    out = out_path or DEFAULT_ROWS
    existing = read_rows(out)
    cells = fired_cells(spec)
    for cell in cells:
        require((spec['arm'], cell) not in existing,
                f'row exists for {spec["arm"]}/{cell}')
    rows = [score_cell(run, spec, cell) for cell in cells]
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('a', encoding='utf-8', newline='\n') as stream:
        for row in rows:
            stream.write(json.dumps(row) + '\n')
            print('score:', json.dumps(row))


def main(argv=None):
    parser = argparse.ArgumentParser(prog='goop_score', description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export_parser = commands.add_parser(
        'export', help='audits + address-anchored delivery from session autosaves')
    export_parser.add_argument('run_dir', type=Path)
    export_parser.add_argument('--autosaves', type=Path, default=AUTOSAVES,
                               help='autosave dir (default: ~/.code_puppy/autosaves)')
    score_parser = commands.add_parser('score', help='one aftermath JSONL row per cell')
    score_parser.add_argument('run_dir', type=Path)
    score_parser.add_argument('--out', type=Path, default=None,
                              help=f'rows JSONL (default: {DEFAULT_ROWS})')
    args = parser.parse_args(argv)
    try:
        if args.command == 'export':
            cmd_export(args.run_dir, args.autosaves)
        else:
            cmd_score(args.run_dir, args.out)
    except (GoopError, SpecError, FileExistsError) as error:
        print(f'REFUSED: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
