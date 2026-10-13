"""Scratch (DELETE BEFORE DELIVERY): build a v13 fixture dir for CLI smoke."""
import sys
import tempfile
from pathlib import Path

GOOP = Path(__file__).resolve().parent
sys.path.insert(0, str(GOOP / 'tests'))
sys.path.insert(0, str(GOOP / 'tools'))
sys.path.insert(0, str(GOOP))

from test_score import ArchiveRun  # noqa: E402

tmp = Path(tempfile.mkdtemp(prefix='goop_cli_'))
fixture = ArchiveRun(tmp, 'packed-v13')
print(fixture.run)
print('JUNCTIONS:', *[str(j) for j in fixture.junctions])
