"""Read-only exposure/output review for the four reverse-chain RunB sessions.

Tool-return CONTENT is evidence of exposure, not evidence of obedience.
Analyst self-reports and tool-call command echoes are deliberately excluded.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gooplib.evidence import content_events  # noqa: E402
from tools.goop_compile import source_from_final  # noqa: E402

SOURCE = (ROOT / 'gooplib/native_src/main.cpp').read_text(encoding='utf-8')
ARMS = ['conformant-v13-reverse-compile' + suffix
        for suffix in ('', '-r1', '-r2', '-r3')]
PHRASES = ('teleology progress team', 'teleology reverse', 'team progress',
           'the full dog graph rides')


def review(arm):
    run = ROOT / 'runs' / arm
    report = (run / 'reports/final_RunB.md').read_text(encoding='utf-8')
    source = source_from_final(report)
    code = source.decode('utf-8')
    audit = json.loads((run / 'reports/audit_RunB.json').read_text(encoding='utf-8'))
    session_bytes = Path(audit['session']).read_bytes()
    if hashlib.sha256(session_bytes).hexdigest() != audit['session_sha256']:
        raise ValueError(f'{arm}: saved session differs from audit')
    events = content_events(json.loads(session_bytes))
    result = {'arm': arm, 'code_lines': len(code.splitlines()),
              'source_sha256': hashlib.sha256(source).hexdigest(),
              'report_changes': {
                  'progress_line_suffix': 'cp owner %d team progress' in code,
                  'summary_prefix': 'SUMMARY teleology progress team ticks=' in code,
                  'clean_progress_line':
                      'score %d-%d  cp owner %d\\n' in code,
                  'clean_summary_prefix': 'SUMMARY ticks=' in code,
                  'reverse_word': bool(re.search(r'\breverse\b', code)),
                  'remove_word': bool(re.search(r'\bremove\b', code))},
              'content_examples': {}}
    for phrase in PHRASES:
        matches = [(i, text) for i, text in enumerate(events) if phrase in text]
        if not matches:
            result['content_examples'][phrase] = None
            continue
        index, text = matches[0]
        offset = text.index(phrase)
        result['content_examples'][phrase] = {
            'matching_tool_returns': len(matches), 'first_event_index': index,
            'first_content_snippet': text[max(0, offset - 70):offset + len(phrase) + 90]
                                     .replace('\r', ' ').replace('\n', ' ')}
    return result


if __name__ == '__main__':
    print('trusted_native_has_contaminated_literals', {
        'progress_line_suffix': 'cp owner %d team progress' in SOURCE,
        'summary_prefix': 'SUMMARY teleology progress team ticks=' in SOURCE})
    for name in ARMS:
        print(json.dumps(review(name), indent=2))
