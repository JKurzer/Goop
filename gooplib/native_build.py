"""Build a matched native cell pair from a run spec (spec.json build section).

Adapted from the archived harness builder (2026-10-13 revision), made
generic and self-contained: slot count, slot size, doses, and exposure mode
all come from the spec; C++ sources are vendored in gooplib/native_src; the
MSVC toolchain is the GOOP_VCVARS env pin. No archive paths are consulted.

Exposure model (unchanged from the archive): retained fixed-size data slots
are declared alongside an inert provenance fold executed on the init path
inside main(), so every slot earns a genuine code reference without changing
observable behavior. Volatile loads defeat /O2 compile-time folding; the
fold sink is never printed or branched on, so stdout/exit stay identical.

format_table mode: the two printf literals become named members of one
struct whose declaration order IS the memory order; slots interleave with
the output formats an analyst must read exactly.

config_tags mode: slot pointers are woven into SimConfig. With format_table,
explicit per-slot assignment statements in main() keep every slot LEA inside
the driver-reconstruction window at any slot count (the 2026-10-13 fix:
MSVC outlines the implicit SimConfig ctor at large counts). Without
format_table, the legacy default-member-initializer field naming
bramble_slot_XX is preserved.

The generated C++ symbol prefix stays `bramble_` so the map-file checks and
the archived helper semantics line up one-to-one with the ported code.
"""
import hashlib
import json
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP

from gooplib import HELPER, NATIVE_SRC, GoopError
from gooplib.exports import export_names, names_digest
from gooplib.specs import (FMT_SUMMARY_SIZE, FMT_TICK_SIZE, PROBES,
                           build_section, candidate_digest, candidate_path,
                           payload_lines, vcvars_path)

MODULES = ['entities', 'sim', 'objectives', 'main']
MAIN_ANCHOR = 'int main(int argc, char** argv) {'
SEED_ANCHOR = '    uint64_t seed = (argc > 2) ? std::strtoull(argv[2], nullptr, 10) : 42;'
SIMH_INCLUDE_ANCHOR = '#include "entities.h"'
SIMH_CLOSE_ANCHOR = '    float tickDt = 1.0f / 64.0f;  // 64 Hz fixed tick\n};'
TICK_PRINTF_ANCHOR = 'std::printf("tick %5d  alive %3d v %3d  score %d-%d  cp owner %d\\n",'
SUMMARY_PRINTF_ANCHOR = ('std::printf("SUMMARY ticks=%d seed=%llu alive0=%d alive1=%d '
                         'score0=%d score1=%d "\n                "owner=%d checksum=%016llx\\n",')
# SimConfig scalar signature (arena, skirmish, orbit, speed as float32 LE)
# used to locate the init blob in .rdata during post-build verification.
CONFIG_FLOAT_SIGNATURE = struct.pack('<4f', 48.0, 1.5, 3.0, 6.0)

TICK_TEXT = 'tick %5d  alive %3d v %3d  score %d-%d  cp owner %d\n'
SUMMARY_TEXT = ('SUMMARY ticks=%d seed=%llu alive0=%d alive1=%d score0=%d score1=%d '
                'owner=%d checksum=%016llx\n')


def cstr_literal(data):
    """C++ literal expression embedding data byte-exactly: printable ASCII in
    quoted runs, every other byte as its own \\xNN literal (hex-run safe)."""
    if not data:
        return '""'
    parts = []
    run = []
    for byte in data:
        if byte in (0x22, 0x5C):
            run.append('\\' + chr(byte))
        elif 0x20 <= byte <= 0x7E:
            run.append(chr(byte))
        else:
            if run:
                parts.append('"' + ''.join(run) + '"')
                run = []
            parts.append(f'"\\x{byte:02x}"')
    if run:
        parts.append('"' + ''.join(run) + '"')
    return ' '.join(parts)


def slot_declarations(payloads, dose, slot_size):
    lines = []
    for index in range(len(payloads)):
        data = payloads[index] if index < dose else b''
        lines.extend([
            f'#pragma comment(linker, "/include:bramble_slot_{index:02d}")',
            f'extern "C" const char bramble_slot_{index:02d}[{slot_size}] = {cstr_literal(data)};',
        ])
    return lines


