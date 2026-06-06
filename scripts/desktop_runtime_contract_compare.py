#!/usr/bin/env python3
"""Desktop runtime wrapper V1 contract comparison helper.

This helper is intentionally non-state-changing. It compares an older wrapper
contract evidence record with newer normalized capability evidence that a caller
has already supplied. It never calls Desktop thread tools and never reads
Desktop private runtime state.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from typing import Any


COMPARISON_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "compare-runtime-contract-evidence"

CAPABILITY_SOURCES = {
    "active tool list",
    "connector metadata",
    "documented API",
    "installed plugin metadata",
    "official documentation",
    "runtime-reported schema",
}

FORBIDDEN_SOURCE_HINTS = {
    "desktop private runtime state": "Desktop private runtime state",
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

COMPARED_FIELDS = [
    "action",
    "tool_or_api",
    "classification",
    "required_request_fields",
    "minimum_response_fields",
]


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
        for hint, description in FORBIDDEN_SOURCE_HINTS.items():
            if hint in lower:
                hits.add(description)
    return sorted(hits)


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


def _normalized_contract(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": record.get("action"),
        "tool_or_api": record.get("tool_or_api"),
        "classification": record.get("classification"),
        "required_request_fields": record.get("required_request_fields"),
        "minimum_response_fields": record.get("minimum_response_fields"),
        "capability_source": record.get("capability_source"),
        "contract_version": record.get("contract_version"),
        "last_verified": record.get("last_verified"),
    }


def _base_response(
    request: dict[str, Any],
    status: str,
    old_contract: dict[str, Any] | None = None,
    new_capability: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": request.get("target_action"),
        "comparison_helper_version": COMPARISON_HELPER_VERSION,
        "failure_class": None,
        "contract_comparison": {
            "compared_fields": COMPARED_FIELDS,
            "old_contract": _normalized_contract(old_contract or {}),
            "new_capability": _normalized_contract(new_capability or {}),
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
    old_contract: dict[str, Any] | None = None,
    new_capability: dict[str, Any] | None = None,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "stopped", old_contract, new_capability)
    response["failure_class"] = failure_class
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or []
    return response


def _fallback(
    request: dict[str, Any],
    reason: str,
    old_contract: dict[str, Any] | None = None,
    residual_risk: list[str] | None = None,
) -> dict[str, Any]:
    response = _base_response(request, "fallback", old_contract, None)
    response["failure_class"] = "missing_capability"
    response["result"]["stop_reason"] = reason
    response["result"]["residual_risk"] = residual_risk or [
        "No compatible capability evidence was available to compare."
    ]
    return response


def _required_old_contract_paths() -> list[str]:
    return [
        "old_contract.action",
        "old_contract.tool_or_api",
        "old_contract.classification",
        "old_contract.required_request_fields",
        "old_contract.minimum_response_fields",
        "old_contract.capability_source",
        "old_contract.contract_version",
        "old_contract.last_verified",
    ]


def _validate_contract_record(
    request: dict[str, Any],
    record: dict[str, Any],
    label: str,
) -> dict[str, Any] | None:
    required_request_fields = _string_list(record.get("required_request_fields"))
    minimum_response_fields = _string_list(record.get("minimum_response_fields"))
    if required_request_fields is None:
        return _stopped(
            request,
            "missing_contract_evidence",
            f"{label}.required_request_fields must be a non-empty string list.",
            record,
        )
    if minimum_response_fields is None:
        return _stopped(
            request,
            "missing_contract_evidence",
            f"{label}.minimum_response_fields must be a non-empty string list.",
            record,
        )

    if record.get("classification") not in {"read-only", "state-changing"}:
        return _stopped(
            request,
            "missing_contract_evidence",
            f"{label}.classification must be read-only or state-changing.",
            record,
        )

    if record.get("capability_source") not in CAPABILITY_SOURCES:
        return _stopped(
            request,
            "missing_contract_evidence",
            f"{label}.capability_source is not a recognized documented source.",
            record,
        )

    if _is_missing(record.get("contract_version")) or not _valid_iso_date(record.get("last_verified")):
        return _stopped(
            request,
            "missing_contract_evidence",
            f"{label} requires contract_version and YYYY-MM-DD last_verified.",
            record,
        )

    return None


def _select_new_capability(request: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    evidence = request.get("new_capability_evidence")
    target_action = request.get("target_action")

    if not isinstance(evidence, dict):
        return "stopped", None

    status = evidence.get("status")
    if status == "unavailable":
        return "fallback", None
    if status == "stopped":
        return "stopped", None
    if status != "available":
        return "stopped", None

    capabilities = evidence.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        return "fallback", None

    for capability in capabilities:
        if isinstance(capability, dict) and capability.get("action") == target_action:
            return "available", capability
    return "fallback", None


def compare_contract_evidence(request: dict[str, Any]) -> dict[str, Any]:
    """Compare old wrapper evidence with newer normalized capability evidence."""

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

    missing = [path for path in _required_old_contract_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped(
            request,
            "validation_error",
            "Missing required field(s): " + ", ".join(missing),
        )

    old_contract = request["old_contract"]
    if not isinstance(old_contract, dict):
        return _stopped(request, "validation_error", "old_contract must be a JSON object.")

    old_validation = _validate_contract_record(request, old_contract, "old_contract")
    if old_validation is not None:
        return old_validation

    target_action = request.get("target_action")
    if target_action != old_contract.get("action"):
        return _stopped(
            request,
            "tool_or_api_changed",
            "target_action must match old_contract.action before comparison.",
            old_contract,
        )

    selection_status, new_capability = _select_new_capability(request)
    if selection_status == "fallback":
        return _fallback(
            request,
            f"New normalized capability evidence does not include available {target_action}.",
            old_contract,
            ["Use the planner fallback path or provide documented metadata from an allowed source."],
        )
    if selection_status == "stopped":
        return _stopped(
            request,
            "missing_contract_evidence",
            "new_capability_evidence must be normalized available capability evidence.",
            old_contract,
        )
    if new_capability is None:
        return _fallback(request, "New normalized capability evidence is missing.", old_contract)

    new_validation = _validate_contract_record(request, new_capability, "new_capability")
    if new_validation is not None:
        return _stopped(
            request,
            new_validation["failure_class"],
            new_validation["result"]["stop_reason"],
            old_contract,
            new_capability,
            new_validation["result"]["residual_risk"],
        )

    if old_contract.get("tool_or_api") != new_capability.get("tool_or_api"):
        return _stopped(
            request,
            "tool_or_api_changed",
            "Runtime tool/API name changed.",
            old_contract,
            new_capability,
        )

    if old_contract.get("classification") != new_capability.get("classification"):
        return _stopped(
            request,
            "classification_changed",
            "Action classification changed.",
            old_contract,
            new_capability,
        )

    if old_contract.get("required_request_fields") != new_capability.get("required_request_fields"):
        return _stopped(
            request,
            "request_shape_changed",
            "Required request fields changed.",
            old_contract,
            new_capability,
        )

    if old_contract.get("minimum_response_fields") != new_capability.get("minimum_response_fields"):
        return _stopped(
            request,
            "response_shape_changed",
            "Minimum response fields changed.",
            old_contract,
            new_capability,
        )

    response = _base_response(request, "compatible", old_contract, new_capability)
    response["result"]["residual_risk"] = [
        "Comparison used caller-supplied evidence only.",
        "This helper did not call or authorize Desktop thread tools.",
        "State-changing capabilities remain evidence only until a separately approved runtime-call path exists.",
    ]
    return response


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": "read-thread",
        "old_contract": {
            "action": "read-thread",
            "tool_or_api": "read_thread",
            "classification": "read-only",
            "required_request_fields": ["thread_id"],
            "minimum_response_fields": ["status", "thread_id"],
            "capability_source": "active tool list",
            "contract_version": "version unavailable",
            "last_verified": today,
            "wrapper_version": "0.1.0",
        },
        "new_capability_evidence": {
            "status": "available",
            "capabilities": [
                {
                    "action": "read-thread",
                    "tool_or_api": "read_thread",
                    "classification": "read-only",
                    "required_request_fields": ["thread_id"],
                    "optional_request_fields": ["include_metadata"],
                    "minimum_response_fields": ["status", "thread_id"],
                    "error_response_fields": ["message"],
                    "capability_source": "runtime-reported schema",
                    "contract_version": "version unavailable",
                    "last_verified": today,
                    "discovery_helper_version": "0.1.0",
                }
            ],
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
        response = compare_contract_evidence(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, "validation_error", f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
