#!/usr/bin/env python3
"""Explicit fixed prestart anonymous app-server container fixture; no qualification."""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
import time
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import model_app_server_container_fixture as guest


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


# These are fixed source references, not CLI loaders or callable dispatch.
helpers = _load('fixed_container_host_helpers', 'scripts/verify-model-packet-integrator.py')
probe = _load('fixed_container_admission_probe', 'scripts/verify-model-app-server.py')
IMAGE = 'sha256:3c3afc67f71a5eef90b76ff0cdd68eea7289db310df08e224af4a8cc43630633'
FILES = helpers._ADMISSION_FILES + ('scripts/verify-model-app-server-container.py',
                                   'scripts/model_app_server_container_fixture.py')
WRAPPER_CMD = ['-i', 'PATH=/usr/local/bin:/usr/bin:/bin', 'HOME=/control/home', 'LANG=C.UTF-8',
               '/usr/local/bin/python3', '-I', '-S', '-B', '/fixture/scripts/model_app_server_container_fixture.py']


class FixtureError(ValueError):
    pass


def snapshot(path, *, socket=False):
    value = os.stat(path, follow_symlinks=False)
    if (not (stat.S_ISSOCK(value.st_mode) if socket else stat.S_ISREG(value.st_mode))
            or value.st_uid not in (0, os.getuid())):
        raise FixtureError('fixture-identity-untrusted')
    return helpers._reload_identity(value)


def socket_snapshot(endpoint):
    if not endpoint.startswith('unix:///') or '..' in pathlib.PurePosixPath(endpoint[7:]).parts:
        raise FixtureError('fixed-local-unix-endpoint-required')
    original = pathlib.Path(endpoint[7:])
    resolved = original.resolve(strict=True)
    return {'original': helpers._reload_identity(os.lstat(original)), 'path': str(resolved),
            'identity': snapshot(resolved, socket=True)}


def copy_binary(original, target, *, _bwrap=False):
    expected_bytes = guest.BWRAP_BYTES if _bwrap else guest.BINARY_BYTES
    expected_sha = guest.BWRAP_SHA if _bwrap else guest.BINARY_SHA
    fd = os.open(original, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in (0, os.getuid()) or before.st_mode & 0o022
                or before.st_size != expected_bytes or before.st_nlink != 1):
            raise FixtureError('fixed-linux-binary-required')
        out = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o500)
        digest = hashlib.sha256(); count = 0
        with os.fdopen(out, 'wb') as stream:
            while count <= expected_bytes:
                raw = os.read(fd, min(1048576, expected_bytes + 1 - count))
                if not raw:
                    break
                stream.write(raw); digest.update(raw); count += len(raw)
            stream.flush(); os.fsync(stream.fileno())
        if (count != expected_bytes or digest.hexdigest() != expected_sha
                or helpers._reload_identity(os.fstat(fd)) != helpers._reload_identity(before)
                or snapshot(original) != helpers._reload_identity(before)):
            raise FixtureError('fixed-linux-binary-fingerprint-drift')
        return {'sha256': digest.hexdigest(), 'original': helpers._reload_identity(before), 'bytes': count}
    finally:
        os.close(fd)


def capture(root, binary, bwrap=None):
    fixture = root / 'capture'; fixture.mkdir(mode=0o700)
    sources = {}; allowed = {pathlib.PurePosixPath(name).stem for name in FILES} | set(sys.stdlib_module_names) | {'model_packet_lifecycle'}
    for name in FILES:
        raw, reference = helpers._reload_read(ROOT, name, private=False)
        for node in ast.walk(ast.parse(raw)):
            names = ([item.name for item in node.names] if isinstance(node, ast.Import)
                     else [node.module or ''] if isinstance(node, ast.ImportFrom) else [])
            if any(item.split('.')[0] not in allowed for item in names):
                raise FixtureError('fixture-extra-source-dependency')
        path = fixture / name; path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o500)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        module = sys.modules.get(pathlib.PurePosixPath(name).stem)
        if module is not None and pathlib.Path(module.__file__).resolve() != ROOT / name:
            raise FixtureError('fixture-loaded-module-origin-drift')
        sources[name] = reference
    binary_ref = copy_binary(binary, fixture / 'codex')
    if bwrap is not None:
        (fixture / 'codex-resources').mkdir(mode=0o700)
        binary_ref['bwrap'] = copy_binary(bwrap, fixture / guest.BWRAP_RELATIVE, _bwrap=True)
    for directory, _, _ in os.walk(fixture, topdown=False):
        pathlib.Path(directory).chmod(0o500)
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    check_capture(fixture, sources, bwrap=bwrap is not None)
    return sources, binary_ref


