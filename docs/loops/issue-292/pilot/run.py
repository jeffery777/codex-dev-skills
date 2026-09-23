from pathlib import Path
import json,subprocess,shutil,time,hashlib,tomllib,os,signal,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from event_evidence import inspect
BASE=Path(os.environ['CODEX_PILOT_ROOT']).resolve(); REPO=Path(__file__).resolve().parents[4]
DEFAULT_CLI=Path(shutil.which('codex') or '/nonexistent-codex').resolve(); CLI=Path(os.environ.get('CODEX_PILOT_CLI',str(DEFAULT_CLI))).resolve()
packets={p['id']:p for p in json.loads((BASE/'packets.json').read_text())}
def digest(b):return hashlib.sha256(b).hexdigest()
def file_digest(path):return digest(path.read_bytes()) if path.is_file() else None
def stop_after_timeout(proc,record):
 record['timeout']={'limit_seconds':600,'signal':'SIGTERM','grace_seconds':15}
 os.killpg(proc.pid,signal.SIGTERM)
 try:proc.communicate(timeout=15)
 except subprocess.TimeoutExpired:
  record['timeout']['grace_expired']=True;record['timeout']['final_signal']='SIGKILL';os.killpg(proc.pid,signal.SIGKILL);proc.communicate()
def run(key,variant='default'):
 p=packets[key]; profile=(REPO/'agent-profiles'/f"{p['role']}.toml").read_bytes(); config=tomllib.loads(profile.decode()); effort=config['model_reasoning_effort']
 if variant=='lower':effort='low' if key=='E' else 'medium'
 if variant in ('review-guidance','review-high'):effort='high'
 out=BASE/'runs'/f'{key}-{variant}';out.mkdir(parents=True,exist_ok=False);work=out/'workspace';shutil.copytree(BASE/'fixtures'/key,work)
 p=dict(p)
 if variant in ('review-guidance','review-high'):
  assert key=='V'
  refs=['skills/code-review/SKILL.md','skills/code-review-deep/SKILL.md','skills/code-review/references/integration-boundaries.md']
  (work/'REVIEW.md').write_text('\n\n'.join((REPO/x).read_text() for x in refs))
  p['task']+='\n本次審查也依 REVIEW.md 的適用規則執行；該檔包含當前 source 審查指引，引用的未附檔案不要求到 workspace 外讀取。'
  p['fixture_hashes']={str(f.relative_to(work)):digest(f.read_bytes()) for f in sorted(work.rglob('*')) if f.is_file()}
 (out/'profile.toml').write_bytes(profile);(out/'prompt.txt').write_text(p['task'])
 argv=[str(CLI),'exec','--ignore-user-config','--ephemeral','--json','--color','never','--sandbox',p['sandbox'],'--model',config['model'],'-c','model_reasoning_effort='+json.dumps(effort),'-c','developer_instructions='+json.dumps(config['developer_instructions']),'-c','sandbox_workspace_write.network_access=false','--skip-git-repo-check','-C',str(work),'-o',str(out/'final.txt'),'-']
 record={'packet':key,'variant':variant,'role':p['role'],'requested_model':config['model'],'requested_effort':effort,'sandbox':p['sandbox'],'profile_sha256':digest(profile),'developer_instructions_sha256':digest(config['developer_instructions'].encode()),'prompt_sha256':digest(p['task'].encode()),'fixture_hashes':p['fixture_hashes'],'cli_version':subprocess.run([str(CLI),'--version'],capture_output=True,text=True).stdout.strip(),'cli_before_discovery_path':str(DEFAULT_CLI),'cli_before_discovery_sha256':file_digest(DEFAULT_CLI),'cli_after_selection_path':str(CLI),'cli_after_selection_sha256':file_digest(CLI),'cli_sha256':file_digest(CLI),'cli_override':os.environ.get('CODEX_PILOT_CLI'),'dispatch':'explicit-cli-configuration-not-native-role','resolved_model_attestation':None,'argv':argv}
 (out/'invocation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 start=time.monotonic()
 with (out/'events.jsonl').open('w') as stdout,(out/'stderr.log').open('w') as stderr:
  proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,text=True,start_new_session=True)
  try:proc.communicate(p['task'],timeout=600)
  except subprocess.TimeoutExpired:stop_after_timeout(proc,record)
 record['exit_code']=proc.returncode;record['wall_seconds']=round(time.monotonic()-start,3)
 record['cli_sha256_after']=file_digest(CLI);record['cli_binary_drift']=record['cli_sha256']!=record['cli_sha256_after']
 raw=(out/'events.jsonl').read_bytes(); final=(out/'final.txt').read_bytes() if (out/'final.txt').is_file() else None
 record['event_evidence']=inspect(raw,final);record['usage']=record['event_evidence']['usage'];record['final_present']=final is not None
 record['after_hashes']={str(f.relative_to(work)):digest(f.read_bytes()) for f in sorted(work.rglob('*')) if f.is_file()}
 (out/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:record[k] for k in ('packet','variant','requested_model','requested_effort','exit_code','wall_seconds','usage','final_present')},ensure_ascii=False),flush=True)
 if proc.returncode!=0 or record.get('timeout') or record['cli_binary_drift'] or record['event_evidence']['stream_integrity']!='valid':raise SystemExit(proc.returncode or 1)
if __name__=='__main__':run(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else 'default')
