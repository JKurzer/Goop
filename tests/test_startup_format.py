"""Opt-in startup output: pinned, printable rows with safe framing."""

import pytest

from gooplib import GoopError, NATIVE_SRC
from gooplib.native_build import inject_startup_format
from gooplib.specs import build_section

GRAPH = 'teleology team reverse | teleology progress team | teleology reverse remove'
FORMAT = f'STARTUP seed {GRAPH}\n'


def spec_with_format(text):
    return {'payload': {'sha256': '0' * 64},
            'build': {'slots': 2, 'slot_size': 16,
                      'doses': {'RunA': 0, 'RunB': 2},
                      'startup_format': text}}


def test_startup_format_is_opt_in_and_preserves_complete_graph():
    spec = spec_with_format(FORMAT)
    assert build_section(spec)['startup_format'] == FORMAT
    del spec['build']['startup_format']
    assert build_section(spec)['startup_format'] is None


@pytest.mark.parametrize('invalid', [
    'missing newline', 'extra\n\nnewline\n', 'bad %d\n', 'bad\tchar\n',
    'A' * 2500 + '\n', 'ok\n' + 'A' * 191 + '\n',
])
def test_startup_format_refuses_unsafe_or_overwide_multiline_input(invalid):
    with pytest.raises(GoopError, match='startup_format'):
        build_section(spec_with_format(invalid))


def test_multiline_bounded_format_and_legacy_line_still_validate():
    multiline = 'STARTUP seed graph 01/02: teleology team\n'
    multiline += 'STARTUP seed graph 02/02: reverse remove\n'
    spec = spec_with_format(multiline)
    assert build_section(spec)['startup_format'] == multiline
    # Already built v21 uses a long single line; do not invalidate its spec.
    assert build_section(spec_with_format('x' * 1952 + '\n'))['startup_format']


def test_long_format_can_hold_full_graph_and_zero_probe_is_explicit():
    full = f'STARTUP seed full_graph={"teleology team reverse " * 40}\n'
    spec = spec_with_format(full)
    spec['build']['startup_zero_probe'] = True
    assert build_section(spec)['startup_format'] == full
    assert build_section(spec)['startup_zero_probe'] is True
    del spec['build']['startup_format']
    with pytest.raises(GoopError, match='startup_zero_probe'):
        build_section(spec)


def test_startup_printf_uses_named_format_before_argument_parsing():
    source = (NATIVE_SRC / 'main.cpp').read_text(encoding='utf-8')
    generated = inject_startup_format(source, FORMAT)
    assert generated.count('static const char bramble_startup_format[]') == 1
    assert generated.count('std::printf(bramble_startup_format);') == 1
    assert generated.index('std::printf(bramble_startup_format);') < generated.index(
        'int ticks =')
    assert GRAPH in generated
    gated = inject_startup_format(source, FORMAT, zero_probe=True)
    assert gated.count('bramble_startup_format[]') == 1
    assert gated.count('std::printf(bramble_startup_format);') == 1
    assert gated.index('uint64_t seed =') < gated.index('if (ticks == 0 && seed == 0)')
    with pytest.raises(GoopError, match='anchor not unique'):
        inject_startup_format('not main.cpp', FORMAT)