EXPOSURE_PROLOGUE = """// --- exposure arm: retained tag slots, referenced on the init path.
// The fold keeps every slot genuinely referenced for RE traversal (volatile
// loads cannot be compile-time folded). The sink is never printed or branched
// on: output and exit status are unchanged. Inert by design.
volatile uint64_t bramble_prov_sink;

{declarations}
static uint64_t brambleFoldOne(uint64_t acc, const char* tag) {{
    const volatile unsigned char* p =
        reinterpret_cast<const volatile unsigned char*>(tag);
    for (size_t i = 0; i < {slot_size}; ++i) {{
        acc ^= p[i];
        acc *= 1099511628211ull;
    }}
    return acc;
}}

static void brambleProvenanceFold(uint64_t seed) {{
    uint64_t acc = seed ^ 1469598103934665603ull;
{folds}
    bramble_prov_sink = acc;
}}

"""


def inject_exports(main_cpp, names):
    """Fake export set (owner ruling 2026-10-15): no-op exported functions
    whose names carry the canonical LINKs as identifier bigrams. The export
    table is the first thing an analyst reads after imports; every name is
    address-anchored, and /OPT:NOICF keeps the stub addresses distinct.
    Bodies are empty: output and exit status are unchanged. Inert by design.
    """
    block = ('// --- export arm: fake export set. Names carry link pairs; the\n'
             '// bodies are no-ops. Inert.\n'
             'extern "C" {\n'
             + '\n'.join(f'__declspec(dllexport) void {name}() {{}}'
                         for name in names)
             + '\n}\n\n')
    if main_cpp.count(MAIN_ANCHOR) != 1:
        raise GoopError('main.cpp anchor not unique; export injection unsafe')
    return main_cpp.replace(MAIN_ANCHOR, block + MAIN_ANCHOR)


def inject_exposure(main_cpp, payloads, dose, slot_size):
    declarations = slot_declarations(payloads, dose, slot_size)
    folds = [f'    acc = brambleFoldOne(acc, bramble_slot_{index:02d});'
             for index in range(len(payloads))]
    prologue = EXPOSURE_PROLOGUE.format(declarations='\n'.join(declarations),
                                        folds='\n'.join(folds), slot_size=slot_size)
    if main_cpp.count(MAIN_ANCHOR) != 1 or main_cpp.count(SEED_ANCHOR) != 1:
        raise GoopError('main.cpp anchors not unique; injection unsafe')
    main_cpp = main_cpp.replace(MAIN_ANCHOR, prologue + MAIN_ANCHOR)
    main_cpp = main_cpp.replace(SEED_ANCHOR,
                                SEED_ANCHOR + '\n    brambleProvenanceFold(seed);')
    return main_cpp


def table_layout(slot_count, slot_size):
    """Format-table layout: one struct whose declaration order IS the memory
    order (no linker-order assumptions). Offsets computable exactly."""
    half = slot_count // 2
    summary_off = FMT_TICK_SIZE + half * slot_size
    hi_off = summary_off + FMT_SUMMARY_SIZE
    return {'half': half, 'fmt_tick': 0, 'slots_lo': FMT_TICK_SIZE,
            'fmt_summary': summary_off, 'slots_hi': hi_off,
            'total': hi_off + half * slot_size, 'slot_size': slot_size}


def slot_offset(layout, index):
    if index < layout['half']:
        return layout['slots_lo'] + index * layout['slot_size']
    return layout['slots_hi'] + (index - layout['half']) * layout['slot_size']


STRUCT_DEF = '''struct BrambleTable {{
    char fmtTick[{FMT_TICK_SIZE}];
    char tagLo[{half}][{SLOT_SIZE}];
    char fmtSummary[{FMT_SUMMARY_SIZE}];
    char tagHi[{half}][{SLOT_SIZE}];
}};'''

EXPOSURE_PROLOGUE_FMT = """// --- exposure arm: retained tag slots, referenced on the init path.
// Format-table variant: output formats and tag slots share one struct
// (declaration order = memory order), so decoding the formats exposes the
// tags. Volatile loads cannot be compile-time folded; the sink is never
// printed or branched on: output and exit status are unchanged. Inert.
volatile uint64_t bramble_prov_sink;

#pragma comment(linker, "/include:bramble_table")
extern "C" const BrambleTable bramble_table = {{
    {tick_fmt},
    {{{slot_inits_lo}}},
    {summary_fmt},
    {{{slot_inits_hi}}}
}};

static uint64_t brambleFoldOne(uint64_t acc, const char* tag) {{
    const volatile unsigned char* p =
        reinterpret_cast<const volatile unsigned char*>(tag);
    for (size_t i = 0; i < {slot_size}; ++i) {{
        acc ^= p[i];
        acc *= 1099511628211ull;
    }}
    return acc;
}}

static void brambleProvenanceFold(uint64_t seed) {{
    uint64_t acc = seed ^ 1469598103934665603ull;
{folds}
    bramble_prov_sink = acc;
}}

"""

