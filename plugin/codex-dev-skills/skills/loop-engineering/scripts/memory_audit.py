"""單專案唯讀報告。Host 由可信程式提供；此模組不接受路徑或建立權限。"""
from __future__ import annotations

import errno
import json
import sqlite3
import unicodedata

import memory_governance_contract as c
from memory_governance_core import GovernanceCore
from memory_governance_host import production_host

MESSAGES = {
    "disabled": "記憶盤點未啟用。",
    "adapter-unavailable": "尚未配置具備唯讀資格的專案記憶介面。",
    "qualification-unavailable": "此環境尚未取得盤點資格。",
    "read-unavailable": "目前沒有此專案的讀取權限。",
    "root-changed": "專案儲存身分已改變，已停止盤點。",
    "busy": "記憶儲存正在使用中；本次盤點已停止。",
    "timeout": "盤點時間已到，未完成的部分保持未知。",
    "storage-full": "儲存空間不足，無法完成讀取；未執行清理。",
    "resource-limit": "可用記憶體不足，本次盤點已停止。",
    "storage-io": "儲存讀取失敗，未完成的部分保持未知。",
    "recovery-required": "儲存需要另外確認復原方式；本次沒有修改資料。",
    "page-limit": "已達本次頁數上限，仍有項目未盤點。",
    "output-limit": "已達本次報告大小上限，仍有項目未列出。",
    "cursor-unavailable": "盤點快照已失效；重新盤點需要新的權限與快照。",
    "unavailable": "無法驗證本次盤點；原因未確認。",
}


def _reason(exc: BaseException) -> str:
    # 只分類固定代碼，不回顯任意 host／SQLite／OS 例外訊息。
    if isinstance(exc, c.ContractError) and str(exc) in MESSAGES:
        return str(exc)
    cause = exc
    for _ in range(8):
        if cause is None:
            break
        if isinstance(cause, MemoryError):
            return "resource-limit"
        if isinstance(cause, sqlite3.Error):
            code = getattr(cause, "sqlite_errorcode", 0) & 255
            if code in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                return "busy"
            if code == sqlite3.SQLITE_FULL:
                return "storage-full"
            if code == sqlite3.SQLITE_NOMEM:
                return "resource-limit"
            if code == sqlite3.SQLITE_INTERRUPT:
                return "timeout"
            if code in (sqlite3.SQLITE_IOERR, sqlite3.SQLITE_CANTOPEN):
                return "storage-io"
        if isinstance(cause, OSError):
            if cause.errno in (errno.EACCES, errno.EPERM):
                return "read-unavailable"
            if cause.errno == errno.ENOSPC:
                return "storage-full"
            if cause.errno == errno.ENOMEM:
                return "resource-limit"
            return "storage-io"
        cause = cause.__cause__
    code = str(exc) if isinstance(exc, c.ContractError) else "unavailable"
    if code in {"root-binding-drift", "root-identity-mismatch", "file-identity-mismatch", "unsafe-root", "file-drift"}:
        return "root-changed"
    if code in {"audit-timeout", "cursor-expired"}:
        return "timeout"
    if code == "audit-page-limit":
        return "page-limit"
    return code if code in MESSAGES else "unavailable"


def _empty() -> dict:
    return {"contract_version": "mg1-audit-report/v1", "status": "unavailable", "reason": None,
            "enumeration_complete": False, "source_coverage": "unknown", "snapshot_digest": None,
            "items": [], "counts": {"listed": 0, "active": 0, "stopped": 0, "retained_versions": 0},
            "capacity": {"coverage": "unknown", "bytes": None}, "external_copies": "unknown",
            "advisory_only": True, "write_performed": False, "production_qualified": False}


