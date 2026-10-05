from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('engineering_fixture', ROOT / 'scripts/verify-engineering-workflow.py')
fixture = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(fixture)
IMPLEMENTATION = """def normalize_port(value):
    if not isinstance(value, str):
        raise ValueError('string required')
    value = value.strip()
    if not value or not value.isascii() or not value.isdecimal():
        raise ValueError('ASCII digits required')
    result = int(value)
    if not 1 <= result <= 65535:
        raise ValueError('out of range')
    return result
"""


class EngineeringFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name).resolve()
        self.root = self.base / 'fixture'
        self.digest = fixture.prepare(self.root, 'hermes')

    def complete(self):
        (self.root / 'port.py').write_text(IMPLEMENTATION)
        (self.root / 'README.md').write_text('Accept ASCII strings in 1..65535; invalid inputs raise ValueError.\n')
        case = json.loads((self.root / 'case.json').read_text())
        (self.root / 'CHECKPOINT.md').write_text(case['sentinel'] + '\nCompleted implementation; independent review and delivery pending.\n')

    def test_both_labels_observe_same_functional_outcomes_without_granting_readiness(self):
        self.complete()
        hermes = fixture.verify(self.root, self.digest)
        other = self.base / 'codex'
        digest = fixture.prepare(other, 'codex')
        for name in ('port.py', 'README.md'):
            (other / name).write_bytes((self.root / name).read_bytes())
        case = json.loads((other / 'case.json').read_text())
        (other / 'CHECKPOINT.md').write_text(case['sentinel'] + '\nIndependent review pending.\n')
        codex = fixture.verify(other, digest)
        self.assertTrue(hermes['functional_passed'])
        self.assertEqual(hermes['checks'], codex['checks'])
        for result in (hermes, codex):
            for claim in ('delivery_ready', 'runtime_qualified', 'identity_verified'):
                self.assertIs(result[claim], False)

    def test_incomplete_implementation_cannot_pass(self):
        result = fixture.verify(self.root, self.digest)
        self.assertFalse(result['functional_passed'])
        self.assertFalse(result['checks']['fixed_tests'])

    def test_preflight_checks_contract_without_executing_or_granting_readiness(self):
        (self.root / 'port.py').write_text("raise RuntimeError('must not execute')\n")
        with mock.patch.object(fixture.subprocess, 'run', side_effect=AssertionError('must not spawn')):
            result = fixture.preflight(self.root, self.digest)
        self.assertTrue(result['contract_passed'])
        for claim in ('fixture_code_executed', 'functional_passed', 'delivery_ready',
                      'runtime_qualified', 'identity_verified'):
            self.assertIs(result[claim], False)

    def test_preflight_and_verify_reject_protected_drift_before_execution(self):
        with mock.patch.object(fixture.subprocess, 'run', side_effect=AssertionError('must not spawn')):
            for name in ('SPEC.md', 'test_port.py', 'case.json'):
                path = self.root / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                for action in (fixture.preflight, fixture.verify):
                    with self.subTest(name=name, action=action.__name__), self.assertRaises(fixture.FixtureError):
                        action(self.root, self.digest)
                path.write_bytes(original)

    def test_public_preflight_json_shape_on_source_and_plugin_consumers(self):
        import subprocess
        import sys
        for script in (ROOT / 'scripts/verify-engineering-workflow.py',
                       ROOT / 'plugin/codex-dev-skills/scripts/verify-engineering-workflow.py'):
            run = subprocess.run([sys.executable, str(script), 'preflight',
                                  '--fixture-root', str(self.root),
                                  '--expected-case-sha256', self.digest],
                                 capture_output=True, text=True, timeout=20)
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual(fixture.preflight(self.root, self.digest), json.loads(run.stdout))

    def test_early_successful_process_exit_cannot_impersonate_completed_tests(self):
        self.complete()
        (self.root / 'port.py').write_text('import sys\nsys.exit(0)\n')
        self.assertFalse(fixture.verify(self.root, self.digest)['functional_passed'])

    def test_public_test_command_then_independent_verification(self):
        import subprocess
        import sys
        self.complete()
        run = subprocess.run([sys.executable, '-B', '-m', 'unittest', 'test_port.py'],
                             cwd=self.root, capture_output=True, timeout=20)
        self.assertEqual(0, run.returncode)
        self.assertTrue(fixture.verify(self.root, self.digest)['functional_passed'])

    def test_unicode_digits_and_missing_docs_or_checkpoint_fail_independently(self):
        self.complete()
        (self.root / 'port.py').write_text(IMPLEMENTATION.replace('not value.isascii() or ', ''))
        self.assertFalse(fixture.verify(self.root, self.digest)['checks']['fixed_tests'])
        self.complete()
        (self.root / 'README.md').write_text('done')
        self.assertFalse(fixture.verify(self.root, self.digest)['functional_passed'])
        self.complete()
        (self.root / 'CHECKPOINT.md').write_text('review pending')
        self.assertFalse(fixture.verify(self.root, self.digest)['functional_passed'])

    def test_protected_spec_tests_and_case_drift_refuse_verification(self):
        for name in ('SPEC.md', 'test_port.py', 'case.json'):
            path = self.root / name
            original = path.read_bytes()
            path.write_bytes(original + b'\n# changed\n')
            with self.subTest(name=name), self.assertRaises(fixture.FixtureError):
                fixture.verify(self.root, self.digest)
            path.write_bytes(original)

    def test_execution_mutation_is_not_accepted_or_rolled_back(self):
        self.complete()
        (self.root / 'port.py').write_text("from pathlib import Path\nPath('README.md').write_text('changed')\n" + IMPLEMENTATION)
        with self.assertRaisesRegex(fixture.FixtureError, 'changed during'):
            fixture.verify(self.root, self.digest)
        self.assertEqual('changed', (self.root / 'README.md').read_text())

    def test_existing_project_and_symlink_cannot_be_adopted(self):
        with self.assertRaises(FileExistsError):
            fixture.prepare(self.root, 'codex')
        link = self.base / 'link'
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(fixture.FixtureError):
            fixture.safe_root(str(link))
        (self.root / 'port.py').unlink()
        (self.root / 'port.py').symlink_to(self.root / 'SPEC.md')
        with self.assertRaises(fixture.FixtureError):
            fixture.verify(self.root, self.digest)

    def test_unknown_entries_are_not_read(self):
        (self.root / '.env').write_text('SYNTHETIC=not-a-credential')
        with self.assertRaisesRegex(fixture.FixtureError, 'unexpected'):
            fixture.verify(self.root, self.digest)

    def test_consumer_package_contains_same_contract_and_verifier(self):
        catalog = json.loads((ROOT / 'hermes/catalog.json').read_text())
        for name in ('policies/engineering-workflow-contract.md', 'scripts/verify-engineering-workflow.py'):
            self.assertIn(name, catalog['resources'])
            self.assertIn(name, (ROOT / 'install.sh').read_text())
            self.assertIn(name, (ROOT / 'scripts/sync-plugin-package.py').read_text())


if __name__ == '__main__':
    unittest.main()
