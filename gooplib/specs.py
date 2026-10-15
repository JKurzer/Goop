"""spec.json loading and validation for the build+pack+verify utility.

The build section of a run's spec.json is the ONLY source of build
parameters (goop rule 2: zero magic numbers in utilities):

    {
      "arm": "example-arm",
      "payload": {"path": "inputs/candidate.txt", "sha256": "<64 hex>"},
      "build": {
        "slots": 20,
        "slot_size": 256,
        "doses": {"k7": 5, "m2": 10},
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
                shape as exports; N x 18 named const char arrays carrying
                the LINKs as plain bigram strings, each referenced inline
                inside main's tick loop and checksum loop (volatile reads
                into the inert sink; output unchanged).

The MSVC toolchain is an environment pin: GOOP_VCVARS must name the
vcvars64.bat to use; the utility asserts the pinned file exists.
"""
import hashlib
import json
import os
from pathlib import Path

from gooplib import GoopError
from gooplib.exports import (EXPORT_ROLES, validate_export_words,
                             validate_pairs)

SPEC_NAME = 'spec.json'
VCVARS_ENV = 'GOOP_VCVARS'
DEFAULT_PAYLOAD_PATH = 'inputs/candidate.txt'
# Fixed geometry of the output-format strings inside the slot struct.
# These are properties of the vendored C++ source (main.cpp printf text),
# not of any run, so they live here rather than in the spec.
FMT_TICK_SIZE = 64
FMT_SUMMARY_SIZE = 128
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
    if 'pairs' in value:
        _require(set(value) == {'sets', 'pairs'},
                 f"build.{where} with 'pairs' must hold only 'sets' and 'pairs'")
        raw_pairs = value['pairs']
        _require(isinstance(raw_pairs, list) and 1 <= len(raw_pairs) <= 2,
                 f'build.{where}.pairs must be a list of 1-2 pair objects')
        for i, pair in enumerate(raw_pairs):
            _require(isinstance(pair, dict) and set(pair) == set(EXPORT_ROLES),
                     f'build.{where}.pairs[{i}] must hold exactly '
                     f'{list(EXPORT_ROLES)}')
        pairs = validate_pairs([{role: pair[role] for role in EXPORT_ROLES}
                                for pair in raw_pairs])
        return {'sets': sets, 'pairs': pairs}
    _require(set(value) == {'sets', *EXPORT_ROLES},
             f"build.{where} must be {{'sets', *{list(EXPORT_ROLES)}}} or "
             "{'sets', 'pairs'}")
    return {'sets': sets,
            'words': validate_export_words(
                {role: value[role] for role in EXPORT_ROLES})}


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
    exports = build.get('exports')
    if exports is not None:
        exports = _link_block(exports, 'exports')
    fn_literals = build.get('fn_literals')
    if fn_literals is not None:
        fn_literals = _link_block(fn_literals, 'fn_literals')
    attention = build.get('attention')
    if attention is not None:
        _require(isinstance(attention, str) and attention
                 and all(0x20 <= ord(ch) <= 0x7E for ch in attention)
                 and len(attention) <= 127,
                 'build.attention must be printable ASCII, 1-127 chars')
        _require(format_table,
                 'build.attention requires format_table (it rides the '
                 'format-table struct after the SUMMARY format)')
    return {'slots': slots, 'slot_size': slot_size, 'doses': dict(doses),
            'format_table': format_table, 'config_tags': config_tags,
            'exports': exports, 'fn_literals': fn_literals,
            'attention': attention,
            'payload_path': payload_path, 'payload_sha256': sha}


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