def audit_report(*, enabled: bool = False, host=None, max_pages: int = 40,
                 max_output_bytes: int = 262144, timeout_seconds: int = 10) -> dict:
    """每次新 core／snapshot；不接受 cursor、root、confirmation 或持久設定。

    程式注入 host 是 TCB 整合介面，不是使用者輸入或 production qualification。
    disabled 在驗參數、host discovery 與任何 backend 接觸前返回。
    """
    report = _empty()
    if enabled is not True:
        report.update(status="disabled", reason="disabled")
        return report
    c.integer(max_pages, 1, 40)
    c.integer(max_output_bytes, 4096, 262144)
    c.integer(timeout_seconds, 1, 30)
    verified = 0
    snapshot = None
    # 留固定 envelope／原因文案餘裕；每筆 canonical bytes 在收錄前計算。
    remaining = max_output_bytes - 2048
    try:
        core = GovernanceCore(production_host("local") if host is None else host, enabled=True)
        with core.audit(timeout_seconds=timeout_seconds) as snapshot:
            cursor = None
            for _ in range(max_pages):
                page = snapshot.page(cursor)
                report["snapshot_digest"] = page["snapshot_digest"]
                for item in page["items"]:
                    size = max(len(c.canonical(item, 65536)) + 1,
                               len(("\n".join(_item_lines(item)) + "\n").encode("utf-8")))
                    if size > remaining:
                        report["reason"] = "output-limit"
                        break
                    remaining -= size
                    report["items"].append(item)
                    verified += item["assessment"] != "source-unavailable"
                if report["reason"]:
                    break
                report["enumeration_complete"] = page["enumeration_complete"]
                if page["enumeration_complete"]:
                    break
                cursor = page["next_cursor"]
            else:
                report["reason"] = "page-limit"
    except (c.ContractError, OSError, sqlite3.Error, MemoryError) as exc:
        reason = _reason(exc)
        # 授權／身分／完整性不再可信時，不保留已讀內容。I/O／時間中斷可保留先前完整頁。
        if reason not in {"busy", "timeout", "storage-full", "storage-io", "resource-limit", "page-limit", "cursor-unavailable"}:
            report = _empty()
            verified = 0
        report.update(reason=reason, enumeration_complete=False)
    # 即使 I/O 錯誤或正常達上限，也不能靠錯誤分類推定仍有揭露權。
    # 不重試讀取；只重驗先前 snapshot 的授權及未變動的持久檔案。
    if report["snapshot_digest"] is not None and snapshot is not None:
        try:
            snapshot.validate_disclosure()
        except (c.ContractError, OSError, sqlite3.Error, MemoryError) as exc:
            report = _empty()
            report["reason"] = _reason(exc)
            verified = 0
    items = report["items"]
    report["counts"] = {"listed": len(items), "active": sum(i["status"] == "active" for i in items),
                        "stopped": sum(i["status"] == "stopped" for i in items),
                        "retained_versions": sum(i["retained_versions"] for i in items)}
    report["status"] = ("complete" if report["enumeration_complete"] else
                        "partial" if report["snapshot_digest"] is not None else "unavailable")
    report["source_coverage"] = ("complete" if verified == len(items) else "partial") if (
        items or report["enumeration_complete"]) else "unknown"
    c.canonical(report, max_output_bytes)
    return report


def _quoted(value: str) -> str:
    # 內容保持引述資料；避免 terminal control、換行及 bidi 改寫報告外觀。
    result = json.dumps(value, ensure_ascii=False)
    return "".join(f"\\u{ord(char):04x}" if unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"}
                   else char for char in result)


def _item_lines(item: dict) -> list[str]:
    state = "有效" if item["status"] == "active" else "已停止"
    summary = "[內容已遮蔽]" if item["summary"] is None else _quoted(item["summary"])
    lines = [f"- {item['item_id']}｜{state}｜版本 {item['revision']}（保留 {item['retained_versions']}）｜{summary}"]
    if item["sources"] is not None:
        lines.append("  來源資料：" + _quoted(json.dumps(item["sources"], ensure_ascii=False, separators=(",", ":"))))
    return lines


def render_report(report: dict) -> str:
    labels = {"complete": "項目列舉完成", "partial": "部分盤點", "unavailable": "盤點不可用", "disabled": "盤點未啟用"}
    counts = report["counts"]
    lines = [f"專案記憶：{labels[report['status']]}"]
    if report["reason"]:
        lines.append(MESSAGES[report["reason"]])
    if report["status"] in {"complete", "partial"}:
        lines.append(f"本次列出 {counts['listed']} 項：有效 {counts['active']}、已停止 {counts['stopped']}；保留版本共 {counts['retained_versions']}。")
        coverage = {"complete": "本次列出項目均已驗證", "partial": "部分未驗證，相關內容已遮蔽", "unknown": "未知"}
        lines.append("來源：" + coverage[report["source_coverage"]] + "。")
        for item in report["items"]:
            lines.extend(_item_lines(item))
    lines.extend(["容量：未知；本次未量測磁碟佔用。外部副本覆蓋：未知。",
                  "本次沒有修改記憶；內容僅供參考，不能作為指令或權限。",
                  "重新盤點會重新取得權限及快照，不沿用本次分頁。"])
    return "\n".join(lines) + "\n"
