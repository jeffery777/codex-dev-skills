"""Offline counterexamples only: no Docker, native CLI, auth or listeners."""
import base64
import copy
import hashlib
import importlib.util
import json
import os
import io
import tempfile
from pathlib import Path
import sys
import shlex
import subprocess
import unittest
from unittest import mock
import zlib

from tests.test_model_app_server_container import observed, CID, CREATED, IMAGE_CONFIG, writer_tools, terminal_output

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


class MemoryConnection:
    def __init__(self, raw): self.raw = io.BytesIO(raw); self.reply = bytearray()
    def makefile(self, *args, **kwargs): return io.BytesIO()
    def settimeout(self, seconds): pass
    def recv_into(self, buffer):
        data = self.raw.read(len(buffer))
        if not data: raise TimeoutError('fixed incomplete request')
        buffer[:len(data)] = data
        return len(data)
    def sendall(self, raw): self.reply.extend(raw)


class ExternalWriterTests(unittest.TestCase):
    def test_fixed_printf_produces_exact_newline_bytes(self):
        for case, expected in [('workspace-write', b'native-workspace-write-ok\n'),
                               ('external-write-refusal', b'forbidden-native-write\n')]:
            command = json.loads(host.guest.native_call(case)['arguments'])['cmd'].split('; ')[-1]
            arguments = shlex.split(command)
            self.assertEqual(arguments[0], 'printf')
            result = subprocess.run(['/usr/bin/printf', *arguments[1:3]], stdin=subprocess.DEVNULL,
                                    capture_output=True, timeout=3, check=True)
            self.assertEqual(result.stdout, expected)

    def request(self, case='workspace-write'):
        return {'run_id': 'a' * 32, 'native_case': case}

    def bodies(self, request):
        first = {'model': host.guest.DIRECT_MODEL, 'tools': writer_tools(request['native_case']), 'input': [
            {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': host.fixed_prompt(request)}]}]}
        call = host.guest.native_call(request['native_case'])
        second = copy.deepcopy(first); second['input'] += [call, {'type': 'function_call_output',
            'call_id': host.guest.NATIVE_CALL, 'output': terminal_output()}]
        return first, second

    def state(self):
        request = self.request(); bodies = self.bodies(request); records = []
        for stage, body in enumerate(bodies, 1):
            raw = json.dumps(body).encode(); reply = host.guest.response_bytes(stage, request['native_case'])
            record = {'stage': stage, 'response_sent': True}
            for name, data in [('request', raw), ('response', reply)]:
                record.update({name + '_base64': base64.b64encode(data).decode(), name + '_bytes': len(data),
                               name + '_sha256': hashlib.sha256(data).hexdigest()})
            records.append(record)
        raw = json.dumps(bodies[0]).encode()
        state = {'slots': 2, 'total_bytes': sum(x['request_bytes'] for x in records), 'failed': False, 'stopped': True,
            'records': records, 'declaration': host.guest.declaration(raw, host.base.probe.boundary, 'workspace-write'),
            'native_output': terminal_output(), 'native_result': {'exit_code': 0, 'body': '', 'outcome': 'native-workspace-write'},
            'catalog_fixture': self.catalog()}
        return request, state

    def catalog(self):
        fixture = host.guest.catalog_bytes()
        return {'source_kind': host.guest.CATALOG_KIND, 'query_spawn_count': 0,
            'fixture_bytes': len(fixture), 'fixture_sha256': hashlib.sha256(fixture).hexdigest(),
            'fixture_identity': [1, 2, os.getuid(), os.getgid(), 33152, 1, len(fixture), 3, 4]}

    def test_catalog_file_is_exclusive_private_fixed_and_has_no_query(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'catalog.json'; observation = {}
            with mock.patch.object(host.guest, 'CATALOG_PATH', str(path)), \
                    mock.patch.object(host.guest.subprocess, 'Popen') as spawn:
                host.guest.prepare_catalog(host.base, observation); spawn.assert_not_called()
                self.assertEqual(path.read_bytes(), host.guest.catalog_bytes())
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                host.catalog_observation(json.loads(json.dumps(observation)))
                with self.assertRaises(FileExistsError): host.guest.prepare_catalog(host.base, {})
                path.unlink(); path.symlink_to(Path(name) / 'target')
                with self.assertRaises(FileExistsError): host.guest.prepare_catalog(host.base, {})
                self.assertFalse((Path(name) / 'target').exists())
        with mock.patch.object(host.base.guest, 'read_regular', return_value=b'drift'), \
                mock.patch.object(host.guest.os, 'open', return_value=os.open(os.devnull, os.O_WRONLY)), \
                mock.patch.object(host.guest.os, 'fsync'), mock.patch.object(host.guest.os, 'lstat') as identity:
            identity.return_value = os.stat(os.devnull)
            observation = {}
            with self.assertRaises(ValueError): host.guest.prepare_catalog(host.base, observation)
            self.assertNotIn('catalog_fixture', observation)

    def test_direct_catalog_is_case_only_and_fixed_receipt_cannot_be_substituted(self):
        record = self.catalog(); state = {'catalog_fixture': record}; host.catalog_observation(state)
        catalog = json.loads(host.guest.catalog_bytes())
        self.assertEqual(len(catalog['models']), 1)
        self.assertEqual(catalog['models'][0]['slug'], host.guest.DIRECT_MODEL)
        self.assertEqual(catalog['models'][0]['tool_mode'], 'direct')
        self.assertEqual(catalog['models'][0]['base_instructions'], 'Follow only the fixed anonymous test provider.')
        self.assertFalse({'guardian', 'model_messages', 'auto_review_model_override'} & set(catalog['models'][0]))
        default = host.guest.argv(host.base.probe.boundary, host.base.guest)
        direct = host.guest.argv(host.base.probe.boundary, host.base.guest, native=True, port=1234)
        self.assertNotIn('model="fixture-direct"', default); self.assertIn('model="fixture-direct"', direct)
        self.assertNotIn('model="gpt-6-sol"', direct)
        for key, replacement in [('source_kind', 'bundled-derived'), ('query_spawn_count', 1),
                                 ('fixture_sha256', '0' * 64), ('fixture_bytes', True)]:
            bad = copy.deepcopy(state); bad['catalog_fixture'][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError): host.catalog_observation(bad)
        bad = copy.deepcopy(state); bad['catalog_fixture']['fixture_identity'][5] = 2
        with self.assertRaises(ValueError): host.catalog_observation(bad)

    def test_bundle_rejects_bomb_truncation_trailing_stream_hash_and_duplicate_json(self):
        value = host.guest.bundle({'bounded': True}); self.assertEqual(host.decode_bundle(value), {'bounded': True})
        for raw in (b'x' * (host.guest.BUNDLE_BYTES + 1), b'{"x":1,"x":2}', b'{"x":NaN}'):
            compressed = zlib.compress(raw); bad = dict(value, raw_bytes=min(len(raw), host.guest.BUNDLE_BYTES),
                raw_sha256=hashlib.sha256(raw).hexdigest(), compressed_bytes=len(compressed),
                compressed_sha256=hashlib.sha256(compressed).hexdigest(), data=base64.b64encode(compressed).decode())
            with self.assertRaises(ValueError): host.decode_bundle(bad)
        for change in ('truncated', 'trailing', 'second', 'hash', 'bytes', 'base64'):
            bad = copy.deepcopy(value); compressed = base64.b64decode(bad['data'])
            if change in ('truncated', 'trailing', 'second'):
                compressed = compressed[:-1] if change == 'truncated' else compressed + (b'x' if change == 'trailing' else compressed)
                bad.update(compressed_bytes=len(compressed), compressed_sha256=hashlib.sha256(compressed).hexdigest(),
                           data=base64.b64encode(compressed).decode())
            elif change == 'hash': bad['raw_sha256'] = '0' * 64
            elif change == 'bytes': bad['raw_bytes'] += 1
            else: bad['data'] += '!'
            with self.subTest(change=change), self.assertRaises(ValueError): host.decode_bundle(bad)

    def test_raw_two_requests_match_exact_call_prompt_output_and_response(self):
        request, state = self.state(); self.assertEqual(host.writer_observation(host.guest.bundle(state), request), state)
        body = self.bodies(request)[0]; root = copy.deepcopy(body); root['tools'] = root['tools'][0]['tools']
        host.guest.declaration(json.dumps(root).encode(), host.base.probe.boundary, 'workspace-write')
        duplicate = copy.deepcopy(root); duplicate['tools'] += body['tools']
        with self.assertRaises(ValueError): host.guest.declaration(json.dumps(duplicate).encode(), host.base.probe.boundary, 'workspace-write')
        wrong = copy.deepcopy(body); wrong['tools'][0]['name'] = 'other'
        with self.assertRaises(ValueError): host.guest.declaration(json.dumps(wrong).encode(), host.base.probe.boundary, 'workspace-write')
        for change in ('slots', 'failed', 'stopped', 'bytes', 'output', 'call', 'prompt', 'response', 'records', 'sent'):
            bad = copy.deepcopy(state)
            if change == 'slots': bad['slots'] = 3
            elif change == 'failed': bad['failed'] = True
            elif change == 'stopped': bad['stopped'] = False
            elif change == 'bytes': bad['total_bytes'] += 1
            elif change == 'output': bad['native_output'] = terminal_output(1, 'generic failure\n')
            elif change == 'records': bad['records'].append(copy.deepcopy(bad['records'][0]))
            elif change == 'sent': bad['records'][0]['response_sent'] = False
            else:
                index = 1 if change == 'call' else 0; record = bad['records'][index]
                name = 'response' if change == 'response' else 'request'
                raw = base64.b64decode(record[name + '_base64'])
                if change == 'response': raw += b'noise'
                else:
                    body = json.loads(raw)
                    if change == 'call': body['input'][1]['arguments'] = '{}'
                    else: body['input'][0]['content'][0]['text'] = 'wrong attempt'
                    raw = json.dumps(body).encode()
                bad['total_bytes'] += len(raw) - record['request_bytes'] if name == 'request' else 0
                record.update({name + '_base64': base64.b64encode(raw).decode(), name + '_bytes': len(raw),
                               name + '_sha256': hashlib.sha256(raw).hexdigest()})
            with self.subTest(change=change), self.assertRaises(ValueError):
                host.writer_observation(host.guest.bundle(bad), request)

    def test_reserved_http_slots_and_partial_or_unsupported_requests_are_sticky(self):
        request = self.request(); receipt = {}
        with mock.patch.object(host.guest.http.server, 'HTTPServer', side_effect=lambda address, handler: handler):
            handler = host.guest.provider(host.base, request, receipt)
        for body in self.bodies(request):
            raw = json.dumps(body).encode(); connection = MemoryConnection(
                b'POST /v1/responses HTTP/1.0\r\nContent-Length: ' + str(len(raw)).encode() + b'\r\n\r\n' + raw)
            handler(connection, ('127.0.0.1', 1), None)
            self.assertIn(b'200 OK', connection.reply)
        self.assertFalse(receipt['_provider_state']['failed']); self.assertEqual(receipt['_provider_state']['slots'], 2)
        handler(MemoryConnection(b'POST /v1/responses HTTP/1.0\r\nContent-Length: 2\r\n\r\n{}'), ('127.0.0.1', 1), None)
        self.assertTrue(receipt['_provider_state']['failed']); self.assertEqual(receipt['_provider_state']['slots'], 3)
        for raw in (b'PUT /v1/responses HTTP/1.0\r\n\r\n', b'bad\r\n', b'',
                b'POST /v1/responses HTTP/1.0\r\nContent-Length: 10\r\n\r\n{}',
                b'POST /v1/responses HTTP/1.0\r\nContent-Length: 2\r\nContent-Length: 2\r\n\r\n{}',
                b'POST /v1/responses HTTP/1.0\r\nContent-Length: 1048577\r\n\r\n'):
            fresh = {}
            with mock.patch.object(host.guest.http.server, 'HTTPServer', side_effect=lambda address, handler: handler):
                handler = host.guest.provider(host.base, request, fresh)
            handler(MemoryConnection(raw), ('127.0.0.1', 1), None)
            self.assertTrue(fresh['_provider_state']['failed'])

        broken = self.bodies(request)[0]; broken['tools'] = [{'type': 'unknown', 'name': 'unsupported'}]
        raw = json.dumps(broken).encode(); fresh = {}
        with mock.patch.object(host.guest.http.server, 'HTTPServer', side_effect=lambda address, handler: handler):
            handler = host.guest.provider(host.base, request, fresh)
        handler(MemoryConnection(b'POST /v1/responses HTTP/1.0\r\nContent-Length: ' + str(len(raw)).encode() + b'\r\n\r\n' + raw), ('127.0.0.1', 1), None)
        state = fresh['_provider_state']; self.assertTrue(state['failed']); self.assertFalse(state['records'][0]['response_sent'])
        self.assertEqual(base64.b64decode(state['records'][0]['request_base64']), raw)
        self.assertEqual(host.decode_bundle(host.guest.bundle(state)), state)

    def test_canary_guard_and_generic_failures_never_count_as_os_denial(self):
        good = terminal_output(2, '/usr/bin/sh: 1: cannot create /inputs/canary: Read-only file system\n')
        self.assertEqual(host.guest.native_output(good, 'external-write-refusal', host.base.guest)['body'], good.split('Output:\n')[1])
        for raw in (terminal_output(17), terminal_output(18), terminal_output(1, 'bwrap failure\n'),
                    good.replace('/inputs/canary', '/other'), good.replace('code 2', 'code 0'),
                    good.replace('/usr/bin/sh', '/usr/sbin/sh'), good + 'extra diagnostic\n'):
            with self.assertRaises(ValueError): host.guest.native_output(raw, 'external-write-refusal', host.base.guest)

    def wire(self):
        request, state = self.state(); command = json.loads(host.guest.native_call('workspace-write')['arguments'])['cmd']
        item = {'type': 'commandExecution', 'id': host.guest.NATIVE_CALL, 'cwd': '/workspace',
                'command': shlex.join(['/usr/bin/sh', '-c', command]),
                'status': 'completed', 'exitCode': 0, 'aggregatedOutput': ''}
        messages = [('out-sent', {'method': 'thread/settings/update'}), ('in', settings(model=host.guest.DIRECT_MODEL)),
            ('out-sent', {'method': 'turn/start', 'params': {'threadId': 'thread',
                'environments': [{'environmentId': 'local', 'cwd': '/workspace', 'runtimeWorkspaceRoots': ['/workspace']}],
                'input': [{'type': 'text', 'text': host.fixed_prompt(request)}]}}),
            ('in', {'method': 'turn/started', 'params': {'threadId': 'thread', 'turn': {'id': 'turn'}}}),
            ('in', {'method': 'item/started', 'params': {'threadId': 'thread', 'turnId': 'turn', 'item': item}}),
            ('in', {'method': 'item/completed', 'params': {'threadId': 'thread', 'turnId': 'turn', 'item': item}}),
            ('in', {'method': 'turn/completed', 'params': {'threadId': 'thread', 'turn': {'id': 'turn', 'status': 'completed'}}})]
        wire = [{'direction': d, 'message': m, 'raw_base64': base64.b64encode((json.dumps(m) + '\n').encode()).decode()} for d, m in messages]
        return {'thread_id': 'thread', 'turn_id': 'turn', 'wire': wire, 'settings_sequence': {'notification_index': 1}}, request, state

    def test_command_lifecycle_has_one_thread_turn_native_command_and_no_approval(self):
        receipt, request, state = self.wire(); host.writer_wire(receipt, request, state)
        for change in ('thread', 'turn', 'command', 'order', 'duplicate', 'approval', 'raw', 'exit'):
            bad = copy.deepcopy(receipt)
            if change == 'thread': bad['wire'][4]['message']['params']['threadId'] = 'wrong'
            elif change == 'turn': bad['wire'][5]['message']['params']['turnId'] = 'wrong'
            elif change == 'command': bad['wire'][4]['message']['params']['item']['command'] = 'unexpected'
            elif change == 'exit': bad['wire'][5]['message']['params']['item']['exitCode'] = 17
            elif change == 'order': bad['wire'][4:6] = reversed(bad['wire'][4:6])
            elif change == 'duplicate': bad['wire'].insert(5, copy.deepcopy(bad['wire'][4]))
            elif change == 'approval': bad['wire'].insert(5, {'direction': 'in', 'message': {'id': 42, 'method': 'item/commandExecution/requestApproval'}})
            elif change == 'raw': bad['wire'][4]['raw_base64'] = base64.b64encode(b'{}').decode()
            if change != 'raw':
                for row in bad['wire']: row['raw_base64'] = base64.b64encode((json.dumps(row['message']) + '\n').encode()).decode()
            with self.subTest(change=change), self.assertRaises(ValueError): host.writer_wire(bad, request, state)

    def test_command_display_and_null_aggregate_require_exact_argv_and_bounded_output(self):
        receipt, request, state = self.wire()
        for row in receipt['wire'][4:6]: row['message']['params']['item']['aggregatedOutput'] = None
        def refresh(value):
            for row in value['wire']: row['raw_base64'] = base64.b64encode((json.dumps(row['message']) + '\n').encode()).decode()
        refresh(receipt); host.writer_wire(receipt, request, state)
        for prefix in ('/bin/bash -c', '/usr/bin/sh -lc', '/usr/bin/sh -c extra'):
            bad = copy.deepcopy(receipt); command = json.loads(host.guest.native_call('workspace-write')['arguments'])['cmd']
            bad['wire'][4]['message']['params']['item']['command'] = prefix + ' ' + shlex.quote(command)
            refresh(bad)
            with self.assertRaises(ValueError): host.writer_wire(bad, request, state)
        state['native_result']['body'] = 'bounded output\n'
        with self.assertRaises(ValueError): host.writer_wire(receipt, request, state)
        delta = {'method': 'item/commandExecution/outputDelta', 'params': {'threadId': 'thread', 'turnId': 'turn',
                 'itemId': host.guest.NATIVE_CALL, 'delta': state['native_result']['body']}}
        receipt['wire'].insert(5, {'direction': 'in', 'message': delta}); refresh(receipt)
        host.writer_wire(receipt, request, state)
        for key, value in [('itemId', 'other'), ('delta', 'x' * 4097), ('delta', 'different output')]:
            bad = copy.deepcopy(receipt); bad['wire'][5]['message']['params'][key] = value; refresh(bad)
            with self.assertRaises(ValueError): host.writer_wire(bad, request, state)

    def test_host_postimage_rejects_extra_files_symlink_mode_and_wrong_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); workspace = root / 'workspace'; workspace.mkdir(mode=0o700)
            self.assertEqual(host.check_workspace(root, 'external-write-refusal'), {'workspace_empty': True})
            target = workspace / 'native-write.txt'; target.write_bytes(b'native-workspace-write-ok\n'); target.chmod(0o600)
            host.check_workspace(root, 'workspace-write')
            with self.assertRaises(ValueError): host.check_workspace(root, 'external-write-refusal')
            extra = workspace / 'extra'; extra.write_bytes(b'')
            with self.assertRaises(ValueError): host.check_workspace(root, 'workspace-write')
            extra.unlink(); target.chmod(0o644)
            with self.assertRaises(ValueError): host.check_workspace(root, 'workspace-write')
            target.chmod(0o600); target.write_bytes(b'wrong')
            with self.assertRaises(ValueError): host.check_workspace(root, 'workspace-write')
            target.unlink(); target.symlink_to(root / 'outside')
            with self.assertRaises((ValueError, OSError)): host.check_workspace(root, 'workspace-write')



# Fixed anonymous public CLI format; no runtime evidence is needed by these tests.
PATCH_FORMAT = {"type":"grammar","syntax":"lark","definition":"start: begin_patch hunk+ end_patch\nbegin_patch: \"*** Begin Patch\" LF\nend_patch: \"*** End Patch\" LF?\n\nhunk: add_hunk | delete_hunk | update_hunk\nadd_hunk: \"*** Add File: \" filename LF add_line+\ndelete_hunk: \"*** Delete File: \" filename LF\nupdate_hunk: \"*** Update File: \" filename LF change_move? change?\n\nfilename: /(.+)/\nadd_line: \"+\" /(.*)/ LF -> line\n\nchange_move: \"*** Move to: \" filename LF\nchange: (change_context | change_line)+ eof_line?\nchange_context: (\"@@\" | \"@@ \" /(.+)/) LF\nchange_line: (\"+\" | \"-\" | \" \") /(.*)/ LF\neof_line: \"*** End of File\" LF\n\n%import common.LF\n"}


class ExternalPatchTests(unittest.TestCase):
    def output(self, case, *, time='0'):
        body = ('Success. Updated the following files:\nA /workspace/native-patch.txt\n' if case == 'workspace-patch'
                else 'Failed to write file /inputs/canary\n')
        return 'Exit code: ' + ('0' if case == 'workspace-patch' else '1') + '\nWall time: ' + time + ' seconds\nOutput:\n' + body

    def tools(self):
        return [{'type': 'custom', 'name': 'apply_patch', 'format': copy.deepcopy(PATCH_FORMAT)}]

    def observation(self, case):
        request = {'run_id': 'a' * 32, 'native_case': case}; call = host.guest.native_call(case)
        bodies = [{'model': 'fixture-direct', 'tools': self.tools(),
                   'input': [{'type': 'message', 'content': [{'type': 'input_text', 'text': host.fixed_prompt(request)}]}]},
                  {'model': 'fixture-direct', 'tools': self.tools(),
                   'input': [call, {'type': 'custom_tool_call_output', 'call_id': host.guest.NATIVE_CALL,
                                    'output': self.output(case)}]}]
        records = []
        for stage, body in enumerate(bodies, 1):
            record = {'stage': stage, 'response_sent': True}
            for name, raw in [('request', json.dumps(body).encode()), ('response', host.guest.response_bytes(stage, case))]:
                record.update({name + '_base64': base64.b64encode(raw).decode(),
                               name + '_bytes': len(raw), name + '_sha256': hashlib.sha256(raw).hexdigest()})
            records.append(record)
        state = {'slots': 2, 'total_bytes': sum(r['request_bytes'] for r in records), 'failed': False,
                 'records': records, 'native_output': self.output(case),
                 'native_result': host.guest.native_output(self.output(case), case, host.base.guest),
                 'declaration': host.guest.declaration(json.dumps(bodies[0]).encode(), host.base.probe.boundary, case),
                 'stopped': True, 'catalog_fixture': ExternalWriterTests().catalog()}
        return request, state

    def wire(self, case):
        request, state = self.observation(case)
        change = ({'path': '/workspace/native-patch.txt', 'kind': {'type': 'add'}, 'diff': 'native-workspace-patch-ok\n'}
                  if case == 'workspace-patch' else
                  {'path': '/inputs/canary', 'kind': {'type': 'update', 'move_path': None},
                   'diff': '@@ -1 +1 @@\n-fixed-external-canary\n+forbidden-native-patch\n'})
        first = {'type': 'fileChange', 'id': host.guest.NATIVE_CALL, 'changes': [change], 'status': 'inProgress'}
        last = dict(first, status='completed' if case == 'workspace-patch' else 'failed')
        messages = [('out-sent', {'method': 'thread/settings/update'}), ('in', settings(model='fixture-direct')),
            ('out-sent', {'method': 'turn/start', 'params': {'threadId': 'thread',
                'environments': [{'environmentId': 'local', 'cwd': '/workspace', 'runtimeWorkspaceRoots': ['/workspace']}],
                'input': [{'type': 'text', 'text': host.fixed_prompt(request)}]}}),
            ('in', {'method': 'turn/started', 'params': {'threadId': 'thread', 'turn': {'id': 'turn'}}}),
            ('in', {'method': 'item/started', 'params': {'threadId': 'thread', 'turnId': 'turn', 'item': first}}),
            ('in', {'method': 'item/completed', 'params': {'threadId': 'thread', 'turnId': 'turn', 'item': last}}),
            ('in', {'method': 'turn/completed', 'params': {'threadId': 'thread', 'turn': {'id': 'turn', 'status': 'completed'}}})]
        receipt = {'thread_id': 'thread', 'turn_id': 'turn', 'settings_sequence': {'notification_index': 1},
                   'wire': [{'direction': d, 'message': copy.deepcopy(m)} for d, m in messages]}
        self.refresh(receipt)
        return receipt, request, state

    def refresh(self, receipt):
        for row in receipt['wire']:
            row['raw_base64'] = base64.b64encode((json.dumps(row['message']) + '\n').encode()).decode()

    def test_only_fixed_custom_patch_and_exact_public_format(self):
        for case in ('workspace-patch', 'patch-canary-write-failure'):
            call = host.guest.native_call(case)
            self.assertEqual(set(call), {'type', 'namespace', 'name', 'call_id', 'input'})
            self.assertEqual((call['type'], call['namespace'], call['name']), ('custom_tool_call', 'functions', 'apply_patch'))
            self.assertEqual(call['input'].count('*** Add File:') + call['input'].count('*** Update File:'), 1)
            body = {'tools': self.tools()}; host.guest.declaration(json.dumps(body).encode(), host.base.probe.boundary, case)
            for variant in ('definition', 'syntax', 'type', 'duplicate', 'namespace'):
                bad = copy.deepcopy(body)
                if variant == 'definition': bad['tools'][0]['format']['definition'] += '\n'
                elif variant == 'syntax': bad['tools'][0]['format']['syntax'] = 'regex'
                elif variant == 'type': bad['tools'][0] = {'type': 'function', 'name': 'apply_patch', 'parameters': {}}
                elif variant == 'duplicate': bad['tools'].append(copy.deepcopy(bad['tools'][0]))
                else: bad['tools'] = [{'type': 'namespace', 'name': 'other', 'tools': bad['tools']}]
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError):
                    host.guest.declaration(json.dumps(bad).encode(), host.base.probe.boundary, case)

    def test_patch_carrier_is_not_exec_carrier_or_errno_proof(self):
        for case in ('workspace-patch', 'patch-canary-write-failure'):
            result = host.guest.native_output(self.output(case), case, host.base.guest)
            self.assertTrue(result['write_phase_observed']); self.assertFalse(result['os_refusal_proven'])
            self.assertEqual(result['failure_cause'], None if case == 'workspace-patch' else 'unknown')
            host.guest.native_output(self.output(case, time='30'), case, host.base.guest)
            raw = self.output(case)
            for bad in (self.output(case, time='30.1'), self.output(case, time='0.0000'),
                        raw.replace('Wall time:', 'Total output lines: 2\nWall time:'), raw + 'extra\n',
                        raw.replace('Exit code: 0', 'Exit code: 1').replace('Exit code: 1', 'Exit code: 2'),
                        terminal_output(1, 'Failed to write file /inputs/canary\n')):
                with self.subTest(case=case, bad=bad), self.assertRaises(ValueError):
                    host.guest.native_output(bad, case, host.base.guest)
        for body in ('generic failure\n', 'Failed to read file to update /inputs/canary\n',
                     'Failed to write file /other\n', 'unsupported custom tool call: apply_patch',
                     'Failed to find expected lines in /inputs/canary\n', 'Read-only file system\n'):
            bad = 'Exit code: 1\nWall time: 0 seconds\nOutput:\n' + body
            with self.subTest(body=body), self.assertRaises(ValueError):
                host.guest.native_output(bad, 'patch-canary-write-failure', host.base.guest)
        with self.assertRaises(ValueError):
            host.guest.native_output(terminal_output(1, 'Failed to write file /inputs/canary\n'),
                                     'external-write-refusal', host.base.guest)

    def test_two_raw_requests_require_exact_custom_input_and_output_kind(self):
        for case in ('workspace-patch', 'patch-canary-write-failure'):
            request, state = self.observation(case)
            self.assertEqual(host.writer_observation(host.guest.bundle(state), request), state)
            for variant in ('call', 'output_type', 'grammar', 'claim'):
                bad = copy.deepcopy(state)
                if variant == 'claim': bad['native_result']['os_refusal_proven'] = True
                else:
                    record = bad['records'][1]; body = json.loads(base64.b64decode(record['request_base64']))
                    if variant == 'call': body['input'][0]['input'] += '\n*** Add File: /other\n+bad'
                    elif variant == 'output_type': body['input'][1]['type'] = 'function_call_output'
                    else: body['tools'][0]['format']['definition'] += '\n'
                    raw = json.dumps(body).encode(); bad['total_bytes'] += len(raw) - record['request_bytes']
                    record.update(request_base64=base64.b64encode(raw).decode(), request_bytes=len(raw),
                                  request_sha256=hashlib.sha256(raw).hexdigest())
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError):
                    host.writer_observation(host.guest.bundle(bad), request)

    def test_patch_wire_needs_exact_lifecycle_and_planned_changes(self):
        for case in ('workspace-patch', 'patch-canary-write-failure'):
            receipt, request, state = self.wire(case); host.writer_wire(receipt, request, state)
            for variant in ('thread', 'turn', 'call', 'path', 'diff', 'extra', 'status', 'move', 'order', 'duplicate', 'raw'):
                bad = copy.deepcopy(receipt); params = bad['wire'][5]['message']['params']; item = params['item']
                if variant == 'thread': params['threadId'] = 'other'
                elif variant == 'turn': params['turnId'] = 'other'
                elif variant == 'call': item['id'] = 'other'
                elif variant == 'path': item['changes'][0]['path'] = '/other'
                elif variant == 'diff': item['changes'][0]['diff'] += 'extra'
                elif variant == 'extra': item['changes'].append(copy.deepcopy(item['changes'][0]))
                elif variant == 'status': item['status'] = 'declined'
                elif variant == 'move': item['changes'][0]['kind']['movePath'] = '/other'
                elif variant == 'order': bad['wire'][4:6] = reversed(bad['wire'][4:6])
                elif variant == 'duplicate': bad['wire'].insert(5, copy.deepcopy(bad['wire'][4]))
                self.refresh(bad)
                if variant == 'raw': bad['wire'][4]['raw_base64'] = base64.b64encode(b'{}').decode()
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError):
                    host.writer_wire(bad, request, state)

    def test_other_tool_approval_and_deprecated_output_event_rejected(self):
        receipt, request, state = self.wire('workspace-patch')
        for method in ('item/commandExecution/outputDelta', 'item/fileChange/outputDelta',
                       'item/fileChange/requestApproval', 'item/tool/call', 'model/rerouted', 'error'):
            bad = copy.deepcopy(receipt); bad['wire'].insert(5, {'direction': 'in',
                'message': {'method': method, 'params': {'threadId': 'thread', 'turnId': 'turn'}}})
            self.refresh(bad)
            with self.subTest(method=method), self.assertRaises(ValueError): host.writer_wire(bad, request, state)

    def test_patch_postimage_is_actual_regular_singlelink_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); work = root / 'workspace'; work.mkdir(mode=0o700)
            host.check_workspace(root, 'patch-canary-write-failure')
            target = work / 'native-patch.txt'; target.write_bytes(b'native-workspace-patch-ok\n'); target.chmod(0o600)
            host.check_workspace(root, 'workspace-patch')
            with self.assertRaises(ValueError): host.check_workspace(root, 'patch-canary-write-failure')
            alias = work / 'alias'; os.link(target, alias)
            with self.assertRaises(ValueError): host.check_workspace(root, 'workspace-patch')
            alias.unlink(); target.chmod(0o644)
            with self.assertRaises(ValueError): host.check_workspace(root, 'workspace-patch')
            target.chmod(0o600); target.write_bytes(b'partial')
            with self.assertRaises(ValueError): host.check_workspace(root, 'workspace-patch')
            target.unlink(); target.symlink_to(root / 'missing')
            with self.assertRaises((ValueError, OSError)): host.check_workspace(root, 'workspace-patch')

