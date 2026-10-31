from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest

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


class CoreFeedbackCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            'feedback_candidate_eval', ROOT / 'scripts/eval-core-feedback-candidate.py')
        cls.candidate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.candidate)

    def candidate_copy(self):
        import shutil
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        target = pathlib.Path(folder.name) / 'snapshot'
        shutil.copytree(self.candidate.FIXTURE, target)
        return target

    def observations(self, cases):
        return {'candidate_revision': self.candidate.REVISION,
                'answers': [{'id': c['id'], **c['expected']} for c in cases]}

    def test_one_fixed_candidate_has_complete_links_and_preserves_formal_defaults(self):
        pin, documents, cases = self.candidate.inspect()
        self.assertEqual(self.candidate.REVISION, pin['revision'])
        self.assertEqual(15, len(documents))
        self.assertEqual(9, len(cases))
        spec = importlib.util.spec_from_file_location(
            'ordinary_core_loader', ROOT / 'scripts/validate-core-contract-snapshot.py')
        ordinary = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ordinary)
        lock = json.loads((ROOT / 'vendor/engineering-workflow-core.lock.json').read_text())
        self.assertEqual('7b66978a76597d09be1b55ad199a969b4ee59c0f',
                         ordinary.validate(ROOT)['core_revision'])
        lock['source']['revision'] = self.candidate.REVISION
        with self.assertRaises(ordinary.SnapshotError):
            ordinary.parse_lock(json.dumps(lock).encode())

    def test_corruption_missing_extra_and_unsafe_types_are_rejected(self):
        for failure in ('changed', 'missing', 'extra', 'symlink', 'executable'):
            with self.subTest(failure=failure):
                root = self.candidate_copy()
                path = root / 'contracts/workflow.md'
                if failure == 'changed':
                    path.write_bytes(path.read_bytes().replace(b'Core', b'CoRe', 1))
                elif failure == 'missing':
                    path.unlink()
                elif failure == 'extra':
                    (root / 'unexpected.txt').write_text('SYNTHETIC')
                elif failure == 'symlink':
                    path.unlink()
                    path.symlink_to(root / 'README.md')
                else:
                    path.chmod(0o755)
                with self.assertRaises((self.candidate.EvaluationError, OSError)):
                    self.candidate.inspect(root)

    def test_raw_byte_preservation_rejects_normalization_and_reordering(self):
        value = '甲 must stay.\nKeep  two spaces.\ncafé\n'.encode()
        self.assertTrue(self.candidate.inserted_only(value, b'Added.\n' + value))
        mutations = (value.replace('甲'.encode(), b''), value.replace(b'must', b'may'),
                     value.replace(b'  ', b' '), value.replace(b'\n', b'\r\n'),
                     value.replace('é'.encode(), 'e\u0301'.encode()), value[:-1],
                     b''.join(reversed(value.splitlines(keepends=True))))
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assertFalse(self.candidate.inserted_only(value, mutation))

    def test_scorer_rejects_wrong_binding_shape_and_boolean_coercion(self):
        _, _, cases = self.candidate.inspect()
        valid = self.observations(cases)
        self.assertTrue(self.candidate.score(valid, cases)['passed'])
        for failure in ('revision', 'missing', 'repeat', 'reorder'):
            bad = json.loads(json.dumps(valid))
            if failure == 'revision':
                bad['candidate_revision'] = '0' * 40
            elif failure == 'missing':
                bad['answers'].pop()
            elif failure == 'repeat':
                bad['answers'][1] = bad['answers'][0]
            else:
                bad['answers'].reverse()
            with self.subTest(failure=failure):
                with self.assertRaises(self.candidate.EvaluationError):
                    self.candidate.score(bad, cases)
        for replacement in (1, 'true', False):
            bad = json.loads(json.dumps(valid))
            bad['answers'][0]['implement_now'] = replacement
            result = self.candidate.score(bad, cases)
            self.assertFalse(result['passed'])
            self.assertFalse(result['formal_core_adopted'])
            self.assertFalse(result['runtime_qualified'])
        with self.assertRaises(self.candidate.EvaluationError):
            self.candidate.parse(b'{"answers":[],"answers":[]}')

    def test_provider_hygiene_exception_is_fixed_verified_and_not_active(self):
        import os
        import shutil
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp) / 'source'
            root.mkdir()
            for relative in ('scripts/eval-core-feedback-candidate.py',
                             'scripts/validate-core-contract-snapshot.py',
                             'tests/fixtures/core-feedback-candidate.lock.json',
                             'tests/fixtures/core-feedback-cases.json',
                             'docs/evals/issue-361-core-feedback-candidate.md'):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, target)
            for relative in ('tests/fixtures/core-feedback-candidate',
                             'vendor/engineering-workflow-core'):
                shutil.copytree(ROOT / relative, root / relative)
            output = pathlib.Path(temp) / 'output'
            output.mkdir()
            source = (ROOT / 'scripts/validate-repo.sh').read_text()
            function = 'check_no_provider_terms() {' + source.split(
                'check_no_provider_terms() {', 1)[1].split(
                    '\ncheck_sensitive_private_terms()', 1)[0]
            command = ('set -euo pipefail\n'
                       'fail() { exit 34; }\n'
                       'ok() { :; }\n' + function + '\ncheck_no_provider_terms\n')
            env = dict(os.environ, PROJECT_PYTHON=sys.executable,
                       TMP_DIR=str(output))
            def run():
                return subprocess.run(['bash', '-c', command], cwd=root, env=env,
                                      capture_output=True, text=True, timeout=20)
            self.assertEqual(0, run().returncode)
            # A provenance allowance must not become a whole-directory ignore.
            for relative in ('skills/active.md', 'policies/active.md',
                             'docs/evals/other-feedback.md'):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('cl' + 'aude integration\n')
                self.assertNotEqual(0, run().returncode, relative)
                target.unlink()
                self.assertEqual(0, run().returncode)
            # The exact source path still needs the independently fixed bytes.
            target = root / 'tests/fixtures/core-feedback-candidate/docs/provenance/source-map.md'
            original = target.read_bytes()
            target.write_bytes(original + b'\nChanged source.\n')
            self.assertNotEqual(0, run().returncode)
            target.write_bytes(original)
            lock = root / 'tests/fixtures/core-feedback-candidate.lock.json'
            lock.unlink()
            self.assertNotEqual(0, run().returncode)


if __name__ == '__main__':
    unittest.main()
