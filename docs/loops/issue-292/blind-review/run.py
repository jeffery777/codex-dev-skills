from pathlib import Path
import os,sys,shutil,subprocess,tomllib,json,hashlib,time,signal
BASE=Path(os.environ['CODEX_REVIEW_PILOT_ROOT']).resolve()
REPO=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from event_evidence import inspect
DEFAULT_CLI=Path(shutil.which('codex') or '/nonexistent-codex').resolve();CLI=Path(os.environ.get('CODEX_PILOT_CLI',str(DEFAULT_CLI))).resolve()
ARMS={'sol-medium':('gpt-6-sol','medium'),'sol-high':('gpt-6-sol','high'),'astra-xhigh':('gpt-6-astra','xhigh')}
PROMPT='依 README.md 的契約及 REVIEW.md 的適用規則，唯讀審查 review_target.py、retention.py、maintenance.py 作為本次完整變更集。只回報有證據支持的 findings、severity、path:line、repro、實際 run/skip/fail 與限制，並區分維護建議和文件化設計取捨。不要修改 workspace，不讀父目錄、oracle、其他 runs 或外部資料，不派子代理，不安裝、不查網路。可在自己建立的 temporary directory 做受控重現，僅清理自己的產物；使用 ./scripts/project-python -B。以繁體中文回報。'
def sha(b):return hashlib.sha256(b).hexdigest()
def file_digest(path):return sha(path.read_bytes()) if path.is_file() else None
def stop_after_timeout(proc,record):
 record['timeout']={'limit_seconds':600,'signal':'SIGTERM','grace_seconds':15}
 os.killpg(proc.pid,signal.SIGTERM)
 try:proc.communicate(timeout=15)
 except subprocess.TimeoutExpired:
  record['timeout']['grace_expired']=True;record['timeout']['final_signal']='SIGKILL';os.killpg(proc.pid,signal.SIGKILL);proc.communicate()
def hashes(d):return {str(p.relative_to(d)):sha(p.read_bytes()) for p in sorted(d.rglob('*')) if p.is_file()}
def main(variant,arm):
 manifest=json.loads((BASE/'manifest.json').read_text());src=BASE/'fixtures'/variant;assert hashes(src)==manifest['variants'][variant]['files']
 d=BASE/'runs'/f'{variant}-{arm}';d.mkdir(parents=True,exist_ok=False);w=d/'workspace';shutil.copytree(src,w)
 model,effort=ARMS[arm];profile=(REPO/'agent-profiles/loop_v2a_routine_reviewer.toml').read_bytes();dev=tomllib.loads(profile.decode())['developer_instructions']
 argv=[str(CLI),'exec','--ignore-user-config','--ephemeral','--json','--color','never','--sandbox','read-only','--model',model,'-c','model_reasoning_effort='+json.dumps(effort),'-c','developer_instructions='+json.dumps(dev),'--skip-git-repo-check','-C',str(w),'-o',str(d/'final.txt'),'-']
 r={'variant':variant,'arm':arm,'requested_model':model,'requested_effort':effort,'sandbox':'read-only','developer_instructions_sha256':sha(dev.encode()),'source_prompt_profile_sha256':sha(profile),'prompt_sha256':sha(PROMPT.encode()),'fixture_hashes':hashes(w),'cli_version':subprocess.run([str(CLI),'--version'],capture_output=True,text=True).stdout.strip(),'cli_before_discovery_path':str(DEFAULT_CLI),'cli_before_discovery_sha256':file_digest(DEFAULT_CLI),'cli_after_selection_path':str(CLI),'cli_after_selection_sha256':file_digest(CLI),'cli_sha256':file_digest(CLI),'cli_override':os.environ.get('CODEX_PILOT_CLI'),'dispatch':'explicit-cli-evaluation-not-native-custom-role','resolved_model_attestation':None,'argv':argv}
 (d/'invocation.json').write_text(json.dumps(r,indent=2)+'\n');(d/'prompt.txt').write_text(PROMPT);start=time.monotonic()
 with (d/'events.jsonl').open('w') as out,(d/'stderr.log').open('w') as err:
  proc=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,start_new_session=True)
  try:proc.communicate(PROMPT,timeout=600)
  except subprocess.TimeoutExpired:stop_after_timeout(proc,r)
 r['exit_code']=proc.returncode;r['wall_seconds']=round(time.monotonic()-start,3);r['after_hashes']=hashes(w)
 r['cli_sha256_after']=file_digest(CLI);r['cli_binary_drift']=r['cli_sha256']!=r['cli_sha256_after']
 raw=(d/'events.jsonl').read_bytes();final=(d/'final.txt').read_bytes() if (d/'final.txt').is_file() else None;r['event_evidence']=inspect(raw,final);r['usage']=r['event_evidence']['usage'];r['final_present']=final is not None
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ('variant','arm','exit_code','wall_seconds','usage','final_present')}),flush=True)
 if proc.returncode!=0 or r.get('timeout') or r['cli_binary_drift'] or r['event_evidence']['stream_integrity']!='valid':raise SystemExit(proc.returncode or 1)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
