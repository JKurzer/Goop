"""Local Capstone repro: x86-64 cannot encode a long ASCII operand."""

import capstone
import pytest

GRAPH = b'teleology team reverse | teleology progress team | teleology reverse remove'


def disassemble(code, *, skipdata=False):
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    decoder.skipdata = skipdata
    return list(decoder.disasm(code, 0x1000))


def printed(instructions):
    return '\n'.join(f'{ins.mnemonic} {ins.op_str}' for ins in instructions)


def test_rip_relative_displacement_is_four_bytes_and_printed_as_hex():
    code = b'\x48\x8d\x05' + b'TELE'  # lea rax, [rip + disp32]
    instructions = disassemble(code)
    assert len(instructions) == 1
    assert instructions[0].size == 7
    assert instructions[0].op_str == 'rax, [rip + 0x454c4554]'
    assert 'TELE' not in printed(instructions)
    print('RIP displacement:', printed(instructions))


def test_prefixes_reach_fifteen_bytes_but_cannot_hold_graph():
    longest_nop = b'\x66' * 14 + b'\x90'
    instructions = disassemble(longest_nop)
    assert len(instructions) == 1
    assert instructions[0].size == 15
    assert instructions[0].mnemonic == 'nop'
    assert instructions[0].op_str == ''

    overlong_nop = b'\x66' * 15 + b'\x90'
    assert disassemble(overlong_nop) == []
    with_skipdata = disassemble(overlong_nop, skipdata=True)
    assert with_skipdata
    assert all(ins.size <= 15 for ins in with_skipdata)
    print('15-byte NOP:', printed(instructions))
    print('16-byte overlong decode:', printed(with_skipdata))


def test_movabs_eight_byte_immediate_is_printed_as_number():
    instructions = disassemble(b'\x48\xb8' + GRAPH[:8])
    assert len(instructions) == 1
    assert instructions[0].size == 10
    assert instructions[0].mnemonic == 'movabs'
    assert 'teleolog' not in printed(instructions)
    print('8-byte immediate:', printed(instructions))


@pytest.mark.parametrize('payload', [GRAPH, GRAPH.ljust(256, b'A')],
                         ids=['75-byte-graph', '256-byte-block'])
def test_disassembling_payload_does_not_print_graph_as_one_operand(payload):
    instructions = disassemble(payload, skipdata=True)
    assert instructions
    assert all(ins.size <= 15 for ins in instructions)
    assert GRAPH.decode('ascii') not in printed(instructions)
    print('payload bytes:', len(payload), 'decoded instructions:', len(instructions),
          'largest instruction:', max(ins.size for ins in instructions))


@pytest.mark.parametrize(('code', 'expected'), [
    (b'\x48\x8d\x84\xc8' + b'TELE',
     'lea rax, [rax + rcx*8 + 0x454c4554]'),
    (b'\x48\xa1' + GRAPH[:8],
     'movabs rax, qword ptr [0x676f6c6f656c6574]'),
], ids=['sib-with-disp32', 'absolute-address-imm64'])
def test_other_address_operands_show_hex_not_ascii(code, expected):
    instructions = disassemble(code)
    assert len(instructions) == 1
    assert printed(instructions) == expected
    print('address operand:', printed(instructions))


def test_long_runs_of_different_prefixes_cannot_exceed_fifteen_bytes():
    decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    sizes = [ins.size for prefix in (b'\x66', b'\x67', b'\xf2',
                                    b'\xf3', b'\x2e', b'\x40')
             for count in range(257)
             for ins in decoder.disasm(prefix * count + b'\x90',
                                       0x1000, count=1)]
    assert sizes
    assert max(sizes) == 15
    print('prefix inputs:', 6 * 257, 'decoded:', len(sizes),
          'largest instruction:', max(sizes))


def test_linear_disassembly_decodes_bytes_even_after_jump_over_them():
    # A short jump skips the graph at runtime. The analyst used linear
    # c.disasm(), which still visits bytes immediately after the jump.
    code = b'\xeb' + bytes([len(GRAPH)]) + GRAPH
    instructions = disassemble(code, skipdata=True)
    assert instructions[0].mnemonic == 'jmp'
    assert instructions[1].address == 0x1002
    assert all(ins.size <= 15 for ins in instructions)
    assert GRAPH.decode('ascii') not in printed(instructions)
    print('jump-over graph:', printed(instructions[:3]))


def test_rep_string_instructions_name_memory_not_embedded_text():
    # REP MOVS/SCAS read memory through registers; none have a literal
    # text operand. The following bytes are not part of their instruction.
    for opcode in (b'\xa4', b'\xa5', b'\xac',
                   b'\xaa', b'\xa6', b'\xae'):
        instructions = disassemble(b'\xf3' + opcode + GRAPH)
        assert instructions
        assert instructions[0].size == 2
        assert GRAPH.decode('ascii') not in printed(instructions)
    print('REP string example:', printed(disassemble(b'\xf3\xa4')))


def test_bounded_jump_prefix_string_opcode_search_does_not_emit_graph():
    prefixes = (b'\x66', b'\x67', b'\xf2', b'\xf3',
                b'\x2e', b'\x40', b'\xf3\x66', b'\x67\x2e')
    opcodes = (b'\xa4', b'\xa5', b'\xac', b'\xaa', b'\xa6', b'\xae')
    attempts = 0
    largest = 0
    for skipdata in (False, True):
        decoder = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
        decoder.skipdata = skipdata
        for prefix in prefixes:
            for count in range(17):
                for opcode in opcodes:
                    for text_first in (False, True):
                        body = ((GRAPH + prefix * count + opcode) if text_first
                                else (prefix * count + opcode + GRAPH))
                        assert len(body) < 128  # one synthetic short jump
                        code = b'\xeb' + bytes([len(body)]) + body
                        instructions = list(decoder.disasm(code, 0x1000))
                        attempts += 1
                        assert instructions[0].mnemonic == 'jmp'
                        assert GRAPH.decode('ascii') not in printed(instructions)
                        largest = max(largest, *(ins.size for ins in instructions))
    assert attempts == 2 * len(prefixes) * 17 * len(opcodes) * 2
    assert largest <= 15
    print('synthetic variants:', attempts, 'largest instruction:', largest)
