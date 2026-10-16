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
spec JSON and the word-list JSONs it references. Nothing is hardcoded here
but machinery.

The classic corpus-remap pipeline (hub/vocab rotation, incorrect_terms
graft, trigram_sets placement + measurement), the second_pair and
flat-triple bridging forms, and the non-megaline bridging mode are DELETED
(owner ruling 2026-10-15: "delete the code paths"; the specs they served
were burned in the same session). The surviving contract is megaline +
pairs: one shared anchor, 1-3 chained pairs, `doses` copies of every
pair's canonical set per line.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError, check_keys, load_json, resolve_path

ROOT = Path(__file__).resolve().parents[1]

PAYLOAD_SECTION_KEYS = {'spec_file', 'candidate_file', 'sha256', 'output'}
SPEC_KEYS = {'name', 'lines', 'min_line_bytes', 'max_line_bytes',
             'seed', 'bridging'}
SPEC_REQUIRED = {'name', 'lines', 'max_line_bytes', 'seed', 'bridging'}
# Megaline-only keys; all required (megaline is the only surviving mode).
MEGALINE_KEYS = {'filter_terms', 'filter_prefix_chars', 'truncation_chars',
                 'lead_ins'}
BRIDGING_KEYS = {'anchor', 'doses', 'paren', 'form', 'carriers',
                 'common_words_file', 'errata', 'megaline', 'pairs',
                 'filter_terms', 'filter_prefix_chars', 'truncation_chars',
                 'lead_ins'}
BRIDGING_REQUIRED = BRIDGING_KEYS - {'common_words_file', 'paren', 'errata'}
# Deleted classic-pipeline / pre-pairs keys (2026-10-15): a spec carrying
# any of these fails here with a pointed error, not a bare key list.
CLASSIC_KEYS = {'hub', 'vocab_file', 'vocab', 'filter_terms',
                'incorrect_terms', 'trigram_sets', 'corpus_file',
                'visibility', 'graft', 'common_words_file',
                'target', 'destination', 'second_pair'}
COMMON_WORDS_FILE_KEYS = {'provenance', 'words'}
DEFAULT_ORDINARY_WORDS_FILE = 'payloads/ordinary_words.json'


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


def _trigram_word(value, where):
    """A word the edge regex ([a-z]+) can measure exactly."""
    if (not isinstance(value, str) or not value.isascii()
            or not value.isalpha() or not value.islower()):
        raise SpecError(f'{where} must be a single lowercase ascii word')
    return value


def _drill_sentences(raw_list, word_values, where):
    """Carrier-register sentences: nonempty ascii, paren-free, role-word-free."""
    sentences = _list_of_str(raw_list, where)
    for i, sentence in enumerate(sentences):
        if not sentence.strip() or not sentence.isascii():
            raise SpecError(f'{where}[{i}] must be nonempty ascii')
        if '(' in sentence or ')' in sentence:
            raise SpecError(f'{where}[{i}] must not contain parens; '
                            'the inserts own the parens')
        clash = set(br.WORD.findall(sentence.lower())) & set(word_values)
        if clash:
            raise SpecError(f'{where}[{i}] contains role words '
                            f'{sorted(clash)}; every role occurrence must be '
                            'attributable to a planted insert')
    return sentences


# --- spec validation -------------------------------------------------------

