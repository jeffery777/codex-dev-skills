#!/usr/bin/env python3
"""Validate loop templates and project ledgers through structured YAML parsing."""

from __future__ import annotations

import pathlib
import hashlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOOP_SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(LOOP_SCRIPTS))

try:
    import yaml
    import loop_yaml
except (ModuleNotFoundError, RuntimeError) as exc:
    print(
        "[FAIL] structured loop validation requires PyYAML; "
        "run `python3 -m pip install -r requirements.txt`",
        file=sys.stderr,
    )
    raise SystemExit(2) from exc


REQUIRED_TEMPLATE_SNIPPETS = {
    "templates/orchestration/loop-engineering-spec.template.md": [
        "## Repo-Owned Loop Ledger",
        "Allowed task statuses:",
        "Claim And Lease Policy",
    ],
    "templates/orchestration/loop-iteration-report.template.md": [
        "Source revision:",
        "Task Ledger Update",
        "Previous status:",
        "New status:",
        "Claim / lease:",
    ],
    "templates/orchestration/loop-event.template.yaml": [
        "idempotency_key:",
        "expected_state_revision:",
        "previous_event_hash:",
        "event_hash:",
        "authorization_receipt_sha256",
        "protected_payload_sha256",
    ],
    "templates/orchestration/loop-decision-input.template.yaml": [
        "requires_external_write:",
        "source_conflict:",
        "capabilities:",
        "ownership_disjoint:",
        "goal_status:",
        "security_scan:",
        "protected_history_sha256:",
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


def ok(message: str) -> None:
    print(f"[OK] {message}")


def read_repo_file(relative: str) -> str:
    path = ROOT / relative
    if not path.is_file():
        raise ValueError(f"missing file: {relative}")
    return path.read_text(encoding="utf-8")


def validate_templates() -> list[str]:
    errors: list[str] = []
    ledger_path = ROOT / "templates" / "orchestration" / "loop-state-ledger.template.yaml"
    try:
        ledger = loop_yaml.load_yaml(ledger_path)
    except loop_yaml.LedgerValidationError as exc:
        errors.append(str(exc))
    else:
        errors.extend(
            f"{ledger_path.relative_to(ROOT)}: {error}"
            for error in loop_yaml.validate_ledger(ledger, allow_placeholders=True)
        )
    event_path = ROOT / "templates" / "orchestration" / "loop-event.template.yaml"
    try:
        event = loop_yaml.load_yaml(event_path)
    except loop_yaml.LedgerValidationError as exc:
        errors.append(str(exc))
    else:
        required_event_keys = {
            "sequence",
            "event_id",
            "occurred_at",
            "actor",
            "type",
            "task_id",
            "idempotency_key",
            "expected_state_revision",
            "previous_event_hash",
            "payload",
            "event_hash",
        }
        missing = sorted(required_event_keys - set(event))
        if missing:
            errors.append(f"{event_path.relative_to(ROOT)}: missing keys {', '.join(missing)}")
        if not isinstance(event.get("payload"), dict):
            errors.append(f"{event_path.relative_to(ROOT)}: payload must be a mapping")
        if not str(event.get("type", "")).startswith("<"):
            errors.append(f"{event_path.relative_to(ROOT)}: type must remain an explicit placeholder")
    decision_path = ROOT / "templates" / "orchestration" / "loop-decision-input.template.yaml"
    try:
        decision = loop_yaml.load_yaml(decision_path)
    except loop_yaml.LedgerValidationError as exc:
        errors.append(str(exc))
    else:
        if not isinstance(decision.get("input"), dict):
            errors.append(f"{decision_path.relative_to(ROOT)}: input must be a mapping")
        for section in ("request", "objective", "state", "runtime", "work"):
            if not isinstance((decision.get("input") or {}).get(section), dict):
                errors.append(f"{decision_path.relative_to(ROOT)}: input.{section} must be a mapping")
        if "authority" in (decision.get("input") or {}):
            errors.append(
                f"{decision_path.relative_to(ROOT)}: trusted authority must not be stored in input"
            )
    for relative, snippets in REQUIRED_TEMPLATE_SNIPPETS.items():
        try:
            text = read_repo_file(relative)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        for snippet in snippets:
            if snippet not in text:
                errors.append(f"{relative}: missing required content {snippet!r}")
    return errors


def discover_project_ledgers() -> list[pathlib.Path]:
    loops_dir = ROOT / "docs" / "loops"
    if not loops_dir.exists():
        return []
    return sorted(loops_dir.glob("**/loop-state-ledger.yaml"))


def validate_project_ledger(path: pathlib.Path) -> list[str]:
    try:
        document = loop_yaml.load_yaml(path)
    except loop_yaml.LedgerValidationError as exc:
        return [str(exc)]
    label = path.relative_to(ROOT)
    errors = loop_yaml.validate_ledger(document)
    if (document.get("ledger") or {}).get("schema_version") != 2:
        errors.append("project loop ledger requires schema_version 2")
    if errors:
        return [f"{label}: {error}" for error in errors]
    ledger = document["ledger"]
    source = ledger.get("source_revision") or {}

    def resolve(reference: object, label: str) -> pathlib.Path | None:
        if not isinstance(reference, str) or not reference or reference.startswith("<"):
            return None
        candidate = pathlib.Path(reference)
        candidates = [candidate] if candidate.is_absolute() else [ROOT / candidate, path.parent / candidate]
        selected = next((item for item in candidates if item.is_file()), candidates[0])
        resolved = selected.resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{label} must stay within the repository")
            return None
        return resolved

    manifest_path = resolve(ledger.get("task_manifest"), "task manifest")
    spec_path = resolve(ledger.get("loop_spec"), "loop spec")
    if manifest_path is None or not manifest_path.is_file():
        errors.append("task manifest is required for semantic replay")
    else:
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if digest != source.get("task_manifest_sha256"):
            errors.append("task manifest digest mismatch")
    if spec_path is None or not spec_path.is_file():
        errors.append("loop spec is required for source revision verification")
    else:
        digest = hashlib.sha256(spec_path.read_bytes()).hexdigest()
        if digest != source.get("spec_sha256"):
            errors.append("loop spec digest mismatch")
    try:
        head = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "-C", str(ROOT), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        errors.append("could not verify git source revision")
    else:
        if source.get("head_sha") != head:
            errors.append("git HEAD source revision mismatch")
        if source.get("branch") != branch:
            errors.append("git branch source revision mismatch")
    if not errors and manifest_path is not None:
        definitions = loop_yaml.manifest_definitions(
            loop_yaml.load_yaml(manifest_path),
            expected_objective_id=ledger.get("objective_id"),
        )
        errors.extend(loop_yaml.semantic_audit(document, definitions))
    return [f"{label}: {error}" for error in errors]


def validate_task_block(label: pathlib.Path, block: str) -> list[str]:
    """Compatibility helper for older tests, backed by the structured parser."""
    try:
        parsed = yaml.safe_load("tasks:\n" + block)
    except yaml.YAMLError as exc:
        return [f"{label}: malformed YAML: {exc}"]
    tasks = parsed.get("tasks") if isinstance(parsed, dict) else None
    if not isinstance(tasks, list) or len(tasks) != 1 or not isinstance(tasks[0], dict):
        return [f"{label}: expected exactly one task mapping"]
    document = {
        "ledger": {
            "schema_version": 1,
            "objective_id": "compatibility-test",
            "objective": "compatibility test",
            "source_revision": {
                "branch": "test",
                "head_sha": "test",
                "updated_at": "2026-01-01T00:00:00Z",
            },
        },
        "tasks": tasks,
    }
    return [f"{label}: {error}" for error in loop_yaml.validate_ledger(document)]


def main() -> int:
    errors = validate_templates()
    ledgers = discover_project_ledgers()
    for ledger in ledgers:
        errors.extend(validate_project_ledger(ledger))
    if errors:
        for error in errors:
            print(f"[FAIL] {error}", file=sys.stderr)
        return 1
    ok("loop ledger templates are structurally valid")
    ok(f"validated {len(ledgers)} project loop ledger(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
