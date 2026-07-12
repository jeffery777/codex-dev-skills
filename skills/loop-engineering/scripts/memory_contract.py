#!/usr/bin/env python3
"""Loop Engineering V2b backend-neutral external memory safety contract.

This module validates data and produces advisory dispositions. It deliberately
has no backend, persistence, network, tool, authorization, or completion API.
"""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import pathlib
import re
from typing import Any


CONTRACT_VERSION = "loop-memory/v1"
MAX_DOCUMENT_BYTES = 131_072
MAX_CONTENT_BYTES = 32_768
MAX_RECORDS = 100
MAX_STRING = 2_048
MAX_EXTENSIONS = 16
SHA256 = re.compile(r"^[0-9a-f]{64}$")
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
NAMESPACE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
EXTENSION = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,62}\.)+[a-z0-9][a-z0-9-]{0,62}/[A-Za-z0-9._-]{1,64}$"
)
REMOTE = re.compile(r"^https://[a-z0-9.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$")
RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
CANONICAL_KEY = re.compile(r"^[\x20-\x7e]+$")
MAX_SAFE_INTEGER = 9_007_199_254_740_991

CAPABILITIES = (
    "read_query",
    "write_upsert",
    "invalidate",
    "tombstone",
    "delete",
    "namespaces",
    "repository_isolation",
    "filters",
    "pagination",
    "ttl_retention",
    "atomicity",
    "idempotency",
    "provenance_preservation",
    "sensitivity_handling",
    "audit",
)
CAPABILITY_STATES = {"supported", "unsupported", "unknown"}
HANDSHAKE_STATUSES = {
    "ready",
    "degraded",
    "unavailable",
    "disabled",
    "incompatible",
    "untrusted",
}
RESPONSE_STATUSES = {
    "ok",
    "partial",
    "unavailable",
    "timeout",
    "unsupported",
    "incompatible",
    "untrusted",
}
RECORD_KINDS = {
    "durable-lesson",
    "iteration-summary",
    "code-context",
    "coordination",
    "decision-context",
}
SOURCE_KINDS = {
    "repository-artifact",
    "git-commit",
    "verification",
    "review",
    "platform",
    "chat",
    "worker",
    "memory",
}
INJECTION_PATTERNS = (
    re.compile(r"(?i)ignore (?:all |the )?(?:previous|prior) instructions"),
    re.compile(r"(?i)(?:system|developer) (?:message|instruction)"),
    re.compile(r"(?i)(?:call|invoke|use) (?:the )?(?:tool|shell|terminal)"),
    re.compile(r"(?i)you must (?:ignore|execute|run|write|delete|merge|deploy)"),
    re.compile(r"(?i)<\s*(?:system|developer|tool)\b"),
)
SENSITIVE_CONTENT_PATTERNS = (
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)
MANDATORY_CONFORMANCE_EXPECTATIONS = {
    "retrieval-valid": {"fallback_to_no_memory": False},
    "retrieval-disabled": {"fallback_to_no_memory": True, "fallback_reason": "adapter-disabled"},
    "retrieval-partial": {"fallback_to_no_memory": True, "fallback_reason": "response-partial"},
    "retrieval-stale-handshake": {"fallback_to_no_memory": True, "fallback_reason": "handshake-stale"},
    "retrieval-future-handshake": {"fallback_to_no_memory": True, "fallback_reason": "handshake-timestamp-in-future"},
    "retrieval-unknown-clock": {"fallback_to_no_memory": True, "fallback_reason": "handshake-freshness-unknown-clock"},
    "retrieval-handshake-age-boundary": {"fallback_to_no_memory": False},
    "write-valid": {"eligible": True},
    "write-sensitive": {"eligible": False},
}


