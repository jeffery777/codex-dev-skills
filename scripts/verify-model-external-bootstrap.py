#!/usr/bin/env python3
"""Explicit anonymous external-OS bootstrap or fixed native probes; no qualification."""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shlex
import stat
import sys
import tempfile
import time
import uuid
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import model_external_bootstrap_fixture as guest

base = guest.load('external_bootstrap_fixed_host', ROOT / 'scripts/verify-model-app-server-container.py')
helpers = base.helpers
FILES = base.FILES + guest.FILES
WRAPPER = ['-i', 'PATH=' + guest.ENV['PATH'], 'HOME=' + guest.ENV['HOME'], 'LANG=' + guest.ENV['LANG'],
           '/usr/local/bin/python3', '-I', '-S', '-B', '/fixture/scripts/model_external_bootstrap_fixture.py']
POLICY = {'type': 'externalSandbox', 'networkAccess': 'restricted'}


class InputObservationSession(base.probe.AdmissionSession):
    """These two negative controls never answer any server request."""
    def _dispatch(self, message, expected_id, deadline):
        if 'method' in message and 'id' in message:
            self._fail('external-input-server-request')
        return super()._dispatch(message, expected_id, deadline)


INPUT_DEVELOPER_INSTRUCTIONS = 'Fixed anonymous default-mode probe.'


def input_mode(*, adopted=False):
    return {'mode': 'default', 'settings': {'model': guest.DIRECT_MODEL,
            'reasoning_effort': 'low', 'developer_instructions':
                INPUT_DEVELOPER_INSTRUCTIONS if adopted else None}}


def input_settings(*, adopted=False):
    # Complete pinned ThreadSettings, independent of observed native values.
    return {'disabledPluginIds': [], 'cwd': '/workspace', 'approvalPolicy': 'never',
        'approvalsReviewer': 'user', 'sandboxPolicy': dict(POLICY), 'activePermissionProfile': None,
        'model': guest.DIRECT_MODEL, 'modelProvider': 'fixture', 'serviceTier': 'default',
        'effort': 'low', 'summary': 'none', 'collaborationMode': input_mode(adopted=adopted),
        'multiAgentMode': 'explicitRequestOnly', 'personality': 'none'}


def input_settings_match(message, thread, *, adopted=False):
    params = message.get('params')
    if (message.get('method') != 'thread/settings/updated' or type(params) is not dict
            or params.get('threadId') != thread
            or params.get('threadSettings') != input_settings(adopted=adopted)):
        raise ValueError('external-input-complete-settings-drift')


def settings_update_params(thread, case=None):
    params = {'threadId': thread, 'cwd': '/workspace', 'approvalPolicy': 'never', 'sandboxPolicy': dict(POLICY)}
    if case in guest.INPUT_CASES:
        params.update(disabledPluginIds=[], approvalsReviewer='user', effort='low',
                      summary='none', serviceTier='default', personality='none')
    return params


def input_call_confirmed(call):
    # Independently fixed host payload. The native mode guard precedes parsing;
    # its denial cannot prove the native argument parser accepted this object.
    expected = {'questions': [{'id': 'fixed_input_choice', 'header': 'Fixture',
        'question': 'Choose the fixed fixture option.', 'options': [
            {'label': 'A (Recommended)', 'description': 'Fixed option A.'},
            {'label': 'B', 'description': 'Fixed option B.'}]}]}
    if (type(call) is not dict or set(call) != {'type', 'namespace', 'name', 'call_id', 'arguments'}
            or {key: call[key] for key in ('type', 'namespace', 'name', 'call_id')} !=
                {'type': 'function_call', 'namespace': 'functions', 'name': 'request_user_input',
                 'call_id': guest.NATIVE_CALL}
            or type(call['arguments']) is not str or len(call['arguments'].encode()) > 1024
            or base.probe.manifest.decode(call['arguments'].encode()) != expected):
        raise ValueError('external-fixed-input-call-drift')


def turn_params(thread, request):
    params = {'threadId': thread,
        'environments': [{'environmentId': 'local', 'cwd': '/workspace', 'runtimeWorkspaceRoots': ['/workspace']}],
        'input': [{'type': 'text', 'text': fixed_prompt(request)}]}
    if request['native_case'] in guest.INPUT_CASES:
        params['collaborationMode'] = input_mode(adopted=True)
    return params


def capture(root, binary):
    sources, binary_ref = base.capture(root, binary)
    fixture = root / 'capture'
    for directory, _, _ in os.walk(fixture):
        pathlib.Path(directory).chmod(0o700)  # Only this new private snapshot.
    for name in guest.FILES:
        raw, ref = helpers._reload_read(ROOT, name, private=False)
        fd = os.open(fixture / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o500)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        sources[name] = ref
    for directory, _, _ in os.walk(fixture, topdown=False):
        pathlib.Path(directory).chmod(0o500)
    check_capture(fixture, sources)
    return sources, binary_ref


