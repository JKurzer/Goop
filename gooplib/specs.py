"""spec.json loading and validation for the build+pack+verify utility.

The build section of a run's spec.json is the ONLY source of build
parameters (goop rule 2: zero magic numbers in utilities):

    {
      "arm": "example-arm",
      "payload": {"path": "inputs/candidate.txt", "sha256": "<64 hex>"},
      "build": {
        "slots": 20,
        "slot_size": 256,
        "doses": {"RunA": 5, "RunB": 10},
        "format_table": true,
        "config_tags": true
      }
    }

- slots:        even integer >= 2; one fixed-size retained data slot per
                candidate payload line.
- slot_size:    bytes per slot; every payload line must be strictly shorter
                (slots are NUL-padded to slot_size).
- doses:        exactly two cells; dose = occupied slots in that cell
                (0 <= dose <= slots). Cell names come from the dict keys.
- format_table: hoist printf formats into the slot struct (formats and tags
                interleaved in .rdata).
- config_tags:  weave slot pointers into SimConfig. With format_table, the
                pointers are assigned by explicit statements in main() (the
                2026-10-13 scheme: LEAs stay in the driver window at any N).
                Without format_table, the legacy default-member-initializer
                field naming bramble_slot_XX is used.
- exports:      optional fake export set (owner ruling 2026-10-15):
                {"sets": N, "anchor": w, "target": w, "destination": w}.
                N full canonical LINK sets ride the PE export table as
                no-op exported functions named '<from>_<to>_<NNN>'; one set
                is functionally one dose (gooplib/exports.py).
- fn_literals:  optional function-literals vector (owner 2026-10-15: "just
                shoving them as string literals into some functions"). Same
                words/sets shape as exports; optionally add
                `links_per_literal: 2` or `4` to keep complete two-LINK
                configs inside independently visible <=120-byte strings.
                `resource_carrier: true` also plants one copy of each
                distinct bundle in RCDATA. Historical UPX builds used this
                mirror; direct-staged builds already expose the .rdata copy.
                Without that key, the historical one-LINK layout remains
                reproducible. Arrays are referenced in both loops via
                volatile reads into the inert sink; output unchanged.

The MSVC toolchain is an environment pin: GOOP_VCVARS must name the
vcvars64.bat to use; the utility asserts the pinned file exists.
"""
import hashlib
import json
import os
import re
from pathlib import Path

from gooplib import GoopError
from gooplib.exports import (EXPORT_ROLES, block_texts,
                             validate_export_words, validate_pairs)
from gooplib.graph_delivery import ROW_LIMIT

SPEC_NAME = 'spec.json'
VCVARS_ENV = 'GOOP_VCVARS'
DEFAULT_PAYLOAD_PATH = 'inputs/candidate.txt'
# Fixed geometry of the output-format strings inside the slot struct.
# These are properties of the vendored C++ source (main.cpp printf text),
# not of any run, so they live here rather than in the spec.
FMT_TICK_SIZE = 64
FMT_SUMMARY_SIZE = 128

# Default output format strings (the re-entrant print channel). Overridable
# per-run via build.formats (owner 2026-10-16: "if they don't come from a
# json, implement that" — all content strings live in JSON). The conversion
# specifiers are a fixed contract with the printf call sites.
DEFAULT_TICK_TEXT = 'tick %5d  alive %3d v %3d  score %d-%d  cp owner %d\n'
DEFAULT_SUMMARY_TEXT = ('SUMMARY ticks=%d seed=%llu alive0=%d alive1=%d '
                        'score0=%d score1=%d owner=%d checksum=%016llx\n')
FMT_SPECIFIER = re.compile(r'%(?:\d+)?(?:\.\d+)?(?:ll|l)?[a-z]')
# The exports-attention string rides a fixed-size field between fmtSummary
# and the hi slots in the format-table struct (owner ruling 2026-10-15).
ATTENTION_SIZE = 128

