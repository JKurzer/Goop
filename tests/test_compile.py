"""Compile-only protocol: real MSVC smoke tests, never run the binary."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

GOOP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOOP / 'tools'))
sys.path.insert(0, str(GOOP))

import goop_compile  # noqa: E402
from gooplib import GoopError  # noqa: E402

GOOD = ('```cpp\n// replacement.cpp\n#include <cstdio>\n'
        'int main(int argc, char** argv) { std::printf("ok\\n"); return 0; }\n```')
BAD = '```cpp\n// replacement.cpp\nint main( { return 0; }\n```'


class SourceTest(unittest.TestCase):
    def test_extract_one_complete_file(self):
        self.assertEqual(goop_compile.source_from_final(GOOD),
                         GOOD.split('```cpp\n')[1].split('```')[0].encode())
        self.assertEqual(goop_compile.source_from_final(GOOD.replace('\n', '\r\n')),
                         goop_compile.source_from_final(GOOD))
        for invalid in ('some plausible pseudocode', '```cpp\nint main() {}\n```',
                        GOOD + '\n```text\nextra\n```'):
            with self.subTest(invalid=invalid), self.assertRaises(GoopError):
                goop_compile.source_from_final(invalid)


class CompileSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name) / 'compile-arm'
        (self.run / 'reports').mkdir(parents=True)
        (self.run / 'spec.json').write_text(json.dumps({
            'arm': self.run.name,
            'fire': {'prompt_file': 'compile.md', 'cells': ['RunB']}}))
        (self.run / 'reports/status_RunB.json').write_text(json.dumps({
            'cell': 'RunB', 'exit': 0}))
        self.final = self.run / 'reports/final_RunB.md'

    def test_missing_source_is_not_compilation_success(self):
        self.final.write_text('Pseudocode with no source block.')
        result = goop_compile.grade(self.run, 'RunB')
        self.assertEqual(result['grade'], 'no_artifact')
        with self.assertRaisesRegex(GoopError, 'already exists'):
            goop_compile.grade(self.run, 'RunB')

    def test_old_protocol_never_gets_retroactive_compile_grade(self):
        spec = json.loads((self.run / 'spec.json').read_text())
        spec['fire']['prompt_file'] = 'natural.md'
        (self.run / 'spec.json').write_text(json.dumps(spec))
        self.final.write_text(GOOD)
        with self.assertRaisesRegex(GoopError, 'only new'):
            goop_compile.grade(self.run, 'RunB')

    def test_real_msvc_compile_and_link_without_execution(self):
        try:
            goop_compile.find_vcvars()
        except GoopError as exc:
            self.skipTest(str(exc))
        self.final.write_text(GOOD)
        result = goop_compile.grade(self.run, 'RunB')
        self.assertEqual(result['grade'], 'compiled', result.get('diagnostics'))
        self.assertEqual(result['compiler_exit'], 0)
        self.assertEqual(result['report_sha256'],
                         hashlib.sha256(self.final.read_bytes()).hexdigest())
        self.assertEqual(json.loads((self.run / 'analysis/compile_RunB.json')
                                   .read_text())['grade'], 'compiled')
        self.assertFalse((self.run / 'analysis/replacement.exe').exists())

    def test_link_is_required_not_just_syntax(self):
        try:
            vcvars = goop_compile.find_vcvars()
        except GoopError as exc:
            self.skipTest(str(exc))
        result = goop_compile.compile_source(
            b'// replacement.cpp\nint helper() { return 42; }\n', vcvars)
        self.assertEqual(result['grade'], 'compile_error')
        self.assertIn('LNK', result['diagnostics'])

    def test_real_msvc_compile_error_is_not_a_pass(self):
        try:
            goop_compile.find_vcvars()
        except GoopError as exc:
            self.skipTest(str(exc))
        self.final.write_text(BAD)
        result = goop_compile.grade(self.run, 'RunB')
        self.assertEqual(result['grade'], 'compile_error')
        self.assertNotEqual(result['compiler_exit'], 0)
        self.assertIn('error C', result['diagnostics'])


if __name__ == '__main__':
    unittest.main()
