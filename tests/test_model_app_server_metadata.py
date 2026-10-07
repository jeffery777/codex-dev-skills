"""Anonymous in-memory Session fixtures: no native subprocess, login or network."""
import copy
import json
import pathlib
import sys
import traceback
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] /
                       'skills/loop-engineering/scripts'))
import model_app_server_metadata as metadata


SECRET = 'anonymous-credential-secret-do-not-retain'
CWD = '/anonymous/workspace'
THREAD = 'anonymous-thread'


def layer(kind='user', **config):
    return {'name': {'type': kind, 'file': '/' + SECRET, 'domain': SECRET,
                     'id': SECRET}, 'version': SECRET, 'config': config}


def feature(name='shell_tool', enabled=False):
    return {'name': name, 'enabled': enabled, 'defaultEnabled': True,
            'stage': 'underDevelopment', 'description': SECRET}


class MockSession:
    """Only request exists: no process/connection/notification lifecycle API."""

    def __init__(self, *, config=None, requirements=None, pages=None, status=None):
        self.calls = []
        self.responses = {
            'config/read': [copy.deepcopy(config if config is not None else {
                'config': {'mcp_servers': {}, 'notify': None, 'token': SECRET},
                'layers': [layer()], 'origins': {SECRET: SECRET}})],
            'configRequirements/read': [copy.deepcopy(requirements if requirements
                is not None else {'requirements': None})],
            'experimentalFeature/list': copy.deepcopy(pages if pages is not None
                else [{'data': [feature()], 'nextCursor': None}]),
            'mcpServerStatus/list': [copy.deepcopy(status if status is not None
                else {'data': [], 'nextCursor': None})],
        }

    def request(self, method, params):
        self.calls.append((method, dict(params)))
        if method not in self.responses or not self.responses[method]:
            raise AssertionError('unexpected request')
        response = self.responses[method].pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class MetadataTests(unittest.TestCase):
    def collect(self, session, **inputs):
        return metadata.collect(session, **dict({'cwd': CWD, 'thread_id': THREAD},
                                               **inputs))

    def fails(self, session, code, **inputs):
        with self.assertRaises(metadata.MetadataError) as raised:
            self.collect(session, **inputs)
        error = raised.exception
        self.assertEqual(error.code, code)
        self.assertEqual(str(error), code)
        self.assertNotIn(SECRET, repr(error))
        self.assertIsNone(error.__context__)
        return error

    def test_fixed_receipt_and_exact_public_requests(self):
        session = MockSession()
        receipt = self.collect(session)
        self.assertEqual(set(receipt), {
            'layer_type_counts', 'mcp_entry_count', 'mcp_status_count',
            'notify_empty', 'managed_requirements_present', 'selected_features',
            'feature_pages', 'feature_inventory_complete',
            'startup_isolation_qualified', 'thread_snapshot_verified'})
        self.assertEqual(receipt['layer_type_counts']['user'], 1)
        self.assertEqual(receipt['selected_features'], {'shell_tool': False})
        self.assertEqual(receipt['feature_pages'], 1)
        self.assertTrue(receipt['feature_inventory_complete'])
        self.assertFalse(receipt['startup_isolation_qualified'])
        self.assertFalse(receipt['thread_snapshot_verified'])
        self.assertNotIn(SECRET, json.dumps(receipt))
        self.assertEqual(session.calls, [
            ('config/read', {'cwd': CWD, 'includeLayers': True}),
            ('configRequirements/read', {}),
            ('experimentalFeature/list', {'threadId': THREAD, 'limit': 256,
                                          'cursor': None}),
            ('mcpServerStatus/list', {'threadId': THREAD, 'detail': 'full',
                                     'limit': 256, 'cursor': None}),
        ])
        # Exact method inventory excludes init, startup, refresh, login,
        # notifications, connection, tools/list, write and thread/turn methods.
        self.assertNotIn('apps', receipt['selected_features'])

    def test_layer_types_counts_and_maximum_without_identities(self):
        layers = [layer(kind) for kind in metadata.LAYER_TYPES]
        layers.extend(layer('sessionFlags') for _ in range(32 - len(layers)))
        receipt = self.collect(MockSession(config={
            'config': {'mcp_servers': None}, 'layers': layers}))
        self.assertEqual(sum(receipt['layer_type_counts'].values()), 32)
        self.assertEqual(receipt['layer_type_counts']['enterpriseManaged'], 1)
        self.assertNotIn(SECRET, json.dumps(receipt))

    def test_unknown_source_and_malformed_layers_stop_before_other_reads(self):
        values = [None, {}, [layer()] * 33, [None], [{'type': 'user'}],
                  [{'name': None}], [{'name': {'type': SECRET}}],
                  [{'name': {'type': True}}], [{'name': {}}]]
        codes = ['invalid_layers'] * 3 + ['invalid_layer'] * 3 + \
                ['unknown_layer_type'] * 3
        for value, code in zip(values, codes):
            with self.subTest(value=type(value).__name__):
                session = MockSession(config={'config': {'mcp_servers': {}},
                                             'layers': value})
                self.fails(session, code)
                self.assertEqual([m for m, _ in session.calls], ['config/read'])

    def test_missing_config_and_exact_container_types_are_required(self):
        class FakeDict(dict):
            pass
        class FakeList(list):
            pass
        for config in ({}, {'config': []}, {'config': FakeDict(mcp_servers={})},
                       {'config': None}):
            self.fails(MockSession(config=dict(config, layers=[])), 'invalid_config')
        self.fails(MockSession(config={'config': {'mcp_servers': {}},
                   'layers': FakeList()}), 'invalid_layers')
        self.fails(MockSession(config={'config': {'mcp_servers': {}},
                   'layers': [FakeDict(name={'type': 'user'})]}), 'invalid_layer')

    def test_mcp_unknown_schema_rejects_and_empty_dict_or_null_is_observed(self):
        for values, code in [({}, 'unknown_mcp_config'),
                ({'mcp_servers': []}, 'invalid_mcp_config'),
                ({'mcp_servers': False}, 'invalid_mcp_config'),
                ({'mcp_servers': SECRET}, 'invalid_mcp_config')]:
            session = MockSession(config={'config': values, 'layers': []})
            self.fails(session, code)
            self.assertEqual(len(session.calls), 1)
        for value in ({}, None):
            receipt = self.collect(MockSession(config={
                'config': {'mcp_servers': value}, 'layers': []}))
            self.assertEqual(receipt['mcp_entry_count'], 0)
            self.assertEqual(receipt['mcp_status_count'], 0)

    def test_nonempty_disabled_lower_mcp_is_never_cleared_by_empty_overlay(self):
        for enabled in (False, True):
            session = MockSession(config={
                'config': {'mcp_servers': {SECRET: {'enabled': enabled,
                                                   'bearer_token': SECRET}}},
                'layers': [layer('user', mcp_servers={SECRET: {'enabled': enabled}}),
                           layer('sessionFlags', mcp_servers={})]})
            self.fails(session, 'mcp_config_present')
            self.assertEqual(session.calls, [
                ('config/read', {'cwd': CWD, 'includeLayers': True})])

    def test_notify_empty_missing_null_and_nonempty_are_observations(self):
        for value, empty in [(None, True), ([], True), ([SECRET], False)]:
            receipt = self.collect(MockSession(config={
                'config': {'mcp_servers': {}, 'notify': value}, 'layers': []}))
            self.assertIs(receipt['notify_empty'], empty)
            self.assertFalse(receipt['startup_isolation_qualified'])
            self.assertNotIn(SECRET, json.dumps(receipt))
        self.assertTrue(self.collect(MockSession(config={
            'config': {'mcp_servers': {}}, 'layers': []}))['notify_empty'])
        for value in (False, SECRET, {}, [1], [SECRET] * 257):
            self.fails(MockSession(config={
                'config': {'mcp_servers': {}, 'notify': value}, 'layers': []}),
                'invalid_notify')

    def test_requirements_presence_does_not_qualify_or_retain_secrets(self):
        for value, present in [(None, False), ({}, True),
                               ({SECRET: {'network': [SECRET]}}, True)]:
            receipt = self.collect(MockSession(requirements={'requirements': value}))
            self.assertIs(receipt['managed_requirements_present'], present)
            self.assertFalse(receipt['startup_isolation_qualified'])
            self.assertFalse(receipt['thread_snapshot_verified'])
            self.assertNotIn(SECRET, json.dumps(receipt))
        for value in ({}, {'requirements': False}, {'requirements': []},
                       {'requirements': SECRET}):
            session = MockSession(requirements=value)
            self.fails(session, 'invalid_requirements')
            self.assertEqual(len(session.calls), 2)

    def test_paginated_features_select_only_public_keys_and_omit_unknown_names(self):
        pages = [{'data': [feature('apps', True), feature(SECRET)],
                  'nextCursor': SECRET},
                 {'data': [feature('code_mode_host'), feature('memories', True)],
                  'nextCursor': None}]
        session = MockSession(pages=pages)
        receipt = self.collect(session)
        self.assertEqual(receipt['selected_features'], {
            'apps': True, 'code_mode_host': False, 'memories': True})
        self.assertEqual(receipt['feature_pages'], 2)
        self.assertNotIn(SECRET, json.dumps(receipt))
        self.assertEqual(session.calls[3], ('experimentalFeature/list',
            {'threadId': THREAD, 'limit': 256, 'cursor': SECRET}))
        self.assertFalse(receipt['thread_snapshot_verified'])

    def test_feature_data_and_rows_are_bounded_and_enabled_cannot_spoof_bool(self):
        for data in (None, {}, False, [feature()] * 257):
            self.fails(MockSession(pages=[{'data': data, 'nextCursor': None}]),
                       'invalid_feature_data')
        for row in (None, [], {}, {'name': 'apps'}, feature('', False),
                    feature('   ', False), feature('x' * 257, False),
                    feature(True, False), feature('apps', 0),
                    feature('apps', 1), feature('apps', 'false'),
                    feature('apps', None)):
            session = MockSession(pages=[{'data': [row], 'nextCursor': None}])
            self.fails(session, 'invalid_feature_row')
            self.assertNotIn('mcpServerStatus/list', [m for m, _ in session.calls])
        receipt = self.collect(MockSession(pages=[{
            'data': [feature('x' * 256)], 'nextCursor': None}]))
        self.assertEqual(receipt['selected_features'], {})

    def test_duplicate_known_and_unknown_feature_names_across_pages_reject(self):
        for name in ('apps', SECRET):
            for pages in ([{'data': [feature(name)] * 2, 'nextCursor': None}],
                    [{'data': [feature(name)], 'nextCursor': 'next'},
                     {'data': [feature(name, True)], 'nextCursor': None}]):
                session = MockSession(pages=pages)
                self.fails(session, 'duplicate_feature_name')
                self.assertNotIn('mcpServerStatus/list', [m for m, _ in session.calls])

    def test_missing_blank_oversize_and_duplicate_cursors_stop_pagination(self):
        self.fails(MockSession(pages=[{'data': []}]), 'missing_feature_cursor')
        for value in ('', '   ', 'x' * 257, False, 1, [], {}):
            self.fails(MockSession(pages=[{'data': [], 'nextCursor': value}]),
                       'invalid_feature_cursor')
        session = MockSession(pages=[{'data': [], 'nextCursor': 'repeat'}] * 2)
        self.fails(session, 'duplicate_feature_cursor')
        self.assertEqual(len(session.calls), 4)

    def test_maximum_pages_items_and_empty_inventory_can_complete(self):
        pages = [{'data': [feature(f'unknown-{p}-{n}') for n in range(256)],
                  'nextCursor': f'page-{p}' if p < 7 else None}
                 for p in range(8)]
        receipt = self.collect(MockSession(pages=pages))
        self.assertEqual(receipt['feature_pages'], 8)
        self.assertEqual(receipt['selected_features'], {})
        self.assertTrue(receipt['feature_inventory_complete'])
        self.assertEqual(self.collect(MockSession(pages=[{
            'data': [], 'nextCursor': None}]))['selected_features'], {})
        pages[-1]['nextCursor'] = 'ninth-page'
        session = MockSession(pages=pages)
        self.fails(session, 'feature_page_limit')
        self.assertEqual(len(session.calls), 10)
        self.assertNotIn('mcpServerStatus/list', [m for m, _ in session.calls])

    def test_nonempty_or_unknown_mcp_status_never_follows_another_cursor(self):
        for status in ({}, {'data': []}, {'data': None, 'nextCursor': None},
                {'data': {}, 'nextCursor': None},
                {'data': [{'name': SECRET, 'tools': {SECRET: SECRET}}],
                 'nextCursor': None}, {'data': [], 'nextCursor': SECRET},
                {'data': [], 'nextCursor': False}):
            session = MockSession(status=status)
            self.fails(session, 'unknown_mcp_status')
            self.assertEqual([m for m, _ in session.calls].count('mcpServerStatus/list'), 1)

    def test_session_response_and_exception_never_echo_sensitive_payloads(self):
        for method in ('config/read', 'configRequirements/read',
                       'experimentalFeature/list', 'mcpServerStatus/list'):
            for response, code in [(RuntimeError(SECRET), 'metadata_request_failed'),
                                   ([SECRET], 'invalid_metadata_response')]:
                session = MockSession()
                session.responses[method] = [response]
                error = self.fails(session, code)
                self.assertNotIn(SECRET, ''.join(traceback.format_exception(error)))
                self.assertEqual(session.calls[-1][0], method)
                self.assertEqual(len(session.calls), (
                    'config/read', 'configRequirements/read',
                    'experimentalFeature/list', 'mcpServerStatus/list').index(method) + 1)

    def test_invalid_host_inputs_fail_before_any_request(self):
        for inputs in ({'cwd': 'relative'}, {'cwd': False}, {'cwd': '/x\0y'},
                {'thread_id': None}, {'thread_id': ''}, {'thread_id': '  '},
                {'thread_id': True}, {'thread_id': 'x' * 257},
                {'thread_id': 'x\0y'}):
            session = MockSession()
            self.fails(session, 'invalid_metadata_inputs', **inputs)
            self.assertEqual(session.calls, [])


if __name__ == '__main__':
    unittest.main()