# Cargo strings (owner ruling 2026-10-15, verbatim: "I don't care about over
# priming. remove the existing exports, go ahead and build the cargo
# strings."). Free-form content: over-priming concerns explicitly waived.
STRING_TEXT_MAX = 4096   # printable ASCII, single line (newlines split rows)
STRINGS_MAX = 99
STRING_NAME = re.compile(r'^[a-z][a-z0-9_]{0,31}$')
# The four probe observations every cell must reproduce (ticks, seed).
# Harness protocol constant, identical for every arm.
PROBES = [(0, 42), (513, 42), (4096, 42), (4096, 7)]


def load_spec(run_dir):
    path = Path(run_dir) / SPEC_NAME
    if not path.is_file():
        raise GoopError(f'missing spec: {path}')
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise GoopError(f'bad spec JSON: {path}: {exc}') from exc


def _require(condition, message):
    if not condition:
        raise GoopError(f'spec validation: {message}')


def _link_block(value, where):
    """An exports/fn_literals block: {'sets', anchor, target, destination}
    (single pair) or {'sets', 'pairs': [pair, ...]} (1-2 pairs, 2026-10-15
    multi-pair doctrine). Normalized to {'sets', 'words'} or
    {'sets', 'pairs'} respectively.
    """
    _require(isinstance(value, dict), f'build.{where} must be an object')
    sets = value.get('sets')
    _require(isinstance(sets, int) and not isinstance(sets, bool)
             and 1 <= sets <= 99,
             f'build.{where}.sets must be an integer in [1, 99]')
    grouped = where == 'fn_literals' and 'links_per_literal' in value
    resource = where == 'fn_literals' and 'resource_carrier' in value
    extra = ({'links_per_literal'} if grouped else set()) | \
            ({'resource_carrier'} if resource else set())
    if resource:
        _require(grouped and value['resource_carrier'] is True,
                 'build.fn_literals.resource_carrier requires grouping and true')
    if grouped:
        _require(type(value['links_per_literal']) is int
                 and value['links_per_literal'] in (2, 4),
                 'build.fn_literals.links_per_literal must be 2 or 4')
    if 'pairs' in value:
        _require(set(value) == {'sets', 'pairs'} | extra,
                 f"build.{where} with 'pairs' has unexpected keys")
        raw_pairs = value['pairs']
        _require(isinstance(raw_pairs, list) and 1 <= len(raw_pairs) <= 3,
                 f'build.{where}.pairs must be a list of 1-3 pair objects')
        for i, pair in enumerate(raw_pairs):
            _require(isinstance(pair, dict) and set(pair) == set(EXPORT_ROLES),
                     f'build.{where}.pairs[{i}] must hold exactly '
                     f'{list(EXPORT_ROLES)}')
        pairs = validate_pairs([{role: pair[role] for role in EXPORT_ROLES}
                                for pair in raw_pairs])
        normalized = {'sets': sets, 'pairs': pairs}
        if grouped:
            normalized['links_per_literal'] = value['links_per_literal']
            block_texts(normalized)  # reject strings too long for one row
        if resource:
            normalized['resource_carrier'] = True
        return normalized
    _require(set(value) == {'sets', *EXPORT_ROLES} | extra,
             f"build.{where} must be {{'sets', *{list(EXPORT_ROLES)}}} or "
             "{'sets', 'pairs'}")
    normalized = {'sets': sets,
                  'words': validate_export_words(
                      {role: value[role] for role in EXPORT_ROLES})}
    if grouped:
        normalized['links_per_literal'] = value['links_per_literal']
        block_texts(normalized)  # reject strings too long for one row
    if resource:
        normalized['resource_carrier'] = True
    return normalized


