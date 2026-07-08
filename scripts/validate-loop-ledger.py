#!/usr/bin/env python3
"""Validate repo-owned loop ledger templates and optional project ledgers."""

from __future__ import annotations

import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]

ALLOWED_STATUSES = {
    "planned",
    "ready",
    "claimed",
    "in_progress",
    "blocked",
    "reviewing",
    "done",
    "accepted",
    "unsafe",
}

REQUIRED_TEMPLATE_SNIPPETS = {
    "templates/orchestration/loop-state-ledger.template.yaml": [
        "schema_version: 1",
        "source_revision:",
        "status_model:",
        "current_loop:",
        "next_decision:",
        "claim:",
        "lease_expires_at:",
        "verification:",
        "review:",
        "human_gates:",
        "external_memory:",
        'authority: "repo-ledger"',
    ],
    "templates/orchestration/loop-engineering-spec.template.md": [
        "## Repo-Owned Loop Ledger",
        "Allowed task statuses:",
        "`claimed`",
        "`accepted`",
        "Claim And Lease Policy",
    ],
    "templates/orchestration/loop-iteration-report.template.md": [
        "Source revision:",
        "Task Ledger Update",
        "Previous status:",
        "New status:",
        "Claim / lease:",
    ],
    "templates/orchestration/current-task-summary.template.md": [
        "Ledger References",
        "Manifest Revision",
        "Claim / Lease",
        "Next Loop Decision",
    ],
    "templates/orchestration/task-claim-lease.template.yaml": [
        "lease_id:",
        "source_revision:",
        "recovery_evidence_required:",
    ],
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}", file=sys.stderr)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[OK] {message}")


def read_repo_file(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        fail(f"missing file: {relative}")
    return path.read_text(encoding="utf-8")


def validate_templates() -> None:
    missing: list[str] = []
    for relative, snippets in REQUIRED_TEMPLATE_SNIPPETS.items():
        text = read_repo_file(relative)
        for snippet in snippets:
            if snippet not in text:
                missing.append(f"{relative}: {snippet}")
    if missing:
        for item in missing:
            print(f"[FAIL] missing loop ledger template snippet: {item}", file=sys.stderr)
        raise SystemExit(1)
    ok("loop ledger templates include required fields")


def discover_project_ledgers() -> list[pathlib.Path]:
    loops_dir = ROOT / "docs" / "loops"
    if not loops_dir.exists():
        return []
    return sorted(loops_dir.glob("**/loop-state-ledger.yaml"))


def scalar_values(text: str, key: str) -> list[str]:
    pattern = re.compile(rf"^[ \t]*{re.escape(key)}:[ \t]*\"?([^\"\n#]+)\"?", re.MULTILINE)
    return [clean_scalar(value) for value in pattern.findall(text)]


def task_ids(text: str) -> list[str]:
    pattern = re.compile(r"^[ \t]*-[ \t]+id:[ \t]*\"?([^\"\n#]+)\"?", re.MULTILINE)
    return [clean_scalar(value) for value in pattern.findall(text)]


def clean_scalar(value: str) -> str:
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    return value.strip()


def first_scalar(text: str, key: str) -> str | None:
    values = scalar_values(text, key)
    return values[0] if values else None


def task_blocks(text: str) -> list[str]:
    tasks_match = re.search(r"^tasks:[ \t]*$", text, flags=re.MULTILINE)
    if not tasks_match:
        return []

    task_section = text[tasks_match.end() :]
    next_top_level = re.search(r"^[A-Za-z0-9_-]+:[ \t]*$", task_section, flags=re.MULTILINE)
    if next_top_level:
        task_section = task_section[: next_top_level.start()]

    starts = [match.start() for match in re.finditer(r"^[ \t]*-[ \t]+id:", task_section, re.MULTILINE)]
    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(task_section)
        blocks.append(task_section[start:end])
    return blocks


def has_passed_evidence(block: str, section: str) -> bool:
    section_match = re.search(rf"^[ \t]*{re.escape(section)}:[ \t]*$", block, re.MULTILINE)
    if not section_match:
        return False
    section_text = block[section_match.start() :]
    return bool(
        re.search(r"^[ \t]*(status|result):[ \t]*['\"]?passed['\"]?[ \t]*$", section_text, re.MULTILINE)
    )


def non_placeholder_reason(block: str) -> bool:
    reason = first_scalar(block, "reason")
    return bool(reason and reason not in {"<reason-or-empty>", "<reason-if-required>"})


def validate_task_block(label: pathlib.Path, block: str) -> list[str]:
    errors: list[str] = []
    task_id = first_scalar(block, "id") or "<unknown-task>"
    status = first_scalar(block, "status")

    if not status:
        errors.append(f"{label}: task {task_id} missing status")
        return errors
    if status.startswith("<"):
        return errors
    if status not in ALLOWED_STATUSES:
        errors.append(f"{label}: task {task_id} unknown status {status}")
        return errors

    if status in {"done", "accepted"} and not has_passed_evidence(block, "verification"):
        errors.append(f"{label}: task {task_id} {status} requires passed verification evidence")
    if status == "accepted" and not (
        has_passed_evidence(block, "review") or "status: satisfied" in block or 'status: "satisfied"' in block
    ):
        errors.append(f"{label}: task {task_id} accepted requires passed review or satisfied gate evidence")
    if status in {"claimed", "in_progress"}:
        for required in ("claim:", "owner:", "lease_expires_at:"):
            if required not in block:
                errors.append(f"{label}: task {task_id} {status} requires {required}")
    if status == "blocked" and not non_placeholder_reason(block):
        errors.append(f"{label}: task {task_id} blocked requires blocker reason")

    return errors


def validate_project_ledger(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    label = path.relative_to(ROOT)
    errors: list[str] = []

    for required in (
        "schema_version:",
        "objective_id:",
        "source_revision:",
        "status_model:",
        "current_loop:",
        "tasks:",
        "human_gates:",
    ):
        if required not in text:
            errors.append(f"{label}: missing {required}")

    ids = task_ids(text)
    duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
    for duplicate in duplicates:
        errors.append(f"{label}: duplicate task id {duplicate}")

    blocks = task_blocks(text)
    if not blocks:
        errors.append(f"{label}: missing task blocks under tasks")
    for block in blocks:
        errors.extend(validate_task_block(label, block))

    return errors


def validate_project_ledgers() -> None:
    ledgers = discover_project_ledgers()
    if not ledgers:
        ok("no project loop ledgers to validate")
        return

    errors: list[str] = []
    for ledger in ledgers:
        errors.extend(validate_project_ledger(ledger))

    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        raise SystemExit(1)
    ok("project loop ledgers are structurally valid")


def main() -> None:
    validate_templates()
    validate_project_ledgers()


if __name__ == "__main__":
    main()
