"""Show exactly what the export arm injects, to the byte (v7-meg spec)."""
import json

from gooplib import native_build as nb
from gooplib.exports import block_names

spec = json.load(open('runs/conformant-v7-meg/spec.json', encoding='utf-8'))
exports = spec['build']['exports']
names = block_names(exports)

print('export slots total:', len(names))
print()
print('--- first 6 slot names, repr (exact bytes) ---')
for n in names[:6]:
    print(repr(n))
print()

block = nb.inject_exports(nb.MAIN_ANCHOR, names)
print('--- injected block: head of the C source ---')
for line in block.split('\n')[:6]:
    print(line)
print('    ... (%d stub lines total) ...' % len(names))
print('}')
print()

first_line = ('__declspec(dllexport) void ' + names[0] + '() {}').encode('ascii')
print('--- one slot line, to the exact byte ---')
print('repr:', repr(first_line))
print('len :', len(first_line), 'bytes')
print('hex :', first_line.hex(' '))
print()

payload = block.encode('ascii')
print('--- whole injected block ---')
print('bytes spliced into main.cpp:', len(payload))
print('pure ASCII:', all(b < 128 for b in payload))
print('splice anchor:', repr(nb.MAIN_ANCHOR))
print()
print('--- and what the PE holds per slot after the link ---')
pe_name = names[0].encode('ascii') + b'\x00'
print('name-table string:', repr(pe_name), '->', pe_name.hex(' '))
