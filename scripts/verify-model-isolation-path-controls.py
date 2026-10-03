#!/usr/bin/env python3
"""Opt-in fixed macOS Docker exact-path read/write controls, without providers.

Only fresh synthetic canaries are mounted. No pull, stop, removal, restart,
credentials, host repository, production adapter or complete qualification.
"""
import argparse
import errno
import hashlib
import importlib.util
import json
import os
import pathlib
import stat
import subprocess
import sys
import tempfile

_paths=list(sys.path)
try:
    _spec=importlib.util.spec_from_file_location('path_control_backend',pathlib.Path(__file__).with_name('verify-model-container-native.py'))
    backend=importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(backend)
finally:
    sys.path[:]=_paths

LABELS=('source','checkpoint','sibling')
DENIED={errno.ENOENT,errno.EACCES,errno.EPERM,errno.EROFS}
PROGRAM=r'''
import json,os,pathlib,sys
labels=('source','checkpoint','sibling')
targets=json.loads(sys.argv[1]);cases=[]
assert len(targets)==3
for label,target in zip(labels,targets,strict=True):
    row={'label':label,'target':target,'read':None,'read_errno':None,'write_count':None,'write_errno':None,'readback':None}
    try:
        with open(target,'rb') as stream:row['read']=stream.read(64).decode('ascii')
    except OSError as error:row['read_errno']=error.errno
    # Always attempt write, even when read fails. Never create target files.
    try:
        fd=os.open(target,os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            data=('changed-'+label+'\n').encode('ascii')
            row['write_count']=os.write(fd,data);os.ftruncate(fd,len(data));os.fsync(fd)
        finally:os.close(fd)
        with open(target,'rb') as stream:row['readback']=stream.read(64).decode('ascii')
    except OSError as error:row['write_errno']=error.errno
    cases.append(row)
own=pathlib.Path('/workspace/positive-control');own.write_bytes(b'path-control\n')
print(json.dumps({'schema':1,'targets':targets,'uid':os.getuid(),'workspace_control':own.read_bytes()==b'path-control\n','cases':cases}),flush=True)
'''

FIELDS={'id':'.Id','image':'.Image','entrypoint':'.Config.Entrypoint','command':'.Config.Cmd','user':'.Config.User',
    'mounts':'.Mounts','readonly':'.HostConfig.ReadonlyRootfs','network':'.HostConfig.NetworkMode',
    'caps':'.HostConfig.CapDrop','security':'.HostConfig.SecurityOpt','restart':'.HostConfig.RestartPolicy',
    'pids':'.HostConfig.PidsLimit','memory':'.HostConfig.Memory','cpus':'.HostConfig.NanoCpus',
    'tmpfs':'.HostConfig.Tmpfs','privileged':'.HostConfig.Privileged','pid_mode':'.HostConfig.PidMode',
    'ipc_mode':'.HostConfig.IpcMode','userns_mode':'.HostConfig.UsernsMode','cgroupns_mode':'.HostConfig.CgroupnsMode',
    'devices':'.HostConfig.Devices','device_requests':'.HostConfig.DeviceRequests','volumes_from':'.HostConfig.VolumesFrom',
    'state':'.State.Status','running':'.State.Running','pid':'.State.Pid','exit':'.State.ExitCode','oom':'.State.OOMKilled'}
FORMAT='{'+','.join(json.dumps(key)+':{{json '+value+'}}' for key,value in FIELDS.items())+'}'


def identity(path,content):
    info=path.lstat()
    if (not stat.S_ISREG(info.st_mode) or path.resolve(strict=True)!=path
            or info.st_uid!=os.getuid() or info.st_nlink!=1
            or stat.S_IMODE(info.st_mode)!=0o666 or info.st_size!=len(content)
            or path.read_bytes()!=content):raise ValueError('synthetic canary identity or bytes drift')
    return info.st_dev,info.st_ino,info.st_uid,info.st_mode


