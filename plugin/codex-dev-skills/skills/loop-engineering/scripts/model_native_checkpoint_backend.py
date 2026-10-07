"""Explicit fixed anonymous native checkpoint fixture, never a production adapter."""
from __future__ import annotations
import copy
import hashlib
import os
import pathlib
import stat
import sys

import model_container_backend as containers
import model_container_launcher as launcher
import model_packet_store as packets
import model_packet_integrator as integration
import model_packet_supervisor as supervisors

CONTRACT_SHA256 = packets.digest(pathlib.Path(__file__).read_bytes())
IMAGE = 'sha256:916619b289581c9a4f2941745a09b2934cee4bd354049355b4d4d53485d67573'
CASES = frozenset({'checkpoint', 'quarantine', 'claim-replay'})
EXECUTION_CASES = CASES | {'successor-checkpoint'}
GUEST_SCRIPT = 'scripts/model_native_checkpoint_fixture.py'
HOST_SCRIPT = 'scripts/verify-model-native-checkpoint.py'
FIXED_PATCH = integration.NATIVE_UPDATE_PATCH
TMPFS = 'rw,noexec,nosuid,nodev,size=16m,mode=0700,uid=65534,gid=65534'
BINARY_BYTES = 247459224
BINARY_SHA = '54a834b6b16d8a01ff80f7f9cee4aedec35a61c90379e088792623bf1b4c1e3d'
SOURCE_FILES = (
    'scripts/verify-model-packet-integrator.py',
    *('skills/loop-engineering/scripts/' + name + '.py' for name in (
        'agent_qualification', 'model_packet_store', 'model_packet_supervisor',
        'model_packet_integrator', 'model_container_backend', 'model_container_launcher',
        'model_control_archive', 'model_packet_governance', 'agent_routing', 'model_failover',
        'profile_preflight', 'local_model_mapping', 'model_packet_lifecycle',
        'model_packet_preparation', 'model_packet_bootstrap', 'model_packet_native', 'model_native_host_control')),
    'scripts/verify-model-app-server.py', 'scripts/verify-model-tool-boundary.py',
    'scripts/model_probe_tools.py',
    'skills/loop-engineering/scripts/model_app_server_transport.py',
    'skills/loop-engineering/scripts/model_app_server_metadata.py',
    'scripts/verify-model-app-server-container.py', 'scripts/model_app_server_container_fixture.py',
    'scripts/verify-model-external-bootstrap.py', 'scripts/model_external_bootstrap_fixture.py',
    'skills/loop-engineering/scripts/model_native_checkpoint_backend.py', GUEST_SCRIPT, HOST_SCRIPT)


def identity(value):
    return [value.st_dev, value.st_ino, value.st_uid, value.st_gid, value.st_mode,
            value.st_nlink, value.st_size, value.st_mtime_ns, value.st_ctime_ns]


def read_file(path, limit, mode):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except OSError as error:
        raise packets.PacketError('native-capture-file-unavailable') from error
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) != mode or before.st_size > limit):
            raise packets.PacketError('native-capture-file-rejected')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(fd)
        if identity(before) != identity(after) or identity(after) != identity(os.lstat(path)):
            raise packets.PacketError('native-capture-file-drift')
        os.lseek(fd, 0, os.SEEK_SET)
        raw = os.read(fd, limit + 1) if limit <= 1048576 else None
        if raw is not None and len(raw) != after.st_size:
            raise packets.PacketError('native-capture-short-read')
        return raw, {'sha256': digest, 'identity': identity(after)}
    finally:
        os.close(fd)


def inspect_tree(root, files, *, private):
    """Closed inventory and stable inode metadata, including every directory."""
    mode = 0o700 if private else 0o555
    directories = {}; actual = set()
    for directory, dirs, names in os.walk(root, followlinks=False):
        value = os.lstat(directory)
        if (not stat.S_ISDIR(value.st_mode) or value.st_uid != os.getuid()
                or stat.S_IMODE(value.st_mode) != mode):
            raise packets.PacketError('native-capture-directory-rejected')
        directories[str(pathlib.Path(directory).relative_to(root))] = identity(value)
        for name in dirs:
            if (pathlib.Path(directory) / name).is_symlink():
                raise packets.PacketError('native-capture-directory-link')
        actual.update(str((pathlib.Path(directory) / name).relative_to(root)) for name in names)
    if actual != set(files):
        raise packets.PacketError('native-capture-inventory-drift')
    rows = {}
    for name in sorted(files):
        binary = name == 'codex'
        _, rows[name] = read_file(root / name, BINARY_BYTES if binary else 1048576,
                                 0o555 if binary else 0o600 if private else 0o444)
        if binary and (rows[name]['identity'][6] != BINARY_BYTES or rows[name]['sha256'] != BINARY_SHA):
            raise packets.PacketError('native-binary-fingerprint-drift')
    # Detect a directory replaced or an extra file appearing during inventory.
    for name, before in directories.items():
        if identity(os.lstat(root / name)) != before:
            raise packets.PacketError('native-capture-directory-drift')
    return {'directories': directories, 'files': rows}


