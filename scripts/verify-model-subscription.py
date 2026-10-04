#!/usr/bin/env python3
"""Opt-in official subscription smoke test; never a production qualification.

Uses the existing public CLI login, without reading or copying credentials.
Only a fixed synthetic prompt is sent. The operator must bind the reviewed
user AGENTS instructions digest, since ignore-user-config does not remove them.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

MARKER = 'subscription-probe-ok'
PROMPT = 'Do not use any tools. Reply with exactly: ' + MARKER


def environment(home, codex_home):
    # No API key, alternate endpoint, credentials or ambient proxy forwarding.
    return {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(codex_home),
        'PYTHONDONTWRITEBYTECODE': '1'}


def login_is_subscription(result):
    value = result.stdout + result.stderr
    return result.returncode == 0 and 'ChatGPT' in value and 'API key' not in value


def parse_events(raw):
    if len(raw) > 1024 * 1024:
        raise ValueError('oversized event stream')
    try:
        events = [json.loads(line) for line in raw.splitlines() if line.strip()]
    except (ValueError, UnicodeError):
        raise ValueError('invalid event stream')
    if not events or any(type(event) is not dict for event in events):
        raise ValueError('invalid event shape')
    allowed = {'thread.started', 'turn.started', 'turn.completed', 'turn.failed', 'error',
        'item.started', 'item.updated', 'item.completed'}
    for event in events:
        kind = event.get('type')
        if not isinstance(kind, str) or kind not in allowed or ('item' in event and not kind.startswith('item.')):
            raise ValueError('unknown event type')
        if kind.startswith('item.') and type(event.get('item')) is not dict:
            raise ValueError('invalid item shape')
        if kind.startswith('item.') and not isinstance(event['item'].get('type'), str):
            raise ValueError('invalid item type')
    return events


def event_items(events):
    return [event['item'] for event in events if event['type'].startswith('item.')]


def validate_events(raw):
    try:
        events = parse_events(raw)
    except ValueError:
        return False
    items = event_items(events)
    # CLI also emits diagnostic items (type=error). They are not tool dispatch
    # events; retain their count separately and never treat this smoke result as
    # clean runtime qualification. A failed turn or top-level error still fails.
    if any(type(item) is not dict or item.get('type') not in {'agent_message', 'reasoning', 'error'} for item in items):
        return False
    messages = [event['item'].get('text') for event in events
        if event.get('type') == 'item.completed' and event['item'].get('type') == 'agent_message']
    return (messages == [MARKER] and any(event.get('type') == 'turn.completed' for event in events)
            and not any(event.get('type') in {'error', 'turn.failed'} for event in events))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--instructions-sha256', required=True)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    args = parser.parse_args()
    base = args.evidence_root.resolve(strict=True)
    if not base.is_relative_to('/private/tmp') or any((p / '.git').exists() for p in [base, *base.parents]):
        parser.error('evidence root under /private/tmp outside Git required')
    home = pathlib.Path.home().resolve(strict=True)
    codex_home = pathlib.Path(os.environ.get('CODEX_HOME', str(home / '.codex'))).resolve(strict=True)
    instructions = codex_home / 'AGENTS.md'
    if (instructions.is_symlink() or not instructions.is_file()
            or (codex_home / 'AGENTS.override.md').exists()
            or hashlib.sha256(instructions.read_bytes()).hexdigest() != args.instructions_sha256):
        parser.error('reviewed user instructions binding required')
    catalog_path = codex_home / 'models_cache.json'
    catalog_raw = catalog_path.read_bytes()
    models = [entry for entry in json.loads(catalog_raw)['models'] if entry['slug'] == args.model]
    if len(models) != 1 or models[0].get('visibility') != 'list':
        parser.error('requested model must be in current CLI catalog')
    executable = str(pathlib.Path(shutil.which('codex')).resolve(strict=True))
    env = environment(home, codex_home)
    login = subprocess.run([executable, 'login', 'status'], env=env, capture_output=True, text=True, timeout=15)
    if not login_is_subscription(login):
        parser.error('existing subscription login required; no login mutation or API fallback')
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-subscription-', dir=base))
    root.chmod(0o700)
    client = root / 'client'
    client.mkdir(mode=0o500)
    catalog_snapshot = root / 'catalog.json'
    catalog_snapshot.write_bytes(catalog_raw)
    catalog_snapshot.chmod(0o400)
    source = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location('broker_probe', source / 'verify-model-broker.py')
    broker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(broker)
    broker.audit_client_directory(client)
    permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny', ':slash_tmp': 'deny',
        str(client): 'read', str(codex_home): 'deny', executable: 'read',
        str(pathlib.Path(executable).parent): 'read'}
    fs = ','.join(json.dumps(key) + '=' + json.dumps(value) for key, value in permissions.items())
    settings = ['model_provider="openai"', 'forced_login_method="chatgpt"',
        'model=' + json.dumps(args.model), 'model_reasoning_effort="low"',
        'model_catalog_json=' + json.dumps(str(catalog_snapshot)),
        'default_permissions="probe"', 'permissions.probe.filesystem={' + fs + '}',
        'permissions.probe.network.enabled=false', 'approval_policy="never"',
        'shell_environment_policy.inherit="none"', 'web_search="disabled"',
        *['features.' + key + '=false' for key in broker.DISABLED_FEATURES]]
    argv = [executable, 'exec', '--strict-config', '--ignore-user-config', '--ignore-rules',
        '--skip-git-repo-check', '--ephemeral', '--json', '-C', str(client)]
    for setting in settings:
        argv += ['-c', setting]
    argv += [PROMPT]
    receipt = {'schema_version': 1, 'scope': 'official-subscription-fixed-prompt-only',
        'requested_model': args.model, 'catalog_sha256': hashlib.sha256(catalog_raw).hexdigest(),
        'instructions_sha256': args.instructions_sha256, 'subscription_login_observed': True,
        'executable_sha256': hashlib.sha256(pathlib.Path(executable).read_bytes()).hexdigest(),
        'settings_sha256': hashlib.sha256(json.dumps(settings).encode()).hexdigest(),
        'production_qualified': False, 'repository_completion': False,
        'unknown': ['independent-provider-model-readback', 'role-quality', 'full-context-enforcement',
            'credential-broker', 'company-provider', 'complete-tool-isolation', 'client-diagnostic-resolution']}
    try:
        # No raw client logs or authentication error text is retained.
        run = subprocess.run(argv, env=env, cwd=client, capture_output=True, timeout=60, close_fds=True)
        receipt['stdout_sha256'] = hashlib.sha256(run.stdout).hexdigest()
        if len(run.stdout) <= 1024 * 1024:
            events = parse_events(run.stdout)
            items = event_items(events)
            # Shape-only diagnostics: never retain reply text or auth errors.
            receipt['completed_message_count'] = sum(event.get('type') == 'item.completed'
                and event.get('item', {}).get('type') == 'agent_message' for event in events)
            receipt['tool_item_count'] = sum(item.get('type') not in
                {'agent_message', 'reasoning', 'error'} for item in items)
            receipt['client_diagnostic_count'] = sum(event.get('type') == 'item.completed'
                and event.get('item', {}).get('type') == 'error' for event in events)
            receipt['metadata_warning_observed'] = any(event.get('type') == 'item.completed'
                and event.get('item', {}).get('type') == 'error'
                and event['item'].get('message', '').startswith('Model metadata for') for event in events)
            known = {'agent_message', 'reasoning', 'error', 'command_execution', 'mcp_tool_call',
                'file_change', 'todo_list', 'web_search'}
            receipt['observed_item_types'] = sorted({item.get('type')
                if item.get('type') in known else 'other' for item in items})
            receipt['marker_response_observed'] = any(event.get('type') == 'item.completed'
                and event.get('item', {}).get('type') == 'agent_message'
                and event['item'].get('text') == MARKER for event in events)
        receipt['checks'] = {'cli_success': run.returncode == 0,
            'fixed_response_and_no_tool_events': validate_events(run.stdout)}
        return 0 if all(receipt['checks'].values()) else 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        receipt.update(outcome='unknown', error_type=type(error).__name__, independent_readback_required=True)
        return 1
    finally:
        output = root / 'subscription-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), 'checks': receipt.get('checks'),
            'error_type': receipt.get('error_type'), 'production_qualified': False}))


if __name__ == '__main__':
    raise SystemExit(main())
