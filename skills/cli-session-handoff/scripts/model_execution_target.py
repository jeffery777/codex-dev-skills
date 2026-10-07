"""Protected, opt-in typed targets for one existing CLI start executor.

Protected summaries are trusted operator inputs, not independent authorization,
qualification, runtime readback, or evidence of a provider actually being used.
No network, login mutation, auth.json/.env parsing, or credential persistence.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time
import tomllib
import urllib.parse
from dataclasses import dataclass

import agent_qualification as trust
import agent_routing
import profile_preflight as profiles

STORE = 'model-execution-targets.json'
ARTIFACT_PREFIX = 'model-execution/'
MAX_RECORDS = 32
TTL = 300
PUBLIC_KEYS = {'model', 'model_reasoning_effort', 'model_provider', 'model_providers',
               'model_catalog_json', 'model_context_window', 'model_auto_compact_token_limit',
               'developer_instructions', 'forced_login_method', 'shell_environment_policy.exclude'}
RECORD_KEYS = {'id', 'enabled', 'expires_at', 'task', 'provider', 'model', 'reasoning_effort',
               'runtime', 'canonical_profile', 'effective_profile', 'catalog', 'summaries'}
COMMON = {'schema_version', 'status', 'identity_sha256', 'task_sha256', 'observed_at', 'expires_at'}
CORE_ENV = {'PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'TMPDIR', 'TEMP', 'TMP', 'LANG', 'TZ',
            'SYSTEMROOT', 'WINDIR'}
SECRET_ENV = re.compile(r'(?i)(?:key|token|secret|password|credential|authorization|cookie)')
SECRET_TEXT = re.compile(r'(?i)(?:\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]{8,}|\bgh[pousr]_[A-Za-z0-9]{12,})')
ID = re.compile(r'[A-Za-z0-9_.-]{1,100}\Z')
MODEL = re.compile(r'[A-Za-z0-9_./:-]{1,120}\Z')


class TargetError(ValueError):
    """Only fixed, non-sensitive reason identifiers are exposed."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def obj(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise TargetError('invalid-target-schema')
    return value


def text(value):
    if type(value) is not str or not value.strip() or len(value) > 256 or SECRET_TEXT.search(value):
        raise TargetError('invalid-target-string')


def digest(value):
    if type(value) is not str or not trust.SHA.fullmatch(value):
        raise TargetError('invalid-target-digest')


def integer(value):
    if type(value) is not int or not 0 <= value <= 10**12:
        raise TargetError('invalid-target-integer')


def decode(raw):
    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=trust._pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(TargetError('nonfinite-target-json')))
    except (ValueError, UnicodeError, RecursionError):
        raise TargetError('invalid-target-json') from None


def root():
    return pathlib.Path(os.environ.get('CODEX_HOME', str(pathlib.Path.home()/'.codex')))


def _artifact(home, ref, *, limit=trust.MAX_EVIDENCE_BYTES):
    obj(ref, {'path', 'sha256'}); digest(ref['sha256'])
    path = ref['path']
    if type(path) is not str or not path.startswith(ARTIFACT_PREFIX) or '\\' in path or len(path) > 240:
        raise TargetError('unsafe-target-artifact')
    parts = path.split('/')
    if any(part in {'', '.', '..', '.git', '.env', 'auth.json', 'config.toml'} or part.startswith('.') for part in parts):
        raise TargetError('unsafe-target-artifact')
    fd = trust._directory(home.joinpath(*parts[:-1]))
    try:
        raw = trust._read(fd, parts[-1], limit)
    finally:
        os.close(fd)
    if sha(raw) != ref['sha256']:
        raise TargetError('target-artifact-drift')
    return raw