def check_capture(fixture, sources, *, bwrap=False):
    if set(sources) != set(FILES):
        raise FixtureError('fixture-source-closure-missing')
    for name, reference in sources.items():
        if helpers._reload_read(ROOT, name, private=False)[1] != reference:
            raise FixtureError('fixture-host-source-drift')
        raw, actual = helpers._reload_read(fixture, name)
        if actual['sha256'] != reference['sha256'] or actual['identity'][3] & 0o777 != 0o500:
            raise FixtureError('fixture-captured-source-drift')
    expected = set(FILES) | {'codex'}
    if bwrap:
        expected.add(guest.BWRAP_RELATIVE)
    found = set()
    for directory, dirs, files in os.walk(fixture, followlinks=False):
        if any((pathlib.Path(directory) / name).is_symlink() for name in dirs):
            raise FixtureError('fixture-capture-symlink')
        found.update(str((pathlib.Path(directory) / name).relative_to(fixture)) for name in files)
    if found != expected:
        raise FixtureError('fixture-source-closure-extra')
    fd = os.open(fixture / 'codex', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if before.st_size != guest.BINARY_BYTES or stat.S_IMODE(before.st_mode) != 0o500 or before.st_uid != os.getuid():
            raise FixtureError('fixture-copy-binary-drift')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != guest.BINARY_SHA or guest.file_identity(os.fstat(fd)) != guest.file_identity(before) or guest.file_identity(os.lstat(fixture / 'codex')) != guest.file_identity(before):
            raise FixtureError('fixture-copy-binary-drift')
    finally:
        os.close(fd)
    if bwrap:
        raw, reference = helpers._reload_read(fixture, guest.BWRAP_RELATIVE, guest.BWRAP_BYTES)
        if (len(raw) != guest.BWRAP_BYTES or reference['sha256'] != guest.BWRAP_SHA
                or stat.S_IMODE(reference['identity'][3]) != 0o500):
            raise FixtureError('fixture-copy-bwrap-drift')


def image_policy(image, *, writer=False):
    config = image.get('Config', {})
    environment, labels = config.get('Env'), config.get('Labels')
    if (type(environment) is not list or len(environment) > 32
            or any(type(item) is not str or '=' not in item or len(item) > 4096 for item in environment)
            or len({item.split('=', 1)[0] for item in environment}) != len(environment)
            or type(labels) is not dict or len(labels) > 32
            or any(type(key) is not str or type(value) is not str or len(key) > 256 or len(value) > 4096
                   for key, value in labels.items()) or 'codex.fixture.run' in labels):
        raise FixtureError('fixed-image-metadata-shape-invalid')
    if (image.get('Id') != IMAGE or image.get('Os') != 'linux' or image.get('Architecture') != 'arm64'
            or config.get('Entrypoint') is not None or config.get('Volumes') is not None
            or config.get('OnBuild') not in (None, []) or config.get('Healthcheck') not in (None, {})):
        raise FixtureError('fixed-existing-image-policy-drift')
    compared = helpers._reload_json(helpers.packets.canonical(config))
    if writer:
        # Only fixed writer selection enables this projection, never a drift
        # failure. Raw image/Config references and every other field remain.
        inert = {**dict.fromkeys(('AttachStderr', 'AttachStdin', 'AttachStdout', 'OpenStdin', 'StdinOnce', 'Tty'), False),
                 **dict.fromkeys(('Domainname', 'Hostname', 'Image', 'User'), ''),
                 **dict.fromkeys(('Entrypoint', 'OnBuild', 'Volumes'), None)}
        for key, empty in inert.items():
            if key in compared and type(compared[key]) is type(empty) and compared[key] == empty:
                compared.pop(key)
    return compared


def tmpfs_options(uid, gid):
    if type(uid) is not int or type(gid) is not int or uid <= 0 or gid <= 0:
        raise FixtureError('fixed-nonroot-tmpfs-owner-required')
    return 'rw,nosuid,nodev,noexec,size=16777216,mode=0700,uid=' + str(uid) + ',gid=' + str(gid)


def create_argv(root, name, uid, gid, *, writer=False):
    return ['container', 'create', '--pull=never', '--cidfile', str(root / 'cidfile'), '--name', name,
            '--label', 'codex.fixture.run=' + name, '--log-driver=none', '--restart=no', '--network=none', '--read-only',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--user', str(uid) + ':' + str(gid),
            '--pids-limit=64', '--memory=512m', '--memory-swap=512m', '--cpus=1', '--ipc=private', '--cgroupns=private',
            '--no-healthcheck', '--interactive', '--attach=stdin', '--attach=stdout', '--attach=stderr',
            *(['--tmpfs', '/tmp:' + tmpfs_options(uid, gid)] if writer else []),
            '--workdir=/control', '--mount', 'type=bind,src=' + str(root / 'capture') + ',dst=/fixture,readonly,bind-propagation=rprivate',
            '--mount', 'type=bind,src=' + str(root / 'control') + ',dst=/control,bind-propagation=rprivate',
            '--entrypoint=/usr/bin/env', IMAGE, *WRAPPER_CMD]


def policy(value, root, name, uid, gid, cid, created=None, *, stopped=False, image_config, writer=False):
    try:
        config, host, state = value['Config'], value['HostConfig'], value['State']
        expected_mounts = {'/fixture': (str(root / 'capture'), False), '/control': (str(root / 'control'), True)}
        mounts = value['Mounts']
        if len(mounts) != 2 or {mount['Destination'] for mount in mounts} != set(expected_mounts):
            raise FixtureError('fixture-mount-drift')
        for mount in mounts:
            source, rw = expected_mounts[mount['Destination']]
            if (mount['Type'] != 'bind' or mount['Source'] != source or mount['RW'] is not rw or mount['Propagation'] != 'rprivate'):
                raise FixtureError('fixture-mount-drift')
        if (value['Id'] != cid or not re.fullmatch(r'[a-f0-9]{64}', cid) or type(value['Created']) is not str
                or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,9})?Z', value['Created'])
                or created is not None and value['Created'] != created or value['Name'] != '/' + name
                or value['Image'] != IMAGE or config['Image'] != IMAGE
                or config['Entrypoint'] != ['/usr/bin/env'] or config['Cmd'] != WRAPPER_CMD
                or config['Env'] != image_config['Env'] or config['Labels'] != {**image_config['Labels'], 'codex.fixture.run': name}
                or config['User'] != str(uid) + ':' + str(gid) or uid <= 0 or gid <= 0
                or config['WorkingDir'] != '/control' or config['Healthcheck'] != {'Test': ['NONE']}
                or any(config[key] is not True for key in ('OpenStdin', 'StdinOnce', 'AttachStdin', 'AttachStdout', 'AttachStderr'))
                or config['Tty'] is not False or config.get('Volumes') not in (None, {})
                or host['NetworkMode'] != 'none' or host['ReadonlyRootfs'] is not True or host['Privileged'] is not False
                or host['CapDrop'] != ['ALL'] or host['CapAdd'] not in (None, [])
                or host['SecurityOpt'] != ['no-new-privileges'] or host['PidsLimit'] != 64
                or host['Memory'] != 536870912 or host['MemorySwap'] != 536870912 or host['NanoCpus'] != 1000000000
                or host['CpuPeriod'] != 0 or host['CpuQuota'] != 0
                or (host.get('Tmpfs') != {'/tmp': tmpfs_options(uid, gid)} if writer else host.get('Tmpfs') not in (None, {}))
                or host['LogConfig'] != {'Type': 'none', 'Config': {}}
                or host['RestartPolicy'] != {'Name': 'no', 'MaximumRetryCount': 0} or host['AutoRemove'] is not False
                or host['PidMode'] != '' or host['IpcMode'] != 'private' or host['CgroupnsMode'] != 'private'
                or host['UTSMode'] != '' or host['UsernsMode'] != '' or host['PublishAllPorts'] is not False
                or any(host.get(key) not in (None, []) for key in ('Devices', 'DeviceRequests', 'DeviceCgroupRules', 'GroupAdd',
                     'ExtraHosts', 'Binds', 'Links', 'VolumesFrom')) or host.get('PortBindings') not in (None, {})
                or value['NetworkSettings'].get('Ports') not in (None, {}) or config.get('ExposedPorts') not in (None, {})
                or value['RestartCount'] != 0 or type(value['RestartCount']) is not int
                or state['Running'] is not False or state['Pid'] != 0 or type(state['Pid']) is not int
                or state.get('Paused') is not False or state.get('Restarting') is not False
                or state.get('Dead') is not False or state.get('OOMKilled') is not False or state.get('Error') != ''
                or state['Status'] != ('exited' if stopped else 'created')
                or type(state['ExitCode']) is not int or state['ExitCode'] != 0):
            raise FixtureError('fixture-full-policy-or-state-drift')
        return value['Created']
    except (KeyError, TypeError, IndexError) as error:
        raise FixtureError('fixture-policy-incomplete') from error


