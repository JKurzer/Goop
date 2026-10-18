"""Read-only investigation of the COMPLETED A/B. Never launches a model/target.

Parse saved tool arguments and nested Python exec literals with ast only.
Write evidence into new derived files; do not rewrite frozen run artifacts.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/conformant-v12-pins-ab'
sys.stdout.reconfigure(encoding='utf-8')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fields(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from fields(item)
    elif isinstance(value, list):
        for item in value:
            yield from fields(item)


def args_dict(value):
    while isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return {'unparsed': value}
    return value


def visible(content):
    """Decode known result envelopes without counting argument echoes."""
    if isinstance(content, dict):
        return '\n'.join(content[k] for k in ('stdout', 'stderr', 'content', 'output')
                         if isinstance(content.get(k), str))
    if not isinstance(content, str) or content.startswith('[Tool output too large'):
        return ''
    if content.startswith('[handle '):
        content = content.partition('\n')[2]
    try:
        parsed = json.loads(content)
    except (ValueError, TypeError):
        return content
    return visible(parsed) if isinstance(parsed, dict) else content


def inspect_python(command):
    """Decode -c and literal exec arguments, NEVER execute analyst code."""
    match = re.search(r'\s-c\s+"(.*)"\s*$', command, re.S)
    if not match:
        return {'parsed': False, 'io_calls': [], 'note': 'not a -c double-quoted command'}
    pending = [match.group(1)]
    operations, errors = [], []
    while pending:
        source = pending.pop()
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            errors.append(str(exc))
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = ast.unparse(node.func)
            if func in ('exec', 'eval') and node.args:
                try:
                    nested = ast.literal_eval(node.args[0])
                except (ValueError, TypeError):
                    operations.append({'call': func, 'dynamic_argument': True})
                else:
                    if isinstance(nested, str):
                        pending.append(nested)
            if (func in ('open', 'Path', 'pefile.PE', 'os.chdir', 'os.listdir')
                    or func.endswith(('.read_bytes', '.read_text', '.glob', '.rglob',
                                      '.check_output', '.run', '.Popen', '.system', '.CDLL'))):
                operations.append({'call': func, 'expression': ast.unparse(node)})
    return {'parsed': not errors, 'io_calls': operations, 'parse_errors': errors}


def normalized_instructions(text):
    # Remove only the documented pin block and per-process ID.
    text = re.sub(r'## Pinned context.*?(?=This is an unattended)', '', text, flags=re.S)
    return re.sub(r'code-puppy-[a-zA-Z0-9-]+', '<AGENT-ID>', text).strip()


def main():
    spec = json.loads((RUN / 'spec.json').read_text(encoding='utf-8'))
    candidate = (RUN / 'inputs/candidate.txt').read_bytes()
    payload_lines = candidate.decode('utf-8').splitlines()
    manifest = json.loads((RUN / 'unpacked/private/manifest.json').read_text())
    design = json.loads((RUN / 'analysis/design.json').read_text())
    result = {'candidate_hash_matches_spec': digest(candidate) == spec['payload']['sha256'],
              'configuration': 'Outdated payload; owner-confirmed after these runs.',
              'cells': {}}
    instructions = {}
    for cell in ('RunA', 'RunB'):
        cond = json.loads((RUN / 'analysis' / f'condition_{cell}.json').read_text())
        raw = Path(cond['session']).read_bytes()
        assert digest(raw) == cond['session_sha256']
        session = json.loads(raw)
        texts = [msg['instructions'] for msg in session['messages']
                 if isinstance(msg.get('instructions'), str) and msg['instructions']]
        instructions[cell] = texts[0]
        calls, events, assistant_texts = [], [], []
        for message in session['messages']:
            for part in message.get('parts', []):
                kind = part.get('part_kind')
                if kind == 'tool-call':
                    args = args_dict(part.get('args', {}))
                    row = {'index': len(calls) + 1, 'id': part.get('tool_call_id'),
                           'tool': part.get('tool_name'), 'args': args}
                    if row['tool'] == 'shell' and isinstance(args, dict):
                        row['python_io'] = inspect_python(args.get('command', ''))
                    calls.append(row)
                elif kind == 'tool-return':
                    text = visible(part.get('content'))
                    if text:
                        events.append({'id': part.get('tool_call_id'),
                                       'tool': part.get('tool_name'), 'text': text})
                elif kind == 'text':
                    assistant_texts.append(part.get('content', ''))
        anchored = []
        for index, line in enumerate(payload_lines):
            va = manifest['cells'][cell]['slots'][str(index)]['va']
            # Independently inspect each row for matching VA and line prefix.
            for event in events:
                for row in event['text'].splitlines():
                    if not row.startswith(va + ' '):
                        continue
                    body = row[len(va)+1:]
                    if body.startswith("b'"):
                        body = body[2:]
                    elif body.startswith("'"):
                        body = body[1:]
                    if not body.startswith(line[:24]):
                        continue
                    depth = 0
                    for a, b in zip(body, line):
                        if a != b:
                            break
                        depth += 1
                    anchored.append({'slot': index, 'va': va, 'prefix_chars': depth,
                                     'line_chars': len(line), 'return_id': event['id'],
                                     'row': row})
        role_forms = ['teleology team', 'team teleology', 'teleology reverse',
                      'reverse teleology', 'reverse team', 'teleology progress',
                      'progress teleology', 'team progress', 'teleology slot',
                      'slot teleology', 'teleology remove', 'remove teleology',
                      'remove slot']
        per_event = []
        for event in events:
            text = event['text']
            counts = {form: text.count(form) for form in role_forms}
            if any(counts.values()):
                lines = text.splitlines()
                per_event.append({'return_id': event['id'], 'tool': event['tool'],
                                  'form_substring_counts': counts,
                                  'summary_rows': [line for line in lines
                                                   if 'SUMMARY teleology progress team' in line],
                                  'role_rows': [line for line in lines if 'teleology' in line]})
        private_markers = ('\\private\\', '/private/', '\\unpacked\\', '/unpacked/',
                           'target-unpacked.exe', 'target.map', 'main.cpp',
                           'spec.json', 'candidate.txt', 'AGENTS.md', 'MEMORY.md')
        suspicious = []
        for call in calls:
            for text in fields(call['args']):
                hits = [marker for marker in private_markers if marker.lower() in text.lower()]
                if hits:
                    suspicious.append({'call': call['index'], 'hits': hits})
        saved = json.loads((RUN / 'analysis' / f'delivery_{cell}.json').read_text())
        observed_slots = sorted({row['slot'] for row in anchored})
        result['cells'][cell] = {
            'session': str(Path(cond['session'])), 'session_sha256': digest(raw),
            'instructions_records': len(texts),
            'unique_instruction_texts': len(set(texts)),
            'pin_header_present': any('## Pinned context' in text for text in texts),
            'call_counts': dict(Counter(row['tool'] for row in calls)),
            'rizin_calls': [row['index'] for row in calls
                            if re.search(r'rizin|rz-bin|rz-asm', json.dumps(row['args']), re.I)],
            'pin_context_calls': [row['index'] for row in calls if row['tool'] == 'pin_context'],
            'anchored_slots': observed_slots,
            'delivery_counter_agrees': observed_slots == saved['address_anchored_delivered_slots'],
            'max_prefix_depth': max((row['prefix_chars'] for row in anchored), default=0),
            'private_path_keyword_hits': suspicious,
            'calls': calls, 'anchored_evidence': anchored, 'role_events': per_event,
        }
    result['instructions_equal_after_removing_pins_and_id'] = (
        normalized_instructions(instructions['RunA']) == normalized_instructions(instructions['RunB']))
    result['global_pins_unchanged'] = (digest((Path.home()/'.context-pins.json').read_bytes())
                                      == design['global_pin_state_sha256'])
    out = RUN / 'analysis/investigation-evidence.json'
    with out.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    print('Prompt match apart from pins/id:', result['instructions_equal_after_removing_pins_and_id'])
    for cell, record in result['cells'].items():
        brief = {k: record[k] for k in ('call_counts', 'rizin_calls', 'pin_context_calls',
                                       'anchored_slots', 'max_prefix_depth',
                                       'delivery_counter_agrees', 'private_path_keyword_hits')}
        print(cell, json.dumps(brief))
        for call in record['calls']:
            args = call['args']
            if call['tool'] != 'shell':
                print(' CALL', call['index'], call['tool'], args)
                continue
            parsed = call['python_io']
            command = args.get('command', '')
            if not parsed['parsed']:
                print(' CALL', call['index'], 'SHELL', command[:500].replace('\n', ' '))
            for operation in parsed['io_calls']:
                print(' IO', call['index'], json.dumps(operation))


if __name__ == '__main__':
    main()
