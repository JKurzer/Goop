"""Print what actually differs between the k7 and m2 cells (v8 + control):
fire config, per-cell binary hashes/sizes/doses, slot contents, helpers."""
import json

for run in ('runs/conformant-v8-meg', 'runs/v8-undosed-control'):
    print(f'===== {run} =====')
    spec = json.load(open(f'{run}/spec.json', encoding='utf-8'))
    print('fire.model:', spec['fire']['model'], '| cells:', spec['fire']['cells'])
    print('build.doses:', spec['build']['doses'])
    manifest = json.load(open(f'{run}/unpacked/private/manifest.json',
                              encoding='utf-8'))
    for cell, info in manifest['cells'].items():
        print(f"  {cell}: dose={info['dose']} bytes={info['bytes']} "
              f"sha={info['sha256'][:16]}...")
    slots = {cell: info['slots'] for cell, info in manifest['cells'].items()}
    same_vas = slots['k7'] == slots['m2']
    print('  slot VAs identical:', same_vas)
    checks = manifest['checks']
    print('  executable_sections_identical:', checks['executable_sections_identical'],
          '| slot_locations_identical:', checks['slot_locations_identical'],
          '| equal_file_size:', checks['equal_file_size'],
          '| four_observations_identical:', checks['four_observations_identical'])