def _provider(p):
    obj(p, {'id', 'billing', 'base_url', 'wire_api', 'env_key'})
    if type(p['id']) is not str or not ID.fullmatch(p['id']):
        raise TargetError('invalid-target-provider')
    if p['billing'] == 'chatgpt-subscription':
        if p != {'id': 'openai', 'billing': 'chatgpt-subscription', 'base_url': None, 'wire_api': 'responses', 'env_key': None}:
            raise TargetError('official-subscription-provider-required')
        return
    if p['billing'] != 'internal' or p['id'] == 'openai' or p['wire_api'] != 'responses':
        raise TargetError('unsupported-target-provider')
    if type(p['base_url']) is not str or len(p['base_url']) > 512:
        raise TargetError('invalid-provider-url')
    try:
        url = urllib.parse.urlsplit(p['base_url'])
        port = url.port
    except ValueError:
        raise TargetError('invalid-provider-url') from None
    if not url.hostname or url.username or url.password or url.query or url.fragment or '\\' in p['base_url'] or any(c.isspace() for c in p['base_url']):
        raise TargetError('invalid-provider-url')
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in {'localhost', '127.0.0.1', '::1'}):
        raise TargetError('unsafe-provider-transport')
    if SECRET_TEXT.search(urllib.parse.unquote(p['base_url'])):
        raise TargetError('provider-config-contains-secret')
    if port is not None and port == 0:
        raise TargetError('invalid-provider-url')
    env = p['env_key']
    if type(env) is not str or not re.fullmatch(r'[A-Z][A-Z0-9_]{0,99}(?:_KEY|_TOKEN)', env) or env in {'OPENAI_API_KEY', 'CODEX_API_KEY'} or env.startswith('OPENAI_'):
        raise TargetError('unsafe-provider-credential-selector')


def identity(record):
    return {'provider_sha256': canonical_sha(record['provider']), 'model': record['model'],
            'reasoning_effort': record['reasoning_effort'], 'runtime': record['runtime'],
            'role': record['task']['role'], 'canonical_profile_sha256': record['canonical_profile']['sha256'],
            'effective_profile_sha256': record['effective_profile']['sha256'],
            'catalog_sha256': record['catalog']['sha256']}


@dataclass(frozen=True)
class Binding:
    target_id: str
    store_sha256: str
    binding_sha256: str
    identity_sha256: str
    task_sha256: str
    root: pathlib.Path
    config: tuple[str, ...]
    credential_env: str | None
    subscription: bool
    profile_instructions: str
    planner_identity: tuple[tuple[str, str], ...]
    catalog_bytes: bytes
    task_id: str
    scope: str
    acceptance_sha256: str
    role: str
    checkpoint_sha256: str | None
    valid_from: int
    valid_until: int

    def reference(self):
        return {'schema_version': 1, 'id': self.target_id, 'store_sha256': self.store_sha256,
                'binding_sha256': self.binding_sha256}


def preprobe(ref, *, prompt, expected_head, executable_sha256, sandbox, now=None):
    """Approve the exact executable and all target prerequisites before --version.

    The protected capability summary supplies the expected public CLI version;
    this approval is followed by an actual bounded version probe and full resolve.
    """
    try:
        obj(ref, {'schema_version', 'id', 'store_sha256', 'binding_sha256'})
        digest(ref['store_sha256']); digest(ref['binding_sha256'])
        home = root(); fd = trust._directory(home)
        try:
            raw = trust._read(fd, STORE, trust.MAX_STORE_BYTES)
        finally:
            os.close(fd)
        if sha(raw) != ref['store_sha256']:
            raise TargetError('target-store-drift')
        store = obj(decode(raw), {'schema_version', 'enabled', 'targets'})
        if type(store['targets']) is not list or not 1 <= len(store['targets']) <= MAX_RECORDS:
            raise TargetError('invalid-target-list')
        candidates = [item for item in store['targets'] if type(item) is dict and item.get('id') == ref['id']]
        if len(candidates) != 1 or canonical_sha(candidates[0]) != ref['binding_sha256']:
            raise TargetError('target-binding-drift')
        cap = decode(_artifact(home, candidates[0]['summaries']['capability'], limit=trust.MAX_STORE_BYTES))
        if type(cap) is not dict or type(cap.get('cli_version')) is not str or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?', cap['cli_version']):
            raise TargetError('target-public-executor-unsupported')
        return resolve(ref, prompt=prompt, expected_head=expected_head, executable_sha256=executable_sha256,
                       cli_version=cap['cli_version'], sandbox=sandbox, now=now)
    except TargetError:
        raise
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise TargetError('untrusted-or-unavailable-target') from None


def resolve(ref, *, prompt, expected_head, executable_sha256, cli_version, sandbox, now=None):
    """Resolve a protected binding; callers still own real authority and dispatch."""
    try:
        return _resolve(ref, prompt=prompt, expected_head=expected_head,
                        executable_sha256=executable_sha256, cli_version=cli_version,
                        sandbox=sandbox, now=int(time.time()) if now is None else now)
    except TargetError:
        raise
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise TargetError('untrusted-or-unavailable-target') from None


