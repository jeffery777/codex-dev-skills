"""Shared one-shot maintenance；真實 runtime 無正式 host ports 時 unavailable。"""
from __future__ import annotations

from contextlib import closing

import memory_governance_contract as c
import memory_governance_storage as db
from memory_audit import _reason as storage_reason
from memory_governance_core import GovernanceCore
from memory_maintenance_dispatch import MaintenanceDispatch

REASONS = frozenset({'authority-unavailable', 'request-not-accepted', 'request-revoked',
    'request-consumed-or-unrecognized', 'request-scope-mismatch', 'request-preview-mismatch',
    'qualification-unavailable', 'source-unavailable', 'expired-or-clock-changed', 'expired',
    'confirmation-consumed', 'dispatch-consumed', 'process-changed', 'capability-unavailable',
    'root-binding-mismatch', 'revision-conflict', 'state-conflict', 'identity-conflict',
    'source-identity-mismatch', 'source-integrity-failed', 'acceptance-unavailable',
    'state-unknown', 'verification-mismatch', 'preview-unrecognized', 'host-unavailable',
    'inspection-unavailable', 'scope-unavailable', 'confirmation-port-unavailable', 'storage-port-unavailable'})


def reason(exc):
    cause = exc
    for _ in range(8):
        if cause is None:
            break
        if isinstance(cause, c.ContractError) and str(cause) in REASONS and str(cause) != 'host-unavailable':
            return str(cause)
        cause = cause.__cause__
    return storage_reason(exc)


def _verify(host, fresh, readback, preview):
    """新 reader／read-only connection，核對當前 revision、保留版本及 recall。

    每個 snapshot 必須仍等於 proof after digest；合法並行前進也回 unknown，
    不以舊 proof 宣稱目前狀態。只向呼叫端回有界驗證摘要，不揭露內容。
    """
    binding = host.binding()
    scope, limits = c.decode(binding.scope_bytes), c.decode(binding.profile_bytes)
    host.check()
    with db.locked(binding), closing(db.connect(binding, limits)) as connection:
        connection.execute('BEGIN')
        state = db.snapshot(connection, scope, limits)
        c.require(state.digest == readback['state_digest'], 'verification-mismatch')
        item = db.load_item(connection, preview['item_id'], scope, limits)
        c.require(item is not None and item['current_revision'] == readback['proof']['after_revision']
                  and item['projection_digest'] == readback['proof']['projection_digest'], 'verification-mismatch')
    current = item['versions'][-1]
    cues = sorted({cue for version in item['versions'] for cue in version['cues']})
    for cue in cues:
        result = fresh.recall([cue])
        matches = [entry for entry in result['items'] if entry['item_id'] == item['item_id']]
        expected = item['status'] == 'active' and cue in current['cues']
        c.require(result['snapshot_digest'] == state.digest and result['enumeration_complete']
                  and (len(matches) == 1 if expected else not matches)
                  and all(entry['version'] == current for entry in matches), 'verification-mismatch')
    host.check()
    if host.reader is not None:
        host.reader.validate_disclosure()
        c.require(host.reviewer.disclosure_valid(), 'source-unavailable')
    return {'revision': item['current_revision'], 'retained_versions': len(item['versions']),
            'item_status': item['status'], 'current_only_verified': True}


def maintenance_report(*, enabled=False, dispatch=None, emit=None):
    report = {'contract_version': 'memory-maintenance-result/v1', 'status': 'disabled',
              'outcome': 'not-applied', 'reason': 'disabled', 'operation_id': None,
              'preview_digest': None, 'proof': None, 'verification': None,
              'mutation_attempted': False, 'production_qualified': False,
              'runtime_proven': False, 'output_delivered': None}
    # Off returns before validating, touching callbacks, importing production or consuming authority.
    if enabled is not True:
        return report
    host = core = preview = None
    try:
        c.require(dispatch is not None, 'adapter-unavailable')
        c.require(type(dispatch) is MaintenanceDispatch, 'authority-unavailable')
        host = dispatch.acquire()
        value = c.decode(dispatch.request.intent_bytes, 20000)
        core = GovernanceCore(host, enabled=True)
        preview = core.preview(value['operation'], value['item_id'], value['candidate'],
                               restore_revision=value['restore_revision'])
        report.update(operation_id=preview['operation_id'], preview_digest=c.digest(preview))
        handle = core.authorize(preview)
        report['mutation_attempted'] = True
        report['outcome'] = 'unknown'
        try:
            core.execute(handle)
        except Exception as exc:
            # An exception is not a rollback receipt. Exactly one independent read follows.
            report['reason'] = reason(exc)
        reader = host.fresh_reader()
        fresh = GovernanceCore(reader, enabled=True)
        readback = fresh.readback(preview['operation_id'], c.digest(preview), preview=preview)
        report['proof'] = readback['proof']
        if readback['result'] == 'applied':
            report['verification'] = _verify(reader, fresh, readback, preview)
            report.update(status='complete', outcome='applied', reason='verified')
        elif readback['result'] == 'not-applied':
            report.update(status='not-applied', outcome='not-applied', reason='verified-not-applied')
        else:
            report.update(status='unknown', outcome='unknown', reason=readback['result'])
    except Exception as exc:
        report.update(status='unknown' if report['mutation_attempted'] else 'unavailable', reason=reason(exc))
    finally:
        if core is not None:
            core.cancel()
    if emit is not None:
        try:
            emit(c.decode(c.canonical(report)))
            report['output_delivered'] = True
        except Exception:
            # Preserve the observed outcome; failed delivery must never replay the mutation.
            report.update(status='output-unavailable', output_delivered=False, reason='output-unavailable')
    return report


def desktop_maintenance(*, enabled=False, dispatch=None, emit=None):
    """Desktop host adapter：只接可信程式 dispatch，無 UI/內部 runtime 探索或自動確認。"""
    return maintenance_report(enabled=enabled, dispatch=dispatch, emit=emit)


def render_report(report):
    labels = {'applied': '已套用並讀回驗證', 'not-applied': '未套用', 'unknown': '結果未知'}
    return f"記憶維護：{labels[report['outcome']]}；{report['reason']}。\n"
