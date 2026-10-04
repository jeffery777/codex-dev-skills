"""Opt-in fixed synthetic Docker backend; no provider, broker or registry adoption.

The host alone selects the local Unix endpoint and already-installed image ID.
Only prepare creates a container, only launch starts its sealed exact physical ID.
Neither reconciliation nor sealed export runs any command in the worker.
"""
from __future__ import annotations
import copy
import difflib
import hashlib
import json
import os
import pathlib
import re
import select
import shutil
import stat
import subprocess
import time
import tempfile
import uuid

import model_container_launcher as launcher
import model_control_archive as archive

import agent_qualification as trust
import model_packet_store as packets
import model_packet_supervisor as supervisors

# Bind the loaded implementation/validator, not merely a subset of launch flags.
CONTRACT_SHA256 = packets.digest(pathlib.Path(__file__).read_bytes())
ARCHIVE_CONTRACT_SHA256 = packets.digest(pathlib.Path(archive.__file__).read_bytes())
MAX_ENGINE_OUTPUT = 65536
MAX_FILES = 32
MAX_FILE_BYTES = 262144
MAX_TREE_BYTES = 1048576
IMAGE = re.compile(r'sha256:[0-9a-f]{64}\Z')
BASELINE = {'example.txt': b'old\n', 'remove.txt': b'delete\n'}
ALLOWED_PATHS = frozenset({'example.txt', 'remove.txt', 'added.txt', 'background-started.txt', 'late.txt', 'privileges.json', 'grandchild.json'})
BINDING_KEYS = frozenset({'packet_id', 'attempt_id', 'identity_sha256', 'generation', 'request_sha256',
    'target_sha256', 'predecessor_sha256', 'source_sha256', 'scope_sha256', 'acceptance_sha256',
    'runtime_id', 'host_id', 'backend_id', 'policy_sha256'})
ENV_KEYS = frozenset({'PATH', 'LANG', 'GPG_KEY', 'PYTHON_VERSION', 'PYTHON_SHA256'})
AUDIT_CHILD = """import json,os,pathlib
status={}
for line in pathlib.Path('/proc/self/status').read_text().splitlines():
 if ':' in line:
  key,value=line.split(':',1); status[key]=value.strip()
fds=[]
for name in os.listdir('/proc/self/fd'):
 try: target=os.readlink('/proc/self/fd/'+name)
 except FileNotFoundError: continue
 if int(name)>2: fds.append(target)
denied=False
try: os.open('/control/input.json',os.O_RDONLY)
except PermissionError: denied=True
report={'uid':list(os.getresuid()),'gid':list(os.getresgid()),'groups':os.getgroups(),'caps':{key:status[key] for key in ['CapInh','CapPrm','CapEff','CapBnd','CapAmb']},'nnp':status['NoNewPrivs'],'fds':fds,'control_denied':denied}
pathlib.Path('/workspace/'+REPORT).write_text(json.dumps(report,sort_keys=True)+'\\n')
"""
BACKGROUND_CHILD = "import pathlib,time; w=pathlib.Path('/workspace'); (w/'background-started.txt').write_text('active\\n'); time.sleep(2); (w/'late.txt').write_text('late\\n')"
WORKERS = {
    'edit': "import pathlib; w=pathlib.Path('/workspace'); (w/'example.txt').write_text('new\\n'); (w/'added.txt').write_text('added\\n'); (w/'remove.txt').unlink(missing_ok=True)",
    'add-update': "import pathlib; w=pathlib.Path('/workspace'); (w/'example.txt').write_text('new\\n'); (w/'added.txt').write_text('added\\n')",
    'privileges': "REPORT='privileges.json'\n"+AUDIT_CHILD+"\nimport subprocess,sys; subprocess.run([sys.executable,'-I','-c',"+repr("REPORT='grandchild.json'\n"+AUDIT_CHILD)+"],check=True)",
    'noop': "pass",
    'hold': "import pathlib,time; w=pathlib.Path('/workspace'); (w/'example.txt').write_text('holding\\n'); time.sleep(15); (w/'example.txt').write_text('done\\n')",
    'background': "import pathlib,subprocess,sys,time; w=pathlib.Path('/workspace'); subprocess.Popen([sys.executable,'-I','-c',"
        + repr(BACKGROUND_CHILD) + "],start_new_session=True); deadline=time.monotonic()+1;\n"
        "while not (w/'background-started.txt').exists():\n"
        " if time.monotonic()>deadline: raise RuntimeError('child-not-ready')\n"
        " time.sleep(.01)\n(w/'example.txt').write_text('background\\n')",
}


def tree_manifest(files):
    return {name: {'bytes': len(raw), 'sha256': packets.digest(raw)} for name, raw in sorted(files.items())}


def source_digest():
    return packets.digest(packets.canonical(tree_manifest(BASELINE)))


def validate_fixed_predecessor(patch):
    if type(patch) is not bytes or len(patch)>packets.MAX_PATCH:
        raise packets.PacketError('invalid-fixed-predecessor')
    if not patch:
        return
    targets=[]
    for line in patch.splitlines():
        if line.startswith(b'diff --git '):
            match=re.fullmatch(rb'diff --git a/([a-z.-]+) b/([a-z.-]+)',line)
            if match is None or match[1]!=match[2] or match[1].decode() not in ALLOWED_PATHS:
                raise packets.PacketError('predecessor-scope-rejected')
            target=match[1]
            if target in targets or len(targets)>=len(ALLOWED_PATHS):
                raise packets.PacketError('predecessor-duplicate-target')
            targets.append(target)
        elif line.startswith((b'new file mode ',b'deleted file mode ',b'old mode ',b'new mode ')):
            if line.rsplit(b' ',1)[-1]!=b'100644':
                raise packets.PacketError('predecessor-mode-rejected')
        elif line.startswith(b'index ') and len(line.split())==3:
            if line.split()[-1]!=b'100644':
                raise packets.PacketError('predecessor-mode-rejected')
        elif line.startswith((b'rename ',b'copy ',b'GIT binary patch',b'Binary files ')):
            raise packets.PacketError('predecessor-type-rejected')
    actual=_fixed_git_numstat(patch)
    if not targets or len(actual)!=len(targets) or set(actual)!=set(targets):
        raise packets.PacketError('predecessor-actual-target-drift')


