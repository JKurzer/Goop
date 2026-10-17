"""Three independently scoped RunB arms use identical pinned input bytes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'runs'
SOURCE = ROOT / 'conformant-v13-reverse-compile'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_replica_contracts_and_input_identity():
    plan = json.loads((SOURCE / 'replication-plan.json').read_text(encoding='utf-8'))
    source_spec = SOURCE / 'spec.json'
    source_preflight = SOURCE / 'PREFLIGHT.json'
    assert len(plan['replicas']) == 3
    for ordinal, name in enumerate(plan['replicas'], 1):
        replica = ROOT / name
        spec_path = replica / 'spec.json'
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        provenance = json.loads((replica / 'inputs/source.json').read_text(encoding='utf-8'))
        preflight = json.loads((replica / 'PREFLIGHT.json').read_text(encoding='utf-8'))
        assert spec['arm'] == name
        assert spec['fire']['cells'] == ['RunB']
        assert spec['fire']['prompt_file'] == plan['prompt_file'] == 'compile.md'
        assert spec['fire']['model'] == plan['model'] == 'gpt-6-astra'
        assert provenance['ordinal'] == ordinal
        assert provenance['source_spec_sha256'] == sha(source_spec)
        assert provenance['source_preflight_sha256'] == sha(source_preflight)
        assert provenance['replica_spec_sha256'] == sha(spec_path)
        assert all(preflight['native_checks'].values())
        assert all(preflight['packed_checks'].values())
        for relative, expected in provenance['assets_sha256'].items():
            assert sha(replica / relative) == expected == sha(SOURCE / relative)
        assert preflight['cells']['RunB']['packed_sha256'] == plan['source_RunB_packed_sha256']
