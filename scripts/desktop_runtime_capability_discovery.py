#!/usr/bin/env python3
"""Desktop runtime wrapper V1 capability discovery helper.

This helper is intentionally non-state-changing. It normalizes caller-supplied
documented capability metadata into a small evidence record for later wrapper
planning. It never discovers capabilities by reading Desktop private runtime
state, filesystem locations, logs, UI state, unpublished endpoints, daemons, or
background services, and it never calls Desktop thread tools.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from typing import Any


DISCOVERY_HELPER_VERSION = "0.1.0"
REQUESTED_ACTION = "normalize-runtime-capability-metadata"

CAPABILITY_SOURCES = {
    "active tool list",
    "connector metadata",
    "documented API",
    "installed plugin metadata",
    "official documentation",
    "runtime-reported schema",
}

CLASSIFICATIONS = {
    "read-only",
    "state-changing",
}

FORBIDDEN_SOURCE_HINTS = {
    "desktop private runtime state": "Desktop private runtime state",
    "database": "Desktop private runtime database",
    "logs": "Desktop runtime logs",
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


def _string_list(value: Any, *, allow_empty: bool = False) -> list[str] | None:
    if not isinstance(value, list) or (not value and not allow_empty):
        return None
    strings: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            return None
        strings.append(item.strip())
    return strings


def _stopped(reason: str, failure_class: str = "validation_error") -> dict[str, Any]:
    return {
        "status": "stopped",
        "requested_action": REQUESTED_ACTION,
        "discovery_helper_version": DISCOVERY_HELPER_VERSION,
        "failure_class": failure_class,
        "capabilities": [],
        "result": {
            "stop_reason": reason,
            "residual_risk": [],
        },
    }


def _unavailable(reason: str, residual_risk: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": "unavailable",
        "requested_action": REQUESTED_ACTION,
        "discovery_helper_version": DISCOVERY_HELPER_VERSION,
        "failure_class": "missing_capability_metadata",
        "capabilities": [],
        "result": {
            "stop_reason": reason,
            "residual_risk": residual_risk or ["No capability metadata was normalized."],
        },
    }


def _required_metadata_paths() -> list[str]:
    return [
        "requested_action",
        "metadata_source.source",
        "metadata_source.last_verified",
        "metadata_source.contract_version",
    ]


def _required_capability_paths(index: int) -> list[str]:
    prefix = f"capabilities[{index}]"
    return [
        f"{prefix}.action",
        f"{prefix}.tool_or_api",
        f"{prefix}.classification",
        f"{prefix}.request.required",
        f"{prefix}.response.required",
        f"{prefix}.source",
        f"{prefix}.contract_version",
        f"{prefix}.last_verified",
    ]


def normalize_capability_metadata(request: dict[str, Any]) -> dict[str, Any]:
    """Normalize caller-supplied capability metadata.

    The helper returns ``available`` when at least one capability is normalized,
    ``unavailable`` when the caller explicitly reports no metadata or no matching
    capabilities, and ``stopped`` when metadata is ambiguous or unsafe.
    """

    if not isinstance(request, dict):
        return _stopped("Request must be a JSON object.")

    missing = [path for path in _required_metadata_paths() if _is_missing(_get(request, path))]
    if missing:
        return _stopped("Missing required field(s): " + ", ".join(missing))

    if _get(request, "requested_action") != REQUESTED_ACTION:
        return _stopped(f"Unsupported requested_action: {_get(request, 'requested_action')}")

    metadata_source = str(_get(request, "metadata_source.source")).strip()
    if metadata_source not in CAPABILITY_SOURCES:
        return _stopped(
            "metadata_source.source is not a recognized caller-supplied documented source.",
            "missing_contract_evidence",
        )

    metadata_last_verified = _get(request, "metadata_source.last_verified")
    if not _valid_iso_date(metadata_last_verified):
        return _stopped(
            "metadata_source.last_verified must be YYYY-MM-DD.",
            "missing_contract_evidence",
        )

    metadata_contract_version = str(_get(request, "metadata_source.contract_version")).strip()
    if metadata_contract_version == "version unavailable" and metadata_source not in CAPABILITY_SOURCES:
        return _stopped(
            "version unavailable requires a verifiable capability source.",
            "missing_contract_evidence",
        )

    forbidden_hits = _forbidden_source_hits(_get(request, "metadata_source"))
    if forbidden_hits:
        return _stopped(
            "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
            "forbidden_private_runtime_state",
        )

    metadata_available = _as_bool(_get(request, "metadata_source.available"))
    capabilities = _get(request, "capabilities")
    if metadata_available is False or capabilities == []:
        return _unavailable(
            "Caller-supplied documented metadata reports no available capabilities.",
            ["Use the planner fallback path or provide documented metadata from an allowed source."],
        )

    if not isinstance(capabilities, list) or not capabilities:
        return _stopped("capabilities must be a non-empty list when metadata is available.")

    normalized_capabilities: list[dict[str, Any]] = []
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            return _stopped(f"capabilities[{index}] must be a JSON object.")

        missing_capability = []
        for path in _required_capability_paths(index):
            local_path = path.split(".", 1)[1]
            value = _get(capability, local_path)
            if local_path == "request.required":
                if not isinstance(value, list):
                    missing_capability.append(path)
            elif _is_missing(value):
                missing_capability.append(path)
        if missing_capability:
            return _stopped("Missing required field(s): " + ", ".join(missing_capability))

        forbidden_hits = _forbidden_source_hits(capability)
        if forbidden_hits:
            return _stopped(
                "Forbidden Desktop runtime source hint(s): " + ", ".join(forbidden_hits),
                "forbidden_private_runtime_state",
            )

        classification = str(capability["classification"]).strip()
        if classification not in CLASSIFICATIONS:
            return _stopped(
                f"capabilities[{index}].classification must be read-only or state-changing.",
                "missing_contract_evidence",
            )

        source = str(capability["source"]).strip()
        if source not in CAPABILITY_SOURCES:
            return _stopped(
                f"capabilities[{index}].source is not a recognized caller-supplied documented source.",
                "missing_contract_evidence",
            )

        last_verified = capability["last_verified"]
        if not _valid_iso_date(last_verified):
            return _stopped(
                f"capabilities[{index}].last_verified must be YYYY-MM-DD.",
                "missing_contract_evidence",
            )

        required_request_fields = _string_list(
            _get(capability, "request.required"), allow_empty=True
        )
        minimum_response_fields = _string_list(_get(capability, "response.required"))
        if required_request_fields is None:
            return _stopped(
                f"capabilities[{index}].request.required must be a string list.",
                "missing_contract_evidence",
            )
        if minimum_response_fields is None:
            return _stopped(
                f"capabilities[{index}].response.required must be a non-empty string list.",
                "missing_contract_evidence",
            )

        optional_request_fields = _string_list(_get(capability, "request.optional")) or []
        error_response_fields = _string_list(_get(capability, "response.errors")) or []
        contract_version = str(capability["contract_version"]).strip()
        discovery_mapping = (
            f"discovery helper {DISCOVERY_HELPER_VERSION} -> "
            f"{capability['tool_or_api']} {contract_version}"
        )

        normalized_capabilities.append(
            {
                "action": capability["action"],
                "tool_or_api": capability["tool_or_api"],
                "classification": classification,
                "required_request_fields": required_request_fields,
                "optional_request_fields": optional_request_fields,
                "minimum_response_fields": minimum_response_fields,
                "error_response_fields": error_response_fields,
                "capability_source": source,
                "contract_version": contract_version,
                "last_verified": last_verified,
                "discovery_helper_version": DISCOVERY_HELPER_VERSION,
                "discovery_mapping": discovery_mapping,
            }
        )

    return {
        "status": "available",
        "requested_action": REQUESTED_ACTION,
        "discovery_helper_version": DISCOVERY_HELPER_VERSION,
        "metadata_source": {
            "source": metadata_source,
            "contract_version": metadata_contract_version,
            "last_verified": metadata_last_verified,
        },
        "failure_class": None,
        "capabilities": normalized_capabilities,
        "result": {
            "stop_reason": None,
            "residual_risk": [
                "Capabilities were normalized from caller-supplied metadata only.",
                "This helper did not call or verify Desktop thread tools.",
            ],
        },
    }


def example_request() -> dict[str, Any]:
    today = _dt.date.today().isoformat()
    return {
        "requested_action": REQUESTED_ACTION,
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
                    "required": ["threadId"],
                    "optional": ["hostId", "turnLimit", "cursor", "includeOutputs", "maxOutputCharsPerItem"],
                },
                "response": {
                    "required": ["status", "threadId"],
                    "errors": ["message"],
                },
                "source": "runtime-reported schema",
                "contract_version": "version unavailable",
                "last_verified": today,
            }
        ],
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
        response = normalize_capability_metadata(request)
    except (OSError, json.JSONDecodeError) as exc:
        response = _stopped(f"Could not load request JSON: {exc}")

    print(json.dumps(response, indent=indent, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