def _resolve(ref, *, prompt, expected_head, executable_sha256, cli_version, sandbox, now):
    obj(ref, {'schema_version', 'id', 'store_sha256', 'binding_sha256'})
    if type(ref['schema_version']) is not int or ref['schema_version'] != 1 or type(ref['id']) is not str or not ID.fullmatch(ref['id']):
        raise TargetError('invalid-target-reference')
    text(ref['id'])
    digest(ref['store_sha256']); digest(ref['binding_sha256']); integer(now)
    home = root(); fd = trust._directory(home)
    try:
        raw = trust._read(fd, STORE, trust.MAX_STORE_BYTES)
    finally:
        os.close(fd)
    if sha(raw) != ref['store_sha256']:
        raise TargetError('target-store-drift')
    store = obj(decode(raw), {'schema_version', 'enabled', 'targets'})
    if type(store['schema_version']) is not int or store['schema_version'] != 1 or type(store['enabled']) is not bool:
        raise TargetError('invalid-target-store')
    if not store['enabled']:
        raise TargetError('target-store-disabled')
    if type(store['targets']) is not list or not 1 <= len(store['targets']) <= MAX_RECORDS:
        raise TargetError('invalid-target-list')
    seen = set(); record = None
    for candidate in store['targets']:
        obj(candidate, RECORD_KEYS)
        if type(candidate['id']) is not str or not ID.fullmatch(candidate['id']) or candidate['id'] in seen:
            raise TargetError('invalid-target-id')
        seen.add(candidate['id'])
        if candidate['id'] == ref['id']:
            record = candidate
    if record is None or canonical_sha(record) != ref['binding_sha256']:
        raise TargetError('target-binding-drift')
    if type(record['enabled']) is not bool or not record['enabled']:
        raise TargetError('target-revoked')
    integer(record['expires_at'])
    if record['expires_at'] <= now:
        raise TargetError('target-expired')
    task = obj(record['task'], {'route_task', 'acceptance_sha256', 'prompt_sha256', 'expected_head', 'role', 'checkpoint_sha256'})
    if task['checkpoint_sha256'] is not None:
        digest(task['checkpoint_sha256'])
    for key in ['acceptance_sha256', 'prompt_sha256']:
        digest(task[key])
    text(task['role'])
    if task['prompt_sha256'] != sha(prompt.encode()) or task['expected_head'] != expected_head:
        raise TargetError('target-task-drift')
    route_task = obj(task['route_task'], {'id', 'factors', 'workload_kind', 'qualification_scope', 'quality_preference'})
    for key in ['id', 'qualification_scope']:
        text(route_task[key])
    classification = agent_routing.classify_task(route_task['factors'], contract_version=2,
        workload_kind=route_task['workload_kind'], quality_preference=route_task['quality_preference'])
    if record['runtime'] != 'cli' or type(record['model']) is not str or not MODEL.fullmatch(record['model']) or type(record['reasoning_effort']) is not str or record['reasoning_effort'] not in profiles.REASONING_EFFORTS:
        raise TargetError('invalid-target-runtime-or-model')
    text(record['model'])
    _provider(record['provider'])
    canonical_raw = _artifact(home, record['canonical_profile'])
    effective_raw = _artifact(home, record['effective_profile'])
    base = tomllib.loads(canonical_raw.decode()); effective = tomllib.loads(effective_raw.decode())
    registry = profiles.load_registry(profiles.DEFAULT_REGISTRY)
    entries = [e for e in registry['profiles'] if e.get('name') == task['role']]
    if len(entries) != 1 or entries[0]['profile_sha256'] != sha(canonical_raw) or base.get('name') != task['role']:
        raise TargetError('canonical-profile-drift')
    entry = entries[0]; required_tier = classification['capability_tier']; tier = entry['capability_tier']
    if entry['capability_class'] != classification['capability_class'] or profiles.TIER_RANK[tier] < profiles.TIER_RANK[required_tier] or (tier == 'exceptional' and required_tier != 'exceptional'):
        raise TargetError('target-role-classification-mismatch')
    if sandbox not in profiles.SAFE_SANDBOX_MODES or profiles.SANDBOX_RANK[sandbox] > profiles.SANDBOX_RANK[base['sandbox_mode']]:
        raise TargetError('target-sandbox-widening')
    if effective != {**base, 'model': record['model'], 'model_reasoning_effort': record['reasoning_effort']}:
        raise TargetError('effective-profile-drift')
    catalog_raw = _artifact(home, record['catalog']); catalog = decode(catalog_raw)
    if type(catalog) is not dict or set(catalog) != {'models'} or type(catalog['models']) is not list or not 1 <= len(catalog['models']) <= 256:
        raise TargetError('invalid-target-catalog')
    pending = [(catalog, 0)]; nodes = 0
    forbidden = {'api_key', 'apikey', 'access_token', 'refresh_token', 'authorization', 'password', 'credentials', 'secret'}
    while pending:
        value, depth = pending.pop(); nodes += 1
        if depth > 32 or nodes > 10000:
            raise TargetError('target-catalog-too-complex')
        if type(value) is dict:
            if any(key.lower() in forbidden for key in value):
                raise TargetError('target-catalog-contains-secret')
            pending.extend((item, depth+1) for item in value.values())
        elif type(value) is list:
            pending.extend((item, depth+1) for item in value)
        elif type(value) is str and SECRET_TEXT.search(value):
            raise TargetError('target-catalog-contains-secret')
    selected = [m for m in catalog['models'] if type(m) is dict and m.get('slug') == record['model']]
    if len(selected) != 1:
        raise TargetError('target-catalog-model-missing')
    summaries = obj(record['summaries'], {'qualification', 'context', 'capability', 'authorization', 'secret_check'})
    bound_identity = canonical_sha(identity(record)); bound_task = canonical_sha(task)
    extra = {'qualification': {'capability_class', 'capability_tier', 'scope', 'evidence_sha256'},
             'context': {'input_tokens', 'output_tokens', 'reasoning_tokens', 'margin_tokens', 'input_limit', 'output_limit', 'total_limit', 'client_limit', 'compact_limit'},
             'capability': {'executable_sha256', 'cli_version', 'public_config_keys', 'tool_calling', 'streaming'},
             'authorization': {'authority_ref', 'sandbox_ceiling'},
             'secret_check': {'evidence_sha256'}}
    accepted = {'qualification': 'qualified', 'context': 'qualified', 'capability': 'available',
                'authorization': 'granted', 'secret_check': 'excluded'}
    values = {}
    for name, file_ref in summaries.items():
        value = obj(decode(_artifact(home, file_ref, limit=trust.MAX_STORE_BYTES)), COMMON | extra[name])
        if type(value['schema_version']) is not int or value['schema_version'] != 1 or type(value['status']) is not str or value['status'] != accepted[name]:
            raise TargetError('target-'+name+'-unqualified')
        for key in ['identity_sha256', 'task_sha256']:
            digest(value[key])
        integer(value['observed_at']); integer(value['expires_at'])
        if value['identity_sha256'] != bound_identity or value['task_sha256'] != bound_task or not 0 <= now-value['observed_at'] <= TTL or value['expires_at'] <= now or value['expires_at'] > record['expires_at']:
            raise TargetError('target-summary-stale-or-drifted')
        values[name] = value
    q = values['qualification']
    if q['capability_class'] != entry['capability_class'] or q['capability_tier'] != tier or q['scope'] != route_task['qualification_scope']:
        raise TargetError('target-qualification-scope-mismatch')
    digest(q['evidence_sha256']); digest(values['secret_check']['evidence_sha256'])
    cap = values['capability']
    if cap['executable_sha256'] != executable_sha256 or cap['cli_version'] != cli_version or cap['tool_calling'] is not True or cap['streaming'] is not True or type(cap['public_config_keys']) is not list or set(cap['public_config_keys']) != PUBLIC_KEYS or len(cap['public_config_keys']) != len(PUBLIC_KEYS):
        raise TargetError('target-public-executor-unsupported')
    authority = values['authorization']; text(authority['authority_ref'])
    if authority['sandbox_ceiling'] not in profiles.SAFE_SANDBOX_MODES or profiles.SANDBOX_RANK[sandbox] > profiles.SANDBOX_RANK[authority['sandbox_ceiling']]:
        raise TargetError('target-authorization-sandbox-mismatch')
    ctx = values['context']
    for key in extra['context']:
        integer(ctx[key])
    output = ctx['output_tokens'] + ctx['reasoning_tokens']; total = ctx['input_tokens'] + output + ctx['margin_tokens']
    compact_bound = min(ctx['input_limit'], ctx['total_limit']-output-ctx['margin_tokens'], ctx['client_limit']-output-ctx['margin_tokens'])
    if min(ctx['output_tokens'], ctx['margin_tokens'], ctx['input_limit'], ctx['output_limit'], ctx['total_limit'], ctx['client_limit'], ctx['compact_limit']) <= 0 or ctx['input_tokens'] > ctx['input_limit'] or output > ctx['output_limit'] or total > min(ctx['total_limit'],ctx['client_limit']) or ctx['client_limit'] > ctx['total_limit'] or ctx['compact_limit'] >= compact_bound:
        raise TargetError('target-context-budget-unsafe')
    if type(selected[0].get('context_window')) is not int or selected[0]['context_window'] != ctx['client_limit']:
        raise TargetError('target-catalog-context-drift')
    cfg = {'model': record['model'], 'model_reasoning_effort': record['reasoning_effort'],
           'model_provider': record['provider']['id'], 'model_catalog_json': str(home/record['catalog']['path']),
           'model_context_window': ctx['client_limit'], 'model_auto_compact_token_limit': ctx['compact_limit'],
           'developer_instructions': base['developer_instructions']}
    provider = record['provider']
    if provider['billing'] == 'chatgpt-subscription':
        cfg['forced_login_method'] = 'chatgpt'
    else:
        cfg['model_providers'] = {provider['id']: {'name': provider['id'], 'base_url': provider['base_url'],
            'wire_api': provider['wire_api'], 'env_key': provider['env_key'], 'requires_openai_auth': False}}
    # Explicit excludes supplement core inheritance and default secret exclusions.
    cfg['shell_environment_policy.exclude'] = ['*KEY*', '*TOKEN*', '*SECRET*', '*PASSWORD*', '*CREDENTIAL*', '*COOKIE*', '*AUTH*']
    args = []
    for key, value in cfg.items():
        # JSON string/int/list syntax is also TOML; inline provider tables differ.
        if key == 'model_providers':
            spec = value[provider['id']]
            encoded = '{'+json.dumps(provider['id'])+'={'+', '.join(k+'='+('false' if v is False else json.dumps(v)) for k,v in spec.items())+'}}'
        else:
            encoded = json.dumps(value, ensure_ascii=False)
        args.extend(['-c', key+'='+encoded])
    planner_identity = {'provider_id': provider['id'], 'provider_config_sha256': canonical_sha(provider),
        'model': record['model'], 'runtime': 'cli', 'profile_sha256': record['effective_profile']['sha256'],
        'context_policy_sha256': record['summaries']['context']['sha256'],
        'model_catalog_sha256': record['catalog']['sha256'], 'billing': provider['billing']}
    # Artifact reads can outlive the first store read. Confirm the whole
    # protected snapshot still matches before returning an accepted binding.
    for file_ref in (record['canonical_profile'], record['effective_profile'], record['catalog']):
        _artifact(home, file_ref)
    for file_ref in summaries.values():
        _artifact(home, file_ref, limit=trust.MAX_STORE_BYTES)
    fd = trust._directory(home)
    try:
        if trust._read(fd, STORE, trust.MAX_STORE_BYTES) != raw:
            raise TargetError('target-store-drift')
    finally:
        os.close(fd)
    return Binding(record['id'], sha(raw), canonical_sha(record), bound_identity, bound_task,
        home, tuple(args), provider['env_key'], provider['billing']=='chatgpt-subscription', base['developer_instructions'],
        tuple(sorted(planner_identity.items())), catalog_raw, route_task['id'], route_task['qualification_scope'],
        task['acceptance_sha256'], task['role'], task['checkpoint_sha256'],
        max(value['observed_at'] for value in values.values()),
        min(record['expires_at'], *(min(value['expires_at'], value['observed_at'] + TTL + 1)
                                    for value in values.values())))


