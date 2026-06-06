#!/usr/bin/env python3
"""Desktop runtime wrapper V1 session compatibility status validator.

This helper is intentionally non-state-changing. It validates an explicit
caller-supplied session compatibility status so a later preflight can decide
whether the status is usable evidence. It never calls Desktop thread tools,
never writes a compatibility cache, and never reads Desktop private runtime
state.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from typing import Any


SESSION_STATUS_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "validate-session-compatibility-status"

CAPABILITY_SOURCES = {
    "active tool list",
    "connector metadata",
    "documented API",
    "installed plugin metadata",
    "official documentation",
    "runtime-reported schema",
}

COMPARISON_RESULTS = {"compatible", "fallback", "stopped"}
READY_RESULTS = {"compatible"}
WRAPPER_ID_FIELDS = ("wrapper_version", "skill_package_version", "repo_commit")

SESSION_MARKER_TYPES = {
    "runtime-lifecycle",
    "session-id",
    "current-process",
    "current-session",
}

CURRENT_SCOPED_MARKERS = {
    "current process/session scoped",
    "current-process scoped",
    "current-session scoped",
}

PRIVATE_RUNTIME_HINTS = {
    "desktop private runtime state": "Desktop private runtime state",
    "sqlite": "Desktop private runtime database",
    "database": "Desktop private runtime database",
    "logs": "Desktop runtime logs",
    "sessions": "Desktop runtime sessions",
    "auth file": "Desktop runtime auth files",
    "auth files": "Desktop runtime auth files",
    "caches": "Desktop runtime caches",
    "app state": "Desktop app state",
    "local runtime directory": "Desktop local runtime directories",
    "local runtime directories": "Desktop local runtime directories",
    "private runtime file": "Desktop private runtime files",
    "private runtime files": "Desktop private runtime files",
    "unpublished endpoint": "unpublished Desktop endpoint",
    "ui scraping": "Desktop UI scraping",
    "reverse-engineered": "reverse-engineered Desktop internals",
    "daemon": "daemon or background service",
    "sidecar": "sidecar service",
    "background service": "background service",
    "app-server client": "app-server client",
}

AUTHORIZATION_FIELDS = {
    "action_authorized",
    "thread_action_authorized",
    "external_write_authorized",
    "destructive_action_authorized",
    "runtime_call_authorized",
    "target_validated",
    "permission_validated",
    "response_validated",
}


def _get(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    if isinstance(value, dict):
        return not value
    return False


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_iter_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_iter_strings(item))
        return strings
    return []


def _forbidden_source_hits(value: Any) -> list[str]:
    hits: set[str] = set()
    for text in _iter_strings(value):
        lower = text.lower()
        for hint, description in PRIVATE_RUNTIME_HINTS.items():
            if hint in lower:
                hits.add(description)
    return sorted(hits)


def _authorization_field_hits(value: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key) in AUTHORIZATION_FIELDS:
                hits.append(path)
            hits.extend(_authorization_field_hits(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_authorization_field_hits(item, f"{prefix}[{index}]"))
    return hits


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def _contract_hash(value: Any) -> str:
    normalized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _evidence_hash(record: dict[str, Any]) -> str | None:
    if isinstance(record.get("schema_hash"), str) and record["schema_hash"].strip():
        return record["schema_hash"].strip()
    evidence = record.get("normalized_contract_evidence")
    if not _is_missing(evidence):
        return _contract_hash(evidence)
    return None


def _wrapper_identifier(record: dict[str, Any]) -> tuple[str, Any] | None:
    for field in WRAPPER_ID_FIELDS:
        if not _is_missing(record.get(field)):
            return field, record[field]
    return None


def _session_summary(status_record: dict[str, Any] | None) -> dict[str, Any]:
    status_record = status_record or {}
    session_identity = status_record.get("session_identity")
    if not isinstance(session_identity, dict):
        session_identity = {}
    return {
        "marker_type": session_identity.get("marker_type"),
        "marker": session_identity.get("marker"),
    }


def _status_summary(status_record: dict[str, Any] | None) -> dict[str, Any]:
    status_record = status_record or {}
    wrapper_identifier = _wrapper_identifier(status_record)
    wrapper_field = None if wrapper_identifier is None else wrapper_identifier[0]
    wrapper_value = None if wrapper_identifier is None else wrapper_identifier[1]
    return {
        "wrapper_identifier_field": wrapper_field,
        "wrapper_identifier": wrapper_value,
        "helper_version": status_record.get("helper_version"),
        "target_action": status_record.get("target_action"),
        "tool_or_api": status_record.get("tool_or_api"),
        "runtime_reported_version": status_record.get("runtime_reported_version"),
        "capability_source": status_record.get("capability_source"),
        "schema_hash": _evidence_hash(status_record),
        "comparison_result": status_record.get("comparison_result"),
        "last_verified": status_record.get("last_verified"),
        "session_identity": _session_summary(status_record),
    }


def _base_response(
    request: dict[str, Any],
    status: str,
    status_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": _get(request, "expected.target_action"),
        "session_status_helper_version": SESSION_STATUS_HELPER_VERSION,
        "runtime_call_performed": False,
        "cache_write_performed": False,
        "private_runtime_state_read": False,
        "readiness_meaning": (
            "ready means the caller-supplied session compatibility status is "
            "valid evidence for a later preflight reference only; it does not "
            "authorize a runtime call, external write, target, permission, or "
            "response."
        ),
        "later_runtime_path_blocked": status != "ready",
        "validated_status": _status_summary(status_record),
        "result": {
            "stop_reason": None,
            "residual_risk": [],
        },
    }


def _stopped(
    request: dict[str, Any],
    failure_class: str,
    reason: str,
    status_record: dict[str, Any] | None = None,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "stopped", status_record)
    response["failure_class"] = failure_class
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or []
    return response


def _fallback(
    request: dict[str, Any],
    reason: str,
    status_record: dict[str, Any] | None = None,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback", status_record)
    response["failure_class"] = "session_compatibility_fallback"
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or [
        "A fallback session compatibility status must block later runtime-call paths."
    ]
    return response


def _required_paths() -> list[str]:
    return [
        "expected.target_action",
        "expected.tool_or_api",
        "expected.helper_version",
        "compatibility_status.helper_version",
        "compatibility_status.target_action",
        "compatibility_status.tool_or_api",
        "compatibility_status.runtime_reported_version",
        "compatibility_status.capability_source",
        "compatibility_status.comparison_result",
        "compatibility_status.last_verified",
    ]


def _validate_session_identity(
    request: dict[str, Any],
    status_record: dict[str, Any],
) -> dict[str, Any] | None:
    session_identity = status_record.get("session_identity")
    if not isinstance(session_identity, dict):
        return _stopped(
            request,
            "missing_session_marker",
            "compatibility_status.session_identity must be a JSON object.",
            status_record,
        )

    marker_type = session_identity.get("marker_type")
    marker = session_identity.get("marker")
    if marker_type not in SESSION_MARKER_TYPES:
        return _stopped(
            request,
            "missing_session_marker",
            "session_identity.marker_type must identify runtime lifecycle, session id, current process, or current session scope.",
            status_record,
        )
    if _is_missing(marker):
        return _stopped(
            request,
            "missing_session_marker",
            "session_identity.marker is required.",
            status_record,
        )
    if marker_type in {"current-process", "current-session"} and str(marker).strip().lower() not in CURRENT_SCOPED_MARKERS:
        return _stopped(
            request,
            "missing_session_marker",
            "current-process/current-session status requires an explicit current-session scoped marker.",
            status_record,
        )
    return None


def _validate_expected_identity(
    request: dict[str, Any],
    status_record: dict[str, Any],
) -> dict[str, Any] | None:
    expected = request.get("expected")
    if not isinstance(expected, dict):
        return _stopped(request, "validation_error", "expected must be a JSON object.", status_record)

    expected_wrapper = _wrapper_identifier(expected)
    status_wrapper = _wrapper_identifier(status_record)
    if expected_wrapper is None:
        return _stopped(
            request,
            "validation_error",
            "expected requires wrapper_version, skill_package_version, or repo_commit.",
            status_record,
        )
    if status_wrapper is None:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "compatibility_status requires wrapper_version, skill_package_version, or repo_commit.",
            status_record,
        )
    if expected_wrapper != status_wrapper:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "compatibility_status wrapper/package/repo identity does not match expected identity.",
            status_record,
        )

    if expected.get("helper_version") != SESSION_STATUS_HELPER_VERSION:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "expected.helper_version must match this session compatibility status helper version.",
            status_record,
        )

    for path, failure_class in (
        ("helper_version", "wrapper_or_helper_version_mismatch"),
        ("target_action", "target_action_mismatch"),
        ("tool_or_api", "tool_or_api_mismatch"),
    ):
        if expected.get(path) != status_record.get(path):
            return _stopped(
                request,
                failure_class,
                f"compatibility_status.{path} does not match expected.{path}.",
                status_record,
            )

    expected_hash = _evidence_hash(expected)
    status_hash = _evidence_hash(status_record)
    if expected_hash is None:
        return _stopped(
            request,
            "missing_contract_evidence",
            "expected requires schema_hash or normalized_contract_evidence.",
            status_record,
        )
    if status_hash is None:
        return _stopped(
            request,
            "missing_contract_evidence",
            "compatibility_status requires schema_hash or normalized_contract_evidence.",
            status_record,
        )
    if expected_hash != status_hash:
        return _stopped(
            request,
            "contract_evidence_mismatch",
            "compatibility_status schema hash or normalized contract evidence does not match expected evidence.",
            status_record,
        )
    return None


def validate_session_compatibility_status(request: dict[str, Any]) -> dict[str, Any]:
    """Validate explicit session compatibility status without calling runtime tools."""

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")

    forbidden_hits = _forbidden_source_hits(request)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
        )

    if request.get("requested_action") != REQUESTED_ACTION:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported requested_action: {request.get('requested_action')}",
        )

    status_record = request.get("compatibility_status")
    if not isinstance(status_record, dict):
        return _stopped(
            request,
            "validation_error",
            "compatibility_status must be a JSON object.",
        )

    missing = [path for path in _required_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped(
            request,
            "validation_error",
            "Missing required field(s): " + ", ".join(missing),
            status_record,
        )

    auth_hits = _authorization_field_hits(status_record)
    if auth_hits:
        return _stopped(
            request,
            "authorization_out_of_scope",
            "Session compatibility status must not include authorization or validation substitute field(s): "
            + ", ".join(auth_hits),
            status_record,
        )

    if status_record.get("capability_source") not in CAPABILITY_SOURCES:
        return _stopped(
            request,
            "missing_contract_evidence",
            "compatibility_status.capability_source is not a recognized documented source.",
            status_record,
        )

    if status_record.get("comparison_result") not in COMPARISON_RESULTS:
        return _stopped(
            request,
            "missing_contract_evidence",
            "compatibility_status.comparison_result must be compatible, fallback, or stopped.",
            status_record,
        )

    if not _valid_iso_date(status_record.get("last_verified")):
        return _stopped(
            request,
            "missing_contract_evidence",
            "compatibility_status.last_verified must be YYYY-MM-DD.",
            status_record,
        )

    identity_validation = _validate_expected_identity(request, status_record)
    if identity_validation is not None:
        return identity_validation

    session_validation = _validate_session_identity(request, status_record)
    if session_validation is not None:
        return session_validation

    comparison_result = status_record.get("comparison_result")
    if comparison_result == "fallback":
        return _fallback(
            request,
            "Caller-supplied session compatibility status is fallback.",
            status_record,
        )
    if comparison_result == "stopped":
        return _stopped(
            request,
            "session_compatibility_stopped",
            "Caller-supplied session compatibility status is stopped.",
            status_record,
            ["Stopped session compatibility status must block later runtime-call paths."],
        )
    if comparison_result not in READY_RESULTS:
        return _stopped(
            request,
            "session_compatibility_stopped",
            "Caller-supplied session compatibility status is not ready for preflight reference.",
            status_record,
        )

    response = _base_response(request, "ready", status_record)
    response["failure_class"] = None
    response["result"]["residual_risk"] = [
        "Validation used caller-supplied session compatibility status only.",
        "This helper did not call Desktop thread tools or read Desktop private runtime state.",
        "This helper did not write or update a compatibility cache.",
        "Runtime-call authorization, external-write authorization, target validation, permission handling, and response validation remain separate.",
    ]
    return response


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    contract = {
        "action": "read-thread",
        "tool_or_api": "read_thread",
        "classification": "read-only",
        "required_request_fields": ["thread_id"],
        "minimum_response_fields": ["status", "thread_id"],
        "capability_source": "runtime-reported schema",
        "contract_version": "version unavailable",
        "last_verified": today,
    }
    contract_hash = _contract_hash(contract)
    return {
        "requested_action": REQUESTED_ACTION,
        "expected": {
            "repo_commit": "9211a0f5eb44dfd17502ecc60bab430b397dfdfd",
            "helper_version": SESSION_STATUS_HELPER_VERSION,
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
            "schema_hash": contract_hash,
        },
        "compatibility_status": {
            "repo_commit": "9211a0f5eb44dfd17502ecc60bab430b397dfdfd",
            "helper_version": SESSION_STATUS_HELPER_VERSION,
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
            "runtime_reported_version": "version unavailable",
            "capability_source": "runtime-reported schema",
            "schema_hash": contract_hash,
            "comparison_result": "compatible",
            "last_verified": today,
            "session_identity": {
                "marker_type": "current-session",
                "marker": "current-session scoped",
            },
        },
    }


def _load_request(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="Path to a JSON request. Reads stdin when omitted.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument("--example", action="store_true", help="Print an example request and exit.")
    args = parser.parse_args(argv)

    indent = 2 if args.pretty or args.example else None
    if args.example:
        print(json.dumps(example_request(), indent=indent, sort_keys=True))
        return 0

    try:
        request = _load_request(args.request)
        response = validate_session_compatibility_status(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
