#!/usr/bin/env python3
"""Opt-in, credential-free native sandbox background probe; no model calls.

Run using project-python on macOS. Evidence and bounded background processes
are retained; this does not qualify Codex exec, builtin tools or an adapter.
"""
import argparse
import hashlib
import json
import pathlib
import shutil
import shlex
import subprocess
import sys
import tempfile
import time


def reader_guard(reader='/bin/cat'):
    """Positive control in the same shell/sandbox as the forbidden read."""
    return ('test "$(' + shlex.quote(reader) + ' reader-sentinel)" = reader-ok || exit 12; '
            'echo verified > reader-verified; ')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=pathlib.Path, required=True)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('this qualification probe is macOS-only')
    base = args.evidence_root.resolve(strict=True)
    if not base.is_dir() or any((p / '.git').exists() for p in [base, *base.parents]):
        parser.error('existing evidence directory outside Git required')
    executable = shutil.which('codex')
    if executable is None:
        parser.error('installed Codex CLI required')
    executable = str(pathlib.Path(executable).resolve(strict=True))
    root = pathlib.Path(tempfile.mkdtemp(prefix='model-permissions-', dir=base))
    a, b, home, control = [root / name for name in ['a', 'b', 'codex', 'control']]
    for directory in [a, b, home, control]:
        directory.mkdir()
    (control / 'sentinel').write_text('synthetic-only')
    (a / 'reader-sentinel').write_text('reader-ok')
    # Never inherit host credentials, proxy/auth variables or user configuration.
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'CODEX_HOME': str(home)}
    receipt = {'schema_version': 1, 'scope': 'synthetic-native-background-only',
        'fixture': str(root), 'production_qualified': False,
        'executable_sha256': hashlib.sha256(pathlib.Path(executable).read_bytes()).hexdigest()}
    start = time.monotonic()

    def invoke(workspace, other, script):
        permissions = {':root': 'deny', ':minimal': 'read', ':tmpdir': 'deny',
            ':slash_tmp': 'deny', str(workspace): 'write', str(other): 'deny',
            str(home): 'deny', str(control): 'deny'}
        # Only quoted string keys/values from this private fixture; not user TOML.
        config = 'permissions.probe.filesystem={' + ','.join(
            json.dumps(key) + '=' + json.dumps(value) for key, value in permissions.items()) + '}'
        return subprocess.run([executable, 'sandbox', '-P', 'probe', '-C', str(workspace),
            '-c', config, '-c', 'permissions.probe.network.enabled=false', '--', '/bin/sh',
            '-c', script], env=env, capture_output=True, text=True, timeout=15)

    try:
        # Root exits promptly; a reparented descendant retains its sandbox.
        child = (reader_guard() + 'echo ready > ready; i=0; while test ! -f release; do '
            'i=$((i+1)); test "$i" -lt 100 || exit 10; sleep 0.2; done; '
            'echo old > result; if echo stale > ' + shlex.quote(str(b / 'result')) +
            '; then echo write-violation > violation; fi; if /bin/cat ' + shlex.quote(str(control / 'sentinel')) +
            ' >/dev/null; then echo read-violation > violation; fi; echo done > done')
        old = invoke(a, b, '(' + child + ') >/dev/null 2>&1 &')
        deadline = time.monotonic() + 5
        while not (a / 'ready').exists():
            if time.monotonic() >= deadline:
                raise OSError('background writer ready deadline exceeded')
            time.sleep(0.05)
        pending = not (a / 'result').exists()
        new = invoke(b, a, 'echo successor > result')
        (a / 'release').touch(exist_ok=False)
        deadline = time.monotonic() + 5
        while not (a / 'done').exists():
            if time.monotonic() >= deadline:
                raise OSError('background writer completion deadline exceeded')
            time.sleep(0.05)
        receipt['checks'] = {'old_root_exited': old.returncode == 0,
            'old_root_exited_before_child_write': pending,
            'reader_positive_control': (a / 'reader-verified').exists(),
            'successor_completed': new.returncode == 0,
            'old_child_later_wrote': (a / 'result').read_text().strip() == 'old',
            'successor_preserved': (b / 'result').read_text().strip() == 'successor',
            'forbidden_access_rejected': not (a / 'violation').exists()}
        return 0 if all(receipt['checks'].values()) else 1
    except (OSError, subprocess.SubprocessError) as error:
        receipt['error'] = str(error)
        return 1
    finally:
        receipt['elapsed_seconds'] = round(time.monotonic() - start, 2)
        output = root / 'permissions-evidence.json'
        output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'evidence': str(output), **receipt}, indent=2))


if __name__ == '__main__':
    raise SystemExit(main())
