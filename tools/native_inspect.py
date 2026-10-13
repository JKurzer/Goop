"""Read-only PE inspection; no execution, symbols, source, or ground-truth access.

Use --binary PATH info|strings|functions|disasm|data|xrefs. Addresses are VAs.
Disassembly is bounded linear decoding, not proof of reachability.
"""
import argparse
import json
import struct

import pefile
from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_REG_RIP


def inspect(args):
    pe = pefile.PE(args.binary)
    base = pe.OPTIONAL_HEADER.ImageBase
    decoder = Cs(CS_ARCH_X86, CS_MODE_64)
    decoder.detail = True
    sections = list(pe.sections)
    executable = [s for s in sections if s.Characteristics & 0x20000000]
    if args.action == 'info':
        return {'image_base': hex(base),
                'entry_va': hex(base + pe.OPTIONAL_HEADER.AddressOfEntryPoint),
                'sections': [{'name': s.Name.rstrip(b'\0').decode(),
                              'va': hex(base + s.VirtualAddress),
                              'virtual_size': s.Misc_VirtualSize,
                              'raw_size': s.SizeOfRawData,
                              'flags': hex(s.Characteristics)} for s in sections],
                'imports': [{'dll': d.dll.decode(), 'name': (f.name or b'ordinal').decode(),
                             'iat_va': hex(f.address)}
                            for d in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])
                            for f in d.imports],
                'exports': len(getattr(getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None),
                                      'symbols', [])),
                'debug_entries': len(getattr(pe, 'DIRECTORY_ENTRY_DEBUG', []))}
    if args.action == 'functions':
        entries = getattr(pe, 'DIRECTORY_ENTRY_EXCEPTION', [])
        return [{'begin': hex(base + e.struct.BeginAddress),
                 'end': hex(base + e.struct.EndAddress)}
                for e in entries[args.offset:args.offset + args.count]]
    if args.action == 'strings':
        import re
        rows = []
        for section in sections:
            if args.section and section.Name.rstrip(b'\0').decode() != args.section:
                continue
            for match in re.finditer(rb'[\x20-\x7e]{5,}', section.get_data()):
                text = match.group().decode('ascii')
                if args.contains.lower() in text.lower():
                    rows.append({'va': hex(base + section.VirtualAddress + match.start()),
                                 'text': text})
        return {'total_matches': len(rows),
                'rows': rows[args.offset:args.offset + args.count]}
    if args.va is None:
        raise ValueError('--va is required for disasm, data, and xrefs')
    rva = args.va - base
    if not 0 <= rva < pe.OPTIONAL_HEADER.SizeOfImage:
        raise ValueError('Address outside image')
    if args.action == 'data':
        data = pe.get_data(rva, args.size)
        return {'va': hex(args.va), 'hex': data.hex(' '),
                'ascii': ''.join(chr(b) if 32 <= b < 127 else '.' for b in data),
                'u32_le': [v[0] for v in struct.iter_unpack('<I', data[:len(data)//4*4])],
                'f32_le': [str(v[0]) for v in struct.iter_unpack('<f', data[:len(data)//4*4])]}
    if args.action == 'disasm':
        return [f'{ins.address:x}: {ins.mnemonic} {ins.op_str}'
                for ins in decoder.disasm(pe.get_data(rva, args.count * 15),
                                          args.va, count=args.count)]
    rows = []
    # Linear sweep can miss code after embedded data; skipdata helps traversal,
    # but matches remain candidate references, not a complete call graph.
    decoder.skipdata = True
    for section in executable:
        for ins in decoder.disasm(section.get_data(), base + section.VirtualAddress):
            if not ins.id:
                continue
            targets = []
            for operand in ins.operands:
                if operand.type == X86_OP_IMM:
                    targets.append(operand.imm)
                elif operand.type == X86_OP_MEM and operand.mem.base == X86_REG_RIP:
                    targets.append(ins.address + ins.size + operand.mem.disp)
            if args.va in targets:
                rows.append(f'{ins.address:x}: {ins.mnemonic} {ins.op_str}')
    return {'candidate_matches': len(rows),
            'rows': rows[args.offset:args.offset + args.count],
            'caveat': 'Immediate/RIP-relative candidates only; absence is not proof of no use'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('action', choices=['info', 'strings', 'functions', 'disasm', 'data', 'xrefs'])
    parser.add_argument('--va', type=lambda value: int(value, 0))
    parser.add_argument('--count', type=int, default=80)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--size', type=int, default=64)
    parser.add_argument('--contains', default='')
    parser.add_argument('--section', default='', help='Exact section name for strings')
    args = parser.parse_args()
    if not 1 <= args.count <= 200 or not 1 <= args.size <= 1024 or args.offset < 0:
        parser.error('count must be 1..200, size 1..1024, offset >= 0')
    print(json.dumps(inspect(args), indent=2))


if __name__ == '__main__':
    main()
