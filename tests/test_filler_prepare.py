"""Literal filler bytes survive copying, while runtime rows remain bounded."""
import pytest

from tools.goop_filler_prepare import first_lines, runtime_text


def test_excerpt_retains_crlf_and_trailing_spaces():
    source = b'Cat sat.  \r\nDog ran. \r\nThird line.\r\n'
    excerpt, lines = first_lines(source, 2)
    assert excerpt == b'Cat sat.  \r\nDog ran. \r\n'
    assert runtime_text(lines, 2, 2) == (
        b'Cat sat.  \nDog ran. \n' * 2)
    assert (excerpt * 3)[:len(excerpt)] == source[:len(excerpt)]


def test_incomplete_or_unsafe_excerpt_is_refused():
    with pytest.raises(ValueError, match='CRLF'):
        first_lines(b'Cat sat.\r\npartial', 2)
    with pytest.raises(ValueError, match='unsafe'):
        runtime_text([b'bad %s\r\n'], 1, 1)
    with pytest.raises(ValueError, match='range'):
        runtime_text([b'Cat sat.\r\n'], 2, 1)
