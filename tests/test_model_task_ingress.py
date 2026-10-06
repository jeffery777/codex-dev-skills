"""Real temporary Git/source reads; synthetic inputs are not dispatch authority."""
import copy
import json
import os
import pathlib
import subprocess
import shlex
import sys
import tempfile
import time
import unittest
from unittest import mock
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'skills/loop-engineering/scripts'))
import model_task_ingress as ingress
import model_packet_store as packets

ACCEPTANCE = b'Synthetic acceptance: preserve the original source.\n'


class InputFixture:
    def __init__(self, home, request, *, task_id='T1', scope='repair', destinations=None):
        self.home = home
        home.mkdir(mode=0o700, parents=True, exist_ok=True)
        (home/'model-task-inputs').mkdir(mode=0o700, exist_ok=True)
        self.request = copy.deepcopy(request)
        self.original = {k: v for k, v in request.items() if k != 'target_ref'}
        root = pathlib.Path(request['workspace']).resolve()
        source_files = {'README.md': packets.digest((root/'README.md').read_bytes())}
        now = int(time.time())
        self.record = {'schema_version': 1, 'enabled': True, 'observed_at': now, 'expires_at': now+300,
            'task_id': task_id, 'scope': scope, 'request': self.artifact('request.json', packets.canonical(self.original)),
            'acceptance': self.artifact('acceptance.txt', ACCEPTANCE),
            'source': {'workspace': str(root), 'head': request['expected_head'], 'files': source_files,
                'index_sha256': packets.digest((ingress.git_source.validated_git_marker(root).git_dir/'index').read_bytes()),
                'origin_sha256': packets.digest(subprocess.check_output(['/usr/bin/git', '-C', str(root), 'config', '--get', 'remote.origin.url']).strip())},
            'destinations': destinations or ['b'*64]}
        self.refresh()

    def artifact(self, name, raw):
        path = self.home/'model-task-inputs'/name
        path.write_bytes(raw); path.chmod(0o600)
        return {'path': 'model-task-inputs/'+name, 'sha256': packets.digest(raw)}

    def refresh(self):
        self.ref = self.artifact('record.json', packets.canonical(self.record))

    def read(self, request=None, identity=None):
        item = ingress.read_input(self.home, self.ref, {'id': self.record['task_id'],
            'qualification_scope': self.record['scope']}, {'task': {'acceptance_sha256': packets.digest(ACCEPTANCE)}},
            request or self.request)
        item.verify(request or self.request, SimpleNamespace(task_id=self.record['task_id'], scope=self.record['scope'],
            acceptance_sha256=packets.digest(ACCEPTANCE), identity_sha256=packets.digest(packets.canonical(identity or {'synthetic': True}))))
        return item


class InputContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform == 'darwin' else None)
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name).resolve()
        self.repo = self.base/'repo'; self.repo.mkdir(mode=0o700)
        self.git('init', '-q'); self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.git('remote', 'add', 'origin', 'https://example.invalid/fixture.git')
        (self.repo/'README.md').write_text('source\n')
        self.git('add', 'README.md'); self.git('commit', '-qm', 'fixture')
        self.identity = {'synthetic': True}
        self.request = {'operation': 'start', 'workspace': str(self.repo), 'expected_head': self.git('rev-parse', 'HEAD'),
            'prompt': 'Synthetic bounded local task', 'sandbox': 'workspace-write',
            'authorization': {'sandbox_ceiling': 'workspace-write'}, 'target_ref': {'id': 'synthetic'}}
        self.f = InputFixture(self.base/'home', self.request, destinations=[packets.digest(packets.canonical(self.identity))])

    def git(self, *args):
        return subprocess.run(['/usr/bin/git', '-C', str(self.repo), *args], check=True,
            capture_output=True, text=True).stdout.strip()

    def test_real_source_rechecks_and_readonly_downgrade_preserves_identity(self):
        item = self.f.read()
        readonly = copy.deepcopy(self.request)
        readonly['sandbox'] = readonly['authorization']['sandbox_ceiling'] = 'read-only'
        self.assertEqual(item.verify(readonly), item.identity_sha256)
        self.assertEqual(item.verify(self.request), item.identity_sha256)

    def test_original_prompt_scope_acceptance_destination_and_authority_schema_rejected(self):
        changed = copy.deepcopy(self.request); changed['prompt'] += ' changed'
        with self.assertRaises(ingress.InputError): self.f.read(changed)
        for field, value in [('scope', 'other'), ('task_id', 'other'), ('destinations', ['d'*64]),
                             ('authority', {'status': 'granted', 'qualification': 'qualified'})]:
            record = copy.deepcopy(self.f.record); self.f.record[field] = value; self.f.refresh()
            with self.assertRaises(ingress.InputError):
                ingress.read_input(self.f.home, self.f.ref, {'id': 'T1', 'qualification_scope': 'repair'},
                    {'task': {'acceptance_sha256': packets.digest(ACCEPTANCE)}}, self.request)
                self.f.read()
            self.f.record = record; self.f.refresh()

    def test_changed_or_revoked_original_is_not_reused(self):
        item = self.f.read()
        (self.f.home/'model-task-inputs/acceptance.txt').write_bytes(b'changed acceptance')
        with self.assertRaises(ValueError): item.verify(self.request)
        self.f.artifact('acceptance.txt', ACCEPTANCE)
        self.f.record['enabled'] = False; self.f.refresh()
        with self.assertRaises(ValueError): item.verify(self.request)

    def test_source_dirty_hidden_index_changes_and_head_drift_rejected(self):
        item = self.f.read()
        self.git('update-index', '--assume-unchanged', 'README.md')
        (self.repo/'README.md').write_text('hidden source change\n')
        with self.assertRaises(ValueError): item.verify(self.request)
        (self.repo/'README.md').write_text('source\n')
        with self.assertRaises(ValueError): item.verify(self.request)
        self.git('update-index', '--no-assume-unchanged', 'README.md')
        self.git('commit', '--allow-empty', '-qm', 'different head')
        with self.assertRaises(ValueError): item.verify(self.request)

    def test_expiry_renewal_and_reference_alias_do_not_change_packet_identity(self):
        item = self.f.read()
        self.f.record['observed_at'] -= 1; self.f.record['expires_at'] -= 1; self.f.refresh()
        renewed = self.f.read()
        self.assertEqual(item.packet_identity('example.invalid/fixture'), renewed.packet_identity('example.invalid/fixture'))
        alias = self.f.artifact('alias.json', packets.canonical(self.f.record))
        self.f.ref = alias
        self.assertEqual(self.f.read().identity_sha256, renewed.identity_sha256)
        with mock.patch.object(ingress.time, 'time', return_value=self.f.record['expires_at']):
            with self.assertRaises(ValueError): renewed.verify(self.request)

    def test_source_readback_crossing_expiry_is_rejected_at_final_clock_sample(self):
        item = self.f.read()
        expiry = item.record['expires_at']
        with mock.patch.object(ingress.time, 'time', side_effect=[expiry-1, expiry]):
            with self.assertRaisesRegex(ingress.InputError, 'expired-during-readback'):
                item.verify(self.request)

    def test_original_changed_during_source_readback_is_rejected(self):
        item = self.f.read(); original = ingress._source
        def drift(source):
            result = original(source)
            (self.f.home/'model-task-inputs/acceptance.txt').write_bytes(b'changed at boundary')
            return result
        with mock.patch.object(ingress, '_source', side_effect=drift):
            with self.assertRaises(ValueError): item.verify(self.request)

    def test_links_fifo_traversal_duplicate_keys_and_repository_store_rejected(self):
        path = self.f.home/'model-task-inputs/request.json'
        raw = path.read_bytes(); path.unlink()
        path.symlink_to(self.f.home/'model-task-inputs/acceptance.txt')
        with self.assertRaises(ingress.InputError): self.f.read()
        path.unlink(); path.write_bytes(raw); path.chmod(0o600)
        os.link(path, path.with_name('hardlink'))
        with self.assertRaises(ingress.InputError): self.f.read()
        path.with_name('hardlink').unlink(); path.unlink(); os.mkfifo(path, 0o600)
        with self.assertRaises(ingress.InputError): self.f.read()
        path.unlink(); path.write_bytes(raw); path.chmod(0o600)
        self.f.record['request']['path'] = 'model-task-inputs/../request.json'; self.f.refresh()
        with self.assertRaises(ingress.InputError): self.f.read()
        (self.f.home/'.git').mkdir()
        with self.assertRaises(ingress.InputError): self.f.read()

    def test_public_input_cannot_omit_original_or_add_self_asserted_qualification(self):
        self.f.ref = self.f.artifact('record.json', b'{"schema_version":1,"schema_version":1}')
        with self.assertRaises(ingress.InputError): self.f.read()
        self.f.refresh()
        self.f.record['qualified'] = True; self.f.refresh()
        with self.assertRaises(ingress.InputError): self.f.read()

    def test_nested_git_directories_gitfiles_and_malformed_reference_are_rejected(self):
        parent = self.f.home/'model-task-inputs'
        for gitfile in (False, True):
            marker = parent/'.git'
            marker.write_text('gitdir: synthetic') if gitfile else marker.mkdir()
            with self.assertRaises(ingress.InputError): self.f.read()
            marker.unlink() if gitfile else marker.rmdir()
        deeper = parent/'deeper'; deeper.mkdir(mode=0o700)
        (deeper/'.git').mkdir()
        raw = (parent/'record.json').read_bytes()
        (deeper/'record.json').write_bytes(raw); (deeper/'record.json').chmod(0o600)
        reference = {'path': 'model-task-inputs/deeper/record.json', 'sha256': packets.digest(raw)}
        with self.assertRaises(ingress.InputError):
            ingress.read_input(self.f.home, reference, {}, {}, self.request)
        for value in (None, 12, [], {}):
            reference = {'path': value, 'sha256': 'a'*64}
            with self.assertRaises(ingress.InputError):
                ingress.read_input(self.f.home, reference, {}, {}, self.request)

    def test_actual_wrapper_rejects_malformed_references_without_traceback(self):
        import loopctl
        import model_task_execution as execution
        from contextlib import redirect_stdout
        from io import StringIO
        from tests.test_model_failover import route_fixture
        route = route_fixture()
        adapter = mock.Mock(); adapter.PACKET_STOP_ADAPTERS = {}
        loader = SimpleNamespace(root=lambda: self.f.home)
        path = self.base/'wrapper.json'
        for value in (None, 1, [], {}):
            path.write_text(json.dumps({**route, 'cli_request': self.request,
                'task_input_ref': {'path': value, 'sha256': 'a'*64}}))
            out = StringIO()
            with redirect_stdout(out), mock.patch.object(execution, '_cli_adapter', return_value=(adapter, loader)):
                self.assertEqual(loopctl.command_model_task_execute(path), 1)
            result = json.loads(out.getvalue())
            self.assertEqual(result['status'], 'blocked'); self.assertFalse(result['dispatched'])
            self.assertNotIn('Traceback', out.getvalue())
        adapter.validate_request.assert_not_called(); adapter.execute_packet_attempt.assert_not_called()

    def test_actual_routing_consumer_reads_source_before_zero_effect_containment_stop(self):
        import model_task_execution as execution
        from tests.test_model_failover import route_fixture
        route = route_fixture()
        identity = route['model_failover']['targets'][0]['identity']
        for key in ('task', 'authorization', 'secret_check'):
            route['model_failover'][key]['acceptance_sha256'] = packets.digest(ACCEPTANCE)
        self.f.record['destinations'] = [packets.digest(packets.canonical(identity))]; self.f.refresh()
        adapter = mock.Mock(); adapter.PACKET_STOP_ADAPTERS = {}
        loader = SimpleNamespace(root=lambda: self.f.home)
        with mock.patch.object(execution, '_cli_adapter', return_value=(adapter, loader)):
            with self.assertRaisesRegex(execution.ExecutionContractError, 'containment-unavailable'):
                execution.execute_next(route['task'], route['model_failover'], self.request, self.f.ref)
            adapter.validate_request.assert_not_called()
            adapter.execute_packet_attempt.assert_not_called()
            self.assertFalse((self.f.home/'model-packets').exists())
            (self.repo/'README.md').write_text('source drift\n')
            with self.assertRaisesRegex(execution.ExecutionContractError, 'input-or-source-rejected'):
                execution.execute_next(route['task'], route['model_failover'], self.request, self.f.ref)
        adapter.execute_packet_attempt.assert_not_called()

    def test_size_private_mode_and_secret_paths_reject_without_reading_special_files(self):
        path = self.f.home/'model-task-inputs/request.json'
        path.write_bytes(b'x'*(ingress.MAX_BYTES+1))
        with self.assertRaises(ingress.InputError): self.f.read()
        self.f.artifact('request.json', packets.canonical(self.f.original))
        path.chmod(0o644)
        with self.assertRaises(ingress.InputError): self.f.read()
        path.chmod(0o600)
        self.f.record['source']['files'] = {'credentials.json': 'a'*64}; self.f.refresh()
        with self.assertRaises(ingress.InputError): self.f.read()

    def test_git_failure_is_redacted_at_actual_consumer(self):
        import model_task_execution as execution
        from tests.test_model_failover import route_fixture
        route = route_fixture()
        for key in ('task', 'authorization', 'secret_check'):
            route['model_failover'][key]['acceptance_sha256'] = packets.digest(ACCEPTANCE)
        identity = route['model_failover']['targets'][0]['identity']
        self.f.record['destinations'] = [packets.digest(packets.canonical(identity))]; self.f.refresh()
        adapter = mock.Mock(); adapter.PACKET_STOP_ADAPTERS = {}
        loader = SimpleNamespace(root=lambda: self.f.home)
        fault = subprocess.CalledProcessError(1, ['git', 'synthetic-sensitive-sentinel'], stderr='synthetic-sensitive-sentinel')
        with mock.patch.object(execution, '_cli_adapter', return_value=(adapter, loader)), mock.patch.object(ingress.git_source, 'run_git', side_effect=fault):
            with self.assertRaises(execution.ExecutionContractError) as raised:
                execution.execute_next(route['task'], route['model_failover'], self.request, self.f.ref)
        self.assertNotIn('sentinel', str(raised.exception))
        adapter.validate_request.assert_not_called(); adapter.execute_packet_attempt.assert_not_called()

    def test_ingress_does_not_execute_worktree_filter_before_containment_gate(self):
        import model_task_execution as execution
        from tests.test_model_failover import route_fixture
        marker = self.base/'filter-marker.txt'
        script = self.base/'filter.py'
        script.write_text('import pathlib,sys\np=pathlib.Path(sys.argv[1])\np.write_text((p.read_text() if p.exists() else "")+"called\\n")\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n')
        command = ' '.join(shlex.quote(str(p)) for p in (sys.executable, script, marker))
        self.git('config', 'filter.fixture.clean', command)
        (self.repo/'.gitattributes').write_text('README.md filter=fixture\n')
        self.git('add', '.gitattributes', 'README.md'); self.git('commit', '-qm', 'local filter fixture')
        self.request['expected_head'] = self.git('rev-parse', 'HEAD')
        route = route_fixture(); identity = route['model_failover']['targets'][0]['identity']
        for key in ('task', 'authorization', 'secret_check'):
            route['model_failover'][key]['acceptance_sha256'] = packets.digest(ACCEPTANCE)
        self.f = InputFixture(self.f.home, self.request, destinations=[packets.digest(packets.canonical(identity))])
        before = marker.read_text() if marker.exists() else ''
        os.utime(self.repo/'README.md', (time.time()+2, time.time()+2))
        adapter = mock.Mock(); adapter.PACKET_STOP_ADAPTERS = {}
        with mock.patch.object(execution, '_cli_adapter', return_value=(adapter, SimpleNamespace(root=lambda: self.f.home))):
            with self.assertRaisesRegex(execution.ExecutionContractError, 'containment-unavailable'):
                execution.execute_next(route['task'], route['model_failover'], self.request, self.f.ref)
        self.assertEqual(marker.read_text() if marker.exists() else '', before)
        adapter.validate_request.assert_not_called(); adapter.execute_packet_attempt.assert_not_called()


if __name__ == '__main__': unittest.main()
