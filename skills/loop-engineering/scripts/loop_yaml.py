"""Structured YAML validation and v1 migration helpers for Loop Engineering."""

from __future__ import annotations

import copy
import datetime as dt
import pathlib
import re
from typing import Any

import loop_core

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised in a dependency-free subprocess.
    yaml = None


V1_STATUSES = {
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
V2_STATUSES = {"planned", "ready", "in_progress", "blocked", "reviewing", "done", "accepted", "cancelled"}
REVIEW_MODES = {
    "none",
    "code-review",
    "code-review-deep",
    "docs-review",
    "formal-gate",
}
OPAQUE_ADAPTER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


class LedgerValidationError(ValueError):
    pass


def _require_yaml() -> Any:
    if yaml is None:
        raise RuntimeError(
            "PyYAML is required for loop YAML commands; run "
            "`python3 -m pip install -r <installed-loop-engineering>/requirements.txt`"
        )
    return yaml


def load_yaml(path: pathlib.Path) -> dict[str, Any]:
    parser = _require_yaml()

    class UniqueKeyLoader(parser.SafeLoader):
        pass

    def construct_mapping(loader: Any, node: Any, deep: bool = False) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as exc:
                raise parser.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable mapping key",
                    key_node.start_mark,
                ) from exc
            if duplicate:
                raise parser.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = loader.construct_object(value_node, deep=deep)
        return mapping

    UniqueKeyLoader.add_constructor(
        parser.resolver.BaseResolver.DEFAULT_MAPPING_TAG, construct_mapping
    )
    try:
        value = parser.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
    except (OSError, parser.YAMLError) as exc:
        raise LedgerValidationError(f"could not parse {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LedgerValidationError(f"{path}: root must be a mapping")
    return value


def dump_yaml(document: dict[str, Any]) -> str:
    parser = _require_yaml()
    return parser.safe_dump(document, sort_keys=False, allow_unicode=True)


def _timestamp(
    value: Any,
    label: str,
    errors: list[str],
    *,
    allow_empty: bool = False,
    allow_placeholders: bool = False,
) -> None:
    if allow_empty and value in (None, ""):
        return
    if isinstance(value, dt.datetime):
        return
    if not isinstance(value, str):
        errors.append(f"{label} must be an ISO-8601 string")
        return
    if value.startswith("<") and allow_placeholders:
        return
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} must be a valid ISO-8601 timestamp")


def _parsed_timestamp(value: Any) -> dt.datetime | None:
    if isinstance(value, dt.datetime):
        parsed = value
    elif isinstance(value, str) and not _placeholder(value):
        try:
            parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=dt.timezone.utc)


def _placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("<")


def _nonempty(value: Any, *, allow_placeholders: bool) -> bool:
    return isinstance(value, str) and bool(value) and (allow_placeholders or not _placeholder(value))


def _sha256_or_placeholder(value: Any, *, allow_placeholders: bool) -> bool:
    return bool(
        isinstance(value, str)
        and (
            (allow_placeholders and _placeholder(value))
            or (len(value) == 64 and all(character in "0123456789abcdef" for character in value))
        )
    )