class Engine(helpers._ReloadDocker):
    def __init__(self, endpoint, root, create):
        super().__init__(endpoint, root, 'prestart-engine', image=IMAGE)
        self.fixed_create = tuple(create); self.create_used = False; self.allowed_cid = None

    def _allowed(self, argv, input_bytes):
        exact = {('info', '--format', '{{json .ID}}'), ('image', 'inspect', IMAGE)}
        if self.allowed_cid is not None:
            exact.add(('container', 'inspect', self.allowed_cid))
        if input_bytes is not None:
            raise FixtureError('fixture-engine-stdin-denied')
        if tuple(argv) == self.fixed_create and not self.create_used:
            self.create_used = True
            return
        if tuple(argv) not in exact:
            raise FixtureError('fixture-engine-command-denied')


def cidfile(root):
    raw, reference = helpers._reload_read(root, 'cidfile', 128, private=False)
    cid = raw.strip().decode('ascii')
    if not re.fullmatch(r'[a-f0-9]{64}', cid):
        raise FixtureError('fixture-cidfile-invalid')
    return cid, reference


def native_environments(case):
    if case is None:
        return []
    if case not in guest.WRITER_CASES:
        raise FixtureError('fixed-native-writer-case-required')
    return [{'environmentId': 'local', 'cwd': '/control/workspace', 'runtimeWorkspaceRoots': ['/control/workspace']}]


