#!/usr/bin/env python3
"""Desktop runtime wrapper V1 request planner.

This helper is intentionally non-state-changing. It validates a prepared
thread-action request, classifies the safest outcome, and emits structured
evidence or a CLI-compatible fallback prompt. It never opens, forks, continues,
messages, or reads a Desktop thread.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from typing import Any


WRAPPER_VERSION = "0.1.0"
REQUESTED_ACTION = "plan-thread-action"

SUPPORTED_TARGET_ACTIONS = {
    "create-thread": "create_thread",
    "fork-thread": "fork_thread",
    "send-message": "send_message_to_thread",
    "read-thread": "read_thread",
}

STATE_CHANGING_TARGET_ACTIONS = {
    "create-thread",
    "fork-thread",
    "send-message",
}

CAPABILITY_SOURCES = {
    "active tool list",
    "connector metadata",
    "official documentation",
    "runtime-reported schema",
    "installed plugin metadata",
    "documented API",
}

UNAVAILABLE_CAPABILITY_SOURCES = {
    "unavailable",
    "not available",
    "missing capability",
}

PRIVATE_RUNTIME_HINTS = {
    "desktop private runtime state": "Desktop private runtime state hint",
    "sqlite": "Desktop private runtime database hint",
    "database": "Desktop private runtime database hint",
    "logs": "Desktop private runtime log hint",
    "sessions": "Desktop private runtime session hint",
    "auth file": "Desktop private runtime auth-file hint",
    "auth files": "Desktop private runtime auth-file hint",
    "caches": "Desktop private runtime cache hint",
    "app state": "Desktop private runtime app-state hint",
    "local runtime directory": "Desktop private runtime directory hint",
    "local runtime directories": "Desktop private runtime directory hint",
    "private runtime file": "Desktop private runtime file hint",
    "private runtime files": "Desktop private runtime file hint",
    "unpublished endpoint": "unpublished Desktop endpoint hint",
    "ui scraping": "Desktop UI scraping hint",
    "reverse-engineered": "reverse-engineered Desktop internals hint",
    "daemon": "daemon or background service hint",
    "sidecar": "sidecar service hint",
    "background service": "background service hint",
    "app-server client": "app-server client hint",
}

EXTERNAL_WRITE_TERMS = {
    "commit",
    "push",
    "pr creation",
    "pull request creation",
    "platform comment",
    "review submission",
    "merge",
    "deploy",
    "destructive action",
}

PRIVATE_RUNTIME_REQUEST_VERBS = {
    "access",
    "discover",
    "infer",
    "inspect",
    "load",
    "open",
    "query",
    "read",
    "scrape",
    "use",
}

NEGATION_MARKERS = {
    "blocked",
    "do not",
    "don't",
    "forbidden",
    "must not",
    "never",
    "out of scope",
    "should not",
    "stop before",
    "without",
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


def _contains_any(texts: list[str], terms: set[str] | dict[str, str]) -> list[str]:
    hits: list[str] = []
    for text in texts:
        lower = text.lower()
        for term in terms:
            if term in lower and term not in hits:
                hits.append(term)
    return hits


def _contains_private_runtime_request(texts: list[str]) -> list[str]:
    hits: list[str] = []
    for text in texts:
        lower = text.lower()
        for term in PRIVATE_RUNTIME_HINTS:
            start = lower.find(term)
            while start != -1:
                context = lower[max(0, start - 80):start]
                has_request_verb = any(verb in context.split() for verb in PRIVATE_RUNTIME_REQUEST_VERBS)
                is_negated = any(marker in context for marker in NEGATION_MARKERS)
                if has_request_verb and not is_negated and term not in hits:
                    hits.append(term)
                start = lower.find(term, start + len(term))
    return hits


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def _required_paths(target_action: str | None) -> list[str]:
    required = [
        "action",
        "target_action",
        "runtime_contract.tool_or_api",
        "runtime_contract.underlying_contract_version",
        "runtime_contract.capability_source",
        "runtime_contract.last_verified",
        "runtime_contract.wrapper_version",
        "target.repo",
        "target.remote",
        "target.branch",
        "prompt.summary",
        "prompt.body",
        "boundaries.external_writes_blocked",
        "authorization.thread_action_authorized",
        "authorization.external_write_authorized",
    ]
    if target_action in {"fork-thread", "send-message", "read-thread"}:
        required.append("target.thread_id")
    return required


def _fallback_prompt(request: dict[str, Any], reason: str) -> str:
    target_action = _get(request, "target_action") or "unknown"
    repo = _get(request, "target.repo") or "unknown repo"
    branch = _get(request, "target.branch") or "unknown branch"
    summary = _get(request, "prompt.summary") or "No summary provided."
    body = _get(request, "prompt.body") or "No prepared prompt body provided."

    return "\n".join(
        [
            "No Desktop thread was opened/forked/continued/messaged/read by this planner.",
            "",
            "CLI-compatible fallback prompt:",
            "Use the prompt below in a separate Codex session or in a Codex Desktop thread when Desktop is intentionally selected, then return the diff and verification notes here for integration review.",
            "",
            f"Fallback reason: {reason}",
            f"Requested target action: {target_action}",
            f"Repository: {repo}",
            f"Branch: {branch}",
            "",
            "Boundary:",
            "- This fallback is based only on durable request fields supplied to the planner.",
            "- Keep commit, push, PR creation, platform comments, review submissions, merge, deploy, destructive actions, and other external writes blocked unless explicitly authorized later.",
            "- Do not use Desktop private runtime state, unpublished endpoints, UI scraping, daemons, sidecars, background services, or app-server clients.",
            "",
            "Prepared prompt summary:",
            summary,
            "",
            "Prepared prompt body:",
            body,
        ]
    )


def _base_response(request: dict[str, Any], status: str) -> dict[str, Any]:
    target_action = _get(request, "target_action")
    contract_version = _get(request, "runtime_contract.underlying_contract_version")
    tool_or_api = _get(request, "runtime_contract.tool_or_api")
    wrapper_version = _get(request, "runtime_contract.wrapper_version") or WRAPPER_VERSION
    required = _required_paths(target_action)
    optional_used = [
        path
        for path in ["target.expected_head", "target.thread_id", "runtime_contract.available"]
        if not _is_missing(_get(request, path))
    ]

    return {
        "status": status,
        "requested_action": _get(request, "action") or REQUESTED_ACTION,
        "target_action": target_action,
        "runtime_contract": {
            "tool_or_api": tool_or_api,
            "underlying_contract_version": contract_version,
            "capability_source": _get(request, "runtime_contract.capability_source"),
            "last_verified": _get(request, "runtime_contract.last_verified"),
            "wrapper_mapping": f"wrapper {wrapper_version} -> {tool_or_api} {contract_version}",
        },
        "request_shape_relied_on": {
            "required": required,
            "optional_used": optional_used,
        },
        "response_shape_relied_on": {
            "required": ["status"],
            "fallback_fields": ["paste_ready_prompt", "stop_reason"],
        },
        "result": {
            "paste_ready_prompt": None,
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
    response["result"]["residual_risk"] = residual_risk or []
    return response


def _fallback(
    request: dict[str, Any],
    failure_class: str,
    reason: str,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback")
    response["failure_class"] = failure_class
    response["result"]["paste_ready_prompt"] = _fallback_prompt(request, reason)
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or []
    return response


def plan_request(request: dict[str, Any]) -> dict[str, Any]:
    """Classify a prepared Desktop thread-action request.

    The planner performs no Desktop runtime calls. The returned status is one of
    dry-run, fallback, or stopped.
    """

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")

    target_action = _get(request, "target_action")
    missing = [path for path in _required_paths(target_action) if _is_missing(_get(request, path))]
    if missing:
        return _stopped(
            request,
            "validation_error",
            "Missing required field(s): " + ", ".join(missing),
        )

    if _get(request, "action") != REQUESTED_ACTION:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported action: {_get(request, 'action')}",
        )

    if target_action not in SUPPORTED_TARGET_ACTIONS:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported target_action: {target_action}",
        )

    last_verified = _get(request, "runtime_contract.last_verified")
    if not _valid_iso_date(last_verified):
        return _stopped(
            request,
            "missing_contract_evidence",
            "runtime_contract.last_verified must be YYYY-MM-DD.",
        )

    expected_tool = SUPPORTED_TARGET_ACTIONS[target_action]
    tool_or_api = _get(request, "runtime_contract.tool_or_api")
    if tool_or_api != expected_tool:
        return _stopped(
            request,
            "missing_contract_evidence",
            f"runtime_contract.tool_or_api must be {expected_tool} for {target_action}.",
        )

    capability_source = str(_get(request, "runtime_contract.capability_source")).strip()
    capability_source_lower = capability_source.lower()
    capability_available = _as_bool(_get(request, "runtime_contract.available"))
    capability_missing = (
        capability_available is False
        or capability_source_lower in UNAVAILABLE_CAPABILITY_SOURCES
    )
    if not capability_missing and capability_source not in CAPABILITY_SOURCES:
        return _stopped(
            request,
            "missing_contract_evidence",
            "runtime_contract.capability_source is not a recognized verifiable source.",
        )

    contract_version = _get(request, "runtime_contract.underlying_contract_version")

    external_writes_blocked = _as_bool(_get(request, "boundaries.external_writes_blocked"))
    external_write_authorized = _as_bool(_get(request, "authorization.external_write_authorized"))
    if external_writes_blocked is not True:
        return _stopped(
            request,
            "external_write_request",
            "boundaries.external_writes_blocked must be true for this first slice.",
        )
    if external_write_authorized is not False:
        return _stopped(
            request,
            "external_write_request",
            "authorization.external_write_authorized must be false for this first slice.",
        )

    in_scope_text = _iter_strings(_get(request, "boundaries.in_scope"))
    external_hits = _contains_any(in_scope_text, EXTERNAL_WRITE_TERMS)
    if external_hits:
        return _stopped(
            request,
            "external_write_request",
            "External-write term(s) found in boundaries.in_scope: " + ", ".join(external_hits),
        )

    prompt_text = []
    prompt_text.extend(_iter_strings(_get(request, "prompt.summary")))
    prompt_text.extend(_iter_strings(_get(request, "prompt.body")))
    private_hits = _contains_any(in_scope_text, PRIVATE_RUNTIME_HINTS)
    private_hits.extend(_contains_private_runtime_request(prompt_text))
    if private_hits:
        descriptions = sorted({PRIVATE_RUNTIME_HINTS[hit] for hit in private_hits})
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): " + ", ".join(descriptions),
        )

    thread_action_authorized = _as_bool(_get(request, "authorization.thread_action_authorized"))
    if target_action in STATE_CHANGING_TARGET_ACTIONS and thread_action_authorized is not True:
        return _fallback(
            request,
            "state_changing_thread_action_not_authorized",
            "State-changing Desktop thread action is not authorized.",
            ["Planner generated a fallback prompt instead of relying on Desktop thread state."],
        )

    if capability_missing:
        return _fallback(
            request,
            "missing_capability",
            "The target runtime thread tool or documented API is unavailable.",
            ["Runtime capability was not verified as present."],
        )

    response = _base_response(request, "dry-run")
    response["failure_class"] = None
    response["result"]["residual_risk"] = [
        "This first slice does not call a Desktop thread tool.",
        "Compatibility evidence still needs re-checking before any future runtime action.",
    ]
    return response


def example_request() -> dict[str, Any]:
    return {
        "action": REQUESTED_ACTION,
        "target_action": "create-thread",
        "runtime_contract": {
            "tool_or_api": "create_thread",
            "underlying_contract_version": "version unavailable",
            "capability_source": "active tool list",
            "last_verified": _dt.date.today().isoformat(),
            "wrapper_version": WRAPPER_VERSION,
        },
        "target": {
            "repo": "owner/name",
            "remote": "origin URL",
            "branch": "branch-name",
            "expected_head": "optional commit SHA",
        },
        "prompt": {
            "summary": "Short prepared prompt summary",
            "body": "Prepared prompt or message body",
        },
        "boundaries": {
            "in_scope": ["docs/runtime-adapter-v2.md"],
            "out_of_scope": [".work/", "Desktop private runtime state"],
            "external_writes_blocked": True,
        },
        "authorization": {
            "thread_action_authorized": False,
            "external_write_authorized": False,
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
        response = plan_request(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