def target_identity(binding):
    """Planner identity. Provider digest hashes the complete allowlisted provider
    {id,billing,base_url,wire_api,env_key}, never a credential value. Profile,
    context policy, and catalog digests are protected artifact byte digests.
    """
    return dict(binding.planner_identity)


def config_argv(binding, *, catalog_path=None):
    args = list(binding.config)
    if catalog_path is not None:
        for index, value in enumerate(args):
            if value.startswith('model_catalog_json='):
                args[index] = 'model_catalog_json='+json.dumps(str(catalog_path))
    return args


def snapshot_catalog(binding, directory):
    """Materialize already validated bytes beside the private clone, outside Git."""
    path = directory/'typed-model-catalog.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(binding.catalog_bytes)
    except BaseException:
        # fdopen owns the descriptor once constructed; the surrounding private
        # executor temporary directory owns cleanup of any partial artifact.
        raise
    return path


def probe_environment(inherited):
    return {key: value for key, value in inherited.items()
            if (key in CORE_ENV or key.startswith('LC_')) and not SECRET_ENV.search(key)}


def child_environment(binding, inherited):
    """Credential values exist only in the inference process environment."""
    output = probe_environment(inherited)
    output['CODEX_HOME'] = str(binding.root)
    if binding.credential_env:
        value = inherited.get(binding.credential_env)
        if type(value) is not str or not value:
            raise TargetError('target-credential-unavailable')
        output[binding.credential_env] = value
    return output
