"""Embed a PE CodeView path in reserved DOS-header bytes after UPX packing.

UPX discards linker debug records and rejects packed files with added PE
sections. This uses existing header padding only: no new section or PDB file.
"""
import struct

import pefile

from gooplib import GoopError

DEBUG_ENTRY_SIZE = 28


def hint_bytes(path):
    if not isinstance(path, str) or not path or '\x00' in path:
        raise GoopError('PDB hint must be a nonempty NUL-free string')
    try:
        value = path.encode('ascii')
    except UnicodeEncodeError as exc:
        raise GoopError('PDB hint must be ASCII') from exc
    if not all(32 <= byte <= 126 for byte in value):
        raise GoopError('PDB hint must be printable ASCII')
    return value


def reserved_bytes(path):
    """DOS header space required by one IMAGE_DEBUG_DIRECTORY and RSDS blob."""
    return DEBUG_ENTRY_SIZE + 24 + len(hint_bytes(path)) + 1


def add_pdb_hint(binary, path):
    """Return a packed PE with a genuine debug directory, no new sections."""
    hint = hint_bytes(path)
    pe = pefile.PE(data=binary)
    if pe.OPTIONAL_HEADER.Magic != 0x20b or not pe.sections:
        raise GoopError('PDB hint requires a PE32+ image')
    debug = pe.OPTIONAL_HEADER.DATA_DIRECTORY[6]
    security = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]
    if debug.VirtualAddress or debug.Size or security.VirtualAddress or security.Size:
        raise GoopError('PDB hint refuses signed or already-debugged images')
    end = pe.DOS_HEADER.e_lfanew
    # The DOS print routine uses function 09h: '$' terminates its message.
    sentinel = binary.find(b'$', 78, end)
    if sentinel < 0:
        raise GoopError('DOS stub lacks a text terminator')
    count = reserved_bytes(path)
    start = sentinel + 1
    if start + count > end or any(binary[start:start + count]):
        raise GoopError('insufficient zero-filled DOS header reservation for PDB hint')
    codeview_offset = start + DEBUG_ENTRY_SIZE
    codeview = b'RSDS' + bytes(16) + struct.pack('<I', 1) + hint + b'\x00'
    result = bytearray(binary)
    struct.pack_into('<IIHHIIII', result, start, 0, 0, 0, 0, 2,
                     len(codeview), codeview_offset, codeview_offset)
    result[codeview_offset:codeview_offset + len(codeview)] = codeview
    struct.pack_into('<II', result, debug.get_file_offset(), start, DEBUG_ENTRY_SIZE)
    checksum_offset = pe.OPTIONAL_HEADER.get_file_offset() + 64
    struct.pack_into('<I', result, checksum_offset, 0)
    struct.pack_into('<I', result, checksum_offset,
                     pefile.PE(data=bytes(result)).generate_checksum())
    parsed = pefile.PE(data=bytes(result))
    entries = getattr(parsed, 'DIRECTORY_ENTRY_DEBUG', [])
    if (len(entries) != 1 or entries[0].struct.Type != 2
            or hint not in result[start:start + count]):
        raise GoopError('PDB hint PE parse verification failed')
    return bytes(result)
