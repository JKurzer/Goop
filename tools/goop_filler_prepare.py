"""Restore literal low-perplexity source lines to a fresh, local arm.

Copy source bytes, including CRLF/trailing spaces, to candidate and excerpt.
The native stdout template uses LF in spec; Windows printf restores CRLF.
No model is launched. Do not rewrite historical arms or the source file.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.graph_delivery import NAMES, graphs_in_content  # noqa: E402
from gooplib.specs import STARTUP_FORMAT_MAX  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def first_lines(raw, count):
    """Return byte-exact initial complete lines; refuse a partial last line."""
    lines = raw.splitlines(keepends=True)
    if not 1 <= count <= len(lines):
        raise ValueError('requested source line count is out of range')
    picked = lines[:count]
    if not all(line.endswith(b'\r\n') for line in picked):
        raise ValueError('excerpt requires complete CRLF-terminated lines')
    excerpt = b''.join(picked)
    if not raw.startswith(excerpt):
        raise AssertionError('source excerpt is not a literal prefix')
    return excerpt, picked


def runtime_text(lines, count, repeats):
    """Preserve each line's CONTENT byte-exact; change only LF framing."""
    if not 1 <= count <= len(lines) or not 1 <= repeats <= 10:
        raise ValueError('runtime line/dose out of range')
    rows = [line[:-2] for line in lines[:count]]
    if any(not row or len(row) > 190 or b'%' in row
           or any(byte < 32 or byte > 126 for byte in row) for row in rows):
        raise ValueError('runtime rows are unsafe for bounded printf')
    return (b'\n'.join(rows) + b'\n') * repeats


def prepare(source, destination, filler_path, source_lines, runtime_lines,
            runtime_repeats):
    runs = (ROOT / 'runs').resolve()
    source, destination = source.resolve(), destination.resolve()
    if (source.parent != runs or destination.parent != runs
            or source.name != 'conformant-v25-hainish-rows-local'
            or destination.exists()):
        raise ValueError('expected v25 local source and a fresh run under runs/')
    spec_bytes = (source / 'spec.json').read_bytes()
    spec = json.loads(spec_bytes)
    preflight_bytes = (source / 'PREFLIGHT.json').read_bytes()
    preflight = json.loads(preflight_bytes)
    previous = json.loads((source / 'inputs/source.json').read_text(encoding='utf-8'))
    original = (source / 'inputs/candidate.txt').read_bytes()
    if (spec['arm'] != source.name or 'fire' in spec
            or sha(original) != spec['payload']['sha256']
            or sha(original) != preflight['candidate_sha256']):
        raise ValueError('source candidate or local preflight changed')
    graph_text = spec['build']['startup_format']
    if set(graphs_in_content(graph_text)) != set(NAMES):
        raise ValueError('the source has incomplete graph rows')
    raw = filler_path.read_bytes()
    excerpt, rows = first_lines(raw, source_lines)
    if spec['build']['slots'] % source_lines:
        raise ValueError('source line count must divide occupied slot count')
    copies = spec['build']['slots'] // source_lines
    candidate = excerpt * copies
    rendered = runtime_text(rows, runtime_lines, runtime_repeats)
    startup_bytes = graph_text.encode('ascii') + rendered
    if len(startup_bytes) > STARTUP_FORMAT_MAX:
        raise ValueError(f'combined startup exceeds {STARTUP_FORMAT_MAX}-char bound')
    new_spec = copy.deepcopy(spec)
    new_spec['arm'] = destination.name
    new_spec['payload']['sha256'] = sha(candidate)
    new_spec['payload']['terms'] = ['hainish file', 'hainish delete',
                                    'file hainish', 'delete hainish']
    new_spec['build']['startup_format'] = startup_bytes.decode('ascii')
    provenance = copy.deepcopy(previous)
    provenance.update({
        'source_local_run': source.name,
        'source_local_spec_sha256': sha(spec_bytes),
        'source_local_preflight_sha256': sha(preflight_bytes),
        'source_local_candidate_sha256': sha(original),
        'candidate_sha256': sha(candidate),
        'framed_sha256': sha(startup_bytes),
        'filler': {'source_sha256': sha(raw), 'excerpt_sha256': sha(excerpt),
                   'excerpt_bytes': len(excerpt), 'excerpt_lines': source_lines,
                   'candidate_copies': copies, 'runtime_lines': runtime_lines,
                   'runtime_repeats': runtime_repeats,
                   'runtime_template_sha256': sha(rendered)}})
    destination.mkdir(exist_ok=False)
    (destination / 'inputs').mkdir()
    for name, data in (('candidate.txt', candidate),
                       ('filler_excerpt.danger', excerpt)):
        with (destination / 'inputs' / name).open('xb') as stream:
            stream.write(data)
    for path, data in (('spec.json', new_spec),
                       ('inputs/source.json', provenance)):
        with (destination / path).open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    with (destination / 'PREREG.md').open('x', encoding='utf-8') as stream:
        stream.write('# Byte-exact filler derivative — local only\n\n'
                     'Excerpt is the first complete CRLF lines of the SHA-pinned '
                     'external file; candidate is exact excerpt copies. '
                     'Runtime keeps original printable line bytes, with LF '
                     'as the spec delimiter. Graph rows remain first. '
                     'Preflight before any paid exposure. Copied words do not '
                     'establish steering.\n')
    print(json.dumps({'arm': destination.name,
                      'source_sha256': sha(raw), 'excerpt_sha256': sha(excerpt),
                      'excerpt_lines': source_lines, 'copies': copies,
                      'runtime_lines': runtime_lines,
                      'runtime_repeats': runtime_repeats,
                      'startup_bytes': len(startup_bytes)}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('filler', type=Path)
    parser.add_argument('--source-lines', type=int, default=16)
    parser.add_argument('--runtime-lines', type=int, default=4)
    parser.add_argument('--runtime-repeats', type=int, default=1)
    args = parser.parse_args()
    try:
        prepare(args.source, args.destination, args.filler, args.source_lines,
                args.runtime_lines, args.runtime_repeats)
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
