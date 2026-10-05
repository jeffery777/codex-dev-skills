"""Fixed synthetic one-shot root launcher source; host code only, no registry.

The persisted exclusive claim precedes every worker action. Existing/partial
claim means exit 73 without running the body. Trusted Docker administrators
remain outside this boundary; model workers have no daemon/control interface.
"""
import hashlib
import json
import pathlib
import re

CONTRACT_SHA256 = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
FAULTS = frozenset({'none', 'claim-created', 'claim-fsync', 'before-fork', 'completion-created'})
SOURCE = r'''
import ctypes,hashlib,json,os,signal,stat,sys

def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def digest(raw): return hashlib.sha256(raw).hexdigest()
def pairs(values):
 result={}
 for key,value in values:
  if key in result: raise ValueError('duplicate-key')
  result[key]=value
 return result
def read(name):
 fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=control)
 try:
  st=os.fstat(fd)
  if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_gid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or st.st_size>16384: raise ValueError('control-file')
  raw=os.read(fd,16385)
  after=os.fstat(fd); named=os.stat(name,dir_fd=control,follow_symlinks=False)
  identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_uid,s.st_gid,s.st_mode,s.st_nlink)
  if len(raw)!=st.st_size or identity(st)!=identity(after) or identity(after)!=identity(named): raise ValueError('control-read')
  return raw
 finally: os.close(fd)
def create(name,raw):
 fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=control)
 try:
  if CONFIG['fault']==name.split('.')[0]+'-created': os._exit(74)
  sent=0
  while sent<len(raw): sent+=os.write(fd,raw[sent:])
  os.fsync(fd)
  if CONFIG['fault']==name.split('.')[0]+'-fsync': os._exit(74)
 finally: os.close(fd)
 os.fsync(control)
 if read(name)!=raw: raise ValueError('control-write-readback')
def checked(result):
 if result<0: raise OSError(ctypes.get_errno(),'privilege-drop')
def drop():
 os.close(control)
 libc=ctypes.CDLL(None,use_errno=True)
 # Clear ambient, inheritable/permitted/effective and the complete bounding set.
 checked(libc.prctl(47,4,0,0,0))
 for cap in range(64):
  present=libc.prctl(23,cap,0,0,0)
  if present<0:
   if ctypes.get_errno()==22: break
   checked(present)
  if present: checked(libc.prctl(24,cap,0,0,0))
 os.setgroups([]); os.setresgid(65534,65534,65534); os.setresuid(65534,65534,65534)
 libc.setfsgid(65534); libc.setfsuid(65534)
 if libc.setfsgid(65534)!=65534 or libc.setfsuid(65534)!=65534: raise ValueError('fs-identity')
 class Header(ctypes.Structure): _fields_=[('version',ctypes.c_uint32),('pid',ctypes.c_int)]
 class Data(ctypes.Structure): _fields_=[('effective',ctypes.c_uint32),('permitted',ctypes.c_uint32),('inheritable',ctypes.c_uint32)]
 header=Header(0x20080522,0); data=(Data*2)()
 checked(libc.capset(ctypes.byref(header),ctypes.byref(data)))
 checked(libc.prctl(38,1,0,0,0))
 status={}
 with open('/proc/self/status') as stream:
  for line in stream:
   if ':' in line:
    key,value=line.split(':',1); status[key]=value.strip()
 if (os.getresuid()!=(65534,)*3 or os.getresgid()!=(65534,)*3 or os.getgroups()
     or status.get('NoNewPrivs')!='1' or any(int(status[key],16) for key in ['CapInh','CapPrm','CapEff','CapBnd','CapAmb'])): raise ValueError('drop-proof')
 os.closerange(3,1048576)
 os.chdir('/workspace')
 os.execve('/usr/local/bin/python3',CHILD_ARGV,
           {'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp','LANG':'C.UTF-8'})

control=os.open('/control',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
st=os.fstat(control)
if st.st_uid!=0 or st.st_gid!=0: os._exit(74)
os.fchmod(control,0o700); os.fsync(control)
# Any existing claim is a durable refusal, never a retry/repair opportunity.
try:
 os.stat('claim.json',dir_fd=control,follow_symlinks=False)
except FileNotFoundError: pass
else: os._exit(73)
try:
 raw=read('input.json'); value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('constant')))
 if (type(value)is not dict or set(value)!={'schema_version','binding','nonce','volume','descriptor_sha256','container_id','launcher_sha256'}
     or value['schema_version']!=1 or value['binding']!=CONFIG['binding'] or value['nonce']!=CONFIG['nonce'] or value['volume']!=CONFIG['volume']
     or value['launcher_sha256']!=CONFIG['launcher_sha256']): raise ValueError('input-binding')
 for key in ['descriptor_sha256','container_id','launcher_sha256']:
  if type(value[key])is not str or len(value[key])!=64 or any(c not in '0123456789abcdef' for c in value[key]): raise ValueError('input-digest')
 claim={'schema_version':1,'input_sha256':digest(raw),'input':value}
 try: create('claim.json',canonical(claim))
 except FileExistsError: os._exit(73)
 if CONFIG['fault']=='before-fork': os._exit(74)
 signal.alarm(40)
 child=os.fork()
 if child==0:
  try: drop()
  except BaseException: os._exit(75)
 _,status=os.waitpid(child,0)
 completion={'schema_version':1,'claim_sha256':digest(canonical(claim)),'input_sha256':digest(raw),'input':value,'worker_status':status}
 create('completion.json',canonical(completion))
 os.close(control)
 os._exit(0 if status==0 else 76)
except BaseException: os._exit(74)
'''


def render(binding, volume, nonce, worker, fault='none'):
    """Called only by trusted host backend with one of its fixed recipes."""
    from model_container_backend import WORKERS
    if worker not in WORKERS or fault not in FAULTS:
        raise ValueError('fixed-launcher-recipe-required')
    # This digest identifies the immutable launcher implementation, avoiding a
    # source hash self-reference when the full runtime program embeds config.
    launcher_sha = CONTRACT_SHA256
    config = {'binding':binding,'volume':volume,'nonce':nonce,'launcher_sha256':launcher_sha,'fault':fault}
    # Preserve the existing fixed synthetic recipe declaration for its capture
    # observers; only the closed native renderer uses a separate helper argv.
    return 'CONFIG='+repr(config)+'\nWORKER='+repr(WORKERS[worker])+'\n' + \
        "CHILD_ARGV=['/usr/local/bin/python3','-I','-c',WORKER]\n"+SOURCE


def render_native(binding, volume, nonce, case):
    """Closed fixture helper only; never accepts a worker program or argv."""
    if case not in {'checkpoint','quarantine','claim-replay'} or type(nonce) is not str or not re.fullmatch(r'[a-f0-9]{64}',nonce):
        raise ValueError('fixed-native-launcher-recipe-required')
    config = {'binding':binding,'volume':volume,'nonce':nonce,
              'launcher_sha256':CONTRACT_SHA256,'fault':'none'}
    argv = ['/usr/local/bin/python3','-I','-S','-B',
            '/fixture/scripts/model_native_checkpoint_fixture.py',case,nonce]
    return 'CONFIG='+repr(config)+'\nCHILD_ARGV='+repr(argv)+'\n'+SOURCE


def contract_digest():
    return CONTRACT_SHA256
