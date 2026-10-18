"""Optional uncompressed RCDATA mirror of grouped function-literal text."""

RESOURCE_START = 0x4000
RCDATA = 10


def unique_bundles(block):
    """One resource per distinct complete bundle, in canonical order."""
    from gooplib.exports import block_texts

    return list(dict.fromkeys(block_texts(block))) if block.get('resource_carrier') else []


def write_resources(directory, texts):
    """Prepare .rc inputs for rc.exe; no C++ reference or runtime side effect."""
    entries = []
    for index, text in enumerate(texts):
        name = f'fnlit_resource_{index:03d}.bin'
        (directory / name).write_bytes(text.encode('ascii') + b'\0')
        entries.append(f'{RESOURCE_START + index} RCDATA "{name}"')
    (directory / 'fnlit.rc').write_text('\n'.join(entries) + '\n',
                                        encoding='ascii')


def read_resources(pe, count):
    """Return our resource bytes by ID, or None for absent IDs/directories."""
    result = {}
    root = getattr(pe, 'DIRECTORY_ENTRY_RESOURCE', None)
    if root is None:
        return result
    for kind in root.entries:
        if kind.id != RCDATA:
            continue
        for entry in kind.directory.entries:
            if not isinstance(entry.id, int) or not RESOURCE_START <= entry.id < RESOURCE_START + count:
                continue
            language = entry.directory.entries[0]
            data = language.data.struct
            result[entry.id] = pe.get_data(data.OffsetToData, data.Size)
    return result


def resources_match(pe, texts):
    found = read_resources(pe, len(texts))
    return len(found) == len(texts) and all(
        found.get(RESOURCE_START + index) == text.encode('ascii') + b'\0'
        for index, text in enumerate(texts))
