"""Audit literal filler delivery in saved analyst CONTENT, never call args.

Separate byte-exact CRLF runtime exposure from LF-normalized textual
exposure. Neither implies steering or predictive accuracy.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.evidence import content_events  # noqa: E402
from gooplib.graph_delivery import frame_graphs, graphs_in_content  # noqa: E402
from tools.goop_filler_prepare import runtime_text  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def audit(run):
    run = run.resolve()
    paid_info = json.loads((run / 'inputs/source.json').read_text(encoding='utf-8'))
    local = run.parent / paid_info['source_run']
    spec_bytes = (local / 'spec.json').read_bytes()
    spec = json.loads(spec_bytes)
    info = json.loads((local / 'inputs/source.json').read_text(encoding='utf-8'))
    filler = info['filler']
    excerpt = (local / 'inputs/filler_excerpt.danger').read_bytes()
    candidate = (local / 'inputs/candidate.txt').read_bytes()
    if (sha(spec_bytes) != paid_info['source_spec_sha256']
            or sha(excerpt) != filler['excerpt_sha256']
            or sha(candidate) != info['candidate_sha256']
            or candidate != excerpt * filler['candidate_copies']):
        raise ValueError('local excerpt, candidate or spec changed')
    paid_spec = json.loads((run / 'spec.json').read_text(encoding='utf-8'))
    startup = spec['build']['startup_format']
    graph_prefix = frame_graphs(graphs_in_content(startup))
    if (not startup.startswith(graph_prefix)
            or startup != paid_spec['build']['startup_format']
            or sha(startup.encode('ascii')) != info['framed_sha256']):
        raise ValueError('startup graph-first proof changed')
    rendered = runtime_text(excerpt.splitlines(keepends=True),
                            filler['runtime_lines'], filler['runtime_repeats'])
    if (sha(rendered) != filler['runtime_template_sha256']
            or startup != graph_prefix + rendered.decode('ascii')):
        raise ValueError('runtime filler is not the exact excerpt text')
    status = json.loads((run / 'reports/status_RunB.json').read_text(encoding='utf-8'))
    if status.get('exit') != 0 or status.get('aborted'):
        raise ValueError('paid analyst did not finish cleanly')
    record = json.loads((run / 'reports/audit_RunB.json').read_text(encoding='utf-8'))
    saved = Path(record['session']).read_bytes()
    if sha(saved) != record['session_sha256']:
        raise ValueError('saved analyst session changed')
    events = content_events(json.loads(saved))
    literal_crlf = rendered.replace(b'\n', b'\r\n').decode('ascii')
    literal_lf = rendered.decode('ascii')
    exact = [i for i, event in enumerate(events) if literal_crlf in event]
    textual = [i for i, event in enumerate(events)
               if literal_lf in event.replace('\r\n', '\n')]
    result = {'arm': run.name, 'cell': 'RunB',
              'source_sha256': filler['source_sha256'],
              'excerpt_sha256': filler['excerpt_sha256'],
              'excerpt_lines': filler['excerpt_lines'],
              'candidate_copies': filler['candidate_copies'],
              'runtime_lines': filler['runtime_lines'],
              'runtime_repeats': filler['runtime_repeats'],
              'session_sha256': sha(saved),
              'exact_crlf_content_event_indices': exact,
              'newline_normalized_event_indices': textual,
              'paid_cost_usd': status['usage']['cost_usd'],
              'steering_graded': False}
    path = run / 'analysis/filler_delivery_RunB.json'
    with path.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: goop_filler_audit.py <fired-run>')
    try:
        print(json.dumps(audit(Path(sys.argv[1])), indent=2))
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
