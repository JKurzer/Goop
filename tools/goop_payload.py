"""goop payload utility: compose a goop candidate from files, or freeze one.

Usage:
    python tools/goop_payload.py payload <run_dir>

Reads <run_dir>/spec.json, section "payload":

  compose: {"spec_file": "specs/payload_x.json", "output": "payload/candidate.txt"}
  freeze:  {"candidate_file": "path/to.txt", "sha256": "<hex pin>",
            "output": "payload/candidate.txt"}

Exactly one of spec_file / candidate_file. Input paths resolve against the
goop repo root; `output` resolves against run_dir. Writes are exclusive
('x' mode): existing bytes are never overwritten. A small manifest lands
next to the output. All construction inputs come from files — the payload
spec JSON, the vocab JSON it references, and the corpus text. Nothing is
hardcoded here but machinery.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gooplib import payload as pl
from gooplib.spec import SpecError, check_keys, load_json, resolve_path

ROOT = Path(__file__).resolve().parents[1]

PAYLOAD_SECTION_KEYS = {'spec_file', 'candidate_file', 'sha256', 'output'}
SPEC_KEYS = {'name', 'hub', 'vocab_file', 'vocab', 'filter_terms',
             'incorrect_terms', 'trigram_sets', 'common_words_file',
             'corpus_file', 'lines', 'max_line_bytes',
             'seed', 'visibility', 'graft'}
SPEC_REQUIRED = {'name', 'hub', 'vocab_file', 'vocab', 'corpus_file',
                 'lines', 'max_line_bytes', 'seed'}
VISIBILITY_KEYS = {'prefix_chars', 'require_hub_in_prefix', 'require_filter_in_prefix'}
GRAFT_KEYS = {'bridges_visible_in_prefix', 'visible_line_range'}
TERM_KEYS = {'term', 'neighbors'}
TRIGRAM_SET_KEYS = {'a', 'b', 'c', 'occurrences', 'visible_occurrences'}
TRIGRAM_SET_REQUIRED = {'a', 'b', 'c', 'occurrences'}
COMMON_WORDS_FILE_KEYS = {'provenance', 'words'}
VOCAB_FILE_KEYS = {'vocab', 'corpus_words', 'identity_words',
                   'hub_marker', 'rotation_markers'}

# Owner rule (2026-10-13): each trigram set's edge forms appear 4-10 times;
# b is always a rare word (see _rarity_gate), task-relevance optional.
TRIGRAM_MIN_OCCURRENCES = 4
TRIGRAM_MAX_OCCURRENCES = 10
DEFAULT_COMMON_WORDS_FILE = 'payloads/common_words.json'


# --- typed validation ------------------------------------------------------

def _list_of_str(value, where):
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SpecError(f'{where} must be a list of strings')
    return list(value)


def _int(value, where, minimum=1):
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise SpecError(f'{where} must be an integer >= {minimum}')
    return value


def _bool(value, where):
    if not isinstance(value, bool):
        raise SpecError(f'{where} must be a boolean')
    return value


def _visibility(raw):
    if raw is None:
        return None
    check_keys(raw, VISIBILITY_KEYS, VISIBILITY_KEYS, where='visibility')
    return {
        'prefix_chars': _int(raw['prefix_chars'], 'visibility.prefix_chars'),
        'require_hub_in_prefix': _bool(raw['require_hub_in_prefix'],
                                       'visibility.require_hub_in_prefix'),
        'require_filter_in_prefix': _bool(raw['require_filter_in_prefix'],
                                          'visibility.require_filter_in_prefix'),
    }


def _graft(raw):
    if raw is None:
        return None
    check_keys(raw, GRAFT_KEYS, GRAFT_KEYS, where='graft')
    window = raw['visible_line_range']
    if (not isinstance(window, list) or len(window) != 2
            or not all(isinstance(v, int) and not isinstance(v, bool) and v >= 0
                       for v in window)):
        raise SpecError('graft.visible_line_range must be [start, end] integers >= 0')
    return {'bridges_visible_in_prefix': _bool(raw['bridges_visible_in_prefix'],
                                               'graft.bridges_visible_in_prefix'),
            'visible_line_range': list(window)}


def _terms(raw):
    out = []
    for i, entry in enumerate(raw or []):
        where = f'incorrect_terms[{i}]'
        check_keys(entry, TERM_KEYS, TERM_KEYS, where=where)
        if not entry['term'] or not entry['term'].islower():
            raise SpecError(f'{where}.term must be a nonempty lowercase string')
        out.append({'term': entry['term'],
                    'neighbors': _list_of_str(entry['neighbors'], f'{where}.neighbors')})
    return out


def _trigram_word(value, where):
    """A word the edge regex ([a-z]+) can measure exactly."""
    if (not isinstance(value, str) or not value.isascii()
            or not value.isalpha() or not value.islower()):
        raise SpecError(f'{where} must be a single lowercase ascii word')
    return value


def _occurrences(value, where):
    bounds = f'[{TRIGRAM_MIN_OCCURRENCES}, {TRIGRAM_MAX_OCCURRENCES}]'
    if isinstance(value, int) and not isinstance(value, bool):
        low = high = value
    elif (isinstance(value, list) and len(value) == 2 and all(
            isinstance(v, int) and not isinstance(v, bool) for v in value)):
        low, high = value
    else:
        raise SpecError(f'{where}.occurrences must be an integer in {bounds} '
                        'or a [min, max] range inside it')
    if not TRIGRAM_MIN_OCCURRENCES <= low <= high <= TRIGRAM_MAX_OCCURRENCES:
        raise SpecError(f'{where}.occurrences {value!r} outside {bounds}')
    return value


def _visible_occurrences(value, occurrences, where):
    """Visible-window quota: visible copies count toward the set total."""
    low = occurrences if isinstance(occurrences, int) else occurrences[0]
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= low:
        raise SpecError(f'{where}.visible_occurrences must be an integer in '
                        f'[0, {low}] (visible occurrences count toward the total)')
    return value


def _trigram_sets(raw):
    out = []
    seen_b = set()
    for i, entry in enumerate(raw or []):
        where = f'trigram_sets[{i}]'
        check_keys(entry, TRIGRAM_SET_KEYS, TRIGRAM_SET_REQUIRED, where=where)
        row = {key: _trigram_word(entry[key], f'{where}.{key}') for key in 'abc'}
        if row['b'] in (row['a'], row['c']):
            raise SpecError(f'{where}.b must differ from a and c')
        if row['b'] in seen_b:
            raise SpecError(f'duplicate trigram middle word {row["b"]!r}; '
                            'edge-form measurement would alias across sets')
        seen_b.add(row['b'])
        row['occurrences'] = _occurrences(entry['occurrences'], where)
        row['visible_occurrences'] = _visible_occurrences(
            entry.get('visible_occurrences', 0), row['occurrences'], where)
        out.append(row)
    return out


def _rarity_gate(spec, base):
    """Reject any trigram middle word that is not rare by construction.

    b must be absent from the common-words file (case-insensitive whole
    word) and must not be the hub or a filter term. Hard spec error before
    any composition work.
    """
    if not spec['trigram_sets']:
        return
    path = resolve_path(spec['common_words_file'], base, where='common_words_file')
    if not path.is_file():
        raise SpecError(f'common words file not found: {path} '
                        '(required by the trigram_sets rarity gate)')
    data = load_json(path)
    check_keys(data, COMMON_WORDS_FILE_KEYS, {'words'}, where=path.name)
    common = {word.lower() for word in _list_of_str(data['words'], f'{path.name}.words')}
    off_limits = {spec['hub'].lower(), *(term.lower() for term in spec['filter_terms'])}
    for i, entry in enumerate(spec['trigram_sets']):
        word = entry['b'].lower()
        if word in off_limits:
            raise SpecError(f'trigram_sets[{i}].b {entry["b"]!r} collides with the hub '
                            'or a filter_term; b must be rare by construction')
        if word in common:
            raise SpecError(f'trigram_sets[{i}].b {entry["b"]!r} is listed in '
                            f'{path.name}; b must be rare by construction')


# --- compose ---------------------------------------------------------------

def load_payload_spec(path):
    """Load and validate a payload spec file into plain data."""
    raw = load_json(path)
    check_keys(raw, SPEC_KEYS, SPEC_REQUIRED, where=f'payload spec {path.name}')
    spec = {
        'name': raw['name'],
        'hub': raw['hub'],
        'vocab': _list_of_str(raw['vocab'], 'vocab'),
        'filter_terms': _list_of_str(raw.get('filter_terms', []), 'filter_terms'),
        'incorrect_terms': _terms(raw.get('incorrect_terms')),
        'trigram_sets': _trigram_sets(raw.get('trigram_sets')),
        'common_words_file': raw.get('common_words_file', DEFAULT_COMMON_WORDS_FILE),
        'corpus_file': raw['corpus_file'],
        'lines': _int(raw['lines'], 'lines'),
        'max_line_bytes': _int(raw['max_line_bytes'], 'max_line_bytes'),
        'seed': _int(raw['seed'], 'seed', minimum=0),
        'visibility': _visibility(raw.get('visibility')),
        'graft': _graft(raw.get('graft')),
        'vocab_file': raw['vocab_file'],
    }
    if not isinstance(spec['name'], str) or not spec['name']:
        raise SpecError('name must be a nonempty string')
    if not isinstance(spec['hub'], str) or not spec['hub']:
        raise SpecError('hub must be a nonempty string')
    if spec['hub'] in spec['vocab']:
        raise SpecError('hub must not be inside the rotation vocab')
    if not isinstance(spec['common_words_file'], str) or not spec['common_words_file']:
        raise SpecError('common_words_file must be a nonempty path string')
    if any(s['visible_occurrences'] for s in spec['trigram_sets']):
        if spec['visibility'] is None:
            raise SpecError('trigram visible_occurrences requires a visibility '
                            'section (prefix_chars bounds the visible window)')
        if spec['graft'] is None:
            raise SpecError('trigram visible_occurrences requires '
                            'graft.visible_line_range (the visible window lines)')
    return spec


def compose_from_spec(spec, base=ROOT):
    """Run the full pipeline from validated spec data. Returns (lines, info)."""
    _rarity_gate(spec, base)
    vocab_path = resolve_path(spec['vocab_file'], base, where='vocab_file')
    vocab_data = load_json(vocab_path)
    check_keys(vocab_data, VOCAB_FILE_KEYS, VOCAB_FILE_KEYS, where=vocab_path.name)
    file_vocab = _list_of_str(vocab_data['vocab'], f'{vocab_path.name}.vocab')
    if spec['vocab'] != file_vocab:
        raise SpecError(f'vocab list does not match {vocab_path.name}; '
                        'keep one source of truth per run')
    remap = pl.build_remap(file_vocab,
                           _list_of_str(vocab_data['corpus_words'], 'corpus_words'),
                           _list_of_str(vocab_data['identity_words'], 'identity_words'))
    corpus_path = resolve_path(spec['corpus_file'], base, where='corpus_file')
    if not corpus_path.is_file():
        raise SpecError(f'corpus file not found: {corpus_path}')
    corpus_lines = [line for line in
                    corpus_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    frames, offsets = pl.transform_corpus(
        corpus_lines, spec['hub'], file_vocab, remap,
        vocab_data['hub_marker'],
        _list_of_str(vocab_data['rotation_markers'], 'rotation_markers'),
        carry=True)
    predicate = pl.make_predicate(spec['hub'], spec['filter_terms'], spec['visibility'])
    lines, traces, redraws = pl.compose(frames, spec['seed'], spec['lines'],
                                        spec['max_line_bytes'], predicate)
    lines, placement = pl.graft(lines, spec['incorrect_terms'], spec['hub'],
                                spec['filter_terms'], spec['visibility'],
                                spec['graft'], spec['max_line_bytes'], predicate)
    graft_range = spec['graft']['visible_line_range'] if spec['graft'] else None
    reserved = {entry['line'] for entries in placement.values()
                for entry in entries if entry.get('offset') == 0}
    lines, trigram_reports = pl.place_trigram_sets(
        lines, spec['trigram_sets'], spec['max_line_bytes'],
        f'{spec["seed"]}:{spec["name"]}:trigram_sets',
        hub=spec['hub'], filter_terms=spec['filter_terms'],
        visibility=spec['visibility'], visible_range=graft_range,
        predicate=predicate, reserved_lines=reserved)
    for report in trigram_reports:
        measured = pl.measure_trigram(lines, report['a'], report['b'], report['c'])
        out_of_bounds = {form: count for form, count in measured.items()
                         if not TRIGRAM_MIN_OCCURRENCES <= count
                         <= TRIGRAM_MAX_OCCURRENCES}
        if out_of_bounds:
            raise SpecError(f'trigram edge forms measured outside '
                            f'[{TRIGRAM_MIN_OCCURRENCES}, {TRIGRAM_MAX_OCCURRENCES}]: '
                            f'{out_of_bounds} (planned {report["planned_occurrences"]})')
        report['measured'] = measured
        wanted = report['planned_visible_occurrences']
        if wanted:
            measured_visible = pl.measure_trigram_visible(
                lines, report['a'], report['b'], report['c'],
                spec['visibility']['prefix_chars'], graft_range)
            shortfall = {form: count for form, count in measured_visible.items()
                         if count < wanted}
            if shortfall:
                raise SpecError(f'trigram visible occurrences measured below the '
                                f'planned {wanted}: {shortfall}')
            report['measured_visible'] = measured_visible
    for line in lines:
        if not 0 < len(line.encode('utf-8')) <= spec['max_line_bytes']:
            raise SpecError('a composed line violates the byte budget')
        if '(' in line or ')' in line:
            raise SpecError('parentheses survived the post-fit strip')
    if predicate is not None and not all(predicate(line) for line in lines):
        raise SpecError('a composed line fails the visibility predicate')
    info = {'frame_start_marker_offsets': offsets, 'frame_indices_per_line': traces,
            'predicate_redraws': redraws, 'graft_placement': placement,
            'trigram_sets': trigram_reports}
    return lines, info


# --- freeze / write --------------------------------------------------------

def exclusive_write(path, data):
    """Write bytes, refusing to overwrite anything. Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, 'xb') as handle:
            handle.write(data)
    except FileExistsError as exc:
        raise SpecError(f'output already exists; refusing to overwrite: {path}') from exc
    return path


