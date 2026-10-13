"""goop shared library: spec loading/validation and small helpers.

Every run parameter traces to a file (spec.json, candidate payload). No
historical hardcodes; the archive is never consulted.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
HELPER = TOOLS / 'native_inspect.py'     # bundled analyst helper (byte-frozen per repo)
UPX = TOOLS / 'upx' / 'upx.exe'          # bundled stock UPX
NATIVE_SRC = Path(__file__).resolve().parent / 'native_src'


class GoopError(RuntimeError):
    """Refusal or integrity failure raised by any goop step."""