# Independent fixed public schema and payload; neither is built by the guest.
INPUT_PAYLOAD = {'questions': [{'id': 'fixed_input_choice', 'header': 'Fixture',
    'question': 'Choose the fixed fixture option.', 'options': [
        {'label': 'A (Recommended)', 'description': 'Fixed option A.'},
        {'label': 'B', 'description': 'Fixed option B.'}]}]}
INPUT_SCHEMA = {'type': 'object', 'properties': {'questions': {'type': 'array',
    'description': 'Questions to show the user. Prefer 1 and do not exceed 3',
    'items': {'type': 'object', 'properties': {
        'id': {'type': 'string', 'description': 'Stable identifier for mapping answers (snake_case).'},
        'header': {'type': 'string', 'description': 'Short header label shown in the UI (12 or fewer chars).'},
        'question': {'type': 'string', 'description': 'Single-sentence prompt shown to the user.'},
        'options': {'type': 'array', 'description': 'Provide 2-3 mutually exclusive choices. Put the recommended option first and suffix its label with "(Recommended)". Do not include an "Other" option in this list; the client will add a free-form "Other" option automatically.',
            'items': {'type': 'object', 'properties': {
                'label': {'type': 'string', 'description': 'User-facing label (1-5 words).'},
                'description': {'type': 'string', 'description': 'One short sentence explaining impact/tradeoff if selected.'}},
                'required': ['label', 'description'], 'additionalProperties': False}}},
        'required': ['id', 'header', 'question', 'options'], 'additionalProperties': False}}},
    'required': ['questions'], 'additionalProperties': False}