def _strings_block(value):
    """A build.strings block: the cargo strings (owner ruling 2026-10-15).

    Each entry is exactly {'name', 'text'}: a unique C-identifier-safe
    name (it becomes bramble_str_<name> in the emitted source) and a
    printable-ASCII single-line text — newlines are refused because the
    strings channel ([\x20-\x7e]{5,}) would split the string into
    separate rows.
    """
    _require(isinstance(value, list) and 1 <= len(value) <= STRINGS_MAX,
             f'build.strings must be a list of 1-{STRINGS_MAX} entries')
    entries = []
    for i, entry in enumerate(value):
        _require(isinstance(entry, dict) and set(entry) == {'name', 'text'},
                 f"build.strings[{i}] must hold exactly 'name' and 'text'")
        name, text = entry['name'], entry['text']
        _require(isinstance(name, str) and STRING_NAME.match(name),
                 f'build.strings[{i}].name {name!r} must match '
                 "'^[a-z][a-z0-9_]{0,31}$' (it becomes a C identifier)")
        _require(isinstance(text, str) and text
                 and len(text) <= STRING_TEXT_MAX
                 and all(0x20 <= ord(ch) <= 0x7E for ch in text),
                 f'build.strings[{i}].text must be printable ASCII, '
                 f'1-{STRING_TEXT_MAX} chars, single line')
        entries.append({'name': name, 'text': text})
    names = [entry['name'] for entry in entries]
    _require(len(set(names)) == len(names),
             f'build.strings names must be unique: {sorted(names)}')
    return entries


def _formats(raw):
    """A build.formats block: {'tick', 'summary'} custom output format
    strings (owner 2026-10-16: content strings come from JSON, hand-editable
    per run). Printable ASCII with exactly one trailing newline, sized to
    the struct fields, and the printf conversion specifiers must match the
    defaults exactly \u2014 the call sites pass a fixed argument list, so a
    dropped or reordered specifier reads garbage off the stack.
    """
    _require(isinstance(raw, dict) and set(raw) == {'tick', 'summary'},
             "build.formats must hold exactly 'tick' and 'summary'")
    out = {}
    for key, default, size in (('tick', DEFAULT_TICK_TEXT, FMT_TICK_SIZE),
                               ('summary', DEFAULT_SUMMARY_TEXT, FMT_SUMMARY_SIZE)):
        text = raw[key]
        _require(isinstance(text, str) and text.endswith('\n')
                 and '\n' not in text[:-1]
                 and all(0x20 <= ord(ch) <= 0x7E for ch in text[:-1])
                 and len(text) <= size - 1,
                 f'build.formats.{key} must be single-line printable ASCII '
                 f'with one trailing newline, <= {size - 1} chars')
        _require(FMT_SPECIFIER.findall(text) == FMT_SPECIFIER.findall(default),
                 f'build.formats.{key} must keep the exact conversion '
                 f'specifiers {FMT_SPECIFIER.findall(default)} (the printf '
                 'call site passes a fixed argument list)')
        out[key] = text
    return out


def _metadata_lines(raw, doses, slots, name):
    if raw is None:
        return None
    _require(isinstance(raw, dict) and set(raw) == set(doses),
             f'build.{name} must map every cell to line indices or null')
    for cell, indices in raw.items():
        if indices is None:
            continue
        _require(doses[cell] > 0,
                 f'build.{name}.{cell} must be null for zero-dose controls')
        _require(isinstance(indices, list) and bool(indices)
                 and all(type(index) is int and 0 <= index < slots
                         for index in indices)
                 and len(set(indices)) == len(indices),
                 f'build.{name}.{cell} needs distinct candidate-line indices')
    return {cell: list(indices) if indices is not None else None
            for cell, indices in raw.items()}


