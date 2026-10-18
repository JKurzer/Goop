"""Print the dose-carrying tool return (k7 session, 'unpacked 711192'),
showing each line that contains our material or a truncation marker —
as the analyst's context actually saw it."""
import json

PATH = (r'C:\Users\poly\.code_puppy\autosaves'
        r'\auto_session_20261016_004205_063901_36832.json')
session = json.load(open(PATH, encoding='utf-8'))
content = None
for msg in session['messages']:
    for part in msg.get('parts', []):
        text = part.get('content', '')
        if 'unpacked 711192' in text:
            content = text
if content is None:
    raise SystemExit('return not found')
lines = content.split('\n')
print(f'total lines in return: {len(lines)}; total chars: {len(content)}')
for i, line in enumerate(lines):
    if 'initialization' in line or '[truncated]' in line or line.startswith('unpacked'):
        marker = ' <<<CUT>>>' if line.rstrip().endswith('[truncated]') else ''
        print(f'--- [{i}] ({len(line)} chars){marker} ---')
        print(line[:400] + ('' if len(line) <= 400
                            else f'  <<{len(line) - 400} more chars>>'))
