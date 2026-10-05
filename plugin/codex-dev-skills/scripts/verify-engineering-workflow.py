#!/usr/bin/env python3
"""Prepare, preflight or independently verify a runtime-neutral engineering fixture.

No model dispatch, credentials, installation or publication. Verification executes
the reviewed fixture under the caller's permissions; it is not a sandbox or gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import uuid

SPEC = """# Port normalization

Implement normalize_port(value) in port.py. Only strings are accepted. Strip
surrounding whitespace, require nonempty ASCII decimal digits, then return an
integer in 1..65535; raise ValueError otherwise. Do not modify this specification,
test_port.py or case.json. Update README.md to describe inputs and errors.
Create CHECKPOINT.md with the case sentinel, completed work, remaining independent
review/delivery gates and the next action. Work only in this fixture; no config,
credentials, dependencies, network, platform writes or publication.
Run the fixed tests with python -B -m unittest test_port.py to avoid bytecode files.
"""
TESTS = """import unittest
from port import normalize_port

class PortTests(unittest.TestCase):
    def test_valid(self):
        for value, expected in [('1', 1), ('65535', 65535), (' 80 ', 80), ('00080', 80)]:
            with self.subTest(value=value):
                self.assertEqual(expected, normalize_port(value))
                self.assertIs(type(normalize_port(value)), int)
    def test_invalid(self):
        for value in ['', ' ', '0', '65536', '80.0', '+80', '-1', '８０', 'a', None, True, 80]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_port(value)

if __name__ == '__main__':
    unittest.main()
