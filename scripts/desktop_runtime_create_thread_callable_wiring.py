#!/usr/bin/env python3
"""Create-thread documented callable wiring-boundary helper.

This helper accepts a caller-supplied documented ``create_thread`` callable
descriptor or adapter registration envelope and converts it into the injected
adapter contract shape expected by ``desktop_runtime_create_thread_executor``.

It is intentionally non-live: it does not locate, import, obtain, or invoke a
Desktop runtime callable, and the CLI default falls back when no descriptor is
supplied. ``ready`` means callable wiring readiness only, not Desktop runtime
execution.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


WIRING_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "wire-create-thread-runtime-provided-callable-adapter"
EXPECTED_EXECUTOR_ACTION = "execute-create-thread-documented-callable-adapter"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"

HUMAN_WIRING_MARKER = "human-approved-create-thread-documented-callable-wiring-boundary"
HUMAN_WIRING_SCOPE = "single-documented-create-thread-callable-wiring-non-live-by-default"

ALLOWED_DESCRIPTOR_TYPES = {
    "runtime-provided-documented-callable-descriptor",
    "runtime-provided-adapter-registration-envelope",
    "explicit-non-live-adapter-wiring-contract",
}
ALLOWED_SOURCE_TYPES = {
    "caller-supplied-documented-runtime-metadata",
    "active-tool-list-excerpt",
    "runtime-provided-schema-excerpt",
    "runtime-provided-documented-callable-descriptor",
    "explicit-non-live-adapter-wiring-contract",
}
REQUIRED_EXECUTOR_CONTRACT_CHECKS = [
    "target_identity_rechecked_by_executor",
    "authorization_intent_rechecked_by_executor",
    "permission_auth_failure_classified_by_executor",
    "runtime_response_shape_validated_by_executor",
    "returned_thread_id_validated_by_executor",
    "returned_status_validated_by_executor",
]
REQUIRED_DESCRIPTOR_REQUEST_FIELDS = {"prompt.body", "target.repo"}
REQUIRED_DESCRIPTOR_RESPONSE_FIELDS = {"thread_id", "status"}

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
UNSUPPORTED_THREAD_TOOL_NAMES = {
    "fork_" + "thread",
    "send_message_" + "to_thread",
    "read_" + "thread",
}
UNSUPPORTED_THREAD_ACTION_NAMES = {
    "fork-thread",
    "send-message",
    "read-thread",
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


def _unsupported_thread_path_hits(value: Any) -> list[str]:
    hits: set[str] = set()
    for text in _iter_strings(value):
        lower = text.lower()
        for tool_name in UNSUPPORTED_THREAD_TOOL_NAMES:
            if tool_name in lower:
                hits.add(tool_name)
        for action_name in UNSUPPORTED_THREAD_ACTION_NAMES:
            if action_name in lower:
                hits.add(action_name)
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


def _descriptor(request: dict[str, Any]) -> dict[str, Any] | None:
    descriptor = request.get("callable_descriptor")
    if descriptor is None:
        descriptor = request.get("adapter_registration")
    if descriptor is None:
        return None
    return descriptor if isinstance(descriptor, dict) else {}


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    descriptor = _descriptor(request) or {}
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "wiring_helper_version": WIRING_HELPER_VERSION,
        "runtime_call_performed": False,
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": status != "ready",
        "readiness_label": "callable-wiring-readiness-not-desktop-runtime-execution",
        "readiness_meaning": (
            "ready means callable wiring readiness: a caller-supplied documented "
            "create_thread descriptor or explicit non-live adapter wiring contract "
            "was converted into the controlled injected adapter contract expected "
            "by the executor helper. It does not mean the CLI default or tests "
            "called Desktop runtime."
        ),
        "target_evidence": {
            "repo": _get(request, "target.repo"),
            "remote": _get(request, "target.remote"),
            "branch": _get(request, "target.branch"),
            "expected_head": _get(request, "target.expected_head"),
        },
        "prompt_evidence": {
            "summary_present": not _is_missing(_get(request, "prompt.summary")),
            "body_present": not _is_missing(_get(request, "prompt.body")),
            "summary": _get(request, "prompt.summary"),
        },
        "approval_boundary": {
            "human_wiring_marker": _get(request, "authorization.human_wiring_marker"),
            "human_wiring_scope": _get(request, "authorization.human_wiring_scope"),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "destructive_action_approved": _get(request, "authorization.destructive_action_approved"),
        },
        "descriptor_evidence": {
            "descriptor_type": descriptor.get("descriptor_type"),
            "source_type": descriptor.get("source_type"),
            "tool_or_api": descriptor.get("tool_or_api"),
            "target_action": descriptor.get("target_action"),
            "caller_supplied": descriptor.get("caller_supplied"),
            "documented_callable": descriptor.get("documented_callable"),
            "live_desktop_runtime": descriptor.get("live_desktop_runtime"),
        },
        "executor_call_site_requirements": REQUIRED_EXECUTOR_CONTRACT_CHECKS,
        "result": {
            "stop_reason": None,
            "adapter_contract": None,
            "executor_request_patch": None,
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
        "Stopped wiring evidence must block later runtime-call paths."
    ]
    return response


def _fallback(
    request: dict[str, Any],
    failure_class: str,
    reason: str,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback")
    response["failure_class"] = failure_class
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or [
        "Fallback wiring evidence must block later runtime-call paths."
    ]
    return response


def _required_base_paths() -> list[str]:
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
        "authorization.human_wiring_marker",
        "authorization.human_wiring_scope",
        "executor_contract.target_identity_rechecked_by_executor",
        "executor_contract.authorization_intent_rechecked_by_executor",
        "executor_contract.permission_auth_failure_classified_by_executor",
        "executor_contract.runtime_response_shape_validated_by_executor",
        "executor_contract.returned_thread_id_validated_by_executor",
        "executor_contract.returned_status_validated_by_executor",
        "executor_contract.target_validation.satisfied_by_prior_evidence",
        "executor_contract.permission_failure_handling.satisfied_by_prior_evidence",
        "executor_contract.response_validation.satisfied_by_prior_evidence",
        "previous_executor_evidence",
    ]


def _validate_exact_action(request: dict[str, Any]) -> dict[str, Any] | None:
    if request.get("requested_action") != REQUESTED_ACTION:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported requested_action: {request.get('requested_action')}",
        )
    if request.get("target_action") != TARGET_ACTION:
        return _stopped(request, "target_action_mismatch", "target_action must be create-thread.")
    if request.get("tool_or_api") != TOOL_OR_API:
        return _stopped(request, "tool_or_api_mismatch", "tool_or_api must be create_thread.")
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
            "boundaries.runtime_call_performed must be false before wiring.",
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
            "destructive action approval must be absent or false for this helper.",
        )
    if destructive not in (None, False):
        return _stopped(
            request,
            "destructive_action_approval_present",
            "authorization.destructive_action_approved must be absent or boolean false.",
        )
    return None


def _validate_human_marker(request: dict[str, Any]) -> dict[str, Any] | None:
    marker = _get(request, "authorization.human_wiring_marker")
    scope = _get(request, "authorization.human_wiring_scope")
    if _is_missing(marker) or _is_missing(scope):
        return _fallback(
            request,
            "human_wiring_marker_missing",
            "Missing exact human-approved callable wiring marker.",
        )
    if marker != HUMAN_WIRING_MARKER or scope != HUMAN_WIRING_SCOPE:
        return _stopped(
            request,
            "human_wiring_boundary_unclear",
            "Human wiring marker must be scoped to one documented create_thread callable path.",
        )
    return None


def _validate_executor_contract(request: dict[str, Any]) -> dict[str, Any] | None:
    for field in REQUIRED_EXECUTOR_CONTRACT_CHECKS:
        if _as_bool(_get(request, f"executor_contract.{field}")) is not True:
            return _stopped(
                request,
                "executor_contract_missing",
                f"executor_contract.{field} must be true.",
            )

    substitution_checks = (
        (
            "target_validation",
            "target_validation_substituted",
            "Prior evidence cannot satisfy executor call-site target validation.",
        ),
        (
            "permission_failure_handling",
            "permission_handling_substituted",
            "Prior evidence cannot satisfy executor permission/auth failure handling.",
        ),
        (
            "response_validation",
            "response_validation_substituted",
            "Prior evidence cannot satisfy executor runtime response validation.",
        ),
    )
    for section, failure_class, reason in substitution_checks:
        if _as_bool(
            _get(request, f"executor_contract.{section}.satisfied_by_prior_evidence")
        ) is not False:
            return _stopped(request, failure_class, reason)
    return None


def _validate_previous_executor_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("previous_executor_evidence")
    if not isinstance(evidence, dict):
        return _stopped(
            request,
            "previous_executor_evidence_missing",
            "previous_executor_evidence must be a JSON object.",
        )
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "previous_executor_evidence_fallback",
            "Fallback previous executor evidence blocks callable wiring readiness.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "previous_executor_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Previous executor evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "previous_executor_evidence_missing",
            "previous_executor_evidence.status must be ready.",
        )
    if evidence.get("requested_action") != EXPECTED_EXECUTOR_ACTION:
        return _stopped(
            request,
            "previous_executor_evidence_mismatch",
            "previous_executor_evidence.requested_action has the wrong executor action.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "previous_executor_evidence_mismatch",
            "previous_executor_evidence.target_action must be create-thread.",
        )
    if evidence.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "previous_executor_evidence_mismatch",
            "previous_executor_evidence.tool_or_api must be create_thread.",
        )
    if _as_bool(evidence.get("desktop_runtime_call_performed")) is not False:
        return _stopped(
            request,
            "live_desktop_runtime_not_allowed_by_default",
            "previous_executor_evidence.desktop_runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "previous_executor_evidence.private_runtime_state_read must be false.",
        )
    if _as_bool(evidence.get("external_write_performed")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "previous_executor_evidence.external_write_performed must be false.",
        )

    for field in ("repo", "remote", "branch", "expected_head"):
        if _get(evidence, f"target_evidence.{field}") != _get(request, f"target.{field}"):
            return _stopped(
                request,
                "previous_executor_evidence_mismatch",
                f"previous_executor_evidence.target_evidence.{field} must match target.{field}.",
            )
    if _get(evidence, "prompt_evidence.summary") != _get(request, "prompt.summary"):
        return _stopped(
            request,
            "previous_executor_evidence_mismatch",
            "previous_executor_evidence.prompt_evidence.summary must match prompt.summary.",
        )
    if _as_bool(_get(evidence, "prompt_evidence.summary_present")) is not True:
        return _stopped(
            request,
            "previous_executor_evidence_mismatch",
            "previous executor evidence must include prompt summary evidence.",
        )
    if _as_bool(_get(evidence, "prompt_evidence.body_present")) is not True:
        return _stopped(
            request,
            "previous_executor_evidence_mismatch",
            "previous executor evidence must include prompt body evidence.",
        )
    return None


def _validate_descriptor_shape(
    request: dict[str, Any], descriptor: dict[str, Any]
) -> dict[str, Any] | None:
    if not descriptor:
        return _fallback(
            request,
            "callable_descriptor_missing",
            "No caller-supplied documented create_thread callable descriptor was supplied; CLI default is non-live.",
        )
    if descriptor.get("descriptor_type") not in ALLOWED_DESCRIPTOR_TYPES:
        return _stopped(
            request,
            "callable_descriptor_malformed",
            "callable_descriptor.descriptor_type must identify a documented create_thread descriptor or non-live wiring contract.",
        )
    if descriptor.get("source_type") not in ALLOWED_SOURCE_TYPES:
        return _stopped(
            request,
            "callable_descriptor_source_unclear",
            "callable_descriptor.source_type must be caller-supplied documented runtime metadata, active tool list excerpt, runtime-provided schema excerpt, or explicit non-live wiring contract.",
        )
    if descriptor.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "target_action_mismatch",
            "callable_descriptor.target_action must be create-thread.",
        )
    if descriptor.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "callable_descriptor.tool_or_api must be create_thread.",
        )
    if _as_bool(descriptor.get("caller_supplied")) is not True:
        return _stopped(
            request,
            "callable_descriptor_source_unclear",
            "callable_descriptor.caller_supplied must be true.",
        )
    if _as_bool(descriptor.get("documented_callable")) is not True:
        return _stopped(
            request,
            "callable_descriptor_source_unclear",
            "callable_descriptor.documented_callable must be true.",
        )
    for field, failure_class, message in (
        ("execution_allowed", "runtime_call_authorization_present", "execution_allowed must be false."),
        (
            "runtime_lookup_performed",
            "runtime_callable_lookup_performed",
            "runtime_lookup_performed must be false.",
        ),
        (
            "runtime_call_shape_present",
            "direct_runtime_call_shape_present",
            "runtime_call_shape_present must be false.",
        ),
        (
            "live_desktop_runtime",
            "live_desktop_runtime_not_allowed_by_default",
            "live_desktop_runtime must be false.",
        ),
        (
            "external_write_authorized",
            "external_write_request",
            "external_write_authorized must be false.",
        ),
    ):
        if _as_bool(descriptor.get(field)) is not False:
            return _stopped(request, failure_class, f"callable_descriptor.{message}")

    allowed_actions = _string_list(descriptor.get("allowed_target_actions"))
    if allowed_actions != [TARGET_ACTION]:
        return _stopped(
            request,
            "unsupported_thread_tool_path",
            "callable_descriptor.allowed_target_actions must contain only create-thread.",
        )

    request_fields = _string_list(descriptor.get("required_request_fields"))
    response_fields = _string_list(descriptor.get("minimum_response_fields"))
    if request_fields is None or not REQUIRED_DESCRIPTOR_REQUEST_FIELDS.issubset(request_fields):
        return _stopped(
            request,
            "callable_descriptor_malformed",
            "callable_descriptor.required_request_fields must include prompt.body and target.repo.",
        )
    if response_fields is None or not REQUIRED_DESCRIPTOR_RESPONSE_FIELDS.issubset(response_fields):
        return _stopped(
            request,
            "callable_descriptor_malformed",
            "callable_descriptor.minimum_response_fields must include thread_id and status.",
        )
    if _is_missing(descriptor.get("source_excerpt")):
        return _stopped(
            request,
            "callable_descriptor_source_unclear",
            "callable_descriptor.source_excerpt must describe the documented source supplied by the caller.",
        )
    if _is_missing(descriptor.get("last_verified")):
        return _stopped(
            request,
            "callable_descriptor_source_unclear",
            "callable_descriptor.last_verified is required.",
        )

    source_path_reason = _request_path_rejection_reason(descriptor.get("source_path"))
    if source_path_reason is not None:
        return _stopped(request, "forbidden_private_runtime_state", source_path_reason)
    return None


def _adapter_contract_from_descriptor(descriptor: dict[str, Any]) -> dict[str, Any]:
    mode = "explicit-injected-documented-callable-adapter"
    if descriptor.get("descriptor_type") == "explicit-non-live-adapter-wiring-contract":
        mode = "explicit-injected-non-live-test-adapter"
    return {
        "mode": mode,
        "tool_or_api": TOOL_OR_API,
        "documented_callable": True,
        "caller_supplied": True,
        "live_desktop_runtime": False,
        "external_write_authorized": False,
        "source_type": descriptor.get("source_type"),
        "descriptor_type": descriptor.get("descriptor_type"),
        "required_request_fields": descriptor.get("required_request_fields"),
        "minimum_response_fields": descriptor.get("minimum_response_fields"),
        "wiring_readiness_label": "callable-wiring-readiness-not-desktop-runtime-execution",
    }


def wire_create_thread_callable_descriptor(request: dict[str, Any]) -> dict[str, Any]:
    """Validate one documented create_thread descriptor and emit adapter contract."""

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")

    forbidden_hits = _forbidden_source_hits(request)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
        )
    unsupported_hits = _unsupported_thread_path_hits(request)
    if unsupported_hits:
        return _stopped(
            request,
            "unsupported_thread_tool_path",
            "Only create_thread is allowed for this wiring boundary; found: "
            + ", ".join(unsupported_hits),
        )

    missing = [path for path in _required_base_paths() if _is_missing(_get(request, path))]
    if missing:
        if (
            "authorization.human_wiring_marker" in missing
            or "authorization.human_wiring_scope" in missing
        ):
            return _fallback(
                request,
                "human_wiring_marker_missing",
                "Missing exact human-approved callable wiring marker.",
            )
        return _stopped(request, "validation_error", "Missing required field(s): " + ", ".join(missing))

    validations = (
        _validate_exact_action,
        _validate_safety_boundaries,
        _validate_human_marker,
        _validate_executor_contract,
        _validate_previous_executor_evidence,
    )
    for validation in validations:
        response = validation(request)
        if response is not None:
            return response

    descriptor_supplied = "callable_descriptor" in request or "adapter_registration" in request
    descriptor = _descriptor(request)
    if descriptor_supplied and not descriptor:
        return _stopped(
            request,
            "callable_descriptor_malformed",
            "callable_descriptor or adapter_registration must be a non-empty JSON object.",
        )
    descriptor_response = _validate_descriptor_shape(request, descriptor or {})
    if descriptor_response is not None:
        return descriptor_response

    adapter_contract = _adapter_contract_from_descriptor(descriptor or {})
    response = _base_response(request, "ready")
    response["failure_class"] = None
    response["later_runtime_path_blocked"] = False
    response["result"]["adapter_contract"] = adapter_contract
    response["result"]["executor_request_patch"] = {
        "callable_adapter": {
            "mode": adapter_contract["mode"],
            "tool_or_api": TOOL_OR_API,
            "documented_callable": True,
            "caller_supplied": True,
            "live_desktop_runtime": False,
            "external_write_authorized": False,
        }
    }
    response["result"]["residual_risk"] = [
        "This ready result is callable wiring readiness only.",
        "The helper did not execute an injected adapter or call Desktop runtime.",
        "CLI default and tests remain non-live.",
        "The executor helper must still recheck target identity and authorization intent at the actual call site.",
        "The executor helper must still classify permission/auth failures and validate response shape, returned thread id, and returned status.",
        "True Desktop runtime create_thread use still requires separate human approval and a runtime-provided documented callable.",
    ]
    return response


def example_request() -> dict[str, Any]:
    target = {
        "repo": "owner/name",
        "remote": "https://github.com/owner/name.git",
        "branch": "codex/example",
        "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
    }
    prompt = {
        "summary": "Wire one documented create-thread callable descriptor.",
        "body": "Convert only the supplied descriptor to an executor adapter contract.",
    }
    previous_executor_evidence = {
        "status": "ready",
        "requested_action": EXPECTED_EXECUTOR_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "runtime_call_performed": True,
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "execution_kind": "injected-callable-adapter",
        "target_evidence": target,
        "prompt_evidence": {
            "summary_present": True,
            "body_present": True,
            "summary": prompt["summary"],
        },
        "result": {
            "stop_reason": None,
            "returned_thread_id": "thread_non_live_example",
            "returned_status": "created",
        },
    }
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "target": target,
        "prompt": prompt,
        "boundaries": {
            "external_writes_blocked": True,
            "runtime_call_performed": False,
            "desktop_private_runtime_state_read": False,
        },
        "authorization": {
            "authorized_runtime_action": TARGET_ACTION,
            "human_wiring_marker": HUMAN_WIRING_MARKER,
            "human_wiring_scope": HUMAN_WIRING_SCOPE,
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
        "executor_contract": {
            "target_identity_rechecked_by_executor": True,
            "authorization_intent_rechecked_by_executor": True,
            "permission_auth_failure_classified_by_executor": True,
            "runtime_response_shape_validated_by_executor": True,
            "returned_thread_id_validated_by_executor": True,
            "returned_status_validated_by_executor": True,
            "target_validation": {"satisfied_by_prior_evidence": False},
            "permission_failure_handling": {"satisfied_by_prior_evidence": False},
            "response_validation": {"satisfied_by_prior_evidence": False},
        },
        "callable_descriptor": {
            "descriptor_type": "runtime-provided-documented-callable-descriptor",
            "source_type": "caller-supplied-documented-runtime-metadata",
            "source_excerpt": "Documented create_thread callable descriptor supplied by the caller.",
            "last_verified": "2026-06-06",
            "target_action": TARGET_ACTION,
            "tool_or_api": TOOL_OR_API,
            "allowed_target_actions": [TARGET_ACTION],
            "required_request_fields": ["prompt.body", "target.repo"],
            "minimum_response_fields": ["thread_id", "status"],
            "caller_supplied": True,
            "documented_callable": True,
            "execution_allowed": False,
            "runtime_lookup_performed": False,
            "runtime_call_shape_present": False,
            "live_desktop_runtime": False,
            "external_write_authorized": False,
        },
        "previous_executor_evidence": previous_executor_evidence,
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
        response = wire_create_thread_callable_descriptor(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
