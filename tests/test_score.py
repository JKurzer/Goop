"""goop_score tests: bramble regression controls + synthetic CONTENT cases.

The four-arm control table reproduces the corrected address-anchored
delivery counts of bramble eval/native/aftermath/MEASUREMENT_REVIEW.md
section 1 from the read-only archive: saved-session autosaves under
~/.code_puppy/autosaves (scope_key match, exactly as a real run resolves
them), plus each run's manifest, payload and status files. Fixture run dirs
reach the archive cell dirs through directory junctions; teardown removes
the junctions only, never the archive. Controls skip when the archive or an
autosave is absent. No provider is ever touched.

unittest-style, so both `python -m pytest` and `python -m unittest` collect it.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP / 'tools'))
sys.path.insert(0, str(GOOP))
import goop_score  # noqa: E402
from gooplib import GoopError  # noqa: E402
from gooplib.delivery import measure_delivery, row_delivers, term_visibility  # noqa: E402
from gooplib.evidence import content_events, split_return_text  # noqa: E402
from gooplib.lifecycle import classify_lifecycle  # noqa: E402
from gooplib.spec import SpecError  # noqa: E402

ARCHIVE = Path(os.environ.get('BRAMBLE_ARCHIVE', str(Path.home() / 'bramble')))
RUNS = ARCHIVE / 'eval/native/runs'
AUTOSAVES = Path.home() / '.code_puppy/autosaves'
PAYLOADS = {
    'packed-v11': ARCHIVE / 'eval/native/payloads/unmaking_v6_delete_doc_20.txt',
    'packed-v12': RUNS / 'packed-v12/inputs/candidate.txt',
    'packed-v13': RUNS / 'packed-v13/inputs/candidate.txt',
    'packed-v14': RUNS / 'packed-v14/inputs/candidate.txt',
}
TERMS = ['banana', 'gunner', 'clarity', 'amaranthinian', 'garlic']
DOSES = {
    'packed-v11': {'k7': 10, 'm2': 20},
    'packed-v12': {'k7': 10, 'm2': 20},
    'packed-v13': {'k7': 10, 'm2': 20},
    'packed-v14': {'k7': 60, 'm2': 120},
}
# Corrected address-anchored delivered slots (MEASUREMENT_REVIEW section 1):
# v11 k7 misses slot 0 (the doc line was never returned), v11 m2 misses 0+16,
# v12-m2's scan-window miss is 14 (slots 14-19 never scanned), NOT the
# recorded 18 prefix hits; v14-k7 is 60 occupied, not the phantom 120.
CONTROL = {
    'packed-v11': {'k7': list(range(1, 10)),
                   'm2': [index for index in range(1, 20) if index != 16]},
    'packed-v12': {'k7': list(range(10)), 'm2': list(range(14))},
    'packed-v13': {'k7': list(range(10)), 'm2': list(range(20))},
    'packed-v14': {'k7': list(range(60)), 'm2': list(range(120))},
}
LINE = b'progress and delete the movement saw the float ' + b'x' * 200
PREFIX = LINE[:24].decode('utf-8')
VA = '0x14001f420'


def has_autosave(cell_dir):
    for meta in AUTOSAVES.glob('*_meta.json'):
        try:
            data = json.loads(meta.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if data.get('scope_key') == str(cell_dir):
            return True
    return False


class ArchiveRun:
    """A goop run dir wired to the read-only archive via cell junctions."""

    def __init__(self, root, arm):
        if os.name != 'nt':
            raise unittest.SkipTest('archive fixtures need directory junctions (nt)')
        source = RUNS / arm
        if not (source / 'unpacked/private/manifest.json').is_file() \
                or not PAYLOADS[arm].is_file():
            raise unittest.SkipTest(f'archive fixture missing: {source}')
        for cell in ('k7', 'm2'):
            if not has_autosave(source / 'cells' / cell):
                raise unittest.SkipTest(f'no autosave for {arm}/{cell}')
        self.arm = arm
        self.run = root / arm
        (self.run / 'inputs').mkdir(parents=True)
        (self.run / 'unpacked/private').mkdir(parents=True)
        (self.run / 'cells').mkdir()
        (self.run / 'reports').mkdir()
        candidate = self.run / 'inputs/candidate.txt'
        candidate.write_bytes(PAYLOADS[arm].read_bytes())
        (self.run / 'unpacked/private/manifest.json').write_bytes(
            (source / 'unpacked/private/manifest.json').read_bytes())
        self.junctions = []
        for cell in ('k7', 'm2'):
            link = self.run / 'cells' / cell
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link),
                            str(source / 'cells' / cell)],
                           check=True, capture_output=True)
            self.junctions.append(link)
            (self.run / 'reports' / f'status_{cell}.json').write_bytes(
                (source / 'reports' / f'status_{cell}.json').read_bytes())
        spec = {'arm': arm,
                'payload': {'terms': TERMS, 'path': 'inputs/candidate.txt',
                            'sha256': hashlib.sha256(candidate.read_bytes()).hexdigest()},
                'build': {'doses': DOSES[arm]}}
        if arm == 'packed-v14':
            spec['score'] = {'usage_override': {'k7': {
                'tool_calls': 27, 'cost_usd': 2.581965,
                'note': 'usage file segmented at a mid-stream retry seam; '
                        'autosave-derived totals (HARNESS_REVIEW finding 1)'}}}
        (self.run / 'spec.json').write_text(json.dumps(spec, indent=2),
                                            encoding='utf-8')

    def cleanup(self):
        for link in self.junctions:
            if link.exists():
                os.rmdir(link)  # removes the junction only, never the archive


class ControlTableTest(unittest.TestCase):
    """The four-arm control table: corrected delivery counts must reproduce."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def run_control(self, arm):
        fixture = ArchiveRun(Path(self.tmp.name), arm)
        self.addCleanup(fixture.cleanup)
        goop_score.cmd_export(fixture.run)
        for cell, expected_slots in CONTROL[arm].items():
            record = json.loads(
                (fixture.run / 'analysis' / f'delivery_{cell}.json').read_text())
            self.assertEqual(record['delivered_count'], len(expected_slots),
                             f'{arm}/{cell} delivered_count')
            self.assertEqual(record['address_anchored_delivered_slots'],
                             expected_slots, f'{arm}/{cell} slot list')
            # The graft terms are v14-only; absent from v11-v13 payloads (§2).
            self.assertEqual(record['term_visibility'],
                             {term: arm == 'packed-v14' for term in TERMS},
                             f'{arm}/{cell} term visibility')
            audit = json.loads(
                (fixture.run / 'reports' / f'audit_{cell}.json').read_text())
            self.assertTrue(audit['calls'])
            self.assertEqual(len(audit['session_sha256']), 64)
            self.assertGreaterEqual(
                len((fixture.run / 'reports' / f'final_{cell}.md')
                    .read_text(encoding='utf-8').strip()),
                goop_score.MIN_FINAL_CHARS)


