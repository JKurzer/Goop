"""Generic preflight for a packed goop run: read-only checks; exclusively
creates <run_dir>/PREFLIGHT.json ('x' mode — refuses if it already exists).

Pattern ported from the archived frozen-run verifier, made generic: slot
count, slot size, doses, and the frozen candidate hash all come from the
run's spec.json; the helper reference is the bundled goop copy of
native_inspect.py. Verified live:

- candidate bytes hash to spec.payload.sha256; line geometry matches the
  build section (one line per slot, each shorter than slot_size)
- both manifests exist and their checks are green
- per-slot bytes at manifest offsets equal the frozen candidate lines
  (NUL-padded; zero-filled past the cell dose)
- packed and unpacked cell hashes match both manifests
- pair isolation recomputed live: executable sections identical across cells
- reports/ absent (never retry a cell), PREREG.md present (registered first)

(The shipped-helper byte check died with the helper, 2026-10-16: the
bundled pe_inspect.py was destroyed by owner ruling - real RE tooling
replaces it, and nothing is shipped beside target.exe anymore.)

The runner and prompt are the fire utility's domain and are not checked here.
"""
import hashlib
import json
from pathlib import Path

import pefile

from gooplib import GoopError
from gooplib.specs import (build_section, candidate_digest, candidate_path,
                           load_spec, payload_lines)

REVIEWER = 'code-puppy-48cac1'
PREREG_NAME = 'PREREG.md'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def executable_sections(path):
    with pefile.PE(str(path)) as image:
        return [(s.Name, s.VirtualAddress, s.get_data()) for s in image.sections
                if s.Characteristics & 0x20000000]


def require(condition, message):
    if not condition:
        raise GoopError(f'preflight: {message}')


def preflight(run_dir):
    """Run all preflight checks on <run_dir>; write PREFLIGHT.json ('x').

    Returns the preflight record dict. Raises GoopError on the first failed
    check; writes nothing on failure.
    """
    run_dir = Path(run_dir).resolve()
    spec = load_spec(run_dir)
    build = build_section(spec)
    candidate = candidate_path(run_dir, build)
    require(candidate_digest(candidate) == build['payload_sha256'],
            'frozen candidate hash changed vs spec.payload.sha256')
    lines = payload_lines(candidate, build)  # count + length already enforced

    unpacked_path = run_dir / 'unpacked' / 'private' / 'manifest.json'
    packed_path = run_dir / 'private' / 'manifest.json'
    require(unpacked_path.is_file(), f'missing {unpacked_path}')
    require(packed_path.is_file(), f'missing {packed_path}')
    unpacked = json.loads(unpacked_path.read_text(encoding='utf-8'))
    packed = json.loads(packed_path.read_text(encoding='utf-8'))
    require(all(unpacked['checks'].values()), 'native builder check failed')
    require(all(packed['checks'].values()), 'packed builder check failed')
    require(not (run_dir / 'reports').exists(),
            'reports/ already exists; never retry a cell')
    prereg = run_dir / PREREG_NAME
    require(prereg.is_file() and prereg.stat().st_size > 0,
            f'{PREREG_NAME} must be registered before fire')

    cells = list(build['doses'])
    sections = {}
    record = {'reviewer': REVIEWER,
              'candidate_sha256': build['payload_sha256'],
              'slot_count': build['slots'], 'slot_size': build['slot_size'],
              'doses': dict(build['doses']),
              'native_checks': unpacked['checks'],
              'packed_checks': packed['checks'], 'cells': {}}
    for cell, dose in build['doses'].items():
        binary = run_dir / 'unpacked' / 'cells' / cell / 'target.exe'
        raw = binary.read_bytes()
        require(unpacked['cells'][cell]['dose'] == dose, f'{cell}: wrong occupancy')
        for index, line in enumerate(lines):
            slot = unpacked['cells'][cell]['slots'][str(index)]
            expected = (line if index < dose else b'').ljust(build['slot_size'], b'\0')
            window = raw[slot['offset']:slot['offset'] + build['slot_size']]
            require(window == expected,
                    f'{cell}: slot {index} bytes or padding mismatch')
        sections[cell] = executable_sections(binary)
        fired = run_dir / 'cells' / cell / 'target.exe'
        require(digest(fired) == packed['cells'][cell]['packed_sha256'],
                f'{cell}: packed hash mismatch vs packed manifest')
        require(digest(binary) == packed['cells'][cell]['source_sha256'],
                f'{cell}: unpacked hash mismatch vs packed manifest')
        require(digest(binary) == unpacked['cells'][cell]['sha256'],
                f'{cell}: unpacked hash mismatch vs native manifest')
        record['cells'][cell] = {
            'dose': dose, 'slot_size': build['slot_size'],
            'slot_bytes_verified': True,
            'packed_sha256': digest(fired), 'unpacked_sha256': digest(binary),
            'packed_bytes': fired.stat().st_size,
            'observations_match_source':
                packed['cells'][cell]['observations_match_source']}
    first, second = cells
    require(sections[first] == sections[second],
            'pair isolation: executable sections differ between cells')
    record['pair_isolation_executable_sections'] = True
    with (run_dir / 'PREFLIGHT.json').open('x', encoding='utf-8') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    return record
