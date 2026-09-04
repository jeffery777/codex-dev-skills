"""Thin, explicit, local-only façade for the qualified Memory M1 adapter.

This is intentionally a caller library, not a lifecycle hook.  Its envelopes
classify an already eligible durable lesson; they never mint authority.
"""

from __future__ import annotations

import copy
import pathlib
import re
from collections.abc import Mapping
from typing import Any

import memory_contract as memory
import memory_operation as operation
import memory_sqlite as sqlite


PROFILE = "memory-m1-local-pilot/v1"
PILOT_EXTENSION = "dev.jeffery.memory-pilot/profile"
PILOT_CLASSES = frozenset({"verified-fact", "decision", "constraint", "evidence-reference"})
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SENSITIVE = re.compile(
    r"(?i)(?:raw\s+(?:chat|session|transcript|log)|-----BEGIN|(?:api[_-]?key|"
    r"access[_-]?token|client[_-]?secret|password|authorization)\s*[:=]|"
    r"\bbearer\s+\S+|\b(?:gh[oprsu]_[A-Za-z0-9_]{8,}|github_pat_[A-Za-z0-9_]+)|"
    r"\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_-]{20,}\b|\bxox[baprs]-[0-9A-Za-z-]{10,}\b|"
    r"\bsk-(?:proj-|svcacct-)?[0-9A-Za-z_-]{16,}\b|"
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b\d{3}-\d{2}-\d{4}\b|"
    r"(?:^|\s)/\S+|\\\\|(?:^|\s)(?:user|assistant|system)\s*:|"
    r"^\d{4}-\d{2}-\d{2}(?:T|\s).*(?:DEBUG|INFO|WARN|ERROR)|"
    r"\b[A-Za-z][A-Za-z0-9_.-]*\s*=\s*\S+)"
)
MAX_PILOT_CONTENT_BYTES = 512


class MemoryPilotError(ValueError):
    """A deliberately non-echoing pilot rejection."""


def _reject() -> MemoryPilotError:
    return MemoryPilotError("memory pilot request rejected")


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _reject()
    return value


def _safe(value: Any) -> None:
    """Reject raw/private material before any state/backend interaction."""
    if isinstance(value, str):
        if SENSITIVE.search(value):
            raise _reject()
    elif isinstance(value, dict):
        for item in value.values():
            _safe(item)
    elif isinstance(value, list):
        for item in value:
            _safe(item)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    """Load one bounded, duplicate-free, regular-file pilot document."""
    try:
        return memory.load_json(path)
    except memory.MemoryContractError as exc:
        raise _reject() from exc


def validate_envelope(value: Any, *, action: str) -> dict[str, Any]:
    _safe(value)
    envelope = _object(value)
    required = {"profile", "action", "scope", "tokens"}
    if action in {"remember", "recall"}:
        required.add("pilot_class")
    if set(envelope) != required or envelope.get("profile") != PROFILE or envelope.get("action") != action:
        raise _reject()
    if action in {"remember", "recall"} and envelope["pilot_class"] not in PILOT_CLASSES:
        raise _reject()
    scope = envelope["scope"]
    if (
        not isinstance(scope, list) or not scope
        or any(not isinstance(path, str) or not path or len(path.encode("utf-8")) > 256 for path in scope)
        or any(path.startswith("/") or "\\" in path or any(part in {"", ".", ".."} for part in path.split("/")) for path in scope)
        or scope != sorted(set(scope))
    ):
        raise _reject()
    tokens = envelope["tokens"]
    if (
        not isinstance(tokens, list) or not tokens
        or any(not isinstance(token, str) for token in tokens)
        or tokens != sorted(set(tokens))
    ):
        raise _reject()
    if any(not TOKEN.fullmatch(token) for token in tokens):
        raise _reject()
    return copy.deepcopy(envelope)


def _record_for_pilot(candidate: Mapping[str, Any], pilot: Mapping[str, Any]) -> dict[str, Any]:
    record = candidate.get("record")
    try:
        record = memory.validate_record(record)
    except memory.MemoryContractError as exc:
        raise _reject() from exc
    # This extension is within the canonical record body, so profile tampering
    # changes the record digest and invalidates the pre-existing M0 bindings.
    if (
        record["record_kind"] != "durable-lesson"
        or record["scope"] != pilot["scope"]
        or record["extensions"].get(PILOT_EXTENSION)
        != {"profile": PROFILE, "pilot_class": pilot["pilot_class"]}
    ):
        raise _reject()
    content = record["content"]
    if (
        not isinstance(content, str)
        or not content.strip()
        or content != content.strip()
        or len(content.encode("utf-8")) > MAX_PILOT_CONTENT_BYTES
        or any(character in content for character in ("\n", "\r", "\t"))
    ):
        raise _reject()
    _safe(content)
    return record


def _revalidate_recalled_record(record: Mapping[str, Any], pilot: Mapping[str, Any]) -> dict[str, Any]:
    """Reapply pilot-specific constraints to records from the shared M1 store."""
    return _record_for_pilot({"record": record}, pilot)


