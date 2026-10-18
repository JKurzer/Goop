"""Stage native PE bytes unchanged for delivery; verify paired smoke output.

The staged file is deliberately uncompressed. A byte present in the PE is
not necessarily a byte encountered in an analyst's saved tool return.
Refuses to overwrite completed or partially staged runs.
"""
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pefile

from gooplib import GoopError
from gooplib.literal_resources import resources_match, unique_bundles
from gooplib.specs import (PROBES, build_section, candidate_path,
                           metadata_texts, payload_lines)

NEEDLE_MIN = 16


def stage_pair(run_dir, spec):
    """Copy the built pair into cells/ without changing any executable bytes."""
    build = build_section(spec)
    resources = unique_bundles(build['fn_literals']) if build['fn_literals'] else []
    run_dir = Path(run_dir).resolve()
    source_run = run_dir / 'unpacked'
    source_manifest_path = source_run / 'private' / 'manifest.json'
    if not source_manifest_path.is_file():
        raise GoopError(f'no unpacked pair to stage: {source_manifest_path}')
    source_manifest = json.loads(source_manifest_path.read_text(encoding='utf-8'))
    candidate = candidate_path(run_dir, build)
    lines = payload_lines(candidate, build)
    if any((build['pdb_lines'] or {}).get(cell) for cell in build['doses']):
        raise GoopError('PDB-line injection is not supported by direct staging; '
                        'omit build.pdb_lines in direct-delivery arms')
    needles = {line for line in lines if len(line) >= NEEDLE_MIN}
    graph = next((entry['text'].encode('ascii') for entry in (build['strings'] or [])
                  if entry['name'] == 'trigram_sets'), None)
    # x-mode refusal: create the output anchors exclusively.
    (run_dir / 'private').mkdir(parents=True, exist_ok=False)
    (run_dir / 'cells').mkdir(exist_ok=False)
    manifest = {'source_run': source_run.name, 'delivery_method': 'native-copy',
                'cells': {}, 'checks': {}}
    for cell in build['doses']:
        private = run_dir / 'private' / cell
        public = run_dir / 'cells' / cell
        private.mkdir(parents=True)
        public.mkdir(parents=True)
        source = source_run / 'cells' / cell / 'target.exe'
        stub_text, _ = metadata_texts(build, lines, cell)
        delivered = public / 'target.exe'
        shutil.copyfile(source, delivered)
        observations = []
        for ticks, seed in PROBES:
            run = subprocess.run([str(delivered), str(ticks), str(seed)],
                                 capture_output=True, text=True, timeout=30)
            if run.returncode:
                raise GoopError(f'staged {cell} smoke run failed')
            observations.append({'ticks': ticks, 'seed': seed, 'stdout': run.stdout})
        binary = delivered.read_bytes()
        pe = pefile.PE(data=binary)
        if stub_text is not None:
            if stub_text.encode('ascii') not in binary[:pe.DOS_HEADER.e_lfanew]:
                raise GoopError(f'{cell}: linked DOS stub changed during staging')
        sections = [{'name': s.Name.rstrip(b'\0').decode(errors='replace'),
                     'va': hex(pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress),
                     'virtual_size': s.Misc_VirtualSize,
                     'raw_size': s.SizeOfRawData,
                     'flags': hex(s.Characteristics)} for s in pe.sections]
        imports = [getattr(d, 'dll', b'').decode(errors='replace')
                   for d in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]
        strings = re.findall(rb'[\x20-\x7e]{5,}', binary)
        stub_refs = set((build['dos_stub'] or {}).get(cell) or [])
        visible_lines = {lines[index] for index in stub_refs}
        metadata_present = all(line in binary for line in visible_lines)
        needles_present = sum(line in binary for line in needles)
        source_bytes = source.read_bytes()
        manifest['cells'][cell] = {
            'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
            # Legacy manifest key: downstream tools mean *delivered* bytes.
            'packed_sha256': hashlib.sha256(binary).hexdigest(),
            'source_bytes': len(source_bytes),
            'packed_bytes': len(binary),
            'entry_va': hex(pe.OPTIONAL_HEADER.ImageBase
                            + pe.OPTIONAL_HEADER.AddressOfEntryPoint),
            'sections': sections, 'import_dlls': imports,
            'strings_total': len(strings),
            'payload_needles': len(needles),
            'payload_needles_present': needles_present,
            'metadata_lines': sorted(stub_refs),
            'metadata_lines_present': metadata_present,
            'resource_bundles_exposed': resources_match(pe, resources)
            if resources else None,
            'trigram_sets_in_bytes': graph in binary if graph else None,
            'observations': observations,
            'observations_match_source': (
                observations == source_manifest['cells'][cell]['observations'])}
    manifest['checks']['observations_identical_all'] = all(
        manifest['cells'][cell]['observations_match_source'] for cell in build['doses'])
    manifest['checks']['source_bytes_unchanged'] = all(
        manifest['cells'][cell]['source_sha256'] ==
        manifest['cells'][cell]['packed_sha256'] for cell in build['doses'])
    manifest['checks']['metadata_delivered_as_declared'] = all(
        manifest['cells'][cell]['metadata_lines_present'] for cell in build['doses'])
    if resources:
        manifest['checks']['resource_bundles_exposed'] = all(
            manifest['cells'][cell]['resource_bundles_exposed']
            for cell in build['doses'])
    if graph:
        manifest['checks']['trigram_sets_in_bytes'] = all(
            manifest['cells'][cell]['trigram_sets_in_bytes']
            for cell in build['doses'])
    (run_dir / 'private' / 'manifest.json').write_text(
        json.dumps(manifest, indent=2), encoding='utf-8')
    if not all(manifest['checks'].values()):
        raise GoopError(f'Stage checks failed; inspect {run_dir / "private/manifest.json"}')
    return manifest