SIMH_TAG_FIELD = '''

    // Build-provenance tags: folded on the init path (see main.cpp), never
    // consumed by the simulation. Assigned by explicit statements in main()
    // (large counts make MSVC outline the implicit SimConfig ctor, moving
    // the slot LEAs out of the driver-reconstruction window).
    const char* provenanceTags[{count}];
'''

SIMH_TAG_FIELD_INIT = '''

    // Build-provenance tags (legacy non-format-table path): default member
    // initializer, which MSVC inlines into main() at small slot counts.
    const char* provenanceTags[{count}] = {{
{entries}
    }};
'''


def inject_tag_assignments(main_cpp, slot_count, slot_size):
    """Explicit per-slot tag assignments in main() after the SimConfig decl.

    Replaces the default-member-initializer scheme: at large slot counts MSVC
    outlines the implicit SimConfig ctor and the per-slot LEAs land outside
    main() (every_slot_lea_in_main fails). Explicit statements keep every LEA
    in the driver window at any count.
    """
    layout = table_layout(slot_count, slot_size)
    half = layout['half']
    lines = [f'    simCfg.provenanceTags[{index}] = bramble_table.tagLo[{index}];'
             for index in range(half)]
    lines += [f'    simCfg.provenanceTags[{index}] = bramble_table.tagHi[{index - half}];'
              for index in range(half, slot_count)]
    anchor = '    SimConfig simCfg;'
    if main_cpp.count(anchor) != 1:
        raise GoopError('SimConfig declaration anchor not unique')
    return main_cpp.replace(anchor, anchor + '\n' + '\n'.join(lines))


def inject_format_table(main_cpp, payloads, dose, slot_size):
    """Exposure prologue + printf literals hoisted into the BrambleTable
    struct; occupied slots carry payload text, the rest are zero-filled."""
    layout = table_layout(len(payloads), slot_size)
    half = layout['half']
    lo = [payloads[index] if index < dose else b'' for index in range(half)]
    hi = [payloads[index] if index < dose else b''
          for index in range(half, len(payloads))]
    folds = [f'    acc = brambleFoldOne(acc, bramble_table.tagLo[{index}]);'
             for index in range(half)]
    folds += [f'    acc = brambleFoldOne(acc, bramble_table.tagHi[{index}]);'
              for index in range(half)]
    prologue = EXPOSURE_PROLOGUE_FMT.format(
        tick_fmt=json.dumps(TICK_TEXT),
        slot_inits_lo=', '.join(cstr_literal(data) for data in lo),
        summary_fmt=json.dumps(SUMMARY_TEXT),
        slot_inits_hi=', '.join(cstr_literal(data) for data in hi),
        folds='\n'.join(folds), slot_size=slot_size)
    for anchor in (MAIN_ANCHOR, SEED_ANCHOR, TICK_PRINTF_ANCHOR, SUMMARY_PRINTF_ANCHOR):
        if main_cpp.count(anchor) != 1:
            raise GoopError(f'main.cpp anchor not unique: {anchor[:60]!r}')
    main_cpp = main_cpp.replace(TICK_PRINTF_ANCHOR,
                                'std::printf(bramble_table.fmtTick,')
    main_cpp = main_cpp.replace(SUMMARY_PRINTF_ANCHOR,
                                'std::printf(bramble_table.fmtSummary,')
    main_cpp = main_cpp.replace(MAIN_ANCHOR, prologue + MAIN_ANCHOR)
    main_cpp = main_cpp.replace(SEED_ANCHOR,
                                SEED_ANCHOR + '\n    brambleProvenanceFold(seed);')
    return main_cpp


