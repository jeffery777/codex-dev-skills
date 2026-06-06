#!/usr/bin/env python3
"""Create-thread callable wiring evidence bundle helper.

This helper assembles ready callable wiring evidence, caller-supplied
target/prompt evidence, and a human-approved authorization envelope into a
non-live executor request preview for ``desktop_runtime_create_thread_executor``.

It is intentionally non-live: it does not locate, import, obtain, or invoke a
Desktop runtime callable, does not execute an injected runner, and the CLI
default falls back when no wiring evidence is supplied. ``ready`` means only
that a non-live executor request preview / handoff bundle was assembled.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


BUNDLE_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "assemble-create-thread-callable-executor-request-preview"
EXPECTED_WIRING_ACTION = "wire-create-thread-runtime-provided-callable-adapter"
EXPECTED_EXECUTOR_ACTION = "execute-create-thread-documented-callable-adapter"
EXPECTED_SHELL_ACTION = "validate-create-thread-executor-shell-surface"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"

HUMAN_BUNDLE_MARKER = "human-approved-create-thread-callable-executor-request-bundle"
HUMAN_BUNDLE_SCOPE = "single-documented-create-thread-callable-bundle-non-live-by-default"
HUMAN_IMPLEMENTATION_MARKER = "human-approved-create-thread-documented-callable-executor-implementation"
HUMAN_IMPLEMENTATION_SCOPE = "single-documented-callable-adapter-non-live-by-default"

ALLOWED_ADAPTER_MODES = {
    "explicit-injected-non-live-test-adapter",
    "explicit-injected-documented-callable-adapter",
}
REQUIRED_EXECUTOR_RECHECKS = [
    "target_identity_rechecked_by_executor",
    "authorization_intent_rechecked_by_executor",
    "permission_auth_failure_classified_by_executor",
    "runtime_response_shape_validated_by_executor",
    "returned_thread_id_validated_by_executor",
    "returned_status_validated_by_executor",
]

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
FORBIDDEN_EXECUTOR_REQUEST_KEYS = {
    "runner",
    "callable_object",
    "runtime_callable",
    "direct_runtime_call",
    "runtime_call_shape",
    "callable_descriptor",
    "adapter_registration",
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


def _iter_keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        keys = []
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_iter_keys(item))
        return keys
    if isinstance(value, list):
        keys = []
        for item in value:
            keys.extend(_iter_keys(item))
        return keys
    return []


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


def _forbidden_executor_request_key_hits(value: Any) -> list[str]:
    hits: set[str] = set()
    for key in _iter_keys(value):
        normalized = key.strip().lower().replace("-", "_")
        if normalized in FORBIDDEN_EXECUTOR_REQUEST_KEYS:
            hits.add(normalized)
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


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "bundle_helper_version": BUNDLE_HELPER_VERSION,
        "runtime_call_performed": False,
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "live_desktop_runtime": False,
        "injected_runner_executed": False,
        "later_runtime_path_blocked": status != "ready",
        "readiness_label": "executor-request-preview-readiness-not-desktop-runtime-execution",
        "readiness_meaning": (
            "ready means executor request preview readiness only: ready callable "
            "wiring evidence was assembled into a non-live executor request preview "
            "/ handoff bundle. It does not mean the CLI default or tests called "
            "Desktop runtime, and it does not authorize true Desktop runtime "
            "create_thread use."
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
            "human_bundle_marker": _get(request, "authorization.human_bundle_marker"),
            "human_bundle_scope": _get(request, "authorization.human_bundle_scope"),
            "human_implementation_marker": _get(
                request, "authorization.human_implementation_marker"
            ),
            "human_implementation_scope": _get(
                request, "authorization.human_implementation_scope"
            ),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "destructive_action_approved": _get(
                request, "authorization.destructive_action_approved"
            ),
        },
        "executor_call_site_requirements": REQUIRED_EXECUTOR_RECHECKS,
        "result": {
            "stop_reason": None,
            "executor_request_preview": None,
            "handoff_bundle": None,
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
        "Stopped bundle evidence must block later runtime-call paths."
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
        "Fallback bundle evidence must block later runtime-call paths."
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
        "authorization.human_bundle_marker",
        "authorization.human_bundle_scope",
        "authorization.human_implementation_marker",
        "authorization.human_implementation_scope",
        "call_site_validation_plan.target_identity_rechecked_by_executor",
        "call_site_validation_plan.authorization_intent_rechecked_by_executor",
        "call_site_validation_plan.permission_auth_failure_classified_by_executor",
        "call_site_validation_plan.runtime_response_shape_validated_by_executor",
        "call_site_validation_plan.returned_thread_id_validated_by_executor",
        "call_site_validation_plan.returned_status_validated_by_executor",
        "call_site_validation_plan.target_validation.satisfied_by_prior_evidence",
        "call_site_validation_plan.permission_failure_handling.satisfied_by_prior_evidence",
        "call_site_validation_plan.response_validation.satisfied_by_prior_evidence",
        "executor_shell_evidence",
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
            "boundaries.runtime_call_performed must be false before bundling.",
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


def _validate_human_markers(request: dict[str, Any]) -> dict[str, Any] | None:
    marker = _get(request, "authorization.human_bundle_marker")
    scope = _get(request, "authorization.human_bundle_scope")
    if _is_missing(marker) or _is_missing(scope):
        return _fallback(
            request,
            "human_bundle_marker_missing",
            "Missing exact human-approved callable bundle marker.",
        )
    if marker != HUMAN_BUNDLE_MARKER or scope != HUMAN_BUNDLE_SCOPE:
        return _stopped(
            request,
            "human_bundle_boundary_unclear",
            "Human bundle marker must be scoped to one documented create_thread executor-request preview.",
        )
    if _get(request, "authorization.human_implementation_marker") != HUMAN_IMPLEMENTATION_MARKER:
        return _stopped(
            request,
            "human_implementation_boundary_unclear",
            "authorization.human_implementation_marker must match the executor helper boundary.",
        )
    if _get(request, "authorization.human_implementation_scope") != HUMAN_IMPLEMENTATION_SCOPE:
        return _stopped(
            request,
            "human_implementation_boundary_unclear",
            "authorization.human_implementation_scope must match the executor helper boundary.",
        )
    return None


def _validate_call_site_plan(request: dict[str, Any]) -> dict[str, Any] | None:
    for field in REQUIRED_EXECUTOR_RECHECKS:
        if _as_bool(_get(request, f"call_site_validation_plan.{field}")) is not True:
            return _stopped(
                request,
                "executor_contract_missing",
                f"call_site_validation_plan.{field} must be true.",
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
            _get(request, f"call_site_validation_plan.{section}.satisfied_by_prior_evidence")
        ) is not False:
            return _stopped(request, failure_class, reason)
    return None


def _validate_executor_shell_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("executor_shell_evidence")
    if not isinstance(evidence, dict):
        return _stopped(
            request,
            "executor_shell_evidence_missing",
            "executor_shell_evidence must be a JSON object.",
        )
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "executor_shell_evidence_fallback",
            "Fallback executor shell evidence blocks executor request preview assembly.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "executor_shell_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Executor shell evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "executor_shell_evidence_missing",
            "executor_shell_evidence.status must be ready.",
        )
    if evidence.get("requested_action") != EXPECTED_SHELL_ACTION:
        return _stopped(
            request,
            "executor_shell_evidence_mismatch",
            "executor_shell_evidence.requested_action has the wrong shell action.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "executor_shell_evidence_mismatch",
            "executor_shell_evidence.target_action must be create-thread.",
        )
    if evidence.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "executor_shell_evidence_mismatch",
            "executor_shell_evidence.tool_or_api must be create_thread.",
        )
    if _as_bool(evidence.get("runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "executor_shell_evidence.runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "executor_shell_evidence.private_runtime_state_read must be false.",
        )
    if _as_bool(evidence.get("external_write_performed")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "executor_shell_evidence.external_write_performed must be false.",
        )

    for field in ("repo", "remote", "branch", "expected_head"):
        if _get(evidence, f"target_evidence.{field}") != _get(request, f"target.{field}"):
            return _stopped(
                request,
                "executor_shell_evidence_mismatch",
                f"executor_shell_evidence.target_evidence.{field} must match target.{field}.",
            )
    if _get(evidence, "prompt_evidence.summary") != _get(request, "prompt.summary"):
        return _stopped(
            request,
            "executor_shell_evidence_mismatch",
            "executor_shell_evidence.prompt_evidence.summary must match prompt.summary.",
        )
    if _as_bool(_get(evidence, "prompt_evidence.summary_present")) is not True:
        return _stopped(
            request,
            "executor_shell_evidence_mismatch",
            "executor shell evidence must include prompt summary evidence.",
        )
    if _as_bool(_get(evidence, "prompt_evidence.body_present")) is not True:
        return _stopped(
            request,
            "executor_shell_evidence_mismatch",
            "executor shell evidence must include prompt body evidence.",
        )
    return None


def _validate_adapter_patch(
    request: dict[str, Any], adapter: dict[str, Any] | None
) -> dict[str, Any] | None:
    if not isinstance(adapter, dict) or not adapter:
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable_wiring_evidence.result.executor_request_patch.callable_adapter must be present.",
        )
    if adapter.get("mode") not in ALLOWED_ADAPTER_MODES:
        return _stopped(
            request,
            "callable_adapter_unclear",
            "callable_adapter.mode must identify an explicit injected adapter.",
        )
    if adapter.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "callable_adapter.tool_or_api must be create_thread.",
        )
    if _as_bool(adapter.get("documented_callable")) is not True:
        return _stopped(
            request,
            "callable_adapter_unclear",
            "callable_adapter.documented_callable must be true.",
        )
    if _as_bool(adapter.get("caller_supplied")) is not True:
        return _stopped(
            request,
            "callable_adapter_unclear",
            "callable_adapter.caller_supplied must be true.",
        )
    if _as_bool(adapter.get("live_desktop_runtime")) is not False:
        return _stopped(
            request,
            "live_desktop_runtime_not_allowed_by_default",
            "callable_adapter.live_desktop_runtime must be false.",
        )
    if _as_bool(adapter.get("external_write_authorized")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "callable_adapter.external_write_authorized must be false.",
        )
    key_hits = _forbidden_executor_request_key_hits(adapter)
    if key_hits:
        return _stopped(
            request,
            "direct_runtime_call_shape_present",
            "Callable adapter patch contains forbidden executor request key(s): "
            + ", ".join(key_hits),
        )
    return None


def _validate_callable_wiring_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("callable_wiring_evidence")
    if evidence is None:
        return _fallback(
            request,
            "callable_wiring_evidence_missing",
            "No ready callable wiring evidence was supplied; CLI default is non-live.",
        )
    if not isinstance(evidence, dict):
        return _stopped(
            request,
            "callable_wiring_evidence_malformed",
            "callable_wiring_evidence must be a JSON object.",
        )
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "callable_wiring_evidence_fallback",
            "Fallback callable wiring evidence blocks executor request preview assembly.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "callable_wiring_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Callable wiring evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "callable_wiring_evidence_missing",
            "callable_wiring_evidence.status must be ready.",
        )
    if evidence.get("requested_action") != EXPECTED_WIRING_ACTION:
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable_wiring_evidence.requested_action has the wrong wiring action.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable_wiring_evidence.target_action must be create-thread.",
        )
    if evidence.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable_wiring_evidence.tool_or_api must be create_thread.",
        )
    if _as_bool(evidence.get("runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "callable_wiring_evidence.runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("desktop_runtime_call_performed")) is not False:
        return _stopped(
            request,
            "live_desktop_runtime_not_allowed_by_default",
            "callable_wiring_evidence.desktop_runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "callable_wiring_evidence.private_runtime_state_read must be false.",
        )
    if _as_bool(evidence.get("external_write_performed")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "callable_wiring_evidence.external_write_performed must be false.",
        )
    if _as_bool(evidence.get("later_runtime_path_blocked")) is not False:
        return _stopped(
            request,
            "callable_wiring_evidence_stopped",
            "ready callable wiring evidence must not block later runtime paths by itself.",
        )

    for field in ("repo", "remote", "branch", "expected_head"):
        if _get(evidence, f"target_evidence.{field}") != _get(request, f"target.{field}"):
            return _stopped(
                request,
                "callable_wiring_evidence_mismatch",
                f"callable_wiring_evidence.target_evidence.{field} must match target.{field}.",
            )
    if _get(evidence, "prompt_evidence.summary") != _get(request, "prompt.summary"):
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable_wiring_evidence.prompt_evidence.summary must match prompt.summary.",
        )
    if _as_bool(_get(evidence, "prompt_evidence.summary_present")) is not True:
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable wiring evidence must include prompt summary evidence.",
        )
    if _as_bool(_get(evidence, "prompt_evidence.body_present")) is not True:
        return _stopped(
            request,
            "callable_wiring_evidence_mismatch",
            "callable wiring evidence must include prompt body evidence.",
        )

    for field in REQUIRED_EXECUTOR_RECHECKS:
        if field not in evidence.get("executor_call_site_requirements", []):
            return _stopped(
                request,
                "executor_contract_missing",
                f"callable_wiring_evidence.executor_call_site_requirements must include {field}.",
            )

    return _validate_adapter_patch(
        request, _get(evidence, "result.executor_request_patch.callable_adapter")
    )


def _executor_request_preview(request: dict[str, Any]) -> dict[str, Any]:
    adapter = _get(request, "callable_wiring_evidence.result.executor_request_patch.callable_adapter")
    return {
        "requested_action": EXPECTED_EXECUTOR_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "live_desktop_runtime": False,
        "executor_request_kind": "non-live-preview",
        "target": {
            "repo": _get(request, "target.repo"),
            "remote": _get(request, "target.remote"),
            "branch": _get(request, "target.branch"),
            "expected_head": _get(request, "target.expected_head"),
        },
        "prompt": {
            "summary": _get(request, "prompt.summary"),
            "body": _get(request, "prompt.body"),
        },
        "boundaries": {
            "external_writes_blocked": True,
            "runtime_call_performed": False,
            "desktop_private_runtime_state_read": False,
        },
        "authorization": {
            "authorized_runtime_action": TARGET_ACTION,
            "human_implementation_marker": HUMAN_IMPLEMENTATION_MARKER,
            "human_implementation_scope": HUMAN_IMPLEMENTATION_SCOPE,
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
        "call_site_validation": {
            "target_identity_rechecked_here": True,
            "authorization_intent_rechecked_here": True,
            "target_validation": {"satisfied_by_prior_evidence": False},
            "permission_failure_handling": {"satisfied_by_prior_evidence": False},
            "response_validation": {"satisfied_by_prior_evidence": False},
        },
        "callable_adapter": {
            "mode": adapter["mode"],
            "tool_or_api": TOOL_OR_API,
            "documented_callable": True,
            "caller_supplied": True,
            "live_desktop_runtime": False,
            "external_write_authorized": False,
        },
        "executor_shell_evidence": request["executor_shell_evidence"],
    }


def assemble_create_thread_callable_bundle(request: dict[str, Any]) -> dict[str, Any]:
    """Assemble one non-live executor request preview / handoff bundle."""

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
            "Only create_thread is allowed for this bundle boundary; found: "
            + ", ".join(unsupported_hits),
        )

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

    if "callable_wiring_evidence" not in request or request.get("callable_wiring_evidence") is None:
        return _fallback(
            request,
            "callable_wiring_evidence_missing",
            "No ready callable wiring evidence was supplied; CLI default is non-live.",
        )

    missing = [path for path in _required_base_paths() if _is_missing(_get(request, path))]
    if missing:
        if (
            "authorization.human_bundle_marker" in missing
            or "authorization.human_bundle_scope" in missing
        ):
            return _fallback(
                request,
                "human_bundle_marker_missing",
                "Missing exact human-approved callable bundle marker.",
            )
        return _stopped(request, "validation_error", "Missing required field(s): " + ", ".join(missing))

    validations = (
        _validate_exact_action,
        _validate_safety_boundaries,
        _validate_human_markers,
        _validate_call_site_plan,
        _validate_executor_shell_evidence,
        _validate_callable_wiring_evidence,
    )
    for validation in validations:
        response = validation(request)
        if response is not None:
            return response

    preview = _executor_request_preview(request)
    key_hits = _forbidden_executor_request_key_hits(preview)
    if key_hits:
        return _stopped(
            request,
            "direct_runtime_call_shape_present",
            "Generated executor request preview contains forbidden key(s): "
            + ", ".join(key_hits),
        )

    response = _base_response(request, "ready")
    response["failure_class"] = None
    response["later_runtime_path_blocked"] = False
    response["result"]["executor_request_preview"] = preview
    response["result"]["handoff_bundle"] = {
        "bundle_type": "single-documented-create-thread-callable-executor-request-preview",
        "live_desktop_runtime": False,
        "runtime_call_performed": False,
        "desktop_runtime_call_performed": False,
        "injected_runner_executed": False,
        "allowed_target_actions": [TARGET_ACTION],
        "executor_helper": "scripts/desktop_runtime_create_thread_executor.py",
        "executor_required_rechecks": REQUIRED_EXECUTOR_RECHECKS,
        "fallback_or_stopped_blocks_later_runtime_path": True,
    }
    response["result"]["residual_risk"] = [
        "This ready result is executor request preview readiness only.",
        "The helper did not execute an injected runner or call Desktop runtime.",
        "CLI default and tests remain non-live.",
        "The executor helper must still actually recheck target identity and authorization intent at the call site.",
        "The executor helper must still classify permission/auth failures and validate response shape, returned thread id, and returned status.",
        "Shell, proposal, gate, cache, preflight, executor, and wiring evidence cannot replace actual call-site validation or response validation.",
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
        "summary": "Assemble one non-live create-thread executor request preview.",
        "body": "Use ready wiring evidence to prepare a handoff bundle only.",
    }
    executor_shell_evidence = {
        "status": "ready",
        "requested_action": EXPECTED_SHELL_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": False,
        "target_evidence": target,
        "prompt_evidence": {
            "summary_present": True,
            "body_present": True,
            "summary": prompt["summary"],
        },
        "result": {"stop_reason": None},
    }
    callable_wiring_evidence = {
        "status": "ready",
        "requested_action": EXPECTED_WIRING_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "runtime_call_performed": False,
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": False,
        "readiness_label": "callable-wiring-readiness-not-desktop-runtime-execution",
        "target_evidence": target,
        "prompt_evidence": {
            "summary_present": True,
            "body_present": True,
            "summary": prompt["summary"],
        },
        "executor_call_site_requirements": REQUIRED_EXECUTOR_RECHECKS,
        "result": {
            "stop_reason": None,
            "executor_request_patch": {
                "callable_adapter": {
                    "mode": "explicit-injected-non-live-test-adapter",
                    "tool_or_api": TOOL_OR_API,
                    "documented_callable": True,
                    "caller_supplied": True,
                    "live_desktop_runtime": False,
                    "external_write_authorized": False,
                }
            },
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
            "human_bundle_marker": HUMAN_BUNDLE_MARKER,
            "human_bundle_scope": HUMAN_BUNDLE_SCOPE,
            "human_implementation_marker": HUMAN_IMPLEMENTATION_MARKER,
            "human_implementation_scope": HUMAN_IMPLEMENTATION_SCOPE,
            "external_write_authorized": False,
            "destructive_action_approved": False,
        },
        "call_site_validation_plan": {
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
        "executor_shell_evidence": executor_shell_evidence,
        "callable_wiring_evidence": callable_wiring_evidence,
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
        response = assemble_create_thread_callable_bundle(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
