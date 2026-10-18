"""Hash-pinned, reproducible *incidence* readout of saved paid reports.

python tools/goop_report_incidence.py [output.json]
Never calls Astra. Counts negated lexical mentions, not just endorsed claims.
Only the v33/v36 comparison holds prompt, candidate, and filler dose fixed.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.evidence import extract_audit  # noqa: E402
from gooplib.report_incidence import ANCHOR, LEAF_TERMS, incidence  # noqa: E402

NAMES = (
    'conformant-v23-graph-rows-fire1',
    'conformant-v24-graph-rows-fire2',
    'conformant-v26-hainish-rows-fire1',
    'conformant-v28-hainish-natural-control-fire1',
    'conformant-v29-hainish-filler-natural-fire1',
    'conformant-v32-hainish-observe-control-fire1',
    'conformant-v33-hainish-observe-low-fire1',
    'conformant-v34-hainish-observe-high-fire1',
    'conformant-v36-hainish-pair-graph-five-staged',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def one_sided_exact_one_each(control, treatment):
    """Conditional exact one-sided p, assuming exchangeable arms (not randomized)."""
    if not (control in (0, 1) and treatment in (0, 1)):
        raise ValueError('one observation per arm, incidence must be binary')
    if treatment < control:
        return 1.0
    return 0.5 if treatment != control else 1.0


def read_run(run):
    status = json.loads((run / 'reports/status_RunB.json').read_text(encoding='utf-8'))
    if status['exit'] != 0 or status.get('aborted'):
        raise ValueError(f'{run.name}: analyst did not complete')
    audit = json.loads((run / 'reports/audit_RunB.json').read_text(encoding='utf-8'))
    saved = Path(audit['session']).read_bytes()
    if sha(saved) != audit['session_sha256']:
        raise ValueError(f'{run.name}: saved session changed')
    _, _, final = extract_audit(json.loads(saved))
    report = (run / 'reports/final_RunB.md').read_text(encoding='utf-8')
    if final != report:
        raise ValueError(f'{run.name}: exported report differs from saved session')
    spec = json.loads((run / 'spec.json').read_text(encoding='utf-8'))
    graph_path = run / 'analysis/graph_delivery_RunB.json'
    graph_gate = (json.loads(graph_path.read_text(encoding='utf-8'))['framed_delivered']
                  if graph_path.is_file() else None)
    counts = incidence(report)
    for details in counts.values():
        hits = details.pop('hits')
        # Every position is recoverable; avoid copying a long code literal
        # into the derived table once for every occurrence.
        details['hit_line_numbers_csv'] = ','.join(str(hit['line']) for hit in hits)
        details['examples'] = hits[:2]
    return {
        'arm': run.name,
        'prompt_file': spec['fire']['prompt_file'],
        'report_sha256': sha(report.encode('utf-8')),
        'session_sha256': sha(saved),
        'graph_delivery_gate': graph_gate,
        'reported_cost_usd': status['usage']['cost_usd'],
        'incidence': counts,
    }


def summarize(runs_dir, names=NAMES):
    rows = [read_run(runs_dir / name) for name in names]
    matched = {name: next(row for row in rows if row['arm'].startswith(name))
               for name in ('conformant-v33-', 'conformant-v36-')}
    low = matched['conformant-v33-']['incidence']
    aligned = matched['conformant-v36-']['incidence']
    comparisons = {}
    for term in LEAF_TERMS:
        a = int(low[term]['prose_count'] > 0)
        b = int(aligned[term]['prose_count'] > 0)
        comparisons[term] = {
            'old_graph_low_filler_presence': a,
            'five_set_graph_low_filler_presence': b,
            'one_sided_exact_p_one_per_arm': one_sided_exact_one_each(a, b),
        }
    return {
        'metric': 'whole-word report incidence (including negated mentions); '
                  'not semantic substitution or causal proof',
        'matched_arm_comparison': 'v33 vs v36: prompt, candidate, four-line '
                                  'filler, old literals fixed; graph differs',
        'matched_leaf_outcomes': comparisons,
        'anchor_stealth_diagnostic': {
            'term': ANCHOR,
            'interpretation': 'anchor must not surface in prose; absence is '
                              'expected and is NEVER a failure of leaf steering',
            'v33_prose_count': low[ANCHOR]['prose_count'],
            'v36_prose_count': aligned[ANCHOR]['prose_count'],
        },
        'rows': rows,
        'archival_v9': 'prior reported delete terminology adoption 4/6 in '
                       'docs/wou-construction-doctrine.md; NOT pooled because '
                       'raw paid reports are not among the listed runs',
    }


if __name__ == '__main__':
    destination = (Path(sys.argv[1]) if len(sys.argv) == 2 else
                   ROOT / 'aftermath/report-leaf-incidence-v36.json')
    if len(sys.argv) > 2:
        raise SystemExit('usage: goop_report_incidence.py [fresh-output.json]')
    try:
        record = summarize(ROOT / 'runs')
        with destination.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, indent=2, ensure_ascii=False)
            stream.write('\n')
        print(json.dumps({'path': str(destination),
                          'arms': len(record['rows']),
                          'matched_leaf_outcomes': record['matched_leaf_outcomes'],
                          'anchor_stealth_diagnostic': record['anchor_stealth_diagnostic']},
                         indent=2))
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
