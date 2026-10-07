#!/usr/bin/env python3
"""Opt-in synthetic Responses fixture for native CLI shell/patch boundaries.

No real model, account authentication, repository or production adapter is used.
A successful fixture only proves the measured local tool paths. Unparsed native
model guidance requires explicit opt-in and can never qualify a tool manifest.
"""
import argparse
import hashlib
import http.server
import importlib.util
import json
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def tools_by_name(entries, namespace=None):
    found = []
    for entry in entries:
        if entry.get('type') == 'namespace':
            found.extend(tools_by_name(entry.get('tools', []), entry.get('name')))
        elif entry.get('type') in {'function', 'custom'}:
            found.append((entry['name'], namespace, entry['type']))
    return found


def reader_guard(reader='/bin/cat'):
    """Positive control in the same shell/sandbox as the forbidden read."""
    return ('test "$(' + shlex.quote(reader) + ' reader-sentinel)" = reader-ok || exit 12; '
            'echo verified > reader-verified; ')


def hook_source(case, marker):
    """Trusted synthetic hook; never derived from a provider request."""
    bodies = {
        'deny': 'print(json.dumps({"hookSpecificOutput":{"hookEventName":"PreToolUse",'
            '"permissionDecision":"deny","permissionDecisionReason":"synthetic-deny"}}))',
        'exit1': 'sys.exit(1)',
        'exit2-empty': 'sys.exit(2)',
        'invalid-json': 'print("{")',
        'timeout': 'time.sleep(3)',
    }
    if case not in bodies:
        raise ValueError('unsupported-hook-case')
    return ('import json,pathlib,sys,time\n'
            'with pathlib.Path(' + repr(str(marker)) + ').open("a") as stream: stream.write("invoked\\n")\n'
            + bodies[case] + '\n')


def patch_output_kind(output):
    """Recognize only measured CLI boundary results, not arbitrary errors."""
    if not isinstance(output, str):
        return 'unknown'
    if output.startswith('Command blocked by PreToolUse hook: synthetic-deny. Command: '):
        return 'hook-denied'
    if output == 'patch rejected: writing is blocked by read-only sandbox; rejected by user approval settings':
        return 'readonly-denied'
    if (output.startswith('apply_patch verification failed: Failed to read file to update ')
            and output.endswith(': Operation not permitted (os error 1)')):
        return 'read-denied'
    if output.startswith('Success. Updated the following files:'):
        return 'applied'
    return 'unknown'


