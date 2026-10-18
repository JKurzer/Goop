"""What helper? Receipts: the bundled analyst helper and every shipped copy."""
import hashlib
import json
from pathlib import Path

bundled = Path('tools/native_inspect.py').read_bytes()
print(f'bundled helper: tools/native_inspect.py '
      f'({len(bundled)} bytes, sha256 {hashlib.sha256(bundled).hexdigest()})')
print('role: goop\'s generic READ-ONLY PE inspector, copied byte-exact beside')
print('each cell\'s target.exe by the pack step; the prompt names it and')
print('explicitly allows reading/invoking it (info|strings|functions|disasm|')
print('data|xrefs). Preflight requires shipped bytes == bundled bytes.\n')
for arm in ('conformant-v8-meg-r2', 'conformant-v9-meg', 'conformant-v10-meg',
            'conformant-v11-meg', 'v8-undosed-control'):
    for cell_dir in sorted(Path('runs', arm).glob('cells/*')):
        shipped = cell_dir / 'pe_inspect.py'
        if shipped.exists():
            same = shipped.read_bytes() == bundled
            print(f'  runs/{arm}/cells/{cell_dir.name}/pe_inspect.py: '
                  f'byte-identical={same}')
pre = json.loads(Path('runs/conformant-v11-meg/PREFLIGHT.json').read_text())
print('\npreflight helper_sha256 (v11 RunB):',
      pre['cells']['RunB']['helper_sha256'])
