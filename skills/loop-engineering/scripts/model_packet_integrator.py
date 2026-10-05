"""Host-created synthetic source capability and synchronous sole integrator.

No registry, model JSON, user repository, arbitrary source path, quality approval
flag or asynchronous writer is accepted. The advisory lock serializes this
trusted fixture's synchronous writers; it is NOT operating-system isolation.
Synthetic validation/review artifacts are fixed-content fixture gates, not a
formal independent code-review verdict or production authority.
"""
from __future__ import annotations
import contextlib
import fcntl
import json
import os
import pathlib
import re
import selectors
import time
import stat
import subprocess
import tempfile
import uuid

import agent_qualification as trust
import model_packet_store as packets
import model_container_backend as containers
import model_packet_supervisor as supervisors

_TOKEN=object()
MAX_FILE=262144
MAX_TREE=1048576
SOURCE_PATHS=frozenset({'example.txt','remove.txt','added.txt'})
SCOPE=['added.txt','example.txt']
FIXED_PATCH=(b'diff --git a/added.txt b/added.txt\nnew file mode 100644\n--- /dev/null\n+++ b/added.txt\n@@ -0,0 +1 @@\n+added\n'
             b'diff --git a/example.txt b/example.txt\n--- a/example.txt\n+++ b/example.txt\n@@ -1 +1 @@\n-old\n+new\n')
NATIVE_UPDATE_PATCH=b'diff --git a/example.txt b/example.txt\n--- a/example.txt\n+++ b/example.txt\n@@ -1 +1 @@\n-old\n+new\n'
CONTRACT_SHA256=packets.digest(pathlib.Path(__file__).read_bytes())


def _fixed_patch(recipe):
    if recipe=='add-update': return FIXED_PATCH
    if recipe=='native-update': return NATIVE_UPDATE_PATCH
    if recipe=='noop': return b''
    raise packets.PacketError('fixed-integrator-recipe-required')


def _fixed_postimage(recipe):
    _fixed_patch(recipe)
    if recipe=='add-update': return {**containers.BASELINE,'example.txt':b'new\n','added.txt':b'added\n'}
    if recipe=='native-update': return {**containers.BASELINE,'example.txt':b'new\n'}
    return containers.BASELINE


def _fixed_scope(recipe):
    _fixed_patch(recipe)
    return ['example.txt'] if recipe=='native-update' else SCOPE


def _identity(value):
    return packets.digest(packets.canonical({'device':value.st_dev,'inode':value.st_ino,'owner':value.st_uid}))


def _regular(fd,name,limit=MAX_FILE):
    file_fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    try:
        before=os.fstat(file_fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid!=os.getuid() or before.st_nlink!=1
                or before.st_mode&0o022 or before.st_size>limit):
            raise packets.PacketError('source-regular-file-required')
        raw=bytearray()
        while len(raw)<=limit:
            chunk=os.read(file_fd,min(65536,limit+1-len(raw)))
            if not chunk: break
            raw.extend(chunk)
        after=os.fstat(file_fd); named=os.stat(name,dir_fd=fd,follow_symlinks=False)
        fields=lambda value:(value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns,value.st_uid,value.st_mode,value.st_nlink)
        if len(raw)>limit or fields(before)!=fields(after) or fields(after)!=fields(named):
            raise packets.PacketError('source-file-changed-during-read')
        return bytes(raw),stat.S_IMODE(after.st_mode)
    finally: os.close(file_fd)


def _manifest(files):
    return {name:{'sha256':packets.digest(raw),'bytes':len(raw)} for name,raw in sorted(files.items())}


def _tree(fd):
    names=os.listdir(fd)
    if len(names)>4 or any(name not in SOURCE_PATHS and name!='.git' for name in names):
        raise packets.PacketError('source-unknown-path')
    files={}; total=0
    for name in sorted(names):
        if name=='.git': continue
        raw,mode=_regular(fd,name)
        if mode!=0o644 or b'\x00' in raw or raw and not raw.endswith(b'\n'):
            raise packets.PacketError('source-text-mode-required')
        raw.decode('utf-8'); files[name]=raw; total+=len(raw)
        if total>MAX_TREE: raise packets.PacketError('source-tree-bound')
    if sorted(os.listdir(fd))!=sorted(names): raise packets.PacketError('source-tree-changed-during-read')
    return files


