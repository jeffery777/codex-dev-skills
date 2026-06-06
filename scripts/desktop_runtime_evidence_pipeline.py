#!/usr/bin/env python3
"""Desktop runtime wrapper V1 evidence-only pipeline example.

This helper is intentionally non-state-changing. It chains caller-supplied
capability metadata through discovery, contract comparison, and create/read
preflight helpers so maintainers can inspect one end-to-end evidence record.
It never calls Desktop thread tools and never reads Desktop private runtime
state.
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
from desktop_runtime_create_thread_preflight import preflight_create_thread
from desktop_runtime_read_thread_preflight import preflight_read_thread


PIPELINE_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "build-desktop-runtime-wrapper-v1-evidence-pipeline"
SUPPORTED_TARGET_ACTIONS = {"create-thread", "read-thread"}


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


def _status_from_steps(steps: list[dict[str, Any]]) -> str:
    statuses = [step.get("status") for step in steps]
    if "stopped" in statuses:
        return "stopped"
    if any(status in {"fallback", "unavailable"} for status in statuses):
        return "fallback"
    return "ready"


def _failure_class_from_steps(steps: list[dict[str, Any]]) -> str | None:
    for step in steps:
        if step.get("status") in {"stopped", "fallback", "unavailable"}:
            return step.get("failure_class") or step.get("status")
    return None


def _normalize_target_actions(value: Any) -> tuple[list[str] | None, str | None]:
    if not isinstance(value, list) or not value:
        return None, "target_actions must be a non-empty list."

    actions: list[str] = []
    for index, action in enumerate(value):
        if not isinstance(action, str) or not action.strip():
            return None, f"target_actions[{index}] must be a non-empty string."
        normalized_action = action.strip()
        if normalized_action not in SUPPORTED_TARGET_ACTIONS:
            return None, f"Unsupported target_action(s): {normalized_action}"
        if normalized_action in actions:
            return None, f"Duplicate target_action: {normalized_action}"
        actions.append(normalized_action)
    return actions, None


def _selected_capability(evidence: dict[str, Any], target_action: str) -> dict[str, Any] | None:
    capabilities = evidence.get("capabilities")
    if not isinstance(capabilities, list):
        return None
    for capability in capabilities:
        if isinstance(capability, dict) and capability.get("action") == target_action:
            return capability
    return None


def _old_contract(request: dict[str, Any], target_action: str) -> dict[str, Any] | None:
    contracts = request.get("old_contracts")
    if isinstance(contracts, dict):
        contract = contracts.get(target_action)
        return contract if isinstance(contract, dict) else None
    if isinstance(contracts, list):
        for contract in contracts:
            if isinstance(contract, dict) and contract.get("action") == target_action:
                return contract
    return None


def _comparison_request(
    request: dict[str, Any],
    normalized: dict[str, Any],
    target_action: str,
) -> dict[str, Any] | None:
    old_contract = _old_contract(request, target_action)
    if old_contract is None:
        return None
    return {
        "requested_action": "compare-runtime-contract-evidence",
        "target_action": target_action,
        "old_contract": old_contract,
        "new_capability_evidence": normalized,
    }


def _target_evidence(request: dict[str, Any]) -> dict[str, Any]:
    target = request.get("target")
    return copy.deepcopy(target) if isinstance(target, dict) else {}


def _boundaries(request: dict[str, Any]) -> dict[str, Any]:
    boundaries = request.get("boundaries")
    return copy.deepcopy(boundaries) if isinstance(boundaries, dict) else {}


def _create_authorization(request: dict[str, Any]) -> dict[str, Any]:
    authorization = request.get("authorization")
    if not isinstance(authorization, dict):
        authorization = {}
    thread_authorizations = authorization.get("thread_action_authorized")
    if not isinstance(thread_authorizations, dict):
        thread_authorizations = {}
    authorized = thread_authorizations.get("create-thread", False)
    return {
        "thread_action_authorized": authorized,
        "authorized_thread_action": "create-thread" if authorized else "",
        "external_write_authorized": authorization.get("external_write_authorized", False),
    }


def _read_authorization(request: dict[str, Any]) -> dict[str, Any]:
    authorization = request.get("authorization")
    if not isinstance(authorization, dict):
        authorization = {}
    thread_authorizations = authorization.get("thread_action_authorized")
    if not isinstance(thread_authorizations, dict):
        thread_authorizations = {}
    return {
        "thread_action_authorized": thread_authorizations.get("read-thread", False),
        "external_write_authorized": authorization.get("external_write_authorized", False),
    }


def _create_preflight_request(
    request: dict[str, Any],
    normalized: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    prompt = request.get("prompt")
    if not isinstance(prompt, dict):
        prompt = {}
    return {
        "requested_action": "preflight-create-thread-runtime-call",
        "target_action": "create-thread",
        "target": _target_evidence(request),
        "prompt": copy.deepcopy(prompt),
        "capability_evidence": normalized,
        "contract_comparison": comparison,
        "boundaries": _boundaries(request),
        "authorization": _create_authorization(request),
    }


def _read_preflight_request(
    request: dict[str, Any],
    normalized: dict[str, Any],
    comparison: dict[str, Any],
) -> dict[str, Any]:
    read_request = request.get("read_request")
    if not isinstance(read_request, dict):
        read_request = {}
    return {
        "requested_action": "preflight-read-thread-runtime-call",
        "target_action": "read-thread",
        "target": _target_evidence(request),
        "read_request": copy.deepcopy(read_request),
        "capability_evidence": normalized,
        "contract_comparison": comparison,
        "boundaries": _boundaries(request),
        "authorization": _read_authorization(request),
    }


def _recommended_next_step(status: str) -> str:
    if status == "ready":
        return (
            "Treat ready as evidence only; require separate approval before any "
            "Desktop runtime call or external write."
        )
    if status == "fallback":
        return "Use the paste-ready fallback path or provide the missing compatible evidence."
    return "Resolve the stopped reason before using an adapter, runtime tool, or fallback."


def _basic_summary(
    status: str,
    failure_class: str | None,
    primary_reason: str | None,
    target_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target_results = target_results or []
    counts = {"ready": 0, "fallback": 0, "stopped": 0, "unavailable": 0}
    for result in target_results:
        result_status = result.get("status")
        if result_status in counts:
            counts[result_status] += 1
    return {
        "status": status,
        "failure_class": failure_class,
        "primary_reason": primary_reason,
        "readiness_counts": counts,
        "target_results": target_results,
        "recommended_next_step": _recommended_next_step(status),
    }


def _stopped(reason: str, failure_class: str = "validation_error") -> dict[str, Any]:
    return {
        "status": "stopped",
        "requested_action": REQUESTED_ACTION,
        "pipeline_helper_version": PIPELINE_HELPER_VERSION,
        "runtime_calls_performed": False,
        "failure_class": failure_class,
        "summary": _basic_summary("stopped", failure_class, reason),
        "steps": [],
        "result": {
            "stop_reason": reason,
            "residual_risk": [],
        },
    }


def build_evidence_pipeline(request: dict[str, Any]) -> dict[str, Any]:
    """Build end-to-end wrapper V1 evidence without runtime calls."""

    if not isinstance(request, dict):
        return _stopped("Request must be a JSON object.")
    if request.get("requested_action") != REQUESTED_ACTION:
        return _stopped(f"Unsupported requested_action: {request.get('requested_action')}")

    target_actions, target_error = _normalize_target_actions(request.get("target_actions"))
    if target_error is not None:
        return _stopped(target_error)
    assert target_actions is not None

    metadata_request = request.get("metadata_request")
    if not isinstance(metadata_request, dict):
        return _stopped("metadata_request must be a JSON object.")

    missing = []
    for path in (
        "target.repo",
        "target.remote",
        "target.branch",
        "boundaries.external_writes_blocked",
        "authorization.external_write_authorized",
    ):
        if _is_missing(_get(request, path)):
            missing.append(path)
    if "create-thread" in target_actions and _is_missing(_get(request, "target.expected_head")):
        missing.append("target.expected_head")
    if "read-thread" in target_actions and _is_missing(_get(request, "target.thread_id")):
        missing.append("target.thread_id")
    if missing:
        return _stopped("Missing required field(s): " + ", ".join(missing))

    if _as_bool(_get(request, "boundaries.external_writes_blocked")) is not True:
        return _stopped(
            "boundaries.external_writes_blocked must be true.",
            "external_write_request",
        )
    if _as_bool(_get(request, "authorization.external_write_authorized")) is not False:
        return _stopped(
            "authorization.external_write_authorized must be false.",
            "external_write_request",
        )

    normalized = normalize_capability_metadata(metadata_request)
    steps: list[dict[str, Any]] = [
        {
            "name": "capability-discovery",
            "target_action": None,
            "status": normalized.get("status"),
            "failure_class": normalized.get("failure_class"),
            "output": normalized,
        }
    ]

    if normalized.get("status") == "stopped":
        return _response(request, steps)

    for target_action in target_actions:
        comparison_request = _comparison_request(request, normalized, target_action)
        if comparison_request is None:
            comparison = {
                "status": "fallback",
                "failure_class": "missing_old_contract",
                "result": {
                    "stop_reason": f"Missing old_contracts entry for {target_action}.",
                    "residual_risk": ["Contract comparison cannot run without old wrapper evidence."],
                },
            }
        else:
            comparison = compare_contract_evidence(comparison_request)
        steps.append(
            {
                "name": "contract-comparison",
                "target_action": target_action,
                "status": comparison.get("status"),
                "failure_class": comparison.get("failure_class"),
                "output": comparison,
            }
        )

        if target_action == "create-thread":
            preflight_request = _create_preflight_request(request, normalized, comparison)
            preflight = preflight_create_thread(preflight_request)
        else:
            preflight_request = _read_preflight_request(request, normalized, comparison)
            preflight = preflight_read_thread(preflight_request)
        steps.append(
            {
                "name": "runtime-call-preflight",
                "target_action": target_action,
                "status": preflight.get("status"),
                "failure_class": preflight.get("failure_class"),
                "output": preflight,
            }
        )

    return _response(request, steps)


def _response(request: dict[str, Any], steps: list[dict[str, Any]]) -> dict[str, Any]:
    status = _status_from_steps(steps)
    failure_class = _failure_class_from_steps(steps)
    selected_capabilities = {}
    discovery_output = steps[0]["output"] if steps else {}
    if isinstance(discovery_output, dict):
        for target_action in request.get("target_actions", []):
            selected = _selected_capability(discovery_output, target_action)
            selected_capabilities[target_action] = selected

    stop_reasons = _step_reasons(steps)
    residual_risk = [
        "Pipeline used caller-supplied documented metadata only.",
        "No Desktop thread tool was called and no Desktop private runtime state was read.",
        "Ready preflight results are evidence only and do not authorize runtime calls or external writes.",
    ]
    summary = _pipeline_summary(request, steps, status, failure_class, stop_reasons)

    return {
        "status": status,
        "requested_action": REQUESTED_ACTION,
        "pipeline_helper_version": PIPELINE_HELPER_VERSION,
        "runtime_calls_performed": False,
        "target_actions": request.get("target_actions"),
        "failure_class": failure_class,
        "summary": summary,
        "selected_capabilities": selected_capabilities,
        "steps": steps,
        "result": {
            "stop_reasons": stop_reasons,
            "residual_risk": residual_risk,
        },
    }


def _step_reasons(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reasons = []
    for step in steps:
        output = step.get("output")
        if not isinstance(output, dict):
            continue
        reason = _get(output, "result.stop_reason")
        if reason:
            reasons.append(
                {
                    "step": step.get("name"),
                    "target_action": step.get("target_action"),
                    "reason": reason,
                }
            )
    return reasons


def _find_step(
    steps: list[dict[str, Any]],
    name: str,
    target_action: str | None = None,
) -> dict[str, Any] | None:
    for step in steps:
        if step.get("name") != name:
            continue
        if target_action is not None and step.get("target_action") != target_action:
            continue
        return step
    return None


def _target_summary(steps: list[dict[str, Any]], target_action: str) -> dict[str, Any]:
    comparison = _find_step(steps, "contract-comparison", target_action)
    preflight = _find_step(steps, "runtime-call-preflight", target_action)
    target_status = None if preflight is None else preflight.get("status")
    if target_status is None and comparison is not None:
        target_status = comparison.get("status")

    target_failure_class = None
    for step in (preflight, comparison):
        if step is not None and step.get("failure_class"):
            target_failure_class = step.get("failure_class")
            break

    reason = None
    for step in (preflight, comparison):
        if step is None:
            continue
        output = step.get("output")
        if isinstance(output, dict):
            reason = _get(output, "result.stop_reason")
            if reason:
                break

    return {
        "target_action": target_action,
        "status": target_status,
        "failure_class": target_failure_class,
        "reason": reason,
        "comparison_status": None if comparison is None else comparison.get("status"),
        "preflight_status": None if preflight is None else preflight.get("status"),
    }


def _pipeline_summary(
    request: dict[str, Any],
    steps: list[dict[str, Any]],
    status: str,
    failure_class: str | None,
    stop_reasons: list[dict[str, Any]],
) -> dict[str, Any]:
    target_actions = request.get("target_actions")
    target_results = []
    if isinstance(target_actions, list):
        target_results = [
            _target_summary(steps, target_action)
            for target_action in target_actions
            if isinstance(target_action, str)
        ]

    discovery = _find_step(steps, "capability-discovery")
    primary_reason = None
    if stop_reasons:
        primary_reason = stop_reasons[0]["reason"]
    elif status == "ready":
        primary_reason = "All requested target preflights returned ready evidence."
    elif status == "fallback":
        primary_reason = "One or more requested target actions returned fallback evidence."

    summary = _basic_summary(status, failure_class, primary_reason, target_results)
    summary["discovery_status"] = None if discovery is None else discovery.get("status")
    return summary


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    return {
        "requested_action": REQUESTED_ACTION,
        "target_actions": ["create-thread", "read-thread"],
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
                    "action": "create-thread",
                    "tool_or_api": "create_thread",
                    "classification": "state-changing",
                    "request": {
                        "required": ["prompt"],
                        "optional": ["title", "repository", "branch"],
                    },
                    "response": {
                        "required": ["status", "thread_id"],
                        "errors": ["message"],
                    },
                    "source": "runtime-reported schema",
                    "contract_version": "version unavailable",
                    "last_verified": today,
                },
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
                },
            ],
        },
        "old_contracts": {
            "create-thread": {
                "action": "create-thread",
                "tool_or_api": "create_thread",
                "classification": "state-changing",
                "required_request_fields": ["prompt"],
                "minimum_response_fields": ["status", "thread_id"],
                "capability_source": "runtime-reported schema",
                "contract_version": "version unavailable",
                "last_verified": today,
            },
            "read-thread": {
                "action": "read-thread",
                "tool_or_api": "read_thread",
                "classification": "read-only",
                "required_request_fields": ["thread_id"],
                "minimum_response_fields": ["status", "thread_id"],
                "capability_source": "runtime-reported schema",
                "contract_version": "version unavailable",
                "last_verified": today,
            },
        },
        "target": {
            "repo": "owner/name",
            "remote": "https://github.com/owner/name.git",
            "branch": "codex/example",
            "expected_head": "abcdef1234567890abcdef1234567890abcdef12",
            "thread_id": "thread-id-supplied-by-caller",
        },
        "prompt": {
            "summary": "Prepare a bounded Desktop thread handoff.",
            "body": "Read repo files first, do the scoped task, run verification, and report evidence.",
        },
        "read_request": {
            "summary": "Read only documented thread result fields after separate approval.",
            "expected_fields": ["status", "thread_id"],
        },
        "boundaries": {
            "in_scope": ["docs/runtime-adapter-v2.md", "examples/runtime-adapter-boundary.md"],
            "out_of_scope": [".work/", "Desktop private runtime state"],
            "external_writes_blocked": True,
        },
        "authorization": {
            "thread_action_authorized": {
                "create-thread": True,
                "read-thread": False,
            },
            "external_write_authorized": False,
        },
    }


def _load_request(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.load(sys.stdin)


def _with_target_actions(request: Any, target_actions: list[str] | None) -> Any:
    if target_actions is None or not isinstance(request, dict):
        return request
    filtered = copy.deepcopy(request)
    filtered["target_actions"] = target_actions
    return filtered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", help="Path to a JSON request. Reads stdin when omitted.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    parser.add_argument("--example", action="store_true", help="Print an example request and exit.")
    parser.add_argument(
        "--target-action",
        action="append",
        choices=sorted(SUPPORTED_TARGET_ACTIONS),
        help=(
            "Run or print the pipeline for one target action. Repeat to include "
            "multiple actions. Defaults to target_actions from the request."
        ),
    )
    args = parser.parse_args(argv)
    target_actions, target_error = (
        _normalize_target_actions(args.target_action)
        if args.target_action is not None
        else (None, None)
    )
    if target_error is not None:
        parser.error(target_error)

    indent = 2 if args.pretty or args.example else None
    if args.example:
        example = _with_target_actions(example_request(), target_actions)
        print(json.dumps(example, indent=indent, sort_keys=True))
        return 0

    try:
        request = _load_request(args.request)
        request = _with_target_actions(request, target_actions)
        response = build_evidence_pipeline(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped(f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