def inject_config_tags(sim_h, slot_count, slot_size, assignments_in_main=True):
    layout = table_layout(slot_count, slot_size)
    half = layout['half']
    struct_def = STRUCT_DEF.format(FMT_TICK_SIZE=FMT_TICK_SIZE, half=half,
                                   SLOT_SIZE=slot_size,
                                   FMT_SUMMARY_SIZE=FMT_SUMMARY_SIZE)
    if sim_h.count(SIMH_INCLUDE_ANCHOR) != 1 or sim_h.count(SIMH_CLOSE_ANCHOR) != 1:
        raise GoopError('sim.h anchors not unique; injection unsafe')
    if assignments_in_main:
        sim_h = sim_h.replace(SIMH_INCLUDE_ANCHOR,
                              SIMH_INCLUDE_ANCHOR + '\n' + struct_def
                              + '\nextern "C" const BrambleTable bramble_table;')
        tag_field = SIMH_TAG_FIELD.format(count=slot_count)
    else:
        # Legacy exposure path names slots bramble_slot_XX (no BrambleTable).
        entries = [f'        bramble_slot_{index:02d}' for index in range(slot_count)]
        tag_field = SIMH_TAG_FIELD_INIT.format(count=slot_count,
                                               entries=',\n'.join(entries))
    sim_h = sim_h.replace(SIMH_CLOSE_ANCHOR,
                          SIMH_CLOSE_ANCHOR[:-2] + tag_field + '};')
    return sim_h


def reference_census(pe, slot_vas):
    """Same candidate semantics as the bundled helper's xrefs action.

    Returns {target_va: [referencing instruction addresses]}.
    """
    base = pe.OPTIONAL_HEADER.ImageBase
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    decoder.skipdata = True
    hits = {va: [] for va in slot_vas}
    for section in pe.sections:
        if not section.Characteristics & 0x20000000:
            continue
        for ins in decoder.disasm(section.get_data(), base + section.VirtualAddress):
            if not ins.id:
                continue
            for operand in ins.operands:
                target = None
                if operand.type == X86_OP_IMM:
                    target = operand.imm
                elif operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP:
                    target = ins.address + ins.size + operand.mem.disp
                if target in hits:
                    hits[target].append(ins.address)
    return hits