def native_turn(session, receipt, case=None):
    environments = native_environments(case)
    permission = 'probe' if case is None else 'probe-writer'
    session.request('initialize', {'clientInfo': {'name': 'prestart_anonymous_fixture', 'version': '1'},
                                 'capabilities': {'experimentalApi': True}})
    started = session.request('thread/start', {'model': 'gpt-6-sol', 'modelProvider': 'fixture', 'allowProviderModelFallback': False,
        'cwd': '/control/workspace', 'ephemeral': True, 'permissions': permission,
        'approvalPolicy': 'never', 'environments': environments,
        'dynamicTools': [{'type': 'function', 'name': 'packet_probe', 'description': 'Fixed anonymous admission',
            'inputSchema': {'type': 'object', 'properties': {}, 'additionalProperties': False}, 'deferLoading': False}]})
    if {key: started.get(key) for key in ('model', 'modelProvider', 'cwd', 'approvalPolicy', 'activePermissionProfile')} != {
        'model': 'gpt-6-sol', 'modelProvider': 'fixture', 'cwd': '/control/workspace', 'approvalPolicy': 'never',
        'activePermissionProfile': {'id': permission, 'extends': None}}:
        raise FixtureError('fixture-thread-config-drift')
    identities = receipt['_identities']; identities['threadId'] = started['thread']['id']
    receipt['metadata'] = probe.metadata.collect(session, cwd='/control/workspace', thread_id=identities['threadId'])
    turn = session.request('turn/start', {'threadId': identities['threadId'], 'environments': environments,
        'input': [{'type': 'text', 'text': 'Fixed anonymous container protocol fixture; no integration requested.'}]})
    identities['turnId'] = turn['turn']['id']
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        note = session.notification()
        if note['method'] == 'turn/completed':
            if note['params'].get('threadId') != identities['threadId'] or note['params']['turn'].get('id') != identities['turnId']:
                raise FixtureError('fixture-turn-identity-drift')
            receipt['turn_status'] = note['params']['turn']['status']; break
    session._drain_available(session._deadline())


def writer_wire(native, case, result):
    """Bind the single native command lifecycle to the admitted thread/turn."""
    try:
        call = native['admission_call']; started = []; completed = []; requests = []
        starts = []; completions = []; turn_ends = []; admission_replies = []
        for index, row in enumerate(native['wire']):
            raw = helpers.base64.b64decode(row['raw_base64'], validate=True)
            if probe.manifest.decode(raw) != row['message']:
                return False
            if row['direction'] == 'out-sent' and row['message'].get('id') == call['message_id']:
                admission_replies.append(index)
            if row['direction'] != 'in':
                continue
            message = row['message']
            if 'id' in message and 'method' in message:
                requests.append(message)
            if message.get('method') == 'turn/completed':
                params = message['params']
                if params.get('threadId') != call['threadId'] or params['turn'].get('id') != call['turnId']:
                    return False
                turn_ends.append(index)
            if message.get('method') not in ('item/started', 'item/completed'):
                continue
            params = message['params']; item = params['item']
            if item.get('type') != 'commandExecution':
                continue
            if (params.get('threadId') != call['threadId'] or params.get('turnId') != call['turnId']
                    or item.get('id') != guest.WRITER_CALL):
                return False
            (started if message['method'] == 'item/started' else completed).append(item)
            (starts if message['method'] == 'item/started' else completions).append(index)
        return (len(requests) == 1 and requests[0].get('method') == 'item/tool/call'
            and len(started) == len(completed) == 1
            and len(admission_replies) == len(turn_ends) == 1
            and admission_replies[0] < starts[0] < completions[0] < turn_ends[0]
            and type(completed[0].get('exitCode')) is int and completed[0]['exitCode'] == result['exit_code']
            and completed[0].get('aggregatedOutput') == result['body']
            and completed[0].get('status') in ('completed', 'failed'))
    except (KeyError, ValueError, TypeError, IndexError):
        return False


