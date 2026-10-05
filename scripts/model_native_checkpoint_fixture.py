"""Fixed anonymous native update after the protected launcher has dropped privilege."""
import base64
import hashlib
import http.server
import io
import json
import os
import pathlib
import re
import stat
import sys
import threading
import time

PREFIX = b'ISSUE316-NATIVE-CHECKPOINT:'
CALL = {'type':'custom_tool_call','namespace':'functions','name':'apply_patch',
    'call_id':'native-checkpoint-update-1',
    'input':'*** Begin Patch\n*** Update File: /workspace/example.txt\n@@\n-old\n+new\n*** End Patch'}
DENIAL_LITERAL = 'Fixed anonymous default-mode probe.'


def stable_declaration(value):
    # Raw request identity changes after a tool result; tool declarations do not.
    if type(value) is not dict or 'request_sha256' not in value:
        raise ValueError('native-declaration-incomplete')
    return {key:item for key,item in value.items() if key != 'request_sha256'}


def turn_params(external, thread):
    return {'threadId':thread,
        'environments':[{'environmentId':'local','cwd':'/workspace','runtimeWorkspaceRoots':['/workspace']}],
        'input':[{'type':'text','text':'Perform the fixed anonymous fixture update.'}],
        'collaborationMode':external.input_mode(adopted=True)}


def response(stage):
    item = CALL if stage == 1 else {'type':'message','role':'assistant','id':'native-checkpoint-final',
        'content':[{'type':'output_text','text':'Fixed anonymous update finished.'}]}
    rows = [{'type':'response.created','response':{'id':'native-checkpoint-'+str(stage)}},
        {'type':'response.output_item.done','item':item},
        {'type':'response.completed','response':{'id':'native-checkpoint-'+str(stage),
            'usage':{'input_tokens':0,'output_tokens':0,'total_tokens':0}}}]
    return b''.join(('event: '+r['type']+'\ndata: '+json.dumps(r)+'\n\n').encode() for r in rows)


def output_valid(value):
    return type(value) is str and re.fullmatch(
        r'Exit code: 0\nWall time: (0|[1-9][0-9]?)(?:\.[0-9])? seconds\nOutput:\n'
        r'Success\. Updated the following files:\nM /workspace/example\.txt\n', value) is not None


def provider(external, state):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *unused): pass
        def setup(self):
            super().setup(); deadline = time.monotonic()+5
            self.rfile.close(); self.rfile = io.BufferedReader(external.base.guest.DeadlineReader(self.connection,deadline))
            self.wfile.close(); self.wfile = external.base.guest.DeadlineWriter(self.connection,deadline)
        def handle_one_request(self):
            before = state['slots']
            try: super().handle_one_request()
            finally:
                if state['slots'] == before: state['failed'] = True
        def send_error(self, *args, **kwargs):
            state['failed'] = True; return super().send_error(*args, **kwargs)
        def do_POST(self):
            state['slots'] += 1; stage = state['slots']
            try:
                lengths = self.headers.get_all('Content-Length',[])
                if (state['failed'] or stage not in (1,2) or self.path != '/v1/responses'
                        or self.headers.get_all('Authorization',[]) or self.headers.get_all('Transfer-Encoding',[])
                        or self.headers.get_all('Content-Encoding',['identity']) != ['identity']
                        or len(lengths) != 1 or not re.fullmatch(r'[1-9][0-9]{0,6}',lengths[0])):
                    raise ValueError('native-http-shape')
                length = int(lengths[0]); state['total_bytes'] += length
                if length > 1048576 or state['total_bytes'] > 2097152: raise ValueError('native-http-bound')
                raw = self.rfile.read(length); reply = response(stage)
                state['records'].append({'stage':stage,'request_base64':base64.b64encode(raw).decode(),
                    'request_sha256':hashlib.sha256(raw).hexdigest(),'request_bytes':len(raw),
                    'response_base64':base64.b64encode(reply).decode(),
                    'response_sha256':hashlib.sha256(reply).hexdigest(),'response_bytes':len(reply),'response_sent':False})
                if len(raw) != length: raise ValueError('native-http-incomplete')
                boundary = external.base.probe.boundary
                declaration = external.guest.declaration(raw,boundary,'workspace-patch')
                if stage == 1: state['declaration'] = declaration
                elif stable_declaration(declaration) != stable_declaration(state['declaration']):
                    raise ValueError('native-declaration-drift')
                if stage == 2:
                    state['native_output'] = boundary.output_text(boundary.find_output(boundary.manifest.decode(raw),CALL))
                    if not output_valid(state['native_output']): raise ValueError('native-output-drift')
                self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
                self.wfile.write(reply); self.wfile.flush(); state['records'][-1]['response_sent'] = True
            except Exception:
                state['failed'] = True; self.close_connection = True
                try: self.send_error(422)
                except Exception: pass
        def do_GET(self): self.send_error(405)
        def finish(self):
            try: super().finish()
            except Exception: state['failed'] = True
    return http.server.HTTPServer(('127.0.0.1',0),Handler)


