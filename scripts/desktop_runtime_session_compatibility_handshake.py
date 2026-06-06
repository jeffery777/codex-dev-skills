#!/usr/bin/env python3
"""Desktop runtime wrapper V1 first-use session compatibility handshake helper.

This helper is intentionally non-state-changing. It builds a session
compatibility status from caller-supplied documented capability metadata, old
wrapper contract evidence, and an explicit caller-supplied session marker. It
then validates that status with the session compatibility status validator. It
never calls Desktop thread tools, never reads or writes a compatibility cache,
and never reads Desktop private runtime state.
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import pathlib
import sys
from typing import Any


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from desktop_runtime_capability_discovery import normalize_capability_metadata
from desktop_runtime_contract_compare import compare_contract_evidence
from desktop_runtime_session_compatibility_status import (
    SESSION_STATUS_HELPER_VERSION,
    _contract_hash,
    validate_session_compatibility_status,
)


HANDSHAKE_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "build-session-compatibility-handshake"
WRAPPER_ID_FIELDS = ("wrapper_version", "skill_package_version", "repo_commit")
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


def _wrapper_identifier(record: dict[str, Any]) -> tuple[str, Any] | None:
    for field in WRAPPER_ID_FIELDS:
        if not _is_missing(record.get(field)):
            return field, record[field]
    return None


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


def _contract_for_status(old_contract: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    new_capability = _get(comparison, "contract_comparison.new_capability")
    if isinstance(new_capability, dict) and not _is_missing(new_capability.get("tool_or_api")):
        return _normalized_contract(new_capability)
    return _normalized_contract(old_contract)


def _comparison_result_for_status(comparison: dict[str, Any]) -> str:
    status = comparison.get("status")
    if status == "compatible":
        return "compatible"
    if status == "fallback":
        return "fallback"
    return "stopped"


def _build_status_record(
    request: dict[str, Any],
    old_contract: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    expected = request["expected"]
    wrapper_field, wrapper_value = _wrapper_identifier(expected) or ("repo_commit", "unknown")
    contract_evidence = _contract_for_status(old_contract, comparison)
    schema_hash = _contract_hash(contract_evidence)
    return {
        wrapper_field: wrapper_value,
        "helper_version": SESSION_STATUS_HELPER_VERSION,
        "handshake_helper_version": HANDSHAKE_HELPER_VERSION,
        "target_action": request.get("target_action"),
        "tool_or_api": contract_evidence.get("tool_or_api"),
        "runtime_reported_version": contract_evidence.get("contract_version") or "version unavailable",
        "capability_source": contract_evidence.get("capability_source"),
        "schema_hash": schema_hash,
        "comparison_result": _comparison_result_for_status(comparison),
        "last_verified": contract_evidence.get("last_verified"),
        "session_identity": copy.deepcopy(request.get("session_identity")),
    }


def _status_validation_request(
    request: dict[str, Any],
    status_record: dict[str, Any],
) -> dict[str, Any]:
    expected = request["expected"]
    wrapper_field, wrapper_value = _wrapper_identifier(expected) or ("repo_commit", "unknown")
    status_expected = {
        wrapper_field: wrapper_value,
        "helper_version": expected.get("status_helper_version"),
        "target_action": expected.get("target_action") or request.get("target_action"),
        "tool_or_api": expected.get("tool_or_api") or status_record.get("tool_or_api"),
    }
    if not _is_missing(expected.get("schema_hash")):
        status_expected["schema_hash"] = expected.get("schema_hash")
    elif not _is_missing(expected.get("normalized_contract_evidence")):
        status_expected["normalized_contract_evidence"] = expected.get("normalized_contract_evidence")
    else:
        status_expected["schema_hash"] = status_record.get("schema_hash")
    return {
        "requested_action": "validate-session-compatibility-status",
        "expected": status_expected,
        "compatibility_status": status_record,
    }


def _summary(status: str, failure_class: str | None, primary_reason: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "failure_class": failure_class,
        "primary_reason": primary_reason,
        "recommended_next_step": (
            "Treat ready as first-use handshake evidence only; require later "
            "preflight plus separate approval before any Desktop runtime call "
            "or external write."
            if status == "ready"
            else "Resolve fallback/stopped evidence before any later runtime-call path."
        ),
    }


def _base_response(
    request: dict[str, Any],
    status: str,
    failure_class: str | None,
    steps: list[dict[str, Any]],
    status_record: dict[str, Any] | None,
    validated_status: dict[str, Any] | None,
    primary_reason: str | None,
) -> dict[str, Any]:
    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "target_action": request.get("target_action"),
        "handshake_helper_version": HANDSHAKE_HELPER_VERSION,
        "runtime_calls_performed": False,
        "cache_read_performed": False,
        "cache_write_performed": False,
        "private_runtime_state_read": False,
        "later_runtime_path_blocked": status != "ready",
        "failure_class": failure_class,
        "summary": _summary(status, failure_class, primary_reason),
        "session_compatibility_status": status_record,
        "validated_status": validated_status,
        "steps": steps,
        "result": {
            "stop_reason": primary_reason,
            "residual_risk": [
                "Handshake used caller-supplied documented metadata and explicit session marker only.",
                "This helper did not call Desktop thread tools or read Desktop private runtime state.",
                "This helper did not read or write a compatibility cache.",
                "Runtime-call authorization, external-write authorization, target validation, permission handling, and response validation remain separate.",
            ],
        },
    }


def _stopped(request: dict[str, Any], reason: str, failure_class: str = "validation_error") -> dict[str, Any]:
    return _base_response(request, "stopped", failure_class, [], None, None, reason)


def _required_paths() -> list[str]:
    return [
        "requested_action",
        "target_action",
        "expected.handshake_helper_version",
        "expected.status_helper_version",
        "old_contract",
        "metadata_request",
        "session_identity",
    ]


def _validate_request_shape(request: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(request, dict):
        return _stopped({}, "Request must be a JSON object.")
    if request.get("requested_action") != REQUESTED_ACTION:
        return _stopped(request, f"Unsupported requested_action: {request.get('requested_action')}")

    missing = [path for path in _required_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped(request, "Missing required field(s): " + ", ".join(missing))

    expected = request.get("expected")
    if not isinstance(expected, dict):
        return _stopped(request, "expected must be a JSON object.")
    if _wrapper_identifier(expected) is None:
        return _stopped(
            request,
            "expected requires wrapper_version, skill_package_version, or repo_commit.",
            "wrapper_or_helper_version_mismatch",
        )
    if expected.get("handshake_helper_version") != HANDSHAKE_HELPER_VERSION:
        return _stopped(
            request,
            "expected.handshake_helper_version must match this handshake helper version.",
            "wrapper_or_helper_version_mismatch",
        )
    if expected.get("status_helper_version") != SESSION_STATUS_HELPER_VERSION:
        return _stopped(
            request,
            "expected.status_helper_version must match the session compatibility status helper version.",
            "wrapper_or_helper_version_mismatch",
        )

    if not isinstance(request.get("old_contract"), dict):
        return _stopped(request, "old_contract must be a JSON object.")
    old_wrapper = _wrapper_identifier(request["old_contract"])
    if old_wrapper is not None and old_wrapper != _wrapper_identifier(expected):
        return _stopped(
            request,
            "old_contract wrapper/package/repo identity does not match expected identity.",
            "wrapper_or_helper_version_mismatch",
        )
    if not isinstance(request.get("metadata_request"), dict):
        return _stopped(request, "metadata_request must be a JSON object.")
    if not isinstance(request.get("session_identity"), dict):
        return _stopped(request, "session_identity must be a JSON object.", "missing_session_marker")

    auth_hits = _authorization_field_hits(request)
    if auth_hits:
        return _stopped(
            request,
            "Handshake request must not include authorization or validation substitute field(s): "
            + ", ".join(auth_hits),
            "authorization_out_of_scope",
        )
    return None


def build_session_compatibility_handshake(request: dict[str, Any]) -> dict[str, Any]:
    """Build and validate first-use session compatibility status evidence."""

    shape_error = _validate_request_shape(request)
    if shape_error is not None:
        return shape_error

    normalized = normalize_capability_metadata(request["metadata_request"])
    steps: list[dict[str, Any]] = [
        {
            "name": "capability-discovery",
            "status": normalized.get("status"),
            "failure_class": normalized.get("failure_class"),
            "output": normalized,
        }
    ]

    comparison_request = {
        "requested_action": "compare-runtime-contract-evidence",
        "target_action": request.get("target_action"),
        "old_contract": request["old_contract"],
        "new_capability_evidence": normalized,
    }
    comparison = compare_contract_evidence(comparison_request)
    steps.append(
        {
            "name": "contract-comparison",
            "status": comparison.get("status"),
            "failure_class": comparison.get("failure_class"),
            "output": comparison,
        }
    )

    status_record = _build_status_record(request, request["old_contract"], comparison)
    validation_request = _status_validation_request(request, status_record)
    validated_status = validate_session_compatibility_status(validation_request)
    steps.append(
        {
            "name": "session-status-validation",
            "status": validated_status.get("status"),
            "failure_class": validated_status.get("failure_class"),
            "output": validated_status,
        }
    )

    status = validated_status.get("status") or "stopped"
    failure_class = validated_status.get("failure_class")
    primary_reason = _get(validated_status, "result.stop_reason")
    if primary_reason is None and status == "ready":
        primary_reason = "First-use handshake produced validated ready session compatibility status."
    return _base_response(
        request,
        status,
        failure_class,
        steps,
        status_record,
        validated_status,
        primary_reason,
    )


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    return {
        "requested_action": REQUESTED_ACTION,
        "target_action": "read-thread",
        "expected": {
            "repo_commit": "fb5e3483c7f6630de991413a4e64eeb0aaa14790",
            "handshake_helper_version": HANDSHAKE_HELPER_VERSION,
            "status_helper_version": SESSION_STATUS_HELPER_VERSION,
            "target_action": "read-thread",
            "tool_or_api": "read_thread",
        },
        "old_contract": {
            "action": "read-thread",
            "tool_or_api": "read_thread",
            "classification": "read-only",
            "required_request_fields": ["thread_id"],
            "minimum_response_fields": ["status", "thread_id"],
            "capability_source": "runtime-reported schema",
            "contract_version": "version unavailable",
            "last_verified": today,
        },
        "metadata_request": {
            "requested_action": "normalize-runtime-capability-metadata",
            "metadata_source": {
                "source": "runtime-reported schema",
                "contract_version": "version unavailable",
                "last_verified": today,
                "available": True,
            },
            "capabilities": [
                {
                    "action": "read-thread",
                    "tool_or_api": "read_thread",
                    "classification": "read-only",
                    "request": {
                        "required": ["thread_id"],
                        "optional": ["include_metadata"],
                    },
                    "response": {
                        "required": ["status", "thread_id"],
                        "errors": ["message"],
                    },
                    "source": "runtime-reported schema",
                    "contract_version": "version unavailable",
                    "last_verified": today,
                }
            ],
        },
        "session_identity": {
            "marker_type": "current-session",
            "marker": "current-session scoped",
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
        response = build_session_compatibility_handshake(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped({}, f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
