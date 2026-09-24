#!/usr/bin/env python3
"""Bounded, synthetic killpg investigation; never launches the real Codex CLI.

Run through scripts/project-python. JSONL goes to stdout; retain raw runs outside
the repository. No environment dump, process-list scan, or permission changes.
The environment label is operator supplied, not an attestation of sandbox state.
"""
from __future__ import annotations

import argparse
import collections
import errno
import hashlib
import importlib
import json
import os
import pathlib
import platform
import signal
import subprocess
import sys
import time
import traceback
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
FAST_CHILD = 'import sys; sys.stdout.write("x" * 8192); sys.stdout.flush()\n'


def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)


def exception_record(exc):
    # Preserve every frame and chained exception; redact only local path prefixes.
    trace = ''.join(traceback.format_exception(exc))
    for source, label in [(str(ROOT), '<repo>'), (str(pathlib.Path.home()), '<home>')]:
        trace = trace.replace(source, label)
    return {'type': type(exc).__name__, 'errno': getattr(exc, 'errno', None),
            'repr': repr(exc), 'traceback': trace}


def identity(pid):
    record = {'pid': pid}
    for name, operation in [('pgid', os.getpgid), ('sid', os.getsid)]:
        try:
            record[name] = operation(pid)
        except OSError as exc:
            record[name] = {'type': type(exc).__name__, 'errno': exc.errno}
    return record


def child_code(metadata=False, held=False):
    code = FAST_CHILD
    if metadata:
        code = (
            'import json, os, time, sys\n'
            'sys.stderr.write(json.dumps(dict(pid=os.getpid(), ppid=os.getppid(), '
            'pgid=os.getpgrp(), sid=os.getsid(0), uid=os.getuid(), euid=os.geteuid(), '
            'before_output_ns=time.monotonic_ns())) + "\\n"); sys.stderr.flush()\n'
        ) + code
    if held:
        # Finite control condition; the original fast-exit child has no sleep.
        code += 'import time; time.sleep(0.5)\n'
    return code


def signal_call(pid, sig, events, origin_ns, operation, defer_details=False):
    event = {'event': 'killpg', 'target_pgid': pid, 'signal': int(sig),
             'signal_name': signal.Signals(sig).name if sig else '0',
             'before_ns': time.monotonic_ns() - origin_ns}
    try:
        operation(pid, sig)
    except OSError as exc:
        event['after_ns'] = time.monotonic_ns() - origin_ns
        if defer_details:
            # Do not format traces or run identity syscalls between the adapter's
            # failed signal and its second poll: that could hide the exit race.
            event['_exception'] = exc
            events.append(event)
            raise
        event['exception'] = exception_record(exc)
        event['target_after_error'] = identity(pid)
        # Signal 0 observes only this owned, not-yet-reaped child's PID.
        try:
            os.kill(pid, 0)
            event['kill_pid_0_after_error'] = 'success'
        except OSError as check:
            event['kill_pid_0_after_error'] = exception_record(check)
        events.append(event)
        raise
    else:
        event['after_ns'] = time.monotonic_ns() - origin_ns
        event['result'] = 'sent' if sig else 'permitted'
        events.append(event)