def _task_list(document: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        return []
    return [task for task in tasks if isinstance(task, dict)]


def _dependency_cycle(graph: dict[str, list[str]]) -> str | None:
    state: dict[str, int] = {}
    for start in graph:
        if state.get(start) == 2:
            continue
        stack: list[tuple[str, bool]] = [(start, False)]
        while stack:
            task_id, exiting = stack.pop()
            if exiting:
                state[task_id] = 2
                continue
            current = state.get(task_id, 0)
            if current == 1:
                return task_id
            if current == 2:
                continue
            state[task_id] = 1
            stack.append((task_id, True))
            for dependency in reversed(graph.get(task_id, [])):
                if dependency not in graph:
                    continue
                if state.get(dependency) == 1:
                    return dependency
                if state.get(dependency) != 2:
                    stack.append((dependency, False))
    return None


def _dependency_errors(tasks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids = {task.get("id") for task in tasks if isinstance(task.get("id"), str)}
    graph: dict[str, list[str]] = {}
    for task in tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str):
            continue
        dependencies = task.get("dependencies", [])
        if dependencies is None:
            dependencies = []
        if not isinstance(dependencies, list) or not all(isinstance(item, str) for item in dependencies):
            errors.append(f"task {task_id} dependencies must be a string list")
            continue
        graph[task_id] = dependencies
        for dependency in dependencies:
            if dependency not in ids:
                errors.append(f"task {task_id} references unknown dependency {dependency}")

    cycle = _dependency_cycle(graph)
    if cycle is not None:
        errors.append(f"task dependency cycle includes {cycle}")
    return errors


def validate_ledger(document: dict[str, Any], *, allow_placeholders: bool = False) -> list[str]:
    errors: list[str] = []
    ledger = document.get("ledger")
    if not isinstance(ledger, dict):
        return ["ledger must be a mapping"]
    version = ledger.get("schema_version")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version not in {1, 2}
    ):
        errors.append("ledger.schema_version must be integer 1 or 2")
    for key in ("objective_id", "objective"):
        value = ledger.get(key)
        if not isinstance(value, str) or (not allow_placeholders and (not value or value.startswith("<"))):
            errors.append(f"ledger.{key} must be a non-placeholder string")
    source = ledger.get("source_revision")
    if not isinstance(source, dict):
        errors.append("ledger.source_revision must be a mapping")
    else:
        for key in ("branch", "head_sha"):
            if not _nonempty(source.get(key), allow_placeholders=allow_placeholders):
                errors.append(f"ledger.source_revision.{key} is required")
        _timestamp(
            source.get("updated_at"),
            "ledger.source_revision.updated_at",
            errors,
            allow_placeholders=allow_placeholders,
        )

    tasks_raw = document.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        errors.append("tasks must be a non-empty list")
        return errors
    if len(tasks_raw) != len(_task_list(document)):
        errors.append("every task must be a mapping")
    tasks = _task_list(document)
    ids: list[str] = []
    allowed = V1_STATUSES if version == 1 else V2_STATUSES
    for index, task in enumerate(tasks):
        task_id = task.get("id")
        label = f"task[{index}]"
        if not isinstance(task_id, str) or not task_id or (not allow_placeholders and task_id.startswith("<")):
            errors.append(f"{label}.id must be a non-placeholder string")
            task_id = label
        else:
            ids.append(task_id)
        status = task.get("status")
        if isinstance(status, str) and status.startswith("<") and allow_placeholders:
            continue
        if status not in allowed:
            errors.append(f"task {task_id} has unsupported status {status!r}")
            continue
        evidence = task.get("evidence") or {}
        if not isinstance(evidence, dict):
            errors.append(f"task {task_id} evidence must be a mapping")
            evidence = {}
        verification = evidence.get("verification") or {}
        review = evidence.get("review") or {}
        acceptance = evidence.get("acceptance") or {}
        if not isinstance(verification, dict):
            errors.append(f"task {task_id} verification evidence must be a mapping")
            verification = {}
        if not isinstance(review, dict):
            errors.append(f"task {task_id} review evidence must be a mapping")
            review = {}
        if not isinstance(acceptance, dict):
            errors.append(f"task {task_id} acceptance evidence must be a mapping")
            acceptance = {}
        if status in {"done", "accepted"} and verification.get("status") != "passed":
            errors.append(f"task {task_id} {status} requires passed verification")
        if status in {"done", "accepted"} and review.get("status") not in {"not_required", "passed"}:
            errors.append(f"task {task_id} {status} requires satisfied review evidence")
        if version == 2 and status == "accepted":
            if acceptance.get("status") != "satisfied" or not _nonempty(
                acceptance.get("artifact"), allow_placeholders=allow_placeholders
            ):
                errors.append(f"task {task_id} accepted requires satisfied acceptance evidence")
        if version == 1 and status in {"claimed", "in_progress"}:
            claim = task.get("claim") or {}
            owner = task.get("owner") or {}
            if not isinstance(claim, dict) or not isinstance(owner, dict):
                errors.append(f"task {task_id} {status} owner and claim must be mappings")
            elif not owner.get("id") or not claim.get("lease_id") or not claim.get("lease_expires_at"):
                errors.append(f"task {task_id} {status} requires owner and lease fields")
        if status == "blocked":
            blocker = task.get("blocker") or {}
            if not isinstance(blocker, dict):
                errors.append(f"task {task_id} blocker must be a mapping")
            elif not blocker.get("reason") or str(blocker.get("reason")).startswith("<"):
                errors.append(f"task {task_id} blocked requires blocker reason")
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    errors.extend(f"duplicate task id {item}" for item in duplicates)
    if not allow_placeholders and version == 1:
        errors.extend(_dependency_errors(tasks))

    if version == 2:
        source_map = source if isinstance(source, dict) else {}
        current_loop = document.get("current_loop", {})
        if not isinstance(current_loop, dict):
            errors.append("current_loop must be a mapping")
            current_loop = {}
        elif (
            current_loop
            and not (
                allow_placeholders
                and _placeholder(current_loop.get("lifecycle"))
            )
            and current_loop.get("lifecycle") not in {"active", "complete"}
        ):
            errors.append("current_loop.lifecycle must be active or complete")
        if isinstance(source, dict):
            for key in ("spec_sha256", "task_manifest_sha256"):
                if not _nonempty(source.get(key), allow_placeholders=allow_placeholders):
                    errors.append(f"ledger.source_revision.{key} is required")
            previous_snapshot = source.get("previous_ledger_sha256")
            if previous_snapshot not in (None, "") and not _nonempty(
                previous_snapshot, allow_placeholders=allow_placeholders
            ):
                errors.append("ledger.source_revision.previous_ledger_sha256 must be a string")
            migration_snapshot = source.get("migration_source_sha256")
            if migration_snapshot not in (None, "") and not _nonempty(
                migration_snapshot, allow_placeholders=allow_placeholders
            ):
                errors.append("ledger.source_revision.migration_source_sha256 must be a string")
        revision = ledger.get("state_revision")
        if not isinstance(revision, dict):
            errors.append("ledger.state_revision must be a mapping")
            revision = {}
        sequence = revision.get("sequence")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
            errors.append("ledger.state_revision.sequence must be a non-negative integer")
        last_event_hash = revision.get("last_event_hash")
        if not isinstance(last_event_hash, str):
            errors.append("ledger.state_revision.last_event_hash must be a string")

        external_memory = document.get("external_memory")
        if external_memory is not None:
            if not isinstance(external_memory, dict):
                errors.append("external_memory must be a mapping")
            else:
                expected_fields = {
                    "contract_version", "mode", "backend_status", "adapter",
                    "receipt_digests", "authority", "used_as_authorization",
                    "used_as_completion_evidence", "notes",
                }
                missing = sorted(expected_fields - set(external_memory))
                unknown = sorted(set(external_memory) - expected_fields)
                if missing:
                    errors.append(f"external_memory missing fields: {', '.join(missing)}")
                if unknown:
                    errors.append(f"external_memory unknown fields: {', '.join(unknown)}")
                if external_memory.get("contract_version") != "loop-memory/v1":
                    errors.append("external_memory.contract_version must be loop-memory/v1")
                mode = external_memory.get("mode")
                if not isinstance(mode, str) or (
                    not (allow_placeholders and _placeholder(mode))
                    and mode not in {"disabled", "advisory-cache", "coordination"}
                ):
                    errors.append("external_memory.mode is unsupported")
                backend_status = external_memory.get("backend_status")
                if not isinstance(backend_status, str) or (
                    not (allow_placeholders and _placeholder(backend_status))
                    and backend_status not in {"disabled", "unavailable", "used", "degraded"}
                ):
                    errors.append("external_memory.backend_status is unsupported")
                adapter = external_memory.get("adapter")
                if adapter is not None and not (
                    isinstance(adapter, str)
                    and (
                        (allow_placeholders and _placeholder(adapter))
                        or bool(OPAQUE_ADAPTER_ID.fullmatch(adapter))
                    )
                ):
                    errors.append("external_memory.adapter must be null or an opaque adapter id")
                receipt_digests = external_memory.get("receipt_digests")
                if not isinstance(receipt_digests, list):
                    errors.append("external_memory.receipt_digests must be a list")
                    receipt_digests = []
                elif any(
                    not _sha256_or_placeholder(item, allow_placeholders=allow_placeholders)
                    for item in receipt_digests
                ):
                    errors.append("external_memory.receipt_digests must contain SHA-256 digests")
                elif len(receipt_digests) != len(set(receipt_digests)):
                    errors.append("external_memory.receipt_digests must be unique")
                if external_memory.get("authority") != "advisory-only":
                    errors.append("external_memory.authority must be advisory-only")
                for field in ("used_as_authorization", "used_as_completion_evidence"):
                    if external_memory.get(field) is not False:
                        errors.append(f"external_memory.{field} must be false")
                if not _nonempty(external_memory.get("notes"), allow_placeholders=allow_placeholders):
                    errors.append("external_memory.notes must be a non-empty string")
                if isinstance(backend_status, str) and backend_status in {"disabled", "unavailable"} and receipt_digests:
                    errors.append("disabled or unavailable external_memory cannot reference receipts")
                if isinstance(backend_status, str) and backend_status in {"used", "degraded"} and not receipt_digests:
                    errors.append("used or degraded external_memory requires a receipt digest")
                concrete_mode = mode if isinstance(mode, str) and mode in {"disabled", "advisory-cache", "coordination"} else None
                concrete_status = backend_status if isinstance(backend_status, str) and backend_status in {"disabled", "unavailable", "used", "degraded"} else None
                if concrete_mode == "disabled" and concrete_status != "disabled":
                    errors.append("disabled external_memory mode requires disabled backend_status")
                if concrete_status == "disabled" and concrete_mode != "disabled":
                    errors.append("disabled external_memory backend_status requires disabled mode")
                if concrete_status == "disabled" and adapter is not None:
                    errors.append("disabled external_memory cannot name an adapter")
                if concrete_status in {"unavailable", "used", "degraded"} and not (
                    isinstance(adapter, str) and bool(OPAQUE_ADAPTER_ID.fullmatch(adapter))
                ):
                    errors.append(f"{concrete_status} external_memory requires an adapter id")

        claims_raw = document.get("claims", [])
        if not isinstance(claims_raw, list):
            errors.append("claims must be a list")
            claims_raw = []
        active_claims: dict[str, dict[str, Any]] = {}
        seen_claim_keys: set[tuple[str, int]] = set()
        for index, claim in enumerate(claims_raw):
            label = f"claim[{index}]"
            if not isinstance(claim, dict):
                errors.append(f"{label} must be a mapping")
                continue
            task_id = claim.get("task_id")
            if allow_placeholders and _placeholder(task_id):
                continue
            if task_id not in ids:
                errors.append(f"{label} references unknown task {task_id!r}")
            status = claim.get("status")
            if status not in {"active", "released", "expired", "revoked"}:
                errors.append(f"{label} has unsupported status {status!r}")
            owner = claim.get("owner")
            if not isinstance(owner, dict) or not _nonempty(
                owner.get("id") if isinstance(owner, dict) else None,
                allow_placeholders=allow_placeholders,
            ):
                errors.append(f"{label} requires owner.id")
            elif owner.get("type") not in {
                "current_session",
                "subagent",
                "codex_thread",
                "maintainer",
            }:
                errors.append(f"{label} has unsupported owner.type {owner.get('type')!r}")
            token = claim.get("fencing_token")
            generation = token.get("generation") if isinstance(token, dict) else None
            nonce = token.get("nonce") if isinstance(token, dict) else None
            if not isinstance(generation, int) or isinstance(generation, bool) or generation < 1:
                errors.append(f"{label} fencing generation must be a positive integer")
            if not _nonempty(nonce, allow_placeholders=allow_placeholders):
                errors.append(f"{label} requires fencing nonce")
            expected_revision = claim.get("expected_state_revision")
            if (
                not isinstance(expected_revision, int)
                or isinstance(expected_revision, bool)
                or expected_revision < 0
            ):
                errors.append(f"{label} expected_state_revision must be a non-negative integer")
            elif isinstance(sequence, int) and expected_revision > sequence:
                errors.append(f"{label} expected_state_revision exceeds ledger revision")
            claim_source = claim.get("source_revision")
            if not isinstance(claim_source, dict):
                errors.append(f"{label} source_revision must be a mapping")
            else:
                for field in ("branch", "head_sha", "spec_sha256", "task_manifest_sha256"):
                    if claim_source.get(field) != source_map.get(field):
                        errors.append(f"{label} source_revision mismatch: {field}")
            _timestamp(
                claim.get("claimed_at"),
                f"{label}.claimed_at",
                errors,
                allow_placeholders=allow_placeholders,
            )
            claimed_at = _parsed_timestamp(claim.get("claimed_at"))
            lease_expires_at = _parsed_timestamp(claim.get("lease_expires_at"))
            if claimed_at is not None and lease_expires_at is not None and lease_expires_at <= claimed_at:
                errors.append(f"{label} lease_expires_at must be after claimed_at")
            ledger_updated_at = _parsed_timestamp(source_map.get("updated_at"))
            if status == "active" and lease_expires_at is not None and ledger_updated_at is not None and lease_expires_at <= ledger_updated_at:
                errors.append(f"{label} active lease is expired at ledger source revision")
            _timestamp(
                claim.get("lease_expires_at"),
                f"{label}.lease_expires_at",
                errors,
                allow_placeholders=allow_placeholders,
            )
            if isinstance(task_id, str) and isinstance(generation, int):
                key = (task_id, generation)
                if key in seen_claim_keys:
                    errors.append(f"duplicate fencing generation {generation} for task {task_id}")
                seen_claim_keys.add(key)
            if status == "active" and isinstance(task_id, str):
                if task_id in active_claims:
                    errors.append(f"task {task_id} has more than one active claim")
                active_claims[task_id] = claim

        for task in tasks:
            if task.get("status") == "in_progress" and task.get("id") not in active_claims:
                errors.append(f"task {task.get('id')} in_progress requires an active fenced claim")
            if task.get("status") in {"planned", "accepted", "cancelled"} and task.get("id") in active_claims:
                errors.append(
                    f"task {task.get('id')} status {task.get('status')} cannot retain an active claim"
                )

        events_raw = document.get("events", [])
        if not isinstance(events_raw, list):
            errors.append("events must be a list")
            events_raw = []
        concrete_events = [
            event
            for event in events_raw
            if isinstance(event, dict)
            and not (allow_placeholders and _placeholder(event.get("event_id")))
        ]
        previous_hash = ""
        event_ids: set[str] = set()
        idempotency_keys: set[str] = set()
        event_task_status: dict[str, str] = {}
        event_claim_status: dict[str, tuple[str, Any]] = {}
        event_gates: dict[str, dict[str, Any]] = {}
        objective_completed = False
        previous_event_time: dt.datetime | None = None
        final_event_time: dt.datetime | None = None
        for index, event in enumerate(events_raw):
            label = f"event[{index}]"
            if not isinstance(event, dict):
                errors.append(f"{label} must be a mapping")
                continue
            if allow_placeholders and _placeholder(event.get("event_id")):
                continue
            event_sequence = event.get("sequence")
            if not isinstance(event_sequence, int) or isinstance(event_sequence, bool):
                errors.append(f"{label} sequence must be an integer")
            elif event_sequence != index + 1:
                errors.append(f"{label} sequence must be {index + 1}")
            expected_event_revision = event.get("expected_state_revision")
            if (
                not isinstance(expected_event_revision, int)
                or isinstance(expected_event_revision, bool)
                or expected_event_revision < 0
            ):
                errors.append(f"{label} expected_state_revision must be a non-negative integer")
            elif isinstance(event_sequence, int) and expected_event_revision != event_sequence - 1:
                errors.append(f"{label} expected_state_revision must be sequence - 1")
            if event.get("previous_event_hash") != previous_hash:
                errors.append(f"{label} previous_event_hash mismatch")
            event_id = event.get("event_id")
            if not _nonempty(event_id, allow_placeholders=allow_placeholders):
                errors.append(f"{label} requires event_id")
            elif event_id in event_ids:
                errors.append(f"duplicate event_id {event_id}")
            else:
                event_ids.add(event_id)
            key = event.get("idempotency_key")
            if not _nonempty(key, allow_placeholders=allow_placeholders):
                errors.append(f"{label} requires idempotency_key")
            elif key in idempotency_keys:
                errors.append(f"duplicate idempotency_key {key}")
            else:
                idempotency_keys.add(key)
            if event.get("type") not in loop_core.EVENT_TYPES:
                errors.append(f"{label} has unsupported type {event.get('type')!r}")
            if not _nonempty(event.get("actor"), allow_placeholders=allow_placeholders):
                errors.append(f"{label} requires actor")
            _timestamp(
                event.get("occurred_at"),
                f"{label}.occurred_at",
                errors,
                allow_placeholders=allow_placeholders,
            )
            event_time = _parsed_timestamp(event.get("occurred_at"))
            if event_time is not None:
                if previous_event_time is not None and event_time < previous_event_time:
                    errors.append(f"{label} occurred_at must not move backwards")
                previous_event_time = event_time
                final_event_time = event_time
            if event.get("type") in {
                "task_transition",
                "claim_acquired",
                "claim_released",
                "claim_expired",
                "claim_revoked",
            } and event.get("task_id") not in ids:
                errors.append(f"{label} references unknown task {event.get('task_id')!r}")
            payload = event.get("payload")
            if not isinstance(payload, dict):
                errors.append(f"{label} payload must be a mapping")
                payload = {}
            event_type = event.get("type")
            event_task_id = event.get("task_id")
            if event_type == "migration_snapshot":
                if index != 0:
                    errors.append(f"{label} migration_snapshot must be the first event")
                if event_task_id not in {None, ""}:
                    errors.append(f"{label} migration_snapshot must not target one task")
                source_document = payload.get("source_ledger")
                source_hash = payload.get("source_ledger_sha256")
                if not isinstance(source_document, dict):
                    errors.append(f"{label} migration_snapshot requires embedded source_ledger")
                elif source_hash != loop_core.digest(source_document):
                    errors.append(f"{label} migration_snapshot source hash mismatch")
                if source_hash != source_map.get("migration_source_sha256"):
                    errors.append(f"{label} migration_snapshot provenance mismatch")
            elif event_type == "task_transition" and isinstance(event_task_id, str):
                target = payload.get("target_status")
                if target not in V2_STATUSES:
                    errors.append(f"{label} has unsupported target_status {target!r}")
                else:
                    event_task_status[event_task_id] = target
            elif event_type == "claim_acquired" and isinstance(event_task_id, str):
                event_claim = payload.get("claim")
                if not isinstance(event_claim, dict) or event_claim.get("task_id") != event_task_id:
                    errors.append(f"{label} claim payload must match task_id")
                else:
                    event_claim_status[event_task_id] = (
                        "active",
                        copy.deepcopy(event_claim.get("fencing_token")),
                    )
            elif event_type in {"claim_released", "claim_expired", "claim_revoked"} and isinstance(event_task_id, str):
                event_claim_status[event_task_id] = (
                    {
                        "claim_released": "released",
                        "claim_expired": "expired",
                        "claim_revoked": "revoked",
                    }[event_type],
                    copy.deepcopy(payload.get("fencing_token")),
                )
                if event_type in {"claim_expired", "claim_revoked"}:
                    event_task_status[event_task_id] = "blocked"
            elif event_type == "gate_updated":
                gate_name = payload.get("gate")
                if isinstance(gate_name, str) and gate_name:
                    event_gates[gate_name] = copy.deepcopy(payload)
            elif event_type == "objective_completed":
                objective_completed = True
            event_hash = event.get("event_hash")
            if not isinstance(event_hash, str) or not event_hash:
                errors.append(f"{label} requires event_hash")
            elif event_hash != loop_core.calculate_event_hash(event):
                errors.append(f"{label} event_hash mismatch")
            previous_hash = event_hash if isinstance(event_hash, str) else previous_hash
        if concrete_events:
            if sequence != len(concrete_events):
                errors.append("ledger.state_revision.sequence must equal event count")
            if last_event_hash != previous_hash:
                errors.append("ledger.state_revision.last_event_hash must match the final event")
            ledger_updated_at = _parsed_timestamp(source_map.get("updated_at"))
            if final_event_time is not None and ledger_updated_at != final_event_time:
                errors.append(
                    "ledger.source_revision.updated_at must match the final event occurred_at"
                )
        elif sequence == 0 and last_event_hash not in {"", None}:
            errors.append("empty event history requires an empty last_event_hash")

        task_status_by_id = {task.get("id"): task.get("status") for task in tasks}
        for task_id, event_status in event_task_status.items():
            if task_status_by_id.get(task_id) != event_status:
                errors.append(
                    f"task {task_id} materialized status does not match final transition event"
                )
        current_claims = {
            task_id: claim
            for task_id, claim in active_claims.items()
        }
        for claim in claims_raw:
            if isinstance(claim, dict) and isinstance(claim.get("task_id"), str):
                current = current_claims.get(claim["task_id"])
                current_generation = ((current or {}).get("fencing_token") or {}).get("generation", 0)
                generation = (claim.get("fencing_token") or {}).get("generation", 0)
                if current is None or generation >= current_generation:
                    current_claims[claim["task_id"]] = claim
        for task_id, (event_status, event_token) in event_claim_status.items():
            claim = current_claims.get(task_id)
            if claim is None or claim.get("status") != event_status:
                errors.append(f"task {task_id} materialized claim status does not match final claim event")
            elif claim.get("fencing_token") != event_token:
                errors.append(f"task {task_id} materialized fencing token does not match final claim event")
        materialized_gates = {
            gate.get("gate"): gate
            for gate in document.get("human_gates", [])
            if isinstance(gate, dict) and isinstance(gate.get("gate"), str)
        }
        for gate_name, gate in event_gates.items():
            if materialized_gates.get(gate_name) != gate:
                errors.append(f"human gate {gate_name} materialization does not match final gate event")
        if objective_completed and current_loop.get("lifecycle") != "complete":
            errors.append("objective_completed event requires complete current_loop lifecycle")

        gates_raw = document.get("human_gates", [])
        if not isinstance(gates_raw, list):
            errors.append("human_gates must be a list")
        else:
            gate_names: set[str] = set()
            for index, gate in enumerate(gates_raw):
                label = f"human_gate[{index}]"
                if not isinstance(gate, dict):
                    errors.append(f"{label} must be a mapping")
                    continue
                name = gate.get("gate")
                if allow_placeholders and _placeholder(name):
                    continue
                if not _nonempty(name, allow_placeholders=allow_placeholders):
                    errors.append(f"{label} requires gate")
                elif name in gate_names:
                    errors.append(f"duplicate human gate {name}")
                else:
                    gate_names.add(name)
                if gate.get("status") not in {
                    "not_required",
                    "pending",
                    "satisfied",
                    "blocked",
                }:
                    errors.append(f"{label} has unsupported status {gate.get('status')!r}")
    return errors