def build_section(spec):
    """Validate spec['build'] (+ payload pin) and return a normalized dict."""
    _require(isinstance(spec, dict), 'spec must be a JSON object')
    payload = spec.get('payload')
    _require(isinstance(payload, dict), 'missing payload section')
    sha = payload.get('sha256')
    _require(isinstance(sha, str) and len(sha) == 64
             and all(c in '0123456789abcdef' for c in sha),
             'payload.sha256 must be 64 lowercase hex chars')
    payload_path = payload.get('path', DEFAULT_PAYLOAD_PATH)
    _require(isinstance(payload_path, str) and payload_path
             and not Path(payload_path).is_absolute(),
             'payload.path must be a relative path inside the run dir')

    build = spec.get('build')
    _require(isinstance(build, dict), 'missing build section')
    slots = build.get('slots')
    _require(isinstance(slots, int) and not isinstance(slots, bool)
             and slots >= 2 and slots % 2 == 0,
             'build.slots must be an even integer >= 2')
    slot_size = build.get('slot_size')
    _require(isinstance(slot_size, int) and not isinstance(slot_size, bool)
             and slot_size >= 16,
             'build.slot_size must be an integer >= 16')
    doses = build.get('doses')
    _require(isinstance(doses, dict) and len(doses) == 2,
             'build.doses must name exactly two cells')
    for cell, dose in doses.items():
        _require(isinstance(cell, str) and cell.isidentifier(),
                 f'cell name {cell!r} must be a plain identifier')
        _require(isinstance(dose, int) and not isinstance(dose, bool)
                 and 0 <= dose <= slots,
                 f'build.doses.{cell} must be an integer in [0, slots]')
    format_table = build.get('format_table', False)
    config_tags = build.get('config_tags', False)
    _require(isinstance(format_table, bool) and isinstance(config_tags, bool),
             'build.format_table / build.config_tags must be booleans')
    # The exports block is deleted (owner ruling 2026-10-15, verbatim: "I
    # don't care about over priming. remove the existing exports, go ahead
    # and build the cargo strings.") — refused, not ignored, so a stale
    # spec fails loudly instead of silently building without its arm.
    _require('exports' not in build,
             'build.exports is deleted (2026-10-15 ruling): the fake export '
             'table never landed (0 visible in five consecutive completed '
             'cells); use build.strings (cargo strings)')
    fn_literals = build.get('fn_literals')
    if fn_literals is not None:
        fn_literals = _link_block(fn_literals, 'fn_literals')
    attention = build.get('attention')
    if attention is not None:
        _require(isinstance(attention, str) and attention
                 and all(0x20 <= ord(ch) <= 0x7E for ch in attention)
                 and len(attention) <= ATTENTION_SIZE - 1,
                 f'build.attention must be printable ASCII, '
                 f'1-{ATTENTION_SIZE - 1} chars')
        _require(format_table,
                 'build.attention requires format_table (it rides the '
                 'format-table struct after the SUMMARY format)')
    strings = build.get('strings')
    if strings is not None:
        strings = _strings_block(strings)
    formats = build.get('formats')
    if formats is not None:
        formats = _formats(formats)
    startup_format = build.get('startup_format')
    if startup_format is not None:
        _require(isinstance(startup_format, str)
                 and startup_format.endswith('\n')
                 and len(startup_format) <= 2500
                 and all(ch == '\n' or (0x20 <= ord(ch) <= 0x7E and ch != '%')
                         for ch in startup_format),
                 'build.startup_format must be printable ASCII lines ending '
                 'in newline, <=2500 chars, with no printf conversions')
        rows = startup_format[:-1].split('\n')
        _require(all(row and len(row) <= ROW_LIMIT for row in rows)
                 if len(rows) > 1 else bool(rows[0]),
                 f'build.startup_format multiline rows must be 1-{ROW_LIMIT} chars')
    startup_zero_probe = build.get('startup_zero_probe', False)
    _require(isinstance(startup_zero_probe, bool)
             and (not startup_zero_probe or startup_format is not None),
             'build.startup_zero_probe requires startup_format and a boolean')
    dos_stub = _metadata_lines(build.get('dos_stub'), doses, slots, 'dos_stub')
    pdb_lines = _metadata_lines(build.get('pdb_lines'), doses, slots, 'pdb_lines')
    if dos_stub and pdb_lines:
        for cell in doses:
            if dos_stub[cell] and pdb_lines[cell]:
                _require(not set(dos_stub[cell]) & set(pdb_lines[cell]),
                         f'build metadata line selections overlap in {cell}')
    if format_table:
        # The interleaved-chain check demands max_gap <= slot_size; the
        # summary->hi gap is FMT_SUMMARY_SIZE (+ ATTENTION_SIZE when the
        # attention field is present). Refuse here, not post-compile.
        minimum = FMT_SUMMARY_SIZE + (ATTENTION_SIZE if attention else 0)
        _require(slot_size >= minimum,
                 f'build.slot_size must be >= {minimum} with format_table'
                 f'{" and attention" if attention else ""} (the '
                 f'summary->hi chain gap is {minimum} bytes)')
    return {'slots': slots, 'slot_size': slot_size, 'doses': dict(doses),
            'format_table': format_table, 'config_tags': config_tags,
            'strings': strings, 'fn_literals': fn_literals,
            'attention': attention, 'formats': formats,
            'startup_format': startup_format,
            'startup_zero_probe': startup_zero_probe,
            'dos_stub': dos_stub, 'pdb_lines': pdb_lines,
            'payload_path': payload_path, 'payload_sha256': sha}


