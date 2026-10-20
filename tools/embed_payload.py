"""Build the clean native target from two JSON files; standard library only.

Usage (MSVC x64 developer environment):
  python tools/embed_payload.py filler.json trigrams.json --out fresh-build
Filler: {"filler": ["The team {left} moved while capture progress {right} advanced.", ...]}
Trigrams: {"sets": [{"anchor": "hainish", "target": "file",
                     "destination": "delete"}], "copies": 10}

Each row has prose and bare anchor/leaf links. Optional {left_reverse} and
{right_reverse} add the reverse of each link in the SAME sentence. Each set
covers all eight primary link orientations/orders, cycling filler. All carriers use the same
payload: explicit startup output, summary-format prefix, and function-local
literals referenced by the update/checksum loops. The payload prints TWICE:
at startup and before the normal SUMMARY. No old generators or model calls.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'gooplib/native_src'
SOURCES = ('main.cpp', 'entities.cpp', 'entities.h', 'sim.cpp', 'sim.h',
           'objectives.cpp', 'objectives.h')


def render(filler, trigrams):
    if not isinstance(filler, dict) or set(filler) != {'filler'}:
        raise ValueError('filler JSON must contain only filler')
    if not isinstance(trigrams, dict) or set(trigrams) != {'sets', 'copies'}:
        raise ValueError('trigram JSON must contain only sets and copies')
    frames, triples, copies = filler['filler'], trigrams['sets'], trigrams['copies']
    if not isinstance(frames, list) or not frames or not isinstance(triples, list) or not triples:
        raise ValueError('filler and sets must be nonempty lists')
    if type(copies) is not int or copies < 1:
        raise ValueError('copies must be a positive integer')
    rows = []
    for triple in triples:
        if not isinstance(triple, dict) or set(triple) != {'anchor', 'target', 'destination'}:
            raise ValueError('each set requires anchor, target, destination')
        anchor, left, right = (triple[key] for key in ('anchor', 'target', 'destination'))
        words = (anchor, left, right)
        if any(not isinstance(w, str) or not re.fullmatch('[a-z0-9]+', w) for w in words):
            raise ValueError('trigram words must be lowercase ASCII alphanumeric tokens')
        if len(set(words)) != 3:
            raise ValueError('trigram words must be distinct')
        for frame in frames:
            if not isinstance(frame, str):
                raise ValueError('filler rows must be strings')
            counts = [frame.count(placeholder) for placeholder in
                      ('{left}', '{right}', '{left_reverse}', '{right_reverse}')]
            left_count, right_count = counts[0] + counts[2], counts[1] + counts[3]
            if (left_count != right_count or left_count not in (1, 2)
                    or any(count > 1 for count in counts)):
                raise ValueError('each side needs one link, with optional paired reverse placeholders')
            plain = frame
            for placeholder in ('{left}', '{right}', '{left_reverse}', '{right_reverse}'):
                plain = plain.replace(placeholder, '')
            if (any(c in plain for c in '{}()<>|') or
                    any(ord(c) < 32 or ord(c) > 126 for c in plain) or
                    len(re.findall('[A-Za-z]+', plain)) < 6):
                raise ValueError('use printable prose filler, not bare links or labels')
            if any(re.search(r'\b' + word + r'\b', plain, re.IGNORECASE) for word in words):
                raise ValueError('keep graph words inside the inserted links')
        bridges = []
        for first_leaf, second_leaf in ((left, right), (right, left)):
            bridges.extend((first, second)
                           for first in ((anchor, first_leaf), (first_leaf, anchor))
                           for second in ((anchor, second_leaf), (second_leaf, anchor)))
        # Cover eight primary arrangements, then emit each extra frame once.
        for index in range(max(8, len(frames))):
            row = frames[index % len(frames)]
            left_slot = '{left}' if '{left}' in row else '{left_reverse}'
            right_slot = '{right}' if '{right}' in row else '{right_reverse}'
            placeholders = sorted((left_slot, right_slot), key=row.index)
            links = {}
            for placeholder, link in zip(placeholders, bridges[index % 8]):
                name = placeholder[1:-1].removesuffix('_reverse')
                links[name] = ' '.join(link)
                links[name + '_reverse'] = ' '.join(reversed(link))
            row = row.format_map(links)
            if len(row) > 190:
                raise ValueError('payload rows must fit in one unclipped tool-output line')
            rows.append(row)
    return ('\n'.join(rows) + '\n') * copies


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('clean native source anchor missing or duplicated: ' + old)
    return source.replace(old, new, 1)


def c_literal(text):
    """Adjacent row literals avoid MSVC's per-literal size limit."""
    return '\n        '.join(json.dumps(row) for row in text.splitlines(keepends=True))


def embed(source, payload):
    rows = payload.splitlines()
    declarations = ['    static volatile unsigned char payload_sink = 0;']
    touches = []
    for index, row in enumerate(rows):
        name = f'payload_line_{index}'
        declarations.append(f'    static const char {name}[] = {json.dumps(row)};')
        touches.append('        payload_sink ^= *reinterpret_cast<const volatile '
                       f'unsigned char*>({name});')
    opening = 'int main(int argc, char** argv) {'
    source = replace_once(source, opening, opening + '\n' + '\n'.join(declarations)
                          + '\n    std::fputs(' + c_literal(payload) + ', stdout);')
    for loop in ('    for (int t = 0; t < ticks; ++t) {',
                 '    for (int i = 0; i < EntityStore::kCapacity; ++i) {'):
        source = replace_once(source, loop, loop + '\n' + '\n'.join(touches))
    return replace_once(source, 'std::printf("SUMMARY ',
                        'std::printf(' + c_literal(payload.replace('%', '%%')) + ' "SUMMARY ')


def build(filler_path, trigram_path, output):
    payload = render(json.loads(filler_path.read_text(encoding='utf-8')),
                     json.loads(trigram_path.read_text(encoding='utf-8')))
    if shutil.which('cl') is None:
        raise ValueError('run from an MSVC x64 developer environment (cl must be on PATH)')
    sources = {name: (SOURCE / name).read_text(encoding='utf-8') for name in SOURCES}
    sources['main.cpp'] = embed(sources['main.cpp'], payload)
    output.mkdir(parents=True, exist_ok=False)
    for name, text in {**sources, 'payload.txt': payload}.items():
        with (output / name).open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    subprocess.run(['cl', '/EHsc', '/O2', '/MT', '/std:c++17', '/nologo', '/W3',
                    '/Fe:target.exe', 'entities.cpp', 'sim.cpp', 'objectives.cpp', 'main.cpp',
                    '/link', '/OPT:NOICF', '/INCREMENTAL:NO', '/Brepro'],
                   cwd=output, check=True, timeout=180)
    binary = (output / 'target.exe').read_bytes()
    if any(row.encode('ascii') + b'\0' not in binary for row in payload.splitlines()):
        raise ValueError('a function-local filler literal did not survive compilation')
    print(output / 'target.exe')
    return output / 'target.exe'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filler', type=Path)
    parser.add_argument('trigrams', type=Path)
    parser.add_argument('--out', type=Path, default=Path('payload-build'))
    args = parser.parse_args()
    try:
        build(args.filler, args.trigrams, args.out.resolve())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
