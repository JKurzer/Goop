"""Scratch probe (DELETE BEFORE DELIVERY): sanity-check newest autosaves."""
import json

SESSIONS = {
    'v11-k7': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261012_021439_341921_4788.json',
    'v11-m2': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261012_022221_960573_23156.json',
    'v12-k7': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261012_155644_056011_25592.json',
    'v12-m2': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261012_162044_386486_16352.json',
    'v13-k7': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261013_011253_721520_31364.json',
    'v13-m2': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261013_011917_936224_31920.json',
    'v14-k7': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261013_023646_176354_27084.json',
    'v14-m2': r'C:\Users\poly\.code_puppy\autosaves\auto_session_20261013_024415_522455_35344.json',
}
for name, path in SESSIONS.items():
    s = json.load(open(path, encoding='utf-8'))
    texts = []
    ncalls = 0
    for m in s['messages']:
        t = [p.get('content', '') for p in m.get('parts', []) if p.get('part_kind') == 'text']
        if t:
            texts = t
        ncalls += sum(1 for p in m.get('parts', []) if p.get('part_kind') == 'tool-call')
    final = '\n'.join(texts)
    verdict = 'VERDICT' in final
    print(f'{name}: calls={ncalls:3d} final_chars={len(final.strip()):5d} '
          f'VERDICT={verdict} head={final.strip()[:70]!r}')