class MemoryContractError(ValueError):
    """Raised when untrusted memory input violates the shared contract."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MemoryContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise MemoryContractError(f"document must be a regular non-symlink file: {path}")
    raw = path.read_bytes()
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise MemoryContractError("document exceeds the maximum encoded size")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                MemoryContractError(f"non-finite JSON value: {value}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise MemoryContractError(f"invalid JSON: {exc}") from exc
    return _object(value, "document")


def canonical_json(value: Any) -> str:
    _finite(value, "canonical value")
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _finite(value: Any, label: str, *, depth: int = 0) -> None:
    if depth > 64:
        raise MemoryContractError(f"{label} exceeds the maximum nesting depth")
    if isinstance(value, float):
        raise MemoryContractError(
            f"{label} contains a floating-point number; use a bounded integer or string"
        )
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) > MAX_SAFE_INTEGER:
        raise MemoryContractError(f"{label} contains an integer outside the safe range")
    if isinstance(value, str):
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise MemoryContractError(
                f"{label} contains an invalid Unicode scalar value"
            ) from exc
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise MemoryContractError(f"{label} contains a non-string key")
            if not CANONICAL_KEY.fullmatch(key):
                raise MemoryContractError(f"{label} contains a non-ASCII object key")
            _finite(child, label, depth=depth + 1)
    elif isinstance(value, list):
        for child in value:
            _finite(child, label, depth=depth + 1)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MemoryContractError(f"{label} must be an object")
    return value


def _array(value: Any, label: str, *, maximum: int = MAX_RECORDS) -> list[Any]:
    if not isinstance(value, list):
        raise MemoryContractError(f"{label} must be an array")
    if len(value) > maximum:
        raise MemoryContractError(f"{label} exceeds the maximum item count")
    return value


def _string(value: Any, label: str, *, maximum: int = MAX_STRING) -> str:
    if not isinstance(value, str) or not value:
        raise MemoryContractError(f"{label} must be a bounded non-empty string")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise MemoryContractError(f"{label} must contain valid Unicode scalar values") from exc
    if len(encoded) > maximum:
        raise MemoryContractError(f"{label} must be a bounded non-empty string")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise MemoryContractError(f"{label} must be boolean")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise MemoryContractError(f"{label} must be an integer in range")
    return value


def _exact(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] | None = None,
    label: str,
) -> None:
    optional = optional or set()
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required - optional)
    if missing:
        raise MemoryContractError(f"{label} missing required fields: {','.join(missing)}")
    if unknown:
        raise MemoryContractError(f"{label} contains unknown fields: {','.join(unknown)}")


def _enum(value: Any, allowed: set[str], label: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise MemoryContractError(f"{label} must be one of: {','.join(sorted(allowed))}")
    return value


def _identifier(value: Any, label: str) -> str:
    value = _string(value, label, maximum=128)
    if not IDENTIFIER.fullmatch(value):
        raise MemoryContractError(f"{label} has invalid identifier syntax")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise MemoryContractError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _timestamp(value: Any, label: str) -> dt.datetime:
    value = _string(value, label, maximum=64)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise MemoryContractError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MemoryContractError(f"{label} requires an explicit timezone")
    return parsed.astimezone(dt.timezone.utc)


def _relative_path(value: Any, label: str) -> str:
    value = _string(value, label, maximum=512)
    parsed = pathlib.PurePosixPath(value)
    if (
        not RELATIVE_PATH.fullmatch(value)
        or ".." in parsed.parts
        or (value != "." and str(parsed) != value)
    ):
        raise MemoryContractError(f"{label} must be a normalized repository-relative path")
    return value


def validate_extensions(value: Any) -> dict[str, Any]:
    extensions = _object(value, "extensions")
    if len(extensions) > MAX_EXTENSIONS:
        raise MemoryContractError("extensions exceed the maximum count")
    for key, item in extensions.items():
        if not EXTENSION.fullmatch(key):
            raise MemoryContractError(f"extension key is not namespaced: {key}")
        if not isinstance(item, (dict, list, str, int, float, bool)) and item is not None:
            raise MemoryContractError(f"extension value has unsupported type: {key}")
        if len(canonical_json(item).encode("utf-8")) > 4_096:
            raise MemoryContractError(f"extension value is too large: {key}")
    return extensions


def validate_repository_identity(value: Any) -> dict[str, Any]:
    identity = _object(value, "repository")
    _exact(
        identity,
        required={
            "canonical_repository_id",
            "canonical_remote",
            "repository_identity_digest",
            "principal_scope",
            "source_revision",
            "path_scope",
            "worktree_id_digest",
        },
        label="repository",
    )
    canonical_id = _identifier(identity["canonical_repository_id"], "repository.canonical_repository_id")
    remote = _string(identity["canonical_remote"], "repository.canonical_remote", maximum=512)
    if not REMOTE.fullmatch(remote):
        raise MemoryContractError("repository.canonical_remote must be a canonical HTTPS repository URL")
    principal = _object(identity["principal_scope"], "repository.principal_scope")
    _exact(principal, required={"tenant", "workspace", "user"}, label="repository.principal_scope")
    for key in ("tenant", "workspace", "user"):
        if principal[key] != "not-applicable":
            _digest(principal[key], f"repository.principal_scope.{key}")
    source = _object(identity["source_revision"], "repository.source_revision")
    _exact(source, required={"kind", "commit_sha"}, optional={"branch"}, label="repository.source_revision")
    if source["kind"] != "git" or not isinstance(source["commit_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", source["commit_sha"]):
        raise MemoryContractError("repository.source_revision must identify an exact Git commit")
    if "branch" in source:
        _string(source["branch"], "repository.source_revision.branch", maximum=256)
    paths = _array(identity["path_scope"], "repository.path_scope", maximum=64)
    if not paths:
        raise MemoryContractError("repository.path_scope must not be empty")
    for index, path in enumerate(paths):
        _relative_path(path, f"repository.path_scope[{index}]")
    _digest(identity["worktree_id_digest"], "repository.worktree_id_digest")
    declared = _digest(identity["repository_identity_digest"], "repository.repository_identity_digest")
    body = {
        "canonical_repository_id": canonical_id,
        "canonical_remote": remote,
        "principal_scope": principal,
        "source_revision": source,
        "path_scope": paths,
        "worktree_id_digest": identity["worktree_id_digest"],
    }
    if declared != canonical_digest(body):
        raise MemoryContractError("repository identity digest mismatch")
    return identity


def validate_handshake(value: Any) -> dict[str, Any]:
    doc = _object(value, "capability handshake")
    _exact(
        doc,
        required={"contract_version", "kind", "adapter", "capabilities", "status", "observed_at", "extensions"},
        label="capability handshake",
    )
    if doc["contract_version"] != CONTRACT_VERSION or doc["kind"] != "capability-handshake":
        raise MemoryContractError("unsupported capability handshake contract")
    adapter = _object(doc["adapter"], "adapter")
    _exact(
        adapter,
        required={"adapter_id", "adapter_version", "schema_versions", "consistency", "isolation"},
        label="adapter",
    )
    _identifier(adapter["adapter_id"], "adapter.adapter_id")
    _identifier(adapter["adapter_version"], "adapter.adapter_version")
    versions = _array(adapter["schema_versions"], "adapter.schema_versions", maximum=16)
    if not versions or any(version != CONTRACT_VERSION for version in versions):
        raise MemoryContractError("adapter must explicitly support the current contract version")
    _enum(adapter["consistency"], {"none", "eventual", "read-after-write", "strong", "unknown"}, "adapter.consistency")
    _enum(adapter["isolation"], {"none", "repository", "workspace", "tenant", "unknown"}, "adapter.isolation")
    capabilities = _object(doc["capabilities"], "capabilities")
    _exact(capabilities, required=set(CAPABILITIES), label="capabilities")
    for name in CAPABILITIES:
        capability = _object(capabilities[name], f"capability.{name}")
        _exact(capability, required={"state", "semantics"}, label=f"capability.{name}")
        _enum(capability["state"], CAPABILITY_STATES, f"capability.{name}.state")
        semantics = _object(capability["semantics"], f"capability.{name}.semantics")
        if len(canonical_json(semantics).encode("utf-8")) > 2_048:
            raise MemoryContractError(f"capability.{name}.semantics is too large")
    _enum(doc["status"], HANDSHAKE_STATUSES, "capability handshake status")
    _timestamp(doc["observed_at"], "capability handshake observed_at")
    validate_extensions(doc["extensions"])
    return doc


def validate_query_request(value: Any) -> dict[str, Any]:
    doc = _object(value, "query request")
    _exact(
        doc,
        required={
            "contract_version", "kind", "operation_id", "request_id", "idempotency_key",
            "repository", "namespace", "scope", "record_kinds", "limit",
            "required_capabilities", "extensions",
        },
        label="query request",
    )
    if doc["contract_version"] != CONTRACT_VERSION or doc["kind"] != "query-request":
        raise MemoryContractError("unsupported query request contract")
    for field in ("operation_id", "request_id", "idempotency_key"):
        _identifier(doc[field], f"query request {field}")
    validate_repository_identity(doc["repository"])
    namespace = _string(doc["namespace"], "query request namespace", maximum=128)
    if not NAMESPACE.fullmatch(namespace):
        raise MemoryContractError("query request namespace has invalid syntax")
    scope = _array(doc["scope"], "query request scope", maximum=64)
    if not scope:
        raise MemoryContractError("query request scope must not be empty")
    for index, path in enumerate(scope):
        _relative_path(path, f"query request scope[{index}]")
    kinds = _array(doc["record_kinds"], "query request record_kinds", maximum=len(RECORD_KINDS))
    if not kinds or len(kinds) != len(set(kinds)):
        raise MemoryContractError("query request record_kinds must be unique and non-empty")
    for kind in kinds:
        _enum(kind, RECORD_KINDS, "query request record kind")
    _integer(doc["limit"], "query request limit", minimum=1, maximum=MAX_RECORDS)
    required = _array(doc["required_capabilities"], "query request required_capabilities", maximum=len(CAPABILITIES))
    if "read_query" not in required or len(required) != len(set(required)):
        raise MemoryContractError("query request requires unique capabilities including read_query")
    for capability in required:
        _enum(capability, set(CAPABILITIES), "query request required capability")
    validate_extensions(doc["extensions"])
    return doc


def validate_mutation_candidate(value: Any) -> dict[str, Any]:
    """Validate a future adapter operation candidate without authorizing it."""
    doc = _object(value, "mutation candidate request")
    _exact(
        doc,
        required={
            "contract_version", "kind", "operation", "operation_id", "request_id",
            "idempotency_key", "repository", "namespace", "target_record_id",
            "record", "reason", "eligibility_receipt_digest", "required_capabilities",
            "candidate_only", "external_write_authorized", "write_performed", "extensions",
        },
        label="mutation candidate request",
    )
    if doc["contract_version"] != CONTRACT_VERSION or doc["kind"] != "mutation-candidate-request":
        raise MemoryContractError("unsupported mutation candidate contract")
    operation = _enum(doc["operation"], {"upsert", "invalidate", "tombstone", "delete"}, "mutation candidate operation")
    for field in ("operation_id", "request_id", "idempotency_key", "target_record_id"):
        _identifier(doc[field], f"mutation candidate {field}")
    validate_repository_identity(doc["repository"])
    namespace = _string(doc["namespace"], "mutation candidate namespace", maximum=128)
    if not NAMESPACE.fullmatch(namespace):
        raise MemoryContractError("mutation candidate namespace has invalid syntax")
    if operation == "upsert":
        record = validate_record(doc["record"])
        if record["record_id"] != doc["target_record_id"]:
            raise MemoryContractError("upsert target must match the candidate record")
        if doc["reason"] is not None:
            raise MemoryContractError("upsert mutation reason must be null")
    else:
        if doc["record"] is not None:
            raise MemoryContractError("non-upsert mutation candidate cannot embed a record")
        _string(doc["reason"], "mutation candidate reason", maximum=512)
    _digest(doc["eligibility_receipt_digest"], "mutation candidate eligibility_receipt_digest")
    expected_capability = {
        "upsert": "write_upsert",
        "invalidate": "invalidate",
        "tombstone": "tombstone",
        "delete": "delete",
    }[operation]
    required = _array(doc["required_capabilities"], "mutation candidate required_capabilities", maximum=len(CAPABILITIES))
    if len(required) != len(set(required)) or expected_capability not in required:
        raise MemoryContractError("mutation candidate must require its exact operation capability")
    for capability in required:
        _enum(capability, set(CAPABILITIES), "mutation candidate required capability")
    if doc["candidate_only"] is not True:
        raise MemoryContractError("mutation candidate must remain candidate-only")
    if doc["external_write_authorized"] is not False:
        raise MemoryContractError("mutation candidate cannot authorize external write")
    if doc["write_performed"] is not False:
        raise MemoryContractError("V2b mutation candidate cannot perform a write")
    validate_extensions(doc["extensions"])
    return doc


def _validate_source_ref(value: Any, label: str) -> dict[str, Any]:
    ref = _object(value, label)
    _exact(ref, required={"kind", "locator", "digest"}, label=label)
    kind = _enum(ref["kind"], SOURCE_KINDS, f"{label}.kind")
    locator = _string(ref["locator"], f"{label}.locator", maximum=512)
    if kind in {"repository-artifact", "verification", "review"}:
        _relative_path(locator, f"{label}.locator")
    elif kind == "git-commit" and not re.fullmatch(r"[0-9a-f]{40}", locator):
        raise MemoryContractError(f"{label}.locator must be a Git commit")
    elif kind in {"platform", "chat", "worker", "memory"} and not IDENTIFIER.fullmatch(locator):
        raise MemoryContractError(f"{label}.locator must be opaque and non-dereferenceable")
    _digest(ref["digest"], f"{label}.digest")
    return ref


def record_body(record: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in record.items() if key != "canonical_digest"}


def validate_record(value: Any) -> dict[str, Any]:
    record = _object(value, "memory record")
    _exact(
        record,
        required={
            "contract_version", "kind", "record_id", "record_kind", "repository",
            "namespace", "scope", "content", "content_ref", "canonical_digest", "producer",
            "provenance", "created_at", "observed_at", "last_verified_at", "freshness",
            "sensitivity", "authority", "confidence", "lifecycle", "backend_locator",
            "idempotency", "required_capabilities", "extensions",
        },
        label="memory record",
    )
    if record["contract_version"] != CONTRACT_VERSION or record["kind"] != "memory-record":
        raise MemoryContractError("unsupported memory record contract")
    _identifier(record["record_id"], "memory record record_id")
    _enum(record["record_kind"], RECORD_KINDS, "memory record record_kind")
    validate_repository_identity(record["repository"])
    namespace = _string(record["namespace"], "memory record namespace", maximum=128)
    if not NAMESPACE.fullmatch(namespace):
        raise MemoryContractError("memory record namespace has invalid syntax")
    scope = _array(record["scope"], "memory record scope", maximum=64)
    if not scope:
        raise MemoryContractError("memory record scope must not be empty")
    for index, path in enumerate(scope):
        _relative_path(path, f"memory record scope[{index}]")
    content, content_ref = record["content"], record["content_ref"]
    if (content is None) == (content_ref is None):
        raise MemoryContractError("memory record requires exactly one of content or content_ref")
    if content is not None:
        _string(content, "memory record content", maximum=MAX_CONTENT_BYTES)
    if content_ref is not None:
        reference = _object(content_ref, "memory record content_ref")
        _exact(reference, required={"digest", "media_type"}, label="memory record content_ref")
        _digest(reference["digest"], "memory record content_ref.digest")
        _enum(reference["media_type"], {"text/plain", "application/json"}, "memory record content_ref.media_type")
    producer = _object(record["producer"], "memory record producer")
    _exact(producer, required={"producer_id", "producer_type", "source_identity_digest"}, label="memory record producer")
    _identifier(producer["producer_id"], "memory record producer.producer_id")
    _enum(producer["producer_type"], {"human", "agent", "tool", "adapter"}, "memory record producer.producer_type")
    _digest(producer["source_identity_digest"], "memory record producer.source_identity_digest")
    provenance = _object(record["provenance"], "memory record provenance")
    _exact(provenance, required={"source_refs", "source_revision", "evidence_digests"}, label="memory record provenance")
    refs = _array(provenance["source_refs"], "memory record provenance.source_refs", maximum=32)
    if not refs:
        raise MemoryContractError("memory record provenance requires source refs")
    for index, ref in enumerate(refs):
        _validate_source_ref(ref, f"memory record provenance.source_refs[{index}]")
    repository_sources = [ref["locator"] for ref in refs if ref["kind"] == "repository-artifact"]
    if not repository_sources:
        raise MemoryContractError("memory record provenance requires a repository-artifact source")
    if any(not _path_within(locator, scope) for locator in repository_sources):
        raise MemoryContractError("memory record repository-artifact provenance is outside record scope")
    source_revision = _object(provenance["source_revision"], "memory record provenance.source_revision")
    _exact(source_revision, required={"commit_sha"}, label="memory record provenance.source_revision")
    if not isinstance(source_revision["commit_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", source_revision["commit_sha"]):
        raise MemoryContractError("memory record provenance source revision must be exact")
    if source_revision["commit_sha"] != record["repository"]["source_revision"]["commit_sha"]:
        raise MemoryContractError("memory record provenance revision must match repository source revision")
    evidence = _array(provenance["evidence_digests"], "memory record provenance.evidence_digests", maximum=32)
    if not evidence or len(evidence) != len(set(evidence)):
        raise MemoryContractError("memory record provenance evidence digests must be unique and non-empty")
    for index, digest in enumerate(evidence):
        _digest(digest, f"memory record provenance.evidence_digests[{index}]")
    created = _timestamp(record["created_at"], "memory record created_at")
    observed = _timestamp(record["observed_at"], "memory record observed_at")
    verified = _timestamp(record["last_verified_at"], "memory record last_verified_at")
    if created > observed or observed > verified:
        raise MemoryContractError("memory record timestamps must be non-decreasing")
    freshness = _object(record["freshness"], "memory record freshness")
    _exact(freshness, required={"expires_at", "ttl_seconds", "retention_hint"}, label="memory record freshness")
    expires = _timestamp(freshness["expires_at"], "memory record freshness.expires_at")
    if expires < verified:
        raise MemoryContractError("memory record expiry cannot precede last verification")
    _integer(freshness["ttl_seconds"], "memory record freshness.ttl_seconds", minimum=0, maximum=31_536_000)
    if expires != verified + dt.timedelta(seconds=freshness["ttl_seconds"]):
        raise MemoryContractError("memory record expiry must equal last verification plus TTL")
    _enum(freshness["retention_hint"], {"ephemeral", "bounded", "durable-candidate"}, "memory record freshness.retention_hint")
    sensitivity = _object(record["sensitivity"], "memory record sensitivity")
    _exact(sensitivity, required={"classification", "contains_credentials", "contains_pii"}, label="memory record sensitivity")
    _enum(sensitivity["classification"], {"public", "internal", "confidential", "restricted", "secret"}, "memory record sensitivity.classification")
    _boolean(sensitivity["contains_credentials"], "memory record sensitivity.contains_credentials")
    _boolean(sensitivity["contains_pii"], "memory record sensitivity.contains_pii")
    if record["authority"] != "advisory":
        raise MemoryContractError("memory record authority must remain advisory")
    _integer(record["confidence"], "memory record confidence percentage", minimum=0, maximum=100)
    lifecycle = _object(record["lifecycle"], "memory record lifecycle")
    _exact(lifecycle, required={"state", "supersedes", "invalidates", "reason"}, label="memory record lifecycle")
    _enum(lifecycle["state"], {"active", "superseded", "tombstoned", "invalidated"}, "memory record lifecycle.state")
    for key in ("supersedes", "invalidates"):
        values = _array(lifecycle[key], f"memory record lifecycle.{key}", maximum=32)
        if len(values) != len(set(values)):
            raise MemoryContractError(f"memory record lifecycle.{key} must be unique")
        for item in values:
            _identifier(item, f"memory record lifecycle.{key}")
    if lifecycle["state"] != "active":
        _string(lifecycle["reason"], "memory record lifecycle.reason", maximum=512)
    elif lifecycle["reason"] is not None:
        raise MemoryContractError("active memory record lifecycle reason must be null")
    locator = _string(record["backend_locator"], "memory record backend_locator", maximum=512)
    if not IDENTIFIER.fullmatch(locator):
        raise MemoryContractError("memory record backend_locator must be opaque and non-dereferenceable")
    idempotency = _object(record["idempotency"], "memory record idempotency")
    _exact(idempotency, required={"request_id", "idempotency_key", "sequence"}, label="memory record idempotency")
    _identifier(idempotency["request_id"], "memory record idempotency.request_id")
    _identifier(idempotency["idempotency_key"], "memory record idempotency.idempotency_key")
    _integer(idempotency["sequence"], "memory record idempotency.sequence", minimum=0)
    required = _array(record["required_capabilities"], "memory record required_capabilities", maximum=len(CAPABILITIES))
    if len(required) != len(set(required)):
        raise MemoryContractError("memory record required capabilities must be unique")
    for capability in required:
        _enum(capability, set(CAPABILITIES), "memory record required capability")
    validate_extensions(record["extensions"])
    declared = _digest(record["canonical_digest"], "memory record canonical_digest")
    if declared != canonical_digest(record_body(record)):
        raise MemoryContractError("memory record canonical digest mismatch")
    return record


def response_body(response: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in response.items() if key != "response_digest"}


def validate_query_response(value: Any, request: dict[str, Any], *, validate_records: bool = True) -> dict[str, Any]:
    response = _object(value, "query response")
    _exact(
        response,
        required={
            "contract_version", "kind", "request_id", "operation_id", "request_digest",
            "adapter_id", "status", "records", "partial", "errors", "response_nonce",
            "response_digest", "extensions",
        },
        label="query response",
    )
    if response["contract_version"] != CONTRACT_VERSION or response["kind"] != "query-response":
        raise MemoryContractError("unsupported query response contract")
    validate_query_request(request)
    if response["request_id"] != request["request_id"] or response["operation_id"] != request["operation_id"]:
        raise MemoryContractError("query response request binding mismatch")
    if response["request_digest"] != canonical_digest(request):
        raise MemoryContractError("query response request digest mismatch")
    _identifier(response["adapter_id"], "query response adapter_id")
    status = _enum(response["status"], RESPONSE_STATUSES, "query response status")
    records = _array(response["records"], "query response records", maximum=request["limit"])
    if validate_records:
        for record in records:
            validate_record(record)
    _boolean(response["partial"], "query response partial")
    if response["partial"] is not (status == "partial"):
        raise MemoryContractError("query response partial flag must match status")
    errors = _array(response["errors"], "query response errors", maximum=32)
    for index, error in enumerate(errors):
        error = _object(error, f"query response errors[{index}]")
        _exact(error, required={"code", "message", "retryable"}, label=f"query response errors[{index}]")
        _identifier(error["code"], f"query response errors[{index}].code")
        _string(error["message"], f"query response errors[{index}].message", maximum=512)
        _boolean(error["retryable"], f"query response errors[{index}].retryable")
    _identifier(response["response_nonce"], "query response response_nonce")
    validate_extensions(response["extensions"])
    if _digest(response["response_digest"], "query response response_digest") != canonical_digest(response_body(response)):
        raise MemoryContractError("query response digest mismatch")
    return response


def _contains_injection(record: dict[str, Any]) -> bool:
    content = record.get("content")
    return isinstance(content, str) and any(pattern.search(content) for pattern in INJECTION_PATTERNS)


def _sensitive_content_indicators(record: dict[str, Any]) -> list[str]:
    content = record.get("content")
    if not isinstance(content, str):
        return []
    return [f"content-pattern-{index + 1}" for index, pattern in enumerate(SENSITIVE_CONTENT_PATTERNS) if pattern.search(content)]


def _path_within(path: str, roots: list[str]) -> bool:
    return any(root == "." or path == root or path.startswith(root + "/") for root in roots)


def _same_repository(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return left.get("repository_identity_digest") == right.get("repository_identity_digest")


def _receipt(body: dict[str, Any]) -> dict[str, Any]:
    receipt = copy.deepcopy(body)
    receipt["receipt_digest"] = canonical_digest(body)
    return receipt


def decide_retrieval(
    value: Any,
    *,
    trusted_conformance_receipts: dict[str, dict[str, str]] | None = None,
    trusted_source_digests: dict[str, str] | None = None,
) -> dict[str, Any]:
    doc = _object(value, "retrieval decision input")
    _exact(
        doc,
        required={"contract_version", "kind", "handshake", "request", "response", "current", "extensions"},
        label="retrieval decision input",
    )
    if doc["contract_version"] != CONTRACT_VERSION or doc["kind"] != "retrieval-decision-input":
        raise MemoryContractError("unsupported retrieval decision contract")
    handshake = validate_handshake(doc["handshake"])
    request = validate_query_request(doc["request"])
    response = validate_query_response(doc["response"], request, validate_records=False)
    current = _object(doc["current"], "retrieval current state")
    _exact(
        current,
        required={
            "repository", "namespace", "now", "clock_available", "source_revision_relations",
            "repo_conflicts", "instruction_conflicts", "conflicting_records", "seen_response_nonces",
            "seen_idempotency_keys", "max_clock_skew_seconds", "max_handshake_age_seconds",
        },
        label="retrieval current state",
    )
    current_repository = validate_repository_identity(current["repository"])
    current_namespace = _string(current["namespace"], "retrieval current namespace", maximum=128)
    now = _timestamp(current["now"], "retrieval current now")
    clock_available = _boolean(current["clock_available"], "retrieval current clock_available")
    max_clock_skew = _integer(current["max_clock_skew_seconds"], "retrieval current max_clock_skew_seconds", minimum=0, maximum=3_600)
    max_handshake_age = _integer(
        current["max_handshake_age_seconds"],
        "retrieval current max_handshake_age_seconds",
        minimum=0,
        maximum=86_400,
    )
    trusted_conformance = _object(trusted_conformance_receipts or {}, "trusted conformance receipts")
    for adapter_id, evidence in trusted_conformance.items():
        _identifier(adapter_id, "trusted conformance adapter id")
        evidence = _object(evidence, "trusted conformance receipt evidence")
        _exact(
            evidence,
            required={"receipt_digest", "adapter_fingerprint"},
            label="trusted conformance receipt evidence",
        )
        _digest(evidence["receipt_digest"], "trusted conformance receipt digest")
        _digest(evidence["adapter_fingerprint"], "trusted conformance adapter fingerprint")
    trusted_sources = _object(trusted_source_digests or {}, "trusted source digests")
    for locator, digest in trusted_sources.items():
        _relative_path(locator, "trusted source locator")
        _digest(digest, "trusted source digest")
    relations = _object(current["source_revision_relations"], "retrieval current source_revision_relations")
    validated_sets: dict[str, set[str]] = {}
    for key, label, maximum in (
        ("repo_conflicts", "repo conflict", MAX_RECORDS),
        ("instruction_conflicts", "instruction conflict", MAX_RECORDS),
        ("conflicting_records", "conflicting record", MAX_RECORDS),
        ("seen_response_nonces", "seen response nonce", 1_000),
        ("seen_idempotency_keys", "seen idempotency key", 1_000),
    ):
        values = _array(current[key], f"retrieval current {key}", maximum=maximum)
        identifiers = [_identifier(item, label) for item in values]
        if len(identifiers) != len(set(identifiers)):
            raise MemoryContractError(f"retrieval current {key} must be unique")
        validated_sets[key] = set(identifiers)
    repo_conflicts = validated_sets["repo_conflicts"]
    instruction_conflicts = validated_sets["instruction_conflicts"]
    conflicting_records = validated_sets["conflicting_records"]
    seen_nonces = validated_sets["seen_response_nonces"]
    seen_idempotency_keys = validated_sets["seen_idempotency_keys"]
    validate_extensions(doc["extensions"])

    capability_failures = [
        capability
        for capability in request["required_capabilities"]
        if handshake["capabilities"][capability]["state"] != "supported"
    ]
    fallback_reason: str | None = None
    adapter_fingerprint = canonical_digest({
        "adapter": handshake["adapter"],
        "capabilities": handshake["capabilities"],
    })
    trusted_adapter_evidence = trusted_conformance.get(handshake["adapter"]["adapter_id"])
    handshake_observed_at = _timestamp(
        handshake["observed_at"], "capability handshake observed_at"
    )
    if handshake["status"] != "ready":
        fallback_reason = f"adapter-{handshake['status']}"
    elif not trusted_adapter_evidence or trusted_adapter_evidence["adapter_fingerprint"] != adapter_fingerprint:
        fallback_reason = "untrusted-conformance-evidence"
    elif not clock_available:
        fallback_reason = "handshake-freshness-unknown-clock"
    elif handshake_observed_at > now + dt.timedelta(seconds=max_clock_skew):
        fallback_reason = "handshake-timestamp-in-future"
    elif handshake_observed_at < now - dt.timedelta(seconds=max_handshake_age):
        fallback_reason = "handshake-stale"
    elif handshake["adapter"]["adapter_id"] != response["adapter_id"]:
        fallback_reason = "adapter-identity-mismatch"
    elif capability_failures:
        fallback_reason = "required-capability-unavailable"
    elif response["status"] != "ok":
        fallback_reason = f"response-{response['status']}"
    elif response["response_nonce"] in seen_nonces:
        fallback_reason = "replayed-response"
    elif request["idempotency_key"] in seen_idempotency_keys:
        fallback_reason = "replayed-request"

    valid_records: list[dict[str, Any]] = []
    for raw_record in response["records"]:
        try:
            valid_records.append(validate_record(raw_record))
        except MemoryContractError:
            pass
    record_digests_by_id: dict[str, set[str]] = {}
    for record in valid_records:
        record_digests_by_id.setdefault(record["record_id"], set()).add(
            record["canonical_digest"]
        )
    conflicting_duplicate_ids = {
        record_id
        for record_id, digests in record_digests_by_id.items()
        if len(digests) > 1
    }

    def trusted_lifecycle_controller(record: dict[str, Any]) -> bool:
        repository_source_refs = [
            ref for ref in record["provenance"]["source_refs"]
            if ref["kind"] == "repository-artifact"
        ]
        return (
            _same_repository(record["repository"], current_repository)
            and _same_repository(record["repository"], request["repository"])
            and record["namespace"] == current_namespace
            and record["namespace"] == request["namespace"]
            and record["record_id"] not in conflicting_duplicate_ids
            and record["record_id"] not in conflicting_records
            and record["record_kind"] in request["record_kinds"]
            and bool(repository_source_refs)
            and all(
                trusted_sources.get(ref["locator"]) == ref["digest"]
                for ref in repository_source_refs
            )
            and relations.get(record["record_id"], "unknown") == "exact"
            and all(_path_within(path, request["scope"]) for path in record["scope"])
            and all(
                _path_within(path, record["repository"]["path_scope"])
                for path in record["scope"]
            )
            and record["record_id"] not in repo_conflicts
            and record["record_id"] not in instruction_conflicts
            and not _contains_injection(record)
            and not _sensitive_content_indicators(record)
            and record["content_ref"] is None
            and record["sensitivity"]["classification"] in {"public", "internal"}
            and record["sensitivity"]["contains_credentials"] is False
            and record["sensitivity"]["contains_pii"] is False
            and all(
                handshake["capabilities"][capability]["state"] == "supported"
                for capability in record["required_capabilities"]
            )
            and clock_available
            and all(
                _timestamp(record[field], f"record {field}")
                <= now + dt.timedelta(seconds=max_clock_skew)
                for field in ("created_at", "observed_at", "last_verified_at")
            )
            and _timestamp(record["freshness"]["expires_at"], "record expiry") >= now
        )

    dominated_record_ids: set[str] = set()
    for related in valid_records:
        if trusted_lifecycle_controller(related):
            dominated_record_ids.update(related["lifecycle"]["invalidates"])
            dominated_record_ids.update(related["lifecycle"]["supersedes"])

    dispositions: list[dict[str, Any]] = []
    for raw_record in response["records"]:
        record_id = raw_record.get("record_id") if isinstance(raw_record, dict) else "invalid-record"
        reasons: list[str] = []
        disposition = "adopt-as-context"
        try:
            record = validate_record(raw_record)
        except MemoryContractError as exc:
            dispositions.append({
                "record_id": record_id,
                "disposition": "reject",
                "reasons": [f"invalid-record:{exc}"],
                "authority": "advisory-only",
                "confidence_used_as_authority": False,
            })
            continue
        if record["record_id"] in conflicting_duplicate_ids:
            reasons.append("duplicate-record-id-with-conflicting-digest")
        if fallback_reason:
            reasons.append(fallback_reason)
        unsupported_record_capabilities = [
            capability
            for capability in record["required_capabilities"]
            if handshake["capabilities"][capability]["state"] != "supported"
        ]
        reasons.extend(
            f"record-required-capability-unavailable:{capability}"
            for capability in unsupported_record_capabilities
        )
        if not _same_repository(record["repository"], current_repository) or not _same_repository(record["repository"], request["repository"]):
            reasons.append("wrong-repository-or-principal")
        if record["namespace"] != current_namespace or record["namespace"] != request["namespace"]:
            reasons.append("wrong-namespace")
        if record["record_kind"] not in request["record_kinds"]:
            reasons.append("unexpected-record-kind")
        repository_source_refs = [
            ref for ref in record["provenance"]["source_refs"]
            if ref["kind"] == "repository-artifact"
        ]
        if any(trusted_sources.get(ref["locator"]) != ref["digest"] for ref in repository_source_refs):
            reasons.append("unverified-repository-provenance")
        if any(not _path_within(path, request["scope"]) for path in record["scope"]):
            reasons.append("record-outside-query-scope")
        if any(not _path_within(path, record["repository"]["path_scope"]) for path in record["scope"]):
            reasons.append("record-outside-repository-scope")
        if record["lifecycle"]["state"] != "active":
            reasons.append(f"record-{record['lifecycle']['state']}")
        if record["record_id"] in dominated_record_ids:
            reasons.append("invalidated-or-superseded-by-related-record")
        if record["record_id"] in repo_conflicts:
            reasons.append("contradicts-repository-truth")
        if record["record_id"] in instruction_conflicts:
            reasons.append("contradicts-current-user-instruction")
        if record["record_id"] in conflicting_records:
            reasons.append("conflicts-with-another-memory")
        if _contains_injection(record):
            reasons.append("prompt-injection-indicator")
        if _sensitive_content_indicators(record):
            reasons.append("detected-sensitive-content")
        if record["content_ref"] is not None:
            reasons.append("uninspected-content-reference")
        sensitivity = record["sensitivity"]
        if sensitivity["classification"] in {"restricted", "secret"} or sensitivity["contains_credentials"] or sensitivity["contains_pii"]:
            reasons.append("sensitive-or-secret-content")
        elif sensitivity["classification"] == "confidential":
            reasons.append("sensitive-content-requires-explicit-handling")
        relation = relations.get(record["record_id"], "unknown")
        _enum(relation, {"exact", "ancestor", "descendant", "diverged", "unknown"}, "source revision relation")
        if relation != "exact":
            reasons.append(f"source-revision-{relation}")
        if not clock_available:
            reasons.append("freshness-unknown-clock")
        else:
            skew_limit = now + dt.timedelta(seconds=max_clock_skew)
            if any(
                _timestamp(record[field], f"record {field}") > skew_limit
                for field in ("created_at", "observed_at", "last_verified_at")
            ):
                reasons.append("record-timestamp-in-future")
            if _timestamp(record["freshness"]["expires_at"], "record expiry") < now:
                reasons.append("record-expired")

        reject_prefixes = (
            "wrong-repository", "wrong-namespace", "record-tombstoned", "record-invalidated",
            "contradicts-repository", "contradicts-current", "sensitive-or-secret",
            "detected-sensitive", "duplicate-record", "replayed-response",
            "replayed-request",
            "record-outside", "invalidated-or-superseded",
            "unverified-repository-provenance",
        )
        if any(reason.startswith(reject_prefixes) for reason in reasons):
            disposition = "reject"
        elif reasons:
            disposition = "quarantine"
        dispositions.append({
            "record_id": record["record_id"],
            "record_digest": record["canonical_digest"],
            "disposition": disposition,
            "reasons": sorted(set(reasons)),
            "authority": "advisory-only",
            "confidence_used_as_authority": False,
        })

    body = {
        "contract_version": CONTRACT_VERSION,
        "kind": "memory-retrieval-receipt",
        "request_id": request["request_id"],
        "operation_id": request["operation_id"],
        "request_digest": canonical_digest(request),
        "response_digest": response["response_digest"],
        "trusted_conformance_digest": (
            trusted_adapter_evidence["receipt_digest"] if trusted_adapter_evidence else None
        ),
        "adapter_fingerprint": adapter_fingerprint,
        "trusted_source_set_digest": canonical_digest(trusted_sources),
        "repository_identity_digest": current_repository["repository_identity_digest"],
        "namespace": current_namespace,
        "fallback_to_no_memory": fallback_reason is not None,
        "fallback_reason": fallback_reason,
        "dispositions": dispositions,
        "authority_invariants": {
            "data_only": True,
            "mutation_authorized": False,
            "external_write_authorized": False,
            "gate_satisfied": False,
            "completion_proven": False,
            "model_or_confidence_cannot_raise_authority": True,
        },
    }
    return _receipt(body)


def _validate_acceptance_receipt(value: Any, label: str) -> dict[str, Any]:
    receipt = _object(value, label)
    _exact(
        receipt,
        required={
            "contract_version", "kind", "evidence_kind", "evidence_digest",
            "source_revision", "candidate_record_digest", "accepted", "extensions", "receipt_digest",
        },
        label=label,
    )
    if receipt["contract_version"] != CONTRACT_VERSION or receipt["kind"] != "accepted-evidence-receipt":
        raise MemoryContractError(f"{label} has unsupported receipt contract")
    _enum(receipt["evidence_kind"], {"verification", "review", "platform"}, f"{label}.evidence_kind")
    _digest(receipt["evidence_digest"], f"{label}.evidence_digest")
    _digest(receipt["candidate_record_digest"], f"{label}.candidate_record_digest")
    revision = _object(receipt["source_revision"], f"{label}.source_revision")
    _exact(revision, required={"commit_sha"}, label=f"{label}.source_revision")
    if not isinstance(revision["commit_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", revision["commit_sha"]):
        raise MemoryContractError(f"{label}.source_revision must be an exact Git commit")
    if receipt["accepted"] is not True:
        raise MemoryContractError(f"{label} must be explicitly accepted")
    validate_extensions(receipt["extensions"])
    declared = _digest(receipt["receipt_digest"], f"{label}.receipt_digest")
    if declared != canonical_digest({key: copy.deepcopy(item) for key, item in receipt.items() if key != "receipt_digest"}):
        raise MemoryContractError(f"{label} digest mismatch")
    return receipt


def decide_write_eligibility(
    value: Any,
    *,
    trusted_acceptance_receipt_digests: list[str] | None = None,
) -> dict[str, Any]:
    doc = _object(value, "write eligibility input")
    _exact(
        doc,
        required={"contract_version", "kind", "record", "accepted_evidence", "basis", "extensions"},
        label="write eligibility input",
    )
    if doc["contract_version"] != CONTRACT_VERSION or doc["kind"] != "write-eligibility-input":
        raise MemoryContractError("unsupported write eligibility contract")
    record = validate_record(doc["record"])
    accepted_items = _array(doc["accepted_evidence"], "accepted evidence", maximum=64)
    trusted_receipts = _array(trusted_acceptance_receipt_digests or [], "trusted acceptance receipt digests", maximum=64)
    for index, digest in enumerate(trusted_receipts):
        _digest(digest, f"trusted acceptance receipt digests[{index}]")
    if len(trusted_receipts) != len(set(trusted_receipts)):
        raise MemoryContractError("trusted acceptance receipt digests must be unique")
    trusted_receipt_set = set(trusted_receipts)
    accepted_digests: list[str] = []
    accepted_kinds: set[str] = set()
    untrusted_receipts = False
    for index, raw_item in enumerate(accepted_items):
        item = _validate_acceptance_receipt(raw_item, f"accepted evidence[{index}]")
        kind = item["evidence_kind"]
        accepted_kinds.add(kind)
        accepted_digests.append(item["evidence_digest"])
        if item["source_revision"]["commit_sha"] != record["repository"]["source_revision"]["commit_sha"]:
            untrusted_receipts = True
        if item["candidate_record_digest"] != record["canonical_digest"]:
            untrusted_receipts = True
        if item["receipt_digest"] not in trusted_receipt_set:
            untrusted_receipts = True
    if len(accepted_digests) != len(set(accepted_digests)):
        raise MemoryContractError("accepted evidence digests must be unique")
    basis = _object(doc["basis"], "write eligibility basis")
    _exact(
        basis,
        required={"durable_lesson", "root_cause_verified", "verification_accepted", "review_accepted"},
        label="write eligibility basis",
    )
    for key in basis:
        _boolean(basis[key], f"write eligibility basis.{key}")
    validate_extensions(doc["extensions"])
    reasons: list[str] = []
    if record["record_kind"] != "durable-lesson" or not basis["durable_lesson"]:
        reasons.append("not-a-durable-lesson")
    if not basis["root_cause_verified"]:
        reasons.append("root-cause-unverified")
    if not basis["verification_accepted"] or "verification" not in accepted_kinds:
        reasons.append("verification-not-accepted")
    if not basis["review_accepted"] or "review" not in accepted_kinds:
        reasons.append("review-not-accepted")
    if untrusted_receipts or not accepted_items:
        reasons.append("acceptance-receipt-untrusted-or-revision-mismatched")
    evidence = set(record["provenance"]["evidence_digests"])
    if not evidence.issubset(set(accepted_digests)):
        reasons.append("accepted-evidence-incomplete")
    source_kinds = {ref["kind"] for ref in record["provenance"]["source_refs"]}
    if source_kinds & {"chat", "worker", "memory"}:
        reasons.append("non-authoritative-source-kind")
    sensitivity = record["sensitivity"]
    if sensitivity["classification"] not in {"public", "internal"} or sensitivity["contains_credentials"] or sensitivity["contains_pii"]:
        reasons.append("sensitive-write-candidate")
    if record["lifecycle"]["state"] != "active":
        reasons.append("inactive-write-candidate")
    if _contains_injection(record):
        reasons.append("prompt-injection-indicator")
    if _sensitive_content_indicators(record):
        reasons.append("detected-sensitive-content")
    body = {
        "contract_version": CONTRACT_VERSION,
        "kind": "memory-write-eligibility-receipt",
        "record_id": record["record_id"],
        "record_digest": record["canonical_digest"],
        "eligible": not reasons,
        "reasons": sorted(set(reasons)),
        "authority_invariants": {
            "candidate_only": True,
            "write_performed": False,
            "external_write_authorized": False,
            "completion_proven": False,
        },
    }
    return _receipt(body)


def validate_conformance(
    value: Any,
    *,
    trusted_source_digests: dict[str, str] | None = None,
    trusted_acceptance_receipt_digests: list[str] | None = None,
) -> dict[str, Any]:
    doc = _object(value, "adapter conformance transcript")
    _exact(
        doc,
        required={"contract_version", "kind", "adapter_id", "handshake", "cases", "extensions"},
        label="adapter conformance transcript",
    )
    if doc["contract_version"] != CONTRACT_VERSION or doc["kind"] != "adapter-conformance-transcript":
        raise MemoryContractError("unsupported adapter conformance transcript")
    adapter_id = _identifier(doc["adapter_id"], "adapter conformance adapter_id")
    handshake = validate_handshake(doc["handshake"])
    if handshake["adapter"]["adapter_id"] != adapter_id:
        raise MemoryContractError("conformance adapter identity mismatch")
    adapter_fingerprint = canonical_digest({
        "adapter": handshake["adapter"],
        "capabilities": handshake["capabilities"],
    })
    trusted_sources = _object(trusted_source_digests or {}, "conformance trusted_source_digests")
    for locator, digest in trusted_sources.items():
        _relative_path(locator, "conformance trusted source locator")
        _digest(digest, "conformance trusted source digest")
    trusted_acceptance_receipts = _array(
        trusted_acceptance_receipt_digests or [],
        "conformance trusted acceptance receipt digests",
        maximum=64,
    )
    for index, digest in enumerate(trusted_acceptance_receipts):
        _digest(digest, f"conformance trusted acceptance receipt digests[{index}]")
    cases = _array(doc["cases"], "adapter conformance cases", maximum=128)
    if not cases:
        raise MemoryContractError("adapter conformance requires cases")
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    for index, raw_case in enumerate(cases):
        case = _object(raw_case, f"adapter conformance cases[{index}]")
        _exact(case, required={"case_id", "decision_kind", "input", "expected"}, label=f"adapter conformance cases[{index}]")
        case_id = _identifier(case["case_id"], f"adapter conformance cases[{index}].case_id")
        if case_id in seen:
            raise MemoryContractError(f"duplicate conformance case id: {case_id}")
        seen.add(case_id)
        decision_kind = _enum(case["decision_kind"], {"retrieval", "write-eligibility"}, "conformance decision kind")
        case_input = _object(
            case["input"], f"adapter conformance cases[{index}].input"
        )
        if decision_kind == "retrieval":
            case_handshake = validate_handshake(case_input.get("handshake"))
            if case_handshake["adapter"]["adapter_id"] != adapter_id:
                raise MemoryContractError(f"conformance case {case_id} adapter identity mismatch")
            if canonical_digest({"adapter": case_handshake["adapter"], "capabilities": case_handshake["capabilities"]}) != canonical_digest({"adapter": handshake["adapter"], "capabilities": handshake["capabilities"]}):
                raise MemoryContractError(f"conformance case {case_id} handshake mismatch")
            result = decide_retrieval(
                case_input,
                # The harness exercises the trusted path internally. Its emitted
                # receipt digest is the only value callers may trust later.
                trusted_conformance_receipts={adapter_id: {
                    "receipt_digest": canonical_digest({"adapter_id": adapter_id, "purpose": "conformance-evaluation"}),
                    "adapter_fingerprint": adapter_fingerprint,
                }},
                trusted_source_digests=trusted_sources,
            )
        else:
            result = decide_write_eligibility(
                case_input,
                trusted_acceptance_receipt_digests=trusted_acceptance_receipts,
            )
        expected = _object(case["expected"], f"adapter conformance cases[{index}].expected")
        required_expectation = MANDATORY_CONFORMANCE_EXPECTATIONS.get(case_id)
        if required_expectation is None or expected != required_expectation:
            raise MemoryContractError(f"conformance case {case_id} must use the mandatory oracle")
        mismatches = {key: {"expected": value, "actual": result.get(key)} for key, value in expected.items() if result.get(key) != value}
        if case_id == "retrieval-valid" and (
            not result.get("dispositions")
            or any(item.get("disposition") != "adopt-as-context" for item in result["dispositions"])
        ):
            mismatches["mandatory_semantics"] = {"expected": "all-adopt-as-context", "actual": result.get("dispositions")}
        if case_id in {"retrieval-disabled", "retrieval-partial"} and any(
            item.get("disposition") != "quarantine" for item in result.get("dispositions", [])
        ):
            mismatches["mandatory_semantics"] = {"expected": "all-quarantine", "actual": result.get("dispositions")}
        if case_id == "write-sensitive" and not any(
            reason in {"sensitive-write-candidate", "detected-sensitive-content"}
            for reason in result.get("reasons", [])
        ):
            mismatches["mandatory_semantics"] = {"expected": "sensitivity-rejection", "actual": result.get("reasons")}
        results.append({"case_id": case_id, "passed": not mismatches, "mismatches": mismatches})
    if seen != set(MANDATORY_CONFORMANCE_EXPECTATIONS):
        raise MemoryContractError("conformance transcript must cover the exact mandatory case inventory")
    validate_extensions(doc["extensions"])
    body = {
        "contract_version": CONTRACT_VERSION,
        "kind": "adapter-conformance-receipt",
        "adapter_id": adapter_id,
        "adapter_fingerprint": adapter_fingerprint,
        "transcript_digest": canonical_digest(doc),
        "trusted_source_set_digest": canonical_digest(trusted_sources),
        "trusted_acceptance_receipt_set_digest": canonical_digest(
            sorted(trusted_acceptance_receipts)
        ),
        "passed": all(result["passed"] for result in results),
        "total_cases": len(results),
        "results": results,
        "production_backend_implemented": False,
    }
    return _receipt(body)


def build_rejection_receipt(document: dict[str, Any], error: str) -> dict[str, Any]:
    body = {
        "contract_version": CONTRACT_VERSION,
        "kind": "memory-contract-rejection-receipt",
        "document_digest": canonical_digest(document),
        "error": _string(error, "rejection error", maximum=2_048),
        "authority_invariants": {
            "mutation_authorized": False,
            "external_write_authorized": False,
            "completion_proven": False,
        },
    }
    return _receipt(body)


def validate_document(document: dict[str, Any]) -> dict[str, Any]:
    kind = document.get("kind") if isinstance(document, dict) else None
    if kind == "capability-handshake":
        validate_handshake(document)
    elif kind == "query-request":
        validate_query_request(document)
    elif kind == "memory-record":
        validate_record(document)
    elif kind == "mutation-candidate-request":
        validate_mutation_candidate(document)
    elif kind == "retrieval-decision-input":
        decide_retrieval(document)
    elif kind == "write-eligibility-input":
        decide_write_eligibility(document)
    elif kind == "adapter-conformance-transcript":
        validate_conformance(document)
    else:
        raise MemoryContractError(f"unsupported memory contract kind: {kind!r}")
    return {"status": "valid", "contract_version": CONTRACT_VERSION, "kind": kind, "document_digest": canonical_digest(document)}