def remember(
    envelope: Any, authority: Any, candidate: Any, eligibility: Any, *,
    accepted_authority_receipts: Any, accepted_eligibility_receipts: Any,
    trusted_time: Any, accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str | None, state_root: pathlib.Path,
    repository_root: pathlib.Path,
) -> dict[str, Any]:
    """Explicitly execute a fully caller-authorized M0 upsert, or reject."""
    pilot = validate_envelope(envelope, action="remember")
    _safe(candidate)
    _record_for_pilot(_object(candidate), pilot)
    try:
        return sqlite.execute_authorized_operation(
            authority, candidate, eligibility,
            accepted_authority_receipts=accepted_authority_receipts,
            accepted_eligibility_receipts=accepted_eligibility_receipts,
            trusted_time_value=trusted_time,
            accepted_trusted_time_receipts=accepted_trusted_time_receipts,
            expected_pre_state_digest=expected_pre_state_digest,
            state_root=state_root, repository_root=repository_root,
        )
    except (sqlite.MemorySQLiteError, operation.MemoryOperationError, memory.MemoryContractError) as exc:
        raise _reject() from exc


def invalidate(
    envelope: Any, authority: Any, candidate: Any, eligibility: Any, *,
    accepted_authority_receipts: Any, accepted_eligibility_receipts: Any,
    trusted_time: Any, accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str, state_root: pathlib.Path,
    repository_root: pathlib.Path,
) -> dict[str, Any]:
    """Explicit logical invalidation only; physical purge is not exposed."""
    validate_envelope(envelope, action="invalidate")
    _safe(candidate)
    if _object(candidate).get("operation") != "invalidate":
        raise _reject()
    try:
        return sqlite.execute_authorized_operation(
            authority, candidate, eligibility,
            accepted_authority_receipts=accepted_authority_receipts,
            accepted_eligibility_receipts=accepted_eligibility_receipts,
            trusted_time_value=trusted_time,
            accepted_trusted_time_receipts=accepted_trusted_time_receipts,
            expected_pre_state_digest=expected_pre_state_digest,
            state_root=state_root, repository_root=repository_root,
        )
    except (sqlite.MemorySQLiteError, operation.MemoryOperationError, memory.MemoryContractError) as exc:
        raise _reject() from exc


def recall(
    envelope: Any, query_request: Any, retrieval_context: Any, *,
    trusted_conformance_receipts: Any, trusted_source_digests: Any,
    state_root: pathlib.Path, repository_root: pathlib.Path,
) -> dict[str, Any]:
    """Structured-query first, then V2b advisory adoption decision."""
    pilot = validate_envelope(envelope, action="recall")
    _safe(query_request)
    _safe(retrieval_context)
    request = _object(query_request)
    try:
        extension = request["extensions"][sqlite.QUERY_EXTENSION]
        if set(extension) != {"match", "terms"} or extension["match"] != "all":
            raise _reject()
        if extension["terms"] != pilot["tokens"] or request["scope"] != pilot["scope"]:
            raise _reject()
        if request["record_kinds"] != ["durable-lesson"]:
            raise _reject()
        response = sqlite.query(request, state_root, repository_root)
        matching_records: dict[str, dict[str, Any]] = {}
        for raw_record in response["records"]:
            record = memory.validate_record(raw_record)
            extension = record["extensions"].get(PILOT_EXTENSION)
            if extension is None:
                continue
            if extension != {"profile": PROFILE, "pilot_class": pilot["pilot_class"]}:
                if not isinstance(extension, dict) or extension.get("profile") != PROFILE:
                    raise _reject()
                continue
            record = _revalidate_recalled_record(record, pilot)
            matching_records[record["canonical_digest"]] = record
        context = _object(retrieval_context)
        if set(context) != {"handshake", "current", "extensions"}:
            raise _reject()
        input_value = {
            "contract_version": memory.CONTRACT_VERSION,
            "kind": "retrieval-decision-input",
            "handshake": copy.deepcopy(context["handshake"]),
            "request": request,
            "response": response,
            "current": copy.deepcopy(context["current"]),
            "extensions": copy.deepcopy(context["extensions"]),
        }
        receipt = memory.decide_retrieval(
            input_value,
            trusted_conformance_receipts=trusted_conformance_receipts,
            trusted_source_digests=trusted_source_digests,
        )
    except (KeyError, TypeError, sqlite.MemorySQLiteError, memory.MemoryContractError) as exc:
        raise _reject() from exc
    adopted = [
        item for item in receipt["dispositions"]
        if item["disposition"] == "adopt-as-context" and item["record_digest"] in matching_records
    ]
    adopted_context = [
        {
            "record_digest": item["record_digest"],
            "pilot_class": pilot["pilot_class"],
            "content": matching_records[item["record_digest"]]["content"],
            "source_refs": copy.deepcopy(
                matching_records[item["record_digest"]]["provenance"]["source_refs"]
            ),
        }
        for item in adopted
    ]
    return {
        "profile": PROFILE, "status": "advisory-context", "authority": "advisory-only",
        "backend_touch_count": 1, "retrieval_receipt": receipt,
        "adopted_record_digests": [item["record_digest"] for item in adopted],
        "adopted_context": adopted_context,
    }
