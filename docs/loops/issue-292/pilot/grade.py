from pathlib import Path
import json,subprocess,sys,hashlib,os
BASE=Path(__import__('os').environ['CODEX_PILOT_ROOT']).resolve();REPO=Path(__file__).resolve().parents[4]
ALLOWED={'R':set(),'E':set(),'W':{'chunker.py'},'S':{'parse_overrides.py','merge_config.py'},'A':{'manifest.py','exporter.py','cli.py'},'V':set()}
SCRIPTS={
'W':'''from chunker import chunks
v=[1,2,3,4,5];assert chunks(v,2)==[[1,2],[3,4],[5]]
assert chunks([4,5],1)==[[4],[5]]
assert chunks([],2)==[]
for values in ([],[1]):
 for size in (0,-1,-9):
  try:chunks(values,size)
  except ValueError:pass
  else:raise AssertionError('nonpositive size accepted')
assert v==[1,2,3,4,5]
print('W deterministic checks PASS')
''',
'S':'''from merge_config import merge_config
from parse_overrides import parse_layer
import copy
args=({'retries':1,'enabled':False},{'retries':2},{'retries':'3'},{'retries':'4','enabled':'true'})
before=copy.deepcopy(args);assert merge_config(*args)=={'retries':4,'enabled':True};assert args==before
assert merge_config({'retries':5},{},{},{'retries':0})['retries']==0
assert merge_config({'enabled':True},{},{'enabled':'false'},{})['enabled'] is False
bad=[{'bogus':1},{'retries':'x'},{'retries':True},{'retries':-1},{'enabled':'False'},{'retries':'１２'},{'retries':''},{'enabled':1}]
for x in bad:
 try:merge_config({}, {}, x, {'retries':7,'enabled':True})
 except ValueError:pass
 else:raise AssertionError(('invalid layer accepted',x))
assert parse_layer({})=={}
print('S deterministic checks PASS')
''',
'A':'''from exporter import export
from manifest import load_manifest
from pathlib import Path
import tempfile,shutil,json
with tempfile.TemporaryDirectory() as td:
 r=Path(td);src=r/'src';src.mkdir();(src/'a.txt').write_bytes('你好'.encode());(src/'b.bin').write_bytes(bytes([0,255]));m=src/'m.json';m.write_text(json.dumps(['a.txt','b.bin']));d=r/'out'
 export(m,d);assert (d/'a.txt').read_bytes()=='你好'.encode();assert (d/'b.bin').read_bytes()==bytes([0,255]);assert {p.name for p in d.iterdir()}=={'a.txt','b.bin'}
 snapshot={p.name:p.read_bytes() for p in d.iterdir()};export(m,d);assert snapshot=={p.name:p.read_bytes() for p in d.iterdir()}
 missing=src/'missing.json';missing.write_text(json.dumps(['a.txt','absent.bin']));new=r/'new'
 try:export(missing,new)
 except (ValueError,FileNotFoundError,OSError):pass
 else:raise AssertionError('missing source accepted')
 assert not new.exists()
 sentinel=d/'sentinel.txt';sentinel.write_bytes(b'original');before={p.name:p.read_bytes() for p in d.iterdir()};siblings={p.name for p in r.iterdir()};calls=[]
 def flaky(a,b):
  calls.append(str(a));shutil.copyfile(a,b)
  if len(calls)==2:raise OSError('injected-second-copy-failure')
 try:export(m,d,copy_file=flaky)
 except OSError:pass
 else:raise AssertionError('injected failure swallowed')
 assert len(calls)==2
 assert before=={p.name:p.read_bytes() for p in d.iterdir()}
 assert siblings=={p.name for p in r.iterdir()},[p.name for p in r.iterdir()]
 assert (src/'a.txt').read_bytes()=='你好'.encode();assert (src/'b.bin').read_bytes()==bytes([0,255])
print('A deterministic checks PASS')
'''}

def grade(run):
 d=BASE/'runs'/run;r=json.loads((d/'result.json').read_text());key=r['packet'];after=r['after_hashes'];before=r['fixture_hashes'];changed={p for p in before if after.get(p)!=before[p]};added=set(after)-set(before);unexpected=(changed|added)-ALLOWED[key];unexpected={p for p in unexpected if '__pycache__' not in p and not p.endswith('.pyc')}
 output={'run':run,'startup_pass':r['exit_code']==0 and r['final_present'],'profile_matches_final_source':hashlib.sha256((REPO/'agent-profiles'/f"{r['role']}.toml").read_bytes()).hexdigest()==r['profile_sha256'],'ownership_pass':not unexpected,'unexpected_paths':sorted(unexpected),'semantic_review':'pending','deterministic':'not_applicable'}
 if key=='R':
  expected={'retry':['A'],'non_retry':['B','D','E'],'unknown':['C'],'source_count':6,'latest_count':5,'line_numbers':{'A':1,'B':2,'C':3,'D':4,'E':6}}
  try:actual=json.loads((d/'final.txt').read_text())
  except ValueError:actual=None
  output['deterministic']='PASS' if actual==expected else 'FAIL';output['semantic_review']='PASS' if actual==expected else 'FAIL'
 elif key in SCRIPTS:
  cp=subprocess.run([str(d/'workspace/scripts/project-python'),'-B','-c',SCRIPTS[key]],cwd=d/'workspace',capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  output['deterministic']='PASS' if cp.returncode==0 else 'FAIL';output['checks_output']=(cp.stdout+cp.stderr)[-2000:]
 elif key=='E':
  got=[]
  for args,env_timeout in [(['--timeout','7','--config','11'],'9'),(['--config','11'],'9'),(['--config','11'],None),(['--config','90'],None)]:
   env={**os.environ};env.pop('FIXTURE_TIMEOUT',None)
   if env_timeout is not None:env['FIXTURE_TIMEOUT']=env_timeout
   cp=subprocess.run([str(d/'workspace/scripts/project-python'),'-B','cli.py','--dry-run',*args],cwd=d/'workspace',capture_output=True,text=True,env=env)
   import ast
   got.append(ast.literal_eval(cp.stdout)['timeout'])
  output['deterministic']='PASS' if got==[7,9,11,60] else 'FAIL';output['values']=got
 elif key=='V':
  cp=subprocess.run([str(d/'workspace/scripts/project-python'),'-B','-c',"from prefix import unique_prefix;from ranges import inclusive;from copy_values import copy_values;v=[3,1,3,2];print(unique_prefix(v,2));print(inclusive([1,2,3],1,3));a=[1,2];b=copy_values(a);assert b==a and b is not a"],cwd=d/'workspace',capture_output=True,text=True)
  output['deterministic']='PASS' if cp.returncode==0 and cp.stdout.splitlines()==['[1, 2]','[2, 3]'] else 'FAIL';output['seeded_actual']=cp.stdout.strip()
 (d/'parent-grade.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');print(json.dumps(output,ensure_ascii=False))
for name in sys.argv[1:]:grade(name)
