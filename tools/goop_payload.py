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

from gooplib import bridging as br
from gooplib import payload as pl
from gooplib.spec import SpecError, check_keys, load_json, resolve_path

ROOT = Path(__file__).resolve().parents[1]

PAYLOAD_SECTION_KEYS = {'spec_file', 'candidate_file', 'sha256', 'output'}
SPEC_KEYS = {'name', 'hub', 'vocab_file', 'vocab', 'filter_terms',
             'incorrect_terms', 'trigram_sets', 'common_words_file',
             'corpus_file', 'lines', 'min_line_bytes', 'max_line_bytes',
             'seed', 'visibility', 'graft', 'bridging'}
SPEC_REQUIRED = {'name', 'hub', 'vocab_file', 'vocab', 'corpus_file',
                 'lines', 'max_line_bytes', 'seed'}
VISIBILITY_KEYS = {'prefix_chars', 'require_hub_in_prefix', 'require_filter_in_prefix'}
GRAFT_KEYS = {'bridges_visible_in_prefix', 'visible_line_range'}
TERM_KEYS = {'term', 'neighbors'}
TRIGRAM_SET_KEYS = {'a', 'b', 'c', 'occurrences', 'visible_occurrences'}
TRIGRAM_SET_REQUIRED = {'a', 'b', 'c', 'occurrences'}
# Megaline-only keys: required when 'megaline' is true, rejected otherwise.
MEGALINE_KEYS = {'filter_terms', 'filter_prefix_chars', 'truncation_chars',
                 'lead_ins'}
BRIDGING_KEYS = {'anchor', 'target', 'destination', 'doses', 'paren', 'form',
                 'carriers', 'common_words_file', 'errata', 'megaline',
                 'second_pair',
                 'filter_terms', 'filter_prefix_chars', 'truncation_chars',
                 'lead_ins'}
BRIDGING_REQUIRED = (BRIDGING_KEYS - {'common_words_file', 'megaline',
                                      'second_pair'} - MEGALINE_KEYS)
BRIDGING_SPEC_REQUIRED = {'name', 'lines', 'max_line_bytes', 'seed', 'bridging'}
# Bridging mode is disjoint from the legacy corpus-remap pipeline: these
# keys belong to the legacy mode and are rejected alongside 'bridging'.
BRIDGING_LEGACY_KEYS = {'hub', 'vocab_file', 'vocab', 'filter_terms',
                        'incorrect_terms', 'trigram_sets', 'corpus_file',
                        'visibility', 'graft', 'common_words_file'}
COMMON_WORDS_FILE_KEYS = {'provenance', 'words'}
VOCAB_FILE_KEYS = {'vocab', 'corpus_words', 'identity_words',
                   'hub_marker', 'rotation_markers'}

# Owner rule (2026-10-13): each trigram set's edge forms appear 4-10 times;
# b is always a rare word (see _rarity_gate), task-relevance optional.
TRIGRAM_MIN_OCCURRENCES = 4
TRIGRAM_MAX_OCCURRENCES = 10
DEFAULT_COMMON_WORDS_FILE = 'payloads/common_words.json'
DEFAULT_ORDINARY_WORDS_FILE = 'payloads/ordinary_words.json'
# The goop baseline for the bridging stealth check: the pinned v13 control.
BASELINE_SPEC_FILE = 'specs/payload_v13.json'


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


