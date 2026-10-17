"""goop_fire tests: synthetic raw logs + the read-only bramble v14 fixtures.

No live fires: every end-to-end case injects a fake run_fn, so nothing here
launches code-puppy or touches a provider. unittest-style, so both
`python -m pytest` and `python -m unittest` collect it.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP / 'tools'))
import goop_fire  # noqa: E402

ARCHIVE = Path(os.environ.get('BRAMBLE_ARCHIVE', str(Path.home() / 'bramble')))
V14_REPORTS = ARCHIVE / 'eval/native/runs/packed-v14/reports'


def make_run(root, cells=('RunA', 'RunB'), fire_overrides=None):
    """A synthetic goop run dir: spec.json + staged cells (fake target)."""
    run = root / 'run'
    for cell in cells:
        cell_dir = run / 'cells' / cell
        cell_dir.mkdir(parents=True)
        (cell_dir / 'target.exe').write_bytes(b'MZ fake target')
    fire = {'prompt_file': 'reduced.md', 'model': 'gpt-test',
            'cells': list(cells), 'per_cell_budget_usd': 3}
    fire.update(fire_overrides or {})
    (run / 'spec.json').write_text(json.dumps({'arm': 'test', 'fire': fire}),
                                   encoding='utf-8')
    return run, fire


class FakeRunner:
    """Stands in for subprocess.run: writes canned raw log + usage file."""

    def __init__(self, script):
        self.script = script  # cell -> (returncode, raw_log_text, usage_dict|None)
        self.calls = []
        self.environments = []

    def __call__(self, command, cwd, env, stdout, stderr):
        cell = Path(cwd).name
        self.calls.append(cell)
        self.environments.append(dict(env))
        returncode, raw, usage = self.script[cell]
        stdout.write(raw.encode('utf-8'))
        if usage is not None:
            usage_path = Path(command[command.index('--usage-file') + 1])
            usage_path.write_text(json.dumps(usage), encoding='utf-8')
        return subprocess.CompletedProcess(command, returncode)


def raw_with_calls(count, tool='shell'):
    return ''.join(f'● {tool}  command="x"\n' for _ in range(count))


def usage(calls, cost=1.0):
    return {'tool_calls': calls, 'cost_usd': cost, 'requests': calls}


def fire(run, fire_spec, cells, runner, output_name='reports'):
    return goop_fire.fire_cells(run, fire_spec, cells, output_name,
                                executable='code-puppy', env={}, run_fn=runner)


class DeathMarkerTests(unittest.TestCase):
    def test_each_death_marker_detected(self):
        for marker in goop_fire.DEATH_MARKERS:
            raw = f'prefix noise\n{marker}\ntrailing noise\n'
            self.assertEqual(goop_fire.death_marker(raw), marker)

    def test_clean_log_has_no_death(self):
        self.assertIsNone(goop_fire.death_marker(raw_with_calls(3)))

    def test_assess_flags_nonzero_exit_and_missing_usage(self):
        status, aborted = goop_fire.assess_cell('RunA', 1, 1.0, 'clean\n', None)
        self.assertIn('exit=1', aborted)
        self.assertIn('usage-file missing', aborted)
        self.assertEqual(status['aborted'], aborted)


class ReconciliationTests(unittest.TestCase):
    def test_ignores_thinking_and_prompt_echo(self):
        raw = ('● Thinking  Analyzing\n\n● shell  command="x"\n\n'
               '● read_file  file_path=y\n')
        self.assertEqual(goop_fire.log_tool_calls(raw), 2)

    def test_reset_fragment_prefix_still_counts(self):
        self.assertEqual(goop_fire.log_tool_calls('\x1b[0m● shell  command="x"\n'), 1)

    def test_within_pm1_tolerance_passes(self):
        raw = raw_with_calls(5)
        for filed in (4, 5, 6):
            _, aborted = goop_fire.assess_cell('RunA', 0, 1.0, raw, usage(filed))
            self.assertEqual(aborted, [], f'filed={filed} should reconcile')

    def test_beyond_pm1_aborts(self):
        _, aborted = goop_fire.assess_cell('RunA', 0, 1.0, raw_with_calls(5), usage(1))
        self.assertTrue(any('usage reconciliation' in item for item in aborted))

    def test_zero_observed_skips_reconciliation(self):
        # Ported semantics: `if observed and ...` — a tool-free log can't trip it.
        _, aborted = goop_fire.assess_cell('RunA', 0, 1.0, 'no bullets\n', usage(9))
        self.assertEqual(aborted, [])


@unittest.skipUnless((V14_REPORTS / 'raw_k7.log').is_file(),
                     'bramble archive fixture absent')
class V14FixtureTests(unittest.TestCase):
    """The segmented-usage trap, on the real read-only v14 artifacts."""

    def test_v14_k7_log_counts_27(self):
        raw = (V14_REPORTS / 'raw_k7.log').read_text(encoding='utf-8', errors='replace')
        self.assertEqual(goop_fire.log_tool_calls(raw), 27)

    def test_v14_k7_3_vs_27_aborts(self):
        raw = (V14_REPORTS / 'raw_k7.log').read_text(encoding='utf-8', errors='replace')
        filed = json.loads((V14_REPORTS / 'usage_k7.json').read_text(encoding='utf-8'))
        self.assertEqual(filed['tool_calls'], 3)
        status, aborted = goop_fire.assess_cell('k7', 0, 449.45, raw, filed)
        self.assertEqual(status['log_tool_calls'], 27)
        self.assertTrue(any('usage reconciliation' in item for item in aborted))

    def test_v14_m2_log_matches_usage(self):
        raw = (V14_REPORTS / 'raw_m2.log').read_text(encoding='utf-8', errors='replace')
        filed = json.loads((V14_REPORTS / 'usage_m2.json').read_text(encoding='utf-8'))
        self.assertEqual(goop_fire.log_tool_calls(raw), filed['tool_calls'])
        _, aborted = goop_fire.assess_cell('m2', 0, 1.0, raw, filed)
        self.assertEqual(aborted, [])


class PromptFileTests(unittest.TestCase):
    def test_both_prompt_files_keep_placeholders(self):
        for name in ('natural.md', 'reduced.md'):
            template = goop_fire.load_prompt(name)
            self.assertIn('{cell}', template)
            self.assertIn('{python}', template)

    def test_render_substitutes_cell_and_python(self):
        cell_dir = Path('C:/x/runs/arm/cells/RunA')
        for name in ('natural.md', 'reduced.md'):
            rendered = goop_fire.render_prompt(goop_fire.load_prompt(name), cell_dir)
            self.assertIn(str(cell_dir), rendered)
            self.assertIn(sys.executable, rendered)
            self.assertNotIn('{', rendered)

    def test_files_not_swapped(self):
        self.assertIn('VERDICT', goop_fire.load_prompt('natural.md'))
        self.assertNotIn('VERDICT', goop_fire.load_prompt('reduced.md'))

    def test_escape_and_missing_refused(self):
        for bad in ('../README.md', '..\\README.md', 'nope.md',
                    str(Path.cwd() / 'abs.md')):
            with self.assertRaises(RuntimeError, msg=bad):
                goop_fire.load_prompt(bad)


class RefusalTests(unittest.TestCase):
    def test_completed_cell_refuses_refire(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            reports = run / 'reports'
            reports.mkdir()
            (reports / 'status_RunA.json').write_text(
                json.dumps({'cell': 'RunA', 'exit': 0, 'usage': usage(3)}),
                encoding='utf-8')
            self.assertEqual(goop_fire.completed_cells(run), {'RunA'})
            with self.assertRaisesRegex(RuntimeError, 'never re-run'):
                fire(run, fire_spec, ['RunA'], FakeRunner({}), 'reports-RunA')

    def test_aborted_status_does_not_block_and_sibling_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            reports = run / 'reports'
            reports.mkdir()
            (reports / 'status_RunA.json').write_text(
                json.dumps({'cell': 'RunA', 'exit': 0, 'usage': usage(3)}),
                encoding='utf-8')
            (reports / 'status_RunB.json').write_text(
                json.dumps({'cell': 'RunB', 'exit': 0,
                            'aborted': ['provider-death: Request timed out']}),
                encoding='utf-8')
            self.assertEqual(goop_fire.completed_cells(run), {'RunA'})
            runner = FakeRunner({'RunB': (0, raw_with_calls(2), usage(2))})
            code = fire(run, fire_spec, ['RunB'], runner, 'reports-RunB')
            self.assertEqual(code, 0)
            self.assertTrue((run / 'reports-RunB/status_RunB.json').is_file())
            run_a_status = json.loads((reports / 'status_RunA.json').read_text())
            self.assertNotIn('aborted', run_a_status)  # completed sibling untouched

    def test_stale_output_dir_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            (run / 'reports').mkdir()
            with self.assertRaisesRegex(RuntimeError, 'exists'):
                fire(run, fire_spec, ['RunA', 'RunB'], FakeRunner({}))

    def test_spec_unknown_key_and_missing_key_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, _ = make_run(Path(temporary), fire_overrides={'bogus': 1})
            with self.assertRaisesRegex(RuntimeError, 'unknown keys'):
                goop_fire.load_fire_spec(run)
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / 'run'
            run.mkdir()
            (run / 'spec.json').write_text(
                json.dumps({'fire': {'prompt_file': 'reduced.md'}}), encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'missing keys'):
                goop_fire.load_fire_spec(run)


class ParseCellsTests(unittest.TestCase):
    def test_default_is_full_spec_into_reports(self):
        self.assertEqual(goop_fire.parse_cells(None, ['RunA', 'RunB']),
                         (['RunA', 'RunB'], 'reports'))

    def test_subset_gets_fresh_dir_name(self):
        self.assertEqual(goop_fire.parse_cells('RunB', ['RunA', 'RunB']),
                         (['RunB'], 'reports-RunB'))

    def test_unknown_or_duplicate_refused(self):
        for bad in ('bogus', 'RunB,RunB', 'RunA,bogus'):
            with self.assertRaises(RuntimeError, msg=bad):
                goop_fire.parse_cells(bad, ['RunA', 'RunB'])


class EndToEndFakeFireTests(unittest.TestCase):
    """Full loop through fire_cells with a canned provider; nothing is paid."""

    def test_happy_path_fires_both_cells(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            runner = FakeRunner({'RunA': (0, raw_with_calls(3), usage(3)),
                                 'RunB': (0, raw_with_calls(2), usage(2))})
            self.assertEqual(fire(run, fire_spec, ['RunA', 'RunB'], runner), 0)
            self.assertEqual(runner.calls, ['RunA', 'RunB'])
            for child_env in runner.environments:
                state = Path(child_env['CONTEXT_PINS'])
                self.assertEqual(json.loads(state.read_text(encoding='utf-8')), [])
            prompt = (run / 'reports/prompt_RunA.txt').read_text(encoding='utf-8')
            self.assertIn(str(run / 'cells' / 'RunA'), prompt)
            self.assertIn(sys.executable, prompt)
            status = json.loads((run / 'reports/status_RunA.json').read_text())
            self.assertEqual(status['log_tool_calls'], 3)
            self.assertNotIn('aborted', status)

    def test_inherited_pins_overridden_only_in_rea_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            parent_env = {'CONTEXT_PINS': 'parent-pins.json', 'OTHER': 'untouched'}
            runner = FakeRunner({'RunA': (0, raw_with_calls(1), usage(1))})
            self.assertEqual(goop_fire.fire_cells(
                run, fire_spec, ['RunA'], 'reports', executable='fake',
                env=parent_env, run_fn=runner), 0)
            self.assertEqual(parent_env['CONTEXT_PINS'], 'parent-pins.json')
            self.assertEqual(runner.environments[0]['OTHER'], 'untouched')
            self.assertEqual(json.loads(Path(
                runner.environments[0]['CONTEXT_PINS']).read_text()), [])

    def test_missing_empty_state_refuses_before_launch_or_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            runner = FakeRunner({'RunA': (0, raw_with_calls(1), usage(1))})
            with patch.object(goop_fire, 'REA_EMPTY_PINS',
                              Path(temporary) / 'absent.json'):
                with self.assertRaisesRegex(RuntimeError, 'REA pin state'):
                    fire(run, fire_spec, ['RunA'], runner)
            self.assertEqual(runner.calls, [])
            self.assertFalse((run / 'reports').exists())

    def test_provider_death_stops_before_next_cell(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            runner = FakeRunner({'RunA': (0, 'work...\nRequest timed out\n', None),
                                 'RunB': (0, raw_with_calls(2), usage(2))})
            code = fire(run, fire_spec, ['RunA', 'RunB'], runner)
            self.assertEqual(code, 2)
            self.assertEqual(runner.calls, ['RunA'])  # RunB never launched
            status = json.loads((run / 'reports/status_RunA.json').read_text())
            self.assertIn('provider-death: Request timed out', status['aborted'])
            self.assertIn('usage-file missing', status['aborted'])
            stub = (run / 'ATTEMPT_RUNA_ABORTED.md').read_text(encoding='utf-8')
            self.assertIn('- provider-death: Request timed out', stub)
            self.assertIn('reports/raw_RunA.log', stub)
            self.assertFalse((run / 'reports/status_RunB.json').exists())

    def test_reconciliation_mismatch_aborts(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            runner = FakeRunner({'RunA': (0, raw_with_calls(5), usage(1))})
            code = fire(run, fire_spec, ['RunA'], runner, 'reports-RunA')
            self.assertEqual(code, 2)
            stub = (run / 'ATTEMPT_RUNA_ABORTED.md').read_text(encoding='utf-8')
            self.assertIn('usage reconciliation: file says 1 calls, log shows 5', stub)

    def test_budget_stop_counts_the_cell_and_exits_3(self):
        with tempfile.TemporaryDirectory() as temporary:
            run, fire_spec = make_run(Path(temporary))
            runner = FakeRunner({'RunA': (0, raw_with_calls(3), usage(3, cost=9.99)),
                                 'RunB': (0, raw_with_calls(2), usage(2))})
            code = fire(run, fire_spec, ['RunA', 'RunB'], runner)
            self.assertEqual(code, 3)
            self.assertEqual(runner.calls, ['RunA'])
            status = json.loads((run / 'reports/status_RunA.json').read_text())
            self.assertNotIn('aborted', status)  # budget stop is a real cell
            self.assertFalse((run / 'ATTEMPT_RUNA_ABORTED.md').exists())

    def test_attempt_stub_serializes_on_reabort(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary)
            first = goop_fire.attempt_stub_path(run, 'RunA')
            self.assertEqual(first.name, 'ATTEMPT_RUNA_ABORTED.md')
            first.write_text('# first\n', encoding='utf-8')
            self.assertEqual(goop_fire.attempt_stub_path(run, 'RunA').name,
                             'ATTEMPT_RUNA_ABORTED_2.md')


class ImmutableWriteTests(unittest.TestCase):
    def test_write_exclusive_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / 'f.txt'
            goop_fire.write_exclusive(target, 'a')
            with self.assertRaises(FileExistsError):
                goop_fire.write_exclusive(target, 'b')
            self.assertEqual(target.read_text(), 'a')


class CliTests(unittest.TestCase):
    def test_missing_spec_refuses_with_exit_1(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(goop_fire.main(['fire', temporary]), 1)


if __name__ == '__main__':
    unittest.main()
