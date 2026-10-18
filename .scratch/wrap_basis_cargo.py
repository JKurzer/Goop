"""Wrap the owner's CURRENT cargo strings; no builds or model launches.

Only replace selected ASCII spaces with LF. Graph breaks occur between
complete two-LINK units (4 words / 2 directed edges); prose breaks occur
at existing semicolon sentence separators. All other bytes are preserved.
"""
import copy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gooplib.specs import build_section

BASIS = ROOT / 'specs/run_conformant_v9_meg.json'
WIDTH = 120  # Leaves 136 chars for raw ANSI + address columns under a 256 cap.


def breaks_for(name, text):
    if name == 'full_graph' or name.startswith('graph_pair_'):
        words = list(re.finditer(r'\S+', text))
        if len(words) % 4:
            raise ValueError(f'{name}: expected complete two-LINK units')
        return [words[index].start() - 1 for index in range(4, len(words), 4)]
    if name == 'full_graph_directed':
        pairs = list(re.finditer(r'\S+>\S+\s+\S+>\S+', text))
        return [pair.start() - 1 for pair in pairs[1:]]
    if name in ('carriers', 'lead_ins'):
        return [match.end() - 1 for match in re.finditer(r' ; ', text)]
    if len(text) > WIDTH:
        raise ValueError(f'{name}: no declared safe break boundaries')
    return []


def wrap(name, text):
    if '\n' in text:
        if max(map(len, text.split('\n'))) > WIDTH:
            raise ValueError(f'{name}: already multiline but over budget')
        return text
    candidates = breaks_for(name, text)
    chosen, start = [], 0
    while len(text) - start > WIDTH:
        available = [index for index in candidates if start < index <= start + WIDTH]
        if not available:
            raise ValueError(f'{name}: a complete unit exceeds {WIDTH} chars')
        end = max(available)
        assert text[end] == ' '
        chosen.append(end)
        start = end + 1
    chars = list(text)
    for index in chosen:
        chars[index] = '\n'
    result = ''.join(chars)
    assert result.replace('\n', ' ') == text
    assert all(0 < len(line) <= WIDTH for line in result.split('\n'))
    return result


def main():
    raw = BASIS.read_bytes()
    source = raw.decode('utf-8')
    before = json.loads(source)
    after = copy.deepcopy(before)
    rows = []
    for entry in after['build']['strings']:
        old = entry['text']
        new = wrap(entry['name'], old)
        if new != old:
            old_literal, new_literal = json.dumps(old), json.dumps(new)
            assert source.count(old_literal) == 1, entry['name']
            source = source.replace(old_literal, new_literal, 1)
        entry['text'] = new
        rows.append({'name': entry['name'], 'bytes_before': len(old),
                     'bytes_after': len(new), 'lines': len(new.split('\n')),
                     'max_line_chars': max(map(len, new.split('\n')))})
    assert json.loads(source) == after
    build_section(after)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = ROOT / '.scratch' / f'basis_before_wrap_{stamp}.json'
    with backup.open('xb') as stream:
        stream.write(raw)
    # Targeted literal replacements, not a JSON reserialization of user edits.
    with BASIS.open('w', encoding='utf-8', newline='') as stream:
        stream.write(source)
    report = {'source': str(BASIS), 'backup': str(backup), 'width': WIDTH,
              'before_sha256': hashlib.sha256(raw).hexdigest(),
              'after_sha256': hashlib.sha256(BASIS.read_bytes()).hexdigest(),
              'entries': rows}
    with (ROOT / '.scratch' / f'basis_wrap_{stamp}.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    for row in rows:
        print(row)


if __name__ == '__main__':
    main()
