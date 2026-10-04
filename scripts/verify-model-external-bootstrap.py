#!/usr/bin/env python3
"""Explicit anonymous external-OS bootstrap probe; no turns, auth or qualification."""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import model_external_bootstrap_fixture as guest

base = guest.load('external_bootstrap_fixed_host', ROOT / 'scripts/verify-model-app-server-container.py')
helpers = base.helpers
FILES = base.FILES + guest.FILES
WRAPPER = ['-i', 'PATH=' + guest.ENV['PATH'], 'HOME=' + guest.ENV['HOME'], 'LANG=' + guest.ENV['LANG'],
           '/usr/local/bin/python3', '-I', '-S', '-B', '/fixture/scripts/model_external_bootstrap_fixture.py']
POLICY = {'type': 'externalSandbox', 'networkAccess': 'restricted'}


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


def settings_match(message, thread):
    if message.get('method') != 'thread/settings/updated':
        return False
    params = message.get('params', {}); value = params.get('threadSettings', {})
    if (params.get('threadId') != thread or {key: value.get(key) for key in
            ('cwd', 'approvalPolicy', 'sandboxPolicy', 'activePermissionProfile', 'model', 'modelProvider')} !=
            {'cwd': '/workspace', 'approvalPolicy': 'never', 'sandboxPolicy': POLICY,
             'activePermissionProfile': None, 'model': 'gpt-6-sol', 'modelProvider': 'fixture'}):
        raise ValueError('external-settings-readback-drift')
    return True


def bootstrap(session, receipt):
    session.request('initialize', {'clientInfo': {'name': 'external_bootstrap_only', 'version': '1'},
                                  'capabilities': {'experimentalApi': True}})
    started = session.request('thread/start', {'model': 'gpt-6-sol', 'modelProvider': 'fixture',
        'allowProviderModelFallback': False, 'cwd': '/workspace', 'ephemeral': True, 'sandbox': 'read-only',
        'approvalPolicy': 'never', 'environments': []})
    if ({k: started.get(k) for k in ('model', 'modelProvider', 'cwd', 'approvalPolicy')} !=
            {'model': 'gpt-6-sol', 'modelProvider': 'fixture', 'cwd': '/workspace', 'approvalPolicy': 'never'}
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
    result = session.request('thread/settings/update', {'threadId': thread,
        'cwd': '/workspace', 'approvalPolicy': 'never', 'sandboxPolicy': POLICY})
    if result != {}:
        raise ValueError('external-settings-ack-drift')
    for _ in range(256):
        note = session.notification()
        if settings_match(note, thread):
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
    settings_match(session.wire[notes[0]]['message'], thread)
    receipt['settings_sequence'] = {'out_sent_index': sent[0], 'notification_index': notes[0],
                                    'unique_in_observed_wire': True, 'turn_started': False}


def guest_frame(snapshot, request):
    raw = snapshot['raw']
    if (not snapshot['eof'] or not snapshot['reader_finished'] or snapshot['overflow']
            or snapshot['truncated'] or snapshot['reader_error'] or len(raw) > guest.FRAME_BYTES
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
            or value.get('workspace_empty') is not True or value.get('canary_preserved') is not True
            or value.get('cli_argv') != guest.argv(base.probe.boundary, base.guest)):
        raise ValueError('external-guest-observation-unconfirmed')
    stderr = value.get('cli_stderr', {}); child_raw = base64.b64decode(stderr.get('raw_base64', ''), validate=True)
    if (not base.guest.stderr_complete(stderr) or len(child_raw) != stderr['captured_bytes']
            or hashlib.sha256(child_raw).hexdigest() != stderr['captured_prefix_sha256']):
        raise ValueError('external-child-stderr-incomplete')
    return value


def run(args):
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
        ref = helpers._reload_save(root / 'inputs', 'request.json', request)
        canary = root / 'inputs/canary'; canary.write_bytes(base.guest.CANARY_BYTES); canary.chmod(0o600)
        _, canary_ref = helpers._reload_read(root / 'inputs', 'canary', 128)
        receipt.update(run_id=run_id, source_capture=sources, binary=binary)
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
        session = base.probe.AdmissionSession(command, cwd=str(root), env=dict(engine.environment),
            limits=base.probe.transport.Limits(timeout=10, close_timeout=5), admission_receipt={},
            allow_thread_settings_update=True, capture_stderr=True)
        try:
            bootstrap(session, receipt)
        finally:
            receipt['client_close'] = session.close(); receipt['wire'] = session.wire
            stderr = session.stderr_snapshot(); saved = dict(stderr); saved['raw_base64'] = base64.b64encode(saved.pop('raw')).decode()
            receipt['docker_stderr'] = saved
        observed = engine.inspect(cid); receipt['container_exit'] = observed
        policy(observed, root, name, os.getuid(), os.getgid(), cid, created, image_config=config, stopped=True)
        if receipt['client_close'] != {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}:
            raise ValueError('external-docker-client-unknown')
        receipt['guest_observation'] = guest_frame(stderr, request)
        check_capture(root / 'capture', sources)
        helpers._reload_ref(root / 'inputs', ref); helpers._reload_ref(root / 'inputs', canary_ref)
        if list((root / 'workspace').iterdir()):
            raise ValueError('external-unexpected-workspace-write')
        helpers._reload_ref(root, image_ref)
        if (base.socket_snapshot(args.endpoint) != socket or engine.identity() != daemon or engine.failures
                or engine._executable_snapshot() != engine.executable_identity or base.cidfile(root)[1] != cid_ref
                or helpers.packets.digest(helpers.packets.canonical(base.image_policy(engine.image(base.IMAGE), writer=True))) != digest):
            raise ValueError('external-final-engine-drift')
        receipt['execution_outcome'] = 'measured-synthetic-external-bootstrap-passed'
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
    args = parser.parse_args()
    if not args.external_bootstrap_container_fixture:
        parser.error('explicit bounded fixture opt-in required')
    return run(args)


if __name__ == '__main__':
    main()
