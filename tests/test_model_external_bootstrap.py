"""Offline counterexamples only: no Docker, native CLI, auth or listeners."""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest

from tests.test_model_app_server_container import observed, CID, CREATED, IMAGE_CONFIG

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('external_bootstrap_test', ROOT / 'scripts/verify-model-external-bootstrap.py')
host = importlib.util.module_from_spec(spec); spec.loader.exec_module(host)


def settings(**changes):
    value = {'cwd': '/workspace', 'approvalPolicy': 'never', 'sandboxPolicy': dict(host.POLICY),
             'activePermissionProfile': None, 'model': 'gpt-6-sol', 'modelProvider': 'fixture'}
    value.update(changes)
    return {'method': 'thread/settings/updated', 'params': {'threadId': 'thread', 'threadSettings': value}}


class Peer:
    def __init__(self, *, stale=False, duplicate=False, before_ack=False, drift=False, ack=None):
        self.wire = []; self.stale = stale; self.duplicate = duplicate
        self.before_ack = before_ack; self.drift = drift; self.ack = {} if ack is None else ack
        self.calls = []; self.note = settings(modelProvider='other') if drift else settings()
        self.read = False

    def _deadline(self): return 1

    def _drain_available(self, deadline):
        if self.stale and len(self.calls) == 2:
            self.wire.append({'direction': 'in', 'message': settings()})
        if self.duplicate and self.read:
            self.wire.append({'direction': 'in', 'message': self.note})

    def request(self, method, params):
        self.calls.append((method, params)); self.wire.append({'direction': 'out-sent', 'message': {'method': method, 'params': params}})
        if method == 'initialize': return {}
        if method == 'thread/start':
            return {'thread': {'id': 'thread'}, 'model': 'gpt-6-sol', 'modelProvider': 'fixture',
                    'cwd': '/workspace', 'approvalPolicy': 'never', 'instructionSources': [],
                    'sandbox': {'type': 'readOnly', 'networkAccess': False}}
        if method == 'thread/settings/update':
            if self.before_ack: self.wire.append({'direction': 'in', 'message': self.note})
            return self.ack
        raise AssertionError('unexpected-request')

    def notification(self):
        self.read = True
        if not self.before_ack: self.wire.append({'direction': 'in', 'message': self.note})
        return self.note


