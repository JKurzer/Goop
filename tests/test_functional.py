"""Functional grader controls. No paid calls or untrusted host execution."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP / 'tools'))
sys.path.insert(0, str(GOOP))

import goop_functional  # noqa: E402
from gooplib import GoopError  # noqa: E402
from gooplib.functional import (CASES, RANDOM_CASES, case_record,  # noqa: E402
                                choose_cases, compare_output, extract_submission)


class SubmissionTest(unittest.TestCase):
    def test_requires_real_standalone_python_file(self):
        valid = 'Evidence.\n```python\n# replacement.py\nprint("ok")\n```\n'
        self.assertEqual(extract_submission(valid),
                         b'# replacement.py\nprint("ok")\n')
        for bad in ('pseudocode only', '```python\npass\n```',
                    '```python\n# replacement.py\nif :\n```',
                    valid + '```text\nextra\n```'):
            with self.subTest(bad=bad), self.assertRaises(GoopError):
                extract_submission(bad)

    def test_fresh_withheld_cases_cover_full_input_range(self):
        class Rng:
            def __init__(self):
                self.next_tick = 2048

            def randrange(self, stop):
                if stop == 4097:
                    self.next_tick += 1
                    return self.next_tick
                return self.next_tick % 101

        cases = choose_cases(Rng())
        self.assertEqual(cases[:len(CASES)], CASES)
        self.assertEqual(len(cases), len(CASES) + RANDOM_CASES)
        self.assertEqual(len(set(cases)), len(cases))

    def test_complete_output_and_exit_codes_must_match(self):
        def done(stdout, stderr=b'', code=0):
            return subprocess.CompletedProcess([], code, stdout, stderr)

        original = done(b'PROGRESS 1\r\nSUMMARY ticks=1\r\n')
        self.assertTrue(compare_output(original,
                                       done(b'PROGRESS 1\nSUMMARY ticks=1\n')))
        self.assertFalse(compare_output(original, done(b'SUMMARY ticks=1\n')))
        self.assertFalse(compare_output(original,
                                        done(b'PROGRESS 1\nSUMMARY ticks=1\n', code=1)))
        self.assertFalse(compare_output(original,
                                        done(b'PROGRESS 1\nSUMMARY ticks=1\n', b'error')))
        self.assertFalse(case_record(1, 42, original, done(b'wrong'))['matched'])


class FunctionalGradeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name) / 'functional-arm'
        (self.run / 'reports').mkdir(parents=True)
        (self.run / 'cells/RunB').mkdir(parents=True)
        (self.run / 'analysis').mkdir()
        self.target = self.run / 'cells/RunB/target.exe'
        self.target.write_bytes(b'MZ owned fixture')
        (self.run / 'PREFLIGHT.json').write_text(json.dumps({
            'cells': {'RunB': {'packed_sha256': hashlib.sha256(
                self.target.read_bytes()).hexdigest()}}}), encoding='utf-8')
        (self.run / 'spec.json').write_text(json.dumps({
            'arm': self.run.name, 'fire': {'prompt_file': 'functional.md',
                                           'cells': ['RunB']}}), encoding='utf-8')
        (self.run / 'reports/status_RunB.json').write_text(json.dumps({
            'cell': 'RunB', 'exit': 0}), encoding='utf-8')
        self.report = self.run / 'reports/final_RunB.md'

    def test_no_code_is_not_a_pass_and_does_not_need_docker(self):
        self.report.write_text('A wonderful pseudocode report.', encoding='utf-8')
        with patch.object(goop_functional, 'docker_ready',
                          side_effect=AssertionError('must not run')):
            result = goop_functional.grade(self.run, 'RunB')
        self.assertEqual(result['grade'], 'no_artifact')
        self.assertEqual(result['cases'], [])
        self.assertFalse((self.run / 'analysis/submission_RunB.py').exists())
        with self.assertRaisesRegex(GoopError, 'already exists'):
            goop_functional.grade(self.run, 'RunB')

    def test_missing_docker_refuses_without_executing_code(self):
        self.report.write_text('```python\n# replacement.py\nprint(0)\n```',
                               encoding='utf-8')
        with patch.object(goop_functional, 'docker_ready',
                          side_effect=GoopError('no docker')):
            with self.assertRaisesRegex(GoopError, 'no docker'):
                goop_functional.grade(self.run, 'RunB')
        self.assertFalse((self.run / 'analysis/functional_RunB.json').exists())

    def test_pinned_target_mismatch_refuses_before_any_execution(self):
        self.report.write_text('```python\n# replacement.py\nprint(0)\n```',
                               encoding='utf-8')
        self.target.write_bytes(b'MZ swapped after preflight')
        with self.assertRaisesRegex(GoopError, 'pinned preflight hash'):
            goop_functional.grade(self.run, 'RunB')

    def test_docker_command_mounts_only_the_replacement(self):
        with patch.object(goop_functional.subprocess, 'Popen') as start:
            process = start.return_value
            process.poll.return_value = 0
            process.returncode = 0
            goop_functional.docker_run(Path(self.tmp.name) / 'solution.py', 0, 42)
        cmd = start.call_args.args[0]
        self.assertIn('--network=none', cmd)
        self.assertIn('--read-only', cmd)
        self.assertIn('--cap-drop=ALL', cmd)
        self.assertEqual(cmd.count('--mount'), 1)
        self.assertIn('target=/work/replacement.py,readonly',
                      cmd[cmd.index('--mount') + 1])
        self.assertNotIn(str(self.target), ' '.join(cmd))

    def test_harness_cases_with_injected_trusted_runners(self):
        self.report.write_text('```python\n# replacement.py\nprint(0)\n```',
                               encoding='utf-8')
        def original(command, **kwargs):
            ticks, seed = command[-2:]
            return subprocess.CompletedProcess(command, 0,
                                               f'{ticks}/{seed}\r\n'.encode(), b'')

        def sandbox(source, ticks, seed):
            self.assertEqual(source.read_bytes(),
                             b'# replacement.py\nprint(0)\n')
            return subprocess.CompletedProcess([], 0,
                                               f'{ticks}/{seed}\n'.encode(), b'')

        with patch.object(goop_functional, 'docker_ready', return_value='sha256:test'), \
             patch.object(goop_functional, 'choose_cases', return_value=CASES), \
             patch.object(goop_functional.subprocess, 'run', side_effect=original):
            result = goop_functional.grade(self.run, 'RunB', sandbox)
        self.assertEqual(result['grade'], 'passed')
        self.assertEqual([(x['ticks'], x['seed']) for x in result['cases']],
                         list(CASES))
        self.assertEqual(json.loads((self.run / 'analysis/functional_RunB.json')
                                   .read_text())['grade'], 'passed')
        self.assertEqual((self.run / 'analysis/submission_RunB.py').read_bytes(),
                         b'# replacement.py\nprint(0)\n')

    def test_historical_prompt_is_never_retroactively_graded(self):
        spec = json.loads((self.run / 'spec.json').read_text())
        spec['fire']['prompt_file'] = 'natural.md'
        (self.run / 'spec.json').write_text(json.dumps(spec))
        self.report.write_text('```python\n# replacement.py\npass\n```')
        with self.assertRaisesRegex(GoopError, 'historical'):
            goop_functional.grade(self.run, 'RunB')


if __name__ == '__main__':
    unittest.main()
