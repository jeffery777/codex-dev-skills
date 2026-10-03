#!/usr/bin/env python3
"""Opt-in fixed macOS Docker PID-limit control, without host mounts/providers.

One positive fork, then at most 32 limit-phase fork attempts (33 total).
Private PID/cgroup and an explicit PID1 deadline.
No pull, stop, removal, restart, credentials or production qualification.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile

_paths=list(sys.path)
try:
    _spec=importlib.util.spec_from_file_location('pid_control_support',pathlib.Path(__file__).with_name('verify-model-isolation-path-controls.py'))
    support=importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(support)
finally:
    sys.path[:]=_paths
backend=support.backend
# The fixed Linux guest reports Linux errno, independent of the macOS host.
LINUX_EAGAIN=11

PROGRAM=r'''
import errno,json,os,pathlib,re,signal

def number(name):
    with open('/sys/fs/cgroup/'+name,'rb') as stream:data=stream.read(513)
    if len(data)>512 or re.fullmatch(rb'(0|[1-9][0-9]{0,18})\n',data) is None:raise ValueError('bounded cgroup number required')
    return int(data)

def events(name):
    with open('/sys/fs/cgroup/'+name,'rb') as stream:data=stream.read(513)
    if len(data)>512 or re.fullmatch(rb'max (0|[1-9][0-9]{0,18})\n',data) is None:raise ValueError('bounded local events required')
    return int(data.split()[1])

def snapshot():
    with open('/proc/self/cgroup','rb') as stream:membership=stream.read(513)
    if membership!=b'0::/\n':raise ValueError('private cgroup v2 required')
    return dict(cgroup='0::/',maximum=number('pids.max'),current=number('pids.current'),
        events=events('pids.events'),local_events=events('pids.events.local'))

def batch(limit):
    reader,writer=os.pipe();ready_reader,ready_writer=os.pipe()
    children=[];failure=None;peak=None;waited=[];ready=0
    try:
        for attempt in range(limit):
            try:pid=os.fork()
            except OSError as error:
                failure=error.errno
                break
            if pid==0:
                os.close(writer);os.close(ready_reader)
                os.write(ready_writer,b'R');os.close(ready_writer)
                try:released=os.read(reader,1)==b''
                except OSError:released=False
                os._exit(0 if released else 125)
            children.append(pid)
            if os.read(ready_reader,1)!=b'R':raise ValueError('child readiness missing')
            ready+=1
        peak=snapshot()
    finally:
        # Every child closes its inherited writer before blocking. Closing this
        # sole remaining writer releases all children, including error paths.
        os.close(writer);os.close(reader);os.close(ready_writer);os.close(ready_reader)
        for pid in children:
            actual,status=os.waitpid(pid,0)
            waited.append(dict(pid=actual,status=status))
    return dict(attempts=len(children)+(failure is not None),children=children,
        ready=ready,failure=failure,peak=peak,waited=waited,after=snapshot())

def deadline(signum,frame):
    # PID1 ignores default signal dispositions; install an explicit handler.
    # Exit is failure, never a successful receipt. No host/daemon signal used.
    os._exit(124)

def main():
    signal.signal(signal.SIGALRM,deadline);signal.alarm(30)
    task_count=len(list(pathlib.Path('/proc/self/task').iterdir()))
    if os.getpid()!=1 or os.getuid()!=1000 or task_count!=1:raise ValueError('fixed single-task PID1 UID required')
    baseline=snapshot()
    if baseline['maximum']!=32 or baseline['current']!=1:raise ValueError('fixed fresh limit required')
    positive=batch(1)
    if (positive['failure'] is not None or len(positive['children'])!=1 or positive['ready']!=1
            or positive['peak']!={**baseline,'current':2} or positive['after']!=baseline
            or positive['waited']!=[dict(pid=positive['children'][0],status=0)]):raise ValueError('single child positive failed')
    limited=batch(32)
    print(json.dumps(dict(schema=1,pid=os.getpid(),uid=os.getuid(),task_count=task_count,baseline=baseline,
        positive=positive,limited=limited)),flush=True)
    signal.alarm(0)

if __name__=='__main__':main()
'''


def command(cidfile):
    return ['docker','create','--cidfile',str(cidfile),'--pull=never','--read-only','--network=none',
        '--cap-drop=ALL','--security-opt=no-new-privileges','--user=1000:1000','--pids-limit=32',
        '--memory=512m','--cpus=1','--restart=no','--tmpfs=/tmp:rw,noexec,nosuid,size=32m,mode=1777',
        '--entrypoint=/usr/bin/env',backend.IMAGE,'-i','PATH=/usr/local/bin:/usr/bin:/bin',
        'HOME=/tmp/anonymous-home','python3','-I','-S','-B','-c',PROGRAM]


def validate_policy(value,cid,argv,state):
    expected={'id':cid,'image':backend.IMAGE,'entrypoint':['/usr/bin/env'],'command':argv[argv.index(backend.IMAGE)+1:],
        'user':'1000:1000','mounts':[],'readonly':True,'network':'none','caps':['ALL'],'security':['no-new-privileges'],
        'restart':{'Name':'no','MaximumRetryCount':0},'pids':32,'memory':536870912,'cpus':1000000000,
        'tmpfs':{'/tmp':'rw,noexec,nosuid,size=32m,mode=1777'},'privileged':False,'pid_mode':'','ipc_mode':'private',
        'userns_mode':'','cgroupns_mode':'private','devices':[],'device_requests':None,'volumes_from':None,
        'state':state,'running':False,'pid':0,'exit':0,'oom':False}
    if type(value) is not dict or set(value)!=set(expected):raise ValueError('fixed PID policy shape mismatch')
    if any(type(value[k]) is not type(v) or value[k]!=v for k,v in expected.items()):raise ValueError('fixed PID policy mismatch')


def validate_snapshot(value,current):
    if (type(value) is not dict or set(value)!={'cgroup','maximum','current','events','local_events'}
            or value['cgroup']!='0::/' or any(type(value[k]) is not int for k in ('maximum','current','events','local_events'))
            or value['maximum']!=32 or value['current']!=current
            or not 0<=value['events']<10**19 or not 0<=value['local_events']<10**19):raise ValueError('fixed cgroup counters mismatch')


def validate_result(value):
    if (type(value) is not dict or set(value)!={'schema','pid','uid','task_count','baseline','positive','limited'}
            or type(value['schema']) is not int or value['schema']!=1
            or type(value['pid']) is not int or value['pid']!=1
            or type(value['uid']) is not int or value['uid']!=1000
            or type(value['task_count']) is not int or value['task_count']!=1):raise ValueError('fixed PID result identity mismatch')
    baseline=value['baseline'];validate_snapshot(baseline,1)
    for name,count,failure in [('positive',1,None),('limited',31,LINUX_EAGAIN)]:
        row=value[name]
        if (type(row) is not dict or set(row)!={'attempts','children','ready','failure','peak','waited','after'}
                or type(row['attempts']) is not int or row['attempts']!=count+(failure is not None)
                or type(row['ready']) is not int or row['ready']!=count
                or type(row['children']) is not list or len(row['children'])!=count
                or any(type(pid) is not int or not 1<pid<2**31 for pid in row['children'])
                or len(set(row['children']))!=count or type(row['failure']) is not type(failure) or row['failure']!=failure
                or type(row['waited']) is not list or len(row['waited'])!=count):raise ValueError('fixed fork/wait result mismatch')
        for pid,wait in zip(row['children'],row['waited'],strict=True):
            if type(wait) is not dict or set(wait)!={'pid','status'} or type(wait['pid']) is not int or wait['pid']!=pid or type(wait['status']) is not int or wait['status']!=0:raise ValueError('child did not exit normally')
        validate_snapshot(row['peak'],count+1);validate_snapshot(row['after'],1)
        before=baseline if name=='positive' else value['positive']['after']
        increment=0 if name=='positive' else 1
        for key in ('events','local_events'):
            if row['peak'][key]!=before[key]+increment or row['after'][key]!=row['peak'][key]:raise ValueError('uncorroborated PID boundary failure')


def execute(engine,root):
    cidfile=root/'container-id';argv=command(cidfile)
    (root/'create-intent.json').write_text(json.dumps({'argv':argv,'replay':False},indent=2)+'\n')
    try:cid=engine.call(argv)
    except (OSError,subprocess.SubprocessError) as error:
        recovery={'status':'create-result-unknown','error_type':type(error).__name__,'replayed':False,'started':False}
        if cidfile.is_file() and not cidfile.is_symlink() and cidfile.stat().st_size<=65:
            uncertain=cidfile.read_text().strip()
            if backend.re.fullmatch('[a-f0-9]{64}',uncertain):
                recovery['id']=uncertain
                try:recovery['readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',uncertain])
                except (OSError,subprocess.SubprocessError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/'unknown-create.json').write_text(json.dumps(recovery,indent=2)+'\n')
        raise
    if not backend.re.fullmatch('[a-f0-9]{64}',cid) or cidfile.read_text().strip()!=cid:raise ValueError('own PID CID mismatch')
    def inspect():return json.loads(engine.call(['docker','inspect','--format',support.FORMAT,cid]))
    before=inspect();(root/'before.json').write_text(json.dumps(before,indent=2)+'\n');validate_policy(before,cid,argv,'created')
    (root/'start-intent.json').write_text(json.dumps({'id':cid,'replayed':False})+'\n')
    def unknown_start(error_type):
        recovery={'status':'start-result-unknown','id':cid,'error_type':error_type,'replayed':False,'passed':False}
        try:recovery['exact_readback']=engine.call(['docker','inspect','--format','{{.Id}} {{.Image}} {{.State.Status}} {{.State.Pid}}',cid])
        except (OSError,subprocess.SubprocessError,ValueError) as problem:recovery['readback_error_type']=type(problem).__name__
        (root/'unknown-start.json').write_text(json.dumps(recovery,indent=2)+'\n')
    try:started=engine.call(['docker','start',cid])
    except (OSError,subprocess.SubprocessError,ValueError) as error:
        unknown_start(type(error).__name__)
        raise
    if started!=cid:
        unknown_start('CIDMismatch')
        raise ValueError('PID start result unknown; no replay')
    exit_status=engine.call(['docker','wait',cid]);after=inspect()
    (root/'after.json').write_text(json.dumps(after,indent=2)+'\n');validate_policy(after,cid,argv,'exited')
    if exit_status!='0':raise ValueError('PID probe did not exit naturally')
    raw=engine.call(['docker','logs',cid])
    if len(raw)>32768:raise ValueError('bounded PID output required')
    (root/'output.json').write_text(raw+'\n');value=json.loads(raw);validate_result(value)
    return cid,value


def run(evidence_root):
    parent=backend.evidence_root(evidence_root)
    root=pathlib.Path(tempfile.mkdtemp(prefix='isolation-pid-limit-',dir=parent))
    engine=backend.LocalDesktop();engine_id=engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])
    cid,value=execute(engine,root)
    if engine.call(['docker','info','--format','{{.ID}} {{.OSType}}'])!=engine_id:raise ValueError('engine drift')
    receipt={'fixed_pid_control_passed':True,'n1_qualified':False,'production_qualified':False,'id':cid,'root':str(root),
        'image':backend.IMAGE,'program_sha256':hashlib.sha256(PROGRAM.encode()).hexdigest(),'result':value,
        'limits':['fixed UID/PID/cgroup/image tuple only','ancestor causal attribution not established',
            'no memory/CPU exhaustion, daemon/host restart, native CLI or credential qualification']}
    (root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'root':str(root),'fixed_pid_control_passed':True,'maximum':32,'children':31,'production_qualified':False}))
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence-root',default='/private/tmp')
    raise SystemExit(run(parser.parse_args().evidence_root))
