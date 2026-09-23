"""Analyze owned synthetic CLI evidence; never infer non-execution from missing events."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from event_evidence import inspect


def tool_results(stderr: str) -> list[dict]:
    """Pinned 0.156.0 diagnostic format, not a stable public structured API.

    Extract only nested exec_command arguments and its result. Never export the
    surrounding account metadata or any other tool's output. Caller keeps the
    full original stderr private. Unrecognized/truncated evidence stays unknown.
    """
    results = []
    for block in re.split(r'(?=^20\d\d-\d\d-\d\dT)', stderr, flags=re.M):
        first = block.splitlines()[0] if block else ''
        if not all(x in first for x in ['codex_otel.log_only', 'codex.tool_result', 'tool_name="exec_command"']):
            continue
        arguments, separator, output = block.partition(' arguments=')[2].partition(' output=')
        output, boundary, _ = output.partition('\n mcp_server=')
        ids = re.findall(r'call_id="([^"]+)"', first)
        if not separator or not boundary or not ids or 'output_truncated=false' not in first:
            results.append({'status': 'unknown', 'reason': 'unrecognized_or_truncated_diagnostic'})
            continue
        try:
            arguments = json.loads(arguments)
        except (ValueError, TypeError):
            results.append({'status': 'unknown', 'reason': 'unrecognized_arguments'})
            continue
        if not isinstance(arguments, dict):
            results.append({'status': 'unknown', 'reason': 'non_object_arguments'})
            continue
        code = re.search(r'^Process exited with code (-?\d+)$', output, flags=re.M)
        results.append({'status': 'observed' if code else 'unknown', 'call_id': ids[-1],
                        'arguments': arguments, 'exit_code': int(code[1]) if code else None,
                        'output': output.partition('\nOutput:\n')[2].rstrip('\n'),
                        'output_truncated': False})
    return results


def analyze(run: Path) -> dict:
    metadata = json.loads((run / 'metadata.json').read_text())
    raw = (run / 'model.stdout').read_bytes()
    final = (run / 'final.txt').read_bytes() if (run / 'final.txt').is_file() else None
    stream = inspect(raw, final)
    logs = tool_results((run / 'model.stderr').read_text())
    commands = []
    if stream['stream_integrity'] == 'valid':
        commands = [x['item'] for x in map(json.loads, raw.splitlines())
                    if x.get('type') == 'item.completed' and x.get('item', {}).get('type') == 'command_execution']
    checks = []
    for filename, capture_name in [('command.txt', 'direct'), ('after.txt', 'direct-after')]:
        expected = (run / filename).read_text()
        marker = re.search(r'R292_[0-9a-f]+_(?:HEREDOC|AFTER)', expected)
        matching = [x for x in logs if x.get('arguments', {}).get('cmd') == expected]
        observed = [x for x in commands if marker and marker[0] in x.get('command', '')]
        direct = json.loads((run / (capture_name + '.json')).read_text())
        tool = matching[0] if len(matching) == 1 else None
        raw_direct_output = (run / (capture_name + '.stdout')).read_text() + (run / (capture_name + '.stderr')).read_text()
        request_matches = bool(tool and tool['arguments'].get('shell') == '/bin/zsh'
                               and tool['arguments'].get('login') is True
                               and tool['arguments'].get('workdir') == metadata['cwd'])
        equivalent = bool(request_matches and tool['status'] == 'observed' and tool['exit_code'] == direct['exit_code']
                          and tool['output'].rstrip('\n') == raw_direct_output.rstrip('\n'))
        checks.append({'command_file': filename, 'direct_exit_code': direct['exit_code'],
                       'exact_tool_request_count': len(matching), 'public_command_event_count': len(observed) if stream['stream_integrity'] == 'valid' else None,
                       'tool_exit_code': tool['exit_code'] if tool else None,
                       'shell_login_cwd_match': request_matches,
                       'tool_output_matches_direct': equivalent,
                       'call_id': tool['call_id'] if tool else None,
                       'tool_output_truncated': tool['output_truncated'] if tool else None,
                       'status': 'unknown' if stream['stream_integrity'] != 'valid' else
                                 'confirmed_event_gap' if equivalent and not observed else
                                 'consistent' if equivalent and len(observed) == 1 and observed[0].get('exit_code') == tool['exit_code']
                                     and observed[0].get('aggregated_output', '').rstrip('\n') == tool['output'].rstrip('\n')
                                 else 'unknown'})
    result = {'stream': stream, 'checks': checks,
              'diagnostic_parse_unknown_count': sum(x['status'] == 'unknown' for x in logs),
              'diagnostic_raw_sha256': hashlib.sha256((run / 'model.stderr').read_bytes()).hexdigest(),
              'scope': 'Two exact synthetic commands only; not an attestation of all runtime calls or model identity.'}
    (run / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.run), indent=2))
