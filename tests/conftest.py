"""Pytest scaffolding for the build+pack+verify utility.

Runs under bramble's venv python (pefile/capstone live there); pytest itself
is staged goop-side via PYTHONPATH so the archive stays untouched.

The MSVC toolchain is an environment pin (GOOP_VCVARS). For test sessions on
a machine with a known Visual Studio install, the pin is set from the
well-known path; build-dependent tests skip when no toolchain is pinned.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

GOOP_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP_ROOT))

from gooplib.native_build import build_pair  # noqa: E402
from gooplib.native_pack import pack_pair  # noqa: E402

KNOWN_VCVARS = Path(r'C:\Program Files\Microsoft Visual Studio\18\Community'
                    r'\VC\Auxiliary\Build\vcvars64.bat')
if 'GOOP_VCVARS' not in os.environ and KNOWN_VCVARS.is_file():
    os.environ['GOOP_VCVARS'] = str(KNOWN_VCVARS)


def msvc_available():
    pinned = os.environ.get('GOOP_VCVARS')
    return bool(pinned) and Path(pinned).is_file()


requires_msvc = pytest.mark.skipif(not msvc_available(),
                                   reason='GOOP_VCVARS not pinned to an existing vcvars64.bat')


def synthetic_line(index, length, token='gonkulator'):
    """Deterministic synthetic payload line: unique, needle-bearing, ASCII."""
    head = f'goop-synthetic-line-{index:03d}-needle-{token}-{index:03d}-'
    filler = 'abcdefghij' * ((length - len(head)) // 10 + 1)
    return (head + filler)[:length].encode()


def make_run(base, name, slots, slot_size, doses, line_length,
             format_table=True, config_tags=True, exports=None,
             fn_literals=None):
    """Materialize a complete run dir (spec + candidate + PREREG), unbuilt."""
    run = base / name
    (run / 'inputs').mkdir(parents=True)
    lines = [synthetic_line(i, line_length) for i in range(slots)]
    blob = b'\n'.join(lines) + b'\n'
    (run / 'inputs' / 'candidate.txt').write_bytes(blob)
    build = {'slots': slots, 'slot_size': slot_size,
             'doses': doses, 'format_table': format_table,
             'config_tags': config_tags}
    if exports is not None:
        build['exports'] = exports
    if fn_literals is not None:
        build['fn_literals'] = fn_literals
    spec = {'arm': name,
            'payload': {'path': 'inputs/candidate.txt',
                        'sha256': hashlib.sha256(blob).hexdigest()},
            'build': build}
    (run / 'spec.json').write_text(json.dumps(spec, indent=2), encoding='utf-8')
    (run / 'PREREG.md').write_text('# prereg\nregistered before build.\n',
                                   encoding='utf-8')
    return run, spec


RUN20 = {'slots': 20, 'slot_size': 256, 'doses': {'k7': 5, 'm2': 10},
         'line_length': 120}
RUN120 = {'slots': 120, 'slot_size': 512, 'doses': {'k7': 60, 'm2': 120},
          'line_length': 300}
RUN20X = {'slots': 20, 'slot_size': 256, 'doses': {'k7': 5, 'm2': 10},
          'line_length': 120,
          'exports': {'sets': 2, 'anchor': 'quorlx', 'target': 'vexel',
                      'destination': 'murn'},
          'fn_literals': {'sets': 1, 'anchor': 'quorlx', 'target': 'vexel',
                          'destination': 'murn'}}


def _built_run(tmp_path_factory, name, params):
    base = tmp_path_factory.mktemp('runs')
    run, spec = make_run(base, name, **params)
    unpacked = build_pair(run, spec)
    packed = pack_pair(run, spec)
    return {'run': run, 'spec': spec, 'unpacked': unpacked, 'packed': packed}


@pytest.fixture(scope='session')
def run20(tmp_path_factory):
    if not msvc_available():
        pytest.skip('GOOP_VCVARS not pinned to an existing vcvars64.bat')
    return _built_run(tmp_path_factory, 'arm20', RUN20)


@pytest.fixture(scope='session')
def run120(tmp_path_factory):
    if not msvc_available():
        pytest.skip('GOOP_VCVARS not pinned to an existing vcvars64.bat')
    return _built_run(tmp_path_factory, 'arm120', RUN120)


@pytest.fixture(scope='session')
def run20x(tmp_path_factory):
    if not msvc_available():
        pytest.skip('GOOP_VCVARS not pinned to an existing vcvars64.bat')
    return _built_run(tmp_path_factory, 'arm20x', RUN20X)