def check_capture(fixture, sources):
    if set(sources) != set(FILES):
        raise ValueError('external-source-closure-drift')
    # Bind the complete extended closure, tree and fixed binary directly.
    for name, ref in sources.items():
        if helpers._reload_read(ROOT, name, private=False)[1] != ref:
            raise ValueError('external-host-source-drift')
        raw, actual = helpers._reload_read(fixture, name)
        if actual['sha256'] != ref['sha256'] or stat.S_IMODE(actual['identity'][3]) != 0o500:
            raise ValueError('external-captured-source-drift')
    found = set()
    for directory, dirs, files in os.walk(fixture, followlinks=False):
        if any((pathlib.Path(directory) / name).is_symlink() for name in dirs):
            raise ValueError('external-capture-symlink')
        found.update(str((pathlib.Path(directory) / name).relative_to(fixture)) for name in files)
    if found != set(FILES) | {'codex'}:
        raise ValueError('external-capture-extra')
    fd = os.open(fixture / 'codex', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != base.guest.BINARY_BYTES
                or before.st_uid != os.getuid() or stat.S_IMODE(before.st_mode) != 0o500
                or hashlib.file_digest(stream, 'sha256').hexdigest() != base.guest.BINARY_SHA
                or base.guest.file_identity(before) != base.guest.file_identity(os.fstat(stream.fileno()))
                or base.guest.file_identity(before) != base.guest.file_identity(os.lstat(fixture / 'codex'))):
            raise ValueError('external-binary-drift')


def create_argv(root, name, uid, gid):
    argv = base.create_argv(root, name, uid, gid, writer=True)
    # Fixed new physical layout; no writable control/evidence/auth/socket mount.
    start = argv.index('--workdir=/control')
    return argv[:start] + ['--workdir=/workspace',
        '--mount', 'type=bind,src=' + str(root / 'capture') + ',dst=/fixture,readonly,bind-propagation=rprivate',
        '--mount', 'type=bind,src=' + str(root / 'inputs') + ',dst=/inputs,readonly,bind-propagation=rprivate',
        '--mount', 'type=bind,src=' + str(root / 'workspace') + ',dst=/workspace,bind-propagation=rprivate',
        '--entrypoint=/usr/bin/env', base.IMAGE, *WRAPPER]


def policy(value, root, name, uid, gid, cid, created=None, *, image_config, stopped=False):
    expected = {'/fixture': (str(root / 'capture'), False), '/inputs': (str(root / 'inputs'), False),
                '/workspace': (str(root / 'workspace'), True)}
    try:
        if (len(value['Mounts']) != 3 or {m['Destination'] for m in value['Mounts']} != set(expected)
                or value['Config']['Cmd'] != WRAPPER or value['Config']['WorkingDir'] != '/workspace'):
            raise ValueError('external-physical-layout-drift')
        for mount in value['Mounts']:
            source, rw = expected[mount['Destination']]
            if (mount['Type'] != 'bind' or mount['Source'] != source or mount['RW'] is not rw
                    or mount['Propagation'] != 'rprivate'):
                raise ValueError('external-physical-mount-drift')
        # These three already-checked layout fields are normalized only to
        # reuse the original complete fixed image/host/state checks. Raw engine
        # evidence is never modified and all other fields retain their values.
        view = copy.deepcopy(value)
        view['Config']['Cmd'] = base.WRAPPER_CMD; view['Config']['WorkingDir'] = '/control'
        view['Mounts'] = [{'Type': 'bind', 'Source': str(root / 'capture'), 'Destination': '/fixture',
                           'RW': False, 'Propagation': 'rprivate'},
                          {'Type': 'bind', 'Source': str(root / 'control'), 'Destination': '/control',
                           'RW': True, 'Propagation': 'rprivate'}]
        return base.policy(view, root, name, uid, gid, cid, created, stopped=stopped,
                           image_config=image_config, writer=True)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError('external-policy-incomplete') from error


def settings_match(message, thread, model='gpt-6-sol'):
    if message.get('method') != 'thread/settings/updated':
        return False
    params = message.get('params', {}); value = params.get('threadSettings', {})
    if (params.get('threadId') != thread or {key: value.get(key) for key in
            ('cwd', 'approvalPolicy', 'sandboxPolicy', 'activePermissionProfile', 'model', 'modelProvider')} !=
            {'cwd': '/workspace', 'approvalPolicy': 'never', 'sandboxPolicy': POLICY,
             'activePermissionProfile': None, 'model': model, 'modelProvider': 'fixture'}):
        raise ValueError('external-settings-readback-drift')
    return True


def bootstrap(session, receipt, case=None):
    model = guest.DIRECT_MODEL if case else 'gpt-6-sol'
    session.request('initialize', {'clientInfo': {'name': 'external_bootstrap_only', 'version': '1'},
                                  'capabilities': {'experimentalApi': True}})
    start_params = {'model': model, 'modelProvider': 'fixture',
        'allowProviderModelFallback': False, 'cwd': '/workspace', 'ephemeral': True, 'sandbox': 'read-only',
        'approvalPolicy': 'never', 'environments': []}
    if case in guest.INPUT_CASES:
        start_params['experimentalRawEvents'] = False
    started = session.request('thread/start', start_params)
    if ({k: started.get(k) for k in ('model', 'modelProvider', 'cwd', 'approvalPolicy')} !=
            {'model': model, 'modelProvider': 'fixture', 'cwd': '/workspace', 'approvalPolicy': 'never'}
            or started.get('sandbox', {}).get('type') != 'readOnly'
            or started.get('sandbox', {}).get('networkAccess') is not False
            or started.get('instructionSources') != []):
        raise ValueError('external-readonly-start-drift')
    thread = started.get('thread', {}).get('id')
    if type(thread) is not str or not 0 < len(thread) <= 256:
        raise ValueError('external-thread-identity-drift')
    receipt['thread_start'] = started; receipt['thread_id'] = thread
    session._drain_available(session._deadline())
    if any(row['message'] and row['message'].get('method') == 'thread/settings/updated' for row in session.wire):
        raise ValueError('external-stale-settings-notification')
    result = session.request('thread/settings/update', settings_update_params(thread, case))
    if result != {}:
        raise ValueError('external-settings-ack-drift')
    for _ in range(256):
        note = session.notification()
        if settings_match(note, thread, model):
            receipt['settings_notification'] = note; break
        if note['method'] in ('error', 'turn/started', 'item/started', 'model/rerouted'):
            raise ValueError('external-unexpected-bootstrap-activity')
    else:
        raise ValueError('external-settings-notification-missing')
    session._drain_available(session._deadline())
    sent = [i for i, row in enumerate(session.wire) if row['direction'] == 'out-sent'
            and row['message'].get('method') == 'thread/settings/update']
    notes = [i for i, row in enumerate(session.wire) if row['direction'] == 'in'
             and row['message'].get('method') == 'thread/settings/updated']
    if len(sent) != 1 or len(notes) != 1 or notes[0] <= sent[0]:
        raise ValueError('external-settings-sequence-unconfirmed')
    for row in session.wire:
        message = row.get('message') or {}; method = message.get('method', '')
        if (method.startswith(('turn/', 'item/')) or method in ('error', 'model/rerouted')
                or row['direction'] == 'out-sent' and method not in
                    ('initialize', 'initialized', 'thread/start', 'thread/settings/update')):
            raise ValueError('external-bootstrap-not-only-settings')
    settings_match(session.wire[notes[0]]['message'], thread, model)
    if case in guest.INPUT_CASES:
        input_settings_match(receipt['settings_notification'], thread)
    receipt['settings_sequence'] = {'out_sent_index': sent[0], 'notification_index': notes[0],
                                    'unique_in_observed_wire': True, 'turn_started': False}
    if case in guest.INPUT_CASES:
        del receipt['settings_sequence']['unique_in_observed_wire']
        receipt['settings_sequence']['unique_in_bootstrap_prefix'] = True