def patch_boundary_observed(requests, *, readonly, hook_fault):
    kinds = [item.get('patch_output_kind', 'unknown') for item in requests[1:]]
    if len(kinds) != 2:
        return False
    if hook_fault == 'deny':
        return kinds == ['hook-denied', 'hook-denied']
    return kinds == (['readonly-denied', 'read-denied'] if readonly else ['applied', 'read-denied'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    parser.add_argument('--case', choices=['shell', 'patch'], required=True)
    parser.add_argument('--metadata-model', default='mock-model', help='Local CLI metadata only; this model is never contacted.')
    parser.add_argument('--allow-unparsed-native-fixture', action='store_true')
    parser.add_argument('--hook-fault', choices=['deny', 'exit1', 'exit2-empty', 'invalid-json', 'timeout'])
    parser.add_argument('--host-read-only', action='store_true')
    args = parser.parse_args()
    if (args.hook_fault or args.host_read_only) and args.case != 'patch':
        parser.error('hook and read-only controls require the patch case')
    base = args.evidence_root.resolve(strict=True)
    if any(char in str(base) for char in ['\n', '\r']):
        parser.error('evidence path cannot contain line breaks')
    if not base.is_dir() or any((p / '.git').exists() for p in [base, *base.parents]):
        parser.error('existing evidence directory outside Git required')
    executable = shutil.which('codex')
    if not executable:
        parser.error('installed Codex CLI required')
    real_executable = pathlib.Path(executable).resolve(strict=True)
    executable = str(real_executable)
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-dispatch-', dir=base))
    work, home, control = [root / name for name in ['workspace', 'home', 'control']]
    for folder in [work, home, control]:
        folder.mkdir()
    spec = importlib.util.spec_from_file_location('broker_probe', pathlib.Path(__file__).with_name('verify-model-broker.py'))
    broker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(broker)
    broker.audit_client_directory(work)
    (control / 'sentinel').write_text('synthetic')
    (work / 'reader-sentinel').write_text('reader-ok')
    receipt = {'schema_version': 1, 'scope': 'synthetic-cli-' + args.case + '-dispatch',
        'fixture': str(root), 'requests': [], 'production_qualified': False,
        'executable_sha256': hashlib.sha256(real_executable.read_bytes()).hexdigest(),
        'metadata_model': args.metadata_model, 'unparsed_native_fixture_allowed': args.allow_unparsed_native_fixture}
    limit = 2 if args.case == 'shell' else 3

    class Handler(http.server.BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *unused):
            pass

        def do_GET(self):
            self.send_error(404)

        def do_POST(self):
            if self.path != '/v1/responses':
                self.send_error(404)
                return
            if self.headers.get('Content-Encoding', 'identity') != 'identity':
                self.send_error(415)
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 1024 * 1024:
                    raise ValueError('bounded body required')
                value = json.loads(self.rfile.read(length))
                (root / ('request-' + str(len(receipt['requests']) + 1) + '.json')).write_text(json.dumps(value, sort_keys=True) + '\n')
                catalog = tools_by_name(value.get('tools', []))
                stage = len(receipt['requests']) + 1
                entry = {'stage': stage, 'tools_sha256': digest(value.get('tools', [])),
                    'tool_names': [name for name, _, _ in catalog], 'input_sha256': digest(value.get('input', []))}
                if stage > limit:
                    self.send_error(409)
                    return
                if stage > 1:
                    previous_id = 'fixture-call-' + str(stage - 1)
                    output = next((item for item in value.get('input', [])
                        if item.get('call_id') == previous_id and item.get('type') in
                        {'function_call_output', 'custom_tool_call_output'}), None)
                    if output is None:
                        self.send_error(422)
                        return
                    entry['tool_output_sha256'] = digest(output)
                    if args.case == 'patch':
                        entry['patch_output_kind'] = patch_output_kind(output.get('output'))
                receipt['requests'].append(entry)
                if stage < limit:
                    expected = 'exec_command' if args.case == 'shell' else 'apply_patch'
                    selected = next((item for item in catalog if item[0] == expected), None)
                    if selected is None:
                        # Experimental evidence only: do not claim manifest qualification.
                        if not args.allow_unparsed_native_fixture or expected not in json.dumps(value.get('input', [])):
                            self.send_error(422)
                            return
                        selected = (expected, None, 'function' if args.case == 'shell' else 'custom')
                        entry['manifest_resolution'] = 'unparsed-native-guidance'
                    else:
                        entry['manifest_resolution'] = 'request-tools'
                    name, namespace, kind = selected
                    item = {'call_id': 'fixture-call-' + str(stage), 'name': name}
                    if namespace is not None:
                        item['namespace'] = namespace
                    if args.case == 'shell' and kind == 'function':
                        command = (reader_guard() + 'echo allowed > result; if /bin/cat ' + shlex.quote(str(control / 'sentinel')) +
                            ' >/dev/null 2>&1; then echo read-violation > violation; fi; if echo bad > ' +
                            shlex.quote(str(control / 'sentinel')) + ' 2>/dev/null; then echo write-violation > violation; fi')
                        item.update(type='function_call', arguments=json.dumps({'cmd': command, 'login': False}))
                    elif args.case == 'patch' and kind == 'custom':
                        patch = ('*** Begin Patch\n*** Add File: allowed-patch.txt\n+synthetic-patch\n*** End Patch'
                            if stage == 1 else '*** Begin Patch\n*** Update File: ' + str(control / 'sentinel') +
                            '\n@@\n-synthetic\n+forbidden-patch\n*** End Patch')
                        item.update(type='custom_tool_call', input=patch)
                    else:
                        self.send_error(422)
                        return
                else:
                    item = {'type': 'message', 'role': 'assistant', 'id': 'fixture-final',
                        'content': [{'type': 'output_text', 'text': 'Synthetic fixture complete.'}]}
                events = [
                    {'type': 'response.created', 'response': {'id': 'fixture-response-' + str(stage)}},
                    {'type': 'response.output_item.done', 'item': item},
                    {'type': 'response.completed', 'response': {'id': 'fixture-response-' + str(stage),
                        'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}}]
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.end_headers()
                for event in events:
                    self.wfile.write(('event: ' + event['type'] + '\ndata: ' + json.dumps(event) + '\n\n').encode())
            except (ValueError, KeyError, TypeError, AttributeError):
                self.send_error(400)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    server.timeout = 5
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
        str(work): 'read' if args.host_read_only else 'write', str(work / '.git'): 'read', str(work / '.codex'): 'deny',
        str(home): 'deny', str(control): 'deny', executable: 'read', str(real_executable): 'read',
        str(pathlib.Path(executable).parent): 'read', str(real_executable.parent): 'read'}
    config = 'permissions.probe.filesystem={' + ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in permissions.items()) + '}'
    provider = ('model_providers.fixture={name="Synthetic",base_url="http://127.0.0.1:' +
        str(server.server_port) + '/v1",wire_api="responses",requires_openai_auth=false,'
        'supports_websockets=false,request_max_retries=0,stream_max_retries=0,stream_idle_timeout_ms=5000}')
    settings = ['model_provider="fixture"', provider, 'model=' + json.dumps(args.metadata_model),
        'default_permissions="probe"', config, 'permissions.probe.network.enabled=false',
        'approval_policy="never"', 'shell_environment_policy.inherit="none"', 'web_search="disabled"',
        'features.apps=false', 'features.hooks=false', 'features.multi_agent=false', 'features.goals=false',
        'features.memories=false', 'features.enable_request_compression=false',
        *['features.' + key + '=false' for key in broker.DISABLED_FEATURES
            if key not in {'shell_tool', 'unified_exec', 'hooks', 'apps', 'multi_agent', 'goals', 'memories'}]]
    argv = [executable, 'exec', '--strict-config', '--ignore-user-config', '--ignore-rules', '--skip-git-repo-check', '--json', '-C', str(work)]
    if args.hook_fault:
        hook = control / 'hook.py'
        hook.write_text(hook_source(args.hook_fault, control / 'hook-invoked'))
        hook.chmod(0o400)
        hook_command = shlex.join([sys.executable, '-I', str(hook)])
        settings = [setting for setting in settings if setting != 'features.hooks=false']
        settings += ['features.hooks=true', 'hooks={PreToolUse=[{matcher="apply_patch",hooks=[{type="command",command='
            + json.dumps(hook_command) + ',timeout=1}]}]}']
        # Only this fixed, locally written hook is trusted for the experiment.
        # OS permissions still enforce the host boundary when the hook fails.
        argv += ['--dangerously-bypass-hook-trust']
        receipt.update(hook_fault=args.hook_fault, hook_sha256=hashlib.sha256(hook.read_bytes()).hexdigest())
    receipt['host_read_only'] = args.host_read_only
    for setting in settings:
        argv += ['-c', setting]
    argv += ['Synthetic local tool-dispatch fixture. Only perform the bounded fixture operations.']
    env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(home),
        'NO_PROXY': '127.0.0.1,localhost', 'no_proxy': '127.0.0.1,localhost'}
    start = time.monotonic()
    try:
        broker.audit_client_directory(work)
        run = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=30)
        (root / 'stdout.log').write_text(run.stdout)
        (root / 'stderr.log').write_text(run.stderr)
        result = work / ('result' if args.case == 'shell' else 'allowed-patch.txt')
        receipt['checks'] = {'cli_exited_successfully': run.returncode == 0,
            'tool_roundtrip_observed': len(receipt['requests']) == limit and all(
                'tool_output_sha256' in item for item in receipt['requests'][1:]),
            'reader_positive_control': (work / 'reader-verified').exists() if args.case == 'shell' else None,
            'allowed_result': (not result.exists() if args.host_read_only or args.hook_fault == 'deny' else
                result.exists() and result.read_text().strip() == ('allowed' if args.case == 'shell' else 'synthetic-patch')),
            'hook_positive_control': (control / 'hook-invoked').is_file() if args.hook_fault else None,
            'patch_boundary_observed': patch_boundary_observed(receipt['requests'],
                readonly=args.host_read_only, hook_fault=args.hook_fault) if args.case == 'patch' else None,
            'forbidden_preserved': (control / 'sentinel').read_text() == 'synthetic',
            'forbidden_read_rejected': not (work / 'violation').exists() if args.case == 'shell' else None}
        return 0 if all(value is not False for value in receipt['checks'].values()) else 1
    except subprocess.TimeoutExpired as error:
        for name, partial in [('stdout', error.stdout), ('stderr', error.stderr)]:
            if partial is not None:
                (root / (name + '.log')).write_bytes(partial if isinstance(partial, bytes) else partial.encode())
        receipt.update(error='cli-root-timeout', execution_outcome='unknown', descendant_state='unknown', independent_readback_required=True)
        return 1
    except (OSError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error)
        return 1
    finally:
        server.shutdown()
        server.server_close()
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 2)
        output = root / 'dispatch-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), **receipt}, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
