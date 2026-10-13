"""goop_build — build + pack + verify a run's native pair (utility 2 of 4).

Usage:
    python tools/goop_build.py build  <run_dir>   # native pair -> <run_dir>/unpacked
    python tools/goop_build.py pack   <run_dir>   # UPX pack -> <run_dir>/cells + private
    python tools/goop_build.py verify <run_dir>   # preflight -> <run_dir>/PREFLIGHT.json
    python tools/goop_build.py all    <run_dir>   # the three steps in order

All build parameters come from <run_dir>/spec.json (see gooplib/specs.py for
the schema); the MSVC toolchain is the GOOP_VCVARS environment pin. Steps
refuse to overwrite existing outputs. Exit status is 0 on success, 2 on any
refusal or integrity failure.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gooplib import GoopError
from gooplib.native_build import build_pair
from gooplib.native_pack import pack_pair
from gooplib.preflight import preflight
from gooplib.specs import load_spec


def _print_checks(title, checks):
    print(title)
    for name, ok in checks.items():
        print(f'  {"PASS" if ok else "FAIL"}  {name}')


def _build(run_dir, spec):
    manifest = build_pair(run_dir, spec)
    _print_checks('native pair checks:', manifest['checks'])
    for cell, data in manifest['cells'].items():
        print(f'  {cell}: dose {data["dose"]}, {data["bytes"]} bytes, sha {data["sha256"][:16]}...')
    return manifest


def _pack(run_dir, spec):
    manifest = pack_pair(run_dir, spec)
    _print_checks('packed pair checks:', manifest['checks'])
    for cell, data in manifest['cells'].items():
        print(f'  {cell}: {data["source_bytes"]} -> {data["packed_bytes"]} bytes, '
              f'strings {data["strings_total"]}, needles present '
              f'{data["payload_needles_present"]}/{data["payload_needles"]}')
    return manifest


def _verify(run_dir, spec):
    record = preflight(run_dir)
    print(f'preflight OK: {record["slot_count"]} slots, doses {record["doses"]}, '
          f'pair isolation live-verified')
    print(f'  wrote {Path(run_dir) / "PREFLIGHT.json"} (x-mode)')
    return record


STEPS = {'build': _build, 'pack': _pack, 'verify': _verify}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('step', choices=[*STEPS, 'all'],
                        help='which step to run; "all" runs build, pack, verify in order')
    parser.add_argument('run_dir', type=Path, help='run directory containing spec.json')
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    try:
        spec = load_spec(run_dir)
        names = list(STEPS) if args.step == 'all' else [args.step]
        for name in names:
            print(f'== goop_build {name} {run_dir}')
            STEPS[name](run_dir, spec)
    except GoopError as exc:
        print(f'REFUSED: {exc}', file=sys.stderr)
        return 2
    except FileExistsError as exc:
        print(f'REFUSED: output already exists ({exc.filename}); steps never overwrite',
              file=sys.stderr)
        return 2
    print(json.dumps({'step': args.step, 'run_dir': str(run_dir), 'ok': True}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
