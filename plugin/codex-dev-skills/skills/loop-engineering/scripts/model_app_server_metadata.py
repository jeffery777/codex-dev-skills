"""Anonymous, bounded observations from an already-authorized host Session.

The trusted caller owns session startup, authority and OS controls. This helper
never starts a process, refreshes credentials, directly manages MCP connections
or loads repository-only probe code. The caller also owns the native status
method's discovery behavior; a preceding empty config is not an atomic fence.
The public CLI 0.159.3 response shapes are observed
only for the fields below; this is neither a full handler inventory nor proof of
startup isolation, credentials, a thread snapshot or production qualification.
Raw config, requirements, layer identities and unknown feature names are never
included in the returned receipt or diagnostics. Transport byte/time limits are
still the caller's responsibility. Missing selected flags remain unobserved.
"""
import os


LAYER_TYPES = (
    'packagedDefaults', 'mdm', 'system', 'enterpriseManaged', 'user', 'project',
    'sessionFlags', 'legacyManagedConfigTomlFromFile',
    'legacyManagedConfigTomlFromMdm',
)
# Public observation keys, kept independent of repository-only probe scripts.
SELECTED_FEATURES = (
    'shell_tool', 'unified_exec', 'view_image', 'apps', 'hooks', 'plugins',
    'remote_plugin', 'multi_agent', 'multi_agent_v2', 'goals', 'memories',
    'code_mode', 'code_mode_host', 'code_mode_only', 'code_mode_prewarm',
    'enable_request_compression', 'browser_use', 'computer_use',
    'image_generation', 'skill_search', 'skill_mcp_dependency_install',
    'tool_suggest', 'daemon_auto_start',
)
MAX_LAYERS = 32
PAGE_SIZE = 256
MAX_FEATURE_PAGES = 8
MAX_FEATURE_ITEMS = 2048
MAX_NAME_LENGTH = 256
MAX_CURSOR_LENGTH = 256


class MetadataError(RuntimeError):
    """Fixed diagnostic code only; never includes a response or peer exception."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _request(session, method, params):
    # Raise outside the except block so even __context__ cannot retain a peer
    # exception containing sensitive text. There is no retry or alternate call.
    failed = False
    try:
        result = session.request(method, params)
    except Exception:
        failed = True
    if failed:
        raise MetadataError('metadata_request_failed')
    if type(result) is not dict:
        raise MetadataError('invalid_metadata_response')
    return result


def _config_observation(result):
    config, layers = result.get('config'), result.get('layers')
    if type(config) is not dict:
        raise MetadataError('invalid_config')
    if type(layers) is not list or len(layers) > MAX_LAYERS:
        raise MetadataError('invalid_layers')
    counts = dict.fromkeys(LAYER_TYPES, 0)
    for layer in layers:
        if type(layer) is not dict or type(layer.get('name')) is not dict:
            raise MetadataError('invalid_layer')
        kind = layer['name'].get('type')
        if type(kind) is not str or kind not in counts:
            raise MetadataError('unknown_layer_type')
        counts[kind] += 1
    if 'mcp_servers' not in config:
        raise MetadataError('unknown_mcp_config')
    servers = config['mcp_servers']
    if servers is not None and type(servers) is not dict:
        raise MetadataError('invalid_mcp_config')
    if servers:
        # Even disabled entries stop observation before any status/discovery.
        # An empty session overlay does not clear lower merged MCP entries.
        raise MetadataError('mcp_config_present')
    notify = config.get('notify')
    if notify is not None and (type(notify) is not list or
            len(notify) > PAGE_SIZE or any(type(x) is not str for x in notify)):
        raise MetadataError('invalid_notify')
    return counts, notify is None or len(notify) == 0


def _feature_observation(session, thread_id):
    cursor = None
    cursors, names = set(), set()
    selected = {}
    total = 0
    for pages in range(1, MAX_FEATURE_PAGES + 1):
        result = _request(session, 'experimentalFeature/list', {
            'threadId': thread_id, 'limit': PAGE_SIZE, 'cursor': cursor})
        rows = result.get('data')
        if type(rows) is not list or len(rows) > PAGE_SIZE:
            raise MetadataError('invalid_feature_data')
        total += len(rows)
        if total > MAX_FEATURE_ITEMS:
            raise MetadataError('feature_item_limit')
        for row in rows:
            if type(row) is not dict:
                raise MetadataError('invalid_feature_row')
            name, enabled = row.get('name'), row.get('enabled')
            if (type(name) is not str or not name.strip() or
                    len(name) > MAX_NAME_LENGTH or type(enabled) is not bool):
                raise MetadataError('invalid_feature_row')
            if name in names:
                raise MetadataError('duplicate_feature_name')
            names.add(name)
            if name in SELECTED_FEATURES:
                selected[name] = enabled
        if 'nextCursor' not in result:
            raise MetadataError('missing_feature_cursor')
        cursor = result['nextCursor']
        if cursor is None:
            return selected, pages
        if (type(cursor) is not str or not cursor.strip() or
                len(cursor) > MAX_CURSOR_LENGTH):
            raise MetadataError('invalid_feature_cursor')
        if cursor in cursors:
            raise MetadataError('duplicate_feature_cursor')
        cursors.add(cursor)
    raise MetadataError('feature_page_limit')


def collect(session, *, cwd, thread_id):
    """Return a sanitized observation; failure never yields a partial receipt.

    config/read is for cwd and features/status are for the supplied loaded
    thread. Their refreshed views are not an atomic or verified thread snapshot.
    Empty MCP configuration permits exactly one status query. Any nonempty or
    incomplete status response stops; it never initiates another discovery page.
    Nonempty notify and managed requirements are observations, not permission.
    """
    if (type(cwd) is not str or not os.path.isabs(cwd) or '\0' in cwd or
            type(thread_id) is not str or not thread_id.strip() or
            len(thread_id) > MAX_NAME_LENGTH or '\0' in thread_id):
        raise MetadataError('invalid_metadata_inputs')
    layers, notify_empty = _config_observation(_request(session, 'config/read', {
        'cwd': cwd, 'includeLayers': True}))
    requirements = _request(session, 'configRequirements/read', {})
    if ('requirements' not in requirements or
            (requirements['requirements'] is not None and
             type(requirements['requirements']) is not dict)):
        raise MetadataError('invalid_requirements')
    managed_present = requirements['requirements'] is not None
    del requirements
    selected, feature_pages = _feature_observation(session, thread_id)
    status = _request(session, 'mcpServerStatus/list', {
        'threadId': thread_id, 'detail': 'full', 'limit': PAGE_SIZE,
        'cursor': None})
    if (type(status.get('data')) is not list or status['data'] or
            'nextCursor' not in status or status['nextCursor'] is not None):
        raise MetadataError('unknown_mcp_status')
    return {
        'layer_type_counts': layers,
        'mcp_entry_count': 0,
        'mcp_status_count': 0,
        'notify_empty': notify_empty,
        'managed_requirements_present': managed_present,
        'selected_features': selected,
        'feature_pages': feature_pages,
        'feature_inventory_complete': True,
        'startup_isolation_qualified': False,
        'thread_snapshot_verified': False,
    }
