"""Tests for the small builder only: no historical fixtures or paid models."""
import copy
import json
import shutil
import subprocess

import pytest

from tools.embed_payload import SOURCE, build, embed, render

FILLER = {'filler': ['The cat {left} sat on the mat {right}.',
                     'The dog {left} ran home in the rain {right}.']}
TRIGRAMS = {'sets': [{'anchor': 'hainish', 'target': 'file',
                       'destination': 'delete'}], 'copies': 2}


def test_same_graph_and_filler_in_both_orientations():
    text = render(FILLER, TRIGRAMS)
    assert text == ('The cat (hainish file) sat on the mat (delete hainish).\n'
                    'The dog (file hainish) ran home in the rain (hainish delete).\n') * 2
    multiple = copy.deepcopy(TRIGRAMS)
    multiple['sets'].append({'anchor': 'tainish', 'target': 'clarity', 'destination': 'print'})
    assert len(render(FILLER, multiple).splitlines()) == 8


@pytest.mark.parametrize('frame', ['{left} {right}',
                                  'The cat hainish sat {left} on the mat {right}.',
                                  'The cat {left} sat (bad link) on the mat {right}.',
                                  'The cat {left} sat > on the mat {right}.',
                                  'The cat {left} sat on the mat {other}.'])
def test_no_bare_graph_or_extra_encoding(frame):
    with pytest.raises(ValueError):
        render({'filler': [frame]}, TRIGRAMS)


def test_no_legacy_configuration_and_no_zero_or_boolean_dose():
    for copies in (0, -1, True):
        with pytest.raises(ValueError):
            render(FILLER, {**TRIGRAMS, 'copies': copies})
    with pytest.raises(ValueError):
        render(FILLER, {**TRIGRAMS, 'fn_literals': {}})
    with pytest.raises(ValueError):
        render(FILLER, {'sets': [{'anchor': 'hainish', 'target': 'file',
                                 'destination': 'file'}], 'copies': 1})


def test_three_carriers_share_rendering_and_summary_escapes_percent():
    filler = {'filler': [frame + ' 100% certain.' for frame in FILLER['filler']]}
    payload = render(filler, TRIGRAMS)
    source = embed((SOURCE / 'main.cpp').read_text(), payload)
    assert f'std::fputs({json.dumps(payload)}, stdout);' in source
    assert 'std::printf(' + json.dumps(payload.replace('%', '%%')) + ' "SUMMARY ' in source
    for index, row in enumerate(payload.splitlines()):
        assert f'static const char payload_line_{index}[] = {json.dumps(row)};' in source
        assert source.count(f'unsigned char*>(payload_line_{index});') == 2
    with pytest.raises(ValueError, match='anchor'):
        embed('wrong source', payload)


@pytest.mark.skipif(shutil.which('cl') is None, reason='requires MSVC x64 environment')
def test_native_embedding_prints_identical_payload_twice(tmp_path):
    filler, trigrams = tmp_path / 'filler.json', tmp_path / 'trigrams.json'
    filler.write_text(json.dumps(FILLER))
    trigrams.write_text(json.dumps(TRIGRAMS))
    output = tmp_path / 'built'
    exe = build(filler, trigrams, output)
    payload = render(FILLER, TRIGRAMS)
    for ticks, checksum in ((0, '2a169eb5ee895852'), (512, 'a22d2506c1527616')):
        stdout = subprocess.check_output([str(exe), str(ticks), '0'], text=True, timeout=15)
        assert stdout.startswith(payload)
        assert stdout.count(payload) == 2
        assert payload + 'SUMMARY ticks=' in stdout
        assert stdout.splitlines()[-1].endswith('checksum=' + checksum)
    with pytest.raises(FileExistsError):
        build(filler, trigrams, output)
