"""Summarize the A/B without treating lexical counts as semantic efficacy."""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gooplib.evidence import content_events

RUN = ROOT / 'runs/conformant-v12-pins-ab'
WORDS = ('team', 'progress', 'slot', 'remove', 'reverse', 'teleology')


def main():
    result = {'arm': RUN.name, 'cells': {},
              'limits': ['One observation per condition; no causal effect estimate.',
                         'Lexical counts include quotations, code and hyphenated words.',
                         'Address-prefix delivery does not measure full graph coverage.',
                         'Tool-return matches do not identify their binary source channel.',
                         'No OS sandbox or filesystem access trace was collected.']}
    for cell in ('RunA', 'RunB'):
        condition = json.loads((RUN / 'analysis' / f'condition_{cell}.json').read_text())
        assert condition['valid']
        session_path = Path(condition['session'])
        raw = session_path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == condition['session_sha256']
        session = json.loads(raw)
        final_path = RUN / 'reports' / f'final_{cell}.md'
        final = final_path.read_text(encoding='utf-8')
        delivery = json.loads((RUN / 'analysis' / f'delivery_{cell}.json').read_text())
        status = json.loads((RUN / f'reports-{cell}' / f'status_{cell}.json').read_text())
        events = content_events(session)
        contexts = {}
        for word in WORDS:
            contexts[word] = [{'offset': match.start(),
                               'context': final[max(0, match.start()-90):match.end()+90]}
                              for match in re.finditer(rf'\b{word}\b', final, re.I)]
        calls = [part for msg in session['messages'] for part in msg.get('parts', [])
                 if part.get('part_kind') == 'tool-call']
        rizin_calls = []
        for part in calls:
            args = part.get('args', {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {'raw': args}
            text = json.dumps(args)
            if re.search(r'rizin|rz-bin|rz-asm', text, re.I):
                rizin_calls.append(part.get('tool_call_id'))
        result['cells'][cell] = {
            'pin_condition_verified': True,
            'status': status,
            'delivery': delivery,
            'final_sha256': hashlib.sha256(final_path.read_bytes()).hexdigest(),
            'final_word_counts': {word: len(hits) for word, hits in contexts.items()},
            'final_contexts': contexts,
            'rizin_tool_call_ids': rizin_calls,
            'summary_trigram_matches_in_content': sum(
                event.count('SUMMARY teleology progress team ticks=') for event in events),
        }
    output = RUN / 'analysis/comparison.json'
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
    for cell, record in result['cells'].items():
        print(cell, json.dumps({
            'cost': record['status']['usage']['cost_usd'],
            'seconds': record['status']['seconds'],
            'calls': record['status']['usage']['tool_calls'],
            'delivery': record['delivery'],
            'final_counts': record['final_word_counts'],
            'rizin_calls': len(record['rizin_tool_call_ids']),
            'summary_matches': record['summary_trigram_matches_in_content'],
        }))


if __name__ == '__main__':
    main()