def _fixed_git_numstat(patch):
    """Parse the ENTIRE patch using Git in a fresh trusted empty directory.

    Numstat -z targets include traditional patches without diff --git headers.
    Simultaneous bounded stdin/stdout and one deadline avoid pipe deadlocks;
    this never applies source or consults worker Git/configuration.
    """
    limit=4096; raw=bytearray(); sent=0; deadline=time.monotonic()+10
    with tempfile.TemporaryDirectory(prefix='packet-fixed-numstat-') as directory:
        process=subprocess.Popen(['git','apply','--numstat','-z','-'],cwd=directory,
            env={'PATH':os.defpath,'HOME':directory,'GIT_CONFIG_NOSYSTEM':'1',
                'GIT_CONFIG_GLOBAL':os.devnull,'LC_ALL':'C'},stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,close_fds=True)
        os.set_blocking(process.stdin.fileno(),False); os.set_blocking(process.stdout.fileno(),False)
        reading=True
        try:
            while reading or not process.stdin.closed:
                if sent==len(patch) and not process.stdin.closed: process.stdin.close()
                remaining=deadline-time.monotonic()
                if remaining<=0: raise packets.PacketError('predecessor-parser-timeout')
                readers=[process.stdout] if reading else []
                writers=[process.stdin] if not process.stdin.closed else []
                ready,writable,_=select.select(readers,writers,[],remaining)
                if not ready and not writable: raise packets.PacketError('predecessor-parser-timeout')
                if writable: sent+=os.write(process.stdin.fileno(),patch[sent:sent+8192])
                if ready:
                    chunk=os.read(process.stdout.fileno(),min(4096,limit+1-len(raw)))
                    if not chunk: reading=False
                    else:
                        raw.extend(chunk)
                        if len(raw)>limit: raise packets.PacketError('predecessor-parser-output-bound')
            if process.wait(timeout=max(.01,deadline-time.monotonic()))!=0:
                raise packets.PacketError('predecessor-parser-rejected')
        finally:
            if process.poll() is None: process.kill(); process.wait(timeout=2)
            if not process.stdin.closed: process.stdin.close()
            process.stdout.close()
    targets=[]
    if not raw or not raw.endswith(b'\x00'): raise packets.PacketError('predecessor-parser-rejected')
    for row in bytes(raw).split(b'\x00')[:-1]:
        match=re.fullmatch(rb'[0-9]+\t[0-9]+\t([a-z.-]+)',row)
        if match is None or match[1].decode() not in ALLOWED_PATHS or match[1] in targets:
            raise packets.PacketError('predecessor-parser-target-rejected')
        targets.append(match[1])
    return targets


def _identity(st):
    return packets.digest(packets.canonical({'device': st.st_dev, 'inode': st.st_ino, 'owner': st.st_uid}))


def _json(raw):
    return json.loads(raw, object_pairs_hook=trust._pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(packets.PacketError('invalid-engine-json')))


