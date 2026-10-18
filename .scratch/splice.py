from pathlib import Path

path = Path('gooplib/bridging.py')
lines = path.read_text(encoding='utf-8').splitlines()
start = next(i for i, line in enumerate(lines)
             if line.startswith('# --- parsing / integrity ---'))
end = next(i for i, line in enumerate(lines)
           if line.startswith('# --- carrier statistics ---'))
print(f'deleting lines {start + 1}..{end} ({end - start} lines)')
print('first deleted:', lines[start])
print('last deleted :', lines[end - 1])
print('kept after  :', lines[end])
path.write_text('\n'.join(lines[:start] + lines[end:]) + '\n',
                encoding='utf-8', newline='\n')
