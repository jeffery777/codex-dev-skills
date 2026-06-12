#!/usr/bin/env python3
"""Single documented create_thread live smoke helper.

This helper is the final tiny V1 smoke boundary: it can call exactly one
caller-injected, runtime-provided, documented ``create_thread`` callable after
actual call-site validation. The CLI default remains non-live and returns
``fallback`` because the CLI cannot receive a live Desktop callable.

``ready`` means only that one live create-thread smoke call completed and the
runtime returned a validated thread id or queued worktree id. It does not mean
the created thread completed the audit task and it does not authorize comments,
reviews, file edits, commits, pushes, PRs, merges, labels, status changes, or
other platform writes.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Callable


LIVE_SMOKE_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "smoke-create-thread-live-documented-callable"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"

HUMAN_LIVE_SMOKE_MARKER = "human-approved-single-create-thread-live-smoke"
HUMAN_LIVE_SMOKE_SCOPE = "single-documented-create-thread-live-smoke-read-only-audit"

ALLOWED_DESCRIPTOR_TYPES = {
    "runtime-provided-documented-create-thread-callable",
    "runtime-provided-documented-callable-descriptor",
}
ALLOWED_SOURCE_TYPES = {
    "active-tool-list-excerpt",
    "runtime-provided-schema-excerpt",
    "runtime-provided-documented-callable",
}
THREAD_ID_STATUSES = {"created", "ready", "queued"}
PENDING_WORKTREE_STATUSES = {"queued"}

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

REQUIRED_PROMPT_BOUNDARY_PHRASES = (
    "read-only audit",
    "do not post comments",
    "do not submit reviews",
    "do not edit files",
    "do not commit",
    "do not push",
    "do not open pull requests",
    "do not merge",
    "do not change labels",
    "do not change status",
    "do not perform platform writes",
)


class CreateThreadLiveSmokeAuthError(RuntimeError):
    """Raised by an injected live callable when authentication is unavailable."""


class CreateThreadLiveSmokePermissionError(RuntimeError):
    """Raised by an injected live callable when permission is denied."""


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


def build_read_only_audit_smoke_prompt() -> dict[str, str]:
    """Return the fixed read-only audit prompt used by the live smoke."""

    summary = "Read-only audit: merged PR formal merge review evidence gaps."
    body = "\n".join(
        [
            "Read-only audit for this repository.",
            "",
            "Goal:",
            "- Check whether past merged PRs are missing formal merge review evidence.",
            "- List candidate PRs, evidence, and gap type.",
            "- Suggest remediation options for a human to approve in a separate thread or step.",
            "",
            "Boundaries:",
            "- Do not post comments.",
            "- Do not submit reviews.",
            "- Do not edit files.",
            "- Do not commit.",
            "- Do not push.",
            "- Do not open pull requests.",
            "- Do not merge.",
            "- Do not close PRs or issues.",
            "- Do not change labels.",
            "- Do not change status.",
            "- Do not perform platform writes.",
            "- Remediation requires separate human approval.",
            "",
            "Completion expectation:",
            "- This smoke only verifies new thread creation and prompt delivery.",
            "- The audit task does not need to finish for the smoke to be successful.",
        ]
    )
    return {"summary": summary, "body": body}


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "live_smoke_helper_version": LIVE_SMOKE_HELPER_VERSION,
        "runtime_call_performed": False,
        "desktop_runtime_call_performed": False,
        "private_runtime_state_read": False,
        "external_write_performed": False,
        "later_runtime_path_blocked": status != "ready",
        "execution_kind": "none",
        "readiness_label": "single-create-thread-live-smoke-not-audit-completion",
        "readiness_meaning": (
            "ready means one documented create_thread live smoke call completed "
            "and returned a validated thread creation status. The created audit "
            "thread is not required to complete its read-only task."
        ),
        "target_evidence": {
            "repo": _get(request, "target.repo"),
            "remote": _get(request, "target.remote"),
            "branch": _get(request, "target.branch"),
            "expected_head": _get(request, "target.expected_head"),
        },
        "prompt_evidence": {
            "summary_present": not _is_missing(_get(request, "smoke_prompt.summary")),
            "body_present": not _is_missing(_get(request, "smoke_prompt.body")),
            "summary": _get(request, "smoke_prompt.summary"),
        },
        "approval_boundary": {
            "human_live_smoke_marker": _get(request, "authorization.human_live_smoke_marker"),
            "human_live_smoke_scope": _get(request, "authorization.human_live_smoke_scope"),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "destructive_action_approved": _get(
                request, "authorization.destructive_action_approved"
            ),
        },
        "callable_evidence": {
            "descriptor_type": _get(request, "live_callable_descriptor.descriptor_type"),
            "source_type": _get(request, "live_callable_descriptor.source_type"),
            "tool_or_api": _get(request, "live_callable_descriptor.tool_or_api"),
            "target_action": _get(request, "live_callable_descriptor.target_action"),
            "documented_callable": _get(
                request, "live_callable_descriptor.documented_callable"
            ),
            "runtime_provided": _get(request, "live_callable_descriptor.runtime_provided"),
            "live_desktop_runtime": _get(
                request, "live_callable_descriptor.live_desktop_runtime"
            ),
        },
        "result": {
            "stop_reason": None,
            "returned_thread_id": None,
            "pendingWorktreeId": None,
            "returned_status": None,
            "permission_or_auth_failure": None,
            "prompt_delivered": False,
            "audit_task_completed": False,
            "audit_task_completion_required": False,
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
        "Stopped live smoke envelopes must block later runtime-call paths."
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
        "Fallback live smoke envelopes must block later runtime-call paths."
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
        "smoke_prompt.summary",
        "smoke_prompt.body",
        "boundaries.external_writes_blocked",
        "boundaries.runtime_call_performed",
        "boundaries.desktop_private_runtime_state_read",
        "authorization.authorized_runtime_action",
        "authorization.external_write_authorized",
        "authorization.human_live_smoke_marker",
        "authorization.human_live_smoke_scope",
        "call_site_validation.target_identity_rechecked_here",
        "call_site_validation.authorization_intent_rechecked_here",
        "call_site_validation.target_validation.satisfied_by_prior_evidence",
        "call_site_validation.permission_failure_handling.satisfied_by_prior_evidence",
        "call_site_validation.response_validation.satisfied_by_prior_evidence",
        "live_callable_descriptor",
    ]


def _validate_exact_action(request: dict[str, Any]) -> dict[str, Any] | None:
    unsupported_hits = _unsupported_thread_path_hits(request)
    if unsupported_hits:
        return _stopped(
            request,
            "unsupported_thread_tool_path",
            "Only the documented create_thread path is allowed; found: "
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
            "boundaries.runtime_call_performed must be false before the live smoke.",
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
            "Destructive action approval must be absent or false for this helper.",
        )
    if destructive not in (None, False):
        return _stopped(
            request,
            "destructive_action_approval_present",
            "authorization.destructive_action_approved must be absent or boolean false.",
        )
    return None


def _validate_human_marker(request: dict[str, Any]) -> dict[str, Any] | None:
    marker = _get(request, "authorization.human_live_smoke_marker")
    scope = _get(request, "authorization.human_live_smoke_scope")
    if _is_missing(marker) or _is_missing(scope):
        return _fallback(
            request,
            "human_live_smoke_marker_missing",
            "Missing exact human-approved live smoke marker.",
        )
    if marker != HUMAN_LIVE_SMOKE_MARKER or scope != HUMAN_LIVE_SMOKE_SCOPE:
        return _stopped(
            request,
            "human_live_smoke_boundary_unclear",
            "Human live smoke marker must be scoped to one documented create_thread read-only audit smoke.",
        )
    return None


def _validate_call_site_rechecks(request: dict[str, Any]) -> dict[str, Any] | None:
    if _as_bool(_get(request, "call_site_validation.target_identity_rechecked_here")) is not True:
        return _stopped(
            request,
            "call_site_target_validation_missing",
            "Target identity must be rechecked at the live smoke call site.",
        )
    if _as_bool(_get(request, "call_site_validation.authorization_intent_rechecked_here")) is not True:
        return _stopped(
            request,
            "call_site_authorization_recheck_missing",
            "Authorization intent must be rechecked at the live smoke call site.",
        )

    substitution_checks = (
        (
            "target_validation",
            "target_validation_substituted",
            "Prior evidence cannot satisfy live smoke call-site target validation.",
        ),
        (
            "permission_failure_handling",
            "permission_handling_substituted",
            "Prior evidence cannot satisfy live smoke permission/auth failure handling.",
        ),
        (
            "response_validation",
            "response_validation_substituted",
            "Prior evidence cannot satisfy live smoke runtime response validation.",
        ),
    )
    for section, failure_class, reason in substitution_checks:
        if _as_bool(
            _get(request, f"call_site_validation.{section}.satisfied_by_prior_evidence")
        ) is not False:
            return _stopped(request, failure_class, reason)
    return None


def _validate_descriptor(request: dict[str, Any]) -> dict[str, Any] | None:
    descriptor = request.get("live_callable_descriptor")
    if not isinstance(descriptor, dict) or not descriptor:
        return _stopped(
            request,
            "live_callable_descriptor_malformed",
            "live_callable_descriptor must be a JSON object.",
        )
    if descriptor.get("descriptor_type") not in ALLOWED_DESCRIPTOR_TYPES:
        return _stopped(
            request,
            "live_callable_descriptor_malformed",
            "live_callable_descriptor.descriptor_type must identify one documented create_thread callable.",
        )
    if descriptor.get("source_type") not in ALLOWED_SOURCE_TYPES:
        return _stopped(
            request,
            "live_callable_descriptor_source_unclear",
            "live_callable_descriptor.source_type must be a documented runtime-provided source.",
        )
    if descriptor.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "target_action_mismatch",
            "live_callable_descriptor.target_action must be create-thread.",
        )
    if descriptor.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "live_callable_descriptor.tool_or_api must be create_thread.",
        )
    if _as_bool(descriptor.get("documented_callable")) is not True:
        return _stopped(
            request,
            "live_callable_descriptor_source_unclear",
            "live_callable_descriptor.documented_callable must be true.",
        )
    if _as_bool(descriptor.get("runtime_provided")) is not True:
        return _stopped(
            request,
            "live_callable_descriptor_source_unclear",
            "live_callable_descriptor.runtime_provided must be true.",
        )
    if _as_bool(descriptor.get("caller_supplied")) is not True:
        return _stopped(
            request,
            "live_callable_descriptor_source_unclear",
            "live_callable_descriptor.caller_supplied must be true.",
        )
    if _as_bool(descriptor.get("live_desktop_runtime")) is not True:
        return _stopped(
            request,
            "live_callable_descriptor_source_unclear",
            "live_callable_descriptor.live_desktop_runtime must be true for this smoke.",
        )
    if _as_bool(descriptor.get("external_write_authorized")) is not False:
        return _stopped(
            request,
            "external_write_request",
            "live_callable_descriptor.external_write_authorized must remain false.",
        )
    return None


def _validate_smoke_prompt(request: dict[str, Any]) -> dict[str, Any] | None:
    body = _get(request, "smoke_prompt.body")
    if not isinstance(body, str):
        return _stopped(request, "validation_error", "smoke_prompt.body must be a string.")
    lower_body = body.lower()
    missing_phrases = [
        phrase for phrase in REQUIRED_PROMPT_BOUNDARY_PHRASES if phrase not in lower_body
    ]
    if missing_phrases:
        return _stopped(
            request,
            "smoke_prompt_boundary_missing",
            "smoke_prompt.body is missing read-only audit boundary phrase(s): "
            + ", ".join(missing_phrases),
        )
    return None


def _call_payload(request: dict[str, Any]) -> dict[str, Any]:
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
            "summary": _get(request, "smoke_prompt.summary"),
            "body": _get(request, "smoke_prompt.body"),
        },
        "execution_context": {
            "live_smoke": True,
            "read_only_audit_prompt": True,
            "external_write_authorized": False,
            "audit_task_completion_required": False,
        },
    }


def _classify_callable_failure(
    request: dict[str, Any], failure_class: str, message: str
) -> dict[str, Any]:
    response = _stopped(request, failure_class, message)
    response["result"]["permission_or_auth_failure"] = {
        "failure_class": failure_class,
        "message": message,
    }
    return response


def _validate_runtime_response(request: dict[str, Any], runtime_response: Any) -> dict[str, Any]:
    if not isinstance(runtime_response, dict):
        return _stopped(
            request,
            "runtime_response_shape_invalid",
            "create_thread callable response must be a JSON object.",
        )

    forbidden_hits = _forbidden_source_hits(runtime_response)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s) in create_thread response: "
            + ", ".join(forbidden_hits),
        )

    if runtime_response.get("status") in {"auth-failed", "permission-denied"}:
        return _classify_callable_failure(
            request,
            "runtime_permission_or_auth_failure",
            str(runtime_response.get("message") or runtime_response.get("status")),
        )

    private_runtime_state_read = runtime_response.get("private_runtime_state_read", False)
    if _as_bool(private_runtime_state_read) is not False:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "create_thread response must omit private_runtime_state_read or report false.",
        )
    external_write_performed = runtime_response.get("external_write_performed", False)
    if _as_bool(external_write_performed) is not False:
        return _stopped(
            request,
            "external_write_request",
            "create_thread response must omit external_write_performed or report false.",
        )

    returned_status = runtime_response.get("status")
    thread_id = runtime_response.get("threadId")
    if thread_id is None:
        thread_id = runtime_response.get("thread_id")
    pending_worktree_id = runtime_response.get("pendingWorktreeId")
    if pending_worktree_id is None:
        pending_worktree_id = runtime_response.get("pending_worktree_id")

    has_thread_id = isinstance(thread_id, str) and bool(thread_id.strip())
    has_pending_worktree_id = isinstance(pending_worktree_id, str) and bool(
        pending_worktree_id.strip()
    )
    if not has_thread_id and not has_pending_worktree_id:
        return _stopped(
            request,
            "returned_thread_or_pending_worktree_id_invalid",
            "create_thread response must include threadId, thread_id, or pendingWorktreeId.",
        )
    if has_thread_id and returned_status is not None and returned_status not in THREAD_ID_STATUSES:
        return _stopped(
            request,
            "returned_status_invalid",
            "thread_id responses must return status one of: "
            + ", ".join(sorted(THREAD_ID_STATUSES)),
        )
    if (
        not has_thread_id
        and has_pending_worktree_id
        and returned_status is not None
        and returned_status not in PENDING_WORKTREE_STATUSES
    ):
        return _stopped(
            request,
            "returned_status_invalid",
            "pendingWorktreeId responses must omit status or return queued.",
        )

    response = _base_response(request, "ready")
    response["failure_class"] = None
    response["runtime_call_performed"] = True
    response["desktop_runtime_call_performed"] = True
    response["execution_kind"] = "runtime-provided-documented-create-thread-callable"
    response["later_runtime_path_blocked"] = False
    response["result"]["returned_thread_id"] = thread_id.strip() if has_thread_id else None
    response["result"]["pendingWorktreeId"] = (
        pending_worktree_id.strip() if has_pending_worktree_id else None
    )
    response["result"]["returned_status"] = returned_status
    response["result"]["prompt_delivered"] = True
    response["result"]["audit_task_completed"] = False
    response["result"]["audit_task_completion_required"] = False
    response["result"]["residual_risk"] = [
        "The smoke verified thread creation and prompt delivery only.",
        "The read-only audit task may still be pending or incomplete.",
        "No GitHub comments, reviews, commits, pushes, PRs, merges, labels, status changes, or remediation steps are authorized by this result.",
    ]
    return response


def run_create_thread_live_smoke(
    request: dict[str, Any],
    create_thread_callable: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and run one documented create_thread live smoke call."""

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")

    runtime_source_evidence = {
        "live_callable_descriptor": request.get("live_callable_descriptor"),
        "runtime_source_hints": request.get("runtime_source_hints"),
    }
    forbidden_hits = _forbidden_source_hits(runtime_source_evidence)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
        )

    missing = [path for path in _required_paths() if _is_missing(_get(request, path))]
    if missing:
        if "authorization.human_live_smoke_marker" in missing:
            return _fallback(
                request,
                "human_live_smoke_marker_missing",
                "Missing exact human-approved live smoke marker.",
            )
        if "live_callable_descriptor" in missing:
            return _stopped(
                request,
                "live_callable_descriptor_malformed",
                "live_callable_descriptor must be a JSON object.",
            )
        return _stopped(request, "validation_error", "Missing required field(s): " + ", ".join(missing))

    validations = (
        _validate_exact_action,
        _validate_safety_boundaries,
        _validate_human_marker,
        _validate_call_site_rechecks,
        _validate_descriptor,
        _validate_smoke_prompt,
    )
    for validation in validations:
        response = validation(request)
        if response is not None:
            return response

    if create_thread_callable is None:
        return _fallback(
            request,
            "live_create_thread_callable_missing",
            "No runtime-provided documented create_thread callable was injected; CLI/default/tests are non-live.",
        )

    payload = _call_payload(request)
    try:
        runtime_response = create_thread_callable(payload)
    except CreateThreadLiveSmokeAuthError as exc:
        return _classify_callable_failure(request, "runtime_auth_failure", str(exc))
    except CreateThreadLiveSmokePermissionError as exc:
        return _classify_callable_failure(request, "runtime_permission_failure", str(exc))

    return _validate_runtime_response(request, runtime_response)


def example_request() -> dict[str, Any]:
    prompt = build_read_only_audit_smoke_prompt()
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "target": {
            "repo": "owner/name",
            "remote": "https://github.com/owner/name.git",
            "branch": "codex/example",
            "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
        },
        "smoke_prompt": prompt,
        "boundaries": {
            "external_writes_blocked": True,
            "runtime_call_performed": False,
            "desktop_private_runtime_state_read": False,
        },
        "authorization": {
            "authorized_runtime_action": TARGET_ACTION,
            "human_live_smoke_marker": HUMAN_LIVE_SMOKE_MARKER,
            "human_live_smoke_scope": HUMAN_LIVE_SMOKE_SCOPE,
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
        "live_callable_descriptor": {
            "descriptor_type": "runtime-provided-documented-create-thread-callable",
            "source_type": "active-tool-list-excerpt",
            "target_action": TARGET_ACTION,
            "tool_or_api": TOOL_OR_API,
            "documented_callable": True,
            "runtime_provided": True,
            "caller_supplied": True,
            "live_desktop_runtime": True,
            "external_write_authorized": False,
            "source_excerpt": "Documented active tool list entry for create_thread.",
            "last_verified": "2026-06-06",
        },
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
        response = run_create_thread_live_smoke(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