def write_candidate(run_dir, output, data, manifest):
    out_path = resolve_path(output, run_dir, where='payload.output')
    exclusive_write(out_path, data)
    manifest_path = out_path.with_name(out_path.name + '.manifest.json')
    exclusive_write(manifest_path,
                    (json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    return out_path


# --- CLI -------------------------------------------------------------------

def run(run_dir):
    run_dir = Path(run_dir)
    section = load_json(run_dir / 'spec.json').get('payload')
    if section is None:
        raise SpecError(f'{run_dir}/spec.json has no "payload" section')
    check_keys(section, PAYLOAD_SECTION_KEYS, {'output'}, where='payload section')
    modes = [key for key in ('spec_file', 'candidate_file') if key in section]
    if len(modes) != 1:
        raise SpecError('payload section needs exactly one of spec_file / candidate_file')

    if modes == ['spec_file']:
        spec_path = resolve_path(section['spec_file'], ROOT, where='payload.spec_file')
        spec = load_payload_spec(spec_path)
        lines, info = compose_from_spec(spec)
        data = pl.encode_payload(lines)
        manifest = {'utility': 'goop_payload', 'mode': 'compose',
                    'name': spec['name'], 'seed': spec['seed'], 'hub': spec['hub'],
                    'spec_file': str(spec_path), 'payload_sha256': pl.sha256(data),
                    'line_count': len(lines),
                    'line_bytes': [len(line.encode('utf-8')) for line in lines],
                    **info}
    else:
        if 'sha256' not in section:
            raise SpecError('freeze mode requires a sha256 pin')
        source = resolve_path(section['candidate_file'], ROOT,
                              where='payload.candidate_file')
        if not source.is_file():
            raise SpecError(f'candidate file not found: {source}')
        data = source.read_bytes()
        digest = pl.sha256(data)
        if digest != section['sha256']:
            raise SpecError(f'sha256 pin mismatch for {source}: '
                            f'expected {section["sha256"]}, got {digest}')
        manifest = {'utility': 'goop_payload', 'mode': 'freeze',
                    'candidate_file': str(source), 'payload_sha256': digest}

    out_path = write_candidate(run_dir, section['output'], data, manifest)
    print(f'wrote {out_path} ({len(data)} bytes, sha256 {pl.sha256(data)})')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog='goop_payload', description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    pay = sub.add_parser('payload', help='compose or freeze from run_dir/spec.json')
    pay.add_argument('run_dir', type=Path)
    args = parser.parse_args(argv)
    try:
        return run(args.run_dir)
    except SpecError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
