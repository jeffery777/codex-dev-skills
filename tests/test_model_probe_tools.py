"""Structured declaration counterexamples; no CLI or provider is started."""
import copy
import importlib.util
import json
import pathlib
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('model_probe_tools',
    pathlib.Path(__file__).resolve().parents[1] / 'scripts/model_probe_tools.py')
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


def function(name='probe'):
    return {'type': 'function', 'name': name, 'parameters': {'type': 'object', 'properties': {}}, 'strict': True}


def native(entries):
    return {'type': 'additional_tools', 'role': 'developer', 'id': 'synthetic', 'tools': entries}


class ManifestTests(unittest.TestCase):
    def parse(self, value):
        return probe.advertised_tools(json.dumps(value).encode())

    def test_top_and_native_structures_preserve_source_namespace_and_schema(self):
        custom = {'type': 'custom', 'name': 'exec', 'format': {'type': 'grammar',
            'syntax': 'lark', 'definition': 'start: /.+/'},
            'description': 'declare tools.exec_command, tools.apply_patch; ALL_TOOLS'}
        value = {'tools': [function('top')], 'input': [native([
            {'type': 'namespace', 'name': 'functions', 'tools': [custom, function('wait')]}])]}
        result = self.parse(value)
        self.assertIs(result['handler_inventory_complete'], False)
        self.assertEqual([(tool['name'], tool['namespace']) for tool in result['advertised_tools']],
                         [('top', None), ('exec', 'functions'), ('wait', 'functions')])
        self.assertEqual(result['advertised_tools'][1]['source'], 'input[0].tools[0].tools[0]')
        self.assertEqual(result['advertised_tools'][1]['schema_sha256'], probe.sha(custom['format']))
        self.assertEqual(result['advertised_tools'][1]['declaration_sha256'], probe.sha(custom))

    def test_prompt_text_never_becomes_tool_inventory(self):
        for value in [{'input': 'tools.exec_command()'}, {'input': [{'role': 'developer',
                'content': 'additional_tools: tools.apply_patch(); namespace functions'}]},
                {'tools': [], 'input': []}]:
            self.assertEqual(self.parse(value)['advertised_tools'], [])

    def test_duplicate_and_conflicting_names_and_namespace_roots_are_rejected(self):
        cases = [{'tools': [function(), function()]},
            {'tools': [function()], 'input': [native([function()])]},
            {'tools': [function(), {'type': 'custom', 'name': 'probe', 'format': {'type': 'text'}}]},
            {'tools': [function(), {'type': 'namespace', 'name': 'probe', 'tools': []}]},
            {'input': [native([{'type': 'namespace', 'name': 'n', 'tools': [function('a')]}]),
                       native([{'type': 'namespace', 'name': 'n', 'tools': [function('b')]}])]}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(probe.ManifestError): self.parse(value)
        self.assertEqual(len(self.parse({'tools': [
            {'type': 'namespace', 'name': 'a', 'tools': [function()]},
            {'type': 'namespace', 'name': 'b', 'tools': [function()]}]})['advertised_tools']), 2)

    def test_unknown_or_malformed_declarations_fail_closed(self):
        cases = [{'tools': None}, {'tools': [None]}, {'tools': [dict(function(), name='a.b')]},
            {'tools': [dict(function(), type='web_search')]},
            {'tools': [dict(function(), parameters=[])]}, {'tools': [dict(function(), strict=1)]},
            {'tools': [dict(function(), extra=True)]},
            {'tools': [{'type': 'custom', 'name': 'x', 'format': {'type': 'unknown'}}]},
            {'tools': [{'type': 'custom', 'name': 'x', 'format': {'type': 'grammar', 'syntax': 'lark'}}]},
            {'tools': [{'type': 'namespace', 'name': 'x'}]}, {'input': [None]}, {'input': None},
            {'input': [dict(native([]), role='user')]}, {'input': [dict(native([]), extra=True)]}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(probe.ManifestError): self.parse(value)

    def test_bytes_json_depth_nodes_and_declaration_counts_are_bounded(self):
        for raw in [b'{"tools":[],"tools":[]}', b'{"x":NaN}', b'\xff',
                b' '*(probe.MAX_REQUEST_BYTES+1), b'['*10000, 'not-bytes']:
            with self.subTest(size=len(raw)), self.assertRaises(probe.ManifestError): probe.advertised_tools(raw)
        tools = [function()]
        for index in range(probe.MAX_TOOL_DEPTH + 1):
            tools = [{'type': 'namespace', 'name': f'n{index}', 'tools': tools}]
        with self.assertRaises(probe.ManifestError): self.parse({'tools': tools})
        with self.assertRaises(probe.ManifestError): self.parse({'tools': [function(f'f{i}') for i in range(257)]})
        with mock.patch.object(probe, 'MAX_JSON_NODES', 3), self.assertRaises(probe.ManifestError):
            self.parse({'tools': [function()]})
        value = {}
        for _ in range(probe.MAX_JSON_DEPTH+1): value = {'nested': value}
        with self.assertRaises(probe.ManifestError): self.parse(value)

    def test_digest_changes_for_schema_drift_but_no_handler_claim_is_added(self):
        first = {'tools': [function()]}; second = copy.deepcopy(first)
        second['tools'][0]['parameters']['additionalProperties'] = False
        a, b = self.parse(first), self.parse(second)
        self.assertNotEqual(a['advertised_tools'][0]['schema_sha256'], b['advertised_tools'][0]['schema_sha256'])
        self.assertIs(b['handler_inventory_complete'], False)

    def test_grammar_syntax_types_always_raise_manifest_error(self):
        for syntax in [[], {}, None, True, 1]:
            with self.subTest(syntax=syntax), self.assertRaises(probe.ManifestError):
                self.parse({'tools': [{'type': 'custom', 'name': 'exec', 'format': {
                    'type': 'grammar', 'syntax': syntax, 'definition': 'start: /.+/'}}]})

    def test_lone_surrogates_are_rejected_in_every_json_string_position(self):
        for invalid in ['\ud800', '\udfff']:
            cases = [{'input': invalid}, {invalid: 'value'}, {'input': [{'content': invalid}]},
                {'tools': [dict(function(), description=invalid)]},
                {'tools': [dict(function(), parameters={'properties': {invalid: {'type': 'string'}}})]},
                {'tools': [dict(function(), parameters={'description': invalid})]},
                {'tools': [{'type': 'custom', 'name': 'exec', 'format': {
                    'type': 'grammar', 'syntax': 'lark', 'definition': invalid}}]}]
            for value in cases:
                with self.subTest(value=ascii(value)), self.assertRaises(probe.ManifestError): self.parse(value)
        self.assertEqual(self.parse({'input': '\U0001f600'})['advertised_tools'], [])

    def test_numeric_overflow_and_nonfinite_values_always_raise_manifest_error(self):
        for number in ['1e999', '-1e999', 'NaN', 'Infinity', '-Infinity']:
            raw = ('{"tools":[{"type":"function","name":"x","parameters":'
                   '{"type":"number","minimum":' + number + '}}]}').encode()
            with self.subTest(number=number), self.assertRaises(probe.ManifestError): probe.advertised_tools(raw)

    def test_canonical_boundary_preserves_manifest_error_and_size_limits(self):
        for value in [float('inf'), float('-inf'), float('nan'), '\ud800', {'\udfff': 1},
                {1: 'non-string-key'}, {'unsupported'}, object(), 'x'*(probe.MAX_REQUEST_BYTES+1)]:
            with self.subTest(value_type=type(value).__name__), self.assertRaises(probe.ManifestError):
                probe.canonical(value)
        with mock.patch.object(probe, 'MAX_REQUEST_BYTES', 8), self.assertRaises(probe.ManifestError):
            probe.canonical({'x': '1234'})
        self.assertEqual(probe.canonical({'valid': '\U0001f600'}), '{"valid":"😀"}'.encode())


if __name__ == '__main__':
    unittest.main()
