"""Pin the actual C++ artifacts, not analyst claims about their exposure."""
import hashlib
import json
import re
from pathlib import Path

from tools.goop_compile import source_from_final

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'runs'
BASE = 'conformant-v13-reverse-compile'


def test_four_sources_match_compiler_inputs_and_shared_target_formats():
    base = RUNS / BASE
    spec = json.loads((base / 'spec.json').read_text(encoding='utf-8'))
    formats = spec['build']['formats']
    assert 'cp owner %d team progress' in formats['tick']
    assert 'SUMMARY teleology progress team ticks=' in formats['summary']
    template = (ROOT / 'gooplib/native_src/main.cpp').read_text(encoding='utf-8')
    assert 'teleology progress team' not in template
    manifest = json.loads((base / 'private/manifest.json').read_text(encoding='utf-8'))
    for cell in ('RunA', 'RunB'):
        assert 'SUMMARY teleology progress team ticks=' in (
            manifest['cells'][cell]['observations'][0]['stdout'])
    for suffix in ('', '-r1', '-r2', '-r3'):
        run = RUNS / (BASE + suffix)
        raw_report = (run / 'reports/final_RunB.md').read_bytes()
        source = source_from_final(raw_report.decode('utf-8'))
        assert (run / 'analysis/replacement_RunB.cpp').read_bytes() == source
        grade = json.loads((run / 'analysis/compile_RunB.json').read_text())
        assert grade['grade'] == 'compiled'
        assert grade['report_sha256'] == hashlib.sha256(raw_report).hexdigest()
        assert grade['source_sha256'] == hashlib.sha256(source).hexdigest()
        code = source.decode('utf-8')
        assert 'cp owner %d team progress' in code
        assert 'SUMMARY teleology progress team ticks=' in code
        assert not re.search(r'\b(reverse|remove)\b', code)
