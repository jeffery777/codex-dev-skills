"""Manual, private-evidence-only reproduction for Issue #292; never relaxes sandbox."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import time
import uuid


DIAGNOSTICS = ('warn,codex_core::tools=trace,codex_core::unified_exec=trace,'
               'codex_sandboxing=debug,codex_otel.log_only=info,codex_otel.trace_safe=info')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--cli-sha256', required=True)
    parser.add_argument('--version', default='codex-cli 0.156.0')
    parser.add_argument('--root', type=Path, required=True, help='Private, owned, outside-repository evidence root')
    parser.add_argument('--mode', choices=['baseline', 'disable-unified-exec', 'temp-free'], default='baseline')
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--effort', default='low')
    args = parser.parse_args()
    cli = args.cli.resolve(strict=True)
    if sha(cli) != args.cli_sha256:
        parser.error('CLI digest mismatch; inspect the selected version before running')
    version = subprocess.run([str(cli), '--version'], capture_output=True, text=True, check=True).stdout.strip()
    if version != args.version:
        parser.error('CLI version mismatch')
    os.umask(0o077)
    root = args.root.resolve()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    work = root / 'workspace'
    work.mkdir(mode=0o700, exist_ok=True)
    run = root / ('run-' + uuid.uuid4().hex)
    run.mkdir(mode=0o700)
    marker = 'R292_' + uuid.uuid4().hex
    command = "cat <<'EOF'\n" + marker + '_HEREDOC\nEOF'
    if args.mode == 'temp-free':
        command = "printf '%s\\n' '" + marker + "_HEREDOC'"
    after = "printf '%s\\n' '" + marker + "_AFTER'"
    prompt = ('只執行本次受控診斷，不讀檔、不查網路、不派代理、不提權、不改寫命令。'
              '以 shell 工具使用 /bin/zsh、login=true、cwd=' + str(work) +
              '，先完整執行以下命令，保留換行，不改成 -c：\n' + command +
              '\n然後另外呼叫 shell 工具：\n' + after +
              '\n最終逐項列 requested command、是否呼叫、實際工具回應原文、exit code。'
              '未呼叫就明示未呼叫；只報告觀察，不猜測。')
    for name, content in [('command.txt', command), ('after.txt', after), ('prompt.txt', prompt)]:
        (run / name).write_text(content)

    def capture(name: str, argv: list[str], stdin: bytes | None = None, env: dict | None = None) -> dict:
        started = time.monotonic()
        timed_out = False
        with (run / (name + '.stdout')).open('wb') as out, (run / (name + '.stderr')).open('wb') as err:
            proc = subprocess.Popen(argv, cwd=work, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                    env=env, start_new_session=True)
            try:
                proc.communicate(stdin, timeout=180)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.communicate(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.communicate()
        result = {'argv': argv, 'exit_code': proc.returncode, 'timeout': timed_out,
                  'seconds': round(time.monotonic() - started, 3),
                  'stdout_sha256': sha(run / (name + '.stdout')),
                  'stderr_sha256': sha(run / (name + '.stderr'))}
        (run / (name + '.json')).write_text(json.dumps(result, indent=2) + '\n')
        return result

    metadata = {'marker': marker, 'mode': args.mode, 'cli_version': version, 'cli_sha256': sha(cli),
                'shell': '/bin/zsh', 'shell_sha256': sha(Path('/bin/zsh')), 'cwd': str(work),
                'requested_model': args.model, 'requested_effort': args.effort,
                'sandbox': 'read-only', 'diagnostics': DIAGNOSTICS,
                'platform': {'system': platform.system(), 'release': platform.release(),
                             'machine': platform.machine(), 'macos': platform.mac_ver()[0]},
                'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}
    metadata['shell_version'] = capture('shell-version', ['/bin/zsh', '--version'])
    metadata['direct'] = capture('direct', [str(cli), 'sandbox', '-P', ':read-only', '-C', str(work),
                                            '/bin/zsh', '-lc', command])
    metadata['direct_after'] = capture('direct-after', [str(cli), 'sandbox', '-P', ':read-only', '-C', str(work),
                                                        '/bin/zsh', '-lc', after])
    argv = [str(cli), 'exec', '--ignore-user-config', '--ephemeral', '--json', '--color', 'never',
            '--sandbox', 'read-only', '--model', args.model, '-c', 'model_reasoning_effort=' + json.dumps(args.effort),
            '--skip-git-repo-check', '-C', str(work), '-o', str(run / 'final.txt'), '-']
    if args.mode == 'disable-unified-exec':
        argv[1:1] = ['--disable', 'unified_exec']
    metadata['model'] = capture('model', argv, prompt.encode(), {**os.environ, 'RUST_LOG': DIAGNOSTICS})
    metadata['cli_sha256_after'] = sha(cli)
    metadata['shell_sha256_after'] = sha(Path('/bin/zsh'))
    (run / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'private_run': str(run), 'cli_exit_code': metadata['model']['exit_code'],
                      'mode': args.mode, 'tool_coverage': 'requires_separate_analysis'}))
    if metadata['model']['exit_code'] or metadata['model']['timeout']:
        raise SystemExit(1)
    if metadata['cli_sha256_after'] != metadata['cli_sha256'] or metadata['shell_sha256_after'] != metadata['shell_sha256']:
        raise SystemExit('Executable changed during the run; evidence is not a fixed-version comparison')


if __name__ == '__main__':
    main()
