#!/usr/bin/env python3
"""Run native Hermes discovery/load checks without explicit model or authentication requests."""
from __future__ import annotations
import argparse
import json
import os
import pathlib
import subprocess
import sys

PROBE = r'''
import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
import hermes_bootstrap
from tools.skills_tool import skills_list, skill_view
expected = {'hermes-project-delivery', 'hermes-review-gate', 'hermes-task-continuation'}
listed = json.loads(skills_list())
names = [item['name'] for item in listed.get('skills', [])]
if not listed.get('success') or any(names.count(name) != 1 for name in expected):
    raise SystemExit('native discovery missing or ambiguous')
results = []
for name in sorted(expected):
    value = json.loads(skill_view(name, preprocess=False))
    missing = any(value.get(key) for key in ('missing_required_commands',
        'missing_required_environment_variables', 'missing_credential_files'))
    if not value.get('success') or not value.get('content') or missing or value.get('setup_needed'):
        raise SystemExit('native skill not ready: ' + name)
    results.append({'name': name, 'loaded': True, 'setup_needed': False})
print(json.dumps({'native_loader': 'passed', 'skills': results,
                  'model_request': False, 'runtime_qualified': False}))
'''

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-python', required=True, type=pathlib.Path,
                        help='trusted Hermes interpreter from its public launcher')
    parser.add_argument('--runtime-source', required=True, type=pathlib.Path,
                        help='trusted installed Hermes source root')
    parser.add_argument('--hermes-home', required=True, type=pathlib.Path,
                        help='explicit isolated profile with only this package installed')
    args = parser.parse_args()
    for value in (args.runtime_python, args.runtime_source, args.hermes_home):
        if not value.is_absolute() or not value.exists():
            parser.error('all inputs must be existing absolute trusted paths')
    env = {key: value for key, value in os.environ.items()
           if key in {'HOME', 'PATH', 'LANG', 'TERM', 'TMPDIR'}}
    env.update(HERMES_HOME=str(args.hermes_home), PYTHONDONTWRITEBYTECODE='1',
               HERMES_DISABLE_LAZY_INSTALLS='1')
    try:
        result = subprocess.run([str(args.runtime_python), '-I', '-c', PROBE,
                                 str(args.runtime_source)], cwd=args.hermes_home,
                                env=env, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        print('Native loader unavailable or timed out; no qualification granted.', file=sys.stderr)
        return 1
    if result.returncode:
        print('Native loader failed; inspect the isolated runtime locally.', file=sys.stderr)
        return 1
    try:
        value = json.loads(result.stdout)
    except ValueError:
        print('Native loader returned an unexpected output shape.', file=sys.stderr)
        return 1
    print(json.dumps(value))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
