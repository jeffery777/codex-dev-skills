from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from tests.test_memory_governance_contract import c, fixture, SCOPE, LIMITS
from memory_governance_host import PRODUCTION_ADAPTERS, production_host
from memory_governance_core import GovernanceCore
import memory_governance_storage as db

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT/'skills/loop-engineering/scripts/governancectl.py'


class CliTests(unittest.TestCase):
    def run_cli(self, *args, data=b''):
        return subprocess.run([str(ROOT/'scripts/project-python'), str(CLI), *args], input=data,
                              capture_output=True, cwd=ROOT, timeout=20)

    def test_default_off_ignores_input(self):
        result = self.run_cli('proposal', data=b'private-like invalid input is not read')
        self.assertEqual(0, result.returncode)
        report = json.loads(result.stdout)
        self.assertEqual('disabled', report['status'])
        self.assertFalse(report['operation_authorized'])
        self.assertFalse(report['write_performed'])

    def test_empty_production_registry_and_no_dynamic_registration(self):
        self.assertEqual({}, dict(PRODUCTION_ADAPTERS))
        with self.assertRaises(TypeError):
            PRODUCTION_ADAPTERS['fake'] = object()
        for name in ('local', 'synthetic', 'module:factory', '../private'):
            with self.subTest(name=name), self.assertRaisesRegex(c.ContractError, 'adapter-unavailable'):
                production_host(name)
        result = self.run_cli('audit', '--enabled')
        self.assertEqual(2, result.returncode)
        self.assertEqual('adapter-unavailable', json.loads(result.stdout)['reason'])

    def test_proposal_is_shape_only_not_executable_preview(self):
        payload = c.canonical({'scope': SCOPE, 'profile': LIMITS, 'candidate': fixture.version()})
        result = self.run_cli('proposal', '--enabled', data=payload)
        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual('proposal-only', report['status'])
        self.assertTrue(report['schema_consistent'])
        self.assertEqual('unavailable', report['source_verification'])
        self.assertNotIn('body', report)
        self.assertNotIn('preview_digest', report)
        self.assertFalse(report['runtime_proven'])
        self.assertFalse(report['operation_authorized'])

    def test_bad_and_oversized_inputs_do_not_echo(self):
        for payload in (b'{"secret":"do-not-echo"}', b'{"scope":{},"scope":{}}', b'x'*262145):
            result = self.run_cli('proposal', '--enabled', data=payload)
            self.assertEqual(2, result.returncode)
            self.assertNotIn(b'do-not-echo', result.stdout + result.stderr)
            self.assertNotIn(b'Traceback', result.stderr)

    def test_no_mutation_or_root_path_flags(self):
        for operation in ('add','update','restore','stop','resume','erase','purge','compact'):
            result = self.run_cli(operation, '--enabled')
            self.assertEqual(2, result.returncode)
        for flag in ('--root','--adapter','--confirmation','--accepted','--input'):
            result = self.run_cli('audit', flag, '/arbitrary/path')
            self.assertEqual(2, result.returncode)

    def test_disabled_core_does_not_probe_or_open(self):
        with (mock.patch.object(db, 'runtime_facts', side_effect=AssertionError('probe')),
              mock.patch.object(db, 'root_fd', side_effect=AssertionError('root'))):
            core = GovernanceCore()
            for call in (core.initialize, core.audit, lambda: core.preview('stop', 'x'), lambda: core.recall(['x'])):
                with self.assertRaisesRegex(c.ContractError, 'memory-disabled'):
                    call()