def acceptance(native, guest_receipt, request, probe_module=probe):
    case = request.get('native_case')
    writer_confirmed = (guest_receipt.get('native_case') == case
        and guest_receipt.get('writer_output_confirmed') is True
        and guest_receipt.get('workspace_expected') is True and guest_receipt.get('canary_preserved') is True
        and guest.stderr_complete(guest_receipt.get('cli_stderr'))
        and writer_wire(native, case, guest_receipt.get('native_result')))
    return (probe_module.admission_wire_confirmed(native)
        and type(native.get('accepted_dynamic_calls')) is int and native['accepted_dynamic_calls'] == 1
        and native.get('turn_status') == 'completed' and 'admission_error' not in native
        and native.get('metadata', {}).get('feature_inventory_complete') is True
        and guest_receipt.get('run_id') == request['run_id'] and guest_receipt.get('sources') == request['sources']
        and guest_receipt.get('passed') is True and guest_receipt.get('cli_wait') == 'observed'
        and type(guest_receipt.get('cli_exit_code')) is int and guest_receipt['cli_exit_code'] == 0
        and guest_receipt.get('fixture_stopped') is True and guest_receipt.get('exact_token_confirmed') is True
        and guest_receipt.get('binary') == guest_receipt.get('binary_after')
        and guest_receipt.get('binary', {}).get('sha256') == guest.BINARY_SHA
        and guest_receipt.get('cli_env') == guest.cli_env(case)
        and (case is None or guest.prerequisites_confirmed(guest_receipt.get('prerequisites', {})))
        and guest_receipt.get('sentinel_preserved') is True
        and (writer_confirmed if case is not None else guest_receipt.get('workspace_unchanged') is True)
        and len(guest_receipt.get('requests', [])) == (3 if case is not None else 2)
        and not any(key in guest_receipt for key in ('failure_class', 'provider_error')))


