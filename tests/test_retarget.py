"""The next-run compose recipe stays reproducible without changing either run."""
import hashlib
import json
import re
from pathlib import Path

from gooplib.exports import validate_pairs

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/conformant-v13-reverse-compile'
SOURCE = ROOT / 'runs/conformant-v11-160-metadata'


def test_composed_candidate_and_visible_spec_are_pinned():
    recipe = json.loads((RUN / 'inputs/compose.json').read_text(encoding='utf-8'))
    manifest = json.loads((RUN / 'inputs/compose.manifest.json').read_text(encoding='utf-8'))
    old = (SOURCE / 'inputs/candidate.txt').read_bytes()
    new = (RUN / 'inputs/candidate.txt').read_bytes()
    expected, count = re.subn(rb'\bslot\b', b'reverse', old)
    assert count == recipe['candidate_replacements'] == 2880
    assert new == expected
    assert hashlib.sha256(old).hexdigest() == recipe['source_candidate_sha256']
    assert hashlib.sha256(new).hexdigest() == manifest['candidate_sha256']
    spec_bytes = (RUN / 'spec.json').read_bytes()
    spec = json.loads(spec_bytes)
    assert hashlib.sha256(spec_bytes).hexdigest() == manifest['spec_sha256']
    assert spec['payload']['sha256'] == manifest['candidate_sha256']
    assert spec['fire']['prompt_file'] == 'compile.md'
    assert spec['fire']['cells'] == ['RunB']
    assert spec['build']['doses'] == {'RunA': 0, 'RunB': 160}
    pairs = validate_pairs(spec['build']['fn_literals']['pairs'])
    assert [pair['target'] for pair in pairs] == ['team', 'progress', 'reverse']
    assert pairs[2]['destination'] == 'remove'
    for entry in spec['build']['strings']:
        assert not re.search(r'\bslot\b', entry['text'])
    assert 'teleology reverse' in spec['payload']['terms']
    assert 'teleology slot' not in spec['payload']['terms']


def test_packed_binary_is_preflight_pinned():
    preflight = json.loads((RUN / 'PREFLIGHT.json').read_text(encoding='utf-8'))
    assert all(preflight['native_checks'].values())
    assert all(preflight['packed_checks'].values())
    for cell, metadata in preflight['cells'].items():
        packed = (RUN / 'cells' / cell / 'target.exe').read_bytes()
        assert hashlib.sha256(packed).hexdigest() == metadata['packed_sha256']
