from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('heredoc_rca', ROOT / 'docs/loops/issue-292/heredoc-rca/analyze.py')
assert SPEC and SPEC.loader
rca = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rca)


def diagnostic(command, cwd, truncated=False):
    arguments = json.dumps({'cmd': command, 'shell': '/bin/zsh', 'login': True, 'workdir': cwd})
    return ('2026-09-23T00:00:00Z INFO codex_otel.log_only: event.name="codex.tool_result" '
            'tool_name="exec_command" call_id="synthetic-call" success=true '
            f'output_truncated={str(truncated).lower()} arguments={arguments} output=Chunk ID: synthetic\n'
            'Process exited with code 1\nOutput:\nsynthetic denial\n'
            ' mcp_server= user.email="synthetic-private@example.invalid"\n')


class HeredocRcaTests(unittest.TestCase):
    def test_tool_result_success_flag_does_not_override_nonzero_exit_or_export_identity(self):
        parsed = rca.tool_results(diagnostic('cat', '/synthetic'))
        self.assertEqual(1, parsed[0]['exit_code'])
        self.assertEqual('synthetic denial', parsed[0]['output'])
        self.assertNotIn('synthetic-private', json.dumps(parsed))

    def test_truncated_or_unrecognized_metadata_boundary_is_unknown(self):
        for text in (diagnostic('cat', '/synthetic', True), diagnostic('cat', '/synthetic').replace('\n mcp_server=', '\n changed_metadata=')):
            self.assertEqual([{'status': 'unknown', 'reason': 'unrecognized_or_truncated_diagnostic'}], rca.tool_results(text))

    def test_valid_jsonl_does_not_hide_confirmed_tool_failure_event_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            command = "cat <<'EOF'\nR292_abc_HEREDOC\nEOF"
            after = "printf R292_abc_AFTER"
            (run / 'metadata.json').write_text(json.dumps({'cwd': directory}))
            (run / 'command.txt').write_text(command)
            (run / 'after.txt').write_text(after)
            (run / 'model.stderr').write_text(diagnostic(command, directory))
            (run / 'model.stdout').write_text(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'failure reported'}}) + '\n' + json.dumps({'type':'turn.completed'}) + '\n')
            (run / 'final.txt').write_text('failure reported\n')
            for name in ('direct', 'direct-after'):
                (run / (name + '.json')).write_text(json.dumps({'exit_code': 1}))
                (run / (name + '.stdout')).write_text('')
                (run / (name + '.stderr')).write_text('synthetic denial\n')
            result = rca.analyze(run)
            self.assertEqual('valid', result['stream']['stream_integrity'])
            self.assertEqual('confirmed_event_gap', result['checks'][0]['status'])
            self.assertEqual('unknown', result['checks'][1]['status'])
            self.assertEqual(0, result['checks'][0]['public_command_event_count'])

            visible = {'type': 'item.completed', 'item': {'type': 'command_execution',
                       'command': command, 'exit_code': 1, 'aggregated_output': 'synthetic denial\n'}}
            stream = (run / 'model.stdout').read_text()
            (run / 'model.stdout').write_text(json.dumps(visible) + '\n' + stream)
            self.assertEqual('consistent', rca.analyze(run)['checks'][0]['status'])
            with (run / 'model.stdout').open('a') as out:
                out.write('{\n')
            invalid = rca.analyze(run)
            self.assertEqual('invalid', invalid['stream']['stream_integrity'])
            self.assertEqual('unknown', invalid['checks'][0]['status'])
            self.assertIsNone(invalid['checks'][0]['public_command_event_count'])


if __name__ == '__main__':
    unittest.main()
