"""UPX-pack a built native pair: <run_dir>/unpacked -> <run_dir> top level.

Adapted from the archived packer, made generic and self-contained: the UPX
binary is the bundled tools/upx/upx.exe, and the "payload statically hidden"
check uses needles derived from the run's own candidate payload instead of a
fixed corpus token.

Verifies UPX integrity, probe outputs, hidden long candidate lines, and
optional exposed RCDATA bundles. Writes private/manifest.json; refuses to
overwrite.
"""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pefile

from gooplib import UPX, GoopError
from gooplib.pe_debug import add_pdb_hint
from gooplib.literal_resources import (keep_resource_option, resources_match,
                                       unique_bundles)
from gooplib.specs import (PROBES, build_section, candidate_path,
                           metadata_texts, payload_lines)

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
    resources = unique_bundles(build['fn_literals']) if build['fn_literals'] else []
    run_dir = Path(run_dir).resolve()
    if not UPX.is_file():
        raise GoopError(f'UPX not bundled: {UPX}')
    source_run = run_dir / 'unpacked'
    source_manifest_path = source_run / 'private' / 'manifest.json'
    if not source_manifest_path.is_file():
        raise GoopError(f'no unpacked pair to pack: {source_manifest_path}')
    source_manifest = json.loads(source_manifest_path.read_text(encoding='utf-8'))
    candidate = candidate_path(run_dir, build)
    lines = payload_lines(candidate, build)
    needles = [(index, line) for index, line in enumerate(lines)
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
        upx_args = ([keep_resource_option(len(resources))] if resources else []) + \
                   ['-o', str(packed), str(unpacked_copy)]
        result = _run_upx(upx_args)
        if result.returncode:
            raise GoopError(f'UPX failed for {cell}: {result.stdout} {result.stderr}')
        test = _run_upx(['-t', str(packed)])
        if test.returncode:
            raise GoopError(f'UPX integrity test failed for {cell}')
        stub_text, pdb_hint = metadata_texts(build, lines, cell)
        delivered = public / 'target.exe'
        if pdb_hint:
            delivered.write_bytes(add_pdb_hint(packed.read_bytes(), pdb_hint))
        else:
            shutil.copyfile(packed, delivered)
        observations = []
        for ticks, seed in PROBES:
            run = subprocess.run([str(delivered), str(ticks), str(seed)],
                                 capture_output=True, text=True, timeout=30)
            if run.returncode:
                raise GoopError(f'packed {cell} smoke run failed')
            observations.append({'ticks': ticks, 'seed': seed, 'stdout': run.stdout})
        binary = delivered.read_bytes()
        pe = pefile.PE(data=binary)
        if stub_text is not None:
            if stub_text.encode('ascii') not in binary[:pe.DOS_HEADER.e_lfanew]:
                raise GoopError(f'{cell}: UPX did not preserve the linked DOS stub')
        sections = [{'name': s.Name.rstrip(b'\0').decode(errors='replace'),
                     'va': hex(pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress),
                     'virtual_size': s.Misc_VirtualSize,
                     'raw_size': s.SizeOfRawData,
                     'flags': hex(s.Characteristics)} for s in pe.sections]
        imports = [getattr(d, 'dll', b'').decode(errors='replace')
                   for d in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]
        strings = re.findall(rb'[\x20-\x7e]{5,}', binary)
        stub_refs = set((build['dos_stub'] or {}).get(cell) or [])
        pdb_refs = set((build['pdb_lines'] or {}).get(cell) or [])
        references = stub_refs | pdb_refs
        visible_lines = {lines[index] for index in stub_refs}
        hidden_needles = {line for _, line in needles if line not in visible_lines}
        needles_present = sum(line in binary for line in hidden_needles)
        metadata_present = (all(line in binary for line in visible_lines)
                            and (not pdb_hint or pdb_hint.encode('ascii') in binary))
        debug_present = len(getattr(pe, 'DIRECTORY_ENTRY_DEBUG', [])) == bool(pdb_hint)
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
            'payload_needles': len(hidden_needles),
            'payload_needles_present': needles_present,
            'metadata_lines': sorted(references),
            'metadata_lines_present': metadata_present,
            'resource_bundles_exposed': resources_match(pe, resources)
            if resources else None,
            'debug_directory_expected': bool(pdb_hint),
            'debug_directory_matches': debug_present,
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
    manifest['checks']['metadata_delivered_as_declared'] = all(
        manifest['cells'][cell]['metadata_lines_present']
        and manifest['cells'][cell]['debug_directory_matches']
        for cell in build['doses'])
    if resources:
        manifest['checks']['resource_bundles_exposed'] = all(
            manifest['cells'][cell]['resource_bundles_exposed']
            for cell in build['doses'])
    (run_dir / 'private' / 'manifest.json').write_text(
        json.dumps(manifest, indent=2), encoding='utf-8')
    if not all(manifest['checks'].values()):
        raise GoopError(f'Pack checks failed; inspect {run_dir / "private/manifest.json"}')
    return manifest