def _megaline(raw, vocab):
    """Validate the megaline-only keys (one complete BRIDGING per line).

    vocab is the union of all pairs' words: lead-ins must stay role-word-
    free against EVERY pair, not just the first (a smuggled pair-2 word
    would otherwise pass load and only fail at compose — or never, if the
    carrier is never dealt).
    """
    terms = raw['filter_terms']
    if not terms:
        raise SpecError('bridging.filter_terms must be nonempty')
    filter_terms = [_trigram_word(term, f'bridging.filter_terms[{i}]')
                    for i, term in enumerate(terms)]
    if len(set(filter_terms)) != len(filter_terms):
        raise SpecError('bridging.filter_terms must be duplicate-free')
    prefix_chars = _int(raw['filter_prefix_chars'], 'bridging.filter_prefix_chars')
    truncation = _int(raw['truncation_chars'], 'bridging.truncation_chars')
    if truncation > prefix_chars:
        raise SpecError(f'bridging.truncation_chars ({truncation}) must not exceed '
                        f'bridging.filter_prefix_chars ({prefix_chars}); the '
                        'probable truncation sits inside the delivered-slot window')
    lead_ins = _drill_sentences(raw['lead_ins'], vocab, 'bridging.lead_ins')
    for i, lead in enumerate(lead_ins):
        if not any(term in lead.lower() for term in filter_terms):
            raise SpecError(f'bridging.lead_ins[{i}] carries no filter term; the '
                            'lead-in owns the filter echo (the v13 visibility lesson)')
    return {'filter_terms': filter_terms, 'filter_prefix_chars': prefix_chars,
            'truncation_chars': truncation, 'lead_ins': lead_ins}


def _bridging(raw):
    """Validate a 'bridging' section into plain data (megaline pairs mode —
    the only surviving mode, 2026-10-15)."""
    stray = sorted({'target', 'destination', 'second_pair'} & set(raw))
    if stray:
        raise SpecError(f'bridging.pairs is mutually exclusive with {stray}; '
                        'one shape per spec (the flat-triple and second_pair '
                        'forms were deleted 2026-10-15)')
    check_keys(raw, BRIDGING_KEYS, BRIDGING_REQUIRED, where='bridging')
    megaline = _bool(raw['megaline'], 'bridging.megaline')
    if not megaline:
        raise SpecError('bridging.megaline must be true: the classic bridging '
                        'mode is deleted (2026-10-15); only megaline pairs '
                        'specs survive')
    words = {'anchor': _trigram_word(raw['anchor'], 'bridging.anchor')}
    doses = _int(raw['doses'], 'bridging.doses')
    # 2026-10-15 ruling (verbatim in docs/TRIGRAM_BRIDGING.md): 'strip
    # them.' Parens are STRIPPED by default; legacy paren:true specs keep
    # rendering '(x y)' for byte-identical historical reproduction.
    paren = _bool(raw.get('paren', False), 'bridging.paren')
    forms = _list_of_str(raw['form'], 'bridging.form')
    if not forms or len(set(forms)) != len(forms) or set(forms) - set(br.FORMS):
        raise SpecError(f'bridging.form must be a nonempty duplicate-free subset of '
                        f'{list(br.FORMS)}')
    pair_list = raw['pairs']
    if not (isinstance(pair_list, list) and 1 <= len(pair_list) <= 3):
        raise SpecError('bridging.pairs must be a list of 1-3 pair objects '
                        '(K-way along the one anchor; the chaining limit '
                        'binds pairwise)')
    pairs = []
    for i, entry in enumerate(pair_list):
        where = f'bridging.pairs[{i}]'
        check_keys(entry, {'target', 'destination'},
                   {'target', 'destination'}, where=where)
        pairs.append({'anchor': words['anchor'],
                      'target': _trigram_word(entry['target'],
                                              f'{where}.target'),
                      'destination': _trigram_word(
                          entry['destination'], f'{where}.destination')})
    for pair_index, pair in enumerate(pairs):
        if pair['target'] == pair['destination']:
            raise SpecError(f'pair {pair_index} target/destination must be '
                            'distinct words')
        if words['anchor'] in (pair['target'], pair['destination']):
            raise SpecError(f'pair {pair_index} puts the anchor at a leaf '
                            'position (the R1 mistake)')
    for i, first in enumerate(pairs):
        for j, other in enumerate(pairs[i + 1:], start=i + 1):
            if (first['target'] == other['target']
                    and first['destination'] == other['destination']):
                raise SpecError(f'pairs {i} and {j} are identical duplicates')
            shared = {first['target'], first['destination']} & \
                     {other['target'], other['destination']}
            if len(shared) > 1:
                raise SpecError(f'pairs {i} and {j} share leaves '
                                f'{sorted(shared)}: two shared leaves alias the '
                                'canonical configs between pairs (attribution '
                                'would miscount); one shared leaf is the '
                                'chaining limit')
    vocab = sorted({word for pair in pairs for word in pair.values()})
    carriers = _drill_sentences(raw['carriers'], vocab, 'bridging.carriers')
    gate = raw.get('common_words_file', DEFAULT_ORDINARY_WORDS_FILE)
    if not isinstance(gate, str) or not gate:
        raise SpecError('bridging.common_words_file must be a nonempty path string')
    errata = raw.get('errata')
    if errata is not None and (not isinstance(errata, str) or not errata):
        raise SpecError('bridging.errata must be a nonempty string when present')
    out = {'words': words, 'pairs': pairs, 'doses': doses, 'forms': forms,
           'paren': paren,
           'carriers': carriers, 'common_words_file': gate, 'errata': errata,
           'megaline': True}
    out.update(_megaline(raw, vocab))
    return out