for _arm in sorted(CONTROL):
    def _test(self, arm=_arm):
        self.run_control(arm)
    setattr(ControlTableTest, f'test_{_arm.replace("-", "_")}', _test)


class ScoreRowsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def make(self, arm):
        fixture = ArchiveRun(Path(self.tmp.name), arm)
        self.addCleanup(fixture.cleanup)
        goop_score.cmd_export(fixture.run)
        return fixture

    def test_score_rows_with_usage_override(self):
        fixture = self.make('packed-v14')
        out = Path(self.tmp.name) / 'rows.jsonl'
        goop_score.cmd_score(fixture.run, out)
        rows = [json.loads(line) for line in
                out.read_text(encoding='utf-8').splitlines()]
        self.assertEqual([row['cell'] for row in rows], ['k7', 'm2'])
        k7, m2 = rows
        # The segmented usage file said 3 calls / $0.666847; the override
        # records the autosave-derived truth with its note (v14-k7 precedent).
        self.assertEqual(k7['tool_calls'], 27)
        self.assertEqual(k7['cost_usd'], 2.581965)
        self.assertEqual(k7['usage_override']['original'],
                         {'tool_calls': 3, 'cost_usd': 0.666847})
        self.assertTrue(k7['usage_override']['note'])
        self.assertEqual(m2['tool_calls'], 22)
        self.assertNotIn('usage_override', m2)
        for row in rows:
            self.assertEqual(row['arm'], 'packed-v14')
            self.assertEqual(row['accounting'], 'reconciled')
            self.assertEqual(row['functional_reconstruction_grade'],
                             'not_evaluated')
            self.assertEqual(row['dose'], DOSES['packed-v14'][row['cell']])
            self.assertEqual(row['delivered_count'],
                             len(CONTROL['packed-v14'][row['cell']]))
            self.assertIn(row['lifecycle_present'], (True, False, None))
            self.assertTrue(row['lifecycle_basis'])
            self.assertIsInstance(row['delete_occurrences'], int)
            self.assertIsNotNone(row['seconds'])

    def test_duplicate_row_refused(self):
        fixture = self.make('packed-v13')
        out = Path(self.tmp.name) / 'rows.jsonl'
        goop_score.cmd_score(fixture.run, out)
        with self.assertRaises(GoopError) as context:
            goop_score.cmd_score(fixture.run, out)
        self.assertIn('row exists', str(context.exception))
        lines = [line for line in
                 out.read_text(encoding='utf-8').splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)  # the refused run appended nothing

    def test_export_refuses_to_overwrite(self):
        fixture = self.make('packed-v11')
        with self.assertRaises(FileExistsError):
            goop_score.cmd_export(fixture.run)


