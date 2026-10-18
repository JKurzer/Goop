"""Extract PDF text to a .txt for review (read-only on the PDF)."""
import sys

from pypdf import PdfReader

src, dst = sys.argv[1], sys.argv[2]
reader = PdfReader(src)
with open(dst, 'w', encoding='utf-8', newline='\n') as out:
    for i, page in enumerate(reader.pages):
        out.write(f'\n===== PAGE {i + 1} =====\n')
        out.write(page.extract_text() or '')
        out.write('\n')
print('pages:', len(reader.pages))
meta = reader.metadata or {}
print('title:', meta.get('/Title'))
print('author:', meta.get('/Author'))
