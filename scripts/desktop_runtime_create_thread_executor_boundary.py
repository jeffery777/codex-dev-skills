#!/usr/bin/env python3
"""Create-thread runtime-call executor boundary proposal helper.

This helper validates a caller-supplied proposal envelope for one future
``create_thread`` runtime-call executor. It is still a proposal and boundary
helper, not an executor: it never calls Desktop thread tools, never reads
Desktop private runtime state, and never treats prior gate evidence as a
substitute for call-site target validation, permission/auth handling, or
runtime response validation.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


EXECUTOR_BOUNDARY_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "propose-create-thread-runtime-call-executor-boundary"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"
EXPECTED_GATE_ACTION = "authorize-create-thread-runtime-call-envelope"

HUMAN_APPROVAL_MARKER = "human-approved-create-thread-runtime-call-executor-boundary-proposal-only"
HUMAN_APPROVAL_SCOPE = "proposal-helper-only-no-runtime-call"

REQUIRED_EXECUTOR_RECHECKS = [
    "target_identity",
    "authorization_intent",
    "permission_auth_failure_result",
    "runtime_response_shape",
    "returned_thread_id",
    "returned_status",
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


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "executor_boundary_helper_version": EXECUTOR_BOUNDARY_HELPER_VERSION,
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": status != "ready",
        "readiness_meaning": (
            "ready means the runtime-call implementation proposal/boundary is "
            "complete enough for a human to consider approving one future "
            "create_thread executor wiring slice; it does not authorize or "
            "perform a runtime call."
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
            "human_approval_marker": _get(request, "authorization.human_approval_marker"),
            "human_approval_scope": _get(request, "authorization.human_approval_scope"),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "destructive_action_approved": _get(request, "authorization.destructive_action_approved"),
        },
        "required_executor_rechecks": REQUIRED_EXECUTOR_RECHECKS,
        "executor_contract": {
            "single_tool_path": _get(request, "executor_contract.single_tool_path"),
            "call_site_rechecks": _get(request, "executor_contract.call_site_rechecks"),
            "minimum_response_fields": _get(
                request, "executor_contract.response_validation.minimum_response_fields"
            ),
            "permission_failure_handling": _get(
                request, "executor_contract.permission_failure_handling.requirements"
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
        "Stopped executor boundary proposals must block later runtime-call paths."
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
        "Fallback executor boundary proposals must block later runtime-call paths."
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
        "executor_contract.single_tool_path",
        "executor_contract.call_site_rechecks",
        "executor_contract.target_validation.required_at_call_site",
        "executor_contract.target_validation.satisfied_by_prior_evidence",
        "executor_contract.permission_failure_handling.required_at_call_site",
        "executor_contract.permission_failure_handling.satisfied_by_prior_evidence",
        "executor_contract.permission_failure_handling.requirements",
        "executor_contract.response_validation.required_at_call_site",
        "executor_contract.response_validation.satisfied_by_prior_evidence",
        "executor_contract.response_validation.minimum_response_fields",
        "executor_contract.human_approval_boundary.required_before_executor_use",
        "executor_contract.human_approval_boundary.scope",
        "executor_contract.external_writes_blocked",
        "authorization_gate_evidence",
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
    if _as_bool(_get(request, "executor_contract.external_writes_blocked")) is not True:
        return _stopped(
            request,
            "external_write_request",
            "executor_contract.external_writes_blocked must remain true.",
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
    marker = _get(request, "authorization.human_approval_marker")
    scope = _get(request, "authorization.human_approval_scope")
    if _is_missing(marker) or _is_missing(scope):
        return _fallback(
            request,
            "Missing exact human-approved implementation boundary marker for this proposal.",
        )
    if marker != HUMAN_APPROVAL_MARKER or scope != HUMAN_APPROVAL_SCOPE:
        return _stopped(
            request,
            "human_approval_boundary_unclear",
            "Human approval marker must be scoped to proposal-helper-only with no runtime call.",
        )
    if _get(request, "executor_contract.human_approval_boundary.scope") != HUMAN_APPROVAL_SCOPE:
        return _stopped(
            request,
            "human_approval_boundary_unclear",
            "executor_contract.human_approval_boundary.scope must match the proposal-only scope.",
        )
    if _as_bool(
        _get(request, "executor_contract.human_approval_boundary.required_before_executor_use")
    ) is not True:
        return _stopped(
            request,
            "human_approval_boundary_unclear",
            "executor use must still require separate human approval.",
        )
    return None


def _validate_executor_contract(request: dict[str, Any]) -> dict[str, Any] | None:
    if _get(request, "executor_contract.single_tool_path") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "executor_contract.single_tool_path must be create_thread.",
        )

    rechecks = _string_list(_get(request, "executor_contract.call_site_rechecks"))
    if rechecks is None:
        return _stopped(
            request,
            "call_site_rechecks_missing",
            "executor_contract.call_site_rechecks must be a non-empty string list.",
        )
    missing_rechecks = [item for item in REQUIRED_EXECUTOR_RECHECKS if item not in rechecks]
    if missing_rechecks:
        return _stopped(
            request,
            "call_site_rechecks_missing",
            "Missing required executor recheck(s): " + ", ".join(missing_rechecks),
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
        if _as_bool(_get(request, f"executor_contract.{section}.required_at_call_site")) is not True:
            return _stopped(
                request,
                failure_class.replace("_substituted", "_missing"),
                f"executor_contract.{section}.required_at_call_site must be true.",
            )
        if _as_bool(_get(request, f"executor_contract.{section}.satisfied_by_prior_evidence")) is not False:
            return _stopped(request, failure_class, reason)

    requirements = _string_list(_get(request, "executor_contract.permission_failure_handling.requirements"))
    response_fields = _string_list(_get(request, "executor_contract.response_validation.minimum_response_fields"))
    if requirements is None:
        return _stopped(
            request,
            "permission_handling_missing",
            "executor_contract.permission_failure_handling.requirements must be a non-empty string list.",
        )
    if response_fields is None:
        return _stopped(
            request,
            "response_validation_missing",
            "executor_contract.response_validation.minimum_response_fields must be a non-empty string list.",
        )
    missing_response_fields = [field for field in ("status", "thread_id") if field not in response_fields]
    if missing_response_fields:
        return _stopped(
            request,
            "response_validation_missing",
            "Missing runtime response field(s): " + ", ".join(missing_response_fields),
        )
    return None


def _validate_authorization_gate_evidence(request: dict[str, Any]) -> dict[str, Any] | None:
    evidence = request.get("authorization_gate_evidence")
    if not isinstance(evidence, dict):
        return _stopped(
            request,
            "authorization_gate_evidence_missing",
            "authorization_gate_evidence must be a JSON object.",
        )
    if evidence.get("status") == "fallback":
        return _stopped(
            request,
            "authorization_gate_evidence_fallback",
            "Fallback authorization gate evidence blocks executor boundary proposal readiness.",
        )
    if evidence.get("status") == "stopped":
        return _stopped(
            request,
            evidence.get("failure_class") or "authorization_gate_evidence_stopped",
            _get(evidence, "result.stop_reason") or "Authorization gate evidence stopped.",
        )
    if evidence.get("status") != "ready":
        return _stopped(
            request,
            "authorization_gate_evidence_missing",
            "authorization_gate_evidence.status must be ready.",
        )
    if evidence.get("requested_action") != EXPECTED_GATE_ACTION:
        return _stopped(
            request,
            "authorization_gate_evidence_mismatch",
            "authorization_gate_evidence.requested_action must be authorize-create-thread-runtime-call-envelope.",
        )
    if evidence.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "authorization_gate_evidence_mismatch",
            "authorization_gate_evidence.target_action must be create-thread.",
        )
    if evidence.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "authorization_gate_evidence_mismatch",
            "authorization_gate_evidence.tool_or_api must be create_thread.",
        )
    if _as_bool(evidence.get("runtime_call_performed")) is not False:
        return _stopped(
            request,
            "runtime_call_already_performed",
            "authorization_gate_evidence.runtime_call_performed must be false.",
        )
    if _as_bool(evidence.get("private_runtime_state_read")) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "authorization_gate_evidence.private_runtime_state_read must be false.",
        )
    if _as_bool(evidence.get("external_write_performed")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "authorization_gate_evidence.external_write_performed must be false.",
        )
    if _as_bool(evidence.get("later_runtime_path_blocked")) is not False:
        return _stopped(
            request,
            "authorization_gate_evidence_stopped",
            "ready authorization gate evidence must not block later runtime paths by itself.",
        )
    for field in ("repo", "remote", "branch", "expected_head"):
        if _get(evidence, f"target_evidence.{field}") != _get(request, f"target.{field}"):
            return _stopped(
                request,
                "authorization_gate_evidence_mismatch",
                f"authorization_gate_evidence.target_evidence.{field} must match target.{field}.",
            )
    if _get(evidence, "authorization_evidence.authorized_runtime_action") != TARGET_ACTION:
        return _stopped(
            request,
            "authorization_gate_evidence_mismatch",
            "authorization gate evidence must carry exact create-thread authorization intent.",
        )
    return None


def propose_executor_boundary(request: dict[str, Any]) -> dict[str, Any]:
    """Validate the non-executing create-thread executor boundary proposal."""

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
        _validate_executor_contract,
        _validate_authorization_gate_evidence,
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
        "The proposal does not authorize executor use or any external write.",
        "The future executor must re-check target identity and authorization intent at the call site.",
        "The future executor must classify permission/auth failures and validate status plus thread_id in the runtime response.",
        "A true create_thread executor remains future work and needs separate human approval before it is added or used.",
    ]
    return response


def example_request() -> dict[str, Any]:
    target = {
        "repo": "owner/name",
        "remote": "https://github.com/owner/name.git",
        "branch": "codex/example",
        "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
    }
    authorization_gate_evidence = {
        "status": "ready",
        "requested_action": EXPECTED_GATE_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": False,
        "target_evidence": target,
        "authorization_evidence": {
            "authorized_runtime_action": TARGET_ACTION,
        },
        "result": {"stop_reason": None},
    }
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "target": target,
        "prompt": {
            "summary": "Prepare one create-thread executor boundary proposal.",
            "body": "Document the call-site contract only; do not wire or invoke any runtime tool.",
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
        "executor_contract": {
            "single_tool_path": TOOL_OR_API,
            "call_site_rechecks": REQUIRED_EXECUTOR_RECHECKS,
            "target_validation": {
                "required_at_call_site": True,
                "satisfied_by_prior_evidence": False,
            },
            "permission_failure_handling": {
                "required_at_call_site": True,
                "satisfied_by_prior_evidence": False,
                "requirements": [
                    "stop on auth failure",
                    "stop on permission failure",
                    "return the permission/auth failure result for human review",
                ],
            },
            "response_validation": {
                "required_at_call_site": True,
                "satisfied_by_prior_evidence": False,
                "minimum_response_fields": ["status", "thread_id"],
            },
            "human_approval_boundary": {
                "required_before_executor_use": True,
                "scope": HUMAN_APPROVAL_SCOPE,
            },
            "external_writes_blocked": True,
        },
        "authorization_gate_evidence": authorization_gate_evidence,
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
        response = propose_executor_boundary(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