def manifest_definitions(
    document: dict[str, Any], *, expected_objective_id: str | None = None
) -> dict[str, dict[str, Any]]:
    project = document.get("project")
    if not isinstance(project, dict):
        raise LedgerValidationError("task manifest project must be a mapping")
    schema_version = project.get("schema_version")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != 2
    ):
        raise LedgerValidationError("task manifest project.schema_version must be integer 2")
    objective_id = project.get("objective_id")
    if not isinstance(objective_id, str) or not objective_id or objective_id.startswith("<"):
        raise LedgerValidationError("task manifest project.objective_id is required")
    if expected_objective_id is not None and objective_id != expected_objective_id:
        raise LedgerValidationError("task manifest objective_id does not match ledger")
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        raise LedgerValidationError("task manifest tasks must be a list")
    definitions: dict[str, dict[str, Any]] = {}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or not isinstance(task.get("id"), str):
            raise LedgerValidationError(f"task manifest task[{index}] requires id")
        if task.get("initial_status") not in {"planned", "ready", "cancelled"}:
            raise LedgerValidationError(
                f"task manifest task {task.get('id')} requires a supported initial_status"
            )
        dependencies = task.get("dependencies")
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) for item in dependencies
        ):
            raise LedgerValidationError(
                f"task manifest task {task.get('id')} dependencies must be a string list"
            )
        if task.get("initial_status") == "ready" and dependencies:
            raise LedgerValidationError(
                f"task manifest task {task.get('id')} cannot start ready with dependencies"
            )
        scope = task.get("scope") or {}
        review = task.get("review")
        human_gate = task.get("human_gate")
        if review is None:
            review_required = False
            review_mode = "none"
        elif not isinstance(review, dict) or not isinstance(review.get("required"), bool):
            raise LedgerValidationError(
                f"task manifest task {task.get('id')} review.required must be boolean"
            )
        else:
            review_required = review["required"]
            review_mode = review.get("mode", "none")
            if review_mode not in REVIEW_MODES:
                raise LedgerValidationError(
                    f"task manifest task {task.get('id')} review.mode is unsupported"
                )
            if review_required and review_mode == "none":
                raise LedgerValidationError(
                    f"task manifest task {task.get('id')} requires a concrete review.mode"
                )
        if human_gate is None:
            human_gate_required = False
            human_gate_name = None
        elif not isinstance(human_gate, dict) or not isinstance(
            human_gate.get("required"), bool
        ):
            raise LedgerValidationError(
                f"task manifest task {task.get('id')} human_gate.required must be boolean"
            )
        else:
            human_gate_required = human_gate["required"]
            human_gate_name = human_gate.get("gate")
            if human_gate_required and (
                not isinstance(human_gate_name, str)
                or not human_gate_name
                or human_gate_name.startswith("<")
            ):
                raise LedgerValidationError(
                    f"task manifest task {task.get('id')} requires a concrete human_gate.gate"
                )
        definitions[task["id"]] = {
            "initial_status": task.get("initial_status"),
            "dependencies": copy.deepcopy(dependencies),
            "scope": scope.get("in") if isinstance(scope, dict) else None,
            "dod": task.get("dod"),
            "verification": task.get("verification"),
            "review_required": review_required,
            "review_mode": review_mode,
            "human_gate_required": human_gate_required,
            "human_gate_name": human_gate_name,
        }
    if len(definitions) != len(tasks):
        raise LedgerValidationError("task manifest contains duplicate task ids")
    for task_id, definition in definitions.items():
        for dependency in definition["dependencies"]:
            if dependency not in definitions:
                raise LedgerValidationError(
                    f"task manifest task {task_id} references unknown dependency {dependency}"
                )
    cycle = _dependency_cycle(
        {
            task_id: list(definition["dependencies"])
            for task_id, definition in definitions.items()
        }
    )
    if cycle is not None:
        raise LedgerValidationError(f"task manifest dependency cycle includes {cycle}")
    return definitions