def minimal_trial(args):
    events = []
    start = time.monotonic_ns()
    code = child_code(args.child_metadata, args.case == 'live')
    process = subprocess.Popen([sys.executable, '-c', code],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    record = {'layer': 'minimal', 'child_pid': process.pid, 'events': events,
              'spawn_return_ns': time.monotonic_ns() - start}
    try:
        # No poll()/wait() before signaling: preserve the unreaped-child state.
        data = process.stdout.read(4096 if args.case in ('partial', 'live') else -1)
        record['read_complete_ns'] = time.monotonic_ns() - start
        record['read_bytes'] = len(data)
        record['read_to_eof'] = args.case == 'eof'
        if args.delay:
            time.sleep(args.delay)
        try:
            signal_call(process.pid, 0 if args.signal == 'zero' else signal.SIGTERM,
                        events, start, os.killpg)
        except OSError:
            # Diagnostic collection only. This is not an adapter success receipt.
            record['outcome'] = 'signal-error'
        else:
            record['outcome'] = 'signal-returned'
        _, stderr = process.communicate(timeout=3)
        record['wait_return_ns'] = time.monotonic_ns() - start
        record['returncode'] = process.returncode
        record['child_metadata'] = json.loads(stderr) if stderr else None
        record['receipt'] = None  # No adapter exists in this layer.
        return record
    finally:
        # Both fixed child programs terminate naturally within 0.5 s. Do not
        # introduce a second signaling path that could conceal a denied killpg.
        process.wait(timeout=3)
        process.stdout.close()
        process.stderr.close()


def adapter_trial(args, fixture, case):
    # Reuse only the repository's synthetic fixture and production entrypoints.
    # Do not import a real CLI client or start a model session.
    handoff = fixture.handoff
    events, processes = [], []
    start = time.monotonic_ns()
    real_popen, real_killpg = subprocess.Popen, os.killpg
    record = {'layer': args.layer, 'events': events}

    def launch(*positional, **kwargs):
        process = real_popen(*positional, **kwargs)
        # Only instrument our fake executable, not fixture git subprocesses.
        if positional and pathlib.Path(positional[0][0]).resolve() == case.executable.resolve():
            processes.append(process)
            events.append({'event': 'spawn', 'pid': process.pid,
                           'start_new_session': kwargs.get('start_new_session'),
                           'at_ns': time.monotonic_ns() - start})
            real_poll = process.poll

            def observe_poll(*poll_args, **poll_kwargs):
                caller = sys._getframe(1)
                before = time.monotonic_ns() - start
                result = real_poll(*poll_args, **poll_kwargs)
                events.append({'event': 'poll', 'pid': process.pid,
                               'caller': caller.f_code.co_name, 'line': caller.f_lineno,
                               'before_ns': before, 'after_ns': time.monotonic_ns() - start,
                               'result': result})
                return result

            process.poll = observe_poll
        return process

    def observe_signal(pid, sig):
        if not any(p.pid == pid and p.returncode is None for p in processes):
            raise RuntimeError('diagnostic refused a signal outside its unreaped fake child')
        return signal_call(pid, sig, events, start, real_killpg, defer_details=True)

    try:
        # Reuse one executable across trials, as in the original investigation.
        # A new shebang path per trial can spend the deadline in cold startup.
        with mock.patch.dict(os.environ, {'FAKE_CODEX_VERSION_MODE': 'stdout-overflow-quick'}), \
             mock.patch.object(handoff, 'VERSION_TIMEOUT_SECONDS', 0.1), \
             mock.patch.object(handoff.subprocess, 'Popen', side_effect=launch), \
             mock.patch.object(handoff.os, 'killpg', side_effect=observe_signal):
            if args.layer == 'adapter':
                record['receipt'] = case.execute()
            else:
                record['receipt'] = None
                try:
                    handoff._probe_version(case.executable)
                except handoff.HandoffValidationError as exc:
                    record['probe_exception'] = exception_record(exc)
                    record['probe_failure_class'] = exc.failure_class
                else:
                    raise RuntimeError('synthetic overflow unexpectedly accepted as a version')
        record['outcome'] = 'observed'
        record['elapsed_ns'] = time.monotonic_ns() - start
        record['process_returncodes'] = [p.returncode for p in processes]
        for event in events:
            if '_exception' in event:
                event['exception'] = exception_record(event.pop('_exception'))
        return record
    finally:
        for process in processes:
            process.wait(timeout=3)


def positive_count(value):
    count = int(value)
    if not 1 <= count <= 200:
        raise argparse.ArgumentTypeError('iterations must be between 1 and 200')
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layer', choices=['adapter', 'probe', 'minimal'], default='minimal')
    parser.add_argument('--case', choices=['partial', 'eof', 'live'], default='eof')
    parser.add_argument('--iterations', type=positive_count, default=20)
    parser.add_argument('--environment', choices=['codex-exec-pipe', 'codex-exec-pty', 'ordinary-terminal'], required=True)
    parser.add_argument('--signal', choices=['term', 'zero'], default='term')
    parser.add_argument('--delay', type=float, default=0)
    parser.add_argument('--child-metadata', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.delay <= 0.1:
        parser.error('delay must be between 0 and 0.1 seconds')
    if args.layer != 'minimal' and (args.case != 'eof' or args.signal != 'term' or args.delay):
        parser.error('case, signal and delay controls apply only to the minimal layer')
    if args.layer != 'minimal' and args.child_metadata:
        parser.error('child metadata applies only to the minimal layer; adapter preserves the original fake')
    header = {'kind': 'killpg-diagnostic/v1', 'environment_label': args.environment,
              'label_is_operator_supplied': True, 'settings': vars(args),
              'python': sys.version, 'python_binary_name': pathlib.Path(sys.executable).name,
              'python_binary_sha256': hashlib.sha256(pathlib.Path(sys.executable).read_bytes()).hexdigest(),
              'system': platform.system(), 'kernel_release': platform.release(),
              'macos': platform.mac_ver()[0], 'architecture': platform.machine(),
              'parent': {**identity(os.getpid()), 'ppid': os.getppid(),
                         'uid': os.getuid(), 'euid': os.geteuid()},
              'script_sha256': hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
              'stdin_tty': sys.stdin.isatty(), 'stdout_tty': sys.stdout.isatty(),
              'path_redactions': ['<repo>', '<home>'],
              'security_configuration_changed': False, 'official_cli_invoked': False}
    fixture, case = None, None
    try:
        if args.layer != 'minimal':
            sys.path.insert(0, str(ROOT))
            fixture = importlib.import_module('tests.test_cli_session_handoff')
            case = fixture.CliSessionHandoffTests('runTest')
            case.setUp()
            header['fake_executable_sha256'] = hashlib.sha256(case.executable.read_bytes()).hexdigest()
        emit(header)
        counts = collections.Counter()
        for attempt in range(args.iterations):
            record = minimal_trial(args) if args.layer == 'minimal' else adapter_trial(args, fixture, case)
            record.update(kind='trial', attempt=attempt)
            errors = [e['exception']['errno'] for e in record['events'] if 'exception' in e]
            counts['trials'] += 1
            counts['trials_with_eperm'] += errno.EPERM in errors
            counts['signal_calls'] += sum(e['event'] == 'killpg' for e in record['events'])
            if record.get('receipt'):
                counts['receipt_' + record['receipt']['status']] += 1
                if record['receipt']['boundaries']['session_call_performed']:
                    raise RuntimeError('unexpected session call in synthetic version-only diagnostic')
            emit(record)
    finally:
        if case is not None:
            case.doCleanups()
    emit({'kind': 'summary', 'counts': dict(counts),
          'interpretation': 'diagnostic observations; not a success or remediation verdict'})


if __name__ == '__main__':
    main()
