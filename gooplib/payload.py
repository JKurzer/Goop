"""Shared payload primitives: the edge regexes and byte helpers.

The classic corpus-remap pipeline (frame transform, predicate compose,
incorrect_terms graft, trigram_sets placement + measurement) is DELETED
(owner ruling 2026-10-15: "delete the code paths" — the classic specs it
served were burned in the same session's corrections). The surviving
compose engine is gooplib.bridging (megaline + pairs), driven by
tools/goop_payload.py.
"""
import hashlib
import re

# Lookahead retains both edges in "a and b and c". No punctuation bridges.
PAIR = re.compile(r'(?=\b([a-z]+) and ([a-z]+)\b)')
WORD = re.compile(r'\b[a-z]+\b')


# --- encoding --------------------------------------------------------------

def encode_payload(lines):
    return ('\n'.join(lines) + '\n').encode('utf-8')


def sha256(data):
    return hashlib.sha256(data).hexdigest()
