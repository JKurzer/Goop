"""UPX-pack a built native pair: <run_dir>/unpacked -> <run_dir> top level.

Adapted from the archived packer, made generic and self-contained: the UPX
binary is the bundled tools/upx/upx.exe, and the "payload statically hidden"
check uses needles derived from the run's own candidate payload instead of a
fixed corpus token.

Verifies: UPX integrity test, probe outputs byte-identical to the unpacked
manifest observations, payload needles statically hidden, helper bundled
beside each packed cell. Writes private/manifest.json; refuses to overwrite.
"""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pefile

from gooplib import HELPER, UPX, GoopError
from gooplib.specs import PROBES, build_section, candidate_path, payload_lines

# A payload line must be at least this long to serve as a hiding needle:
# short strings can survive compression by coincidence, so they prove nothing.
NEEDLE_MIN = 16


def _run_upx(args):
    result = subprocess.run([str(UPX), '-q', *args],
                            capture_output=True, text=True, timeout=120)
    return result


def pack_pair(run_dir, spec):
    """Pack the unpacked pair in <run_dir>; writes cells/ + private/.

    Returns the packed manifest dict; also written to private/manifest.json.
    Raises GoopError on refusal (outputs exist) or integrity failure.
    """
    build = build_section(spec)
    run_dir = Path(run_dir).resolve()
    if not UPX.is_file():
        raise GoopError(f'UPX not bundled: {UPX}')
    source_run = run_dir / 'unpacked'
    source_manifest_path = source_run / 'private' / 'manifest.json'
    if not source_manifest_path.is_file():
        raise GoopError(f'no unpacked pair to pack: {source_manifest_path}')
    source_manifest = json.loads(source_manifest_path.read_text(encoding='utf-8'))
    candidate = candidate_path(run_dir, build)
    needles = [line for line in payload_lines(candidate, build)
               if len(line) >= NEEDLE_MIN]
    # x-mode refusal: create the output anchors exclusively.
    (run_dir / 'private').mkdir(parents=True, exist_ok=False)
    (run_dir / 'cells').mkdir(exist_ok=False)
    manifest = {'source_run': source_run.name, 'upx': str(UPX),
                'cells': {}, 'checks': {}}
    for cell in build['doses']:
        private = run_dir / 'private' / cell
        public = run_dir / 'cells' / cell
        private.mkdir(parents=True)
        public.mkdir(parents=True)
        source = source_run / 'cells' / cell / 'target.exe'
        unpacked_copy = private / 'target-unpacked.exe'
        shutil.copyfile(source, unpacked_copy)
        packed = private / 'target-packed.exe'
        upx_args = ['-o', str(packed), str(unpacked_copy)]
        result = _run_upx(upx_args)
        if result.returncode:
            raise GoopError(f'UPX failed for {cell}: {result.stdout} {result.stderr}')
        test = _run_upx(['-t', str(packed)])
        if test.returncode:
            raise GoopError(f'UPX integrity test failed for {cell}')
        shutil.copyfile(packed, public / 'target.exe')
        shutil.copyfile(HELPER, public / 'pe_inspect.py')
        observations = []
        for ticks, seed in PROBES:
            run = subprocess.run([str(public / 'target.exe'), str(ticks), str(seed)],
                                 capture_output=True, text=True, timeout=30)
            if run.returncode:
                raise GoopError(f'packed {cell} smoke run failed')
            observations.append({'ticks': ticks, 'seed': seed, 'stdout': run.stdout})
        binary = (public / 'target.exe').read_bytes()
        pe = pefile.PE(data=binary)
        sections = [{'name': s.Name.rstrip(b'\0').decode(errors='replace'),
                     'va': hex(pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress),
                     'virtual_size': s.Misc_VirtualSize,
                     'raw_size': s.SizeOfRawData,
                     'flags': hex(s.Characteristics)} for s in pe.sections]
        imports = [getattr(d, 'dll', b'').decode(errors='replace')
                   for d in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]
        strings = re.findall(rb'[\x20-\x7e]{5,}', binary)
        needles_present = sum(needle in binary for needle in needles)
        source_bytes = source.read_bytes()
        manifest['cells'][cell] = {
            'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
            'packed_sha256': hashlib.sha256(binary).hexdigest(),
            'source_bytes': len(source_bytes),
            'packed_bytes': len(binary),
            'entry_va': hex(pe.OPTIONAL_HEADER.ImageBase
                            + pe.OPTIONAL_HEADER.AddressOfEntryPoint),
            'sections': sections, 'import_dlls': imports,
            'strings_total': len(strings),
            'payload_needles': len(needles),
            'payload_needles_present': needles_present,
            'observations': observations,
            'observations_match_source': (
                observations == source_manifest['cells'][cell]['observations'])}
        (private / 'upx.log').write_text(
            result.stdout + result.stderr + test.stdout + test.stderr,
            encoding='utf-8')
    manifest['checks']['observations_identical_all'] = all(
        manifest['cells'][cell]['observations_match_source'] for cell in build['doses'])
    manifest['checks']['payload_statically_hidden'] = all(
        manifest['cells'][cell]['payload_needles_present'] == 0
        for cell in build['doses'])
    (run_dir / 'private' / 'manifest.json').write_text(
        json.dumps(manifest, indent=2), encoding='utf-8')
    if not all(manifest['checks'].values()):
        raise GoopError(f'Pack checks failed; inspect {run_dir / "private/manifest.json"}')
    return manifest