def run(args, *, _engine_factory=None, _session_factory=None, _capture=capture, _socket=socket_snapshot):
    case = getattr(args, 'native_workspace_case', None)
    native_environments(case)  # Reject an unknown fixed case before any fixture effects.
    bwrap = getattr(args, 'bwrap_path', None)
    if (case is None) != (bwrap is None):
        raise FixtureError('native-writer-fixed-bwrap-required-only-for-writer')
    parent = args.evidence_root.resolve(strict=True)
    if any((directory / '.git').exists() for directory in (parent, *parent.parents)):
        raise FixtureError('private-evidence-outside-git-required')
    fd = helpers.trust._directory(parent)
    try:
        if os.fstat(fd).st_mode & 0o077 or os.getuid() == 0 or os.getgid() == 0:
            raise FixtureError('private-nonroot-host-required')
    finally:
        os.close(fd)
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-prestart-appserver-', dir=parent)); root.chmod(0o700)
    control = root / 'control'; control.mkdir(mode=0o700)
    receipt = {'schema_version': 1, 'fixture': str(root), 'execution_outcome': 'unknown',
        **{name: False for name in ('qualified', 'native_qualified', 'tool_qualified', 'startup_isolation_qualified',
             'isolation_qualified', 'runtime_qualified', 'adapter_qualified', 'production_qualified', 'n1_complete', 'n2_complete', 'n3_complete')}}
    session = engine = None; started = False
    try:
        run_id = uuid.uuid4().hex; name = 'prestart-appserver-' + run_id
        sources, binary = (_capture(root, args.binary_path) if case is None else _capture(root, args.binary_path, bwrap))
        request = {'schema_version': 1, 'run_id': run_id, 'accepted_token': 'packet-admission-accepted:' + run_id,
            'uid': os.getuid(), 'gid': os.getgid(), 'sources': {key: value['sha256'] for key, value in sources.items()},
            'binary_sha256': guest.BINARY_SHA}
        if case is not None:
            fd = os.open(control / 'external-canary', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(guest.CANARY_BYTES); stream.flush(); os.fsync(stream.fileno())
            directory = os.open(control, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            _, canary_ref = helpers._reload_read(control, 'external-canary', 128)
            request.update(native_case=case, canary_ref=canary_ref, bwrap_sha256=guest.BWRAP_SHA)
            receipt.update(native_case=case, canary_before=canary_ref, docker_client_stderr='not-captured')
        request_ref = helpers._reload_save(control, 'request.json', request)
        receipt.update(run_id=run_id, source_capture=sources, binary=binary, interpreter=helpers._reload_interpreter())
        socket = _socket(args.endpoint); create = create_argv(root, name, request['uid'], request['gid'], writer=case is not None)
        engine = _engine_factory(args.endpoint, root, create) if _engine_factory else Engine(args.endpoint, root, create)
        daemon = engine.identity(); image = engine.image(IMAGE); image_config = image_policy(image, writer=case is not None)
        image_ref = helpers._reload_save(root, 'fixed-image-snapshot.json', image)
        config_sha = helpers.packets.digest(helpers.packets.canonical(image_config))
        receipt['fixed_image_snapshot'] = {'reference': image_ref, 'config_sha256': config_sha,
            **({'comparison': 'writer-only-exact-typed-inert-projection'} if case is not None else {})}
        receipt['engine_binding'] = {'endpoint': args.endpoint, 'socket': socket, 'daemon_sha256': daemon,
                                    'executable': engine.executable, 'identity': list(engine.executable_identity)}
        helpers._reload_save(root, 'create-intent.json', {'run_id': run_id, 'argv': create, 'request_ref': request_ref,
                                                        'engine_binding': receipt['engine_binding']})
        reply = engine.command(*create).decode('ascii'); cid, cid_ref = cidfile(root)
        if reply.strip() != cid or engine.failures:
            raise FixtureError('fixture-create-reply-unknown')
        engine.allowed_cid = cid; observed = engine.inspect(cid)
        created = policy(observed, root, name, request['uid'], request['gid'], cid, image_config=image_config, writer=case is not None)
        receipt.update(cid=cid, cid_ref=cid_ref, created=created, prestart_policy=observed)
        helpers._reload_save(root, 'prestart-policy.json', observed)
        argv = [engine.executable, '--host', args.endpoint, 'container', 'start', '--attach', '--interactive', cid]
        helpers._reload_save(root, 'start-intent.json', {'run_id': run_id, 'cid': cid, 'created': created, 'argv': argv})
        check_capture(root / 'capture', sources, bwrap=case is not None)
        helpers._reload_ref(control, request_ref)
        if _socket(args.endpoint) != socket or engine.identity() != daemon:
            raise FixtureError('fixture-prestart-engine-drift')
        helpers._reload_ref(root, image_ref)
        if helpers.packets.digest(helpers.packets.canonical(image_policy(engine.image(IMAGE), writer=case is not None))) != config_sha:
            raise FixtureError('fixed-image-config-snapshot-drift')
        if engine._executable_snapshot() != engine.executable_identity:
            raise FixtureError('fixture-docker-binary-drift')
        policy(engine.inspect(cid), root, name, request['uid'], request['gid'], cid, created, image_config=image_config, writer=case is not None)
        if engine.failures or cidfile(root)[1] != cid_ref:
            raise FixtureError('fixture-start-binding-unknown')
        native = {'accepted_dynamic_calls': 0, 'accepted_token': request['accepted_token'], '_identities': {}}
        callback = probe.admission_callback(native, native['_identities'])
        factory = _session_factory or probe.AdmissionSession
        started = True  # launch uncertainty is irreversible; never repeat this intent.
        session = factory(argv, cwd=str(root), env=dict(engine.environment),
            limits=probe.transport.Limits(timeout=15, close_timeout=5), fixed_tool='packet_probe',
            tool_callback=callback, admission_receipt=native)
        try:
            native_turn(session, native, case)
        finally:
            close = session.close()
            receipt['transport_client_close'] = {'process_kind': 'docker-client', **close}
            native['wire'] = session.wire; native.pop('_identities', None)
            receipt['native'] = native
            helpers._reload_save(root, 'host-native-wire.json', native)
        if type(close.get('exit_code')) is not int or close != {'protocol': 'observed', 'direct_child': 'exited', 'exit_code': 0, 'descendants': 'unknown'}:
            raise FixtureError('fixture-client-close-unknown')
        # Client exit is not guest stop. Only fixed original-CID readback is used.
        deadline = time.monotonic() + 8
        for _ in range(80):
            if time.monotonic() >= deadline:
                raise FixtureError('fixture-container-stop-readback-expired')
            final = engine.inspect(cid)
            if time.monotonic() >= deadline:
                raise FixtureError('fixture-container-stop-readback-expired')
            if final.get('State', {}).get('Running') is not True:
                break
            if time.monotonic() >= deadline:
                raise FixtureError('fixture-container-still-running')
            time.sleep(min(.1, max(0, deadline-time.monotonic())))
        else:
            raise FixtureError('fixture-container-stop-unavailable')
        receipt['container_exit'] = final
        helpers._reload_save(root, 'container-exit-policy.json', final)
        # Preserve bounded diagnostic readback even when the stopped fixture exits
        # nonzero. It cannot satisfy the unchanged successful-exit policy gate.
        if case is not None:
            diagnostic, diagnostic_ref = helpers._reload_read(control, 'guest-receipt.json')
            receipt['guest_receipt'] = helpers._reload_json(diagnostic); receipt['guest_ref'] = diagnostic_ref
        policy(final, root, name, request['uid'], request['gid'], cid, created, stopped=True, image_config=image_config, writer=case is not None)
        raw, ref = helpers._reload_read(control, 'guest-receipt.json')
        guest_receipt = helpers._reload_json(raw); receipt['guest_receipt'] = guest_receipt; receipt['guest_ref'] = ref
        if not acceptance(native, guest_receipt, request):
            raise FixtureError('fixture-guest-or-admission-unknown')
        port = guest_receipt['provider_port']
        if type(port) is not int or not 1 <= port <= 65535 or guest_receipt['cli_argv'] != guest.cli_argv(port, probe.boundary, case):
            raise FixtureError('fixture-guest-cli-argv-drift')
        for index, expected in enumerate(guest_receipt['requests'], 1):
            raw_record, _ = helpers._reload_read(control, 'provider-request-' + str(index) + '.json')
            record = helpers._reload_json(raw_record)
            raw_request = helpers.base64.b64decode(record['raw_base64'], validate=True)
            decoded = probe.manifest.decode(raw_request)
            if index == 2 and probe.boundary.output_text(probe.boundary.find_output(decoded,
                    {'type': 'function_call', 'call_id': guest.CALL})) != request['accepted_token']:
                raise FixtureError('fixture-host-token-readback-drift')
            if (record['stage'] != index or expected != {'stage': index, 'sha256': record['sha256']}
                    or helpers.packets.digest(raw_request) != record['sha256']):
                raise FixtureError('fixture-provider-raw-drift')
            if case is not None:
                response_raw, response_ref = helpers._reload_read(control, 'provider-response-' + str(index) + '.json')
                response = helpers._reload_json(response_raw)
                payload = helpers.base64.b64decode(response['raw_base64'], validate=True)
                if response.get('stage') != index or helpers.packets.digest(payload) != response.get('sha256'):
                    raise FixtureError('fixture-provider-response-raw-drift')
                events = payload.decode().split('\n\n')
                if len(events) != 4 or events[-1] != '':
                    raise FixtureError('fixture-provider-response-framing-drift')
                decoded_events = []
                for event in events[:-1]:
                    event_name, event_data = event.split('\n')
                    parsed = probe.manifest.decode(event_data.removeprefix('data: ').encode())
                    if event_name != 'event: ' + parsed['type']:
                        raise FixtureError('fixture-provider-response-type-drift')
                    decoded_events.append(parsed)
                if [x['type'] for x in decoded_events] != ['response.created', 'response.output_item.done', 'response.completed']:
                    raise FixtureError('fixture-provider-response-order-drift')
                if index == 2 and decoded_events[1].get('item') != guest.writer_call(case):
                    raise FixtureError('fixture-native-issued-call-drift')
                if index == 3:
                    output = probe.boundary.output_text(probe.boundary.find_output(decoded, guest.writer_call(case)))
                    if guest.writer_output(output, case) != guest_receipt.get('native_result'):
                        raise FixtureError('fixture-native-output-readback-drift')
                receipt.setdefault('provider_response_refs', []).append(response_ref)
        if case is not None:
            raw_stderr, stderr_ref = helpers._reload_read(control, 'cli-stderr-capture.json')
            stderr = helpers._reload_json(raw_stderr)
            stderr_bytes = helpers.base64.b64decode(stderr['raw_base64'], validate=True)
            if (stderr != guest_receipt.get('cli_stderr') or not guest.stderr_complete(stderr)
                    or len(stderr_bytes) != stderr['captured_bytes']
                    or helpers.packets.digest(stderr_bytes) != stderr['captured_prefix_sha256']):
                raise FixtureError('fixture-native-stderr-readback-incomplete')
            receipt['cli_stderr_ref'] = stderr_ref
            canary, canary_after = helpers._reload_read(control, 'external-canary', 128)
            if canary != guest.CANARY_BYTES or canary_after != request['canary_ref']:
                raise FixtureError('fixture-native-canary-drift')
            workspace = control / 'workspace'
            expected_names = ['native-write.txt'] if case == 'workspace-write' else []
            if sorted(path.name for path in workspace.iterdir()) != expected_names:
                raise FixtureError('fixture-native-workspace-extra-effects')
            if case == 'workspace-write':
                written, written_ref = helpers._reload_read(control, 'workspace/native-write.txt', 128)
                if written != guest.WRITE_BYTES:
                    raise FixtureError('fixture-native-workspace-postimage-drift')
                receipt['native_write_ref'] = written_ref
            receipt['canary_after'] = canary_after
        spawn_raw, spawn_ref = helpers._reload_read(control, 'cli-spawn-intent.json')
        if helpers._reload_json(spawn_raw) != {'run_id': run_id, 'argv': guest_receipt['cli_argv'], 'env': guest.cli_env(case)}:
            raise FixtureError('fixture-guest-spawn-intent-drift')
        receipt['guest_spawn_ref'] = spawn_ref
        if type(guest_receipt.get('cli_pid')) is not int or not 1 < guest_receipt['cli_pid'] <= 2147483647:
            raise FixtureError('fixture-guest-child-identity-unavailable')
        check_capture(root / 'capture', sources, bwrap=case is not None); helpers._reload_ref(control, request_ref)
        helpers._reload_ref(root, image_ref)
        if helpers.packets.digest(helpers.packets.canonical(image_policy(engine.image(IMAGE), writer=case is not None))) != config_sha:
            raise FixtureError('fixed-image-config-final-drift')
        if engine.failures or engine.identity() != daemon or _socket(args.endpoint) != socket:
            raise FixtureError('fixture-final-engine-unknown')
        receipt['execution_outcome'] = ('measured-synthetic-prestart-container-admission-passed' if case is None else
                                        'measured-synthetic-native-' + case + '-passed')
    except Exception as error:
        receipt['failure_class'] = type(error).__name__; receipt['failure_reason'] = str(error)[:160]
        if started and case is not None and engine is not None and 'cid' in receipt:
            # Read only the original CID; failure diagnostics never satisfy the
            # successful-exit gate or grant continuation/replay authority.
            try:
                observed_failure = engine.inspect(receipt['cid'])
                receipt['failure_container_observation'] = observed_failure
                helpers._reload_save(root, 'failure-container-observation.json', observed_failure)
                state = observed_failure.get('State', {})
                if (state.get('Running') is False and type(state.get('Pid')) is int and state['Pid'] == 0
                        and state.get('Status') == 'exited'):
                    diagnostic, diagnostic_ref = helpers._reload_read(control, 'guest-receipt.json')
                    receipt['guest_failure_diagnostic'] = helpers._reload_json(diagnostic)
                    receipt['guest_failure_ref'] = diagnostic_ref
            except Exception as diagnostic_error:
                receipt['failure_diagnostic_error'] = type(diagnostic_error).__name__
        # Unknown create permits only the exact persisted CID's readonly inspect.
        if engine is not None and not started and 'cid' not in receipt:
            try:
                cid, reference = cidfile(root); engine.allowed_cid = cid
                receipt['unknown_create_cid_ref'] = reference; receipt['unknown_create_inspect'] = engine.inspect(cid)
            except Exception as evidence_error:
                receipt['unknown_create_readback'] = type(evidence_error).__name__
        raise
    finally:
        receipt['start_attempted'] = started; receipt['transport_failures'] = getattr(engine, 'failures', [])
        receipt['transport_trace_count'] = len(getattr(engine, 'trace', []))
        helpers._reload_save(root, 'prestart-appserver-evidence.json', receipt)
        print(json.dumps({'evidence': str(root / 'prestart-appserver-evidence.json'),
                          'execution_outcome': receipt['execution_outcome'], 'production_qualified': False}))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prestart-container-fixture', action='store_true', required=True)
    parser.add_argument('--native-workspace-case', choices=guest.WRITER_CASES)
    parser.add_argument('--bwrap-path', type=pathlib.Path)
    parser.add_argument('--binary-path', type=pathlib.Path, required=True)
    parser.add_argument('--endpoint', required=True)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    if not args.prestart_container_fixture:
        parser.error('explicit fixed fixture opt-in required')
    run(args)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