def reset_canaries(targets,identities):
    # This runs only after positive exit/readback; unrelated files are never reset.
    for label,path,expected in zip(LABELS,targets,identities,strict=True):
        if identity(path,('changed-'+label+'\n').encode())!=expected:raise ValueError('canary replaced before reset')
    for label,path,expected in zip(LABELS,targets,identities,strict=True):
        fd=os.open(path,os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            info=os.fstat(fd)
            if (info.st_dev,info.st_ino,info.st_uid,info.st_mode)!=expected or info.st_nlink!=1:raise ValueError('reset descriptor drift')
            data=(label+'\n').encode()
            if os.write(fd,data)!=len(data):raise ValueError('partial synthetic reset')
            os.ftruncate(fd,len(data));os.fsync(fd)
        finally:os.close(fd)
        if identity(path,data)!=expected:raise ValueError('reset readback drift')


def command(workspace,targets,positive,cidfile):
    argv=['docker','create','--cidfile',str(cidfile),'--pull=never','--read-only','--network=none',
        '--cap-drop=ALL','--security-opt=no-new-privileges','--user=1000:1000','--pids-limit=64',
        '--memory=512m','--cpus=1','--restart=no','--tmpfs=/tmp:rw,noexec,nosuid,size=32m,mode=1777',
        '--mount',f'type=bind,src={workspace},dst=/workspace']
    if positive:
        for path in targets:argv.extend(['--mount',f'type=bind,src={path},dst={path}'])
    argv.extend(['--entrypoint=/usr/bin/env',backend.IMAGE,'-i','PATH=/usr/local/bin:/usr/bin:/bin',
        'HOME=/tmp/anonymous-home','python3','-I','-S','-B','-c',PROGRAM,json.dumps([str(p) for p in targets])])
    return argv


def validate_policy(value,cid,argv,workspace,targets,positive,state):
    expected={'id':cid,'image':backend.IMAGE,'entrypoint':['/usr/bin/env'],'command':argv[argv.index(backend.IMAGE)+1:],
        'user':'1000:1000','readonly':True,'network':'none','caps':['ALL'],'security':['no-new-privileges'],
        'restart':{'Name':'no','MaximumRetryCount':0},'pids':64,'memory':536870912,'cpus':1000000000,
        'tmpfs':{'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'},'privileged':False,'pid_mode':'','ipc_mode':'private',
        'userns_mode':'','cgroupns_mode':'private','devices':[],'device_requests':None,'volumes_from':None,
        'state':state,'running':False,'pid':0,'exit':0,'oom':False}
    if set(value)!=set(FIELDS) or any(value[k]!=v for k,v in expected.items()):raise ValueError('fixed control policy mismatch')
    mounts=value['mounts'];bindings={(str(workspace),'/workspace',True)}
    if positive:bindings.update((str(p),str(p),True) for p in targets)
    if (type(mounts) is not list or len(mounts)!=len(bindings)
            or any(m.get('Type')!='bind' or m.get('Propagation')!='rprivate' for m in mounts)
            or {(m.get('Source'),m.get('Destination'),m.get('RW')) for m in mounts}!=bindings):raise ValueError('exact control mounts mismatch')


def validate_result(value,targets,positive):
    if (type(value) is not dict or set(value)!={'schema','targets','uid','workspace_control','cases'}
            or type(value['schema']) is not int or value['schema']!=1 or value['targets']!=[str(p) for p in targets]
            or type(value['uid']) is not int or value['uid']!=1000 or value['workspace_control'] is not True
            or type(value['cases']) is not list or len(value['cases'])!=3):raise ValueError('fixed result envelope mismatch')
    keys={'label','target','read','read_errno','write_count','write_errno','readback'}
    for label,path,row in zip(LABELS,targets,value['cases'],strict=True):
        if type(row) is not dict or set(row)!=keys or row['label']!=label or row['target']!=str(path):raise ValueError('fixed case sequence mismatch')
        if positive:
            if (row['read']!=label+'\n' or row['read_errno'] is not None or row['write_errno'] is not None
                    or type(row['write_count']) is not int or row['write_count']!=len('changed-'+label+'\n')
                    or row['readback']!='changed-'+label+'\n'):raise ValueError('read/write positive missing')
        elif (row['read'] is not None or row['readback'] is not None or row['write_count'] is not None
                or type(row['read_errno']) is not int or row['read_errno'] not in DENIED
                or type(row['write_errno']) is not int or row['write_errno'] not in DENIED):raise ValueError('read/write boundary denial missing or unknown')


def execute_phase(engine,root,workspace,targets,positive,previous_cid=None):
    phase='positive' if positive else 'negative';cidfile=root/(phase+'-cid')
    argv=command(workspace,targets,positive,cidfile)
    (root/(phase+'-intent.json')).write_text(json.dumps({'argv':argv,'replay':False},indent=2)+'\n')
    try:cid=engine.call(argv)
    except (OSError,subprocess.SubprocessError) as error:
        recovery={'phase':phase,'status':'create-result-unknown','error_type':type(error).__name__,'replayed':False,'started':False}
        if cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size<=65:
            uncertain=cidfile.read_text().strip()
            if backend.re.fullmatch('[a-f0-9]{64}',uncertain):
                recovery['id']=uncertain
                try:recovery['readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',uncertain])
                except (OSError,subprocess.SubprocessError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/(phase+'-unknown.json')).write_text(json.dumps(recovery,indent=2)+'\n')
        raise
    if not backend.re.fullmatch('[a-f0-9]{64}',cid) or cidfile.read_text().strip()!=cid or cid==previous_cid:raise ValueError('own control CID mismatch')
    def inspect():return json.loads(engine.call(['docker','inspect','--format',FORMAT,cid]))
    before=inspect();(root/(phase+'-before.json')).write_text(json.dumps(before,indent=2)+'\n')
    validate_policy(before,cid,argv,workspace,targets,positive,'created')
    if engine.call(['docker','start',cid])!=cid:raise ValueError('start result unknown; no replay')
    exit_code=engine.call(['docker','wait',cid]);after=inspect()
    (root/(phase+'-after.json')).write_text(json.dumps(after,indent=2)+'\n')
    validate_policy(after,cid,argv,workspace,targets,positive,'exited')
    if exit_code!='0':raise ValueError('control did not exit naturally')
    raw=engine.call(['docker','logs',cid])
    if len(raw)>32768:raise ValueError('bounded control output required')
    (root/(phase+'-output.json')).write_text(raw+'\n')
    value=json.loads(raw);validate_result(value,targets,positive)
    if (workspace/'positive-control').is_symlink() or (workspace/'positive-control').read_bytes()!=b'path-control\n':raise ValueError('workspace positive readback missing')
    return {'phase':phase,'cid':cid,'result':value}