def _megaline(raw, vocab):
    """Validate the megaline-only keys (one complete BRIDGING per line).

    vocab is the union of all pairs' words: lead-ins must stay role-word-
    free against EVERY pair, not just the first (a smuggled pair-2 word
    would otherwise pass load and only fail at compose — or never, if the
    carrier is never dealt).
    """
    missing = sorted(MEGALINE_KEYS - set(raw))
    if missing:
        raise SpecError(f'bridging.megaline requires {missing}')
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
    """Validate a 'bridging' section into plain data (conformant mode)."""
    check_keys(raw, BRIDGING_KEYS, BRIDGING_REQUIRED, where='bridging')
    words = {role: _trigram_word(raw[role], f'bridging.{role}') for role in br.ROLES}
    if len(set(words.values())) != len(br.ROLES):
        raise SpecError('bridging anchor/target/destination must be three distinct '
                        'words; an anchor at a target position is unattributable '
                        '(the R1 mistake)')
    doses = _int(raw['doses'], 'bridging.doses')
    if raw['paren'] is not True:
        raise SpecError('bridging.paren must be true; the conformant drill format is '
                        'parenthesized inserts (paren-stripping was the R5 break)')
    forms = _list_of_str(raw['form'], 'bridging.form')
    if not forms or len(set(forms)) != len(forms) or set(forms) - set(br.FORMS):
        raise SpecError(f'bridging.form must be a nonempty duplicate-free subset of '
                        f'{list(br.FORMS)}')
    megaline = _bool(raw.get('megaline', False), 'bridging.megaline')
    extras = sorted(set(raw) & MEGALINE_KEYS)
    if not megaline and extras:
        raise SpecError(f'bridging sets megaline-only keys {extras} without '
                        '"megaline": true')
    second = raw.get('second_pair')
    pairs = [words]
    if second is not None:
        if not megaline:
            raise SpecError('bridging.second_pair requires "megaline": true '
                            '(the classic bridging mode is single-pair)')
        check_keys(second, {'target', 'destination'}, {'target', 'destination'},
                   where='bridging.second_pair')
        words2 = {'anchor': words['anchor'],
                  'target': _trigram_word(second['target'],
                                          'bridging.second_pair.target'),
                  'destination': _trigram_word(
                      second['destination'], 'bridging.second_pair.destination')}
        if words2['target'] == words2['destination']:
            raise SpecError('bridging.second_pair target/destination must be '
                            'distinct words')
        if words['anchor'] in (words2['target'], words2['destination']):
            raise SpecError('bridging.second_pair puts the anchor at a leaf '
                            'position (the R1 mistake)')
        if words2['target'] == words['target'] and \
                words2['destination'] == words['destination']:
            raise SpecError('bridging.second_pair duplicates the first pair')
        shared = {words['target'], words['destination']} & \
                 {words2['target'], words2['destination']}
        if len(shared) > 1:
            raise SpecError(f'bridging.second_pair shares leaves {sorted(shared)} '
                            'with the first pair: two shared leaves alias the '
                            'canonical configs between pairs (attribution would '
                            'miscount); one shared leaf is the chaining limit')
        pairs.append(words2)
    vocab = sorted({word for pair in pairs for word in pair.values()})
    carriers = _drill_sentences(raw['carriers'], vocab, 'bridging.carriers')
    gate = raw.get('common_words_file', DEFAULT_ORDINARY_WORDS_FILE)
    if not isinstance(gate, str) or not gate:
        raise SpecError('bridging.common_words_file must be a nonempty path string')
    errata = raw.get('errata')
    if errata is not None and (not isinstance(errata, str) or not errata):
        raise SpecError('bridging.errata must be a nonempty string when present')
    out = {'words': words, 'pairs': pairs, 'doses': doses, 'forms': forms,
           'carriers': carriers, 'common_words_file': gate, 'errata': errata,
           'megaline': megaline}
    if megaline:
        out.update(_megaline(raw, vocab))
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


# --- compose ---------------------------------------------------------------

def _load_bridging_spec(raw, where):
    """Validate a bridging-mode spec; disjoint from the legacy pipeline."""
    check_keys(raw, SPEC_KEYS, BRIDGING_SPEC_REQUIRED, where=where)
    legacy = sorted(set(raw) & BRIDGING_LEGACY_KEYS)
    if legacy:
        raise SpecError(f'{where} sets bridging alongside legacy keys {legacy}; '
                        'the modes are disjoint')
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
    bridging = spec['bridging']
    if bridging['megaline']:
        if spec['min_line_bytes'] is None:
            raise SpecError('megaline mode requires min_line_bytes: the line '
                            'band is what makes a full set fit every slot')
        for key in ('carriers', 'lead_ins'):
            if len(bridging[key]) < spec['lines']:
                raise SpecError(f'bridging deals {key} without replacement: '
                                f'{len(bridging[key])} < {spec["lines"]} lines')
        return spec
    need = len(br.CANONICAL_CONFIGS) * bridging['doses']
    if need > spec['lines']:
        raise SpecError(f'bridging plants {need} LINK-pair lines '
                        f'({len(br.CANONICAL_CONFIGS)} configs x doses) but '
                        f'lines is {spec["lines"]}')
    if len(bridging['carriers']) < spec['lines']:
        raise SpecError(f'bridging deals carriers without replacement: '
                        f'{len(bridging["carriers"])} carriers < '
                        f'{spec["lines"]} lines')
    return spec


