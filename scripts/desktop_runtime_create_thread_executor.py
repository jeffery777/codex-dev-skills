#!/usr/bin/env python3
"""Create-thread documented callable executor helper.

This helper is the first tiny executor implementation after the executor shell
surface. It validates ready shell evidence, re-checks the target and
authorization at the actual call site, and may execute exactly one
caller-injected documented callable adapter for ``create_thread``.

The CLI default is non-live: without an injected runner from a Python caller,
the helper falls back and blocks later runtime paths. This file does not locate,
discover, import, or call any Desktop runtime callable by itself.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Callable


EXECUTOR_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "execute-create-thread-documented-callable-adapter"
EXPECTED_SHELL_ACTION = "validate-create-thread-executor-shell-surface"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"

HUMAN_IMPLEMENTATION_MARKER = "human-approved-create-thread-documented-callable-executor-implementation"
HUMAN_IMPLEMENTATION_SCOPE = "single-documented-callable-adapter-non-live-by-default"

ALLOWED_ADAPTER_MODES = {
    "explicit-injected-non-live-test-adapter",
    "explicit-injected-documented-callable-adapter",
}
ALLOWED_RETURNED_STATUSES = {"created", "ready", "queued"}

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


class CreateThreadAdapterAuthError(RuntimeError):
    """Raised by an injected adapter when authentication is unavailable."""


class CreateThreadAdapterPermissionError(RuntimeError):
    """Raised by an injected adapter when permission is denied."""


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


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "executor_helper_version": EXECUTOR_HELPER_VERSION,
        "runtime_call_performed": False,
        "runtime_call_performed_meaning": (
            "false means no injected adapter execution happened; true means only the "
            "caller-injected adapter executed under this helper contract."
        ),
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": status != "ready",
        "execution_kind": "none",
        "readiness_meaning": (
            "ready means one caller-injected documented callable adapter contract "
            "completed under call-site validation. It does not mean the CLI "
            "default called Desktop runtime, and it does not authorize a live "
            "Desktop runtime path."
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
            "human_implementation_marker": _get(
                request, "authorization.human_implementation_marker"
            ),
            "human_implementation_scope": _get(request, "authorization.human_implementation_scope"),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "destructive_action_approved": _get(request, "authorization.destructive_action_approved"),
        },
        "adapter_contract": {
            "mode": _get(request, "callable_adapter.mode"),
            "tool_or_api": _get(request, "callable_adapter.tool_or_api"),
            "documented_callable": _get(request, "callable_adapter.documented_callable"),
            "caller_supplied": _get(request, "callable_adapter.caller_supplied"),
            "live_desktop_runtime": _get(request, "callable_adapter.live_desktop_runtime"),
        },
        "result": {
            "stop_reason": None,
            "returned_thread_id": None,
            "returned_status": None,
            "permission_or_auth_failure": None,
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
        "Stopped executor envelopes must block later runtime-call paths."
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
        "Fallback executor envelopes must block later runtime-call paths."
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
        "authorization.human_implementation_marker",
        "authorization.human_implementation_scope",
        "call_site_validation.target_identity_rechecked_here",
        "call_site_validation.authorization_intent_rechecked_here",
        "call_site_validation.target_validation.satisfied_by_prior_evidence",
        "call_site_validation.permission_failure_handling.satisfied_by_prior_evidence",
        "call_site_validation.response_validation.satisfied_by_prior_evidence",
        "callable_adapter.mode",
        "callable_adapter.tool_or_api",
        "callable_adapter.documented_callable",
        "callable_adapter.caller_supplied",
        "callable_adapter.live_desktop_runtime",
        "callable_adapter.external_write_authorized",
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
    if _as_bool(_get(request, "callable_adapter.external_write_authorized")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "callable_adapter.external_write_authorized must remain false.",
        )
    if _as_bool(_get(request, "boundaries.runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "boundaries.runtime_call_performed must be false before adapter execution.",
        )
    if _as_bool(_get(request, "boundaries.desktop_private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "boundaries.desktop_private_runtime_state_read must be false.",
        )
    if _as_bool(_get(request, "callable_adapter.live_desktop_runtime")) is not False:
        return _stopped(
            request,
            "live_desktop_runtime_not_allowed_by_default",
            "callable_adapter.live_desktop_runtime must be false for this helper path.",
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
    marker = _get(request, "authorization.human_implementation_marker")
    scope = _get(request, "authorization.human_implementation_scope")
    if _is_missing(marker) or _is_missing(scope):
        return _fallback(
            request,
            "human_implementation_marker_missing",
            "Missing exact human-approved executor implementation marker.",
        )
    if marker != HUMAN_IMPLEMENTATION_MARKER or scope != HUMAN_IMPLEMENTATION_SCOPE:
        return _stopped(
            request,
            "human_implementation_boundary_unclear",
            "Human implementation marker must be scoped to one non-live-by-default callable adapter.",
        )
    return None


def _validate_adapter_contract(request: dict[str, Any]) -> dict[str, Any] | None:
    if _get(request, "callable_adapter.mode") not in ALLOWED_ADAPTER_MODES:
        return _stopped(
            request,
            "callable_adapter_unclear",
            "callable_adapter.mode must identify an explicit injected adapter.",
        )
    if _get(request, "callable_adapter.tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "callable_adapter.tool_or_api must be create_thread.",
        )
    if _as_bool(_get(request, "callable_adapter.documented_callable")) is not True:
        return _stopped(
            request,
            "callable_adapter_unclear",
            "callable_adapter.documented_callable must be true.",
        )
    if _as_bool(_get(request, "callable_adapter.caller_supplied")) is not True:
        return _stopped(
            request,
            "callable_adapter_unclear",
            "callable_adapter.caller_supplied must be true.",
        )
    return None


def _validate_call_site_rechecks(request: dict[str, Any]) -> dict[str, Any] | None:
    if _as_bool(_get(request, "call_site_validation.target_identity_rechecked_here")) is not True:
        return _stopped(
            request,
            "call_site_target_validation_missing",
            "target identity must be rechecked in this helper before adapter execution.",
        )
    if _as_bool(_get(request, "call_site_validation.authorization_intent_rechecked_here")) is not True:
        return _stopped(
            request,
            "call_site_authorization_recheck_missing",
            "authorization intent must be rechecked in this helper before adapter execution.",
        )

    substitution_checks = (
        (
            "target_validation",
            "target_validation_substituted",
            "Prior evidence cannot satisfy call-site target validation.",
        ),
        (
            "permission_failure_handling",
            "permission_handling_substituted",
            "Prior evidence cannot satisfy call-site permission/auth failure handling.",
        ),
        (
            "response_validation",
            "response_validation_substituted",
            "Prior evidence cannot satisfy call-site runtime response validation.",
        ),
    )
    for section, failure_class, reason in substitution_checks:
        if _as_bool(
            _get(request, f"call_site_validation.{section}.satisfied_by_prior_evidence")
        ) is not False:
            return _stopped(request, failure_class, reason)
    return None


def _validate_shell_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
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
            "Fallback executor shell evidence blocks executor implementation readiness.",
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
    if _as_bool(evidence.get("later_runtime_path_blocked")) is not False:
        return _stopped(
            request,
            "executor_shell_evidence_stopped",
            "ready executor shell evidence must not block later runtime paths by itself.",
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


def _adapter_payload(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
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
        "execution_context": {
            "adapter_mode": _get(request, "callable_adapter.mode"),
            "desktop_runtime_call_performed": False,
            "private_runtime_state_read": False,
            "external_write_authorized": False,
        },
    }


def _classify_runner_failure(
    request: dict[str, Any], failure_class: str, message: str
) -> dict[str, Any]:
    response = _stopped(request, failure_class, message)
    response["result"]["permission_or_auth_failure"] = {
        "failure_class": failure_class,
        "message": message,
    }
    return response


def _validate_runner_response(request: dict[str, Any], runner_response: Any) -> dict[str, Any]:
    if not isinstance(runner_response, dict):
        return _stopped(
            request,
            "runtime_response_shape_invalid",
            "Injected adapter response must be a JSON object.",
        )

    forbidden_hits = _forbidden_source_hits(runner_response)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s) in adapter response: "
            + ", ".join(forbidden_hits),
        )

    if runner_response.get("status") in {"auth-failed", "permission-denied"}:
        return _classify_runner_failure(
            request,
            "adapter_permission_or_auth_failure",
            str(runner_response.get("message") or runner_response.get("status")),
        )

    if _as_bool(runner_response.get("desktop_runtime_call_performed")) is not False:
        return _stopped(
            request,
            "live_desktop_runtime_not_allowed_by_default",
            "Injected adapter must report desktop_runtime_call_performed: false.",
        )
    if _as_bool(runner_response.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Injected adapter must report private_runtime_state_read: false.",
        )
    if _as_bool(runner_response.get("external_write_performed")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "Injected adapter must report external_write_performed: false.",
        )

    thread_id = runner_response.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        return _stopped(
            request,
            "returned_thread_id_invalid",
            "Injected adapter response must include a non-empty thread_id string.",
        )

    returned_status = runner_response.get("status")
    if returned_status not in ALLOWED_RETURNED_STATUSES:
        return _stopped(
            request,
            "returned_status_invalid",
            "Injected adapter response status must be one of: "
            + ", ".join(sorted(ALLOWED_RETURNED_STATUSES)),
        )

    response = _base_response(request, "ready")
    response["failure_class"] = None
    response["runtime_call_performed"] = True
    response["runtime_call_performed_meaning"] = (
        "true means this helper executed a caller-injected adapter; "
        "desktop_runtime_call_performed remains false."
    )
    response["desktop_runtime_call_performed"] = False
    response["execution_kind"] = "injected-callable-adapter"
    response["later_runtime_path_blocked"] = False
    response["result"]["returned_thread_id"] = thread_id.strip()
    response["result"]["returned_status"] = returned_status
    response["result"]["residual_risk"] = [
        "This ready result is for injected adapter execution only.",
        "CLI default remains non-live and does not call Desktop runtime.",
        "True Desktop runtime create_thread injection still needs separate human approval and a runtime-provided documented callable.",
    ]
    return response


def execute_create_thread_with_injected_adapter(
    request: dict[str, Any],
    runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and execute one caller-injected create_thread adapter."""

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
        if "authorization.human_implementation_marker" in missing:
            return _fallback(
                request,
                "human_implementation_marker_missing",
                "Missing exact human-approved executor implementation marker.",
            )
        return _stopped(request, "validation_error", "Missing required field(s): " + ", ".join(missing))

    validations = (
        _validate_exact_action,
        _validate_safety_boundaries,
        _validate_human_marker,
        _validate_adapter_contract,
        _validate_call_site_rechecks,
        _validate_shell_evidence,
    )
    for validation in validations:
        response = validation(request)
        if response is not None:
            return response

    if runner is None:
        return _fallback(
            request,
            "injected_callable_runner_missing",
            "No caller-injected documented callable adapter was supplied; CLI default is non-live.",
        )

    payload = _adapter_payload(request)
    try:
        runner_response = runner(payload)
    except CreateThreadAdapterAuthError as exc:
        return _classify_runner_failure(request, "adapter_auth_failure", str(exc))
    except CreateThreadAdapterPermissionError as exc:
        return _classify_runner_failure(request, "adapter_permission_failure", str(exc))

    return _validate_runner_response(request, runner_response)


def example_request() -> dict[str, Any]:
    target = {
        "repo": "owner/name",
        "remote": "https://github.com/owner/name.git",
        "branch": "codex/example",
        "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
    }
    shell_evidence = {
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
            "summary": "Execute one injected create-thread adapter.",
        },
        "result": {"stop_reason": None},
    }
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "target": target,
        "prompt": {
            "summary": "Execute one injected create-thread adapter.",
            "body": "Run only the supplied non-live adapter; do not locate Desktop runtime.",
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
            "mode": "explicit-injected-non-live-test-adapter",
            "tool_or_api": TOOL_OR_API,
            "documented_callable": True,
            "caller_supplied": True,
            "live_desktop_runtime": False,
            "external_write_authorized": False,
        },
        "executor_shell_evidence": shell_evidence,
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
        response = execute_create_thread_with_injected_adapter(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