def _git_metadata(source_fd):
    fd=os.open('.git',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=source_fd)
    count=0; total=0; result={}
    def visit(directory,prefix):
        nonlocal count,total
        names=os.listdir(directory)
        for name in sorted(names):
            count+=1
            if count>1024 or name in {'.','..'}: raise packets.PacketError('source-git-bound')
            value=os.stat(name,dir_fd=directory,follow_symlinks=False)
            if value.st_uid!=os.getuid() or value.st_mode&0o022: raise packets.PacketError('source-git-untrusted')
            path=prefix+name
            if stat.S_ISDIR(value.st_mode):
                child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                try: visit(child,path+'/')
                finally: os.close(child)
            else:
                raw,mode=_regular(directory,name,MAX_TREE); total+=len(raw)
                if total>4*MAX_TREE: raise packets.PacketError('source-git-bound')
                result[path]={'sha256':packets.digest(raw),'mode':mode,'identity':_identity(value)}
        if sorted(os.listdir(directory))!=sorted(names): raise packets.PacketError('source-git-drift')
    try:
        trust._check(os.fstat(fd),directory=True); result['.git-identity']=_identity(os.fstat(fd)); visit(fd,'')
    finally: os.close(fd)
    return packets.digest(packets.canonical(result))


def _git(directory,*args,input_bytes=None):
    environment={'PATH':os.defpath,'HOME':str(directory),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,
        'GIT_OPTIONAL_LOCKS':'0','LC_ALL':'C','GIT_AUTHOR_DATE':'2000-01-01T00:00:00Z','GIT_COMMITTER_DATE':'2000-01-01T00:00:00Z'}
    process=subprocess.Popen(['git','--no-optional-locks','-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false',
        '-c','user.name=Synthetic Fixture','-c','user.email=synthetic@example.invalid',*args],cwd=directory,
        env=environment,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,close_fds=True,
        # This fixed command writes only the private staging tree. Git's new
        # text files must retain 0644 even when the host capture mask is 077.
        # Do not change the host mask or masks of other Git commands.
        umask=0o022 if args==('apply','--no-index','--whitespace=nowarn','-') else -1)
    selector=selectors.DefaultSelector(); output=bytearray(); pending=memoryview(input_bytes or b''); offset=0
    deadline=time.monotonic()+10
    try:
        os.set_blocking(process.stdout.fileno(),False); selector.register(process.stdout,selectors.EVENT_READ)
        if pending:
            os.set_blocking(process.stdin.fileno(),False); selector.register(process.stdin,selectors.EVENT_WRITE)
        else: process.stdin.close()
        while selector.get_map():
            remaining=deadline-time.monotonic()
            if remaining<=0: raise packets.PacketError('trusted-fixture-git-timeout')
            for key,_ in selector.select(remaining):
                if key.fileobj is process.stdout:
                    chunk=os.read(process.stdout.fileno(),min(8192,65537-len(output)))
                    if not chunk: selector.unregister(process.stdout)
                    else:
                        output.extend(chunk)
                        if len(output)>65536: raise packets.PacketError('trusted-fixture-git-output-bound')
                else:
                    written=os.write(process.stdin.fileno(),pending[offset:offset+8192]); offset+=written
                    if offset==len(pending): selector.unregister(process.stdin); process.stdin.close()
        remaining=deadline-time.monotonic()
        if remaining<=0 or process.wait(timeout=remaining): raise packets.PacketError('trusted-fixture-git-rejected')
        return bytes(output)
    finally:
        selector.close()
        if process.poll() is None: process.kill(); process.wait(timeout=2)
        if not process.stdin.closed: process.stdin.close()
        process.stdout.close()