"""
SOURCE = "def normalize_port(value):\n    raise NotImplementedError('implement the specification')\n"
DOCUMENTATION = ("ASCII", "1..65535", "ValueError")
FILES = {"SPEC.md", "test_port.py", "case.json", "port.py", "README.md", "CHECKPOINT.md"}


class FixtureError(ValueError):
    pass


def safe_root(raw: str) -> pathlib.Path:
    root = pathlib.Path(raw)
    if not root.is_absolute() or '..' in root.parts:
        raise FixtureError('use an absolute fixture path without ..')
    for path in (root, *root.parents):
        if path.is_symlink():
            raise FixtureError('symlink path component')
    return root


def prepare(root: pathlib.Path, runtime: str) -> str:
    if runtime not in {'codex', 'hermes'}:
        raise FixtureError('unsupported runtime label')
    # Exclusive mkdir: never overwrite or adopt an existing project.
    root.mkdir(mode=0o700)
    contents = {'SPEC.md': SPEC, 'test_port.py': TESTS, 'port.py': SOURCE,
                'README.md': '# Port normalization\n\nTODO: document inputs and errors.\n',
                'CHECKPOINT.md': '# Checkpoint\n\nTODO: record work and pending gates.\n',
                'case.json': json.dumps({'schema_version': 1, 'runtime_label': runtime,
                                         'sentinel': str(uuid.uuid4())}, sort_keys=True) + '\n'}
    for name, text in contents.items():
        with (root / name).open('x', encoding='utf-8') as stream:
            stream.write(text)
    return hashlib.sha256((root / 'case.json').read_bytes()).hexdigest()


def inspect_fixture(root: pathlib.Path, expected_case_sha256: str) -> tuple[dict, dict[str, bytes]]:
    """Cheap contract readback; never import or execute fixture code."""
    if not root.is_dir():
        raise FixtureError('missing fixture directory')
    # Only known direct children are read. Unexpected files are never opened.
    paths = list(root.iterdir())
    if {p.name for p in paths} != FILES:
        raise FixtureError('missing or unexpected fixture entry')
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > 65536 for p in paths):
        raise FixtureError('fixture files must be bounded regular files')
    if hashlib.sha256((root / 'case.json').read_bytes()).hexdigest() != expected_case_sha256:
        raise FixtureError('protected case identity changed')
    if (root / 'SPEC.md').read_text(encoding='utf-8') != SPEC:
        raise FixtureError('protected specification changed')
    if (root / 'test_port.py').read_text(encoding='utf-8') != TESTS:
        raise FixtureError('protected tests changed')
    case = json.loads((root / 'case.json').read_text(encoding='utf-8'))
    if (not isinstance(case, dict) or set(case) != {'schema_version', 'runtime_label', 'sentinel'}
            or type(case['schema_version']) is not int or case['schema_version'] != 1
            or case['runtime_label'] not in {'codex', 'hermes'}
            or not isinstance(case['sentinel'], str)):
        raise FixtureError('invalid case identity')
    if str(uuid.UUID(case['sentinel'])) != case['sentinel']:
        raise FixtureError('invalid sentinel')
    return case, {p.name: p.read_bytes() for p in paths}


def preflight(root: pathlib.Path, expected_case_sha256: str) -> dict:
    case, _ = inspect_fixture(root, expected_case_sha256)
    return {'schema_version': 1, 'runtime_label': case['runtime_label'],
            'contract_passed': True, 'fixture_code_executed': False,
            'functional_passed': False, 'delivery_ready': False,
            'runtime_qualified': False, 'identity_verified': False}


def verify(root: pathlib.Path, expected_case_sha256: str) -> dict:
    case, before = inspect_fixture(root, expected_case_sha256)
    readme = (root / 'README.md').read_text(encoding='utf-8')
    checkpoint = (root / 'CHECKPOINT.md').read_text(encoding='utf-8')
    docs = all(word in readme for word in DOCUMENTATION)
    # These are functional observations, never reviewer approval or gate proof.
    continuation = case['sentinel'] in checkpoint and 'review' in checkpoint.lower()
    command = [sys.executable, '-I', '-B', '-c',
               "import runpy,sys,unittest; root=sys.argv[1]; sys.path.insert(0,root); "
               "namespace=runpy.run_path(root+'/test_port.py',run_name='fixture_tests'); "
               "suite=unittest.defaultTestLoader.loadTestsFromTestCase(namespace['PortTests']); "
               "result=unittest.TextTestRunner().run(suite); "
               "sys.exit(77 if result.testsRun==2 and result.wasSuccessful() else 78)",
               str(root)]
    try:
        result = subprocess.run(command, cwd=root, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=20, env={**{k: v for k, v in os.environ.items()
                                                   if k in {'PATH', 'LANG', 'TMPDIR'}},
                                                 'PYTHONDONTWRITEBYTECODE': '1'})
        # Ordinary early exit(0), import failure or incomplete test execution
        # must not become success. This is not attestation of adversarial code.
        tests = result.returncode == 77
    except subprocess.TimeoutExpired:
        tests = False
    after_paths = list(root.iterdir())
    if ({p.name for p in after_paths} != FILES or
            any(p.is_symlink() or not p.is_file() or p.stat().st_size > 65536
                for p in after_paths) or
            any(p.read_bytes() != before[p.name] for p in after_paths)):
        raise FixtureError('fixture changed during independent verification')
    return {'schema_version': 1, 'runtime_label': case['runtime_label'],
            'checks': {'fixed_tests': tests, 'documentation': docs,
                       'checkpoint_content': continuation},
            'functional_passed': tests and docs and continuation,
            'delivery_ready': False, 'runtime_qualified': False,
            'identity_verified': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'preflight', 'verify'])
    parser.add_argument('--fixture-root', required=True)
    parser.add_argument('--runtime', choices=['codex', 'hermes'])
    parser.add_argument('--expected-case-sha256', help='prepare digest retained independently')
    args = parser.parse_args()
    try:
        root = safe_root(args.fixture_root)
        if args.action == 'prepare':
            if args.runtime is None:
                parser.error('prepare requires --runtime (a label, not qualification)')
            if args.expected_case_sha256 is not None:
                parser.error('prepare does not accept an existing case digest')
            digest = prepare(root, args.runtime)
            print(json.dumps({'prepared': True, 'case_sha256': digest,
                              'runtime_qualified': False}))
            return 0
        if args.runtime is not None:
            parser.error('preflight/verify reads the existing case label; omit --runtime')
        if (not args.expected_case_sha256 or len(args.expected_case_sha256) != 64 or
                any(c not in '0123456789abcdef' for c in args.expected_case_sha256)):
            parser.error('preflight/verify requires the independently retained prepare digest')
        if args.action == 'preflight':
            print(json.dumps(preflight(root, args.expected_case_sha256), sort_keys=True))
            return 0
        result = verify(root, args.expected_case_sha256)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['functional_passed'] else 1
    except (FixtureError, OSError, ValueError, TypeError):
        print('Fixture unavailable, invalid or changed; no acceptance granted.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