def load_payload_spec(path):
    """Load and validate a payload spec file into plain data."""
    raw = load_json(path)
    if 'bridging' in raw:
        return _load_bridging_spec(raw, f'payload spec {path.name}')
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
        'min_line_bytes': (_int(raw['min_line_bytes'], 'min_line_bytes')
                           if 'min_line_bytes' in raw else None),
        'max_line_bytes': _int(raw['max_line_bytes'], 'max_line_bytes'),
        'seed': _int(raw['seed'], 'seed', minimum=0),
        'visibility': _visibility(raw.get('visibility')),
        'graft': _graft(raw.get('graft')),
        'vocab_file': raw['vocab_file'],
    }
    if (spec['min_line_bytes'] is not None
            and spec['min_line_bytes'] > spec['max_line_bytes']):
        raise SpecError('min_line_bytes must not exceed max_line_bytes')
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
    if spec.get('bridging') is not None:
        return _compose_bridging(spec, base)
    return _compose_legacy(spec, base)


def _check_bridging_text(lines, words, sets, min_bytes, max_bytes):
    """Hard-fail text integrity shared by both bridging pipelines.

    Parsed off the final text, not the plan: per-config counts equal `sets`
    exactly (every canonical config), directed forms equal the canonical
    multiset, inserts balanced, every anchor at a bridge position, and
    every line lands in [min_bytes, max_bytes].
    """
    integrity = br.paren_integrity(lines)
    if not integrity['ok']:
        raise SpecError(f'paren integrity failed: {integrity["violations"][:3]}')
    audit = br.role_audit(lines, words)
    if not audit['ok']:
        raise SpecError(f'role audit failed: {audit["violations"][:3]}')
    measured = br.measure_bridging(lines, words)
    expected = {br.config_label(config): sets for config in br.CANONICAL_CONFIGS}
    if measured['per_config'] != expected:
        raise SpecError(f'{len(br.CANONICAL_CONFIGS)}-config coverage mismatch: '
                        f'measured {measured["per_config"]} != expected {expected}')
    if measured['directed_forms'] != br.expected_directed_forms(sets):
        raise SpecError(f'directed-form mismatch: {measured["directed_forms"]}')
    for line in lines:
        if not min_bytes <= len(line.encode('utf-8')) <= max_bytes:
            raise SpecError('a composed line violates the byte budget')
    return measured, audit, integrity


def _bridging_info(bridging, plan, measured, audit, integrity, stats, extra=None):
    """The manifest 'bridging' section, shared by both bridging pipelines."""
    section = {'roles': dict(bridging['words']), 'doses': bridging['doses'],
               'forms': list(bridging['forms']), 'plan': plan,
               'measurement': measured, 'role_audit': audit,
               'paren_integrity': integrity, 'carrier_stats': stats,
               'leaf_links': [f'{first}>{second}' for first, second
                              in br.CANONICAL_LEAF_LINKS],
               'errata': bridging['errata'],
               'pairs': [dict(pair) for pair in bridging['pairs']],
               'canonical_source_note': br.CANONICAL_SOURCE_NOTE}
    if extra:
        section.update(extra)
    return {'bridging': section}


def _compose_bridging(spec, base):
    """Conformant bridging pipeline: weave one BRIDGING across the vehicle.

    Megaline mode branches away; the text integrity hard-fails live in
    _check_bridging_text (parsed off the final text, not the plan).
    """
    if spec['bridging']['megaline']:
        return _compose_megalines(spec, base)
    bridging = spec['bridging']
    _anchor_gate(bridging, base)
    lines, plan = br.compose_bridging(
        bridging['carriers'], bridging['words'], bridging['doses'],
        bridging['forms'], spec['lines'], spec['seed'])
    measured, audit, integrity = _check_bridging_text(
        lines, bridging['words'], bridging['doses'], 1, spec['max_line_bytes'])
    stats = br.carrier_stats(lines, _goop_baseline_lines(base))
    return lines, _bridging_info(bridging, plan, measured, audit, integrity, stats)


