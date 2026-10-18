"""Convert the freshly wrapped basis into independently emitted native strings.

Real rz-bin -z escapes embedded LF instead of separating display rows.
Each chunk therefore needs its own const-char array / NUL terminator.
No model launch, no owner vocabulary changes, no historical-spec recovery.
"""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

from wrap_basis_cargo import wrap, WIDTH

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / 'specs/run_conformant_v9_meg.json'


def main():
    raw = BASIS.read_bytes()
    source = raw.decode('utf-8')
    before = json.loads(source)
    after = copy.deepcopy(before)
    replacements = []
    groups, source_groups = {}, {}
    for entry in before['build']['strings']:
        base = re.sub(r'_l\d+$', '', entry['name'])
        source_groups.setdefault(base, []).append(entry['text'].replace('\n', ' '))
    for name, parts in source_groups.items():
        original = ' '.join(parts)
        lines = wrap(name, original).split('\n')
        chunks = ([{'name': name, 'text': original}] if len(lines) == 1 else
                  [{'name': f'{name}_l{index:02d}', 'text': text}
                   for index, text in enumerate(lines, 1)])
        assert all(0 < len(chunk['text']) <= WIDTH for chunk in chunks)
        assert ' '.join(chunk['text'] for chunk in chunks) == original
        replacements.extend(chunks)
        groups[name] = [chunk['name'] for chunk in chunks]
    assert len(replacements) <= 99
    assert len({entry['name'] for entry in replacements}) == len(replacements)
    after['build']['strings'] = replacements
    # Replace only the strings-array text; preserve the owner's other bytes.
    marker = '"strings": '
    start = source.index(marker) + len(marker)
    _, consumed = json.JSONDecoder().raw_decode(source[start:])
    array = json.dumps(replacements, indent=2).replace('\n', '\n    ')
    result = source[:start] + array + source[start+consumed:]
    assert json.loads(result) == after
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with (ROOT/'.scratch'/f'basis_lf_stage_{stamp}.json').open('xb') as stream:
        stream.write(raw)
    with BASIS.open('w', encoding='utf-8', newline='') as stream:
        stream.write(result)
    with (ROOT/'.scratch'/f'basis_chunks_{stamp}.json').open('x', encoding='utf-8') as stream:
        json.dump({'groups': groups, 'chunks': len(replacements),
                   'max_chars': max(len(entry['text']) for entry in replacements),
                   'sha256': hashlib.sha256(BASIS.read_bytes()).hexdigest()}, stream, indent=2)
    print('chunks:', len(replacements), 'max chars:', max(len(x['text']) for x in replacements))
    for name, names in groups.items():
        print(name, '->', len(names), 'native strings')


if __name__ == '__main__':
    main()