def state_from_ledger(
    document: dict[str, Any], definitions: dict[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Convert the public V2 ledger shape into the executable core state."""
    errors = validate_ledger(document)
    if errors:
        raise LedgerValidationError("ledger is invalid: " + "; ".join(errors))
    if document["ledger"].get("schema_version") != 2:
        raise LedgerValidationError("executable state conversion requires schema_version 2")
    task_definitions = definitions or {}
    claims: dict[str, dict[str, Any]] = {}
    for claim in document.get("claims", []):
        task_id = claim["task_id"]
        current = claims.get(task_id)
        generation = (claim.get("fencing_token") or {}).get("generation", 0)
        current_generation = ((current or {}).get("fencing_token") or {}).get("generation", 0)
        if current is None or generation >= current_generation:
            claims[task_id] = copy.deepcopy(claim)
    events = copy.deepcopy(document.get("events", []))
    return {
        "revision": document["ledger"]["state_revision"]["sequence"],
        "last_event_hash": document["ledger"]["state_revision"]["last_event_hash"],
        "objective_id": document["ledger"]["objective_id"],
        "tasks": {
            task["id"]: {
                "status": task["status"],
                "definition": copy.deepcopy(task_definitions.get(task["id"], {})),
                "evidence": copy.deepcopy(task.get("evidence", {})),
                "blocker": copy.deepcopy(task.get("blocker", {})),
            }
            for task in document["tasks"]
        },
        "claims": claims,
        "events": events,
        "idempotency": {
            event["idempotency_key"]: loop_core.digest(
                {key: value for key, value in event.items() if key != "event_hash"}
            )
            for event in events
        },
        "gates": {
            gate["gate"]: copy.deepcopy(gate) for gate in document.get("human_gates", [])
        },
        "objective_status": (document.get("current_loop") or {}).get(
            "lifecycle", "active"
        ),
        "source_revision": copy.deepcopy(document["ledger"]["source_revision"]),
    }


def replay_ledger(
    document: dict[str, Any], definitions: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Replay a V2 event history from manifest initial state."""
    initial_tasks: dict[str, dict[str, Any]] = {}
    for task in document.get("tasks", []):
        task_id = task["id"]
        definition = copy.deepcopy(definitions.get(task_id) or {})
        initial_status = definition.get("initial_status")
        if initial_status not in V2_STATUSES:
            raise LedgerValidationError(f"manifest task {task_id} requires canonical initial_status")
        initial_tasks[task_id] = {
            "status": initial_status,
            "definition": definition,
            "evidence": {},
            "blocker": {},
        }
    state: dict[str, Any] = {
        "revision": 0,
        "last_event_hash": "",
        "objective_id": document["ledger"]["objective_id"],
        "tasks": initial_tasks,
        "claims": {},
        "events": [],
        "idempotency": {},
        "gates": {},
        "objective_status": "active",
        "source_revision": copy.deepcopy(document["ledger"]["source_revision"]),
    }
    for event in document.get("events", []):
        try:
            state, _ = loop_core.replay_event(state, event)
        except loop_core.LoopContractError as exc:
            raise LedgerValidationError(
                f"event {event.get('event_id', '<unknown>')} replay failed: {exc}"
            ) from exc
    return state


def semantic_audit(
    document: dict[str, Any],
    definitions: dict[str, dict[str, Any]],
    *,
    require_protected_history_authority: bool = False,
    trusted_protected_history_sha256: str | None = None,
) -> list[str]:
    """Replay events and compare every authoritative materialized view."""
    errors = validate_ledger(document)
    if errors:
        return errors
    ledger_ids = {task.get("id") for task in document.get("tasks", [])}
    if ledger_ids != set(definitions):
        return ["task manifest ids do not match materialized ledger task ids"]
    history_digest = loop_core.protected_history_digest(document.get("events", []))
    if (
        require_protected_history_authority
        and history_digest is not None
        and trusted_protected_history_sha256 != history_digest
    ):
        return ["protected event history requires exact current-session re-attestation"]
    try:
        replayed = replay_ledger(document, definitions)
    except LedgerValidationError as exc:
        return [str(exc)]
    actual_tasks = {
        task["id"]: {
            "status": task.get("status"),
            "evidence": task.get("evidence") or {},
            "blocker": task.get("blocker") or {},
        }
        for task in document["tasks"]
    }
    replayed_tasks = {
        task_id: {
            "status": task.get("status"),
            "evidence": task.get("evidence") or {},
            "blocker": task.get("blocker") or {},
        }
        for task_id, task in replayed["tasks"].items()
    }
    if loop_core.canonical_json(actual_tasks) != loop_core.canonical_json(replayed_tasks):
        errors.append("materialized task status/evidence/blocker view does not match event replay")
    actual_claims = {
        claim["task_id"]: claim for claim in document.get("claims", [])
    }
    if loop_core.canonical_json(actual_claims) != loop_core.canonical_json(replayed.get("claims", {})):
        errors.append("materialized claim view does not match event replay")
    actual_gates = {
        gate["gate"]: gate for gate in document.get("human_gates", [])
    }
    if loop_core.canonical_json(actual_gates) != loop_core.canonical_json(replayed.get("gates", {})):
        errors.append("materialized human gate view does not match event replay")
    lifecycle = (document.get("current_loop") or {}).get("lifecycle", "active")
    if lifecycle != replayed.get("objective_status", "active"):
        errors.append("materialized objective lifecycle does not match event replay")
    return errors


def update_ledger_view(document: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Materialize executable state back into a V2 ledger document."""
    result = copy.deepcopy(document)
    result["ledger"]["state_revision"] = {
        "sequence": state["revision"],
        "last_event_hash": state["last_event_hash"],
    }
    by_id = state["tasks"]
    for task in result["tasks"]:
        materialized = by_id[task["id"]]
        task["status"] = materialized["status"]
        if "evidence" in materialized:
            task["evidence"] = copy.deepcopy(materialized["evidence"])
        if "blocker" in materialized:
            task["blocker"] = copy.deepcopy(materialized["blocker"])
    result["claims"] = [copy.deepcopy(claim) for claim in state.get("claims", {}).values()]
    result["events"] = copy.deepcopy(state.get("events", []))
    if result["events"]:
        result["ledger"]["source_revision"]["updated_at"] = result["events"][-1][
            "occurred_at"
        ]
    gates = state.get("gates", {})
    result["human_gates"] = [copy.deepcopy(gate) for gate in gates.values()]
    if state.get("objective_status") == "complete":
        result.setdefault("current_loop", {})["lifecycle"] = "complete"
        result["current_loop"]["next_decision"] = "complete"
    return result


def migrate_v1(
    document: dict[str, Any],
    *,
    target_source_revision: dict[str, Any] | None = None,
    loop_spec: str | None = None,
    task_manifest: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    errors = validate_ledger(document, allow_placeholders=False)
    if errors:
        raise LedgerValidationError("v1 ledger is invalid: " + "; ".join(errors))
    if document["ledger"].get("schema_version") != 1:
        raise LedgerValidationError("migrate-v1 requires schema_version 1")
    result = {key: value for key, value in document.items() if key not in {"tasks", "status_model"}}
    discarded_event_count = len(document.get("events", [])) if isinstance(document.get("events"), list) else 0
    result["ledger"] = dict(document["ledger"])
    result["ledger"]["schema_version"] = 2
    source = dict(result["ledger"].get("source_revision") or {})
    source.pop("ledger_sha256", None)
    if target_source_revision is not None:
        for field in ("branch", "head_sha", "spec_sha256", "task_manifest_sha256"):
            value = target_source_revision.get(field)
            if not isinstance(value, str) or not value:
                raise LedgerValidationError(f"migration target source requires {field}")
            source[field] = value
        if loop_spec is None or task_manifest is None:
            raise LedgerValidationError("bound migration requires loop spec and task manifest references")
        result["ledger"]["loop_spec"] = loop_spec
        result["ledger"]["task_manifest"] = task_manifest
    source_snapshot_sha256 = loop_core.digest(document)
    source["previous_ledger_sha256"] = source_snapshot_sha256
    source["migration_source_sha256"] = source_snapshot_sha256
    source.setdefault("spec_sha256", "unavailable-from-v1")
    source.setdefault("task_manifest_sha256", "unavailable-from-v1")
    result["ledger"]["source_revision"] = source
    result["ledger"]["state_revision"] = {"sequence": 0, "last_event_hash": ""}
    migrated_tasks: list[dict[str, Any]] = []
    accepted_downgrades = 0
    reviewing_downgrades = 0
    for task in _task_list(document):
        migrated = dict(task)
        old_status = task["status"]
        if old_status == "accepted":
            accepted_downgrades += 1
        if old_status == "reviewing":
            reviewing_downgrades += 1
        migrated.pop("claim", None)
        migrated.pop("owner", None)
        migrated_tasks.append(migrated)
    initial_tasks = {
        task["id"]: {
            "status": "planned",
            "definition": {},
            "evidence": {},
            "blocker": {},
        }
        for task in migrated_tasks
    }
    migration_event = {
        "sequence": 1,
        "event_id": f"v1-migration-{source_snapshot_sha256[:16]}",
        "occurred_at": source.get("updated_at"),
        "actor": "v1-migration",
        "type": "migration_snapshot",
        "task_id": "",
        "idempotency_key": f"v1-migration-{source_snapshot_sha256}",
        "expected_state_revision": 0,
        "previous_event_hash": "",
        "payload": {
            "source_ledger_sha256": source_snapshot_sha256,
            "source_ledger": copy.deepcopy(document),
        },
    }
    migration_event["event_hash"] = loop_core.calculate_event_hash(migration_event)
    migrated_state, _ = loop_core.apply_event(
        {
            "revision": 0,
            "last_event_hash": "",
            "objective_id": result["ledger"]["objective_id"],
            "tasks": initial_tasks,
            "claims": {},
            "events": [],
            "idempotency": {},
            "gates": {},
            "objective_status": "active",
            "source_revision": copy.deepcopy(source),
        },
        migration_event,
    )
    result["tasks"] = [
        {
            "id": task_id,
            "status": task["status"],
            "evidence": copy.deepcopy(task.get("evidence") or {}),
            "blocker": copy.deepcopy(task.get("blocker") or {}),
        }
        for task_id, task in migrated_state["tasks"].items()
    ]
    result["claims"] = [copy.deepcopy(claim) for claim in migrated_state["claims"].values()]
    result["events"] = [migration_event]
    result["ledger"]["state_revision"] = {
        "sequence": migrated_state["revision"],
        "last_event_hash": migrated_state["last_event_hash"],
    }
    result["human_gates"] = []
    result["current_loop"] = {
        "lifecycle": "active",
        "classification": "handoff-or-continuation",
        "execution_mode": "sequential-fallback",
        "selected_task_id": "",
        "next_decision": "continue",
        "decision_reason": "v1 migration preview requires maintainer inspection",
    }
    post_errors = validate_ledger(result, allow_placeholders=False)
    if post_errors:
        raise LedgerValidationError("migrated v2 ledger is invalid: " + "; ".join(post_errors))
    report = {
        "status": "preview",
        "source_schema": 1,
        "target_schema": 2,
        "writes_performed": False,
        "task_count": len(migrated_tasks),
        "claim_count": len(result["claims"]),
        "contract_bound": target_source_revision is not None,
        "warnings": [
            "v1 ledger_sha256 was self-referential and was not trusted",
            "the complete V1 source snapshot is embedded in the canonical migration anchor for replay and provenance",
            *(
                [f"{accepted_downgrades} accepted task(s) downgraded to done pending v2 acceptance evidence"]
                if accepted_downgrades
                else []
            ),
            *(
                [f"{reviewing_downgrades} reviewing task(s) converted to blocked until a new fenced claim is acquired"]
                if reviewing_downgrades
                else []
            ),
            *(
                [f"{discarded_event_count} non-canonical v1 event(s) retained only inside the embedded source snapshot"]
                if discarded_event_count
                else []
            ),
        ],
    }
    return result, report