def decode_bundle(value):
    if (type(value) is not dict or set(value) != {'encoding', 'raw_bytes', 'raw_sha256', 'compressed_bytes',
            'compressed_sha256', 'data'} or value['encoding'] != 'zlib-utf8-records-base64'
            or type(value['raw_bytes']) is not int or not 0 < value['raw_bytes'] <= guest.BUNDLE_BYTES
            or type(value['compressed_bytes']) is not int or not 0 < value['compressed_bytes'] <= guest.COMPRESSED_BYTES
            or type(value['data']) is not str or len(value['data']) > 4 * ((guest.COMPRESSED_BYTES + 2) // 3)):
        raise ValueError('external-bundle-shape-bound')
    compressed = base64.b64decode(value['data'], validate=True)
    if (len(compressed) != value['compressed_bytes']
            or hashlib.sha256(compressed).hexdigest() != value['compressed_sha256']):
        raise ValueError('external-compressed-integrity')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, guest.BUNDLE_BYTES + 1)
    # No flush or second stream; no allocation beyond the fixed output ceiling.
    if (not decoder.eof or decoder.unconsumed_tail or decoder.unused_data
            or len(raw) != value['raw_bytes'] or len(raw) > guest.BUNDLE_BYTES
            or hashlib.sha256(raw).hexdigest() != value['raw_sha256']):
        raise ValueError('external-bundle-integrity-bound')
    result = helpers._reload_json(raw)
    if type(result) is not dict:
        raise ValueError('external-bundle-object-required')
    if 'records' in result:
        if type(result['records']) is not list or len(result['records']) > 2:
            raise ValueError('external-bundle-record-count')
        total = 0
        for record in result['records']:
            if type(record) is not dict: raise ValueError('external-bundle-record-shape')
            for name, bound in (('request', guest.HTTP_BYTES), ('response', guest.RESPONSE_BYTES)):
                text = record.pop(name + '_text', None)
                if type(text) is not str or name + '_base64' in record or len(text) > bound:
                    raise ValueError('external-bundle-record-text-bound')
                data = text.encode('utf-8')
                if len(data) > bound: raise ValueError('external-bundle-record-utf8-bound')
                record[name + '_base64'] = base64.b64encode(data).decode()
                if name == 'request': total += len(data)
        if total > guest.HTTP_TOTAL_BYTES: raise ValueError('external-bundle-record-total-bound')
    return result


def fixed_prompt(request):
    return 'Fixed anonymous external writer ' + request['run_id'] + ' ' + request['native_case'] + '; no integration requested.'


def writer_observation(value, request):
    state = decode_bundle(value)
    if (type(state) is not dict or set(state) != {'slots', 'total_bytes', 'failed', 'records', 'native_output',
            'native_result', 'declaration', 'stopped', 'catalog_fixture'} or type(state['slots']) is not int or state['slots'] != 2
            or state['failed'] is not False or state['stopped'] is not True
            or type(state['records']) is not list or len(state['records']) != 2
            or type(state['total_bytes']) is not int or not 0 < state['total_bytes'] <= guest.HTTP_TOTAL_BYTES):
        raise ValueError('external-two-request-observation-required')
    total = 0; declaration = None; output = None
    case = request['native_case']; call = guest.native_call(case)
    if case in guest.INPUT_CASES:
        input_call_confirmed(call)
    for stage, record in enumerate(state['records'], 1):
        if (type(record) is not dict or set(record) != {'stage', 'request_base64', 'request_sha256', 'request_bytes',
                'response_base64', 'response_sha256', 'response_bytes', 'response_sent'} or type(record['stage']) is not int
                or record['stage'] != stage or record['response_sent'] is not True):
            raise ValueError('external-provider-record-shape')
        for name, bound in (('request', guest.HTTP_BYTES), ('response', guest.RESPONSE_BYTES)):
            size, encoded = record[name + '_bytes'], record[name + '_base64']
            if type(size) is not int or not 0 < size <= bound or type(encoded) is not str or len(encoded) > 4 * ((bound + 2) // 3):
                raise ValueError('external-provider-record-byte-bound')
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) != size or hashlib.sha256(raw).hexdigest() != record[name + '_sha256']:
                raise ValueError('external-provider-record-integrity')
            if name == 'response':
                if raw != guest.response_bytes(stage, case):
                    raise ValueError('external-fixed-response-drift')
                continue
            total += size
            body = base.probe.boundary.manifest.decode(raw)
            if body.get('model') != guest.DIRECT_MODEL:
                raise ValueError('external-provider-model-drift')
            current = guest.declaration(raw, base.probe.boundary, case)
            if stage == 1:
                if case in guest.INPUT_CASES and any(type(item) is dict and item.get('type') in
                        ('function_call', 'function_call_output', 'custom_tool_call', 'custom_tool_call_output')
                        for item in body.get('input', [])):
                    raise ValueError('external-input-initial-tool-history')
                declaration = current
                texts = [part.get('text') for item in body.get('input', []) if type(item) is dict
                         for part in item.get('content', []) if type(part) is dict and part.get('type') == 'input_text']
                if texts.count(fixed_prompt(request)) != 1:
                    raise ValueError('external-provider-turn-prompt-drift')
            else:
                calls = [item for item in body.get('input', []) if type(item) is dict and item.get('call_id') == guest.NATIVE_CALL
                         and item.get('type') == call['type']]
                if len(calls) != 1 or {k: calls[0].get(k) for k in call} != call:
                    raise ValueError('external-provider-native-call-drift')
                if case in guest.INPUT_CASES:
                    input_call_confirmed({k: calls[0].get(k) for k in call})
                output = base.probe.boundary.output_text(base.probe.boundary.find_output(body, call))
                if case in guest.INPUT_CASES:
                    tool_items = [item for item in body.get('input', []) if type(item) is dict
                                  and item.get('type') in ('function_call', 'function_call_output',
                                                          'custom_tool_call', 'custom_tool_call_output')]
                    if (len(tool_items) != 2 or any(item.get('call_id') != guest.NATIVE_CALL for item in tool_items)
                            or type(base.probe.boundary.find_output(body, call)) is not str):
                        raise ValueError('external-input-carrier-or-other-call-drift')
                if current['advertised_tools'] != declaration['advertised_tools']:
                    raise ValueError('external-provider-declaration-drift')
    result = guest.native_output(output, case, base.guest)
    if total != state['total_bytes'] or state['declaration'] != declaration or state['native_output'] != output or state['native_result'] != result:
        raise ValueError('external-provider-result-drift')
    return state


def catalog_observation(state):
    record = state['catalog_fixture']
    if (type(record) is not dict or set(record) != {'source_kind', 'query_spawn_count',
            'fixture_sha256', 'fixture_bytes', 'fixture_identity'}
            or record['source_kind'] != guest.CATALOG_KIND or type(record['query_spawn_count']) is not int
            or record['query_spawn_count'] != 0):
        raise ValueError('external-fixed-catalog-unconfirmed')
    fixture = guest.catalog_bytes()
    if (type(record['fixture_bytes']) is not int or len(fixture) != record['fixture_bytes']
            or hashlib.sha256(fixture).hexdigest() != record['fixture_sha256']):
        raise ValueError('external-catalog-fixture-drift')
    identity = record['fixture_identity']
    if (type(identity) is not list or len(identity) != 9 or any(type(n) is not int or n < 0 for n in identity)
            or identity[1] == 0 or identity[2:4] != [os.getuid(), os.getgid()]
            or not stat.S_ISREG(identity[4]) or stat.S_IMODE(identity[4]) != 0o600
            or identity[5] != 1 or identity[6] != len(fixture)):
        raise ValueError('external-catalog-file-identity-drift')


def writer_wire(receipt, request, state):
    """Public RPC and provider observations must agree; neither grants authority."""
    sent = []; starts = []; ends = []; completed = []; turn_starts = []; turn_ends = []; deltas = []
    thread, turn = receipt['thread_id'], receipt['turn_id']
    if request['native_case'] in guest.INPUT_CASES:
        return input_wire(receipt, request, state)
    patch_case = request['native_case'] in guest.PATCH_CASES
    if patch_case:
        return patch_wire(receipt, request, state)
    command = json.loads(guest.native_call(request['native_case'])['arguments'])['cmd']
    for index, row in enumerate(receipt['wire']):
        message = row['message'] or {}
        if base.probe.manifest.decode(base64.b64decode(row['raw_base64'], validate=True)) != row['message']:
            raise ValueError('external-writer-raw-wire-drift')
        method = message.get('method', '')
        if row['direction'] == 'out-sent':
            if method == 'turn/start': sent.append(index)
            elif method not in ('initialize', 'initialized', 'thread/start', 'thread/settings/update'):
                raise ValueError('external-writer-unexpected-outbound')
        if row['direction'] != 'in': continue
        if ('id' in message and 'method' in message or method in ('error', 'model/rerouted')
                or 'requestApproval' in method or method == 'item/tool/call'):
            raise ValueError('external-writer-unexpected-request')
        params = message.get('params', {})
        if method == 'thread/settings/updated': settings_match(message, thread, guest.DIRECT_MODEL)
        if method.startswith(('turn/', 'item/')) and params.get('threadId') != thread:
            raise ValueError('external-writer-thread-drift')
        if method in ('turn/started', 'turn/completed'):
            if params.get('turn', {}).get('id') != turn:
                raise ValueError('external-writer-turn-drift')
            (turn_starts if method == 'turn/started' else turn_ends).append(index)
            if method == 'turn/completed' and params['turn'].get('status') != 'completed':
                raise ValueError('external-writer-turn-incomplete')
        elif method.startswith('item/'):
            if params.get('turnId') != turn:
                raise ValueError('external-writer-item-turn-drift')
            item = params.get('item', {})
            if method in ('item/started', 'item/completed') and item.get('type') == 'commandExecution':
                displayed = item.get('command')
                if (item.get('id') != guest.NATIVE_CALL or item.get('cwd') != '/workspace'
                        or type(displayed) is not str or len(displayed.encode()) > 8192
                        or shlex.split(displayed) != ['/usr/bin/sh', '-c', command]):
                    raise ValueError('external-writer-command-drift')
                if method == 'item/started': starts.append(index)
                else:
                    ends.append(index); completed.append(item)
            elif method == 'item/commandExecution/outputDelta':
                delta = params.get('delta')
                if (params.get('itemId') != guest.NATIVE_CALL or type(delta) is not str
                        or sum(len(text.encode()) for _, text in deltas) + len(delta.encode()) > 4096):
                    raise ValueError('external-writer-output-delta-drift')
                deltas.append((index, delta))
            elif method in ('item/started', 'item/completed') and item.get('type') not in ('userMessage', 'agentMessage', 'reasoning'):
                raise ValueError('external-writer-other-tool')
    result = state['native_result']
    settings = [i for i, row in enumerate(receipt['wire']) if row['direction'] == 'in'
                and (row['message'] or {}).get('method') == 'thread/settings/updated']
    if (len(sent) != len(starts) or len(starts) != len(ends) or len(ends) != len(turn_starts)
            or len(turn_starts) != len(turn_ends) or len(sent) != 1
            or settings != [receipt['settings_sequence']['notification_index']]
            or not receipt['settings_sequence']['notification_index'] < sent[0] < turn_starts[0] < starts[0] < ends[0] < turn_ends[0]
            or type(completed[0].get('exitCode')) is not int or completed[0]['exitCode'] != result['exit_code']
            or completed[0].get('status') not in ('completed', 'failed')):
        raise ValueError('external-writer-lifecycle-unconfirmed')
    aggregate = completed[0].get('aggregatedOutput'); streamed = ''.join(text for _, text in deltas)
    if ('aggregatedOutput' not in completed[0] or any(not starts[0] < index < ends[0] for index, _ in deltas)
            or (aggregate is None and streamed != result['body'])
            or (aggregate is not None and (aggregate != result['body'] or deltas and streamed != result['body']))):
        raise ValueError('external-writer-output-unconfirmed')
    expected = {'threadId': thread,
        'environments': [{'environmentId': 'local', 'cwd': '/workspace', 'runtimeWorkspaceRoots': ['/workspace']}],
        'input': [{'type': 'text', 'text': fixed_prompt(request)}]}
    if receipt['wire'][sent[0]]['message'].get('params') != expected:
        raise ValueError('external-writer-turn-request-drift')


def input_wire(receipt, request, state):
    """Exact guard text is in HTTP; these branches emit no native tool item."""
    sent = []; starts = []; ends = []; settings = []
    thread, turn = receipt['thread_id'], receipt['turn_id']
    for index, row in enumerate(receipt['wire']):
        message = row['message'] or {}
        if base.probe.manifest.decode(base64.b64decode(row['raw_base64'], validate=True)) != row['message']:
            raise ValueError('external-input-raw-wire-drift')
        method = message.get('method', '')
        if row['direction'] == 'out-sent':
            if method == 'turn/start': sent.append(index)
            elif method not in ('initialize', 'initialized', 'thread/start', 'thread/settings/update'):
                raise ValueError('external-input-unexpected-outbound')
        if row['direction'] != 'in': continue
        if ('id' in message and 'method' in message or method in ('error', 'model/rerouted')
                or 'requestApproval' in method or method == 'item/tool/call'
                or method.startswith('rawResponse')):
            raise ValueError('external-input-unexpected-request')
        params = message.get('params', {})
        if method == 'thread/settings/updated':
            input_settings_match(message, thread, adopted=bool(settings))
            settings.append(index)
        if method.startswith(('turn/', 'item/')) and params.get('threadId') != thread:
            raise ValueError('external-input-thread-drift')
        if method in ('turn/started', 'turn/completed'):
            if params.get('turn', {}).get('id') != turn:
                raise ValueError('external-input-turn-drift')
            (starts if method == 'turn/started' else ends).append(index)
            if method == 'turn/completed' and (params['turn'].get('status') != 'completed'
                                               or params['turn'].get('error') is not None):
                raise ValueError('external-input-turn-incomplete')
        elif method.startswith('turn/'):
            raise ValueError('external-input-unexpected-turn-event')
        elif method.startswith('item/'):
            if params.get('turnId') != turn:
                raise ValueError('external-input-item-turn-drift')
            if method in ('item/started', 'item/completed'):
                if params.get('item', {}).get('type') not in ('userMessage', 'agentMessage', 'reasoning'):
                    raise ValueError('external-input-native-tool-item')
            elif not method.startswith(('item/agentMessage/', 'item/reasoning/')):
                raise ValueError('external-input-other-tool-event')
    if (not len(sent) == len(starts) == len(ends) == 1 or len(settings) != 2
            or receipt['settings_sequence'].get('unique_in_bootstrap_prefix') is not True
            or 'unique_in_observed_wire' in receipt['settings_sequence']
            or settings[0] != receipt['settings_sequence']['notification_index']
            or not settings[0] < sent[0] < settings[1] < starts[0] < ends[0]
            or receipt['wire'][sent[0]]['message'].get('params') != turn_params(thread, request)
            or state['native_result'] != guest.native_output(state['native_output'], request['native_case'], base.guest)):
        raise ValueError('external-input-control-unconfirmed')
    receipt['input_adoption_notification'] = receipt['wire'][settings[1]]['message']
    receipt['input_adoption_sequence'] = {'bootstrap_notification_index': settings[0],
        'turn_start_out_sent_index': sent[0], 'adopted_notification_index': settings[1],
        'turn_started_index': starts[0], 'turn_completed_index': ends[0],
        'exactly_two_settings_notifications': True,
        'instructions_source': 'fixed-anonymous-literal'}


def patch_changes(case, *, progress=False):
    if case == 'workspace-patch':
        return [{'path': '/workspace/native-patch.txt', 'kind': {'type': 'add'},
                 'diff': guest.PATCH_BYTES.decode()}]
    if case == 'patch-canary-write-failure':
        diff = guest.PATCH_UPDATE_DIFF
        if progress: diff = diff.replace('@@ -1 +1 @@', '@@', 1)
        return [{'path': '/inputs/canary', 'kind': {'type': 'update', 'move_path': None}, 'diff': diff}]
    raise ValueError('fixed-patch-case-required')


def patch_wire(receipt, request, state):
    """FileChange reports planned changes; host bytes establish actual effects."""
    sent = []; starts = []; ends = []; turn_starts = []; turn_ends = []; updates = []
    thread, turn = receipt['thread_id'], receipt['turn_id']; case = request['native_case']
    terminal = 'completed' if case == 'workspace-patch' else 'failed'
    for index, row in enumerate(receipt['wire']):
        message = row['message'] or {}
        if base.probe.manifest.decode(base64.b64decode(row['raw_base64'], validate=True)) != row['message']:
            raise ValueError('external-patch-raw-wire-drift')
        method = message.get('method', '')
        if row['direction'] == 'out-sent':
            if method == 'turn/start': sent.append(index)
            elif method not in ('initialize', 'initialized', 'thread/start', 'thread/settings/update'):
                raise ValueError('external-patch-unexpected-outbound')
        if row['direction'] != 'in': continue
        if ('id' in message and 'method' in message or method in ('error', 'model/rerouted')
                or 'requestApproval' in method or method == 'item/tool/call'):
            raise ValueError('external-patch-unexpected-request')
        params = message.get('params', {})
        if method == 'thread/settings/updated': settings_match(message, thread, guest.DIRECT_MODEL)
        if method.startswith(('turn/', 'item/')) and params.get('threadId') != thread:
            raise ValueError('external-patch-thread-drift')
        if method in ('turn/started', 'turn/completed'):
            if params.get('turn', {}).get('id') != turn:
                raise ValueError('external-patch-turn-drift')
            (turn_starts if method == 'turn/started' else turn_ends).append(index)
            if method == 'turn/completed' and params['turn'].get('status') != 'completed':
                raise ValueError('external-patch-turn-incomplete')
        elif method == 'turn/diff/updated':
            # Diff text is a bounded original observation, not adoption authority.
            if (params.get('turnId') != turn or type(params.get('diff')) is not str
                    or len(params['diff'].encode()) > 8192):
                raise ValueError('external-patch-turn-diff-drift')
        elif method.startswith('turn/'):
            raise ValueError('external-patch-unexpected-turn-event')
        elif method.startswith('item/'):
            if params.get('turnId') != turn:
                raise ValueError('external-patch-item-turn-drift')
            item = params.get('item', {})
            if method in ('item/started', 'item/completed') and item.get('type') == 'fileChange':
                if (set(item) != {'type', 'id', 'changes', 'status'} or item['id'] != guest.NATIVE_CALL
                        or item['changes'] != patch_changes(case)
                        or item['status'] != ('inProgress' if method == 'item/started' else terminal)):
                    raise ValueError('external-patch-file-change-drift')
                (starts if method == 'item/started' else ends).append(index)
            elif method == 'item/fileChange/patchUpdated':
                if params.get('itemId') != guest.NATIVE_CALL or params.get('changes') != patch_changes(case, progress=True):
                    raise ValueError('external-patch-progress-drift')
                updates.append(index)
            elif method in ('item/started', 'item/completed') and item.get('type') in ('userMessage', 'agentMessage', 'reasoning'):
                continue
            elif not method.startswith(('item/agentMessage/', 'item/reasoning/')):
                # Deprecated fileChange outputDelta is not emitted at this pin.
                raise ValueError('external-patch-other-tool-or-event')
    settings = [i for i, row in enumerate(receipt['wire']) if row['direction'] == 'in'
                and (row['message'] or {}).get('method') == 'thread/settings/updated']
    if (not len(sent) == len(starts) == len(ends) == len(turn_starts) == len(turn_ends) == 1
            or settings != [receipt['settings_sequence']['notification_index']]
            or not settings[0] < sent[0] < turn_starts[0] < starts[0] < ends[0] < turn_ends[0]
            or len(updates) > 4 or any(not turn_starts[0] < i < ends[0] for i in updates)
            or state['native_result']['exit_code'] != (0 if terminal == 'completed' else 1)
            or state['native_result']['os_refusal_proven'] is not False):
        raise ValueError('external-patch-lifecycle-unconfirmed')
    expected = {'threadId': thread,
        'environments': [{'environmentId': 'local', 'cwd': '/workspace', 'runtimeWorkspaceRoots': ['/workspace']}],
        'input': [{'type': 'text', 'text': fixed_prompt(request)}]}
    if receipt['wire'][sent[0]]['message'].get('params') != expected:
        raise ValueError('external-patch-turn-request-drift')


def writer_turn(session, receipt, request):
    result = session.request('turn/start', turn_params(receipt['thread_id'], request))
    turn = result.get('turn', {}).get('id')
    if type(turn) is not str or not 0 < len(turn) <= 256:
        raise ValueError('external-writer-turn-identity')
    receipt['turn_id'] = turn
    deadline = time.monotonic() + 30
    for _ in range(256):
        if time.monotonic() >= deadline: break
        note = session.notification()
        if note['method'] == 'turn/completed': break
        if note['method'] in ('error', 'model/rerouted') or 'requestApproval' in note['method']:
            raise ValueError('external-writer-unexpected-activity')
    else:
        raise ValueError('external-writer-notification-bound')
    session._drain_available(session._deadline())


def check_workspace(root, case):
    workspace = root / 'workspace'
    if not guest.workspace_expected(workspace, case, lambda p, n: helpers._reload_read(workspace, p.name, n)[0]):
        raise ValueError('external-workspace-postimage-drift')
    if case in ('workspace-write', 'workspace-patch'):
        relative = 'native-write.txt' if case == 'workspace-write' else 'native-patch.txt'
        _, ref = helpers._reload_read(workspace, relative, 128)
        if stat.S_IMODE(ref['identity'][3]) != 0o600:
            raise ValueError('external-workspace-mode-drift')
        return ref
    return {'workspace_empty': True}


def guest_frame(snapshot, request):
    raw = snapshot['raw']
    if (not snapshot['eof'] or not snapshot['reader_finished'] or snapshot['overflow']
            or snapshot['truncated'] or snapshot['reader_error'] or len(raw) >
                (guest.WRITER_FRAME_BYTES if request.get('native_case') else guest.FRAME_BYTES)
            or not raw.startswith(guest.PREFIX) or not raw.endswith(b'\n') or b'\n' in raw[:-1]):
        raise ValueError('external-final-frame-incomplete')
    value = helpers._reload_json(raw[len(guest.PREFIX):-1])
    if (type(value.get('schema_version')) is not int or value['schema_version'] != 1
            or value.get('scope') != 'anonymous-external-bootstrap-only'
            or value.get('run_id') != request['run_id'] or value.get('qualified') is not False
            or value.get('production_qualified') is not False or value.get('passed') is not True
            or value.get('cli_spawn_count') != 1 or type(value.get('cli_spawn_count')) is not int
            or value.get('cli_wait') != 'observed' or type(value.get('cli_exit_code')) is not int
            or value['cli_exit_code'] != 0 or type(value.get('cli_pid')) is not int or value['cli_pid'] <= 1
            or (value.get('workspace_expected') is not True if request.get('native_case') else value.get('workspace_empty') is not True)
            or value.get('canary_preserved') is not True):
        raise ValueError('external-guest-observation-unconfirmed')
    case = request.get('native_case'); port = value.get('provider_port') if case else 1
    if type(port) is not int or not 1 <= port <= 65535 or value.get('cli_argv') != guest.argv(base.probe.boundary, base.guest, port=port, native=bool(case), case=case):
        raise ValueError('external-guest-command-unconfirmed')
    if case and (value.get('native_case') != case or value.get('catalog_preserved') is not True):
        raise ValueError('external-guest-case-drift')
    stderr = value.get('cli_stderr', {}); child_raw = base64.b64decode(stderr.get('raw_base64', ''), validate=True)
    if (not base.guest.stderr_complete(stderr) or len(child_raw) != stderr['captured_bytes']
            or hashlib.sha256(child_raw).hexdigest() != stderr['captured_prefix_sha256']):
        raise ValueError('external-child-stderr-incomplete')
    return value


def run(args):
    case = getattr(args, 'native_workspace_case', None)
    if case is not None and case not in guest.CASES:
        raise ValueError('fixed-external-case-required')
    parent = args.evidence_root.resolve(strict=True)
    if any((d / '.git').exists() for d in (parent, *parent.parents)):
        raise ValueError('external-evidence-outside-git-required')
    fd = helpers.trust._directory(parent)
    try:
        if os.fstat(fd).st_mode & 0o077 or min(os.getuid(), os.getgid()) <= 0:
            raise ValueError('external-private-nonroot-host-required')
    finally:
        os.close(fd)
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-external-bootstrap-', dir=parent)); root.chmod(0o700)
    for name in ('inputs', 'workspace'):
        (root / name).mkdir(mode=0o700)
    receipt = {'schema_version': 1, 'execution_outcome': 'unknown', 'qualified': False,
        'native_qualified': False, 'startup_isolation_qualified': False, 'isolation_qualified': False,
        'runtime_qualified': False, 'adapter_qualified': False, 'production_qualified': False,
        'n1_complete': False, 'n2_complete': False, 'n3_complete': False, 'n4_complete': False}
    engine = session = None; started = False
    try:
        run_id = uuid.uuid4().hex; name = 'external-bootstrap-' + run_id
        sources, binary = capture(root, args.binary_path)
        request = {'schema_version': 1, 'run_id': run_id, 'uid': os.getuid(), 'gid': os.getgid(),
                   'sources': {k: v['sha256'] for k, v in sources.items()}}
        if case: request['native_case'] = case
        ref = helpers._reload_save(root / 'inputs', 'request.json', request)
        canary = root / 'inputs/canary'; canary.write_bytes(base.guest.CANARY_BYTES); canary.chmod(0o600)
        _, canary_ref = helpers._reload_read(root / 'inputs', 'canary', 128)
        receipt.update(run_id=run_id, source_capture=sources, binary=binary, canary_initial_ref=canary_ref)
        socket = base.socket_snapshot(args.endpoint); create = create_argv(root, name, os.getuid(), os.getgid())
        engine = base.Engine(args.endpoint, root, create)
        daemon = engine.identity(); image = engine.image(base.IMAGE)
        config = base.image_policy(image, writer=True); image_ref = helpers._reload_save(root, 'raw-image.json', image)
        digest = helpers.packets.digest(helpers.packets.canonical(config))
        receipt['engine_binding'] = {'endpoint': args.endpoint, 'socket': socket, 'daemon': daemon,
            'executable': engine.executable, 'identity': list(engine.executable_identity)}
        helpers._reload_save(root, 'create-intent.json', {'argv': create, 'request_ref': ref,
            'image_ref': image_ref, 'engine_binding': receipt['engine_binding']})
        reply = engine.command(*create).decode('ascii'); cid, cid_ref = base.cidfile(root)
        engine.allowed_cid = cid
        if reply.strip() != cid or engine.failures:
            raise ValueError('external-create-unknown')
        observed = engine.inspect(cid)
        created = policy(observed, root, name, os.getuid(), os.getgid(), cid, image_config=config)
        receipt.update(cid=cid, created=created, prestart_policy=observed)
        helpers._reload_save(root, 'prestart-policy.json', observed)
        check_capture(root / 'capture', sources); helpers._reload_ref(root / 'inputs', ref)
        helpers._reload_ref(root / 'inputs', canary_ref); helpers._reload_ref(root, image_ref)
        if (base.socket_snapshot(args.endpoint) != socket or engine.identity() != daemon
                or engine._executable_snapshot() != engine.executable_identity
                or base.cidfile(root)[1] != cid_ref or engine.failures
                or helpers.packets.digest(helpers.packets.canonical(base.image_policy(engine.image(base.IMAGE), writer=True))) != digest):
            raise ValueError('external-prestart-binding-drift')
        policy(engine.inspect(cid), root, name, os.getuid(), os.getgid(), cid, created, image_config=config)
        if engine.failures or base.cidfile(root)[1] != cid_ref:
            raise ValueError('external-start-binding-unknown')
        command = [engine.executable, '--host', args.endpoint, 'container', 'start', '--attach', '--interactive', cid]
        helpers._reload_save(root, 'start-intent.json', {'cid': cid, 'created': created, 'argv': command})
        started = True
        session_class = InputObservationSession if case in guest.INPUT_CASES else base.probe.AdmissionSession
        session = session_class(command, cwd=str(root), env=dict(engine.environment),
            limits=base.probe.transport.Limits(timeout=10, close_timeout=5), admission_receipt={},
            allow_thread_settings_update=True, capture_stderr=True)
        try:
            bootstrap(session, receipt, case)
            if case: writer_turn(session, receipt, request)
        finally:
            receipt['client_close'] = session.close(); receipt['wire'] = session.wire
            stderr = session.stderr_snapshot(); saved = dict(stderr); saved['raw_base64'] = base64.b64encode(saved.pop('raw')).decode()
            receipt['docker_stderr'] = saved
        observed = engine.inspect(cid); receipt['container_exit'] = observed
        policy(observed, root, name, os.getuid(), os.getgid(), cid, created, image_config=config, stopped=True)
        if receipt['client_close'] != {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}:
            raise ValueError('external-docker-client-unknown')
        receipt['guest_observation'] = guest_frame(stderr, request)
        if case:
            state = writer_observation(receipt['guest_observation'].get('provider_bundle'), request)
            catalog_observation(state)
            writer_wire(receipt, request, state)
            receipt['native_result'] = state['native_result']; receipt['native_case'] = case
        check_capture(root / 'capture', sources)
        helpers._reload_ref(root / 'inputs', ref); helpers._reload_ref(root / 'inputs', canary_ref)
        receipt['workspace_postimage'] = check_workspace(root, case)
        helpers._reload_ref(root, image_ref)
        if (base.socket_snapshot(args.endpoint) != socket or engine.identity() != daemon or engine.failures
                or engine._executable_snapshot() != engine.executable_identity or base.cidfile(root)[1] != cid_ref
                or helpers.packets.digest(helpers.packets.canonical(base.image_policy(engine.image(base.IMAGE), writer=True))) != digest):
            raise ValueError('external-final-engine-drift')
        receipt['execution_outcome'] = ('measured-synthetic-external-native-' + case + '-passed' if case else
                                         'measured-synthetic-external-bootstrap-passed')
    except Exception as error:
        receipt['failure_class'] = type(error).__name__
        if engine is not None:
            try:
                cid, ref = base.cidfile(root); engine.allowed_cid = cid
                receipt['failure_original_cid'] = engine.inspect(cid)
            except Exception as observed_error:
                receipt['failure_readback_class'] = type(observed_error).__name__
        raise
    finally:
        receipt['start_attempted'] = started; receipt['transport_failures'] = getattr(engine, 'failures', [])
        helpers._reload_save(root, 'external-bootstrap-evidence.json', receipt)
        print(json.dumps({'evidence': str(root / 'external-bootstrap-evidence.json'),
                         'execution_outcome': receipt['execution_outcome'], 'production_qualified': False}))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external-bootstrap-container-fixture', action='store_true', required=True)
    parser.add_argument('--binary-path', type=pathlib.Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--native-workspace-case', choices=guest.CASES)
    args = parser.parse_args()
    if not args.external_bootstrap_container_fixture:
        parser.error('explicit bounded fixture opt-in required')
    return run(args)


if __name__ == '__main__':
    main()