def validate_capsule(root, reference):
    """Only the host-created protected capsule reference can authorize this capture."""
    raw, actual = read_file(root / 'capsule.json', 1048576, 0o600)
    if actual != reference:
        raise packets.PacketError('native-capsule-reference-drift')
    value = containers._json(raw)
    if (type(value) is not dict or set(value) != {'schema_version', 'root', 'host', 'guest'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or identity(os.lstat(root)) != value['root'] or stat.S_IMODE(os.lstat(root).st_mode) != 0o700
            or os.lstat(root).st_uid != os.getuid() or not stat.S_ISDIR(os.lstat(root).st_mode)):
        raise packets.PacketError('native-capsule-schema-drift')
    for name, private in (('host', True), ('guest', False)):
        files = set(SOURCE_FILES) | ({'codex', 'guest-manifest.json'} if not private else set())
        if inspect_tree(root / name, files, private=private) != value[name]:
            raise packets.PacketError('native-capsule-tree-drift')
    for name in SOURCE_FILES:
        if value['host']['files'][name]['sha256'] != value['guest']['files'][name]['sha256']:
            raise packets.PacketError('native-source-pair-drift')
    return value


def validate_image_config(config):
    # Docker's image-inspect API may omit unset OCI image fields. Only unset
    # or empty User/WorkingDir have equivalent default semantics; nonempty
    # values and wrong types remain rejected. Image ID/version/Cmd stay fixed.
    if (containers._environment_map(config['Env']).get('PYTHON_VERSION') != '3.12.9'
            or config.get('Cmd') != ['python3'] or config.get('WorkingDir') not in (None, '')
            or config.get('User') not in (None, '') or config.get('OnBuild') not in (None, [])
            or config.get('Healthcheck') is not None):
        raise packets.PacketError('fixed-native-python-image-required')


class OneShotNativeFixtureBackend(containers.OneShotSyntheticContainerBackend):
    """Closed native intake recipes; descriptor v2 and supervisor v4 unchanged."""
    def __init__(self, *args, capture_root, capture_ref, native_case, **kwargs):
        if (native_case not in EXECUTION_CASES or 'worker' in kwargs or 'launcher_fault' in kwargs
                or kwargs.get('image_id') != IMAGE):
            raise packets.PacketError('fixed-native-checkpoint-recipe-required')
        self.capture_root = pathlib.Path(capture_root)
        self.capture_ref = copy.deepcopy(capture_ref)
        self.native_case = native_case
        capsule = validate_capsule(self.capture_root, self.capture_ref)
        super().__init__(*args, worker='noop', **kwargs)
        image = self.engine.image(self.image_id)
        validate_image_config(image['Config'])
        self.backend_id = 'anonymous-native-checkpoint-v1'
        self.policy_sha256 = packets.digest(packets.canonical({'base_policy': self.policy_sha256,
            'native_contract': CONTRACT_SHA256, 'recipe': native_case,
            'capsule_reference': self.capture_ref, 'capsule': capsule,
            'memory': 536870912, 'pids': 64, 'tmpfs': TMPFS,
            'guest_script': GUEST_SCRIPT, 'registry_adoption': False,
            'host_platform': sys.platform, 'fixture_source': self._fixture_source()}))

    def _fixture_source(self):
        # This experimental Darwin recipe pins the exact Docker Desktop
        # readonly-bind translation observed at creation; no alias fallback or
        # prefix normalization is accepted. Linux retains its literal path.
        source = str(self.capture_root / 'guest')
        return '/host_mnt' + source if sys.platform == 'darwin' else source

    def _capture(self):
        return validate_capsule(self.capture_root, self.capture_ref)

    def _create_options(self, binding):
        self._capture()
        options = super()._create_options(binding)
        replacements = {'--pids-limit=32': '--pids-limit=64', '--memory=128m': '--memory=512m',
            '--memory-swap=128m': '--memory-swap=512m',
            '--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m': '--tmpfs=/tmp:' + TMPFS}
        options = [replacements.get(item, item) for item in options]
        position = options.index('--entrypoint=/usr/local/bin/python3')
        options[position:position] = ['--mount', 'type=bind,src=' + str(self.capture_root / 'guest')
            + ',dst=/fixture,readonly,bind-propagation=rprivate']
        context = self.preparing[binding['runtime_id']]
        options[-1] = launcher.render_native(binding, context['name'], context['nonce'], self.native_case)
        return options

    def _validate_policy(self, observed, binding, descriptor=None):
        self._capture()
        context = self.preparing.get(binding['runtime_id']) if descriptor is None else {
            'name': descriptor['control_volume']['name'], 'nonce': descriptor['nonce']}
        try:
            host, config = observed['HostConfig'], observed['Config']
            mounts = observed['Mounts']; fixture = [m for m in mounts if m['Destination'] == '/fixture']
            expected_mounts = [
                {'Type':'bind', 'Source':str(self._workspace(binding)), 'Target':'/workspace',
                    'BindOptions':{'Propagation':'rprivate'}},
                {'Type':'volume', 'Source':context['name'], 'Target':'/control', 'VolumeOptions':{'NoCopy':True}},
                {'Type':'bind', 'Source':self._fixture_source(), 'Target':'/fixture',
                    'ReadOnly':True, 'BindOptions':{'Propagation':'rprivate'}}]
            if (len(mounts) != 3 or len(fixture) != 1
                    or fixture[0] != {'Type':'bind','Source':self._fixture_source(),
                        'Destination':'/fixture','Mode':'','RW':False,'Propagation':'rprivate'}
                    or sorted(host['Mounts'],key=lambda m:m['Target']) != sorted(expected_mounts,key=lambda m:m['Target'])
                    or type(host['Memory']) is not int or host['Memory'] != 536870912
                    or type(host['MemorySwap']) is not int or host['MemorySwap'] != 536870912
                    or type(host['PidsLimit']) is not int or host['PidsLimit'] != 64
                    or host['Tmpfs'] != {'/tmp':TMPFS}
                    or config['Cmd'] != ['-I','-c',launcher.render_native(binding,context['name'],context['nonce'],self.native_case)]):
                raise packets.PacketError('native-container-policy-drift')
            # Every changed field has been independently compared above. Reuse
            # the complete unchanged root-cap/volume/network/image validator.
            adjusted = copy.deepcopy(observed)
            adjusted['Mounts'] = [m for m in mounts if m['Destination'] != '/fixture']
            adjusted['HostConfig']['Mounts'] = [m for m in host['Mounts'] if m['Target'] != '/fixture']
            adjusted['HostConfig'].update(Memory=134217728,MemorySwap=134217728,PidsLimit=32,
                Tmpfs={'/tmp':'rw,noexec,nosuid,nodev,size=8m'})
            adjusted['Config']['Cmd'] = ['-I','-c',launcher.render(binding,context['name'],context['nonce'],'noop')]
            super()._validate_policy(adjusted,binding,descriptor)
        except (KeyError, TypeError, IndexError) as error:
            raise packets.PacketError('native-container-policy-incomplete') from error

    def export_patch(self, binding, limit, descriptor):
        if self._walk(binding, descriptor) != {'example.txt':b'new\n','remove.txt':b'delete\n'}:
            raise packets.PacketError('native-postimage-not-fixed')
        reply = super().export_patch(binding, limit, descriptor)
        if reply['patch'] != FIXED_PATCH:
            raise packets.PacketError('native-checkpoint-patch-drift')
        return reply

    def read_sealed_patch(self, binding, limit, descriptor):
        # Lost export replies must not bypass the fixed native intake contract.
        # Parent validates the original descriptor/stop/bootstrap/export seal.
        reply = super().read_sealed_patch(binding, limit, descriptor)
        if reply['patch'] != FIXED_PATCH:
            raise packets.PacketError('native-checkpoint-patch-drift')
        return reply


class NativeFixturePacketIntegrator(integration.PacketIntegrator):
    """Separate exact-type port for the captured, fixed anonymous native fixture.

    No generic backend, proxy, model grant or user source is accepted. The
    original PacketIntegrator constructor retains its synthetic-only gate.
    Inherited synchronous authority/ledger/lock/recovery gates remain in force.
    """
    def __init__(self,source,governance,supervisor):
        if (type(source)is not integration.SyntheticSource
                or type(governance)is not integration.FixtureGovernance or governance.source is not source):
            raise packets.PacketError('trusted-synthetic-integrator-capabilities-required')
        if (type(supervisor)is not supervisors.PacketSupervisor
                or type(supervisor.backend)is not OneShotNativeFixtureBackend
                or supervisor.backend.native_case!='checkpoint'):
            raise packets.PacketError('fixed-native-source-candidate-required')
        supervisor.backend._capture()
        self.source,self.governance,self.supervisor=source,governance,supervisor
        self.store=supervisor.store

    def _candidate_locked(self,packet_fd,ledger,attempt):
        value=self.supervisor.backend
        if type(value)is not OneShotNativeFixtureBackend or value.native_case!='checkpoint':
            raise packets.PacketError('fixed-native-source-candidate-required')
        value._capture()
        record,candidate=super()._candidate_locked(packet_fd,ledger,attempt)
        if (candidate['patch']!=FIXED_PATCH or any(candidate['binding'][key]!=expected
                for key,expected in self.source.requirements('native-update').items())):
            raise packets.PacketError('fixed-native-source-candidate-required')
        return record,candidate
