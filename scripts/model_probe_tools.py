"""Bounded parsing of structured model-visible declarations, never handlers."""
from __future__ import annotations

import hashlib
import json
import math
import re

MAX_REQUEST_BYTES = 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_JSON_NODES = 32768
MAX_TOOL_DEPTH = 4
MAX_TOOL_NODES = 256
NAME = re.compile(r'[A-Za-z0-9_-]{1,128}')


class ManifestError(ValueError):
    pass


def canonical(value):
    _validate_json(value)
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                         allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise ManifestError('invalid-canonical-json') from None
    if len(raw) > MAX_REQUEST_BYTES:
        raise ManifestError('canonical-json-too-large')
    return raw


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ManifestError('duplicate-json-key')
        result[key] = value
    return result


def decode(raw):
    if type(raw) is not bytes or len(raw) > MAX_REQUEST_BYTES:
        raise ManifestError('request-bytes-required-or-too-large')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(ManifestError('nonfinite-json')))
    except (ValueError, UnicodeError, RecursionError):
        raise ManifestError('invalid-json') from None
    _validate_json(value)
    return value


def _validate_json(value):
    """Reject nonfinite numbers and invalid Unicode anywhere, including keys."""
    pending = [(value, 0)]; count = 0
    while pending:
        item, depth = pending.pop(); count += 1
        if depth > MAX_JSON_DEPTH or count > MAX_JSON_NODES:
            raise ManifestError('json-structure-too-large')
        if type(item) is dict:
            if len(item) > MAX_JSON_NODES or any(type(key) is not str for key in item):
                raise ManifestError('invalid-json-object')
            pending.extend((child, depth + 1) for pair in item.items() for child in pair)
        elif type(item) is list:
            if len(item) > MAX_JSON_NODES:
                raise ManifestError('json-structure-too-large')
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            try:
                size = len(item.encode('utf-8'))
            except UnicodeError:
                raise ManifestError('invalid-unicode') from None
            if size > MAX_REQUEST_BYTES:
                raise ManifestError('json-string-too-large')
        elif type(item) is float:
            if not math.isfinite(item):
                raise ManifestError('nonfinite-json')
        elif item is not None and type(item) not in {int, bool}:
            raise ManifestError('unsupported-json-value')


def advertised_tools(raw):
    """Read only request.tools and structured input additional_tools declarations.

    Arbitrary prompt text, descriptions, TypeScript declarations, and schemas
    nested in descriptions are opaque. The result cannot establish registration,
    execution, permissions, or a complete effective runtime tool inventory.
    """
    request = decode(raw)
    if type(request) is not dict:
        raise ManifestError('request-object-required')
    sources = []
    if 'tools' in request:
        sources.append(('request.tools', request['tools']))
    inputs = request.get('input', [])
    if type(inputs) is list:
        if len(inputs) > 1024:
            raise ManifestError('too-many-input-items')
        for index, item in enumerate(inputs):
            if type(item) is not dict:
                raise ManifestError('input-item-object-required')
            if item.get('type') == 'additional_tools':
                if (set(item) - {'type', 'role', 'id', 'tools'}
                        or item.get('role') != 'developer' or 'tools' not in item
                        or 'id' in item and (type(item['id']) is not str or len(item['id']) > 256)):
                    raise ManifestError('invalid-additional-tools')
                sources.append((f'input[{index}].tools', item['tools']))
    elif type(inputs) is not str:
        raise ManifestError('invalid-input')
    result = []; seen = set(); nodes = 0

    def visit(entries, prefix, source, depth):
        nonlocal nodes
        if type(entries) is not list or len(entries) > MAX_TOOL_NODES or depth > MAX_TOOL_DEPTH:
            raise ManifestError('invalid-or-too-deep-tool-list')
        for index, entry in enumerate(entries):
            nodes += 1
            if nodes > MAX_TOOL_NODES or type(entry) is not dict:
                raise ManifestError('too-many-or-invalid-tools')
            kind, name = entry.get('type'), entry.get('name')
            if type(name) is not str or not NAME.fullmatch(name):
                raise ManifestError('invalid-tool-name')
            identity = (*prefix, name)
            if identity in seen:
                raise ManifestError('duplicate-or-conflicting-tool')
            seen.add(identity)
            location = f'{source}[{index}]'
            if 'description' in entry and (type(entry['description']) is not str
                    or len(entry['description'].encode()) > 128 * 1024):
                raise ManifestError('invalid-tool-description')
            if kind == 'namespace':
                if set(entry) - {'type', 'name', 'description', 'tools'} or 'tools' not in entry:
                    raise ManifestError('invalid-tool-namespace')
                visit(entry['tools'], identity, location + '.tools', depth + 1)
                continue
            if kind == 'function':
                if (set(entry) - {'type', 'name', 'description', 'parameters', 'strict'}
                        or type(entry.get('parameters')) is not dict
                        or 'strict' in entry and entry['strict'] is not None and type(entry['strict']) is not bool):
                    raise ManifestError('invalid-function-declaration')
                schema = entry['parameters']
            elif kind == 'custom':
                if set(entry) - {'type', 'name', 'description', 'format'} or type(entry.get('format')) is not dict:
                    raise ManifestError('invalid-custom-declaration')
                schema = entry['format']
                if schema.get('type') == 'text':
                    valid = set(schema) == {'type'}
                elif schema.get('type') == 'grammar':
                    valid = (set(schema) == {'type', 'syntax', 'definition'}
                        and type(schema.get('syntax')) is str
                        and schema['syntax'] in {'lark', 'regex'} and type(schema.get('definition')) is str)
                else:
                    valid = False
                if not valid:
                    raise ManifestError('invalid-custom-format')
            else:
                raise ManifestError('unsupported-declaration-type')
            result.append({'name': name, 'namespace': '.'.join(prefix) if prefix else None,
                'type': kind, 'source': location, 'schema_sha256': sha(schema),
                'declaration_sha256': sha(entry)})

    for source, entries in sources:
        visit(entries, (), source, 0)
    return {'schema_version': 1, 'scope': 'structured-advertised-tools-only',
        'handler_inventory_complete': False, 'request_sha256': hashlib.sha256(raw).hexdigest(),
        'sources': [source for source, _ in sources], 'advertised_tools': result}
