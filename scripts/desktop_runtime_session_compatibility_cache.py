#!/usr/bin/env python3
"""Desktop runtime wrapper V1 session-scoped compatibility cache helper.

This helper reads or writes caller-explicit compatibility cache files that
contain contract compatibility evidence for the current process/session only.
It never calls Desktop thread tools, never reads Desktop private runtime state,
and never treats cached compatibility as runtime-call authorization.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys
import tempfile
from typing import Any


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from desktop_runtime_session_compatibility_status import (
    SESSION_STATUS_HELPER_VERSION,
    _contract_hash,
    validate_session_compatibility_status,
)


CACHE_HELPER_VERSION = "0.1.0"
WRITE_REQUESTED_ACTION = "write-session-compatibility-cache"
READ_REQUESTED_ACTION = "read-session-compatibility-cache"
REQUESTED_ACTIONS = {WRITE_REQUESTED_ACTION, READ_REQUESTED_ACTION}
WRAPPER_ID_FIELDS = ("wrapper_version", "skill_package_version", "repo_commit")

CACHE_SCOPES = {"same-session"}
SAME_SESSION_LIFECYCLE_MARKERS = {
    "same-session-only",
    "current-session-only",
    "current-process-only",
}
CURRENT_SCOPED_MARKER_TYPES = {"current-process", "current-session"}

PRIVATE_RUNTIME_HINTS = {
    "desktop private runtime state": "Desktop private runtime state",
    "sqlite": "Desktop private runtime database",
    "database": "Desktop private runtime database",
    "logs": "Desktop runtime logs",
    "auth file": "Desktop runtime auth files",
    "auth files": "Desktop runtime auth files",
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

PRIVATE_RUNTIME_PATH_PARTS = {
    ".codex",
    ".codex-desktop",
    "codex desktop",
    "codex-desktop",
    "desktop-private",
    "private-runtime",
    "runtime-state",
    "app-state",
    "sessions",
    "logs",
    "auth",
    "auth-files",
    "databases",
    "sqlite",
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


def _wrapper_identifier(record: dict[str, Any]) -> tuple[str, Any] | None:
    for field in WRAPPER_ID_FIELDS:
        if not _is_missing(record.get(field)):
            return field, record[field]
    return None


def _evidence_hash(record: dict[str, Any]) -> str | None:
    if isinstance(record.get("schema_hash"), str) and record["schema_hash"].strip():
        return record["schema_hash"].strip()
    evidence = record.get("normalized_contract_evidence")
    if not _is_missing(evidence):
        return _contract_hash(evidence)
    return None


def _parse_timestamp(value: Any) -> _dt.datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        if len(text) == 10:
            parsed_date = _dt.date.fromisoformat(text)
            return _dt.datetime.combine(parsed_date, _dt.time(), tzinfo=_dt.timezone.utc)
        parsed = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed.astimezone(_dt.timezone.utc)


def _now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _same_session_scoped_identity(session_identity: dict[str, Any]) -> bool:
    return session_identity.get("marker_type") in CURRENT_SCOPED_MARKER_TYPES


def _path_rejection_reason(cache_file: Any) -> str | None:
    if not isinstance(cache_file, str) or not cache_file.strip():
        return "cache_file is required and must be a caller-supplied absolute path."
    if any(token in cache_file for token in ("~", "$", "\x00")):
        return "cache_file must not use shell expansion, environment variables, or NUL bytes."

    path = pathlib.Path(cache_file)
    if not path.is_absolute():
        return "cache_file must be an absolute caller-supplied path."

    lower = str(path).lower()
    if "/library/application support/" in lower:
        return "cache_file looks like a Desktop private runtime path."
    if pathlib.Path(cache_file).suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        return "cache_file must not point at a database-like runtime file."

    normalized_parts = {part.replace("_", "-").lower() for part in path.parts}
    if normalized_parts & PRIVATE_RUNTIME_PATH_PARTS:
        return "cache_file contains Desktop/private/runtime-looking path segment(s)."
    return None


def _base_response(
    request: dict[str, Any],
    status: str,
    requested_action: str | None = None,
    envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    requested_action = requested_action or request.get("requested_action")
    return {
        "status": status,
        "requested_action": requested_action,
        "target_action": _get(request, "expected.target_action")
        or (envelope or {}).get("target_action"),
        "cache_helper_version": CACHE_HELPER_VERSION,
        "status_helper_version": SESSION_STATUS_HELPER_VERSION,
        "runtime_call_performed": False,
        "cache_read_performed": False,
        "cache_write_performed": False,
        "private_runtime_state_read": False,
        "later_runtime_path_blocked": status != "ready",
        "readiness_meaning": (
            "ready means same-session cache evidence may be referenced by a "
            "later preflight for contract compatibility only; it does not "
            "authorize runtime calls, external writes, target validation, "
            "permission handling, or runtime response validation."
        ),
        "cache_evidence": _cache_summary(envelope),
        "result": {
            "stop_reason": None,
            "residual_risk": [],
        },
    }


def _cache_summary(envelope: dict[str, Any] | None) -> dict[str, Any]:
    envelope = envelope or {}
    wrapper_identifier = _wrapper_identifier(envelope)
    wrapper_field = None if wrapper_identifier is None else wrapper_identifier[0]
    wrapper_value = None if wrapper_identifier is None else wrapper_identifier[1]
    return {
        "wrapper_identifier_field": wrapper_field,
        "wrapper_identifier": wrapper_value,
        "cache_helper_version": envelope.get("cache_helper_version"),
        "status_helper_version": envelope.get("status_helper_version"),
        "target_action": envelope.get("target_action"),
        "tool_or_api": envelope.get("tool_or_api"),
        "runtime_reported_version": envelope.get("runtime_reported_version"),
        "capability_source": envelope.get("capability_source"),
        "schema_hash": _evidence_hash(envelope),
        "comparison_result": envelope.get("comparison_result"),
        "last_verified": envelope.get("last_verified"),
        "cache_scope": envelope.get("cache_scope"),
        "cache_lifecycle_marker": envelope.get("cache_lifecycle_marker"),
        "same_session_only": envelope.get("same_session_only"),
        "created_at": envelope.get("created_at"),
        "expires_at": envelope.get("expires_at"),
        "session_identity": envelope.get("session_identity"),
    }


def _stopped(
    request: dict[str, Any],
    failure_class: str,
    reason: str,
    envelope: dict[str, Any] | None = None,
    requested_action: str | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "stopped", requested_action, envelope)
    response["failure_class"] = failure_class
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = [
        "Stopped cache evidence must block later runtime-call paths."
    ]
    return response


def _fallback(
    request: dict[str, Any],
    reason: str,
    envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback", request.get("requested_action"), envelope)
    response["failure_class"] = "session_compatibility_fallback"
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = [
        "Fallback cache evidence must block later runtime-call paths."
    ]
    return response


def _ready(request: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    response = _base_response(request, "ready", request.get("requested_action"), envelope)
    response["failure_class"] = None
    response["later_runtime_path_blocked"] = False
    response["result"]["residual_risk"] = [
        "Cache evidence is same-session contract compatibility evidence only.",
        "Codex CLI/Desktop restart, session marker mismatch, or expired cache invalidates this evidence.",
        "Runtime-call authorization, external-write authorization, target validation, permission handling, and response validation remain separate.",
    ]
    return response


def _required_expected_paths() -> list[str]:
    return [
        "expected.cache_helper_version",
        "expected.status_helper_version",
        "expected.target_action",
        "expected.tool_or_api",
    ]


def _required_envelope_paths() -> list[str]:
    return [
        "cache_helper_version",
        "status_helper_version",
        "target_action",
        "tool_or_api",
        "runtime_reported_version",
        "capability_source",
        "comparison_result",
        "last_verified",
        "session_identity",
        "cache_scope",
        "cache_lifecycle_marker",
        "created_at",
        "compatibility_status",
    ]


def _validate_request_common(request: dict[str, Any], requested_action: str) -> dict[str, Any] | None:
    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.", requested_action=requested_action)
    if request.get("requested_action") != requested_action:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported requested_action: {request.get('requested_action')}",
            requested_action=requested_action,
        )

    path_reason = _path_rejection_reason(request.get("cache_file"))
    if path_reason is not None:
        return _stopped(request, "forbidden_cache_path", path_reason)

    forbidden_hits = _forbidden_source_hits(request)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
        )

    auth_hits = _authorization_field_hits(request)
    if auth_hits:
        return _stopped(
            request,
            "authorization_out_of_scope",
            "Compatibility cache evidence must not include authorization or validation substitute field(s): "
            + ", ".join(auth_hits),
        )

    missing = [path for path in _required_expected_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped(request, "validation_error", "Missing required field(s): " + ", ".join(missing))
    if _wrapper_identifier(request.get("expected", {})) is None:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "expected requires wrapper_version, skill_package_version, or repo_commit.",
        )
    if _get(request, "expected.cache_helper_version") != CACHE_HELPER_VERSION:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "expected.cache_helper_version must match this cache helper version.",
        )
    if _get(request, "expected.status_helper_version") != SESSION_STATUS_HELPER_VERSION:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "expected.status_helper_version must match the session status helper version.",
        )
    if _evidence_hash(request["expected"]) is None:
        return _stopped(
            request,
            "missing_contract_evidence",
            "expected requires schema_hash or normalized_contract_evidence.",
        )
    return None


def _validate_envelope(
    request: dict[str, Any],
    envelope: dict[str, Any],
    current_session_identity: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(envelope, dict):
        return _stopped(request, "validation_error", "cache_envelope must be a JSON object.")

    missing = [path for path in _required_envelope_paths() if _is_missing(_get(envelope, path))]
    if missing:
        return _stopped(
            request,
            "validation_error",
            "Missing cache envelope field(s): " + ", ".join(missing),
            envelope,
        )

    expected_wrapper = _wrapper_identifier(request["expected"])
    envelope_wrapper = _wrapper_identifier(envelope)
    status_record = envelope.get("compatibility_status")
    status_wrapper = _wrapper_identifier(status_record) if isinstance(status_record, dict) else None
    if envelope_wrapper is None or envelope_wrapper != expected_wrapper or status_wrapper != expected_wrapper:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "Cache envelope wrapper/package/repo identity does not match expected identity.",
            envelope,
        )
    if envelope.get("cache_helper_version") != CACHE_HELPER_VERSION:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "cache_envelope.cache_helper_version must match this cache helper version.",
            envelope,
        )
    if envelope.get("status_helper_version") != SESSION_STATUS_HELPER_VERSION:
        return _stopped(
            request,
            "wrapper_or_helper_version_mismatch",
            "cache_envelope.status_helper_version must match the session status helper version.",
            envelope,
        )
    for expected_field, envelope_field in (
        ("target_action", "target_action"),
        ("tool_or_api", "tool_or_api"),
    ):
        if _get(request, f"expected.{expected_field}") != envelope.get(envelope_field):
            return _stopped(
                request,
                f"{expected_field}_mismatch",
                f"cache_envelope.{envelope_field} does not match expected.{expected_field}.",
                envelope,
            )

    if _evidence_hash(request["expected"]) != _evidence_hash(envelope):
        return _stopped(
            request,
            "contract_evidence_mismatch",
            "Cache envelope schema hash or normalized contract evidence does not match expected evidence.",
            envelope,
        )

    if not isinstance(status_record, dict):
        return _stopped(request, "validation_error", "cache_envelope.compatibility_status must be a JSON object.", envelope)
    status_expected = {
        (_wrapper_identifier(request["expected"]) or ("repo_commit", None))[0]: (
            _wrapper_identifier(request["expected"]) or ("repo_commit", None)
        )[1],
        "helper_version": _get(request, "expected.status_helper_version"),
        "target_action": _get(request, "expected.target_action"),
        "tool_or_api": _get(request, "expected.tool_or_api"),
    }
    if not _is_missing(request["expected"].get("schema_hash")):
        status_expected["schema_hash"] = request["expected"]["schema_hash"]
    else:
        status_expected["normalized_contract_evidence"] = request["expected"]["normalized_contract_evidence"]

    validation = validate_session_compatibility_status(
        {
            "requested_action": "validate-session-compatibility-status",
            "expected": status_expected,
            "compatibility_status": status_record,
        }
    )
    validation_status = validation.get("status")
    validation_failure = validation.get("failure_class")
    if validation_status == "stopped" and validation_failure != "session_compatibility_stopped":
        return _stopped(
            request,
            validation_failure or "validation_error",
            _get(validation, "result.stop_reason")
            or "Compatibility status validation stopped.",
            envelope,
        )

    for field in (
        "target_action",
        "tool_or_api",
        "runtime_reported_version",
        "capability_source",
        "comparison_result",
        "last_verified",
        "session_identity",
    ):
        status_field = "helper_version" if field == "status_helper_version" else field
        if envelope.get(field) != status_record.get(status_field):
            return _stopped(
                request,
                "cache_envelope_mismatch",
                f"cache_envelope.{field} does not match compatibility_status.{status_field}.",
                envelope,
            )
    if _evidence_hash(envelope) != _evidence_hash(status_record):
        return _stopped(
            request,
            "contract_evidence_mismatch",
            "Cache envelope contract evidence does not match compatibility_status evidence.",
            envelope,
        )

    if envelope.get("cache_scope") not in CACHE_SCOPES:
        return _stopped(
            request,
            "cache_scope_mismatch",
            "cache_envelope.cache_scope must be same-session.",
            envelope,
        )
    if envelope.get("cache_lifecycle_marker") not in SAME_SESSION_LIFECYCLE_MARKERS:
        return _stopped(
            request,
            "cache_scope_mismatch",
            "cache_envelope.cache_lifecycle_marker must be a same-session-only marker.",
            envelope,
        )

    session_identity = envelope.get("session_identity")
    if not isinstance(session_identity, dict):
        return _stopped(request, "missing_session_marker", "cache_envelope.session_identity must be a JSON object.", envelope)
    if _same_session_scoped_identity(session_identity) and envelope.get("same_session_only") is not True:
        return _stopped(
            request,
            "cache_scope_mismatch",
            "Explicit current-process/current-session scoped markers are accepted only in same-session-only cache envelopes.",
            envelope,
        )
    if current_session_identity is not None and current_session_identity != session_identity:
        return _stopped(
            request,
            "session_marker_mismatch",
            "Current session marker does not match the cached session marker.",
            envelope,
        )

    created_at = _parse_timestamp(envelope.get("created_at"))
    if created_at is None:
        return _stopped(request, "stale_or_expired_cache", "cache_envelope.created_at must be an ISO date or timestamp.", envelope)
    if created_at > _now_utc() + _dt.timedelta(seconds=5):
        return _stopped(request, "stale_or_expired_cache", "cache_envelope.created_at is in the future.", envelope)

    expires_at = _parse_timestamp(envelope.get("expires_at"))
    if envelope.get("same_session_only") is not True and expires_at is None:
        return _stopped(
            request,
            "cache_scope_mismatch",
            "cache_envelope requires expires_at or same_session_only: true.",
            envelope,
        )
    if expires_at is not None and expires_at <= _now_utc():
        return _stopped(request, "stale_or_expired_cache", "cache_envelope.expires_at is stale or expired.", envelope)

    if validation_status == "fallback":
        return _fallback(request, "Cached session compatibility status is fallback.", envelope)
    if validation_status == "stopped":
        return _stopped(
            request,
            "session_compatibility_stopped",
            "Cached session compatibility status is stopped.",
            envelope,
        )
    return None


def write_session_compatibility_cache(request: dict[str, Any]) -> dict[str, Any]:
    """Validate and write an explicit same-session compatibility cache envelope."""

    common_error = _validate_request_common(request, WRITE_REQUESTED_ACTION)
    if common_error is not None:
        return common_error

    envelope = request.get("cache_envelope")
    envelope_error = _validate_envelope(request, envelope, request.get("current_session_identity"))
    if envelope_error is not None and envelope_error.get("status") == "stopped" and envelope_error.get("failure_class") != "session_compatibility_stopped":
        return envelope_error

    cache_file = pathlib.Path(request["cache_file"])
    if not cache_file.parent.exists():
        return _stopped(request, "validation_error", "cache_file parent directory must already exist.", envelope)

    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{cache_file.name}.",
            suffix=".tmp",
            dir=str(cache_file.parent),
            text=True,
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(envelope, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
        os.replace(tmp_name, cache_file)
    except OSError as exc:
        return _stopped(request, "cache_io_error", f"Could not write cache file: {exc}", envelope)

    if envelope_error is not None:
        envelope_error["cache_write_performed"] = True
        return envelope_error

    response = _ready(request, envelope)
    response["cache_write_performed"] = True
    return response


def read_session_compatibility_cache(request: dict[str, Any]) -> dict[str, Any]:
    """Read and validate an explicit same-session compatibility cache envelope."""

    common_error = _validate_request_common(request, READ_REQUESTED_ACTION)
    if common_error is not None:
        return common_error
    current_session_identity = request.get("current_session_identity")
    if not isinstance(current_session_identity, dict) or _is_missing(current_session_identity):
        return _stopped(request, "missing_session_marker", "current_session_identity is required when reading cache evidence.")

    cache_file = pathlib.Path(request["cache_file"])
    try:
        with cache_file.open("r", encoding="utf-8") as handle:
            envelope = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        return _stopped(request, "cache_io_error", f"Could not read cache file: {exc}")

    envelope_error = _validate_envelope(request, envelope, current_session_identity)
    if envelope_error is not None:
        envelope_error["cache_read_performed"] = True
        return envelope_error

    response = _ready(request, envelope)
    response["cache_read_performed"] = True
    return response


def process_session_compatibility_cache_request(request: dict[str, Any]) -> dict[str, Any]:
    """Process a read or write request without reading Desktop runtime state."""

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")
    requested_action = request.get("requested_action")
    if requested_action == WRITE_REQUESTED_ACTION:
        return write_session_compatibility_cache(request)
    if requested_action == READ_REQUESTED_ACTION:
        return read_session_compatibility_cache(request)
    return _stopped(
        request,
        "validation_error",
        f"Unsupported requested_action: {requested_action}",
        requested_action=requested_action if isinstance(requested_action, str) else None,
    )


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    now = _now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
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
    compatibility_status = {
        "repo_commit": "ba6b974fbfa94e08d55e94a7a6a948b47dec200d",
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
    }
    envelope = {
        "repo_commit": compatibility_status["repo_commit"],
        "cache_helper_version": CACHE_HELPER_VERSION,
        "status_helper_version": SESSION_STATUS_HELPER_VERSION,
        "target_action": "read-thread",
        "tool_or_api": "read_thread",
        "runtime_reported_version": "version unavailable",
        "capability_source": "runtime-reported schema",
        "schema_hash": contract_hash,
        "comparison_result": "compatible",
        "last_verified": today,
        "session_identity": compatibility_status["session_identity"],
        "cache_scope": "same-session",
        "cache_lifecycle_marker": "same-session-only",
        "same_session_only": True,
        "created_at": now,
        "compatibility_status": compatibility_status,
    }
    return {
        "requested_action": WRITE_REQUESTED_ACTION,
        "cache_file": "/tmp/codex-session-compatibility-cache.json",
        "expected": {
            "repo_commit": compatibility_status["repo_commit"],
            "cache_helper_version": CACHE_HELPER_VERSION,
            "status_helper_version": SESSION_STATUS_HELPER_VERSION,
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
            "schema_hash": contract_hash,
        },
        "current_session_identity": compatibility_status["session_identity"],
        "cache_envelope": envelope,
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
    parser.add_argument("--example", action="store_true", help="Print an example write request and exit.")
    args = parser.parse_args(argv)

    indent = 2 if args.pretty or args.example else None
    if args.example:
        print(json.dumps(example_request(), indent=indent, sort_keys=True))
        return 0

    try:
        request = _load_request(args.request)
        response = process_session_compatibility_cache_request(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