def run(evidence_root):
    parent=backend.evidence_root(evidence_root)
    root=pathlib.Path(tempfile.mkdtemp(prefix='isolation-path-controls-',dir=parent))
    targets=[root/label for label in LABELS];identities=[]
    for label,path in zip(LABELS,targets,strict=True):
        data=(label+'\n').encode();path.write_bytes(data);path.chmod(0o666);identities.append(identity(path,data))
    workspaces=[root/phase for phase in ('positive','negative')]
    for path in workspaces:path.mkdir();path.chmod(0o777)
    engine=backend.LocalDesktop();engine_id=engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    positive=execute_phase(engine,root,workspaces[0],targets,True)
    (root/'reset-intent.json').write_text(json.dumps({'positive_cid':positive['cid'],'targets':[str(p) for p in targets],'identities':identities,'replay':False},indent=2)+'\n')
    reset_canaries(targets,identities)
    (root/'reset-confirmed.json').write_text(json.dumps({'positive_cid':positive['cid'],'baseline_confirmed':True})+'\n')
    negative=execute_phase(engine,root,workspaces[1],targets,False,positive['cid'])
    for label,path,expected in zip(LABELS,targets,identities,strict=True):
        if identity(path,(label+'\n').encode())!=expected:raise ValueError('negative host canary drift')
    if engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])!=engine_id:raise ValueError('engine drift')
    receipt={'fixed_path_controls_passed':True,'n1_qualified':False,'production_qualified':False,'root':str(root),
        'image':backend.IMAGE,'program_sha256':hashlib.sha256(PROGRAM.encode()).hexdigest(),
        'controls':[positive,negative],'targets':[str(p) for p in targets],
        'limits':['three synthetic exact paths; read/write only','no resource exhaustion, restart, native Codex, credentials or complete qualification']}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'root':str(root),'fixed_path_controls_passed':True,'paths':3,'operations':12,'production_qualified':False}))
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence-root',default='/private/tmp')
    raise SystemExit(run(parser.parse_args().evidence_root))