def _pdb_component(line):
    prefix = line[:88].decode('ascii')
    last_link = prefix.rfind(')')
    return (prefix[:last_link + 1] if last_link >= 0 else prefix.rsplit(' ', 1)[0]).rstrip('. ')


def metadata_texts(build, lines, cell):
    """Resolve metadata references from the ONE pinned candidate; no prose copies."""
    stub_refs = build['dos_stub'][cell] if build['dos_stub'] else None
    pdb_refs = build['pdb_lines'][cell] if build['pdb_lines'] else None
    try:
        stub = ' '.join(lines[index].decode('ascii') for index in stub_refs) if stub_refs else None
        # Keep complete LINK inserts within short, legible path components.
        components = [_pdb_component(lines[index]) for index in pdb_refs] if pdb_refs else []
    except UnicodeDecodeError as exc:
        raise GoopError('metadata-selected candidate lines must be ASCII') from exc
    if any(not part or any(char in part for char in '\\/:*?"<>|')
           for part in components):
        raise GoopError('candidate PDB directory fragment is not path-safe')
    pdb = '\\'.join([*components, 'debug.pdb']) if components else None
    return stub, pdb


def candidate_path(run_dir, build):
    path = Path(run_dir) / build['payload_path']
    if not path.is_file():
        raise GoopError(f'missing candidate payload: {path}')
    return path


def candidate_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def payload_lines(path, build):
    """Candidate text -> one payload line per slot (CRLF-tolerant).

    Empty lines are dropped (a slot is either an occupied content line or
    zero-filled; an empty line is not addressable content). The surviving
    line count must equal build.slots exactly.
    """
    raw = Path(path).read_bytes().split(b'\n')
    lines = [line[:-1] if line.endswith(b'\r') else line for line in raw]
    lines = [line for line in lines if line]
    if len(lines) != build['slots']:
        raise GoopError(
            f'candidate has {len(lines)} nonempty lines, spec says '
            f'{build["slots"]} slots; they must match exactly')
    too_long = [index for index, line in enumerate(lines)
                if len(line) >= build['slot_size']]
    if too_long:
        raise GoopError(
            f'candidate lines {too_long[:5]} exceed slot_size '
            f'{build["slot_size"]} (need room for NUL padding)')
    return lines


def vcvars_path():
    """The MSVC toolchain pin: GOOP_VCVARS must point at vcvars64.bat."""
    pinned = os.environ.get(VCVARS_ENV)
    if not pinned:
        raise GoopError(
            f'MSVC toolchain not pinned: set {VCVARS_ENV} to the full path '
            'of vcvars64.bat for this machine')
    path = Path(pinned)
    if not path.is_file():
        raise GoopError(f'{VCVARS_ENV} pinned to missing file: {path}')
    return path
