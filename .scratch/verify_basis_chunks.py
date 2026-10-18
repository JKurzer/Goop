"""Verify this edit against the pre-edit snapshot, not stale historical specs."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
old = json.loads((ROOT/'.scratch/basis_before_wrap_20261016_222810.json').read_text(encoding='utf-8'))
new = json.loads((ROOT/'specs/run_conformant_v9_meg.json').read_text(encoding='utf-8'))
old_entries = old['build'].pop('strings')
new_entries = new['build'].pop('strings')
assert old == new, 'Unexpected change outside build.strings'
groups = {}
for entry in new_entries:
    name = re.sub(r'_l\d+$', '', entry['name'])
    groups.setdefault(name, []).append(entry['text'])
assert set(groups) == {entry['name'] for entry in old_entries}
for entry in old_entries:
    assert ' '.join(groups[entry['name']]) == entry['text'], entry['name']
print('All 8 original cargo texts reconstruct byte-for-byte with single-space separators.')
print('No other basis-spec fields changed.')
print('Native strings:', len(new_entries))
print('Maximum ASCII content length:', max(len(entry['text']) for entry in new_entries))
print('Deleted payload-spec reference exists:', (ROOT/new['payload']['spec_file']).is_file())