def _check_bridging_pairs_text(lines, pairs, sets, min_bytes, max_bytes):
    """The pair-mode sibling of _check_bridging_text: whole-text integrity.

    Per pair, every canonical config lands at exactly `sets` across the
    text; the union directed forms equal the pair multiset; every anchor
    at a bridge position; parens balanced; every line in the byte band.
    """
    integrity = br.paren_integrity(lines)
    if not integrity['ok']:
        raise SpecError(f'paren integrity failed: {integrity["violations"][:3]}')
    audit = br.role_audit_pairs(lines, pairs)
    if not audit['ok']:
        raise SpecError(f'role audit failed: {audit["violations"][:3]}')
    measured = br.measure_bridging_pairs(lines, pairs)
    for pair_index, pair in enumerate(pairs):
        expected = {br.config_label(config): sets
                    for config in br.pair_configs(pair)}
        if measured['per_pair'][pair_index] != expected:
            raise SpecError(f'pair {pair_index} coverage mismatch: measured '
                            f'{measured["per_pair"][pair_index]} != expected '
                            f'{expected}')
    if measured['directed_forms'] != br.expected_directed_forms_pairs(pairs, sets):
        raise SpecError(f'directed-form mismatch: {measured["directed_forms"]}')
    for line in lines:
        if not min_bytes <= len(line.encode('utf-8')) <= max_bytes:
            raise SpecError('a composed line violates the byte budget')
    return measured, audit, integrity


def _compose_megalines_pairs(spec, base):
    """Multi-pair megaline pipeline (2026-10-15 doctrine: shared anchor,
    chained leaves, `doses` copies of every pair's set per line).

    The single-pair hard checks hold per pair per line: full coverage, the
    filter echo in the window, a complete LINK-pair in the window, and the
    first four LINKs inside the probable truncation window.
    """
    bridging = spec['bridging']
    pairs = bridging['pairs']
    _anchor_gate(bridging, base)
    try:
        lines, plan = br.compose_megalines_pairs(
            bridging['carriers'], bridging['lead_ins'], pairs,
            bridging['doses'], bridging['forms'], spec['lines'],
            spec['min_line_bytes'], spec['max_line_bytes'], spec['seed'])
    except ValueError as exc:
        raise SpecError(str(exc)) from exc
    sets = bridging['doses'] * spec['lines']
    measured, audit, integrity = _check_bridging_pairs_text(
        lines, pairs, sets, spec['min_line_bytes'], spec['max_line_bytes'])
    mega = br.measure_megalines_pairs(
        lines, pairs, bridging['filter_terms'],
        bridging['filter_prefix_chars'], bridging['truncation_chars'])
    expected_per_pair = [{br.config_label(config): bridging['doses']
                          for config in br.pair_configs(pair)}
                         for pair in pairs]
    expected_links = (2 * len(br.CANONICAL_CONFIGS) * len(pairs)
                      * bridging['doses'])
    for row in mega['per_line']:
        if row['link_total'] != expected_links:
            raise SpecError(f'line {row["line"]}: link total '
                            f'{row["link_total"]} != {expected_links} '
                            '(injected or missing links)')
        for pair_index in range(len(pairs)):
            if row['per_pair'][pair_index]['per_config'] != \
                    expected_per_pair[pair_index]:
                raise SpecError(f'line {row["line"]}: pair {pair_index} '
                                f'{len(br.CANONICAL_CONFIGS)}-config coverage '
                                'mismatch')
        if row['filter_term'] is None:
            raise SpecError(f'line {row["line"]}: no filter term inside the '
                            f'first {bridging["filter_prefix_chars"]} chars')
        if not row['complete_pair_in_window']:
            raise SpecError(f'line {row["line"]}: no complete LINK-pair inside '
                            f'the first {bridging["filter_prefix_chars"]} chars')
        if not row['first_four_links_in_truncation']:
            raise SpecError(f'line {row["line"]}: the first four LINKs do not '
                            f'all end inside the probable truncation window '
                            f'(the first {bridging["truncation_chars"]} chars)')
    stats = br.carrier_stats(lines, _goop_baseline_lines(base))
    extra = {'megaline': {'filter_terms': list(bridging['filter_terms']),
                          'filter_prefix_chars': bridging['filter_prefix_chars'],
                          'truncation_chars': bridging['truncation_chars'],
                          'min_line_bytes': spec['min_line_bytes'],
                          'max_line_bytes': spec['max_line_bytes'],
                          'pairs': [dict(pair) for pair in pairs],
                          **mega}}
    return lines, _bridging_info(bridging, plan, measured, audit, integrity,
                                 stats, extra)