def _save(fd,name,raw):
    try: output=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
    except FileExistsError:
        if _regular(fd,name,65536)[0]!=raw: raise packets.PacketError('fixture-artifact-conflict')
        return
    with os.fdopen(output,'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    os.fsync(fd)
    if _regular(fd,name,65536)[0]!=raw: raise packets.PacketError('fixture-artifact-readback-failed')


class SyntheticSource:
    def __init__(self,root,descriptor,token):
        if token is not _TOKEN: raise packets.PacketError('host-created-source-capability-required')
        self.root,self.descriptor,self._token=root,descriptor,token
        self.source=root/'source'
        self.descriptor_sha256=packets.digest(packets.canonical(descriptor))

    @classmethod
    def create(cls,private_root):
        private_root=pathlib.Path(private_root)
        fd=trust._directory(private_root)
        try:
            if os.fstat(fd).st_mode&0o077: raise packets.PacketError('fixture-root-must-be-private')
        finally: os.close(fd)
        root=pathlib.Path(tempfile.mkdtemp(prefix='source-fixture-',dir=private_root)); root.chmod(0o700)
        (root/'control').mkdir(mode=0o700); (root/'source').mkdir(mode=0o700); (root/'empty-template').mkdir(mode=0o700)
        source=root/'source'
        for name,raw in containers.BASELINE.items():
            with (source/name).open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            (source/name).chmod(0o644)
        _git(root,'init','--initial-branch=fixture','--template='+str(root/'empty-template'),str(source))
        _git(source,'add','--','example.txt','remove.txt'); _git(source,'commit','--no-verify','-m','synthetic baseline')
        source_fd=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        control=trust._directory(root/'control')
        try:
            lock=os.open('writer.lock',os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=control)
            lock_identity=_identity(os.fstat(lock)); os.fsync(lock); os.close(lock)
            files=_tree(source_fd); head=_git(source,'rev-parse','HEAD').strip().decode()
            if _git(source,'status','--porcelain=v1','-z','--untracked-files=all'): raise packets.PacketError('fixture-not-clean')
            index_fd=os.open('.git',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=source_fd)
            try: index_sha=packets.digest(_regular(index_fd,'index',MAX_TREE)[0])
            finally: os.close(index_fd)
            descriptor={'schema_version':1,'kind':'host-created-exclusive-synthetic-source','source_id':'source-'+uuid.uuid4().hex,
                'source_identity_sha256':_identity(os.fstat(source_fd)),'lock_identity_sha256':lock_identity,
                'head':head,'index_sha256':index_sha,'git_metadata_sha256':_git_metadata(source_fd),
                'preimage':_manifest(files),'preimage_sha256':packets.digest(packets.canonical(_manifest(files)))}
            _save(control,'source.json',packets.canonical(descriptor))
        finally: os.close(source_fd); os.close(control)
        return cls(root,descriptor,_TOKEN)

    @classmethod
    def reopen(cls,root,expected_descriptor_sha256):
        root=pathlib.Path(root); packets._sha(expected_descriptor_sha256)
        if not re.fullmatch(r'source-fixture-[A-Za-z0-9_]+',root.name): raise packets.PacketError('synthetic-source-reference-required')
        fd=trust._directory(root/'control')
        try: raw=_regular(fd,'source.json',65536)[0]
        finally: os.close(fd)
        if packets.digest(raw)!=expected_descriptor_sha256: raise packets.PacketError('source-reference-drift')
        descriptor=json.loads(raw,object_pairs_hook=trust._pairs)
        if (type(descriptor)is not dict or set(descriptor)!={'schema_version','kind','source_id','source_identity_sha256',
                'lock_identity_sha256','head','index_sha256','git_metadata_sha256','preimage','preimage_sha256'}
                or type(descriptor['schema_version'])is not int or descriptor['schema_version']!=1
                or descriptor['kind']!='host-created-exclusive-synthetic-source'):
            raise packets.PacketError('invalid-synthetic-source-descriptor')
        if (not re.fullmatch(r'source-[a-f0-9]{32}',descriptor['source_id'])
                or not re.fullmatch(r'[a-f0-9]{40}',descriptor['head'])
                or descriptor['preimage']!=_manifest(containers.BASELINE)
                or descriptor['preimage_sha256']!=packets.digest(packets.canonical(descriptor['preimage']))):
            raise packets.PacketError('invalid-synthetic-source-descriptor')
        for key in ['source_identity_sha256','lock_identity_sha256','index_sha256','git_metadata_sha256']:
            packets._sha(descriptor[key])
        return cls(root,descriptor,_TOKEN)

    @contextlib.contextmanager
    def _locked(self):
        if self._token is not _TOKEN: raise packets.PacketError('host-created-source-capability-required')
        control=trust._directory(self.root/'control'); lock=None; source=None
        try:
            descriptor_raw=_regular(control,'source.json',65536)[0]
            if packets.digest(packets.canonical(self.descriptor))!=self.descriptor_sha256 or packets.digest(descriptor_raw)!=self.descriptor_sha256: raise packets.PacketError('source-reference-drift')
            lock=os.open('writer.lock',os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=control)
            trust._check(os.fstat(lock))
            if (os.fstat(lock).st_nlink!=1 or _identity(os.fstat(lock))!=self.descriptor['lock_identity_sha256']
                    or _identity(os.stat('writer.lock',dir_fd=control,follow_symlinks=False))!=self.descriptor['lock_identity_sha256']):
                raise packets.PacketError('source-lock-identity-drift')
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise packets.PacketError('source-writer-busy') from None
            root=trust._directory(self.root)
            try: source=os.open('source',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
            finally: os.close(root)
            trust._check(os.fstat(source),directory=True)
            if _identity(os.fstat(source))!=self.descriptor['source_identity_sha256']: raise packets.PacketError('source-physical-identity-drift')
            yield source,control
        finally:
            if source is not None: os.close(source)
            if lock is not None: os.close(lock)
            os.close(control)

    def snapshot(self,fd):
        root=trust._directory(self.root)
        try:
            named=os.stat('source',dir_fd=root,follow_symlinks=False)
            if _identity(named)!=self.descriptor['source_identity_sha256'] or not stat.S_ISDIR(named.st_mode):
                raise packets.PacketError('source-physical-identity-drift')
        finally: os.close(root)
        files=_tree(fd)
        if _git_metadata(fd)!=self.descriptor['git_metadata_sha256']: raise packets.PacketError('source-head-index-or-metadata-drift')
        head=_git(self.source,'rev-parse','HEAD').strip().decode()
        git_fd=os.open('.git',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
        try: index=packets.digest(_regular(git_fd,'index',MAX_TREE)[0])
        finally: os.close(git_fd)
        if head!=self.descriptor['head'] or index!=self.descriptor['index_sha256']: raise packets.PacketError('source-head-index-drift')
        return files

    def requirements(self,recipe):
        _fixed_patch(recipe)
        return {'source_sha256':containers.source_digest(),
            'scope_sha256':packets.digest(packets.canonical({'schema_version':1,'paths':_fixed_scope(recipe),'ownership':'exclusive-synthetic-source'})),
            'acceptance_sha256':packets.digest(packets.canonical({'schema_version':1,'recipe':recipe,'kind':'synthetic-fixed-content-acceptance'}))}


class FixtureAuthority:
    def __init__(self,authority_id,sha,token):
        if token is not _TOKEN: raise packets.PacketError('host-issued-fixture-authority-required')
        self.authority_id,self.sha,self._token=authority_id,sha,token


def _candidate_identity(candidate):
    keys={'outcome','attempt_id','checkpoint_sha256','binding','patch_sha256','evidence_sha256','patch'}
    if type(candidate)is not dict or set(candidate)!=keys or candidate['outcome']!='integration-candidate':
        raise packets.PacketError('sealed-candidate-required')
    return packets.digest(packets.canonical({key:value for key,value in candidate.items() if key!='patch'}))


class FixtureGovernance:
    def __init__(self,source):
        if type(source)is not SyntheticSource or source._token is not _TOKEN: raise packets.PacketError('host-created-source-capability-required')
        self.source=source

    def _expected(self,candidate,recipe):
        requirements=self.source.requirements(recipe)
        if any(candidate['binding'][key]!=value for key,value in requirements.items()): raise packets.PacketError('fixture-scope-acceptance-drift')
        expected=_fixed_patch(recipe)
        if candidate['patch']!=expected or candidate['patch_sha256']!=packets.digest(expected): raise packets.PacketError('synthetic-fixed-content-gate-failed')
        return requirements

    def issue(self,supervisor,attempt_id,*,recipe):
        with self.source._locked() as (fd,control):
            requirements=self.source.requirements(recipe)
            candidate=supervisor.admit_candidate(attempt_id,**requirements)
            files=self.source.snapshot(fd)
            if _manifest(files)!=self.source.descriptor['preimage']: raise packets.PacketError('source-not-clean-preimage')
            self._expected(candidate,recipe)
            authority_id='authority-'+uuid.uuid4().hex; candidate_sha=_candidate_identity(candidate)
            gate_binding={'candidate_sha256':candidate_sha,'source_descriptor_sha256':self.source.descriptor_sha256,
                'scope_sha256':requirements['scope_sha256'],'acceptance_sha256':requirements['acceptance_sha256'],
                'recipe':recipe,'validator_sha256':CONTRACT_SHA256,'expected_patch_sha256':packets.digest(candidate['patch'])}
            # Actual fixed-content checks above precede independent saved gates.
            validation={'schema_version':1,'kind':'synthetic-validation-fixture','binding':gate_binding,'result':'fixed-content-matched'}
            review={'schema_version':1,'kind':'synthetic-review-fixture','binding':gate_binding,'result':'fixed-scope-matched-no-production-review-claim'}
            validation_raw=packets.canonical(validation); review_raw=packets.canonical(review)
            validation_sha=packets.digest(validation_raw); review_sha=packets.digest(review_raw)
            _save(control,'validation-'+validation_sha+'.json',validation_raw); _save(control,'review-'+review_sha+'.json',review_raw)
            authority={'schema_version':1,'authority_id':authority_id,'kind':'host-issued-synthetic-source-writer',
                'owner':'synthetic-sole-integrator','scope_paths':_fixed_scope(recipe),'source_descriptor_sha256':self.source.descriptor_sha256,
                'candidate_sha256':candidate_sha,'scope_sha256':requirements['scope_sha256'],'acceptance_sha256':requirements['acceptance_sha256'],
                'recipe':recipe,'validation_sha256':validation_sha,'review_sha256':review_sha,'integrator_sha256':CONTRACT_SHA256}
            raw=packets.canonical(authority); sha=packets.digest(raw)
            _save(control,authority_id+'.json',raw)
            return FixtureAuthority(authority_id,sha,_TOKEN)

    def reopen_authority(self,authority_id,expected_sha256):
        """Host-persisted opaque reference; never a model-approved JSON grant."""
        packets._id(authority_id); packets._sha(expected_sha256)
        with self.source._locked() as (_,control):
            raw=_regular(control,authority_id+'.json',65536)[0]
            if packets.digest(raw)!=expected_sha256: raise packets.PacketError('source-authority-artifact-drift')
            value=json.loads(raw,object_pairs_hook=trust._pairs)
            if type(value)is not dict or value.get('authority_id')!=authority_id or value.get('kind')!='host-issued-synthetic-source-writer':
                raise packets.PacketError('source-authority-binding-drift')
        return FixtureAuthority(authority_id,expected_sha256,_TOKEN)

    def revoke(self,authority):
        if type(authority)is not FixtureAuthority or authority._token is not _TOKEN: raise packets.PacketError('host-issued-fixture-authority-required')
        packets._id(authority.authority_id); packets._sha(authority.sha)
        with self.source._locked() as (_,control):
            _save(control,'revoked-'+authority.authority_id,packets.canonical({'authority_sha256':authority.sha}))

    def read_verified(self,control,authority,candidate):
        if type(authority)is not FixtureAuthority or authority._token is not _TOKEN: raise packets.PacketError('host-issued-fixture-authority-required')
        packets._id(authority.authority_id); packets._sha(authority.sha)
        try: os.stat('revoked-'+authority.authority_id,dir_fd=control,follow_symlinks=False)
        except FileNotFoundError: pass
        else: raise packets.PacketError('source-authority-revoked')
        raw=_regular(control,authority.authority_id+'.json',65536)[0]
        if packets.digest(raw)!=authority.sha: raise packets.PacketError('source-authority-artifact-drift')
        value=json.loads(raw,object_pairs_hook=trust._pairs)
        keys={'schema_version','authority_id','kind','owner','scope_paths','source_descriptor_sha256','candidate_sha256',
            'scope_sha256','acceptance_sha256','recipe','validation_sha256','review_sha256','integrator_sha256'}
        if (type(value)is not dict or set(value)!=keys or type(value['schema_version'])is not int or value['schema_version']!=1
                or value['authority_id']!=authority.authority_id or value['kind']!='host-issued-synthetic-source-writer'
                or value['owner']!='synthetic-sole-integrator' or value['scope_paths']!=_fixed_scope(value['recipe'])
                or value['source_descriptor_sha256']!=self.source.descriptor_sha256 or value['candidate_sha256']!=_candidate_identity(candidate)
                or value['integrator_sha256']!=CONTRACT_SHA256): raise packets.PacketError('source-authority-binding-drift')
        requirements=self._expected(candidate,value['recipe'])
        if value['scope_sha256']!=requirements['scope_sha256'] or value['acceptance_sha256']!=requirements['acceptance_sha256']:
            raise packets.PacketError('source-authority-binding-drift')
        binding={'candidate_sha256':value['candidate_sha256'],'source_descriptor_sha256':self.source.descriptor_sha256,
            'scope_sha256':value['scope_sha256'],'acceptance_sha256':value['acceptance_sha256'],'recipe':value['recipe'],
            'validator_sha256':CONTRACT_SHA256,'expected_patch_sha256':candidate['patch_sha256']}
        for kind,result,key in [('synthetic-validation-fixture','fixed-content-matched','validation_sha256'),
                                ('synthetic-review-fixture','fixed-scope-matched-no-production-review-claim','review_sha256')]:
            packets._sha(value[key]); prefix='validation-' if key=='validation_sha256' else 'review-'
            gate=_regular(control,prefix+value[key]+'.json',65536)[0]
            if packets.digest(gate)!=value[key] or gate!=packets.canonical({'schema_version':1,'kind':kind,'binding':binding,'result':result}):
                raise packets.PacketError('source-validation-review-artifact-drift')
        return value


class PacketIntegrator:
    def __init__(self,source,governance,supervisor):
        if type(source)is not SyntheticSource or type(governance)is not FixtureGovernance or governance.source is not source:
            raise packets.PacketError('trusted-synthetic-integrator-capabilities-required')
        if type(supervisor)is not supervisors.PacketSupervisor or type(supervisor.backend)is not containers.OneShotSyntheticContainerBackend:
            raise packets.PacketError('synthetic-one-shot-candidate-required')
        self.source,self.governance,self.supervisor=source,governance,supervisor
        self.store=supervisor.store

    def _candidate_locked(self,packet_fd,ledger,attempt):
        record=ledger['supervisors'].get(attempt)
        if record is None or record['schema_version']!=4 or record['stage']!='published': raise packets.PacketError('qualified-sealed-candidate-required')
        # Equivalent to PacketSupervisor._current, under the already-held lock.
        # Calling _current here would acquire the packet lock a second time.
        binding=record['binding']
        if ((record['schema_version']>=3)!=self.supervisor.descriptor_required
                or (record['schema_version']==4)!=self.supervisor.bootstrap_required):
            raise packets.PacketError('runtime-descriptor-policy-drift')
        if (binding['host_id']!=self.supervisor.host_id or binding['backend_id']!=self.supervisor.backend_id
                or binding['policy_sha256']!=self.supervisor.policy_sha256):
            raise packets.PacketError('supervisor-host-policy-drift')
        self.store._supervisor_fence(ledger,attempt,ledger['revision'],packets.digest(packets.canonical(record)))
        descriptor=self.store._runtime_descriptor(packet_fd,record); self.store._bootstrap_receipt(packet_fd,record)
        proof=self.supervisor._inspect(record['binding'],descriptor)
        if proof['evidence_sha256']!=record['evidence_sha256']: raise packets.PacketError('candidate-runtime-evidence-drift')
        patch=self.store._checkpoint_bytes(packet_fd,ledger['checkpoint'],ledger)
        if patch!=self.store._sealed_bytes(packet_fd,record) or packets.digest(patch)!=record['patch_sha256']:
            raise packets.PacketError('candidate-checkpoint-seal-drift')
        return record,{'outcome':'integration-candidate','attempt_id':attempt,'checkpoint_sha256':ledger['checkpoint'],
            'binding':record['binding'],'patch_sha256':record['patch_sha256'],'evidence_sha256':record['evidence_sha256'],'patch':patch}

    def _stage(self,files,patch):
        if type(files)is not dict or set(files)-SOURCE_PATHS or any(type(raw)is not bytes or len(raw)>MAX_FILE for raw in files.values()):
            raise packets.PacketError('source-stage-preimage-bound')
        stage=pathlib.Path(tempfile.mkdtemp(prefix='integration-stage-',dir=self.source.root/'control')); stage.chmod(0o700)
        if patch:
            containers.validate_fixed_predecessor(patch)
            targets=containers._fixed_git_numstat(patch)
            if any(target.decode() not in SCOPE for target in targets): raise packets.PacketError('source-patch-scope-rejected')
            for line in patch.splitlines():
                if line.startswith((b'deleted file mode ',b'rename ',b'copy ',b'+++ /dev/null',b'GIT binary patch',b'Binary files ')):
                    raise packets.PacketError('source-add-update-only')
        for name,raw in files.items():
            with (stage/name).open('xb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
            (stage/name).chmod(0o644)
        if patch: _git(stage,'apply','--no-index','--whitespace=nowarn','-',input_bytes=patch)
        fd=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try: post=_tree(fd)
        finally: os.close(fd)
        if not set(files)<=set(post) or any(files[name]!=post[name] for name in files if name not in SCOPE):
            raise packets.PacketError('source-deletion-or-outscope-drift')
        return post

    def _write_file(self,source_fd,name,raw,expected):
        if name not in SCOPE or type(raw)is not bytes or len(raw)>MAX_FILE: raise packets.PacketError('source-write-scope-rejected')
        try: current=_regular(source_fd,name)[0]
        except FileNotFoundError: current=None
        if current!=expected: raise packets.PacketError('source-file-preimage-drift')
        temporary='integration-'+uuid.uuid4().hex
        output=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644,dir_fd=source_fd)
        os.fchmod(output,0o644)
        with os.fdopen(output,'wb') as stream: stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary,name,src_dir_fd=source_fd,dst_dir_fd=source_fd); os.fsync(source_fd)
        if _regular(source_fd,name)[0]!=raw: raise packets.PacketError('source-write-readback-failed')

    def _result(self,intent,state,reason,files):
        return {'schema_version':1,'operation_id':intent['operation_id'],'candidate_sha256':intent['candidate_sha256'],
            'source_descriptor_sha256':intent['source_descriptor_sha256'],'state':state,'reason':reason,
            'observed_image_sha256':None if files is None else packets.digest(packets.canonical(_manifest(files))),
            'effects':'bounded-add-update' if state=='applied' else 'none' if state=='not-applied' else 'unknown'}

    def integrate(self,attempt,authority,*,operation_id):
        packets._id(operation_id); packets._id(attempt)
        with self.source._locked() as (source_fd,control):
            with self.store.locked() as packet_fd:
                ledger=self.store._read(packet_fd)
                if ledger is None: raise packets.PacketError('packet-not-prepared')
                if operation_id in ledger.get('integrations',{}):
                    if ledger['integrations'][operation_id]['attempt_id']!=attempt: raise packets.PacketError('source-integration-attempt-conflict')
                    return self._reconcile_locked(source_fd,control,packet_fd,ledger,operation_id,authority)
                record,candidate=self._candidate_locked(packet_fd,ledger,attempt)
                approved=self.governance.read_verified(control,authority,candidate)
                pre=self.source.snapshot(source_fd)
                if _manifest(pre)!=self.source.descriptor['preimage'] or _git(self.source.source,'status','--porcelain=v1','-z','--untracked-files=all'):
                    raise packets.PacketError('source-not-clean-preimage')
                post=self._stage(pre,candidate['patch'])
                scope=_fixed_scope(approved['recipe'])
                if post!=_fixed_postimage(approved['recipe']) or any(post.get(name)!=pre.get(name) for name in set(pre)|set(post) if name not in scope):
                    raise packets.PacketError('source-fixed-postimage-scope-drift')
                self.governance.read_verified(control,authority,candidate)
                if self.source.snapshot(source_fd)!=pre: raise packets.PacketError('source-preimage-drift')
                intent={'schema_version':1,'kind':'synthetic-synchronous-source-integration','operation_id':operation_id,
                    'binding':record['binding'],'candidate_sha256':_candidate_identity(candidate),
                    'checkpoint_sha256':candidate['checkpoint_sha256'],'patch_sha256':candidate['patch_sha256'],
                    'source_descriptor_sha256':self.source.descriptor_sha256,'source_identity_sha256':self.source.descriptor['source_identity_sha256'],
                    'head':self.source.descriptor['head'],'index_sha256':self.source.descriptor['index_sha256'],
                    'preimage':_manifest(pre),'postimage':_manifest(post),
                    'preimage_sha256':packets.digest(packets.canonical(_manifest(pre))), 'postimage_sha256':packets.digest(packets.canonical(_manifest(post))),
                    'authority_id':authority.authority_id,'authority_sha256':authority.sha,'validation_sha256':approved['validation_sha256'],
                    'review_sha256':approved['review_sha256'],'integrator_sha256':CONTRACT_SHA256,'scope_paths':scope,'no_effect':pre==post}
                ledger,integration=self.store._begin_integration(packet_fd,ledger,attempt,operation_id,intent,
                    expected_revision=ledger['revision'],record_sha256=packets.digest(packets.canonical(record)))
                if pre==post:
                    result=self._result(intent,'not-applied','authorized-noop',pre)
                    self.store._finish_integration(packet_fd,ledger,operation_id,'not-applied',result); return result
                ledger,integration=self.store._start_integration_write(packet_fd,ledger,operation_id)
                try:
                    current=dict(pre)
                    for name in sorted(post):
                        if post[name]!=pre.get(name):
                            if self.source.snapshot(source_fd)!=current: raise packets.PacketError('source-step-preimage-drift')
                            self.governance.read_verified(control,authority,candidate)
                            self.store._integration_fence(ledger,operation_id,ledger['revision'])
                            self._write_file(source_fd,name,post[name],pre.get(name))
                            current[name]=post[name]
                            if self.source.snapshot(source_fd)!=current: raise packets.PacketError('source-step-readback-drift')
                    observed=self.source.snapshot(source_fd)
                    if observed!=post: raise packets.PacketError('source-postimage-readback-drift')
                except Exception:
                    # Preserve uncertainty; never rollback, retry or apply again.
                    result=self._result(intent,'unknown','writer-or-readback-unknown',None)
                    self.store._finish_integration(packet_fd,ledger,operation_id,'unknown',result); return result
                result=self._result(intent,'applied','postimage-readback',observed)
                self.store._finish_integration(packet_fd,ledger,operation_id,'applied',result); return result

    def _reconcile_locked(self,source_fd,control,packet_fd,ledger,operation,authority):
        record=self.store._integration_fence(ledger,operation,ledger['revision'])
        intent=self.store._integration_intent(packet_fd,record,ledger)
        candidate_record,candidate=self._candidate_locked(packet_fd,ledger,record['attempt_id'])
        approved=self.governance.read_verified(control,authority,candidate)
        expected_post=_fixed_postimage(approved['recipe'])
        expected={'schema_version':1,'kind':'synthetic-synchronous-source-integration','operation_id':operation,
            'preimage':self.source.descriptor['preimage'],'preimage_sha256':self.source.descriptor['preimage_sha256'],
            'postimage':_manifest(expected_post),'postimage_sha256':packets.digest(packets.canonical(_manifest(expected_post))),
            'no_effect':approved['recipe']=='noop','authority_id':authority.authority_id,'authority_sha256':authority.sha,'validation_sha256':approved['validation_sha256'],
            'review_sha256':approved['review_sha256'],'source_descriptor_sha256':self.source.descriptor_sha256,
            'source_identity_sha256':self.source.descriptor['source_identity_sha256'],'integrator_sha256':CONTRACT_SHA256,
            'candidate_sha256':_candidate_identity(candidate),'checkpoint_sha256':candidate['checkpoint_sha256'],'patch_sha256':candidate['patch_sha256'],
            'binding':candidate_record['binding'],'scope_paths':_fixed_scope(approved['recipe']),'head':self.source.descriptor['head'],'index_sha256':self.source.descriptor['index_sha256']}
        if set(intent)!=set(expected) or packets.canonical(intent)!=packets.canonical(expected): raise packets.PacketError('source-integration-recovery-binding-drift')
        try: files=self.source.snapshot(source_fd)
        except Exception: files=None
        image=None if files is None else packets.digest(packets.canonical(_manifest(files)))
        if image==intent['preimage_sha256'] and (not record['writer_started'] or intent['no_effect']):
            state,reason='not-applied','authorized-noop' if intent['no_effect'] else 'durable-intent-no-write'
        elif image==intent['postimage_sha256'] and not intent['no_effect']:
            state,reason='applied','postimage-readback'
        else: state,reason='unknown','mixed-or-drift-or-unproven-preimage'
        result=self._result(intent,state,reason,files)
        if record['state']in {'applied','not-applied'}:
            if record['state']!=state: raise packets.PacketError('source-final-image-drift')
            raw=trust._read(packet_fd,'integration-result-'+record['result_sha256']+'.json',65536)
            if packets.digest(raw)!=record['result_sha256'] or raw!=packets.canonical(result): raise packets.PacketError('source-integration-result-drift')
            return result
        self.store._finish_integration(packet_fd,ledger,operation,state,result)
        return result

    def reconcile(self,operation_id,authority):
        packets._id(operation_id)
        # Re-acquiring THIS fixture lock proves its synchronous call has ended;
        # no child, async callback or exposed writable FD can continue that call.
        with self.source._locked() as (source_fd,control):
            with self.store.locked() as packet_fd:
                ledger=self.store._read(packet_fd)
                if ledger is None: raise packets.PacketError('packet-not-prepared')
                return self._reconcile_locked(source_fd,control,packet_fd,ledger,operation_id,authority)
