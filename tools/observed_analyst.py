"""Private child entry point. Observer installation never adds model instructions."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gooplib.observe.budget import install_guard
from gooplib.observe.hooks import install
from gooplib.observe.record import Recorder, environment_secrets


def main():
    cell = Path(os.environ["GOOP_CELL_DIR"]).resolve()
    if cell != Path.cwd().resolve():
        raise RuntimeError("Expected analyst cell as working directory")
    recorder = Recorder(os.environ["GOOP_OBSERVE_DIR"], secrets=environment_secrets())
    install_guard()
    from code_puppy.cli_runner import main_entry

    install(recorder, cell)
    try:
        main_entry()
    finally:
        recorder.snapshot_sources(cell)
        recorder.emit(
            "observer_closed",
            {
                "stored_bytes": recorder.bytes,
                "logging_write_seconds": recorder.write_seconds,
            },
        )


if __name__ == "__main__":
    main()