def _anchor_gate(bridging, base):
    """Reject an ordinary-English anchor: it must be a rare weak-embedding token.

    The gate file is the ordinary-words list (common English; hainish-class
    nonce forms are absent by construction). Hard spec error before any
    composition work — an ordinary-word anchor can never be attributable
    (the R1 mistake: hainish->delete made every hub occurrence noise).
    Target/destination are ordinary task words by design and are not gated.
    """
    path = resolve_path(bridging['common_words_file'], base,
                        where='bridging.common_words_file')
    if not path.is_file():
        raise SpecError(f'ordinary words file not found: {path} '
                        '(required by the bridging anchor gate)')
    data = load_json(path)
    check_keys(data, COMMON_WORDS_FILE_KEYS, {'words'}, where=path.name)
    ordinary = {word.lower() for word in _list_of_str(data['words'], f'{path.name}.words')}
    anchor = bridging['words']['anchor']
    if anchor.lower() in ordinary:
        raise SpecError(f'bridging.anchor {anchor!r} is listed in {path.name}; the '
                        'anchor must be a rare weak-embedding token (an '
                        'ordinary-word anchor is unattributable — the R1 mistake)')


def load_payload_spec(path):
    """Load and validate a payload spec file (megaline pairs mode only)."""
    raw = load_json(path)
    where = f'payload spec {path.name}'
    classic = sorted(set(raw) & CLASSIC_KEYS)
    if classic:
        raise SpecError(f'{where} carries deleted classic-pipeline keys '
                        f'{classic}: the classic compose path and the '
                        'second_pair/flat-triple bridging forms were deleted '
                        '2026-10-15 (megaline + pairs is the surviving contract)')
    check_keys(raw, SPEC_KEYS, SPEC_REQUIRED, where=where)
    if not isinstance(raw['name'], str) or not raw['name']:
        raise SpecError('name must be a nonempty string')
    spec = {'name': raw['name'],
            'lines': _int(raw['lines'], 'lines'),
            'min_line_bytes': (_int(raw['min_line_bytes'], 'min_line_bytes')
                               if 'min_line_bytes' in raw else None),
            'max_line_bytes': _int(raw['max_line_bytes'], 'max_line_bytes'),
            'seed': _int(raw['seed'], 'seed', minimum=0),
            'bridging': _bridging(raw['bridging'])}
    if (spec['min_line_bytes'] is not None
            and spec['min_line_bytes'] > spec['max_line_bytes']):
        raise SpecError('min_line_bytes must not exceed max_line_bytes')
    if spec['min_line_bytes'] is None:
        raise SpecError('megaline mode requires min_line_bytes: the line '
                        'band is what makes a full set fit every slot')
    for key in ('carriers', 'lead_ins'):
        if len(spec['bridging'][key]) < spec['lines']:
            raise SpecError(f'bridging deals {key} without replacement: '
                            f'{len(spec["bridging"][key])} < {spec["lines"]} lines')
    return spec


