"""Shared spec loading/validation for goop utilities.

Every utility reads run_dir/spec.json and only touches its own section.
Unknown keys inside a section are rejected loudly: a typo'd key must never
silently change a run. Keep this module minimal — it is a shared contract.
"""
import json
from pathlib import Path


class SpecError(ValueError):
    """Any malformed spec content: bad JSON, wrong types, unknown keys."""


def load_json(path):
    """Parse a JSON file into a dict; fail loud on missing/bad/non-object."""
    path = Path(path)
    if not path.is_file():
        raise SpecError(f'spec file not found: {path}')
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise SpecError(f'invalid JSON in {path}: {exc}') from exc
    if not isinstance(data, dict):
        raise SpecError(f'{path} must contain a JSON object at top level')
    return data


def check_keys(mapping, allowed, required=(), where='spec'):
    """Reject unknown keys and require the mandatory ones.

    allowed: iterable of permitted key names. required: subset that must be
    present. Raises SpecError listing every offending key.
    """
    if not isinstance(mapping, dict):
        raise SpecError(f'{where} must be a JSON object')
    allowed, required = set(allowed), set(required)
    if not required <= allowed:
        raise SpecError(f'internal error: required keys {sorted(required - allowed)} '
                        f'not in allowed set for {where}')
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise SpecError(f'{where} has unknown keys: {unknown} '
                        f'(allowed: {sorted(allowed)})')
    missing = sorted(required - set(mapping))
    if missing:
        raise SpecError(f'{where} is missing required keys: {missing}')
    return mapping


def resolve_path(value, base, where='path'):
    """Resolve a spec path: absolute stays, relative resolves against base."""
    if not isinstance(value, str) or not value:
        raise SpecError(f'{where} must be a nonempty path string')
    path = Path(value)
    return path if path.is_absolute() else Path(base) / path