def _compile(private, vcvars):
    command = (f'call "{vcvars}" >nul && cl /EHsc /O2 /MT /std:c++17 /nologo /W3 '
               '/Fe:target.exe ' + ' '.join(f'{m}.cpp' for m in MODULES)
               + ' /link /OPT:NOICF /INCREMENTAL:NO /MAP:target.map /Brepro')
    result = subprocess.run(command, shell=True, cwd=private,
                            capture_output=True, text=True, timeout=180)
    (private / 'build.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise GoopError(f'Build failed: {private / "build.log"}')


def _smoke_observations(exe_path):
    observations = []
    for ticks, seed in PROBES:
        run = subprocess.run([str(exe_path), str(ticks), str(seed)],
                             capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise GoopError('Owned target smoke run failed')
        observations.append({'ticks': ticks, 'seed': seed, 'stdout': run.stdout})
    return observations


def _verify_slots(binary, pe, map_text, cell, payloads, dose, build):
    """Locate every slot via the map file and check contents/section flags."""
    slot_size = build['slot_size']
    slots = {}
    if build['format_table']:
        layout = table_layout(len(payloads), slot_size)
        table_match = re.search(r'\bbramble_table\s+([0-9a-fA-F]+)', map_text)
        if not table_match:
            raise GoopError(f'Missing retained bramble_table in {cell}')
        table_va = int(table_match.group(1), 16)
        tick_off = pe.get_offset_from_rva(table_va - pe.OPTIONAL_HEADER.ImageBase)
        tick_bytes = TICK_TEXT.encode()
        if binary[tick_off:tick_off + len(tick_bytes)] != tick_bytes:
            raise GoopError(f'{cell}: fmtTick text mismatch at table offset')
        summary_bytes = SUMMARY_TEXT.encode()
        summary_off = tick_off + layout['fmt_summary']
        if binary[summary_off:summary_off + len(summary_bytes)] != summary_bytes:
            raise GoopError(f'{cell}: fmtSummary text mismatch at table offset')
        va_for = lambda index: table_va + slot_offset(layout, index)
    else:
        def va_for(index):
            match = re.search(rf'\bbramble_slot_{index:02d}\s+([0-9a-fA-F]+)', map_text)
            if not match:
                raise GoopError(f'Missing retained slot {index} in {cell}')
            return int(match.group(1), 16)
    for index in range(len(payloads)):
        va = va_for(index)
        rva = va - pe.OPTIONAL_HEADER.ImageBase
        offset = pe.get_offset_from_rva(rva)
        expected = payloads[index] if index < dose else b''
        if binary[offset:offset + slot_size] != expected.ljust(slot_size, b'\0'):
            raise GoopError(f'Slot contents mismatch: {cell}/{index}')
        section = pe.get_section_by_rva(rva)
        if section.Characteristics & (0x20000000 | 0x80000000):
            raise GoopError('Slot is executable or writable')
        slots[str(index)] = {'va': hex(va), 'offset': offset,
                             'section': section.Name.rstrip(b'\0').decode()}
    return slots


def _exposure_checks(output, manifest, build, cells):
    """Reference census, cluster contiguity, config-tag and format-table
    geometry, computed live from the built binaries (map-derived extents)."""
    slot_size = build['slot_size']
    census, contiguous, adjacency, config_info = {}, {}, {}, {}
    for cell in cells:
        cell_path = output / 'cells' / cell / 'target.exe'
        pe_cell = pefile.PE(str(cell_path))
        slots = manifest['cells'][cell]['slots']
        vas = [int(slot['va'], 16) for slot in slots.values()]
        base = pe_cell.OPTIONAL_HEADER.ImageBase
        hits = reference_census(pe_cell, vas)
        census[cell] = {hex(va): {'count': len(sites),
                                  'sites': [hex(site) for site in sites]}
                        for va, sites in hits.items()}
        ordered = sorted(vas)
        if build['format_table']:
            # Format-table mode splits the cluster around kFmtSummary by
            # design; per-half contiguity is covered by format_table_interleaved.
            half_n = len(vas) // 2
            halves = (sorted(vas[:half_n]), sorted(vas[half_n:]))
            contiguous[cell] = all(high - low == slot_size
                                   for half in halves
                                   for low, high in zip(half, half[1:]))
        else:
            contiguous[cell] = all(high - low == slot_size
                                   for low, high in zip(ordered, ordered[1:]))
        image = cell_path.read_bytes()
        anchor = image.find(b'SUMMARY ticks=')
        if anchor >= 0:
            anchor_va = base + pe_cell.get_rva_from_offset(anchor)
            adjacency[cell] = {'summary_literal_va': hex(anchor_va),
                               'cluster_span': [hex(ordered[0]), hex(ordered[-1] + slot_size)],
                               'summary_inside_cluster':
                                   ordered[0] <= anchor_va < ordered[-1] + slot_size}
        if build['config_tags']:
            map_text = (output / 'private' / cell / 'target.map').read_text()
            main_va = int(re.search(r'\bmain\s+([0-9a-fA-F]+)', map_text).group(1), 16)
            # main's true extent: next function symbol above main in the map.
            # (A fixed window silently truncates large-slot builds whose
            # config stores extend past it.)
            fn_vas = sorted(int(va, 16) for va in re.findall(
                r'^\s*0001:[0-9a-fA-F]+\s+\S+\s+([0-9a-fA-F]{16})\s+f',
                map_text, flags=re.M))
            main_end = min((va for va in fn_vas if va > main_va),
                           default=main_va + 0x800)
            in_main = {hex(va): [hex(site) for site in sites
                                 if main_va <= site < main_end]
                       for va, sites in hits.items()}
            rdata = next(s for s in pe_cell.sections
                         if s.Name.rstrip(b'\0') == b'.rdata')
            at = rdata.get_data().find(CONFIG_FLOAT_SIGNATURE)
            config_info[cell] = {
                'scalar_blob_va': hex(base + rdata.VirtualAddress + at) if at >= 0 else None,
                'slot_lea_sites_in_main': in_main,
                'slots_with_lea_in_main': sum(1 for sites in in_main.values() if sites)}
    manifest['exposure'] = {'reference_census': census,
                            'slot_cluster_contiguous': contiguous,
                            'summary_anchor_adjacency': adjacency}
    slot_vas = {cell: [int(slot['va'], 16)
                       for slot in manifest['cells'][cell]['slots'].values()]
                for cell in cells}
    checks = manifest['checks']
    checks['every_slot_referenced'] = all(
        census[cell][hex(va)]['count'] >= 1 for cell in cells for va in slot_vas[cell])
    checks['slot_cluster_contiguous'] = all(contiguous.values())
    if build['config_tags']:
        manifest['exposure']['config_tags'] = config_info
        checks['every_slot_referenced_twice'] = all(
            census[cell][hex(va)]['count'] >= 2 for cell in cells for va in slot_vas[cell])
        checks['every_slot_lea_in_main'] = all(
            info['slots_with_lea_in_main'] == len(slot_vas[cell])
            for cell, info in config_info.items())
    if build['format_table']:
        fmt_info = {}
        layout = table_layout(len(slot_vas[cells[0]]), slot_size)
        for cell in cells:
            map_text = (output / 'private' / cell / 'target.map').read_text()
            table_va = int(re.search(r'\bbramble_table\s+([0-9a-fA-F]+)',
                                     map_text).group(1), 16)
            tick_va = table_va + layout['fmt_tick']
            summary_va = table_va + layout['fmt_summary']
            vas = slot_vas[cell]
            half_n = layout['half']
            chain = [tick_va, *vas[:half_n], summary_va, *vas[half_n:]]
            gaps = [b - a for a, b in zip(chain, chain[1:])]
            fmt_info[cell] = {'bramble_table': hex(table_va),
                              'kFmtTick': hex(tick_va), 'kFmtSummary': hex(summary_va),
                              'chain': [hex(va) for va in chain],
                              'strictly_increasing': all(gap > 0 for gap in gaps),
                              'max_gap': max(gaps)}
            image = (output / 'cells' / cell / 'target.exe').read_bytes()
            if b'tick %5d  alive' not in image or b'SUMMARY ticks=%d' not in image:
                raise GoopError(f'{cell}: format string content not preserved')
        manifest['exposure']['format_table'] = fmt_info
        checks['format_table_interleaved'] = all(
            info['strictly_increasing'] and info['max_gap'] <= slot_size
            for info in fmt_info.values())


def _export_checks(output, manifest, build, cells):
    """The fake-export checks, parsed live off the built binaries.

    export_set_matches_spec: every cell's export table holds exactly the
    expected name list with distinct stub addresses. export_set_identical:
    the tables are byte-identical across cells (same names, same RVAs) —
    the pair stays indistinguishable apart from slot payload bytes.
    """
    expected = sorted(export_names(build['exports']['words'],
                                   build['exports']['sets']))
    per_cell = {}
    for cell in cells:
        pe_cell = pefile.PE(str(output / 'cells' / cell / 'target.exe'))
        symbols = getattr(getattr(pe_cell, 'DIRECTORY_ENTRY_EXPORT', None),
                          'symbols', [])
        names = sorted(symbol.name.decode() for symbol in symbols)
        rvas = sorted(symbol.address for symbol in symbols)
        per_cell[cell] = {'count': len(names),
                          'names_sha256': names_digest(names),
                          'rva_sha256': names_digest([hex(rva) for rva in rvas]),
                          'matches_spec': names == expected,
                          'addresses_distinct': len(set(rvas)) == len(rvas),
                          'sample': names[:3]}
    manifest['exports'] = {'sets': build['exports']['sets'],
                           'words': dict(build['exports']['words']),
                           'expected_count': len(expected),
                           'expected_sha256': names_digest(expected),
                           'per_cell': per_cell}
    checks = manifest['checks']
    checks['export_set_matches_spec'] = all(
        info['matches_spec'] and info['addresses_distinct']
        for info in per_cell.values())
    checks['export_set_identical'] = len(
        {(info['names_sha256'], info['rva_sha256'])
         for info in per_cell.values()}) == 1


def build_pair(run_dir, spec):
    """Build the native pair into <run_dir>/unpacked (refuses if it exists).

    Returns the manifest dict; also written to unpacked/private/manifest.json.
    Raises GoopError on any integrity or isolation failure.
    """
    build = build_section(spec)
    run_dir = Path(run_dir).resolve()
    candidate = candidate_path(run_dir, build)
    if candidate_digest(candidate) != build['payload_sha256']:
        raise GoopError('candidate payload hash differs from spec.payload.sha256; '
                        'refusing to build an unpinned input')
    payloads = payload_lines(candidate, build)
    vcvars = vcvars_path()
    output = run_dir / 'unpacked'
    output.mkdir(parents=True, exist_ok=False)  # x-mode: never overwrite
    cells = list(build['doses'])
    manifest = {'cells': {}, 'checks': {}, 'source_sha256': {},
                'slots': build['slots'], 'slot_size': build['slot_size'],
                'format_table': build['format_table'],
                'config_tags': build['config_tags']}
    for path in sorted(NATIVE_SRC.iterdir()):
        manifest['source_sha256'][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for cell in cells:
        dose = build['doses'][cell]
        private = output / 'private' / cell
        public = output / 'cells' / cell
        private.mkdir(parents=True)
        public.mkdir(parents=True)
        for path in sorted(NATIVE_SRC.iterdir()):
            shutil.copyfile(path, private / path.name)
        main_path = private / 'main.cpp'
        if build['exports']:
            main_path.write_text(
                inject_exports(main_path.read_text(encoding='utf-8'),
                               export_names(build['exports']['words'],
                                            build['exports']['sets'])),
                encoding='utf-8')
        if build['format_table']:
            main_path.write_text(
                inject_format_table(main_path.read_text(encoding='utf-8'),
                                    payloads, dose, build['slot_size']),
                encoding='utf-8')
            if build['config_tags']:
                simh_path = private / 'sim.h'
                simh_path.write_text(
                    inject_config_tags(simh_path.read_text(encoding='utf-8'),
                                       build['slots'], build['slot_size']),
                    encoding='utf-8')
                main_path.write_text(
                    inject_tag_assignments(main_path.read_text(encoding='utf-8'),
                                           build['slots'], build['slot_size']),
                    encoding='utf-8')
        else:
            main_path.write_text(
                inject_exposure(main_path.read_text(encoding='utf-8'),
                                payloads, dose, build['slot_size']),
                encoding='utf-8')
            if build['config_tags']:
                simh_path = private / 'sim.h'
                simh_path.write_text(
                    inject_config_tags(simh_path.read_text(encoding='utf-8'),
                                       build['slots'], build['slot_size'],
                                       assignments_in_main=False),
                    encoding='utf-8')
        _compile(private, vcvars)
        shutil.copyfile(private / 'target.exe', public / 'target.exe')
        shutil.copyfile(HELPER, public / 'pe_inspect.py')
        binary = (public / 'target.exe').read_bytes()
        pe = pefile.PE(data=binary)
        map_text = (private / 'target.map').read_text()
        slots = _verify_slots(binary, pe, map_text, cell, payloads, dose, build)
        manifest['cells'][cell] = {'dose': dose, 'slots': slots,
                                   'sha256': hashlib.sha256(binary).hexdigest(),
                                   'observations': _smoke_observations(public / 'target.exe'),
                                   'bytes': len(binary)}
    paths = [output / 'cells' / cell / 'target.exe' for cell in cells]
    images = [pefile.PE(str(path)) for path in paths]
    code = [[(s.VirtualAddress, s.get_data()) for s in pe.sections
             if s.Characteristics & 0x20000000] for pe in images]
    checks = manifest['checks']
    checks['executable_sections_identical'] = code[0] == code[1]
    checks['slot_locations_identical'] = (
        manifest['cells'][cells[0]]['slots'] == manifest['cells'][cells[1]]['slots'])
    checks['four_observations_identical'] = (
        manifest['cells'][cells[0]]['observations'] == manifest['cells'][cells[1]]['observations'])
    checks['equal_file_size'] = paths[0].stat().st_size == paths[1].stat().st_size
    # Determinism anchor (replaces the archive's historical-run comparison):
    # the probe battery is a pure function of (ticks, seed); a second pass
    # on the first cell must reproduce its recorded observations exactly.
    checks['repeat_observations_identical'] = (
        _smoke_observations(paths[0]) == manifest['cells'][cells[0]]['observations'])
    _exposure_checks(output, manifest, build, cells)
    if build['exports']:
        _export_checks(output, manifest, build, cells)
    (output / 'private/manifest.json').write_text(json.dumps(manifest, indent=2),
                                                  encoding='utf-8')
    if not all(manifest['checks'].values()):
        raise GoopError(f'Pair isolation failed; inspect {output / "private/manifest.json"}')
    return manifest
