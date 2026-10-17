"""Build a real DOS MZ program for MSVC LINK /STUB, without patching a PE.

The DOS program prints the supplied message and exits. Windows starts at
its own PE entry point; LINK inserts this program before the PE header.
"""
import struct

from gooplib import GoopError

# push cs; pop ds; mov dx,000eh; mov ah,09h; int 21h;
# mov ax,4c01h; int 21h.  DOS function 09 prints to the '$' sentinel.
PRINT_AND_EXIT = bytes.fromhex('0e 1f ba 0e 00 b4 09 cd 21 b8 01 4c cd 21')
MAX_TEXT_BYTES = 16 * 1024
NEUTRAL_TEXT = 'This program cannot be run in DOS mode.'


def make_dos_stub(text, reserve_bytes=None):
    """Return an aligned DOS executable carrying *all* of the supplied text."""
    if not isinstance(text, str) or not text:
        raise GoopError('DOS-stub text must be nonempty')
    try:
        message = text.encode('ascii')
    except UnicodeEncodeError as exc:
        raise GoopError('DOS-stub text must be ASCII') from exc
    if (len(message) > MAX_TEXT_BYTES or b'$' in message
            or any(c < 32 or c > 126 for c in message)):
        raise GoopError('DOS-stub text must be printable ASCII without $, '
                        f'at most {MAX_TEXT_BYTES} bytes')
    if reserve_bytes is None:
        reserve_bytes = len(message)
    if not isinstance(reserve_bytes, int) or reserve_bytes < len(message):
        raise GoopError('DOS-stub reservation cannot truncate the text')
    image = bytearray(64)
    image += PRINT_AND_EXIT + message + b'$'
    image.extend(b'\0' * (reserve_bytes - len(message)))
    image.extend(b'\0' * (-len(image) % 16))
    # MZ pages count the complete DOS executable; e_lfanew points after it.
    pages, remainder = divmod(len(image), 512)
    struct.pack_into('<H', image, 0, 0x5a4d)
    struct.pack_into('<H', image, 2, remainder)
    struct.pack_into('<H', image, 4, pages + bool(remainder))
    struct.pack_into('<H', image, 8, 4)  # 64-byte MZ header
    struct.pack_into('<H', image, 0x0a, 0)  # minalloc
    struct.pack_into('<H', image, 0x0c, 0xffff)  # maxalloc
    struct.pack_into('<H', image, 0x10, 0x100)  # stack pointer
    struct.pack_into('<H', image, 0x18, 0x40)  # relocation table (empty)
    struct.pack_into('<I', image, 0x3c, len(image))
    return bytes(image)
