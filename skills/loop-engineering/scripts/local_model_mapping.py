"""Protected opt-in local role mappings; never connect to or choose a provider."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import sys
import tomllib

import agent_qualification as trust
import profile_preflight as profiles

STORE = 'agent-model-mapping.json'
RECORD_KEYS = {'role', 'runtime', 'provider_id', 'provider_config_sha256', 'model', 'reasoning_effort',
               'base_profile_sha256', 'profile', 'profile_sha256', 'capability_class', 'capability_tier',
               'task_scopes', 'quality_evidence', 'quality_evidence_sha256', 'context_policy', 'context_policy_sha256', 'expires_on', 'enabled'}
BINDING_KEYS = {'role', 'runtime', 'provider_id', 'provider_config_sha256', 'model', 'reasoning_effort',
                'base_profile_sha256', 'profile_sha256', 'store_sha256', 'quality_evidence_sha256', 'context_policy_sha256', 'model_catalog_sha256', 'scope'}


class MappingError(ValueError):
    pass


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def root():
    return pathlib.Path(os.environ.get('CODEX_HOME', str(pathlib.Path.home() / '.codex')))


def _load():
    fd = None
    try:
        try:
            (root() / STORE).lstat()
        except FileNotFoundError:
            return None, None, None
        fd = trust._directory(root())
        try:
            raw = trust._read(fd, STORE, trust.MAX_STORE_BYTES)
        except FileNotFoundError:
            return fd, None, None
        data = json.loads(raw, object_pairs_hook=trust._pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(MappingError('nonfinite-json')))
        if not isinstance(data, dict) or set(data) != {'schema_version', 'enabled', 'mappings'} or type(data['schema_version']) is not int or data['schema_version'] != 1 or type(data['enabled']) is not bool or not isinstance(data['mappings'], list):
            raise MappingError('invalid-mapping-schema')
        seen = set()
        for r in data['mappings']:
            if not isinstance(r, dict) or set(r) != RECORD_KEYS:
                raise MappingError('invalid-mapping-record')
            if any(not isinstance(r[k], str) or not r[k].strip() for k in RECORD_KEYS - {'enabled', 'expires_on', 'task_scopes'}):
                raise MappingError('invalid-mapping-record')
            if type(r['enabled']) is not bool or not trust._strings(r['task_scopes']) or r['runtime'] not in {'cli', 'desktop'} or r['role'] not in profiles.ROLE_CONTRACTS or r['role'] in profiles.CANDIDATE_ROLES:
                raise MappingError('invalid-mapping-record')
            if any(not trust.SHA.fullmatch(r[k]) for k in ['provider_config_sha256', 'base_profile_sha256', 'profile_sha256', 'quality_evidence_sha256', 'context_policy_sha256']) or r['reasoning_effort'] not in profiles.REASONING_EFFORTS:
                raise MappingError('invalid-mapping-record')
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', r['provider_id']) or not re.fullmatch(r'[A-Za-z0-9_./:-]+', r['model']):
                raise MappingError('invalid-model-identity')
            if r['expires_on'] is not None:
                if not isinstance(r['expires_on'], str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', r['expires_on']):
                    raise MappingError('invalid-expiry')
                dt.date.fromisoformat(r['expires_on'])
            identity = (r['role'], r['runtime'])
            if identity in seen:
                raise MappingError('duplicate-mapping-role-runtime')
            seen.add(identity)
        return fd, data, digest(raw)
    except FileNotFoundError:
        if fd is not None:
            os.close(fd)
        return None, None, None
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        if fd is not None:
            os.close(fd)
        raise MappingError(str(exc) if isinstance(exc, (MappingError, trust.Untrusted)) else 'invalid-or-untrusted-mapping') from None


def resolve(*, role, entries, facts, scope, destination, profile_dir, today=None):
    """Return None only for absent/explicitly disabled store. Enabled failures stop."""
    fd, data, store_digest = _load()
    try:
        if data is None or data['enabled'] is False:
            return None
        surface = facts.get('local_model_surface')
        if not isinstance(surface, dict) or set(surface) != {'runtime', 'provider_id', 'provider_config_sha256', 'supported_roles', 'context_metadata'}:
            raise MappingError('current-local-model-surface-missing')
        if not isinstance(surface['runtime'], str) or surface['runtime'] not in {'cli', 'desktop'} or not isinstance(surface['supported_roles'], list) or role not in surface['supported_roles'] or (facts.get('model_surface') or {}).get('runtime') != surface['runtime']:
            raise MappingError('current-runtime-or-role-unsupported')
        if (not isinstance(surface['provider_id'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]+', surface['provider_id'])
            or not isinstance(surface['provider_config_sha256'], str) or not trust.SHA.fullmatch(surface['provider_config_sha256'])
            or any(not isinstance(r, str) for r in surface['supported_roles'])
            or not isinstance(surface['context_metadata'], dict)):
            raise MappingError('invalid-current-local-model-surface')
        records = [r for r in data['mappings'] if r['role'] == role and r['runtime'] == surface['runtime']]
        if len(records) != 1 or records[0]['enabled'] is not True:
            raise MappingError('mapping-missing-or-revoked')
        r = records[0]
        e = entries[role]
        for key in ['provider_id', 'provider_config_sha256']:
            if surface[key] != r[key]:
                raise MappingError('provider-identity-drift')
        if any(r[k] != e[k] for k in ['capability_class', 'capability_tier']) or r['base_profile_sha256'] != e['_profile_digest']:
            raise MappingError('base-profile-drift')
        if not isinstance(scope, str) or scope not in r['task_scopes']:
            raise MappingError('mapping-scope-mismatch')
        if r['expires_on'] is not None and dt.date.fromisoformat(r['expires_on']) < (today or dt.date.today()):
            raise MappingError('mapping-expired')
        evidence = trust._read(fd, r['quality_evidence'], trust.MAX_EVIDENCE_BYTES)
        if digest(evidence) != r['quality_evidence_sha256']:
            raise MappingError('quality-evidence-drift')
        raw_profile = trust._read(fd, r['profile'], trust.MAX_STORE_BYTES)
        if digest(raw_profile) != r['profile_sha256']:
            raise MappingError('effective-profile-drift')
        canonical = profiles.load_profile(profile_dir / e['file'])
        effective = tomllib.loads(raw_profile.decode('utf-8'))
        expected = {**canonical, 'model': r['model'], 'model_reasoning_effort': r['reasoning_effort']}
        if effective != expected:
            raise MappingError('effective-profile-contract-modified')
        target = root() / r['profile']
        if destination.is_symlink() or target != destination / e['file']:
            raise MappingError('mapping-destination-mismatch')
        context = context_policy(fd, r, surface)
        binding = {k:r[k] for k in BINDING_KEYS - {'store_sha256', 'scope', 'model_catalog_sha256'}}
        binding['model_catalog_sha256'] = context['model_catalog_sha256']
        binding.update(store_sha256=store_digest, scope=scope)
        mapped = {**e, '_profile_digest':r['profile_sha256'], 'runtime_mapping':{**e['runtime_mapping'], 'model':r['model'], 'reasoning_effort':r['reasoning_effort']}}
        return mapped, binding, target
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        raise MappingError(str(exc) if isinstance(exc, MappingError) else 'invalid-or-untrusted-mapping-evidence') from None
    finally:
        if fd is not None:
            os.close(fd)


CONTEXT_NUMBERS = {'backend_context_window', 'backend_max_input_tokens', 'backend_max_output_tokens',
                   'reserved_output_tokens', 'reserved_reasoning_tokens', 'safety_margin_tokens',
                   'model_context_window', 'model_auto_compact_token_limit'}
CONTEXT_KEYS = CONTEXT_NUMBERS | {'schema_version', 'model', 'runtime', 'provider_config_sha256',
                                'model_catalog_sha256', 'capacity_evidence', 'capacity_evidence_sha256'}


def context_policy(fd, record, surface):
    raw = trust._read(fd, record['context_policy'], trust.MAX_STORE_BYTES)
    if digest(raw) != record['context_policy_sha256']:
        raise MappingError('context-policy-drift')
    data = json.loads(raw, object_pairs_hook=trust._pairs)
    if not isinstance(data, dict) or set(data) != CONTEXT_KEYS or type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise MappingError('invalid-context-policy')
    for k in CONTEXT_NUMBERS:
        minimum = 0 if k == 'reserved_reasoning_tokens' else 1
        if type(data[k]) is not int or data[k] < minimum:
            raise MappingError('context-capacity-unknown-or-invalid')
    for k in ['model', 'runtime', 'provider_config_sha256']:
        if data[k] != record[k]:
            raise MappingError('context-model-provider-mismatch')
    if any(not isinstance(data[k], str) or not trust.SHA.fullmatch(data[k]) for k in ['model_catalog_sha256', 'capacity_evidence_sha256']):
        raise MappingError('invalid-context-evidence')
    evidence = trust._read(fd, data['capacity_evidence'], trust.MAX_EVIDENCE_BYTES)
    if digest(evidence) != data['capacity_evidence_sha256']:
        raise MappingError('capacity-evidence-drift')
    reserve = data['reserved_output_tokens'] + data['reserved_reasoning_tokens'] + data['safety_margin_tokens']
    budget = min(data['backend_max_input_tokens'], data['backend_context_window'] - reserve)
    if (data['reserved_output_tokens'] + data['reserved_reasoning_tokens'] > data['backend_max_output_tokens']
        or data['model_context_window'] > data['backend_context_window']
        or not 0 < data['model_auto_compact_token_limit'] < min(budget, data['model_context_window'] - reserve)):
        raise MappingError('context-budget-unsafe')
    metadata = surface.get('context_metadata')
    if not isinstance(metadata, dict):
        raise MappingError('current-context-metadata-missing-or-drifted')
    current = metadata.get(record['model'])
    expected = {k:data[k] for k in ['model_context_window', 'model_auto_compact_token_limit', 'model_catalog_sha256']}
    if (not isinstance(current, dict) or set(current) != set(expected)
        or type(current.get('model_context_window')) is not int
        or type(current.get('model_auto_compact_token_limit')) is not int
        or current != expected):
        raise MappingError('current-context-metadata-missing-or-drifted')
    return data


def accepted_profiles(*, entries, facts, destination, profile_dir):
    """Validate other mapped profiles independently before allowing their collisions."""
    fd, data, _ = _load()
    if fd is not None:
        os.close(fd)
    accepted = set()
    if not data or not data['enabled']:
        return accepted
    for r in data['mappings']:
        if not r['enabled'] or r['runtime'] != (facts.get('local_model_surface') or {}).get('runtime'):
            continue
        try:
            value = resolve(role=r['role'], entries=entries, facts=facts, scope=r['task_scopes'][0],
                            destination=destination, profile_dir=profile_dir)
            if value:
                accepted.add((r['role'], str(value[2])))
        except MappingError:
            pass  # Invalid unrelated bytes remain a collision; never a fallback.
    return accepted


def validate_binding(binding):
    if not isinstance(binding, dict) or set(binding) != BINDING_KEYS:
        return False
    if any(not isinstance(v, str) or not v.strip() for v in binding.values()):
        return False
    return (binding['runtime'] in {'cli', 'desktop'} and binding['role'] in profiles.ROLE_CONTRACTS
            and binding['role'] not in profiles.CANDIDATE_ROLES
            and binding['reasoning_effort'] in profiles.REASONING_EFFORTS
            and all(trust.SHA.fullmatch(binding[k]) for k in BINDING_KEYS if k.endswith('_sha256')))


def installer_check(destination):
    """Refuse writes to roots reserved by an enabled mapping, including --force."""
    fd, data, _ = _load()
    try:
        if data and data['enabled']:
            for r in data['mappings']:
                # Validate relative containment even for revoked records.
                parts = r['profile'].split('/')
                if any(p in {'', '.', '..'} for p in parts) or '\\' in r['profile']:
                    raise MappingError('unsafe-profile-path')
                if (root() / r['profile']).parent.resolve() == destination.resolve():
                    raise MappingError('mapping-owned-destination-preserved')
    finally:
        if fd is not None:
            os.close(fd)


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3 or sys.argv[1] != 'installer-check':
            raise MappingError('expected-installer-check-destination')
        installer_check(pathlib.Path(sys.argv[2]))
    except MappingError as exc:
        print('local model mapping: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