class LocalDocker:
    """Fixed argv transport, pinned endpoint, bounded response and closed FDs."""
    def __init__(self, endpoint, home):
        if (type(endpoint) is not str or not endpoint.startswith('unix:///')
                or '..' in pathlib.PurePosixPath(endpoint[7:]).parts or len(endpoint) > 256):
            raise packets.PacketError('local-unix-docker-endpoint-required')
        executable = shutil.which('docker')
        if not executable:
            raise packets.PacketError('docker-unavailable')
        self.executable = str(pathlib.Path(executable).resolve(strict=True))
        st = os.stat(self.executable)
        if not stat.S_ISREG(st.st_mode) or st.st_uid not in {0, os.getuid()} or st.st_mode & 0o022:
            raise packets.PacketError('untrusted-docker-executable')
        self.endpoint = endpoint
        self.environment = {'PATH': os.defpath, 'HOME': str(home), 'DOCKER_CONFIG': str(home/'.docker-disabled'), 'LC_ALL': 'C'}
        self.executable_identity = self._executable_snapshot()
        self.executable_sha256 = self.executable_identity[-1]

    def _executable_snapshot(self):
        fd = os.open(self.executable, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid not in {0, os.getuid()}
                    or before.st_mode & 0o022):
                raise packets.PacketError('untrusted-docker-executable')
            def identity(value):
                return (value.st_dev, value.st_ino, value.st_uid, value.st_mode,
                        value.st_size, value.st_mtime_ns, value.st_ctime_ns)
            approved = getattr(self, 'executable_identity', None)
            if before.st_size > 134217728 or approved is not None and identity(before) != approved[:-1]:
                raise packets.PacketError('docker-executable-identity-drift')
            with os.fdopen(os.dup(fd), 'rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = os.fstat(fd)
            path = os.stat(self.executable, follow_symlinks=False)
            if identity(before) != identity(after) or identity(after) != identity(path):
                raise packets.PacketError('docker-executable-changed-during-read')
            return identity(after)+(digest,)
        finally:
            os.close(fd)

    def command(self, *argv):
        return self._transport(argv).strip()

    def archive(self, *argv, input_bytes=None):
        return self._transport(argv, input_bytes)

    def _transport(self, argv, input_bytes=None):
        deadline = time.monotonic()+10
        if input_bytes is not None and (type(input_bytes) is not bytes or len(input_bytes) > MAX_ENGINE_OUTPUT):
            raise packets.PacketError('docker-input-bound')
        if self._executable_snapshot() != self.executable_identity:
            raise packets.PacketError('docker-executable-identity-drift')
        process = subprocess.Popen([self.executable, '--host', self.endpoint, *argv],
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=self.environment, close_fds=True, cwd=self.environment['HOME'])
        raw = bytearray(); sent = 0; read_open = True
        os.set_blocking(process.stdout.fileno(), False)
        if process.stdin is not None:
            os.set_blocking(process.stdin.fileno(), False)
        try:
            while read_open or process.stdin is not None and not process.stdin.closed:
                remaining = deadline-time.monotonic()
                if remaining <= 0:
                    raise packets.PacketError('docker-reply-unknown')
                if process.stdin is not None and not process.stdin.closed and sent == len(input_bytes):
                    process.stdin.close()
                readers = [process.stdout] if read_open else []
                writers = [process.stdin] if process.stdin is not None and not process.stdin.closed else []
                ready, writable, _ = select.select(readers, writers, [], remaining)
                if not ready and not writable:
                    raise packets.PacketError('docker-reply-unknown')
                if writable:
                    sent += os.write(process.stdin.fileno(), input_bytes[sent:sent+8192])
                if ready:
                    chunk = os.read(process.stdout.fileno(), min(65536, MAX_ENGINE_OUTPUT+1-len(raw)))
                    if not chunk:
                        read_open = False
                    else:
                        raw.extend(chunk)
                        if len(raw) > MAX_ENGINE_OUTPUT:
                            raise packets.PacketError('docker-output-bound')
            if process.wait(timeout=max(.01, deadline-time.monotonic())) != 0:
                raise packets.PacketError('docker-command-rejected')
            return bytes(raw)
        finally:
            if process.poll() is None:
                process.kill(); process.wait(timeout=2)
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            process.stdout.close()

    def identity(self):
        value = _json(self.command('info', '--format', '{{json .ID}}'))
        if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9-]{1,128}', value):
            raise packets.PacketError('docker-daemon-identity-unavailable')
        return packets.digest(packets.canonical({'endpoint': self.endpoint, 'daemon_id': value,
                                               'executable_sha256': self.executable_sha256}))

    def image(self, image_id):
        values = _json(self.command('image', 'inspect', image_id))
        if type(values) is not list or len(values) != 1:
            raise packets.PacketError('invalid-docker-image')
        return values[0]

    def volume(self, name):
        values = _json(self.command('volume', 'inspect', name))
        if type(values) is not list or len(values) != 1:
            raise packets.PacketError('invalid-volume-inspect')
        return values[0]

    def inspect(self, container_id):
        values = _json(self.command('container', 'inspect', container_id))
        if type(values) is not list or len(values) != 1:
            raise packets.PacketError('invalid-container-inspect')
        return values[0]


def _environment_map(values):
    if type(values) is not list or any(type(value) is not str or '=' not in value for value in values):
        raise packets.PacketError('container-environment-invalid')
    result = {}
    for value in values:
        key, item = value.split('=', 1)
        if key in result:
            raise packets.PacketError('container-environment-invalid')
        result[key] = item
    return result


def validate_policy(value, *, image_id, workspace, name, labels, worker, environment):
    """All policy fields are compared with host-owned fixed launch parameters."""
    try:
        host, config = value['HostConfig'], value['Config']
        mount = value['Mounts']
        if (type(mount) is not list or len(mount) != 1 or mount[0]['Type'] != 'bind'
                or mount[0]['Source'] != str(workspace) or mount[0]['Destination'] != '/workspace'
                or mount[0]['RW'] is not True or mount[0]['Propagation'] != 'rprivate'):
            raise packets.PacketError('container-mount-drift')
        if (value['Image'] != image_id or config['Image'] != image_id or value['Name'] != '/'+name
                or config['Labels'] != labels or config['Entrypoint'] != ['/usr/local/bin/python3']
                or config['Cmd'] != ['-I', '-c', WORKERS[worker]] or config['User'] != '65534:65534'
                or config['WorkingDir'] != '/workspace' or config['Healthcheck']['Test'] != ['NONE']
                or _environment_map(config['Env']) != _environment_map(environment) or config['OpenStdin'] is not False or config['Tty'] is not False
                or host['NetworkMode'] != 'none' or host['ReadonlyRootfs'] is not True
                or host['Privileged'] is not False or host['CapDrop'] != ['ALL']
                or host['CapAdd'] not in (None, []) or host['SecurityOpt'] != ['no-new-privileges']
                or type(host['PidsLimit']) is not int or host['PidsLimit'] != 32
                or type(host['Memory']) is not int or host['Memory'] != 134217728
                or type(host['MemorySwap']) is not int or host['MemorySwap'] != 134217728
                or type(host['NanoCpus']) is not int or host['NanoCpus'] != 1000000000
                or host['CpuPeriod'] != 0 or host['CpuQuota'] != 0
                or host['Tmpfs'] != {'/tmp': 'rw,noexec,nosuid,nodev,size=8m'}
                or host['RestartPolicy'] != {'Name': 'no', 'MaximumRetryCount': 0}
                or host['AutoRemove'] is not False or host['VolumesFrom'] not in (None, [])
                or host['Devices'] not in (None, []) or host['DeviceRequests'] not in (None, [])
                or host['DeviceCgroupRules'] not in (None, []) or host['PortBindings'] not in (None, {})
                or host['PidMode'] != '' or host['IpcMode'] != 'private' or host['CgroupnsMode'] != 'private'
                or host['UTSMode'] != '' or host['UsernsMode'] != '' or host['PublishAllPorts'] is not False
                or host['GroupAdd'] not in (None, []) or host['ExtraHosts'] not in (None, [])
                or host['Binds'] not in (None, []) or host['Links'] not in (None, [])):
            raise packets.PacketError('container-policy-drift')
    except (KeyError, TypeError, IndexError) as error:
        raise packets.PacketError('container-policy-incomplete') from error