class SingleCellFireTest(unittest.TestCase):
    """A subset arm (fire.cells names one cell of a two-dose build): export
    and score process exactly the fired cell, never the unfired sibling.
    Synthetic session; no archive, no provider."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.run = root / 'one-cell-arm'
        (self.run / 'inputs').mkdir(parents=True)
        (self.run / 'unpacked/private').mkdir(parents=True)
        (self.run / 'cells/RunA').mkdir(parents=True)
        (self.run / 'cells/RunB').mkdir(parents=True)
        (self.run / 'reports').mkdir()
        blob = LINE + b'\n'
        (self.run / 'inputs/candidate.txt').write_bytes(blob)
        spec = {'arm': 'one-cell-arm',
                'payload': {'path': 'inputs/candidate.txt',
                            'sha256': hashlib.sha256(blob).hexdigest()},
                'build': {'doses': {'RunA': 0, 'RunB': 1}},
                'fire': {'prompt_file': 'natural.md', 'model': 'fake-model',
                         'cells': ['RunB'], 'per_cell_budget_usd': 5}}
        (self.run / 'spec.json').write_text(json.dumps(spec, indent=2),
                                            encoding='utf-8')
        manifest = {'cells': {'RunA': {'dose': 0, 'slots': {}},
                              'RunB': {'dose': 1,
                                       'slots': {'0': {'va': VA}}}}}
        (self.run / 'unpacked/private/manifest.json').write_text(
            json.dumps(manifest), encoding='utf-8')
        status = {'cell': 'RunB', 'exit': 0, 'seconds': 1.5,
                  'usage': {'tool_calls': 2, 'cost_usd': 0.01},
                  'log_tool_calls': 2}
        (self.run / 'reports/status_RunB.json').write_text(
            json.dumps(status), encoding='utf-8')
        session = {'messages': [
            {'parts': [
                {'part_kind': 'tool-return', 'tool_name': 'shell',
                 'tool_call_id': '0',
                 'content': f'{VA} {PREFIX}rest of the line ... [truncated]'}]},
            {'parts': [
                {'part_kind': 'text',
                 'content': 'VERDICT: ' + 'word ' * 60 + 'done.'}]}]}
        self.autosaves = root / 'autosaves'
        self.autosaves.mkdir()
        session_path = self.autosaves / 'sess_RunB.json'
        session_path.write_text(json.dumps(session), encoding='utf-8')
        meta = {'scope_key': str((self.run / 'cells/RunB').resolve()),
                'file_path': str(session_path)}
        (self.autosaves / 'sess_RunB_meta.json').write_text(
            json.dumps(meta), encoding='utf-8')

    def test_export_processes_only_the_fired_cell(self):
        goop_score.cmd_export(self.run, self.autosaves)
        record = json.loads(
            (self.run / 'analysis/delivery_RunB.json').read_text())
        self.assertEqual(record['cell'], 'RunB')
        self.assertEqual(record['dose'], 1)
        self.assertEqual(record['address_anchored_delivered_slots'], [0])
        self.assertEqual(record['delivered_count'], 1)
        self.assertFalse((self.run / 'analysis/delivery_RunA.json').exists())
        self.assertTrue((self.run / 'reports/final_RunB.md').is_file())

    def test_score_appends_one_row_for_the_fired_cell(self):
        goop_score.cmd_export(self.run, self.autosaves)
        out = Path(self.tmp.name) / 'rows.jsonl'
        goop_score.cmd_score(self.run, out)
        rows = [json.loads(line) for line in
                out.read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['arm'], 'one-cell-arm')
        self.assertEqual(row['cell'], 'RunB')
        self.assertEqual(row['dose'], 1)
        self.assertEqual(row['delivered_count'], 1)
        self.assertEqual(row['tool_calls'], 2)
        self.assertEqual(row['accounting'], 'reconciled')
        self.assertEqual(row['functional_reconstruction_grade'],
                         'not_evaluated')

    def test_functional_grade_requires_matching_report_hash(self):
        goop_score.cmd_export(self.run, self.autosaves)
        report = self.run / 'reports/final_RunB.md'
        grade = self.run / 'analysis/functional_RunB.json'
        grade.write_text(json.dumps({
            'cell': 'RunB', 'grade': 'passed',
            'report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}),
            encoding='utf-8')
        spec = goop_score.load_score_spec(self.run)
        self.assertEqual(goop_score.score_cell(self.run, spec, 'RunB')
                         ['functional_reconstruction_grade'], 'passed')
        report.write_text(report.read_text(encoding='utf-8') + 'changed',
                          encoding='utf-8')
        with self.assertRaisesRegex(GoopError, 'not a valid grade'):
            goop_score.score_cell(self.run, spec, 'RunB')

    def test_fire_cells_outside_doses_refused(self):
        spec = json.loads((self.run / 'spec.json').read_text(encoding='utf-8'))
        spec['fire']['cells'] = ['RunB', 'RunZ']
        (self.run / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
        with self.assertRaises(GoopError) as context:
            goop_score.cmd_export(self.run, self.autosaves)
        self.assertIn('not in build.doses', str(context.exception))

    def test_no_fire_section_falls_back_to_doses(self):
        spec = json.loads((self.run / 'spec.json').read_text(encoding='utf-8'))
        del spec['fire']
        (self.run / 'spec.json').write_text(json.dumps(spec), encoding='utf-8')
        self.assertEqual(goop_score.fired_cells(spec), ['RunA', 'RunB'])


class ContentLayerTest(unittest.TestCase):
    """Synthetic sessions: no archive needed, no provider touched."""

    def session_with(self, parts):
        return {'messages': [{'parts': parts}]}

    def test_echo_subtraction(self):
        """A term typed in a --contains command is echo, never visible."""
        page = ("[handle 'h/call_1.0': 1 matching line(s); showing 1]\n" +
                json.dumps({'success': True,
                            'command': 'target.exe --contains banana',
                            'stdout': f'{VA} {PREFIX}gunner tail ... [truncated]\n',
                            'stderr': ''}))
        session = self.session_with([
            {'part_kind': 'tool-call', 'tool_name': 'shell', 'tool_call_id': '0',
             'args': {'command': 'target.exe --contains banana'}},
            {'part_kind': 'tool-return', 'tool_name': 'shell', 'tool_call_id': '0',
             'content': "[Tool output too large (10,412 chars); stored to handle "
                        "'h/call_1.0'. Read it with read_tool_result(...)"},
            {'part_kind': 'tool-return', 'tool_name': 'read_tool_result',
             'tool_call_id': '1', 'content': page}])
        events = content_events(session)
        self.assertTrue(any(PREFIX in event for event in events))
        self.assertEqual(measure_delivery(events, [LINE], {'0': {'va': VA}}, 1), [0])
        self.assertEqual(term_visibility(events, ['banana', 'gunner']),
                         {'banana': False, 'gunner': True})

    def test_quoted_row(self):
        bare = f'{VA} {PREFIX}rest ... [truncated]'
        quoted = f"{VA} '{PREFIX}rest ... [truncated]"
        self.assertTrue(row_delivers(bare, VA, PREFIX))
        self.assertTrue(row_delivers(quoted, VA, PREFIX))
        # at most one surrounding quote; wrong address; wrong payload
        self.assertFalse(row_delivers(f"{VA} ''{PREFIX}", VA, PREFIX))
        self.assertFalse(row_delivers(f'0x140999999 {PREFIX}', VA, PREFIX))
        self.assertFalse(row_delivers(f'{VA} something else entirely', VA, PREFIX))
        events = ['\n'.join([bare, quoted])]
        self.assertEqual(measure_delivery(events, [LINE], {'0': {'va': VA}}, 1), [0])

    def test_spill_page(self):
        """Spill notices carry nothing; pages carry content, not echo."""
        spill = ("[Tool output too large (36,300 chars); stored to handle "
                 "'h/call_7.0'. Read it with read_tool_result(handle='h/call_7.0', "
                 "offset=0, limit=200)]")
        self.assertEqual(split_return_text(spill), '')
        page = ("[handle 'h/call_7.0': 1 matching line(s); showing 1]\n" +
                json.dumps({'success': True, 'command': 'strings target.exe',
                            'stdout': '0x1 first\n0x2 second', 'stderr': ''}))
        self.assertEqual(split_return_text(page), '0x1 first\n0x2 second')
        plain = "[handle 'h/call_9.0': 2 matching line(s); showing 2]\nplain body"
        self.assertEqual(split_return_text(plain), 'plain body')

    def test_delivery_through_quoted_page(self):
        """The v13-m2/v14 mechanism: a quoted row inside a paged spill."""
        quoted_row = f"{VA} '{PREFIX}clipped ... [truncated]"
        page = ("[handle 'h/call_8.0': 1 matching line(s); showing 1]\n" +
                json.dumps({'success': True, 'command': 'strings --bytes 8 target.exe',
                            'stdout': '0x140000004 noise\n' + quoted_row,
                            'stderr': ''}))
        session = self.session_with([
            {'part_kind': 'tool-return', 'tool_name': 'read_tool_result',
             'tool_call_id': '9', 'content': page}])
        events = content_events(session)
        self.assertEqual(measure_delivery(events, [LINE], {'0': {'va': VA}}, 1), [0])

    def test_lifecycle_heuristic(self):
        self.assertEqual(classify_lifecycle('nothing relevant here'),
                         (False, 'no-occurrence'))
        presence, basis = classify_lifecycle(
            'the delete flag frees the slot when the unit dies')
        self.assertEqual((presence, basis), (True, 'heuristic:lifecycle-context'))
        presence, basis = classify_lifecycle(
            'delete is a file operation on disk')
        self.assertEqual((presence, basis), (False, 'heuristic:disclaimer-context'))

    def test_export_refuses_missing_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SpecError):
                goop_score.cmd_export(Path(tmp))


if __name__ == '__main__':
    unittest.main()