# --- compose ---------------------------------------------------------------

def compose_from_spec(spec, base=ROOT):
    """Run the megaline-pairs pipeline from validated spec data.

    Returns (lines, info)."""
    return _compose_megalines_pairs(spec, base)


def _bridging_info(bridging, plan, stats, extra=None):
    """The manifest 'bridging' section, shared by the bridging pipeline.

    The paren-audit sections (measurement / role_audit / paren_integrity)
    were deleted with the audit stack (2026-10-15 ruling): construction
    correctness comes from the deterministic compose + spec validation;
    outcomes are measured downstream.
    """
    section = {'roles': dict(bridging['words']), 'doses': bridging['doses'],
               'forms': list(bridging['forms']), 'plan': plan,
               'paren': bridging['paren'], 'carrier_stats': stats,
               'leaf_links': [f'{first}>{second}' for first, second
                              in br.CANONICAL_LEAF_LINKS],
               'errata': bridging['errata'],
               'pairs': [dict(pair) for pair in bridging['pairs']],
               'canonical_source_note': br.CANONICAL_SOURCE_NOTE}
    if extra:
        section.update(extra)
    return {'bridging': section}


def _check_megaline_delivery_shape(lines, plan, bridging):
    """The surviving delivery-shape checks (construction-side, plan-derived).

    The audit stack is gone; these are the two checks that protect
    DELIVERY (not dose-counting): the filter echo lands inside the slot
    window of EVERY line (the v13 visibility lesson; no echo, no
    delivery), and the first four LINKs of every line end inside the
    probable truncation window (the front-packing fallback). Offsets come
    from the compose plan, not from parsing the text.
    """
    for row in plan:
        line = lines[row['line']]
        if not any(term in line[:bridging['filter_prefix_chars']].lower()
                   for term in bridging['filter_terms']):
            raise SpecError(f'line {row["line"]}: no filter echo inside the '
                            f'first {bridging["filter_prefix_chars"]} chars '
                            '(the v13 visibility lesson)')
        if (len(row['inserts']) >= 4
                and row['inserts'][3]['end'] > bridging['truncation_chars']):
            raise SpecError(f'line {row["line"]}: the first four LINKs do not '
                            'all end inside the probable truncation window '
                            f'(first {bridging["truncation_chars"]} chars)')


def _compose_megalines_pairs(spec, base):
    """Multi-pair megaline pipeline (2026-10-15 doctrine: shared anchor,
    chained leaves, `doses` copies of every pair's set per line).

    Dose-counting audit deleted (2026-10-15 ruling); the surviving checks
    are spec validation, the compose fit, and _check_megaline_delivery_shape.
    """
    bridging = spec['bridging']
    pairs = bridging['pairs']
    _anchor_gate(bridging, base)
    try:
        lines, plan = br.compose_megalines_pairs(
            bridging['carriers'], bridging['lead_ins'], pairs,
            bridging['doses'], bridging['forms'], spec['lines'],
            spec['min_line_bytes'], spec['max_line_bytes'], spec['seed'],
            bridging['paren'])
    except ValueError as exc:
        raise SpecError(str(exc)) from exc
    _check_megaline_delivery_shape(lines, plan, bridging)
    # The v13 goop-baseline entropy delta died with the owner's spec burn
    # (2026-10-15); carrier_stats takes None and the delta fields simply
    # stay out of the manifest.
    stats = br.carrier_stats(lines, None)
    extra = {'megaline': {'filter_terms': list(bridging['filter_terms']),
                          'filter_prefix_chars': bridging['filter_prefix_chars'],
                          'truncation_chars': bridging['truncation_chars'],
                          'min_line_bytes': spec['min_line_bytes'],
                          'max_line_bytes': spec['max_line_bytes'],
                          'pairs': [dict(pair) for pair in pairs]}}
    return lines, _bridging_info(bridging, plan, stats, extra)


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
                    'name': spec['name'], 'seed': spec['seed'],
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
