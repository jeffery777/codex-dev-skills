#!/usr/bin/env python3
"""Create-thread runtime-call authorization/evidence boundary helper.

This helper validates a caller-supplied authorization and evidence envelope for
one future ``create_thread`` implementation slice. It never calls Desktop thread
tools, never reads Desktop private runtime state, and never treats cache or
preflight evidence as authorization, target validation, permission handling, or
runtime response validation.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
from typing import Any


AUTHORIZATION_GATE_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "authorize-create-thread-runtime-call-envelope"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"
EXPECTED_PREFLIGHT_ACTION = "preflight-create-thread-runtime-call"

HUMAN_APPROVAL_MARKER = "human-approval-required-before-runtime-call-implementation"
HUMAN_APPROVAL_SCOPE = "next-step-implementation-only"

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
    "mcp server": "MCP server",
    "sidecar": "sidecar service",
    "background service": "background service",
    "app-server client": "app-server client",
}

PRIVATE_RUNTIME_PATH_PARTS = {
    ".codex",
    ".codex-desktop",
    "codex-desktop",
    "codex desktop",
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


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


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


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        strings.append(item.strip())
    return strings


def _forbidden_source_hits(value: Any) -> list[str]:
    hits: set[str] = set()
    for text in _iter_strings(value):
        lower = text.lower()
        for hint, description in PRIVATE_RUNTIME_HINTS.items():
            if hint in lower:
                hits.add(description)
    return sorted(hits)


def _request_path_rejection_reason(path_value: str | None) -> str | None:
    if path_value is None:
        return None
    if any(token in path_value for token in ("~", "$", "\x00")):
        return "request path must not use shell expansion, environment variables, or NUL bytes."
    path = pathlib.Path(path_value)
    lower = str(path).lower()
    if "/library/application support/" in lower:
        return "request path looks like a Desktop private runtime path."
    if path.suffix.lower() in {".sqlite", ".sqlite3", ".db"}:
        return "request path must not point at a database-like runtime file."
    normalized_parts = {part.replace("_", "-").lower() for part in path.parts}
    if normalized_parts & PRIVATE_RUNTIME_PATH_PARTS:
        return "request path contains Desktop/private/runtime-looking path segment(s)."
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


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "authorization_gate_helper_version": AUTHORIZATION_GATE_HELPER_VERSION,
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": status != "ready",
        "readiness_meaning": (
            "ready means the caller-supplied authorization/evidence envelope "
            "is sufficient for a human to consider approving a separate single "
            "create_thread runtime-call implementation; it does not authorize "
            "or perform a runtime call."
        ),
        "target_evidence": {
            "repo": _get(request, "target.repo"),
            "remote": _get(request, "target.remote"),
            "branch": _get(request, "target.branch"),
            "expected_head": _get(request, "target.expected_head"),
        },
        "authorization_evidence": {
            "authorized_runtime_action": _get(request, "authorization.authorized_runtime_action"),
            "human_approval_marker": _get(request, "authorization.human_approval_marker"),
            "human_approval_scope": _get(request, "authorization.human_approval_scope"),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "destructive_action_approved": _get(request, "authorization.destructive_action_approved"),
        },
        "boundary_evidence": {
            "external_writes_blocked": _get(request, "boundaries.external_writes_blocked"),
            "runtime_call_performed": _get(request, "boundaries.runtime_call_performed"),
            "desktop_private_runtime_state_read": _get(
                request, "boundaries.desktop_private_runtime_state_read"
            ),
        },
        "validation_placeholders": {
            "target_validation_confirmed": _get(request, "target_validation.caller_confirmed"),
            "permission_failure_handling_declared": _get(
                request, "permission_failure_handling.requirements_declared"
            ),
            "runtime_response_validation_declared": _get(
                request, "runtime_response_validation.requirements_declared"
            ),
        },
        "result": {
            "stop_reason": None,
            "residual_risk": [],
        },
    }


def _stopped(
    request: dict[str, Any],
    failure_class: str,
    reason: str,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "stopped")
    response["failure_class"] = failure_class
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or [
        "Stopped authorization/evidence envelopes must block later runtime-call paths."
    ]
    return response


def _fallback(
    request: dict[str, Any],
    reason: str,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback")
    response["failure_class"] = "human_approval_boundary_missing"
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or [
        "Fallback authorization/evidence envelopes must block later runtime-call paths."
    ]
    return response


def _required_paths() -> list[str]:
    return [
        "requested_action",
        "target_action",
        "tool_or_api",
        "target.repo",
        "target.remote",
        "target.branch",
        "target.expected_head",
        "prompt.summary",
        "prompt.body",
        "boundaries.external_writes_blocked",
        "boundaries.runtime_call_performed",
        "boundaries.desktop_private_runtime_state_read",
        "authorization.authorized_runtime_action",
        "authorization.external_write_authorized",
        "target_validation.caller_confirmed",
        "target_validation.repo",
        "target_validation.remote",
        "target_validation.branch",
        "target_validation.expected_head",
        "permission_failure_handling.requirements_declared",
        "permission_failure_handling.satisfied_by_preflight_or_cache",
        "permission_failure_handling.requirements",
        "runtime_response_validation.requirements_declared",
        "runtime_response_validation.satisfied_by_preflight_or_cache",
        "runtime_response_validation.minimum_response_fields",
        "preflight_evidence",
        "session_status_evidence",
        "session_cache_evidence",
        "current_session_identity",
    ]


def _validate_exact_action(request: dict[str, Any]) -> dict[str, Any] | None:
    if request.get("requested_action") != REQUESTED_ACTION:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported requested_action: {request.get('requested_action')}",
        )
    if request.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "target_action_mismatch",
            "target_action must be create-thread.",
        )
    if request.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "tool_or_api must be create_thread.",
        )
    if _get(request, "authorization.authorized_runtime_action") != TARGET_ACTION:
        return _stopped(
            request,
            "runtime_action_authorization_unclear",
            "authorization.authorized_runtime_action must be exactly create-thread.",
        )
    return None


def _validate_safety_boundaries(request: dict[str, Any]) -> dict[str, Any] | None:
    if _as_bool(_get(request, "boundaries.external_writes_blocked")) is not True:
        return _stopped(
            request,
            "external_write_request",
            "boundaries.external_writes_blocked must remain true.",
        )
    if _as_bool(_get(request, "authorization.external_write_authorized")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "authorization.external_write_authorized must remain false.",
        )
    if _as_bool(_get(request, "boundaries.runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "boundaries.runtime_call_performed must be false.",
        )
    if _as_bool(_get(request, "boundaries.desktop_private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "boundaries.desktop_private_runtime_state_read must be false.",
        )

    destructive = _get(request, "authorization.destructive_action_approved")
    if destructive is True:
        return _stopped(
            request,
            "destructive_action_approval_present",
            "destructive action approval must be absent or false for this gate.",
        )
    if destructive not in (None, False):
        return _stopped(
            request,
            "destructive_action_approval_present",
            "authorization.destructive_action_approved must be absent or boolean false.",
        )
    return None


def _validate_human_marker(request: dict[str, Any]) -> dict[str, Any] | None:
    marker = _get(request, "authorization.human_approval_marker")
    scope = _get(request, "authorization.human_approval_scope")
    if _is_missing(marker) or _is_missing(scope):
        return _fallback(
            request,
            "Missing human approval marker for the next implementation boundary.",
        )
    if marker != HUMAN_APPROVAL_MARKER or scope != HUMAN_APPROVAL_SCOPE:
        return _stopped(
            request,
            "human_approval_boundary_unclear",
            "Human approval marker must describe next-step implementation approval only.",
        )
    return None


def _validate_target_validation(request: dict[str, Any]) -> dict[str, Any] | None:
    if _as_bool(_get(request, "target_validation.caller_confirmed")) is not True:
        return _stopped(
            request,
            "target_validation_missing",
            "target_validation.caller_confirmed must be true and separate from cache/preflight evidence.",
        )
    for field in ("repo", "remote", "branch", "expected_head"):
        if _get(request, f"target.{field}") != _get(request, f"target_validation.{field}"):
            return _stopped(
                request,
                "target_validation_mismatch",
                f"target_validation.{field} must match target.{field}.",
            )
    return None


def _validate_permission_and_response_placeholders(request: dict[str, Any]) -> dict[str, Any] | None:
    if _as_bool(_get(request, "permission_failure_handling.requirements_declared")) is not True:
        return _stopped(
            request,
            "permission_handling_missing",
            "permission/auth failure handling requirements must be declared.",
        )
    if _as_bool(_get(request, "permission_failure_handling.satisfied_by_preflight_or_cache")) is not False:
        return _stopped(
            request,
            "permission_handling_substituted",
            "Preflight/cache evidence cannot satisfy permission/auth failure handling.",
        )
    if _string_list(_get(request, "permission_failure_handling.requirements")) is None:
        return _stopped(
            request,
            "permission_handling_missing",
            "permission_failure_handling.requirements must be a non-empty string list.",
        )

    if _as_bool(_get(request, "runtime_response_validation.requirements_declared")) is not True:
        return _stopped(
            request,
            "response_validation_missing",
            "Runtime response validation requirements must be declared.",
        )
    if _as_bool(_get(request, "runtime_response_validation.satisfied_by_preflight_or_cache")) is not False:
        return _stopped(
            request,
            "response_validation_substituted",
            "Preflight/cache evidence cannot satisfy runtime response validation.",
        )
    if _string_list(_get(request, "runtime_response_validation.minimum_response_fields")) is None:
        return _stopped(
            request,
            "response_validation_missing",
            "runtime_response_validation.minimum_response_fields must be a non-empty string list.",
        )
    return None


def _validate_preflight_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("preflight_evidence")
    if not isinstance(evidence, dict):
        return _stopped(request, "preflight_evidence_missing", "preflight_evidence must be a JSON object.")
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "preflight_evidence_fallback",
            "Fallback create-thread preflight evidence blocks the authorization gate.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "preflight_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Create-thread preflight evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "preflight_evidence_missing",
            "preflight_evidence.status must be ready.",
        )
    if evidence.get("requested_action") != EXPECTED_PREFLIGHT_ACTION:
        return _stopped(
            request,
            "preflight_evidence_mismatch",
            "preflight_evidence.requested_action must be preflight-create-thread-runtime-call.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "preflight_evidence_mismatch",
            "preflight_evidence.target_action must be create-thread.",
        )
    if _as_bool(evidence.get("runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "preflight_evidence.runtime_call_performed must be false.",
        )
    if "private_runtime_state_read" in evidence and _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "preflight_evidence.private_runtime_state_read must be false when present.",
        )
    for field in ("repo", "remote", "branch", "expected_head"):
        if _get(evidence, f"target_evidence.{field}") != _get(request, f"target.{field}"):
            return _stopped(
                request,
                "preflight_evidence_mismatch",
                f"preflight_evidence.target_evidence.{field} must match target.{field}.",
            )
    return None


def _session_identity_matches(
    request: dict[str, Any],
    evidence_identity: Any,
    evidence_name: str,
) -> dict[str, Any] | None:
    current_identity = request.get("current_session_identity")
    if not isinstance(current_identity, dict) or _is_missing(current_identity):
        return _stopped(
            request,
            "missing_session_marker",
            "current_session_identity must be a non-empty JSON object.",
        )
    if not isinstance(evidence_identity, dict) or _is_missing(evidence_identity):
        return _stopped(
            request,
            "missing_session_marker",
            f"{evidence_name} must include same-session identity evidence.",
        )
    if current_identity != evidence_identity:
        return _stopped(
            request,
            "session_marker_mismatch",
            f"{evidence_name} does not match current_session_identity.",
        )
    return None


def _validate_session_status_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("session_status_evidence")
    if not isinstance(evidence, dict):
        return _stopped(
            request,
            "session_status_evidence_missing",
            "session_status_evidence must be a JSON object.",
        )
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "session_status_evidence_fallback",
            "Fallback session compatibility status evidence blocks the authorization gate.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "session_status_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Session compatibility status evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "session_status_evidence_missing",
            "session_status_evidence.status must be ready.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "session_status_evidence_mismatch",
            "session_status_evidence.target_action must be create-thread.",
        )
    if _get(evidence, "validated_status.target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "session_status_evidence_mismatch",
            "validated_status.target_action must be create-thread.",
        )
    if _get(evidence, "validated_status.tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "session_status_evidence_mismatch",
            "validated_status.tool_or_api must be create_thread.",
        )
    if _as_bool(evidence.get("runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "session_status_evidence.runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "session_status_evidence.private_runtime_state_read must be false.",
        )
    if _as_bool(evidence.get("later_runtime_path_blocked")) is not False:
        return _stopped(
            request,
            "session_status_evidence_stopped",
            "ready session status evidence must not block later runtime paths by itself.",
        )
    return _session_identity_matches(
        request,
        _get(evidence, "validated_status.session_identity"),
        "session_status_evidence.validated_status.session_identity",
    )


def _validate_cache_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("session_cache_evidence")
    if not isinstance(evidence, dict):
        return _stopped(
            request,
            "session_cache_evidence_missing",
            "session_cache_evidence must be a JSON object.",
        )
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "session_cache_evidence_fallback",
            "Fallback session compatibility cache evidence blocks the authorization gate.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "session_cache_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Session compatibility cache evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "session_cache_evidence_missing",
            "session_cache_evidence.status must be ready.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "session_cache_evidence_mismatch",
            "session_cache_evidence.target_action must be create-thread.",
        )
    if _get(evidence, "cache_evidence.target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "session_cache_evidence_mismatch",
            "cache_evidence.target_action must be create-thread.",
        )
    if _get(evidence, "cache_evidence.tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "session_cache_evidence_mismatch",
            "cache_evidence.tool_or_api must be create_thread.",
        )
    if _get(evidence, "cache_evidence.cache_scope") != "same-session":
        return _stopped(
            request,
            "cache_scope_mismatch",
            "cache_evidence.cache_scope must be same-session.",
        )
    if _get(evidence, "cache_evidence.same_session_only") is not True:
        return _stopped(
            request,
            "cache_scope_mismatch",
            "cache_evidence.same_session_only must be true.",
        )
    expires_at = _parse_timestamp(_get(evidence, "cache_evidence.expires_at"))
    if expires_at is not None and expires_at <= _now_utc():
        return _stopped(
            request,
            "stale_or_expired_cache",
            "cache_evidence.expires_at is stale or expired.",
        )
    if _as_bool(evidence.get("runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "session_cache_evidence.runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "session_cache_evidence.private_runtime_state_read must be false.",
        )
    if _as_bool(evidence.get("cache_read_performed")) is not True:
        return _stopped(
            request,
            "session_cache_evidence_missing",
            "session_cache_evidence.cache_read_performed must be true.",
        )
    if _as_bool(evidence.get("later_runtime_path_blocked")) is not False:
        return _stopped(
            request,
            "session_cache_evidence_stopped",
            "ready session cache evidence must not block later runtime paths by itself.",
        )
    return _session_identity_matches(
        request,
        _get(evidence, "cache_evidence.session_identity"),
        "session_cache_evidence.cache_evidence.session_identity",
    )


def authorize_create_thread_runtime_call_envelope(request: dict[str, Any]) -> dict[str, Any]:
    """Validate the pre-runtime-call authorization/evidence envelope."""

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")

    forbidden_hits = _forbidden_source_hits(request)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
        )

    missing = [path for path in _required_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped(request, "validation_error", "Missing required field(s): " + ", ".join(missing))

    validations = (
        _validate_exact_action,
        _validate_safety_boundaries,
        _validate_human_marker,
        _validate_target_validation,
        _validate_permission_and_response_placeholders,
        _validate_preflight_evidence,
        _validate_session_status_evidence,
        _validate_cache_evidence,
    )
    for validation in validations:
        response = validation(request)
        if response is not None:
            return response

    response = _base_response(request, "ready")
    response["failure_class"] = None
    response["later_runtime_path_blocked"] = False
    response["result"]["residual_risk"] = [
        "This helper did not call create_thread or any Desktop thread tool.",
        "The human approval marker is evidence for considering a future implementation only.",
        "Cache, status, and preflight evidence did not satisfy authorization, target validation, permission handling, or runtime response validation.",
        "A future runtime-call implementation still needs separate human approval before it is added or used.",
    ]
    return response


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    now = _now_utc().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    session_identity = {
        "marker_type": "current-session",
        "marker": "current-session scoped",
    }
    target = {
        "repo": "owner/name",
        "remote": "https://github.com/owner/name.git",
        "branch": "codex/example",
        "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
    }
    preflight_evidence = {
        "status": "ready",
        "requested_action": EXPECTED_PREFLIGHT_ACTION,
        "target_action": TARGET_ACTION,
        "runtime_call_performed": False,
        "target_evidence": target,
        "result": {"stop_reason": None},
    }
    session_status_evidence = {
        "status": "ready",
        "target_action": TARGET_ACTION,
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "later_runtime_path_blocked": False,
        "validated_status": {
            "target_action": TARGET_ACTION,
            "tool_or_api": TOOL_OR_API,
            "schema_hash": "sha256:example",
            "comparison_result": "compatible",
            "last_verified": today,
            "session_identity": session_identity,
        },
        "result": {"stop_reason": None},
    }
    session_cache_evidence = {
        "status": "ready",
        "target_action": TARGET_ACTION,
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "cache_read_performed": True,
        "later_runtime_path_blocked": False,
        "cache_evidence": {
            "target_action": TARGET_ACTION,
            "tool_or_api": TOOL_OR_API,
            "schema_hash": "sha256:example",
            "comparison_result": "compatible",
            "last_verified": today,
            "cache_scope": "same-session",
            "same_session_only": True,
            "created_at": now,
            "session_identity": session_identity,
        },
        "result": {"stop_reason": None},
    }
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "target": target,
        "prompt": {
            "summary": "Prepare one create-thread runtime-call implementation slice.",
            "body": "Implement only the separately approved runtime-call path and then run verification.",
        },
        "boundaries": {
            "external_writes_blocked": True,
            "runtime_call_performed": False,
            "desktop_private_runtime_state_read": False,
        },
        "authorization": {
            "authorized_runtime_action": TARGET_ACTION,
            "human_approval_marker": HUMAN_APPROVAL_MARKER,
            "human_approval_scope": HUMAN_APPROVAL_SCOPE,
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
        "target_validation": {
            "caller_confirmed": True,
            **target,
        },
        "permission_failure_handling": {
            "requirements_declared": True,
            "satisfied_by_preflight_or_cache": False,
            "requirements": [
                "stop on auth or permission failure",
                "surface runtime error response for human review",
            ],
        },
        "runtime_response_validation": {
            "requirements_declared": True,
            "satisfied_by_preflight_or_cache": False,
            "minimum_response_fields": ["status", "thread_id"],
        },
        "current_session_identity": session_identity,
        "preflight_evidence": preflight_evidence,
        "session_status_evidence": session_status_evidence,
        "session_cache_evidence": session_cache_evidence,
    }


def _load_request(path: str | None) -> dict[str, Any]:
    if path:
        path_reason = _request_path_rejection_reason(path)
        if path_reason is not None:
            raise OSError(path_reason)
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
        response = authorize_create_thread_runtime_call_envelope(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
