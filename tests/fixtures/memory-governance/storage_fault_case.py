"""Bounded coordinator for newly created synthetic roots; physical mode is image-owner only."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'skills/loop-engineering/scripts'), str(Path(__file__).parent)]
import memory_governance_contract as c
import memory_governance_storage as db

WORKER = Path(__file__).with_name('storage_fault_worker.py')


def worker(request, *, pass_fds=(), timeout=90):
    argv = [str(ROOT / 'scripts/project-python'), str(WORKER)]
    try:
        completed = subprocess.run(argv, input=c.canonical(request), capture_output=True, cwd=ROOT,
                                   timeout=timeout, pass_fds=pass_fds,
                                   env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        output, code, diagnostic = completed.stdout, completed.returncode, completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as error:
        # subprocess.run kills and waits for this exact child; never broad-kills other processes.
        output, code, diagnostic, timed_out = error.stdout or b'', None, b'worker-timeout', True
    if len(output) > c.MAX_ENVELOPE:
        raise RuntimeError('worker-output-limit')
    events = [c.decode(line) for line in output.splitlines() if line]
    return {'events': events, 'returncode': code, 'timed_out': timed_out,
            'diagnostic': diagnostic.decode(errors='replace')[:1000]}


def inventory(parent):
    result = {}
    for path in sorted(parent.rglob('*')):
        if path.is_symlink():
            raise RuntimeError('fixture-symlink')
        if not path.is_file():
            continue
        if len(result) >= 128 or path.stat().st_size > 256 * 1024 * 1024:
            raise RuntimeError('fixture-inventory-limit')
        before = path.stat()
        digest = hashlib.sha256()
        with path.open('rb') as source:
            while block := source.read(65536):
                digest.update(block)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise RuntimeError('fixture-file-drift')
        result[str(path.relative_to(parent))] = {
            'identity': list(db.identity(after)), 'mode': after.st_mode, 'bytes': after.st_size,
            'mtime_ns': str(after.st_mtime_ns), 'sha256': digest.hexdigest()}
    return result


def classify(fault, completed):
    if completed is None:
        return 'no-completed-observation'
    errors = completed['errors']
    codes = {error['code'] & 255 for error in errors}
    if 14 in codes:
        return 'sqlite-cantopen'
    if 13 in codes:
        if fault == 'page-quota':
            quota = completed['quota']
            pages = quota.get('page_count_before')
            effective = quota.get('effective_max_page_count')
            profile = quota.get('profile_max_page_count')
            if (type(pages) is int and pages > 0 and type(effective) is int
                    and effective == pages and type(profile) is int and profile > pages):
                return 'page-quota-sqlite-full'
        if fault == 'physical':
            quota, filling = completed['quota'], completed['filling']
            pages = quota.get('page_count_before')
            effective = quota.get('effective_max_page_count')
            profile = quota.get('profile_max_page_count')
            if (filling.get('os_enospc_observed') is True and not filling.get('failure')
                    and all(type(value) is int and value > 0 for value in (pages, effective, profile))
                    and effective == profile and profile > pages + 256):
                return 'physical-sqlite-full'
        return 'sqlite-full-origin-unproven'
    if codes:
        return 'other-sqlite-error'
    if completed['filling'].get('os_enospc_observed'):
        return 'os-enospc-only'
    if completed['filling'].get('injected_errno') == 28:
        return 'injected-enospc-reply-loss'
    return 'no-sqlite-error'


def fresh_read(parent, prepared, operation):
    host = prepared['host']
    before = inventory(parent)
    child = worker({'mode': 'read', 'host': host, 'operation_id': operation['operation_id'],
                    'preview_digest': operation['preview_digest']}, timeout=30)
    after = inventory(parent)
    events = child.pop('events')
    event = events[0] if len(events) == 1 and events[0].get('event') == 'read' else None
    return {**child, 'observation': event, 'files_unchanged': before == after,
            'before_files_digest': c.digest(before), 'after_files_digest': c.digest(after),
            'new_process': event is not None and event['pid'] != prepared['pid'] and event['pid'] != os.getpid()}


def fresh_read_complete(observation):
    return (observation['returncode'] == 0 and observation['timed_out'] is False
            and observation['files_unchanged'] and observation['new_process']
            and observation['observation'] is not None)


def run_case(parent, fault, *, physical=None, recover=None):
    """parent is freshly created by this fixture's caller. No CLI accepts an existing parent."""
    assert parent.is_absolute() and parent == parent.resolve(strict=True) and not list(parent.iterdir())
    report = {'contract_version': 'mg1-g1-storage-fault/v1', 'fault': fault, 'synthetic_only': True,
              'production_qualified': False, 'attempt_limit': 1, 'status': 'incomplete',
              'worker_timeout_seconds': 90, 'read_timeout_seconds': 30}
    try:
        child = worker({'mode': 'create', 'parent': str(parent), 'fault': fault, 'physical': physical},
                       pass_fds=(() if physical is None else (physical['fd'],)))
    finally:
        # Restoring capacity is separate from database repair, and must run even after child failure.
        if recover is not None:
            report['space_restoration'] = recover()
        else:
            report['space_restoration'] = {'result': 'not-required', 'reason': 'no-physical-filler'}
    events = child.pop('events')
    report['writer'] = child
    prepared = next((event for event in events if event.get('event') == 'prepared'), None)
    completed = next((event for event in events if event.get('event') == 'completed'), None)
    report['classification'] = classify(fault, completed)
    report['completed'] = completed
    if prepared is None:
        report['incomplete_reason'] = 'no-originating-host-binding'
        return report
    report['prepared'] = {key: value for key, value in prepared.items() if key != 'host'}
    report['fresh_attempt'] = fresh_read(parent, prepared, prepared)
    report['fresh_normal'] = fresh_read(parent, prepared, prepared['normal'])
    attempt, normal = report['fresh_attempt'], report['fresh_normal']
    for observation in (attempt, normal):
        if not fresh_read_complete(observation):
            report['incomplete_reason'] = 'fresh-readback-incomplete-or-mutated'
            return report
    result = attempt['observation']['result']
    original = normal['observation']['result']
    report['journal_requires_maintenance'] = (
        attempt['observation']['audit'].get('reason') == 'recovery-required'
        or normal['observation']['audit'].get('reason') == 'recovery-required')
    report['failed_transaction_unchanged'] = (
        result['result'] == 'state-unknown' and result['proof'] is None
        and result['state_digest'] == prepared['before_digest']
        and original['result'] == 'applied' and original['proof'] == prepared['normal']['proof']
        and original['state_digest'] == prepared['before_digest']
        and attempt['observation']['projection']['blue'] == normal['observation']['projection']['blue']
        and len(attempt['observation']['projection']['blue']) == 1
        and not attempt['observation']['projection']['green'])
    report['committed_transaction_consistent'] = (
        result['result'] == 'applied' and result['proof'] is not None
        and result['state_digest'] == prepared['expected_after_digest']
        and result['proof']['after_revision'] == 2
        and original['result'] == 'state-unknown' and original['proof'] == prepared['normal']['proof']
        and not attempt['observation']['projection']['blue']
        and len(attempt['observation']['projection']['green']) == 1)
    outcome = completed['outcome'] if completed is not None else {}
    report['executor_result_consistent'] = (
        report['failed_transaction_unchanged']
        and outcome.get('result') in {'not-applied', 'state-unknown'} and outcome.get('proof') is None
        or report['committed_transaction_consistent']
        and outcome.get('result') == 'applied' and outcome.get('proof') == result['proof']
        and outcome.get('state_digest') == result['state_digest'])
    clean_reads = all(value['observation']['replay_rejection'] == 'handle-unrecognized-or-consumed'
                      and 'accept' not in value['observation']['calls'] for value in (attempt, normal))
    expected = {
        'none': 'no-sqlite-error', 'page-quota': 'page-quota-sqlite-full',
        'missing-path-cantopen': 'sqlite-cantopen', 'physical': 'physical-sqlite-full',
        'reply-loss': 'injected-enospc-reply-loss',
    }
    if report['journal_requires_maintenance']:
        report['incomplete_reason'] = 'nonempty-journal-preserved; G2-maintenance-required'
    elif report['space_restoration']['result'] not in {'restored', 'not-required'}:
        report['incomplete_reason'] = 'own-filler-space-restoration-failed'
    elif (completed is not None and not child['timed_out'] and child['returncode'] == 0 and clean_reads
          and completed['replay_rejection'] == 'handle-unrecognized-or-consumed'
          and not completed['measurement']['sample_errors']
          and completed['measurement']['coverage']['lock_intervals_complete']
          and report['executor_result_consistent']
          and report['classification'] == expected.get(fault)
          and (report['failed_transaction_unchanged'] if fault in {
              'page-quota', 'missing-path-cantopen', 'physical'} else report['committed_transaction_consistent'])):
        report['status'] = 'observed'
    else:
        report['incomplete_reason'] = 'expected-error-or-state-consistency-not-established'
    if report['status'] == 'observed' and report['failed_transaction_unchanged']:
        control = worker({'mode': 'continue', 'host': prepared['host'],
                          'failed_operation_id': prepared['operation_id']}, timeout=30)
        entries = control.pop('events')
        event = entries[0] if len(entries) == 1 and entries[0].get('event') == 'control' else None
        report['recovery_control'] = {**control, 'new_preview_and_confirmation': True,
                                     'observation': None if event is None else
                                         {key: value for key, value in event.items() if key != 'host'}}
        if (event is None or control['returncode'] != 0 or control['timed_out'] is not False
                or event['result']['result'] != 'applied'):
            report.update(status='incomplete', incomplete_reason='newly-confirmed-control-failed')
        else:
            report['recovery_control']['fresh_read'] = fresh_read(
                parent, {'host': event['host'], 'pid': event['pid']}, event['result'])
            fresh = report['recovery_control']['fresh_read']
            observed = fresh['observation']
            if (not fresh_read_complete(fresh)
                    or observed['result']['result'] != 'applied'
                    or observed['result']['proof'] != event['result']['proof']
                    or observed['result']['proof']['after_revision'] != 2
                    or observed['result']['operation_id'] == prepared['operation_id']):
                report.update(status='incomplete', incomplete_reason='recovery-control-readback-unproven')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', choices=['none', 'page-quota', 'missing-path-cantopen', 'reply-loss', 'precommit-loss'],
                        default='page-quota')
    args = parser.parse_args()
    parent = Path(tempfile.mkdtemp(prefix='mg1-253-storage-')).resolve()
    try:
        report = run_case(parent, args.fault)
    except Exception as error:
        report = {'status': 'incomplete', 'fault': args.fault, 'synthetic_only': True,
                  'production_qualified': False, 'incomplete_reason': 'coordinator-exception',
                  'failure': type(error).__name__, 'diagnostic': str(error)[:1000]}
    # Retain every CLI fixture, including journals after incomplete or unexpected outcomes.
    report['retained_fixture'] = str(parent)
    try:
        with (parent / 'observation.json').open('x', encoding='utf-8') as output:
            output.write(json.dumps(report, indent=2, sort_keys=True) + '\n')
    except OSError as error:
        report.update(status='incomplete', report_save_failure={'errno': error.errno})
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['status'] == 'observed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
