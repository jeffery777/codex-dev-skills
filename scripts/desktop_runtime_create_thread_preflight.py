#!/usr/bin/env python3
"""Create-thread runtime-call preflight helper.

This helper is intentionally non-state-changing. It checks whether caller-
supplied evidence is ready for a future, separately approved ``create_thread``
runtime call. It never calls Desktop thread tools and never reads Desktop
private runtime state.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from typing import Any


PREFLIGHT_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "preflight-create-thread-runtime-call"
TARGET_ACTION = "create-thread"
TOOL_OR_API = "create_thread"
EXPECTED_CLASSIFICATION = "state-changing"

CAPABILITY_SOURCES = {
    "active tool list",
    "connector metadata",
    "documented API",
    "installed plugin metadata",
    "official documentation",
    "runtime-reported schema",
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
    if isinstance(value, list):
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


def _private_runtime_descriptions(hits: list[str]) -> list[str]:
    return sorted({PRIVATE_RUNTIME_HINTS[hit] for hit in hits})


def _valid_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = _dt.date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        strings.append(item.strip())
    return strings


def _required_paths() -> list[str]:
    return [
        "requested_action",
        "target_action",
        "target.repo",
        "target.remote",
        "target.branch",
        "target.expected_head",
        "prompt.summary",
        "prompt.body",
        "boundaries.external_writes_blocked",
        "authorization.thread_action_authorized",
        "authorization.authorized_thread_action",
        "authorization.external_write_authorized",
    ]


def _fallback_prompt(request: dict[str, Any], reason: str) -> str:
    repo = _get(request, "target.repo") or "unknown repo"
    remote = _get(request, "target.remote") or "unknown remote"
    branch = _get(request, "target.branch") or "unknown branch"
    expected_head = _get(request, "target.expected_head") or "unknown expected head"
    summary = _get(request, "prompt.summary") or "No summary provided."
    body = _get(request, "prompt.body") or "No prepared prompt body provided."

    return "\n".join(
        [
            "No Desktop thread was opened, created, forked, messaged, or read by this preflight helper.",
            "",
            "Paste-ready fallback prompt:",
            "Use the prompt below in a separate Codex session or in a Codex Desktop thread when Desktop is intentionally selected, then return the diff and verification notes here for integration review.",
            "",
            f"Fallback reason: {reason}",
            "Requested target action: create-thread",
            f"Repository: {repo}",
            f"Remote: {remote}",
            f"Branch: {branch}",
            f"Expected head: {expected_head}",
            "",
            "Boundary:",
            "- This fallback is based only on durable request fields supplied to the helper.",
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


def _selected_capability(request: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    evidence = request.get("capability_evidence")
    if not isinstance(evidence, dict):
        return "fallback", None

    status = evidence.get("status")
    if status in {"unavailable", "fallback"}:
        return "fallback", None
    if status == "stopped":
        return "stopped", None
    if status != "available":
        return "fallback", None

    capabilities = evidence.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return "fallback", None

    for capability in capabilities:
        if isinstance(capability, dict) and capability.get("action") == TARGET_ACTION:
            return "available", capability
    return "fallback", None


def _base_response(
    request: dict[str, Any],
    status: str,
    capability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    comparison = request.get("contract_comparison")
    if not isinstance(comparison, dict):
        comparison = {}

    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "preflight_helper_version": PREFLIGHT_HELPER_VERSION,
        "runtime_call_performed": False,
        "readiness_meaning": (
            "ready means evidence is ready for a future separately approved "
            "runtime call; it does not mean create_thread was called or that "
            "commit, push, PR creation, merge, or other external writes are authorized."
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
        "contract_evidence": {
            "comparison_status": comparison.get("status"),
            "comparison_helper_version": comparison.get("comparison_helper_version"),
            "compared_fields": _get(comparison, "contract_comparison.compared_fields"),
        },
        "capability_evidence": {
            "status": _get(request, "capability_evidence.status"),
            "tool_or_api": None if capability is None else capability.get("tool_or_api"),
            "classification": None if capability is None else capability.get("classification"),
            "required_request_fields": None
            if capability is None
            else capability.get("required_request_fields"),
            "minimum_response_fields": None
            if capability is None
            else capability.get("minimum_response_fields"),
            "capability_source": None if capability is None else capability.get("capability_source"),
            "contract_version": None if capability is None else capability.get("contract_version"),
            "last_verified": None if capability is None else capability.get("last_verified"),
        },
        "authorization_evidence": {
            "thread_action_authorized": _get(request, "authorization.thread_action_authorized"),
            "authorized_thread_action": _get(request, "authorization.authorized_thread_action"),
            "external_write_authorized": _get(request, "authorization.external_write_authorized"),
            "external_writes_blocked": _get(request, "boundaries.external_writes_blocked"),
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
    capability: dict[str, Any] | None = None,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "stopped", capability)
    response["failure_class"] = failure_class
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or []
    return response


def _fallback(
    request: dict[str, Any],
    failure_class: str,
    reason: str,
    capability: dict[str, Any] | None = None,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback", capability)
    response["failure_class"] = failure_class
    response["result"]["paste_ready_prompt"] = _fallback_prompt(request, reason)
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or []
    return response


def _forbidden_evidence_hits(request: dict[str, Any]) -> list[str]:
    hits = []
    hits.extend(_contains_any(_iter_strings(request.get("capability_evidence")), PRIVATE_RUNTIME_HINTS))
    hits.extend(_contains_any(_iter_strings(request.get("contract_comparison")), PRIVATE_RUNTIME_HINTS))
    hits.extend(_contains_any(_iter_strings(_get(request, "boundaries.in_scope")), PRIVATE_RUNTIME_HINTS))

    prompt_text = []
    prompt_text.extend(_iter_strings(_get(request, "prompt.summary")))
    prompt_text.extend(_iter_strings(_get(request, "prompt.body")))
    hits.extend(_contains_private_runtime_request(prompt_text))
    return hits


def _validate_capability_record(
    request: dict[str, Any],
    capability: dict[str, Any],
) -> dict[str, Any] | None:
    if capability.get("tool_or_api") != TOOL_OR_API:
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "create-thread capability must use create_thread.",
            capability,
        )
    if capability.get("classification") != EXPECTED_CLASSIFICATION:
        return _stopped(
            request,
            "classification_mismatch",
            "create-thread capability classification must be state-changing.",
            capability,
        )

    required_request_fields = _string_list(capability.get("required_request_fields"))
    minimum_response_fields = _string_list(capability.get("minimum_response_fields"))
    if required_request_fields is None or minimum_response_fields is None:
        return _stopped(
            request,
            "unclear_contract_shape",
            "create-thread request or response evidence is unclear.",
            capability,
        )
    if capability.get("capability_source") not in CAPABILITY_SOURCES:
        return _stopped(
            request,
            "missing_contract_evidence",
            "create-thread capability_source is not a recognized documented source.",
            capability,
        )
    if _is_missing(capability.get("contract_version")) or not _valid_iso_date(capability.get("last_verified")):
        return _stopped(
            request,
            "missing_contract_evidence",
            "create-thread capability requires contract_version and YYYY-MM-DD last_verified.",
            capability,
        )
    return None


def _validate_compatible_comparison(
    request: dict[str, Any],
    capability: dict[str, Any],
) -> dict[str, Any] | None:
    comparison = request.get("contract_comparison")
    if not isinstance(comparison, dict):
        return _fallback(
            request,
            "comparison_unavailable",
            "Compatible contract comparison evidence is unavailable.",
            capability,
            ["Run the contract comparison helper before a future runtime call."],
        )

    status = comparison.get("status")
    if status == "fallback":
        return _fallback(
            request,
            "comparison_unavailable",
            "Contract comparison helper returned fallback.",
            capability,
            ["Use the paste-ready prompt or provide compatible comparison evidence."],
        )
    if status == "stopped":
        return _stopped(
            request,
            comparison.get("failure_class") or "contract_comparison_stopped",
            _get(comparison, "result.stop_reason") or "Contract comparison stopped.",
            capability,
        )
    if status != "compatible":
        return _stopped(
            request,
            "contract_not_compatible",
            "Contract comparison status must be compatible.",
            capability,
        )

    old_contract = _get(comparison, "contract_comparison.old_contract")
    new_capability = _get(comparison, "contract_comparison.new_capability")
    if not isinstance(old_contract, dict) or not isinstance(new_capability, dict):
        return _stopped(
            request,
            "unclear_contract_shape",
            "Contract comparison request/response evidence is unclear.",
            capability,
        )

    compared_fields = _get(comparison, "contract_comparison.compared_fields")
    if _string_list(compared_fields) is None:
        return _stopped(
            request,
            "unclear_contract_shape",
            "Contract comparison compared_fields evidence is unclear.",
            capability,
        )

    for record_name, record in (("old_contract", old_contract), ("new_capability", new_capability)):
        if record.get("action") != TARGET_ACTION:
            return _stopped(
                request,
                "contract_action_mismatch",
                f"{record_name}.action must be create-thread.",
                capability,
            )
        if record.get("tool_or_api") != TOOL_OR_API:
            return _stopped(
                request,
                "tool_or_api_mismatch",
                f"{record_name}.tool_or_api must be create_thread.",
                capability,
            )
        if record.get("classification") != EXPECTED_CLASSIFICATION:
            return _stopped(
                request,
                "classification_mismatch",
                f"{record_name}.classification must be state-changing.",
                capability,
            )
        if _string_list(record.get("required_request_fields")) is None:
            return _stopped(
                request,
                "unclear_contract_shape",
                f"{record_name}.required_request_fields evidence is unclear.",
                capability,
            )
        if _string_list(record.get("minimum_response_fields")) is None:
            return _stopped(
                request,
                "unclear_contract_shape",
                f"{record_name}.minimum_response_fields evidence is unclear.",
                capability,
            )

    if old_contract.get("tool_or_api") != new_capability.get("tool_or_api"):
        return _stopped(
            request,
            "tool_or_api_mismatch",
            "Contract comparison is marked compatible but tool/API evidence differs.",
            capability,
        )
    if old_contract.get("classification") != new_capability.get("classification"):
        return _stopped(
            request,
            "classification_mismatch",
            "Contract comparison is marked compatible but classification evidence differs.",
            capability,
        )
    if old_contract.get("required_request_fields") != new_capability.get("required_request_fields"):
        return _stopped(
            request,
            "request_shape_changed",
            "Contract comparison is marked compatible but required request fields differ.",
            capability,
        )
    if old_contract.get("minimum_response_fields") != new_capability.get("minimum_response_fields"):
        return _stopped(
            request,
            "response_shape_changed",
            "Contract comparison is marked compatible but minimum response fields differ.",
            capability,
        )

    for field in (
        "tool_or_api",
        "classification",
        "required_request_fields",
        "minimum_response_fields",
    ):
        if capability.get(field) != new_capability.get(field):
            return _stopped(
                request,
                "contract_evidence_mismatch",
                f"Selected capability evidence does not match comparison new_capability.{field}.",
                capability,
            )
    return None


def preflight_create_thread(request: dict[str, Any]) -> dict[str, Any]:
    """Classify create_thread readiness evidence without calling the runtime."""

    if not isinstance(request, dict):
        return _stopped({}, "validation_error", "Request must be a JSON object.")

    forbidden_hits = _forbidden_evidence_hits(request)
    if forbidden_hits:
        return _stopped(
            request,
            "forbidden_private_runtime_state",
            "Forbidden Desktop runtime source hint(s): "
            + ", ".join(_private_runtime_descriptions(forbidden_hits)),
        )

    external_writes_blocked = _as_bool(_get(request, "boundaries.external_writes_blocked"))
    external_write_authorized = _as_bool(_get(request, "authorization.external_write_authorized"))
    if external_writes_blocked is not None and external_writes_blocked is not True:
        return _stopped(
            request,
            "external_write_request",
            "boundaries.external_writes_blocked must remain true.",
        )
    if external_write_authorized is not None and external_write_authorized is not False:
        return _stopped(
            request,
            "external_write_request",
            "authorization.external_write_authorized must remain false.",
        )

    in_scope_external_hits = _contains_any(
        _iter_strings(_get(request, "boundaries.in_scope")),
        EXTERNAL_WRITE_TERMS,
    )
    if in_scope_external_hits:
        return _stopped(
            request,
            "external_write_request",
            "External-write term(s) found in boundaries.in_scope: "
            + ", ".join(in_scope_external_hits),
        )

    missing = [path for path in _required_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped(
            request,
            "validation_error",
            "Missing required field(s): " + ", ".join(missing),
        )

    if request.get("requested_action") != REQUESTED_ACTION:
        return _stopped(
            request,
            "validation_error",
            f"Unsupported requested_action: {request.get('requested_action')}",
        )
    if request.get("target_action") != TARGET_ACTION:
        return _stopped(
            request,
            "validation_error",
            "Only create-thread preflight is supported by this helper.",
        )

    selection_status, capability = _selected_capability(request)
    if selection_status == "fallback":
        return _fallback(
            request,
            "missing_capability",
            "Normalized create-thread capability evidence is unavailable.",
            None,
            ["Use the paste-ready prompt or provide documented normalized capability evidence."],
        )
    if selection_status == "stopped":
        return _stopped(
            request,
            "missing_contract_evidence",
            "Normalized capability evidence is stopped.",
        )
    if capability is None:
        return _fallback(request, "missing_capability", "create-thread capability is missing.")

    capability_validation = _validate_capability_record(request, capability)
    if capability_validation is not None:
        return capability_validation

    comparison_validation = _validate_compatible_comparison(request, capability)
    if comparison_validation is not None:
        return comparison_validation

    thread_action_authorized = _as_bool(_get(request, "authorization.thread_action_authorized"))
    authorized_thread_action = _get(request, "authorization.authorized_thread_action")
    if thread_action_authorized is not True:
        return _fallback(
            request,
            "thread_action_not_authorized",
            "Exact create-thread runtime action is not authorized.",
            capability,
            ["Preflight generated a fallback prompt instead of treating authorization as implied."],
        )
    if authorized_thread_action != TARGET_ACTION:
        return _stopped(
            request,
            "thread_action_authorization_unclear",
            "authorization.authorized_thread_action must be create-thread.",
            capability,
        )

    response = _base_response(request, "ready", capability)
    response["failure_class"] = None
    response["result"]["residual_risk"] = [
        "This helper did not call create_thread or any Desktop thread tool.",
        "Capability and comparison evidence are caller-supplied metadata only.",
        "A future runtime call still requires separate approval at the call site.",
        "Commit, push, PR creation, merge, and other external writes remain unauthorized.",
    ]
    return response


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    capability = {
        "action": TARGET_ACTION,
        "tool_or_api": TOOL_OR_API,
        "classification": EXPECTED_CLASSIFICATION,
        "required_request_fields": ["prompt", "target"],
        "optional_request_fields": ["model", "thinking"],
        "minimum_response_fields": ["status", "threadId or thread_id or pendingWorktreeId"],
        "error_response_fields": ["message"],
        "capability_source": "active tool list",
        "contract_version": "version unavailable",
        "last_verified": today,
        "discovery_helper_version": "0.1.0",
    }
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": TARGET_ACTION,
        "target": {
            "repo": "owner/name",
            "remote": "https://github.com/owner/name.git",
            "branch": "codex/example",
            "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
        },
        "prompt": {
            "summary": "Prepare a bounded Desktop thread prompt.",
            "body": "Read repo files first, do the scoped task, run tests, and report evidence.",
        },
        "capability_evidence": {
            "status": "available",
            "capabilities": [capability],
        },
        "contract_comparison": {
            "status": "compatible",
            "requested_action": "compare-runtime-contract-evidence",
            "target_action": TARGET_ACTION,
            "comparison_helper_version": "0.1.0",
            "failure_class": None,
            "contract_comparison": {
                "compared_fields": [
                    "action",
                    "tool_or_api",
                    "classification",
                    "required_request_fields",
                    "minimum_response_fields",
                ],
                "old_contract": capability,
                "new_capability": capability,
            },
            "result": {
                "stop_reason": None,
                "residual_risk": [
                    "Comparison used caller-supplied evidence only.",
                    "This helper did not call or authorize Desktop thread tools.",
                ],
            },
        },
        "boundaries": {
            "in_scope": ["docs/runtime-adapter-v2.md"],
            "out_of_scope": [".work/", "Desktop private runtime state"],
            "external_writes_blocked": True,
        },
        "authorization": {
            "thread_action_authorized": True,
            "authorized_thread_action": TARGET_ACTION,
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
        response = preflight_create_thread(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