def privileges():
    status = dict(line.split(':',1) for line in pathlib.Path('/proc/self/status').read_text().splitlines() if ':' in line)
    denied = False
    try: os.open('/control/input.json',os.O_RDONLY)
    except PermissionError: denied = True
    fds = []
    for name in os.listdir('/proc/self/fd'):
        try: target = os.readlink('/proc/self/fd/'+name)
        except FileNotFoundError: continue
        if int(name) > 2: fds.append(target)
    result = {'uid':list(os.getresuid()),'gid':list(os.getresgid()),'groups':os.getgroups(),
        'caps':{k:status[k].strip() for k in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb')},
        'nnp':status['NoNewPrivs'].strip(),'control_denied':denied,'extra_fds':fds}
    if (result['uid'] != [65534]*3 or result['gid'] != [65534]*3 or result['groups'] or fds
            or not denied or result['nnp'] != '1' or any(int(v,16) for v in result['caps'].values())):
        raise ValueError('native-privilege-drop-unproven')
    return result


def run():
    receipt = {'schema_version':1,'scope':'anonymous-native-checkpoint-worker-observation',
        'passed':False,'production_qualified':False}; session = server = serving = None; state = None
    try:
        case, nonce = sys.argv[1:]
        if case not in ('checkpoint','quarantine','claim-replay') or not re.fullmatch(r'[a-f0-9]{64}',nonce):
            raise ValueError('fixed-native-recipe-required')
        receipt.update(case=case,nonce=nonce,privileges=privileges())
        if dict(os.environ) != {'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp','LANG':'C.UTF-8'}:
            raise ValueError('native-worker-environment-drift')
        if sys.version_info[:3] != (3,12,9): raise ValueError('native-guest-python-drift')
        fixture = pathlib.Path('/fixture'); sys.path.insert(0,str(fixture/'scripts'))
        sys.path.insert(0,str(fixture/'skills/loop-engineering/scripts'))
        import model_external_bootstrap_fixture as old
        external = old.load('fixed_native_checkpoint_external',fixture/'scripts/verify-model-external-bootstrap.py')
        # Manifest remains an observation aid. Host capture/policy readback, not
        # this worker's self-report, establishes immutable source identity.
        manifest = external.helpers._reload_json(external.base.guest.read_regular(fixture/'guest-manifest.json',65536))
        for name,digest in manifest['sources'].items():
            if hashlib.sha256(external.base.guest.read_regular(fixture/name,1048576)).hexdigest() != digest:
                raise ValueError('native-guest-source-drift')
        binary = fixture/'codex'; value = os.lstat(binary)
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1 or stat.S_IMODE(value.st_mode) != 0o555:
            raise ValueError('native-guest-binary-shape')
        with binary.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest() != manifest['binary_sha256']:
                raise ValueError('native-guest-binary-drift')
        if (sorted(p.name for p in pathlib.Path('/workspace').iterdir()) != ['example.txt','remove.txt']
                or pathlib.Path('/workspace/example.txt').read_bytes() != b'old\n'
                or pathlib.Path('/workspace/remove.txt').read_bytes() != b'delete\n'
                or list(pathlib.Path('/tmp').iterdir())):
            raise ValueError('native-initial-workspace-drift')
        for name in ('home','home/.codex','registry','codex-daemon-65534'):
            (pathlib.Path('/tmp')/name).mkdir(mode=0o700)
        old.prepare_catalog(external.base,receipt)
        state = {'slots':0,'total_bytes':0,'failed':False,'records':[]}
        server = provider(external,state); serving = threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.05},daemon=True); serving.start()
        command = old.argv(external.base.probe.boundary,external.base.guest,port=server.server_port,native=True,case='workspace-patch')
        class Session(external.InputObservationSession): pass
        session = Session(command,cwd='/workspace',env=old.ENV,
            limits=external.base.probe.transport.Limits(timeout=10,close_timeout=5),
            admission_receipt={},allow_thread_settings_update=True,capture_stderr=True)
        external.bootstrap(session,receipt,case='input-disabled-dispatch')
        result = session.request('turn/start',turn_params(external,receipt['thread_id']))
        receipt['turn_id'] = result['turn']['id']
        for _ in range(256):
            note = session.notification()
            if note['method'] in ('error','model/rerouted') or 'requestApproval' in note['method']: raise ValueError('native-unexpected-activity')
            if note['method'] == 'turn/completed':
                if note['params']['turn']['status'] != 'completed': raise ValueError('native-turn-not-completed')
                break
        else: raise ValueError('native-turn-bound')
        session._drain_available(session._deadline())
        receipt['wire'] = session.wire
        receipt['client_close'] = session.close(); stderr = session.stderr_snapshot()
        stderr['raw_base64'] = base64.b64encode(stderr.pop('raw')).decode(); receipt['cli_stderr'] = stderr
        if (pathlib.Path('/workspace/example.txt').read_bytes() != b'new\n'
                or pathlib.Path('/workspace/remove.txt').read_bytes() != b'delete\n'):
            raise ValueError('native-postimage-drift')
        receipt['passed'] = True
        if case in ('quarantine','claim-replay'): time.sleep(20)  # Fixed bounded live post-write window.
    except Exception as error:
        receipt['failure_class'] = type(error).__name__
    finally:
        if session is not None and 'client_close' not in receipt:
            receipt['client_close'] = session.close(); receipt['wire'] = session.wire
        if server is not None:
            stopping = threading.Thread(target=server.shutdown,daemon=True); stopping.start(); stopping.join(6); serving.join(1)
            state['stopped'] = not stopping.is_alive() and not serving.is_alive(); server.server_close()
            if state['failed'] or state['slots'] != 2 or not state['stopped']: receipt['passed'] = False
            receipt['provider_bundle'] = external.guest.bundle(state)
        # The frame cannot authorize stop, checkpoint publication or integration.
        raw = json.dumps(receipt,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        import zlib
        compressed = zlib.compress(raw)
        if len(raw) > 1048576 or len(compressed) > 32768:
            raw = b'{"passed":false,"failure_class":"FrameBound"}'; compressed = zlib.compress(raw)
        sys.stdout.buffer.write(PREFIX+base64.b64encode(compressed)+b'\n'); sys.stdout.buffer.flush()
    return 0 if receipt['passed'] else 77


if __name__ == '__main__':
    raise SystemExit(run())
