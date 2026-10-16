"""Cargo-string tests (owner ruling 2026-10-15, verbatim: "I don't care
about over priming. remove the existing exports, go ahead and build the
cargo strings.").

Pure validation + source-emission tests; the end-to-end build/pack
assertions live in test_build.py (run20x, skipped without a pinned
toolchain), and the transcript landing measure is goop_score's
string_visibility (wired over the count_visible primitive tested in
test_exports.py).
"""
import json

import pytest

from gooplib import GoopError
from gooplib.native_build import inject_strings
from gooplib.specs import STRINGS_MAX, STRING_TEXT_MAX, build_section

SHA64 = 'ab' * 32
ENTRIES = [{'name': 'signpost', 'text': 'see the slot table'},
           {'name': 'cargo_note', 'text': 'quorlx vexel quorlx murn'}]

STUB_MAIN = ('int main(int argc, char** argv) {\n'
             '    for (int t = 0; t < ticks; ++t) {\n'
             '    }\n'
             '    for (int i = 0; i < EntityStore::kCapacity; ++i) {\n'
             '    }\n'
             '}\n')


def make_spec(strings=None):
    build = {'slots': 20, 'slot_size': 512,
             'doses': {'k7': 10, 'm2': 20},
             'format_table': True, 'config_tags': True}
    if strings is not None:
        build['strings'] = strings
    return {'payload': {'path': 'inputs/candidate.txt', 'sha256': SHA64},
            'build': build}


# ---- spec wiring ------------------------------------------------------------

def test_build_section_strings_roundtrip():
    assert build_section(make_spec(ENTRIES))['strings'] == ENTRIES


def test_build_section_strings_absent():
    assert build_section(make_spec())['strings'] is None


def test_build_section_exports_key_refused():
    """The exports block is deleted (2026-10-15 ruling): a stale spec must
    fail loudly, not silently build without its arm."""
    spec = make_spec()
    spec['build']['exports'] = {'sets': 1, 'anchor': 'a', 'target': 'b',
                                'destination': 'c'}
    with pytest.raises(GoopError, match='deleted'):
        build_section(spec)


@pytest.mark.parametrize('strings', [
    'not-a-list',
    [],
    [{'name': 'x'}],
    [{'name': 'x', 'text': 'y', 'extra': 'z'}],
    [{'name': 'Bad', 'text': 'y'}],
    [{'name': '9x', 'text': 'y'}],
    [{'name': 'x' * 33, 'text': 'y'}],
    [{'name': 'has space', 'text': 'y'}],
    [{'name': 'x', 'text': ''}],
    [{'name': 'x', 'text': 'y' * (STRING_TEXT_MAX + 1)}],
    [{'name': 'x', 'text': 'two\nlines'}],
    [{'name': 'x', 'text': 'nul\x00byte'}],
    [{'name': 'dup', 'text': 'a'}, {'name': 'dup', 'text': 'b'}],
])
def test_strings_validation_refuses(strings):
    with pytest.raises(GoopError):
        build_section(make_spec(strings))


def test_strings_max_count():
    entries = [{'name': f's{i:02d}', 'text': 'x'} for i in range(STRINGS_MAX)]
    assert len(build_section(make_spec(entries))['strings']) == STRINGS_MAX
    too_many = entries + [{'name': 'one_more', 'text': 'x'}]
    with pytest.raises(GoopError):
        build_section(make_spec(too_many))


# ---- emission ---------------------------------------------------------------

def test_inject_strings_emits_decls_and_touches():
    out = inject_strings(STUB_MAIN, ENTRIES)
    for entry in ENTRIES:
        assert f'/include:bramble_str_{entry["name"]}' in out
        assert f'extern "C" const char bramble_str_{entry["name"]}[]' in out
        assert json.dumps(entry['text']) in out
        touches = out.count(f'bramble_prov_sink ^= *reinterpret_cast<const '
                            f'volatile unsigned char*>('
                            f'bramble_str_{entry["name"]});')
        assert touches == 2  # tick loop AND checksum loop


def test_inject_strings_chunks_long_text():
    text = 'z' * 2400
    out = inject_strings(STUB_MAIN, [{'name': 'big', 'text': text}])
    assert out.count(json.dumps('z' * 1000)) == 2   # two full chunks
    assert json.dumps('z' * 400) in out             # remainder chunk
    assert f'"{text}"' not in out                   # never one giant literal


def test_inject_strings_anchor_uniqueness():
    doubled = STUB_MAIN + STUB_MAIN
    with pytest.raises(GoopError, match='anchor not unique'):
        inject_strings(doubled, ENTRIES)


# ---- build.formats (owner 2026-10-16: format strings come from JSON) -------

VALID_TICK = 'tick %5d  alive %3d v %3d  score %d-%d  cp owner %d\n'
VALID_SUMMARY = ('SUMMARY ticks=%d seed=%llu alive0=%d alive1=%d '
                 'score0=%d score1=%d owner=%d checksum=%016llx\n')


def make_formats_spec(formats):
    spec = make_spec()
    spec['build']['formats'] = formats
    return spec


def test_build_section_formats_roundtrip():
    custom = {'tick': 'T %5d | a %3d | v %3d | s %d-%d | o %d\n',
              'summary': ('S ticks=%d seed=%llu alive0=%d alive1=%d score0=%d '
                          'score1=%d owner=%d checksum=%016llx\n')}
    assert build_section(make_formats_spec(custom))['formats'] == custom


def test_build_section_formats_absent():
    assert build_section(make_spec())['formats'] is None


@pytest.mark.parametrize('formats', [
    'not-a-dict',
    {'tick': VALID_TICK},
    {'tick': 'x', 'summary': 'y', 'extra': 'z'},
    {'tick': 'no newline %5d %3d %3d %d-%d %d\n'.rstrip('\n'),
     'summary': VALID_SUMMARY},
    {'tick': 'two\nlines %5d %3d %3d %d-%d %d\n', 'summary': VALID_SUMMARY},
    {'tick': 'dropped %3d %3d %d-%d %d\n', 'summary': VALID_SUMMARY},
    {'tick': '%5d %5d %5d %5d %d-%d %d\n', 'summary': VALID_SUMMARY},
    {'tick': 'x' * 60 + '%5d %3d %3d %d-%d %d\n', 'summary': VALID_SUMMARY},
    {'tick': 'bad\x7fchar %5d %3d %3d %d-%d %d\n', 'summary': VALID_SUMMARY},
    {'tick': VALID_TICK,
     'summary': ('dropped %d alive0=%d alive1=%d score0=%d score1=%d '
                 'owner=%d checksum=%016llx\n')},
])
def test_formats_validation_refuses(formats):
    with pytest.raises(GoopError):
        build_section(make_formats_spec(formats))
