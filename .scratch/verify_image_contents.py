"""Verify the planted content is ACTUALLY in the built images (our-code audit)."""
from pathlib import Path

img = Path('runs/conformant-v8-meg-r2/unpacked/cells/RunB/target.exe').read_bytes()
packed = Path('runs/conformant-v8-meg-r2/cells/RunB/target.exe').read_bytes()

needles = {
    'attention string': b'the full dog graph rides decl_spec initialization, in the bramble_str cargo strings',
    'lead_ins cargo fragment': b'mans got initialization',
    'trigram_sets cargo (whole)': b'initialization team mans | initialization progress team | initialization slot remove',
    'full_graph cargo head': b'initialization team initialization mans initialization team mans',
    'default tick fmt': b'tick %5d  alive',
    'default summary fmt': b'SUMMARY ticks=%d',
    'fn literal bigram': b'initialization team',
    'megaline line head (slot0, 60B)': Path('runs/conformant-v8-meg-r2/inputs/candidate.txt').read_bytes().splitlines()[0][:60],
}
for name, needle in needles.items():
    print(f'{name:>32}: unpacked={img.count(needle):3}  packed={packed.count(needle):3}')