class ExternalBootstrapTests(unittest.TestCase):
    def policy_value(self):
        root = Path('/fixed/evidence'); uid, gid = os.getuid(), os.getgid()
        value = observed(root, 'external', uid, gid)
        value['Config']['Cmd'] = list(host.WRAPPER); value['Config']['WorkingDir'] = '/workspace'
        value['Mounts'] = [{'Type': 'bind', 'Source': str(root / folder), 'Destination': dest,
                            'RW': rw, 'Propagation': 'rprivate'} for folder, dest, rw in
                           [('capture', '/fixture', False), ('inputs', '/inputs', False), ('workspace', '/workspace', True)]]
        value['HostConfig']['Tmpfs'] = {'/tmp': host.base.tmpfs_options(uid, gid)}
        return root, uid, gid, value

    def test_fixed_three_mount_policy_preserves_raw_evidence(self):
        root, uid, gid, value = self.policy_value(); original = copy.deepcopy(value)
        self.assertEqual(host.policy(value, root, 'external', uid, gid, CID, image_config=IMAGE_CONFIG), CREATED)
        self.assertEqual(value, original)
        command = host.create_argv(root, 'external', uid, gid)
        self.assertEqual(command.count('--mount'), 3)
        self.assertIn('--pull=never', command)
        self.assertFalse(any('dst=/control' in x or 'docker.sock' in x for x in command))
        self.assertEqual(command[-len(host.WRAPPER):], host.WRAPPER)

    def test_rejects_extra_or_writable_inputs_and_wrong_physical_sources(self):
        root, uid, gid, value = self.policy_value()
        cases = []
        for key, replacement in [('RW', True), ('Source', '/host/auth'), ('Propagation', 'rshared'), ('Type', 'volume')]:
            changed = copy.deepcopy(value); changed['Mounts'][1][key] = replacement; cases.append(changed)
        changed = copy.deepcopy(value); changed['Mounts'].append(copy.deepcopy(changed['Mounts'][0])); cases.append(changed)
        changed = copy.deepcopy(value); changed['Config']['WorkingDir'] = '/control'; cases.append(changed)
        changed = copy.deepcopy(value); changed['Config']['Cmd'] = host.base.WRAPPER_CMD; cases.append(changed)
        for changed in cases:
            with self.subTest(changed=changed['Mounts']), self.assertRaises(ValueError):
                host.policy(changed, root, 'external', uid, gid, CID, image_config=IMAGE_CONFIG)

    def test_outer_privilege_network_limits_and_state_are_not_projected_away(self):
        root, uid, gid, value = self.policy_value()
        cases = [('HostConfig', 'Privileged', True), ('HostConfig', 'CapAdd', ['SYS_ADMIN']),
                 ('HostConfig', 'NetworkMode', 'host'), ('HostConfig', 'Tmpfs', {}),
                 ('HostConfig', 'ReadonlyRootfs', False), ('HostConfig', 'PidsLimit', 0),
                 ('State', 'Running', True), ('Config', 'User', '0:0')]
        for section, key, replacement in cases:
            changed = copy.deepcopy(value); changed[section][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                host.policy(changed, root, 'external', uid, gid, CID, image_config=IMAGE_CONFIG)

    def test_only_readonly_start_then_one_settings_update_no_turn(self):
        for before in (False, True):
            peer = Peer(before_ack=before); receipt = {}; host.bootstrap(peer, receipt)
            self.assertEqual([m for m, _ in peer.calls], ['initialize', 'thread/start', 'thread/settings/update'])
            self.assertEqual(peer.calls[1][1]['sandbox'], 'read-only')
            self.assertNotIn('permissions', peer.calls[1][1])
            self.assertFalse(receipt['settings_sequence']['turn_started'])
            self.assertGreater(receipt['settings_sequence']['notification_index'], receipt['settings_sequence']['out_sent_index'])

    def test_ack_alone_stale_duplicate_and_policy_drift_never_pass(self):
        for options in ({'stale': True}, {'duplicate': True}, {'drift': True}, {'ack': {'queued': True}}):
            peer = Peer(**options)
            with self.subTest(options=options), self.assertRaises(ValueError): host.bootstrap(peer, {})
            self.assertNotIn('turn/start', [m for m, _ in peer.calls])

    def test_settings_match_rejects_thread_model_provider_approval_and_profile_drift(self):
        self.assertFalse(host.settings_match({'method': 'thread/started'}, 'thread'))
        for key, replacement in [('sandboxPolicy', {'type': 'dangerFullAccess'}), ('cwd', '/other'),
                ('model', 'other'), ('modelProvider', 'openai'), ('approvalPolicy', 'on-request'),
                ('activePermissionProfile', {'id': 'named', 'extends': None})]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                host.settings_match(settings(**{key: replacement}), 'thread')
        with self.assertRaises(ValueError): host.settings_match(settings(), 'different')

    def test_cli_uses_fresh_tmpfs_context_without_named_permissions_or_auth(self):
        command = host.guest.argv(host.base.probe.boundary, host.base.guest)
        self.assertIn('sandbox_mode="read-only"', command)
        self.assertIn('allow_login_shell=false', command)
        self.assertIn('project_doc_max_bytes=0', command)
        self.assertFalse(any(x.startswith(('permissions.', 'default_permissions=')) for x in command))
        self.assertEqual(host.guest.ENV['CODEX_HOME'], '/tmp/home/.codex')
        self.assertEqual(set(host.FILES), set(host.base.FILES) | set(host.guest.FILES))

    def frame(self):
        raw = b'anonymous stderr\n'; value = {'schema_version': 1, 'scope': 'anonymous-external-bootstrap-only',
            'run_id': 'a' * 32, 'qualified': False, 'production_qualified': False, 'passed': True,
            'cli_spawn_count': 1, 'cli_wait': 'observed', 'cli_exit_code': 0, 'cli_pid': 42,
            'workspace_empty': True, 'canary_preserved': True,
            'cli_argv': host.guest.argv(host.base.probe.boundary, host.base.guest),
            'cli_stderr': {'raw_base64': base64.b64encode(raw).decode(), 'captured_bytes': len(raw),
                'total_bytes': len(raw), 'captured_prefix_sha256': hashlib.sha256(raw).hexdigest(),
                'eof': True, 'reader_finished': True, 'reader_error': False, 'overflow': False, 'truncated': False}}
        frame = host.guest.PREFIX + json.dumps(value).encode() + b'\n'
        return {'raw': frame, 'eof': True, 'reader_finished': True, 'reader_error': False,
                'overflow': False, 'truncated': False}, {'run_id': 'a' * 32}

    def test_frame_is_finite_untrusted_observation_with_nested_stderr_integrity(self):
        frame, request = self.frame(); self.assertTrue(host.guest_frame(frame, request)['passed'])
        for key in ('eof', 'reader_finished', 'reader_error', 'overflow', 'truncated'):
            changed = copy.deepcopy(frame); changed[key] = not changed[key]
            with self.subTest(key=key), self.assertRaises(ValueError): host.guest_frame(changed, request)
        for raw in (frame['raw'] + frame['raw'], b'noise' + frame['raw'], host.guest.PREFIX + b'{"a":1,"a":2}\n'):
            changed = copy.deepcopy(frame); changed['raw'] = raw
            with self.assertRaises(ValueError): host.guest_frame(changed, request)
        changed = copy.deepcopy(frame); value = json.loads(frame['raw'][len(host.guest.PREFIX):]); value['cli_stderr']['total_bytes'] += 1
        changed['raw'] = host.guest.PREFIX + json.dumps(value).encode() + b'\n'
        with self.assertRaises(ValueError): host.guest_frame(changed, request)


if __name__ == '__main__':
    unittest.main()