INPUT_ERRORS = {'input-default-guard': 'request_user_input is unavailable in Default mode',
                'input-disabled-dispatch': 'unsupported call: request_user_input'}


class ExternalInputTests(unittest.TestCase):
    def settings(self, *, adopted=False):
        return settings(disabledPluginIds=[], approvalsReviewer='user', serviceTier='default',
            effort='low', summary='none', multiAgentMode='explicitRequestOnly', personality='none',
            model='fixture-direct', collaborationMode={'mode': 'default', 'settings': {
                'model': 'fixture-direct', 'reasoning_effort': 'low', 'developer_instructions':
                    'Fixed anonymous default-mode probe.' if adopted else None}})

    def tools(self, case):
        return [] if case == 'input-disabled-dispatch' else [
            {'type': 'function', 'name': 'request_user_input', 'parameters': copy.deepcopy(INPUT_SCHEMA)}]

    def observation(self, case):
        request = {'run_id': 'a' * 32, 'native_case': case}
        call = {'type': 'function_call', 'namespace': 'functions', 'name': 'request_user_input',
                'call_id': 'external-native-writer-1', 'arguments': json.dumps(INPUT_PAYLOAD, separators=(',', ':'))}
        bodies = [{'model': 'fixture-direct', 'tools': self.tools(case),
                   'input': [{'type': 'message', 'content': [{'type': 'input_text', 'text': host.fixed_prompt(request)}]}]},
                  {'model': 'fixture-direct', 'tools': self.tools(case), 'input': [
                      call, {'type': 'function_call_output', 'call_id': 'external-native-writer-1',
                             'output': INPUT_ERRORS[case]}]}]
        records = []
        for stage, body in enumerate(bodies, 1):
            record = {'stage': stage, 'response_sent': True}
            for name, raw in [('request', json.dumps(body).encode()), ('response', host.guest.response_bytes(stage, case))]:
                record.update({name + '_base64': base64.b64encode(raw).decode(), name + '_bytes': len(raw),
                               name + '_sha256': hashlib.sha256(raw).hexdigest()})
            records.append(record)
        state = {'slots': 2, 'total_bytes': sum(r['request_bytes'] for r in records), 'failed': False,
            'records': records, 'native_output': INPUT_ERRORS[case], 'native_result': {
                'body': INPUT_ERRORS[case], 'outcome': case + '-observed', 'denial_observed': True,
                'native_arguments_parsed': False, 'user_elicitation_observed': False},
            'declaration': host.guest.declaration(json.dumps(bodies[0]).encode(), host.base.probe.boundary, case),
            'stopped': True, 'catalog_fixture': ExternalWriterTests().catalog()}
        return request, state

    def rewrite(self, state, body):
        record = state['records'][1]; raw = json.dumps(body).encode()
        state['total_bytes'] += len(raw) - record['request_bytes']
        record.update(request_base64=base64.b64encode(raw).decode(), request_bytes=len(raw),
                      request_sha256=hashlib.sha256(raw).hexdigest())

    def wire(self, case):
        request, state = self.observation(case)
        mode = {'mode': 'default', 'settings': {'model': 'fixture-direct',
                'reasoning_effort': 'low', 'developer_instructions': None}}
        adopted = copy.deepcopy(mode)
        adopted['settings']['developer_instructions'] = 'Fixed anonymous default-mode probe.'
        messages = [('out-sent', {'method': 'thread/settings/update'}),
            ('in', self.settings()),
            ('out-sent', {'method': 'turn/start', 'params': {'threadId': 'thread',
                'environments': [{'environmentId': 'local', 'cwd': '/workspace', 'runtimeWorkspaceRoots': ['/workspace']}],
                'input': [{'type': 'text', 'text': host.fixed_prompt(request)}], 'collaborationMode': adopted}}),
            ('in', self.settings(adopted=True)),
            ('in', {'method': 'turn/started', 'params': {'threadId': 'thread', 'turn': {'id': 'turn'}}}),
            ('in', {'method': 'turn/completed', 'params': {'threadId': 'thread', 'turn': {'id': 'turn', 'status': 'completed'}}})]
        receipt = {'thread_id': 'thread', 'turn_id': 'turn', 'settings_sequence': {
                       'out_sent_index': 0, 'notification_index': 1,
                       'unique_in_bootstrap_prefix': True, 'turn_started': False},
                   'wire': [{'direction': d, 'message': copy.deepcopy(m)} for d, m in messages]}
        ExternalPatchTests().refresh(receipt)
        return receipt, request, state

    def test_fixed_payload_is_host_checked_without_native_parsing_claim(self):
        for case in INPUT_ERRORS:
            call = host.guest.native_call(case)
            self.assertEqual(json.loads(call['arguments']), INPUT_PAYLOAD)
            host.input_call_confirmed(call)
            for variant in ('namespace', 'type', 'name', 'extra', 'question-extra', 'missing', 'non-string', 'duplicate'):
                bad = copy.deepcopy(call)
                if variant in ('namespace', 'type', 'name'): bad[variant] = 'other'
                elif variant == 'extra': bad['extra'] = True
                elif variant == 'duplicate': bad['arguments'] = '{"questions":[],"questions":[]}'
                else:
                    args = json.loads(bad['arguments'])
                    if variant == 'question-extra': args['questions'][0]['extra'] = True
                    elif variant == 'missing': del args['questions'][0]['options']
                    else: args['questions'][0]['header'] = False
                    bad['arguments'] = json.dumps(args)
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError): host.input_call_confirmed(bad)

    def test_declaration_schema_and_exclusion_are_separate(self):
        self.assertEqual(host.base.probe.manifest.sha(INPUT_SCHEMA), '23ee6f1a8cd81c9d2491cbd33a3cb09d755e6c85d368f3beb346753cfd4558a3')
        for case in INPUT_ERRORS:
            host.guest.declaration(json.dumps({'tools': self.tools(case)}).encode(), host.base.probe.boundary, case)
            for variant in ('missing-or-enabled', 'schema', 'namespace', 'custom', 'duplicate'):
                bad = {'tools': self.tools('input-default-guard')}
                if variant == 'missing-or-enabled': bad['tools'] = [] if case == 'input-default-guard' else bad['tools']
                elif variant == 'schema': bad['tools'][0]['parameters']['additionalProperties'] = True
                elif variant == 'namespace': bad['tools'] = [{'type': 'namespace', 'name': 'other', 'tools': bad['tools']}]
                elif variant == 'custom': bad['tools'][0] = {'type': 'custom', 'name': 'request_user_input', 'format': {'type': 'text'}}
                else: bad['tools'].append(copy.deepcopy(bad['tools'][0]))
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError):
                    host.guest.declaration(json.dumps(bad).encode(), host.base.probe.boundary, case)

    def test_explicit_case_flags_never_enable_default_mode_or_plan(self):
        for case in (None, *host.guest.CASES):
            args = host.guest.argv(host.base.probe.boundary, host.base.guest, native=bool(case), case=case)
            flags = args[5::2]
            self.assertEqual([x for x in flags if x.startswith('tools.experimental_request_user_input.enabled=')],
                ['tools.experimental_request_user_input.enabled=' + ('true' if case == 'input-default-guard' else 'false')])
            self.assertEqual([x for x in flags if x.startswith('features.default_mode_request_user_input=')],
                ['features.default_mode_request_user_input=false'])
        for case in INPUT_ERRORS:
            with self.assertRaises(ValueError): host.guest.argv(host.base.probe.boundary, host.base.guest, case=case)
        self.assertEqual(host.input_mode(), {'mode': 'default', 'settings': {'model': 'fixture-direct',
                         'reasoning_effort': 'low', 'developer_instructions': None}})
        self.assertEqual(host.input_mode(adopted=True), {'mode': 'default', 'settings': {'model': 'fixture-direct',
                         'reasoning_effort': 'low', 'developer_instructions': 'Fixed anonymous default-mode probe.'}})

    def test_exact_denials_reject_cancel_generic_cross_case_and_wrappers(self):
        for case, body in INPUT_ERRORS.items():
            result = host.guest.native_output(body, case, host.base.guest)
            self.assertFalse(result['native_arguments_parsed']); self.assertFalse(result['user_elicitation_observed'])
            for bad in (body + '\n', 'Error: ' + body, 'unsupported call: functions.request_user_input',
                        'request_user_input is unavailable in Plan mode', 'request_user_input can only be used by the root thread',
                        'request_user_input requires non-empty options for every question', 'Cancelled', 'generic failure',
                        [{'type': 'input_text', 'text': body}], INPUT_ERRORS[next(c for c in INPUT_ERRORS if c != case)]):
                with self.subTest(case=case, bad=bad), self.assertRaises(ValueError):
                    host.guest.native_output(bad, case, host.base.guest)

    def test_raw_http_needs_one_exact_function_call_and_plain_output(self):
        for case in INPUT_ERRORS:
            request, state = self.observation(case); host.writer_observation(host.guest.bundle(state), request)
            for variant in ('arguments', 'namespace', 'call-id', 'custom', 'wrapper', 'duplicate-output', 'other-call', 'false-parsing-claim'):
                bad = copy.deepcopy(state)
                if variant == 'false-parsing-claim': bad['native_result']['native_arguments_parsed'] = True
                else:
                    body = json.loads(base64.b64decode(bad['records'][1]['request_base64']))
                    if variant == 'arguments': body['input'][0]['arguments'] = '{}'
                    elif variant == 'namespace': body['input'][0]['namespace'] = 'other'
                    elif variant == 'call-id': body['input'][1]['call_id'] = 'other'
                    elif variant == 'custom': body['input'][1]['type'] = 'custom_tool_call_output'
                    elif variant == 'wrapper': body['input'][1]['output'] = [{'type': 'input_text', 'text': INPUT_ERRORS[case]}]
                    elif variant == 'duplicate-output': body['input'].append(copy.deepcopy(body['input'][1]))
                    else: body['input'].append({'type': 'function_call', 'name': 'exec_command', 'call_id': 'other', 'arguments': '{}'})
                    self.rewrite(bad, body)
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError):
                    host.writer_observation(host.guest.bundle(bad), request)

    def test_wire_requires_default_and_zero_native_tool_or_server_reply(self):
        for case in INPUT_ERRORS:
            receipt, request, state = self.wire(case); host.writer_wire(receipt, request, state)
            for variant in ('mode', 'thread', 'turn', 'failed', 'duplicate', 'order', 'response'):
                bad = copy.deepcopy(receipt)
                if variant == 'mode': bad['wire'][2]['message']['params']['collaborationMode']['mode'] = 'plan'
                elif variant == 'thread': bad['wire'][4]['message']['params']['threadId'] = 'other'
                elif variant == 'turn': bad['wire'][5]['message']['params']['turn']['id'] = 'other'
                elif variant == 'failed': bad['wire'][5]['message']['params']['turn']['status'] = 'failed'
                elif variant == 'duplicate': bad['wire'].append(copy.deepcopy(bad['wire'][5]))
                elif variant == 'order': bad['wire'][4:6] = reversed(bad['wire'][4:6])
                else: bad['wire'].insert(4, {'direction': 'out-sent', 'message': {'id': 42, 'result': {'answers': {}}}})
                ExternalPatchTests().refresh(bad)
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError): host.writer_wire(bad, request, state)
            for method, item in [('item/started', {'type': 'functionCallOutput'}), ('item/completed', {'type': 'commandExecution'}),
                    ('item/started', {'type': 'fileChange'}), ('item/started', {'type': 'dynamicToolCall'}),
                    ('item/tool/requestUserInput', {}), ('turn/diff/updated', {}), ('rawResponseItem/completed', {})]:
                bad = copy.deepcopy(receipt); bad['wire'].insert(4, {'direction': 'in', 'message': {
                    'method': method, 'params': {'threadId': 'thread', 'turnId': 'turn', 'item': item}}})
                ExternalPatchTests().refresh(bad)
                with self.subTest(case=case, method=method), self.assertRaises(ValueError): host.writer_wire(bad, request, state)

    def test_settings_adoption_requires_two_distinct_fixed_observations(self):
        for case in INPUT_ERRORS:
            receipt, request, state = self.wire(case)
            host.writer_wire(receipt, request, state)
            self.assertEqual(receipt['input_adoption_notification'], receipt['wire'][3]['message'])
            self.assertEqual(receipt['input_adoption_sequence'], {
                'bootstrap_notification_index': 1, 'turn_start_out_sent_index': 2,
                'adopted_notification_index': 3, 'turn_started_index': 4, 'turn_completed_index': 5,
                'exactly_two_settings_notifications': True, 'instructions_source': 'fixed-anonymous-literal'})
            for variant in ('missing-bootstrap', 'missing-adopted', 'duplicate-bootstrap', 'duplicate-adopted',
                    'adopted-before-send', 'adopted-after-start', 'bootstrap-after-send', 'third',
                    'literal-change', 'null', 'built-in', 'bootstrap-literal', 'thread', 'effort',
                    'model', 'sandbox', 'approval', 'provider', 'global-unique-claim', 'missing-prefix-proof'):
                bad = copy.deepcopy(receipt)
                if variant.startswith('missing-') and variant != 'missing-prefix-proof':
                    del bad['wire'][1 if variant == 'missing-bootstrap' else 3]
                elif variant.startswith('duplicate-'):
                    bad['wire'].insert(3, copy.deepcopy(bad['wire'][1 if variant == 'duplicate-bootstrap' else 3]))
                elif variant == 'third': bad['wire'].append(copy.deepcopy(bad['wire'][3]))
                elif variant in ('adopted-before-send', 'adopted-after-start', 'bootstrap-after-send'):
                    a, b = {'adopted-before-send': (2, 3), 'adopted-after-start': (3, 4),
                            'bootstrap-after-send': (1, 2)}[variant]
                    bad['wire'][a], bad['wire'][b] = bad['wire'][b], bad['wire'][a]
                elif variant == 'global-unique-claim': bad['settings_sequence']['unique_in_observed_wire'] = True
                elif variant == 'missing-prefix-proof': del bad['settings_sequence']['unique_in_bootstrap_prefix']
                else:
                    params = bad['wire'][3]['message']['params']; value = params['threadSettings']
                    if variant == 'thread': params['threadId'] = 'other'
                    elif variant in ('effort', 'model'): value['collaborationMode']['settings'][
                        'reasoning_effort' if variant == 'effort' else 'model'] = 'other'
                    elif variant in ('sandbox', 'approval', 'provider'):
                        value[{'sandbox': 'sandboxPolicy', 'approval': 'approvalPolicy',
                               'provider': 'modelProvider'}[variant]] = 'other'
                    elif variant == 'bootstrap-literal':
                        bad['wire'][1]['message']['params']['threadSettings']['collaborationMode']['settings'][
                            'developer_instructions'] = 'Fixed anonymous default-mode probe.'
                    else: value['collaborationMode']['settings']['developer_instructions'] = {
                        'literal-change': 'Fixed anonymous default-mode probe!', 'null': None,
                        'built-in': 'Unaccepted built-in instructions.'}[variant]
                ExternalPatchTests().refresh(bad)
                with self.subTest(case=case, variant=variant), self.assertRaises(ValueError):
                    host.writer_wire(bad, request, state)

    def test_turn_rpc_response_can_interleave_with_adoption_notifications(self):
        for case in INPUT_ERRORS:
            for index in (3, 4, 5, 6):
                receipt, request, state = self.wire(case)
                receipt['wire'].insert(index, {'direction': 'in', 'message': {
                    'id': 4, 'result': {'turn': {'id': 'turn'}}}})
                ExternalPatchTests().refresh(receipt)
                with self.subTest(case=case, index=index): host.writer_wire(receipt, request, state)

    def test_complete_settings_reject_each_missing_changed_and_extra_field(self):
        for case in INPUT_ERRORS:
            receipt, request, state = self.wire(case)
            for index in (1, 3):
                golden = receipt['wire'][index]['message']['params']['threadSettings']
                self.assertEqual(len(golden), 14)
                for key in golden:
                    for variant in ('missing', 'changed'):
                        bad = copy.deepcopy(receipt); value = bad['wire'][index]['message']['params']['threadSettings']
                        if variant == 'missing': del value[key]
                        else:
                            value[key] = {'disabledPluginIds': ['unexpected'], 'cwd': '/elsewhere',
                                'approvalPolicy': 'on-request', 'approvalsReviewer': 'auto_review',
                                'sandboxPolicy': {'type': 'readOnly', 'networkAccess': False},
                                'activePermissionProfile': {'id': 'unexpected', 'extends': None},
                                'model': 'other', 'modelProvider': 'other', 'serviceTier': 'priority',
                                'effort': 'high', 'summary': 'detailed',
                                'collaborationMode': {'mode': 'plan', 'settings': copy.deepcopy(
                                    golden['collaborationMode']['settings'])},
                                'multiAgentMode': 'proactive', 'personality': 'friendly'}[key]
                        ExternalPatchTests().refresh(bad)
                        with self.subTest(case=case, index=index, key=key, variant=variant), self.assertRaises(ValueError):
                            host.writer_wire(bad, request, state)
                bad = copy.deepcopy(receipt)
                bad['wire'][index]['message']['params']['threadSettings']['unexpected'] = None
                ExternalPatchTests().refresh(bad)
                with self.subTest(case=case, index=index), self.assertRaises(ValueError): host.writer_wire(bad, request, state)

    def test_input_bootstrap_pins_settings_and_prefix_proof(self):
        for case in INPUT_ERRORS:
            for before in (False, True):
                peer = Peer(before_ack=before); peer.note = self.settings()
                original_request = peer.request
                def request(method, params):
                    value = original_request(method, params)
                    if method == 'thread/start': value['model'] = 'fixture-direct'
                    return value
                peer.request = request; receipt = {}; host.bootstrap(peer, receipt, case)
                self.assertEqual(peer.calls[2][1], {'threadId': 'thread', 'cwd': '/workspace',
                    'approvalPolicy': 'never', 'sandboxPolicy': {'type': 'externalSandbox', 'networkAccess': 'restricted'},
                    'disabledPluginIds': [], 'approvalsReviewer': 'user', 'effort': 'low', 'summary': 'none',
                    'serviceTier': 'default', 'personality': 'none'})
                self.assertFalse(peer.calls[1][1]['experimentalRawEvents'])
                self.assertEqual(receipt['settings_notification'], self.settings())
                self.assertTrue(receipt['settings_sequence']['unique_in_bootstrap_prefix'])
                self.assertNotIn('unique_in_observed_wire', receipt['settings_sequence'])

    def test_input_session_refuses_server_requests_before_dispatch(self):
        session = object.__new__(host.InputObservationSession)
        session._fail = mock.Mock(side_effect=ValueError('fixed-request-denied'))
        with mock.patch.object(host.base.probe.AdmissionSession, '_dispatch') as common:
            for method in ('item/tool/requestUserInput', 'item/tool/call', 'item/commandExecution/requestApproval'):
                with self.subTest(method=method), self.assertRaises(ValueError):
                    session._dispatch({'id': 42, 'method': method, 'params': {}}, 1, 1)
            common.assert_not_called()


if __name__ == '__main__':
    unittest.main()
