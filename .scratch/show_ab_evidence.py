"""Inspect saved A/B evidence snippets only. No launches."""
import json
from pathlib import Path
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
RUN = Path(__file__).resolve().parents[1] / 'runs/conformant-v12-pins-ab'
evidence = json.loads((RUN / 'analysis/investigation-evidence.json').read_text(encoding='utf-8'))
for cell, record in evidence['cells'].items():
    print('\n===', cell, '===')
    session = json.loads(Path(record['session']).read_bytes())
    returns = {part.get('tool_call_id'): part for msg in session['messages']
               for part in msg.get('parts', []) if part.get('part_kind') == 'tool-return'}
    for call in record['calls']:
        command = call['args'].get('command', '')
        if call['index'] in record['rizin_calls']:
            returned = returns.get(call['id'], {}).get('content', {})
            if isinstance(returned, dict):
                print('RIZIN CALL', call['index'], 'exit=', returned.get('exit_code'),
                      'success=', returned.get('success'),
                      'return head=', str(returned.get('stdout', returned.get('content','')))[:250])
            else:
                print('RIZIN CALL', call['index'], 'return head=', str(returned)[:250])
        # Exact command contexts around analyst-authored truncation/IO.
        for match in re.finditer(r'(?:\[:(?:24|240|244|256)\]|teleology|print\(hex|open\(p,)', command):
            print('COMMAND', call['index'], command[max(0,match.start()-80):match.end()+180])
    for row in record['anchored_evidence'][:6]:
        print('SLOT', row['slot'], 'depth', row['prefix_chars'], '/', row['line_chars'],
              'ROW', row['row'])
    for event in record['role_events']:
        counts = {key: value for key,value in event['form_substring_counts'].items() if value}
        print('RETURN', event['return_id'], counts)
        for row in event['role_rows'][:2]:
            print(' EVIDENCE', row[:350])
    # Show full command of any unresolved dynamic file target for manual review.
    for call in record['calls']:
        if call.get('python_io',{}).get('io_calls'):
            if any(op.get('expression','').startswith(('open(p,', 'subprocess.run([p,'))
                   for op in call['python_io']['io_calls']):
                print('DYNAMIC PATH CALL', call['index'], call['args']['command'][:700])