def _compose_megalines(spec, base):
    """Megaline pipeline: a full BRIDGING per line, hard-fail per-line integrity.

    Beyond _check_bridging_text: every line carries all 9 canonical configs
    at `doses`, the filter echo sits inside the window of EVERY line, every
    window holds a complete LINK-pair (dose integrity), and the first four
    LINKs of EVERY line end inside the probable truncation window
    (truncation_chars; the front-packing fallback property).
    """
    bridging = spec['bridging']
    _anchor_gate(bridging, base)
    if len(bridging['pairs']) > 1:
        return _compose_megalines_pairs(spec, base)
    try:
        lines, plan = br.compose_megalines(
            bridging['carriers'], bridging['lead_ins'], bridging['words'],
            bridging['doses'], bridging['forms'], spec['lines'],
            spec['min_line_bytes'], spec['max_line_bytes'], spec['seed'])
    except ValueError as exc:
        raise SpecError(str(exc)) from exc
    sets = bridging['doses'] * spec['lines']
    measured, audit, integrity = _check_bridging_text(
        lines, bridging['words'], sets, spec['min_line_bytes'],
        spec['max_line_bytes'])
    mega = br.measure_megalines(lines, bridging['words'],
                                bridging['filter_terms'],
                                bridging['filter_prefix_chars'],
                                bridging['truncation_chars'])
    expected_per_line = {br.config_label(config): bridging['doses']
                         for config in br.CANONICAL_CONFIGS}
    for row in mega['per_line']:
        if row['per_config'] != expected_per_line:
            raise SpecError(f'line {row["line"]}: per-line '
                            f'{len(br.CANONICAL_CONFIGS)}-config coverage mismatch: '
                            f'{row["per_config"]}')
        if row['filter_term'] is None:
            raise SpecError(f'line {row["line"]}: no filter term inside the first '
                            f'{bridging["filter_prefix_chars"]} chars (the v13 '
                            'visibility lesson; the lead-in owns the echo)')
        if not row['complete_pair_in_window']:
            raise SpecError(f'line {row["line"]}: no complete LINK-pair inside the '
                            f'first {bridging["filter_prefix_chars"]} chars '
                            '(dose integrity)')
        if not row['first_four_links_in_truncation']:
            raise SpecError(f'line {row["line"]}: the first four LINKs do not all '
                            f'end inside the probable truncation window (the '
                            f'first {bridging["truncation_chars"]} chars; '
                            'front-packing is the fallback property)')
    stats = br.carrier_stats(lines, _goop_baseline_lines(base))
    extra = {'megaline': {'filter_terms': list(bridging['filter_terms']),
                          'filter_prefix_chars': bridging['filter_prefix_chars'],
                          'truncation_chars': bridging['truncation_chars'],
                          'min_line_bytes': spec['min_line_bytes'],
                          **mega}}
    return lines, _bridging_info(bridging, plan, measured, audit, integrity,
                                 stats, extra)


def _goop_baseline_lines(base):
    """The goop baseline for the entropy delta: the pinned v13 control text.

    Best effort: a missing/broken baseline never blocks composition (the
    delta fields simply stay out of the manifest); the tests pin it present.
    """
    try:
        baseline = load_payload_spec(resolve_path(BASELINE_SPEC_FILE, base,
                                                  where='baseline spec'))
        lines, _ = _compose_legacy(baseline, base)
    except SpecError:
        return None
    return lines


def _compose_legacy(spec, base=ROOT):
    """The legacy corpus-remap pipeline. Returns (lines, info)."""
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
    min_bytes = spec['min_line_bytes'] or 1
    for line in lines:
        if not min_bytes <= len(line.encode('utf-8')) <= spec['max_line_bytes']:
            raise SpecError('a composed line violates the byte budget')
        if '(' in line or ')' in line:
            raise SpecError('parentheses survived the post-fit strip')
    if predicate is not None and not all(predicate(line) for line in lines):
        raise SpecError('a composed line fails the visibility predicate')
    info = {'hub': spec['hub'],
            'frame_start_marker_offsets': offsets, 'frame_indices_per_line': traces,
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
