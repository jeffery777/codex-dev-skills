"""Real host restriction port; no models, credentials or qualification grants."""
import json
import importlib.util
import os
import pathlib
import selectors
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests import test_model_packet_native as fixtures
import model_native_host_control as control
import model_packet_native as flow
import model_packet_store as packets


class ExecutorLossContractTests(unittest.TestCase):
    def test_full_stage_waits_leave_bounded_session_margin(self):
        path = fixtures.ROOT/'scripts/verify-model-native-governance.py'
        spec = importlib.util.spec_from_file_location('native_loss_budget_test', path)
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        waits=verifier.STAGE_WAIT_SECONDS
        self.assertEqual(set(waits), {'preflight', 'producer', 'consumer'})
        self.assertTrue(all(type(value) is int and value > 0 for value in waits.values()))
        self.assertGreaterEqual(verifier.SESSION_TTL_SECONDS, waits['producer']+waits['consumer']+40)
        self.assertLessEqual(verifier.SESSION_TTL_SECONDS, 600)
        self.assertLess(waits['preflight'], verifier.SESSION_TTL_SECONDS)

    def test_actual_wait_and_eof_are_required_for_the_selected_loss_scenario(self):
        path = fixtures.ROOT/'scripts/verify-model-native-governance.py'
        spec = importlib.util.spec_from_file_location('native_loss_wait_test', path)
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        host = verifier.old_host()
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp).resolve(); root.chmod(0o700)
            host.run_stage(root, 'producer', [sys.executable, '-I', '-S', '-B', '-c',
                'import os; os._exit(86)'], {'PATH': os.defpath, 'HOME': str(root)}, 10)
            started, waited = host.read(root, 'producer-started.json'), host.read(root, 'producer-waited.json')
            verifier.validate_stage_wait({'executor_loss': True}, 'producer', started, waited)
            for key, value in [('exit_code', 0), ('exit_code', 1), ('exit_code', True),
                    ('pid', started['pid']+1), ('pid', True), ('stderr_eof', False),
                    ('stderr_base64', 'ZXJyb3I=')]:
                bad = {**waited, key: value}
                with self.subTest(key=key, value=value), self.assertRaises(packets.PacketError):
                    verifier.validate_stage_wait({'executor_loss': True}, 'producer', started, bad)
            for scenario in (False, 'true', 1, None):
                with self.subTest(scenario=scenario), self.assertRaises(packets.PacketError):
                    verifier.validate_stage_wait({'executor_loss': scenario}, 'producer', started, waited)
            with self.assertRaises(packets.PacketError):
                verifier.validate_stage_wait({'executor_loss': True}, 'consumer', started, waited)


class HostControlTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name).resolve()
        for name in ('engine', 'packets', 'control', 'capsule'): (self.root/name).mkdir(mode=0o700)
        (self.root/'capsule/guest').mkdir(mode=0o700)
        patch = mock.patch.object(flow.native, 'validate_capsule', return_value={})
        patch.start(); self.addCleanup(patch.stop)
        self.engine = fixtures.NativeDouble(self.root/'engine')
        store = packets.PacketStore(self.root/'packets', 'packet-native-v6'); store.prepare('a'*64)
        self.kwargs = dict(endpoint='unix:///fixed.sock', image_id=flow.native.IMAGE,
            capture_root=self.root/'capsule', capture_ref={}, opt_in=True, _engine=self.engine)
        base = flow.NativeBackend(store, **self.kwargs)
        self.base_mode = base.mode()
        objective = dict(repository=str(self.root), task_id='T1', scope='fixed-native-two-attempt',
            acceptance_sha256=packets.digest(flow.FINAL_PATCH), authority_id='authority')
        self.session = control.CoordinatorSession(self.root/'control', store, self.base_mode,
            packets.digest(packets.canonical(objective)), 'd'*64)
        self.addCleanup(self.session.close)
        self.port = self.session.control
        self.h = fixtures.Harness(self.root, self.engine, self.root/'capsule', {}, control=self.port)

    def check(self, action='launch', *, persist=False, port=None):
        with self.h.store.locked() as fd:
            return (port or self.port).check(self.h.host._fence(fd), self.base_mode, action, persist=persist)

    def revoke(self):
        with self.h.store.locked() as fd:
            return self.port.revoke(self.h.host._fence(fd), self.base_mode)

    def reopened_port(self):
        return control.NativeHostControl._from_captured_stage(self.root/'control', self.session.reference)

    def test_coordinator_and_preflight_keep_disjoint_immutable_transcripts(self):
        path = fixtures.ROOT/'scripts/verify-model-native-governance.py'
        spec = importlib.util.spec_from_file_location('native_governance_transcript_test', path)
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        host = verifier.old_host()
        with mock.patch.object(verifier.native.containers.LocalDocker, '__init__', return_value=None), \
                mock.patch.object(verifier.native.containers.LocalDocker, '_transport', return_value=b'{}'):
            for label in ('coordinator', 'preflight'):
                engine = verifier.RecordedDocker('unix:///fixed.sock', self.root, label, host)
                self.assertEqual(engine._transport(['version']), b'{}')
        for label in ('coordinator', 'preflight'):
            intent = self.root/(label+'-docker-0001-intent.json')
            before = intent.read_bytes()
            self.assertEqual(json.loads(before)['argv'], ['version'])
            self.assertEqual((self.root/(label+'-docker-0001.reply')).read_bytes(), b'{}')
            with self.assertRaises(FileExistsError):
                host.save(self.root, intent.name, {'overwrite': True})
            self.assertEqual(intent.read_bytes(), before)

    def test_plain_json_and_untyped_port_cannot_issue_or_strip_control(self):
        with self.assertRaises(control.ControlError):
            control.NativeHostControl(self.root/'control', self.session.reference)
        before = sum(c[:2] == ('container','create') for c in self.engine.calls)
        with self.assertRaisesRegex(flow.lifecycle.LifecycleError, 'native-host-control-required'):
            flow.NativeBackend(self.h.store, **self.kwargs)
        with self.assertRaisesRegex(flow.lifecycle.LifecycleError, 'native-exact-host-control-required'):
            flow.NativeBackend(self.h.store, **self.kwargs, control={})
        self.assertEqual(sum(c[:2] == ('container','create') for c in self.engine.calls), before)
        self.assertNotEqual(self.h.backend.mode(), self.base_mode)

    def test_revoke_is_sticky_in_fresh_consumer_and_blocks_effects(self):
        self.h.acquire(); self.h.chain()
        before = sum(c[:2] == ('container','start') for c in self.engine.calls)
        self.assertEqual(self.revoke()['status'], 'revoked')
        with self.assertRaisesRegex(control.ControlError, 'native-host-permit-revoked'):
            self.h.launch()
        with self.assertRaisesRegex(control.ControlError, 'native-host-permit-revoked'):
            self.check(port=self.reopened_port())
        self.assertTrue(self.check('read', port=self.reopened_port())['revoked'])
        self.assertEqual(sum(c[:2] == ('container','start') for c in self.engine.calls), before)

    def test_lost_session_cannot_be_reissued_on_used_packet(self):
        self.session.close()
        with self.assertRaisesRegex(control.ControlError, 'native-host-coordinator-session-unavailable'):
            self.check()
        (self.root/'other-control').mkdir(mode=0o700)
        with self.assertRaisesRegex(control.ControlError, 'native-host-issuance-requires-unused-packet'):
            control.CoordinatorSession(self.root/'other-control', self.h.store, self.base_mode, 'a'*64, 'd'*64)

    def test_future_rollback_expiry_and_wall_epoch_drift_reject(self):
        issued = self.port._read_session()['issued']
        cases = [dict(wall_ns=issued['wall_ns']-1, monotonic_ns=issued['monotonic_ns']),
            dict(wall_ns=issued['wall_ns'], monotonic_ns=issued['monotonic_ns']-1),
            {k:v+300_000_000_000 for k,v in issued.items()},
            dict(wall_ns=issued['wall_ns']+6_000_000_000, monotonic_ns=issued['monotonic_ns'])]
        for value in cases:
            with self.subTest(value=value), mock.patch.object(control, '_clock', return_value=value):
                with self.assertRaises(control.ControlError): self.check()

    def test_fresh_process_clock_cannot_reset_watermark_and_read_is_readonly(self):
        issued = self.port._read_session()['issued']
        later = {k:v+1_000_000_000 for k,v in issued.items()}
        with mock.patch.object(control, '_clock', return_value=later): self.check(persist=True)
        raw = (self.root/'control/clock.json').read_bytes()
        older = {k:v+500_000_000 for k,v in issued.items()}
        with mock.patch.object(control, '_clock', return_value=older):
            with self.assertRaisesRegex(control.ControlError, 'watermark-rollback'):
                self.check(port=self.reopened_port())
        with mock.patch.object(control, '_clock', return_value=later): self.check('read', port=self.reopened_port())
        self.assertEqual((self.root/'control/clock.json').read_bytes(), raw)

    def test_wrong_mode_prefix_or_replaced_binding_rejects(self):
        with self.h.store.locked() as fd:
            fence = self.h.host._fence(fd)
            wrong = dict(self.base_mode, protocol_sha256='f'*64)
            with self.assertRaises(control.ControlError): self.port.check(fence, wrong, 'launch')
        with self.assertRaises(packets.PacketError): self.port.check(fence, self.base_mode, 'launch')
        path = self.h.store.root/self.h.store.packet_id/control.BINDING_FILE
        path.write_bytes(b'{}')
        with self.assertRaises(control.ControlError): self.check()

    def test_control_cannot_be_stripped_after_constructor(self):
        self.h.backend.control = None
        with self.assertRaises(packets.PacketError): self.h.current()
        self.assertFalse(any(c[:2] == ('container','create') for c in self.engine.calls))

    def test_sticky_marker_corruption_and_busy_withdrawal_fail_closed(self):
        with self.h.store.locked():
            with self.assertRaisesRegex(packets.PacketError, 'packet-busy'):
                with self.h.store.locked(): pass
        self.revoke()
        path = self.h.store.root/self.h.store.packet_id/('native-host-revoked-'+self.port.reference_sha256)
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(control.ControlError, 'revocation-drift'): self.check('read')

    def test_lost_start_reply_stays_unknown_and_is_not_replayed(self):
        self.h.acquire(); self.h.chain(); self.engine.start_fault = RuntimeError('lost')
        with self.assertRaisesRegex(RuntimeError, 'lost'): self.h.launch()
        before = list(self.engine.calls)
        ledger,_ = self.h.current()
        self.h.host.launch_reserved('launch',expected_revision=0,now=110)
        self.assertEqual(self.h.current()[0],ledger)
        self.assertEqual(self.engine.calls,before)

    def test_live_sample_times_do_not_change_historical_confirmation_bytes(self):
        self.h.acquire(); self.h.chain(); self.h.launch()
        first = self.h.host.runtime_evidence(now=110)
        second = self.h.host.runtime_evidence(now=110)
        self.assertEqual(first, second)
        a,b = self.port.samples[-2:]
        self.assertNotEqual(a['sample_end'], b['sample_end'])
        self.assertEqual(a['historical_runtime_sha256'], packets.digest(first))
        self.h.observe(); self.h.failure(); ledger,_ = self.h.publish()
        self.assertIsNotNone(ledger['checkpoint'])

    def test_session_fd_not_inherited_and_live_child_loses_permission_after_close(self):
        self.assertFalse(os.get_inheritable(self.session.session_fd))
        script = '''import json,pathlib,sys
sys.path.insert(0,sys.argv[1])
import model_native_host_control as c
value=json.loads(sys.stdin.readline());print('ready',flush=True);input()
try:c.NativeHostControl._from_captured_stage(pathlib.Path(value['root']),value['reference'])
except c.ControlError as e:
 print(str(e));sys.exit(0)
sys.exit(3)
'''
        child = subprocess.Popen([sys.executable,'-I','-S','-B','-c',script,str(pathlib.Path(flow.__file__).parent)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,close_fds=True,
            env={'PATH':os.defpath,'HOME':str(self.root),'LC_ALL':'C'})
        def cleanup():
            if child.poll() is None:
                child.kill(); child.wait(timeout=10)
            for stream in (child.stdin,child.stdout,child.stderr):
                if stream is not None: stream.close()
        self.addCleanup(cleanup)
        child.stdin.write(json.dumps(dict(root=str(self.root/'control'),reference=self.session.reference))+'\n')
        child.stdin.flush()
        with selectors.DefaultSelector() as poll:
            poll.register(child.stdout,selectors.EVENT_READ)
            self.assertTrue(poll.select(10),'child ready timeout')
            self.assertEqual(child.stdout.readline().strip(), 'ready')
        self.session.close(); out,err = child.communicate('\n',timeout=10)
        self.assertEqual(child.returncode,0,err)
        self.assertIn('coordinator-session-unavailable',out)


if __name__ == '__main__': unittest.main()