class SyntheticContainerBackend:
    requires_runtime_descriptor = True

    def __init__(self, store, *, endpoint, image_id, worker='edit', opt_in=False, _engine=None):
        if opt_in is not True or type(image_id) is not str or not IMAGE.fullmatch(image_id) or worker not in WORKERS:
            raise packets.PacketError('synthetic-container-opt-in-required')
        self.store, self.image_id, self.worker = store, image_id, worker
        self.engine = _engine if _engine is not None else LocalDocker(endpoint, store.root)
        self.daemon_identity_sha256 = self.engine.identity()
        image = self.engine.image(image_id)
        config = image.get('Config', {})
        environment = config.get('Env', [])
        if (image.get('Id') != image_id or image.get('Os') != 'linux' or image.get('Architecture') != 'arm64'
                or config.get('Volumes') not in (None, {}) or config.get('Entrypoint') not in (None, [])
                or type(environment) is not list or len(environment) > 16
                or any(type(item) is not str or len(item) > 1024 or '=' not in item
                       or item.split('=', 1)[0] not in ENV_KEYS for item in environment)
                or len({item.split('=', 1)[0] for item in environment}) != len(environment)
                or config.get('Labels') not in (None, {})):
            raise packets.PacketError('synthetic-python-image-policy-rejected')
        self.environment = environment+['HOME=/tmp']
        self.policy_sha256 = packets.digest(packets.canonical({'schema_version': 1,
            'contract_sha256': CONTRACT_SHA256, 'image_id': image_id,
            'worker': worker, 'script_sha256': packets.digest(WORKERS[worker].encode()),
            'environment': self.environment, 'allowed_paths': sorted(ALLOWED_PATHS),
            'max_files': MAX_FILES, 'max_file_bytes': MAX_FILE_BYTES, 'max_tree_bytes': MAX_TREE_BYTES,
            'network': 'none', 'uid': '65534:65534', 'cpu': 1, 'memory': 134217728, 'pids': 32}))
        self.host_id = 'docker-'+self.daemon_identity_sha256[:32]
        self.backend_id = 'synthetic-container-v1'

    def _binding(self, binding):
        if type(binding) is not dict or set(binding) != BINDING_KEYS:
            raise packets.PacketError('synthetic-container-binding-invalid')
        if (binding['packet_id'] != self.store.packet_id or binding['host_id'] != self.host_id
                or binding['backend_id'] != self.backend_id or binding['policy_sha256'] != self.policy_sha256
                or binding['source_sha256'] != source_digest()):
            raise packets.PacketError('synthetic-container-binding-drift')
        packets._id(binding['runtime_id']); packets._id(binding['attempt_id'])
        if self.engine.identity() != self.daemon_identity_sha256:
            raise packets.PacketError('docker-daemon-identity-drift')

    def _packet_fd(self):
        root = trust._directory(self.store.root)
        try:
            fd = os.open(self.store.packet_id, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            trust._check(os.fstat(fd), directory=True)
            if os.fstat(fd).st_mode & 0o077:
                raise packets.PacketError('packet-directory-must-be-private')
            return fd
        finally:
            os.close(root)

    def _workspace(self, binding):
        return self.store.root/self.store.packet_id/('workspace-'+binding['runtime_id'])

    def _workspace_fd(self, binding, descriptor=None):
        fd = self._packet_fd()
        try:
            child = os.open('workspace-'+binding['runtime_id'], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
        finally:
            os.close(fd)
        st = os.fstat(child)
        if st.st_uid != os.getuid() or descriptor is not None and _identity(st) != descriptor['workspace_identity_sha256']:
            os.close(child); raise packets.PacketError('workspace-identity-drift')
        return child

    def _walk(self, binding, descriptor=None):
        fd = self._workspace_fd(binding, descriptor)
        result = {}; total = 0
        try:
            names = os.listdir(fd)
            if len(names) > MAX_FILES:
                raise packets.PacketError('workspace-file-bound')
            for name in sorted(names):
                if name not in ALLOWED_PATHS:
                    raise packets.PacketError('workspace-path-rejected')
                file_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
                try:
                    before = os.fstat(file_fd)
                    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_mode & 0o111
                            or before.st_uid not in {os.getuid(), 65534} or before.st_size > MAX_FILE_BYTES):
                        raise packets.PacketError('workspace-file-rejected')
                    chunks = []; size = 0
                    while size <= MAX_FILE_BYTES:
                        chunk = os.read(file_fd, min(65536, MAX_FILE_BYTES+1-size))
                        if not chunk:
                            break
                        chunks.append(chunk); size += len(chunk)
                    after = os.fstat(file_fd)
                    path_st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                            or (path_st.st_dev, path_st.st_ino) != (after.st_dev, after.st_ino)
                            or size > MAX_FILE_BYTES):
                        raise packets.PacketError('workspace-changed-during-read')
                    raw = b''.join(chunks); raw.decode('utf-8')
                    if b'\x00' in raw or raw and not raw.endswith(b'\n'):
                        raise packets.PacketError('workspace-text-rejected')
                    result[name] = raw; total += size
                    if total > MAX_TREE_BYTES:
                        raise packets.PacketError('workspace-tree-bound')
                finally:
                    os.close(file_fd)
            if sorted(os.listdir(fd)) != sorted(names):
                raise packets.PacketError('workspace-changed-during-read')
            return result
        finally:
            os.close(fd)

    def _labels(self, binding):
        return {'dev.codex.synthetic': 'true', 'dev.codex.binding': packets.digest(packets.canonical(binding)),
                'dev.codex.runtime': binding['runtime_id']}

    def _validate_policy(self, observed, binding, descriptor=None):
        validate_policy(observed, image_id=self.image_id, workspace=self._workspace(binding), name=binding['runtime_id'],
                        labels=self._labels(binding), worker=self.worker, environment=self.environment)

    def _create_options(self, binding):
        name = binding['runtime_id']
        labels = self._labels(binding)
        options = ['container', 'create', '--name', name, '--pull=never', '--no-healthcheck',
            '--restart=no', '--network=none', '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--pids-limit=32', '--memory=128m', '--memory-swap=128m', '--cpus=1', '--user=65534:65534',
            '--ipc=private', '--cgroupns=private', '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m', '--workdir=/workspace',
            '--mount', f'type=bind,src={self._workspace(binding)},dst=/workspace,bind-propagation=rprivate', '--env=HOME=/tmp']
        for key, value in sorted(labels.items()):
            options += ['--label', key+'='+value]
        options += ['--entrypoint=/usr/local/bin/python3', self.image_id, '-I', '-c', WORKERS[self.worker]]
        return options

    def prepare(self, binding, predecessor_patch):
        """Called once under supervisor lock; create is never replayed on restart."""
        self._binding(binding)
        fd = self._packet_fd()
        try:
            os.mkdir('workspace-'+binding['runtime_id'], 0o777, dir_fd=fd)
            os.chmod('workspace-'+binding['runtime_id'], 0o777, dir_fd=fd, follow_symlinks=False)
            os.fsync(fd)
        finally:
            os.close(fd)
        child = self._workspace_fd(binding)
        try:
            for name, raw in BASELINE.items():
                output = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o666, dir_fd=child)
                os.fchmod(output, 0o666)
                with os.fdopen(output, 'wb') as stream:
                    stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            os.fsync(child)
        finally:
            os.close(child)
        if predecessor_patch:
            validate_fixed_predecessor(predecessor_patch)
            result = subprocess.run(['git', 'apply', '-'], input=predecessor_patch,
                cwd=self._workspace(binding), env={'PATH': os.defpath, 'HOME': str(self.store.root),
                    'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'LC_ALL': 'C'},
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, close_fds=True)
            if result.returncode:
                raise packets.PacketError('predecessor-restore-rejected')
        initial = self._walk(binding)
        workspace_fd = self._workspace_fd(binding)
        try:
            for name in initial:
                os.chmod(name, 0o666, dir_fd=workspace_fd, follow_symlinks=False)
            os.fsync(workspace_fd)
        finally:
            os.close(workspace_fd)
        # Baseline is immutable host state, not a second lifecycle/retry ledger.
        self._save(binding, 'baseline', packets.canonical({name: raw.decode() for name, raw in initial.items()}))
        name = binding['runtime_id']; labels = self._labels(binding)
        options = self._create_options(binding)
        cid = self.engine.command(*options).decode()
        packets._sha(cid)
        observed = self.engine.inspect(cid)
        self._validate_policy(observed, binding)
        if observed['Id'] != cid or observed['State']['Status'] != 'created' or observed['State']['Running'] is not False:
            raise packets.PacketError('container-not-prepared')
        workspace_fd = self._workspace_fd(binding)
        try:
            workspace_identity = _identity(os.fstat(workspace_fd))
        finally:
            os.close(workspace_fd)
        return {'schema_version': 1, 'binding': binding, 'container_id': cid,
                'daemon_identity_sha256': self.daemon_identity_sha256, 'image_id': self.image_id,
                'created_at': observed['Created'], 'workspace_sha256': packets.digest(packets.canonical(tree_manifest(initial))),
                'workspace_identity_sha256': workspace_identity, 'policy_sha256': self.policy_sha256}

    def _observed(self, binding, descriptor):
        self._binding(binding)
        self.store._validate_runtime_descriptor(descriptor, binding)
        # Never inspect an ID chosen by caller payload. It must already be bound
        # in the protected ledger/immutable artifact before any engine lookup.
        packet_fd = self._packet_fd()
        try:
            ledger = self.store._read(packet_fd)
            record = (ledger or {}).get('supervisors', {}).get(binding['attempt_id'])
            if (record is None or record['binding'] != binding or record['schema_version'] not in {3, 4}
                    or record['runtime_descriptor_sha256'] != packets.digest(packets.canonical(descriptor))
                    or self.store._runtime_descriptor(packet_fd, record) != descriptor):
                raise packets.PacketError('container-descriptor-not-bound')
        finally:
            os.close(packet_fd)
        if descriptor['daemon_identity_sha256'] != self.daemon_identity_sha256 or descriptor['image_id'] != self.image_id:
            raise packets.PacketError('container-descriptor-drift')
        observed = self.engine.inspect(descriptor['container_id'])
        self._validate_policy(observed, binding, descriptor)
        if observed['Id'] != descriptor['container_id'] or observed['Created'] != descriptor['created_at']:
            raise packets.PacketError('physical-container-identity-drift')
        fd = self._workspace_fd(binding, descriptor)
        os.close(fd)
        # Engine mount arrays have no semantic ordering; policy validates every
        # fixed destination before normalizing independently observed snapshots.
        observed['Mounts']=sorted(observed['Mounts'],key=lambda mount:mount['Destination'])
        return observed

    def launch(self, binding, descriptor):
        observed = self._observed(binding, descriptor)
        if observed['State']['Status'] != 'created' or observed['State']['Running'] is not False:
            raise packets.PacketError('container-start-not-fresh')
        self.engine.command('container', 'start', descriptor['container_id'])

    def inspect(self, binding, descriptor):
        observed = self._observed(binding, descriptor)
        state = observed['State']
        stopped = (state['Running'] is False and state['Status'] == 'exited' and state['Restarting'] is False
                   and state['Paused'] is False and type(state['Pid']) is int
                   and type(observed['RestartCount']) is int
                   and state['Dead'] is False and state['Pid'] == 0 and observed['RestartCount'] == 0
                   and state['StartedAt'] != '0001-01-01T00:00:00Z' and state['FinishedAt'] != '0001-01-01T00:00:00Z')
        # This immutable stamp records an observation only, not original-start proof.
        if state['Status'] in {'running', 'exited'}:
            self._save(binding, 'started', packets.canonical({'binding': binding,
                'descriptor_sha256': packets.digest(packets.canonical(descriptor)), 'started_at': state['StartedAt']}))
        evidence = packets.digest(packets.canonical({'descriptor_sha256': packets.digest(packets.canonical(descriptor)),
            'state': state, 'restart_count': observed['RestartCount'], 'physically_stopped': stopped,
            'original_execution_qualified': False}))
        return {'binding': binding, 'runtime_identity_sha256': packets.digest(packets.canonical(binding)),
                # Docker StartedAt/RestartCount cannot identify the original execution:
                # manual same-CID starts on a shared daemon may reset these facts.
                # Physical stop remains an observation, never candidate authority.
                'state': 'unknown', 'external_effects': 'excluded', 'evidence_sha256': evidence}

    def _save(self, binding, suffix, raw):
        fd = self._packet_fd()
        try:
            name = 'backend-'+binding['runtime_id']+'.'+suffix
            try:
                existing = trust._read(fd, name, max(packets.MAX_LEDGER, packets.MAX_PATCH))
            except FileNotFoundError:
                self.store._immutable(fd, name, raw)
            else:
                if existing != raw:
                    raise packets.PacketError('container-artifact-conflict')
        finally:
            os.close(fd)

    def _read(self, binding, suffix, limit):
        fd = self._packet_fd()
        try:
            return trust._read(fd, 'backend-'+binding['runtime_id']+'.'+suffix, limit)
        finally:
            os.close(fd)

    def export_patch(self, binding, limit, descriptor):
        before = self.inspect(binding, descriptor)
        if before['state'] != 'stopped':
            raise packets.PacketError('container-not-stopped')
        original = _json(self._read(binding, 'baseline', MAX_TREE_BYTES))
        if type(original) is not dict or any(name not in ALLOWED_PATHS or type(raw) is not str for name, raw in original.items()):
            raise packets.PacketError('invalid-container-baseline')
        baseline = {name: raw.encode() for name, raw in original.items()}
        if packets.digest(packets.canonical(tree_manifest(baseline))) != descriptor['workspace_sha256']:
            raise packets.PacketError('container-baseline-drift')
        final = self._walk(binding, descriptor)
        # Each checkpoint is cumulative against the fixed approved source, so
        # restoring the latest patch alone preserves every predecessor change.
        baseline = BASELINE
        patch = bytearray()
        for name in sorted(set(baseline)|set(final)):
            old, new = baseline.get(name), final.get(name)
            if old == new:
                continue
            header = f'diff --git a/{name} b/{name}\n'
            if old is None:
                header += 'new file mode 100644\n'
            elif new is None:
                header += 'deleted file mode 100644\n'
            difference = ''.join(difflib.unified_diff((old or b'').decode().splitlines(True),
                (new or b'').decode().splitlines(True), fromfile='a/'+name if old is not None else '/dev/null',
                tofile='b/'+name if new is not None else '/dev/null'))
            patch.extend((header+difference).encode())
            if len(patch) > min(limit, packets.MAX_PATCH):
                raise packets.PacketError('container-patch-bound')
        patch = bytes(patch); supervisors.validate_patch(patch)
        if self.inspect(binding, descriptor) != before:
            raise packets.PacketError('container-changed-during-export')
        manifest = {'schema_version': 1, 'binding': binding, 'descriptor_sha256': packets.digest(packets.canonical(descriptor)),
                    'patch_sha256': packets.digest(patch), 'evidence_sha256': before['evidence_sha256']}
        self._save(binding, 'patch', patch)
        self._save(binding, 'export', packets.canonical(manifest))
        return {'binding': binding, 'patch': patch, 'patch_sha256': packets.digest(patch)}

    def read_sealed_patch(self, binding, limit, descriptor):
        if self.inspect(binding, descriptor)['state'] != 'stopped':
            raise packets.PacketError('container-not-stopped')
        manifest = _json(self._read(binding, 'export', packets.MAX_LEDGER))
        expected = {'schema_version', 'binding', 'descriptor_sha256', 'patch_sha256', 'evidence_sha256'}
        if (type(manifest) is not dict or set(manifest) != expected or manifest['schema_version'] != 1
                or manifest['binding'] != binding
                or manifest['descriptor_sha256'] != packets.digest(packets.canonical(descriptor))):
            raise packets.PacketError('container-export-binding-drift')
        packets._sha(manifest['patch_sha256']); packets._sha(manifest['evidence_sha256'])
        patch = self._read(binding, 'patch', min(limit, packets.MAX_PATCH))
        if packets.digest(patch) != manifest['patch_sha256']:
            raise packets.PacketError('container-export-digest-drift')
        supervisors.validate_patch(patch)
        return {'binding': binding, 'patch': patch, 'patch_sha256': manifest['patch_sha256']}


    def isolation_adapter(self, binding, descriptor):
        """Host-only captured adapter for an explicit synthetic fixture store.

        This is not registered globally, cannot select another container and
        never signals/stops a writer. Running may be isolated but is not stopped.
        Reconstruct it from retained protected binding/descriptor facts on restart.
        """
        backend = self
        captured_binding, captured_descriptor = copy.deepcopy(binding), copy.deepcopy(descriptor)
        expected = {'packet_id': binding['packet_id'], 'attempt_id': binding['attempt_id'],
            'generation': binding['generation'], 'identity_sha256': binding['identity_sha256'],
            'target_sha256': binding['target_sha256'], 'checkpoint_sha256': binding['predecessor_sha256']}
        class SyntheticIsolation:
            synthetic_only = True
            def readback_isolation(self, request):
                if request != expected:
                    raise packets.PacketError('synthetic-isolation-binding-drift')
                observed = backend._observed(captured_binding, captured_descriptor)
                now = int(time.time())
                return {**request, 'schema_version': 1, 'status': 'isolated', 'external_effects': 'excluded',
                    'evidence_sha256': packets.digest(packets.canonical({'descriptor': captured_descriptor,
                        'inspect': observed})), 'observed_at': now, 'expires_at': now+30}
        return SyntheticIsolation()


class OneShotSyntheticContainerBackend(SyntheticContainerBackend):
    """Host-only persistent root-latch fixture; still no production qualification."""
    requires_runtime_bootstrap = True

    def __init__(self, *args, launcher_fault='none', **kwargs):
        super().__init__(*args, **kwargs)
        if launcher_fault not in launcher.FAULTS:
            raise packets.PacketError('fixed-launcher-fault-required')
        self.launcher_fault = launcher_fault
        self.policy_sha256 = packets.digest(packets.canonical({'base_policy':self.policy_sha256,
            'launcher_sha256':launcher.contract_digest(),'control_archive_sha256':ARCHIVE_CONTRACT_SHA256,
            'launcher_fault':launcher_fault,'control_driver':'local','root_caps':['SETGID','SETPCAP','SETUID']}))
        self.backend_id = 'synthetic-container-oneshot-v1'
        self.preparing = {}

    def _volume(self, binding, name, expected_sha=None):
        value = self.engine.volume(name)
        expected_labels = {**self._labels(binding),'dev.codex.control':'true'}
        if (type(value) is not dict or value.get('Name') != name or value.get('Driver') != 'local'
                or value.get('Options') not in (None,{}) or value.get('Scope') != 'local'
                or value.get('Labels') != expected_labels or type(value.get('CreatedAt')) is not str
                or type(value.get('Mountpoint')) is not str):
            raise packets.PacketError('control-volume-policy-drift')
        sha = packets.digest(packets.canonical(value))
        if expected_sha is not None and sha != expected_sha:
            raise packets.PacketError('control-volume-identity-drift')
        return sha

    def prepare(self, binding, predecessor_patch):
        self._binding(binding)
        name = 'control-'+binding['runtime_id']; nonce = packets.digest(os.urandom(32))
        self.preparing[binding['runtime_id']] = {'name':name,'nonce':nonce}
        options = ['volume','create','--driver','local']
        for key,value in sorted({**self._labels(binding),'dev.codex.control':'true'}.items()):
            options += ['--label',key+'='+value]
        result = self.engine.command(*options,name).decode()
        if result != name:
            raise packets.PacketError('control-volume-create-unknown')
        volume_sha = self._volume(binding,name)
        descriptor = super().prepare(binding, predecessor_patch)
        descriptor.update(schema_version=2, control_volume={'name':name,'identity_sha256':volume_sha},
            nonce=nonce,launcher_sha256=launcher.contract_digest())
        return descriptor

    def _create_options(self, binding):
        options = super()._create_options(binding)
        context = self.preparing[binding['runtime_id']]
        options[options.index('--user=65534:65534')] = '--user=0:0'
        # Additional root caps exist only for the fixed launcher drop sequence.
        options[2:2] = ['--cap-add=SETGID','--cap-add=SETPCAP','--cap-add=SETUID']
        position = options.index('--entrypoint=/usr/local/bin/python3')
        options[position:position] = ['--mount', 'type=volume,src='+context['name']+',dst=/control,volume-nocopy']
        options[-1] = launcher.render(binding,context['name'],context['nonce'],self.worker,self.launcher_fault)
        return options

    def _validate_policy(self, observed, binding, descriptor=None):
        if descriptor is None:
            context = self.preparing[binding['runtime_id']]
            name,nonce = context['name'],context['nonce']
        else:
            if descriptor['schema_version'] != 2 or descriptor['launcher_sha256'] != launcher.contract_digest():
                raise packets.PacketError('root-launcher-identity-drift')
            name,nonce = descriptor['control_volume']['name'],descriptor['nonce']
            self._volume(binding,name,descriptor['control_volume']['identity_sha256'])
        mounts = observed['Mounts']; host = observed['HostConfig']; config = observed['Config']
        control = [mount for mount in mounts if mount.get('Destination') == '/control']
        controls = [mount for mount in host.get('Mounts',[]) if mount.get('Target') == '/control']
        if (len(mounts)!=2 or len(control)!=1 or control[0].get('Type')!='volume' or control[0].get('Name')!=name
                or control[0].get('Driver')!='local' or control[0].get('RW') is not True
                or control[0].get('Source')!=self.engine.volume(name)['Mountpoint']
                or control[0].get('Propagation') not in ('',None)
                or len(host.get('Mounts',[]))!=2 or len(controls)!=1 or controls[0].get('Type')!='volume' or controls[0].get('Source')!=name
                or controls[0].get('ReadOnly',False) is not False or controls[0].get('VolumeOptions')!={'NoCopy':True}
                or config['User']!='0:0' or sorted(host['CapAdd'] or [])!=['CAP_SETGID','CAP_SETPCAP','CAP_SETUID']
                or config['Cmd']!=['-I','-c',launcher.render(binding,name,nonce,self.worker,self.launcher_fault)]):
            raise packets.PacketError('root-launcher-policy-drift')
        adjusted = copy.deepcopy(observed)
        adjusted['Mounts'] = [mount for mount in mounts if mount.get('Destination')!='/control']
        adjusted['HostConfig']['CapAdd'] = None; adjusted['Config']['User'] = '65534:65534'
        adjusted['Config']['Cmd'] = ['-I','-c',WORKERS[self.worker]]
        super()._validate_policy(adjusted,binding)

    def bootstrap_input(self, binding, descriptor):
        self._observed(binding,descriptor)
        return packets.canonical({'schema_version':1,'binding':binding,'nonce':descriptor['nonce'],
            'volume':descriptor['control_volume']['name'],'descriptor_sha256':packets.digest(packets.canonical(descriptor)),
            'container_id':descriptor['container_id'],'launcher_sha256':descriptor['launcher_sha256']})

    def _bootstrap_record(self, binding, descriptor, *, stage):
        fd = self._packet_fd()
        try:
            ledger = self.store._read(fd); record = ledger['supervisors'][binding['attempt_id']]
            self.store._supervisor_fence(ledger,binding['attempt_id'],ledger['revision'],packets.digest(packets.canonical(record)))
            if record['schema_version']!=4 or record['bootstrap'] is None or record['bootstrap']['stage']!=stage:
                raise packets.PacketError('control-bootstrap-stage-drift')
            if stage=='start-intent':
                self.store._bootstrap_receipt(fd,record)
            return record
        finally: os.close(fd)

    def bootstrap(self, binding, descriptor, input_bytes):
        record = self._bootstrap_record(binding,descriptor,stage='intent')
        if packets.digest(input_bytes)!=record['bootstrap']['input_sha256'] or input_bytes!=self.bootstrap_input(binding,descriptor):
            raise packets.PacketError('control-input-binding-drift')
        observed = self._observed(binding,descriptor)
        if observed['State']['Status']!='created' or observed['State']['Running'] is not False:
            raise packets.PacketError('control-bootstrap-not-created')
        cid = descriptor['container_id']
        archive.read_empty_control_directory(self.engine.archive('container','cp',cid+':/control','-'))
        self.engine.archive('container','cp','-',cid+':/control',input_bytes=archive.build_control_file('input.json',input_bytes))
        raw = archive.read_control_file(self.engine.archive('container','cp',cid+':/control/input.json','-'),'input.json')
        if raw!=input_bytes:
            raise packets.PacketError('control-input-readback-drift')
        self._observed(binding,descriptor)
        return {'schema_version':1,'descriptor_sha256':packets.digest(packets.canonical(descriptor)),
            'input_sha256':packets.digest(input_bytes),'volume_sha256':descriptor['control_volume']['identity_sha256']}

    def launch(self, binding, descriptor):
        record = self._bootstrap_record(binding,descriptor,stage='start-intent')
        raw = archive.read_control_file(self.engine.archive('container','cp',descriptor['container_id']+':/control/input.json','-'),'input.json')
        if packets.digest(raw)!=record['bootstrap']['input_sha256'] or raw!=self.bootstrap_input(binding,descriptor):
            raise packets.PacketError('control-input-readback-drift')
        super().launch(binding,descriptor)

    def inspect(self, binding, descriptor):
        observed = self._observed(binding,descriptor); state = observed['State']
        result = {'binding':binding,'runtime_identity_sha256':packets.digest(packets.canonical(binding)),
            'state':'unknown','external_effects':'excluded','evidence_sha256':packets.digest(packets.canonical(observed))}
        if (state['Status']!='exited' or state['Running'] is not False or state['Restarting'] is not False
                or state['Paused'] is not False or state['Dead'] is not False or type(state['Pid']) is not int or state['Pid']!=0
                or type(state['ExitCode']) is not int or state['ExitCode']!=0
                or type(observed['RestartCount']) is not int or observed['RestartCount']!=0
                or state['StartedAt']=='0001-01-01T00:00:00Z' or state['FinishedAt']=='0001-01-01T00:00:00Z'):
            return result
        record = self._bootstrap_record(binding,descriptor,stage='start-intent')
        cid = descriptor['container_id']
        raw_input = archive.read_control_file(self.engine.archive('container','cp',cid+':/control/input.json','-'),'input.json')
        claim_raw = archive.read_control_file(self.engine.archive('container','cp',cid+':/control/claim.json','-'),'claim.json')
        completion_raw = archive.read_control_file(self.engine.archive('container','cp',cid+':/control/completion.json','-'),'completion.json')
        value = archive.read_control_json(raw_input); claim = archive.read_control_json(claim_raw); completion = archive.read_control_json(completion_raw)
        expected_claim={'schema_version':1,'input_sha256':packets.digest(raw_input),'input':value}
        expected_completion={'schema_version':1,'claim_sha256':packets.digest(claim_raw),'input_sha256':packets.digest(raw_input),'input':value,'worker_status':0}
        if (raw_input!=self.bootstrap_input(binding,descriptor) or packets.digest(raw_input)!=record['bootstrap']['input_sha256']
                or claim!={'schema_version':1,'input_sha256':packets.digest(raw_input),'input':value}
                or completion!={'schema_version':1,'claim_sha256':packets.digest(claim_raw),'input_sha256':packets.digest(raw_input),'input':value,'worker_status':0}
                or claim_raw!=packets.canonical(expected_claim) or completion_raw!=packets.canonical(expected_completion)):
            raise packets.PacketError('control-completion-binding-drift')
        if self._observed(binding,descriptor)!=observed:
            raise packets.PacketError('control-container-changed-during-read')
        result['state']='stopped'
        result['evidence_sha256']=packets.digest(packets.canonical({'descriptor':descriptor,'claim_sha256':packets.digest(claim_raw),
            'completion_sha256':packets.digest(completion_raw),'engine_state':state}))
        return result
