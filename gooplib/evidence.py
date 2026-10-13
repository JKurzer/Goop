"""Session-evidence extraction: audits and the CONTENT layer.

Ports bramble tools/audit_native_session.py (calls/returns/final, never
reasoning) plus the CONTENT-layer rules of bramble
eval/native/aftermath/MEASUREMENT_REVIEW.md:

- CONTENT = stdout/stderr/content/output fields of dict returns, plus the
  string bodies of spill/read_tool_result pages with embedded shell JSON
  unwrapped first (bug 2 fix: the embedded ``command`` echo is not content).
- Spill notices contribute nothing; a page's ``[handle ...]`` banner line
  is not content.
- ECHO (tool-call args, embedded command/args fields) never enters CONTENT.
"""
import json

CONTENT_KEYS = ('stdout', 'stderr', 'content', 'output')
SPILL_MARKER = '[Tool output too large'
HANDLE_MARKER = "[handle '"


def extract_audit(session):
    """(calls, returns, final) from a saved session; no reasoning exported.

    One status row per return, dict AND string — MEASUREMENT_REVIEW bug 8:
    in v13-m2/v14 the string returns carry all delivery evidence, and the
    old audit silently dropped them.
    """
    calls = []
    returns = []
    final_texts = []
    for message in session['messages']:
        texts = []
        for part in message.get('parts', []):
            kind = part.get('part_kind')
            if kind == 'tool-call':
                args = part.get('args')
                if isinstance(args, str):
                    args = json.loads(args)
                calls.append({'tool': part['tool_name'], 'args': args,
                              'id': part.get('tool_call_id')})
            elif kind == 'tool-return':
                returns.append(_return_row(part))
            elif kind == 'text':
                texts.append(part.get('content', ''))
        if texts:
            final_texts = texts
    return calls, returns, '\n'.join(final_texts)


def _return_row(part):
    content = part.get('content')
    row = {'tool': part['tool_name'], 'id': part.get('tool_call_id')}
    if isinstance(content, dict):
        row.update(kind='result', success=content.get('success'),
                   exit_code=content.get('exit_code'), error=content.get('error'),
                   stderr=content.get('stderr'))
    else:
        text = content if isinstance(content, str) else json.dumps(content)
        row.update(kind='spill' if text.startswith(SPILL_MARKER) else 'string',
                   chars=len(text))
    return row


def split_return_text(text):
    """CONTENT text of one string return ('' when it carries none).

    Spill notices carry nothing (their content lives in the handle store
    until paged). A read_tool_result page is a banner line plus a body; a
    body that is serialized shell JSON is unwrapped so only its CONTENT_KEYS
    fields count — the typed ``command`` inside is echo, not evidence.
    """
    if text.startswith(SPILL_MARKER):
        return ''
    candidate = text
    if candidate.startswith(HANDLE_MARKER):
        newline = candidate.find('\n')
        candidate = candidate[newline + 1:] if newline != -1 else ''
    if candidate.lstrip().startswith('{'):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return '\n'.join(parsed[key] for key in CONTENT_KEYS
                             if isinstance(parsed.get(key), str) and parsed[key])
    return candidate


def content_events(session):
    """CONTENT-layer event texts, one per contributing tool return."""
    events = []
    for message in session['messages']:
        for part in message.get('parts', []):
            if part.get('part_kind') != 'tool-return':
                continue
            content = part.get('content')
            if isinstance(content, dict):
                fields = [str(content[key]) for key in CONTENT_KEYS
                          if isinstance(content.get(key), str) and content[key]]
                if fields:
                    events.append('\n'.join(fields))
            elif isinstance(content, str):
                text = split_return_text(content)
                if text:
                    events.append(text)
    return events
