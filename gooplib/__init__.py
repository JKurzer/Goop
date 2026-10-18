"""goop shared library: spec loading/validation and small helpers.

Every run parameter traces to a file (spec.json, candidate payload). No
historical hardcodes; the archive is never consulted.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
# The bundled analyst helper (tools/native_inspect.py) is DESTROYED
# (owner ruling 2026-10-16: it guided analysts away from the payloads;
# real tooling - the rizin suite - replaces it).
NATIVE_SRC = Path(__file__).resolve().parent / 'native_src'


class GoopError(RuntimeError):
    """Refusal or integrity failure raised by any goop step."""
