#!/usr/bin/env python3
"""Strict offline Loop Engineering Operational Evidence V0 contract."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import stat
import types
from collections.abc import Iterable, Mapping, Set
from typing import Any


CONTRACT_VERSION = "loop-operational-evidence/v0"
MAX_DOCUMENT_BYTES = 131_072
MAX_DEPTH = 32
MAX_STRING_BYTES = 512
MAX_ARRAY_ITEMS = 256
MAX_SET_DOCUMENTS = 256
MAX_SAFE_INTEGER = 9_007_199_254_740_991

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
GIT_COMMIT = re.compile(r"^[0-9a-f]{40}$")
ASCII_KEY = re.compile(r"^[\x20-\x7e]+$")
RELATIVE_PATH = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$")
TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    r"(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)

DOCUMENT_KINDS = frozenset({
    "run-receipt",
    "iteration-summary",
    "failure-summary",
    "environment-fingerprint",
    "artifact-reference-set",
})
PRODUCER_KINDS = frozenset({"human", "agent", "tool", "ci"})
EXECUTION_MODES = frozenset({
    "current-session",
    "shared-subagents",
    "sequential-fallback",
    "ci",
})
PHASES = frozenset({
    "bootstrap",
    "planning",
    "implementation",
    "verification",
    "review",
    "integration",
    "release-preparation",
})
FAILURE_CODES: Mapping[str, frozenset[str]] = types.MappingProxyType({
    "contract-validation": frozenset({
        "malformed-document",
        "unsupported-version",
        "unknown-field",
        "duplicate-key",
        "digest-mismatch",
        "reference-mismatch",
    }),
    "source-conflict": frozenset({
        "repository-mismatch",
        "revision-mismatch",
        "identity-conflict",
    }),
    "authority-boundary": frozenset({
        "invariant-violation",
        "authorization-required",
        "completion-evidence-prohibited",
        "promotion-prohibited",
    }),
    "privacy-redaction": frozenset({
        "sensitive-data-detected",
        "private-path-detected",
        "raw-log-detected",
        "prohibited-environment-field",
    }),
    "capability": frozenset({"capability-unavailable", "capability-unsupported"}),
    "tooling": frozenset({"tool-failed", "tool-output-invalid"}),
    "verification": frozenset({"verification-failed", "verification-skipped"}),
    "review": frozenset({"review-blocked", "review-incomplete"}),
    "integration": frozenset({"worker-evidence-invalid", "integration-rejected"}),
    "resource-bound": frozenset({"timeout", "size-limit", "count-limit"}),
    "external-action-gate": frozenset({
        "human-gate-pending",
        "external-write-not-authorized",
    }),
    "unclassified": frozenset({"unclassified"}),
})
ARTIFACT_LOCATORS: Mapping[str, frozenset[str]] = types.MappingProxyType({
    "loop-ledger": frozenset({"repository-relative-path"}),
    "loop-event": frozenset({"repository-relative-path"}),
    "route-receipt": frozenset({"repository-relative-path"}),
    "worker-receipt": frozenset({"repository-relative-path"}),
    "integration-receipt": frozenset({"repository-relative-path"}),
    "memory-receipt": frozenset({"repository-relative-path"}),
    "verification": frozenset({"repository-relative-path"}),
    "review": frozenset({"repository-relative-path"}),
    "git-commit": frozenset({"git-commit"}),
    "platform-artifact": frozenset({"opaque-id"}),
    "gitnexus-fingerprint": frozenset({"repository-relative-path", "opaque-id"}),
    "other-public-artifact": frozenset({"repository-relative-path"}),
})
MEDIA_TYPES = frozenset({
    "application/json",
    "application/yaml",
    "text/markdown",
    "text/plain",
})
_AUTHORITY_INVARIANT_ITEMS = (
    ("used_as_authorization", False),
    ("used_as_completion_evidence", False),
    ("external_write_authorized", False),
    ("promotion_authorized", False),
)


def authority_invariants() -> dict[str, bool]:
    """Return a fresh exact false-authority contract object."""
    return dict(_AUTHORITY_INVARIANT_ITEMS)


AUTHORITY_INVARIANTS: Mapping[str, bool] = types.MappingProxyType(
    authority_invariants()
)

PRIVATE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I),
    re.compile(
        r"(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
        r"\s*[:=]\s*\S+",
        re.I,
    ),
    re.compile(r"\bBearer\s+\S+", re.I),
    re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,255}|"
        r"github_pat_[A-Za-z0-9_]{20,255})\b"
    ),
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    re.compile(
        r"(?:^|[\s\"'=])(?:/(?:Users|home)/|[A-Za-z]:\\Users\\|file://|~/)"
    ),
    re.compile(r"[a-z][a-z0-9+.-]*://[^/\s:@]+:[^@\s/]+@", re.I),
)
RAW_LOG_PATTERNS = (
    re.compile(r"Traceback \(most recent call last\)", re.I),
    re.compile(r"(?:^|\n)\s+at\s+\S+\s+\([^)\n]+:\d+:\d+\)", re.I),
    re.compile(
        r"(?:^|\n)\d{4}-\d{2}-\d{2}[T ][^\n]+\s+(?:DEBUG|INFO|WARN|ERROR)\b",
        re.I,
    ),
    re.compile(r"(?:^|\n)(?:\$|>)\s+\S+.*\n(?:stdout|stderr):", re.I),
)


class OperationalEvidenceError(ValueError):
    """A stable, non-echoing contract rejection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> OperationalEvidenceError:
    return OperationalEvidenceError(code, message)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _error("duplicate-key", "document contains a duplicate object key")
        result[key] = value
    return result


def load_json(path: pathlib.Path) -> dict[str, Any]:
    """Read one bounded regular non-symlink JSON document."""
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise _error(
                "file-boundary",
                "document must be a regular non-symlink file",
            )
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if (
                not stat.S_ISREG(opened.st_mode)
                or (before.st_dev, before.st_ino)
                != (opened.st_dev, opened.st_ino)
            ):
                raise _error(
                    "file-boundary",
                    "document must be a stable regular non-symlink file",
                )
            chunks = []
            remaining = MAX_DOCUMENT_BYTES + 1
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise _error("file-boundary", "document could not be read safely") from exc
    return load_json_bytes(raw)


def load_json_bytes(raw: bytes) -> dict[str, Any]:
    """Parse one bounded immutable JSON byte snapshot."""
    if not isinstance(raw, bytes):
        raise _error("invalid-json", "document must be supplied as bytes")
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise _error("document-size", "document exceeds the encoded size bound")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise _error("invalid-encoding", "document must be valid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                _error("invalid-json", "document contains a non-finite value")
            ),
        )
    except OperationalEvidenceError:
        raise
    except (ValueError, RecursionError) as exc:
        raise _error("invalid-json", "document is not valid bounded JSON") from exc
    if not isinstance(value, dict):
        raise _error("invalid-structure", "document must be a JSON object")
    return value


def _privacy_check(value: str) -> None:
    if any(pattern.search(value) for pattern in PRIVATE_PATTERNS):
        raise _error("privacy-violation", "document contains prohibited sensitive data")
    if any(pattern.search(value) for pattern in RAW_LOG_PATTERNS):
        raise _error("privacy-violation", "document contains prohibited raw log data")


def _finite(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise _error("invalid-structure", "document exceeds the nesting depth bound")
    if isinstance(value, float):
        raise _error("invalid-structure", "floating-point values are unsupported")
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_SAFE_INTEGER:
            raise _error("invalid-structure", "integer exceeds the safe range")
    if isinstance(value, str):
        try:
            encoded = value.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise _error("invalid-structure", "string contains invalid Unicode") from exc
        if len(encoded) > MAX_STRING_BYTES:
            raise _error("invalid-structure", "string exceeds the encoded size bound")
        _privacy_check(value)
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or not ASCII_KEY.fullmatch(key):
                raise _error("invalid-structure", "object key is unsupported")
            if len(key.encode("ascii")) > MAX_STRING_BYTES:
                raise _error("invalid-structure", "object key exceeds the size bound")
            _privacy_check(key)
            _finite(child, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_ARRAY_ITEMS:
            raise _error("invalid-structure", "array exceeds the item count bound")
        for child in value:
            _finite(child, depth=depth + 1)
    elif value is not None and not isinstance(value, (bool, int)):
        raise _error("invalid-structure", "document contains an unsupported value")


def canonical_json(value: Any) -> str:
    _finite(value)
    return _canonical_json_unchecked(value)


def _canonical_json_unchecked(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def document_body(document: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in document.items()
        if key != "document_digest"
    }


def seal_document(document: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with a canonical document digest; performs no I/O."""
    sealed = copy.deepcopy(document)
    sealed.pop("document_digest", None)
    sealed["document_digest"] = canonical_digest(sealed)
    return sealed


def _object(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _error("invalid-structure", "field must be an object")
    return value


def _array(value: Any, *, maximum: int = MAX_ARRAY_ITEMS) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise _error("invalid-structure", "field must be a bounded array")
    return value


def _exact(
    value: dict[str, Any],
    *,
    required: set[str],
) -> None:
    if set(value) != required:
        raise _error("invalid-structure", "object has missing or unknown fields")


def _string(value: Any, *, maximum: int = MAX_STRING_BYTES) -> str:
    if not isinstance(value, str) or not value:
        raise _error("invalid-structure", "field must be a non-empty string")
    try:
        encoded = value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise _error("invalid-structure", "string contains invalid Unicode") from exc
    if len(encoded) > maximum:
        raise _error("invalid-structure", "string exceeds the field bound")
    _privacy_check(value)
    return value


def _identifier(value: Any) -> str:
    value = _string(value, maximum=128)
    if not IDENTIFIER.fullmatch(value):
        raise _error("invalid-structure", "field must be an opaque identifier")
    return value


def _digest(value: Any) -> str:
    if not isinstance(value, str) or not DIGEST.fullmatch(value):
        raise _error("invalid-structure", "field must be a lowercase SHA-256 digest")
    return value


def _integer(value: Any, *, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error("invalid-structure", "field must be an integer")
    if not minimum <= value <= maximum:
        raise _error("invalid-structure", "integer is outside the field range")
    return value


def _enum(value: Any, allowed: Set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise _error("invalid-structure", "field contains an unsupported enum value")
    return value


def _timestamp(value: Any) -> dt.datetime:
    value = _string(value, maximum=64)
    if not TIMESTAMP.fullmatch(value):
        raise _error("invalid-structure", "field must be an ISO-8601 timestamp")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(candidate)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise _error(
                "invalid-structure",
                "timestamp requires an explicit timezone",
            )
        return parsed.astimezone(dt.timezone.utc)
    except OperationalEvidenceError:
        raise
    except (ValueError, OverflowError) as exc:
        raise _error(
            "invalid-structure",
            "field must be an ISO-8601 timestamp",
        ) from exc


def _relative_path(value: Any) -> str:
    value = _string(value)
    parsed = pathlib.PurePosixPath(value)
    if (
        not RELATIVE_PATH.fullmatch(value)
        or ".." in parsed.parts
        or "." in parsed.parts
        or str(parsed) != value
    ):
        raise _error(
            "invalid-structure",
            "locator must be a normalized repository-relative path",
        )
    return value


def _document_ref(value: Any) -> dict[str, Any]:
    reference = _object(value)
    _exact(reference, required={"document_id", "document_digest"})
    _identifier(reference["document_id"])
    _digest(reference["document_digest"])
    return reference


def _source_revision(value: Any) -> dict[str, Any]:
    source = _object(value)
    _exact(source, required={"repository_id", "commit_sha"})
    _identifier(source["repository_id"])
    if not isinstance(source["commit_sha"], str) or not GIT_COMMIT.fullmatch(
        source["commit_sha"]
    ):
        raise _error("invalid-structure", "source revision requires an exact Git commit")
    return source


def _producer(value: Any) -> dict[str, Any]:
    producer = _object(value)
    _exact(producer, required={"kind", "id"})
    _enum(producer["kind"], PRODUCER_KINDS)
    _identifier(producer["id"])
    return producer


def _validate_run(payload: dict[str, Any]) -> None:
    _exact(
        payload,
        required={
            "started_at",
            "ended_at",
            "execution_mode",
            "outcome",
            "iteration_summaries",
            "environment_fingerprint",
            "artifact_reference_set",
            "failure_summaries",
            "verification_observation",
            "review_observation",
            "human_gate_observation",
        },
    )
    started, ended = _timestamp(payload["started_at"]), _timestamp(payload["ended_at"])
    if started > ended:
        raise _error("invalid-structure", "run timestamps are inconsistent")
    _enum(payload["execution_mode"], EXECUTION_MODES)
    _enum(
        payload["outcome"],
        {"work-recorded", "stopped-failure", "stopped-human-gate", "cancelled"},
    )
    iterations = _array(payload["iteration_summaries"])
    failures = _array(payload["failure_summaries"])
    for item in iterations + failures:
        _document_ref(item)
    if len({item["document_id"] for item in iterations}) != len(iterations):
        raise _error("invalid-structure", "document references must be unique")
    if len({item["document_id"] for item in failures}) != len(failures):
        raise _error("invalid-structure", "document references must be unique")
    _document_ref(payload["environment_fingerprint"])
    _document_ref(payload["artifact_reference_set"])
    _enum(
        payload["verification_observation"],
        {"not-run", "passed", "failed", "skipped"},
    )
    _enum(
        payload["review_observation"],
        {"not-required", "required", "passed", "blocked"},
    )
    _enum(
        payload["human_gate_observation"],
        {"not-required", "pending", "satisfied"},
    )


def _validate_iteration(payload: dict[str, Any]) -> None:
    _exact(
        payload,
        required={
            "sequence",
            "phase",
            "result",
            "task_id",
            "started_at",
            "ended_at",
            "artifact_ids",
            "failure_summaries",
        },
    )
    _integer(payload["sequence"], minimum=1)
    _enum(payload["phase"], PHASES)
    _enum(
        payload["result"],
        {"continue", "handoff-prepared", "blocked-by-human-gate", "work-recorded"},
    )
    if payload["task_id"] is not None:
        _identifier(payload["task_id"])
    started, ended = _timestamp(payload["started_at"]), _timestamp(payload["ended_at"])
    if started > ended:
        raise _error("invalid-structure", "iteration timestamps are inconsistent")
    artifacts = _array(payload["artifact_ids"])
    for item in artifacts:
        _identifier(item)
    if len(artifacts) != len(set(artifacts)):
        raise _error("invalid-structure", "artifact ids must be unique")
    failures = _array(payload["failure_summaries"])
    for item in failures:
        _document_ref(item)
    if len({item["document_id"] for item in failures}) != len(failures):
        raise _error("invalid-structure", "failure references must be unique")


def _validate_failure(payload: dict[str, Any]) -> None:
    _exact(
        payload,
        required={
            "iteration_sequence",
            "phase",
            "category",
            "code",
            "retry",
            "artifact_ids",
        },
    )
    if payload["iteration_sequence"] is not None:
        _integer(payload["iteration_sequence"], minimum=1, maximum=1_000_000)
    _enum(payload["phase"], PHASES)
    category = _enum(payload["category"], set(FAILURE_CODES))
    _enum(payload["code"], FAILURE_CODES[category])
    _enum(payload["retry"], {"never", "manual", "after-input", "after-environment-change"})
    artifacts = _array(payload["artifact_ids"])
    for item in artifacts:
        _identifier(item)
    if len(artifacts) != len(set(artifacts)):
        raise _error("invalid-structure", "artifact ids must be unique")


def _validate_environment(payload: dict[str, Any]) -> None:
    _exact(
        payload,
        required={
            "runtime_surface",
            "os_family",
            "architecture",
            "python",
            "execution_mode",
            "sandbox_mode",
            "redaction_applied",
            "prohibited_fields_present",
        },
    )
    _enum(payload["runtime_surface"], {"codex-cli", "codex-desktop", "codex-ide", "ci", "other"})
    _enum(payload["os_family"], {"macos", "linux", "windows", "other"})
    _enum(payload["architecture"], {"arm64", "x86_64", "other"})
    python = _object(payload["python"])
    _exact(python, required={"major", "minor"})
    _integer(python["major"], maximum=99)
    _integer(python["minor"], maximum=99)
    _enum(payload["execution_mode"], EXECUTION_MODES)
    _enum(
        payload["sandbox_mode"],
        {"read-only", "workspace-write", "danger-full-access", "unknown"},
    )
    if payload["redaction_applied"] is not True:
        raise _error("privacy-violation", "environment redaction must be explicit")
    if payload["prohibited_fields_present"] is not False:
        raise _error("privacy-violation", "environment contains prohibited fields")


def _validate_artifact_set(payload: dict[str, Any]) -> None:
    _exact(payload, required={"artifacts"})
    artifacts = _array(payload["artifacts"])
    ids: set[str] = set()
    identities: set[tuple[str, str]] = set()
    for item in artifacts:
        artifact = _object(item)
        _exact(
            artifact,
            required={
                "artifact_id",
                "artifact_kind",
                "locator_kind",
                "locator",
                "content_sha256",
                "media_type",
            },
        )
        artifact_id = _identifier(artifact["artifact_id"])
        kind = _enum(artifact["artifact_kind"], set(ARTIFACT_LOCATORS))
        locator_kind = _enum(
            artifact["locator_kind"],
            {"repository-relative-path", "git-commit", "opaque-id"},
        )
        if locator_kind not in ARTIFACT_LOCATORS[kind]:
            raise _error("invalid-structure", "artifact kind and locator kind conflict")
        locator = artifact["locator"]
        if locator_kind == "repository-relative-path":
            locator = _relative_path(locator)
        elif locator_kind == "git-commit":
            if not isinstance(locator, str) or not GIT_COMMIT.fullmatch(locator):
                raise _error("invalid-structure", "artifact locator must be a Git commit")
        else:
            locator = _identifier(locator)
        digest = _digest(artifact["content_sha256"])
        _enum(artifact["media_type"], MEDIA_TYPES)
        if artifact_id in ids or (locator, digest) in identities:
            raise _error("invalid-structure", "artifact identities must be unique")
        ids.add(artifact_id)
        identities.add((locator, digest))


VALIDATORS: Mapping[str, Any] = types.MappingProxyType({
    "run-receipt": _validate_run,
    "iteration-summary": _validate_iteration,
    "failure-summary": _validate_failure,
    "environment-fingerprint": _validate_environment,
    "artifact-reference-set": _validate_artifact_set,
})


def validate_document(value: Any) -> dict[str, Any]:
    document = _object(value)
    _finite(document)
    if (
        len(_canonical_json_unchecked(document).encode("utf-8"))
        > MAX_DOCUMENT_BYTES
    ):
        raise _error("document-size", "document exceeds the encoded size bound")
    _exact(
        document,
        required={
            "contract_version",
            "kind",
            "document_id",
            "run_id",
            "objective_id",
            "source_revision",
            "observed_at",
            "producer",
            "payload",
            "authority_invariants",
            "document_digest",
        },
    )
    if document["contract_version"] != CONTRACT_VERSION:
        raise _error("unsupported-contract", "document contract version is unsupported")
    kind = _enum(document["kind"], DOCUMENT_KINDS)
    _identifier(document["document_id"])
    _identifier(document["run_id"])
    _identifier(document["objective_id"])
    _source_revision(document["source_revision"])
    _timestamp(document["observed_at"])
    _producer(document["producer"])
    payload = _object(document["payload"])
    invariants = _object(document["authority_invariants"])
    expected_invariants = authority_invariants()
    if (
        set(invariants) != set(expected_invariants)
        or any(
            type(invariants[key]) is not bool or invariants[key] is not False
            for key in expected_invariants
        )
    ):
        raise _error("invalid-structure", "authority invariants are missing or modified")
    VALIDATORS[kind](payload)
    declared = _digest(document["document_digest"])
    if declared != canonical_digest(document_body(document)):
        raise _error("digest-mismatch", "document digest does not match canonical content")
    return copy.deepcopy(document)


def _resolve_reference(
    reference: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    *,
    kind: str,
) -> dict[str, Any]:
    target = by_id.get(reference["document_id"])
    if (
        target is None
        or target["kind"] != kind
        or target["document_digest"] != reference["document_digest"]
    ):
        raise _error("relationship-mismatch", "document reference does not resolve")
    return target


def validate_set(values: Iterable[Any]) -> dict[str, Any]:
    documents = []
    for value in values:
        if len(documents) >= MAX_SET_DOCUMENTS:
            raise _error(
                "relationship-mismatch",
                "document set exceeds the document count bound",
            )
        documents.append(validate_document(value))
    if not documents:
        raise _error("relationship-mismatch", "document set must not be empty")
    by_id: dict[str, dict[str, Any]] = {}
    for document in documents:
        if document["document_id"] in by_id:
            raise _error("relationship-mismatch", "document ids must be unique")
        by_id[document["document_id"]] = document
    first = documents[0]
    identity = (
        first["run_id"],
        first["objective_id"],
        canonical_json(first["source_revision"]),
    )
    if any(
        (
            item["run_id"],
            item["objective_id"],
            canonical_json(item["source_revision"]),
        )
        != identity
        for item in documents[1:]
    ):
        raise _error("relationship-mismatch", "document set identity is inconsistent")

    by_kind = {
        kind: [item for item in documents if item["kind"] == kind]
        for kind in DOCUMENT_KINDS
    }
    if len(by_kind["run-receipt"]) != 1:
        raise _error("relationship-mismatch", "document set requires one run receipt")
    if len(by_kind["environment-fingerprint"]) != 1:
        raise _error(
            "relationship-mismatch",
            "document set requires one environment fingerprint",
        )
    if len(by_kind["artifact-reference-set"]) != 1:
        raise _error(
            "relationship-mismatch",
            "document set requires one artifact reference set",
        )
    run = by_kind["run-receipt"][0]
    payload = run["payload"]
    environment = _resolve_reference(
        payload["environment_fingerprint"],
        by_id,
        kind="environment-fingerprint",
    )
    artifact_set = _resolve_reference(
        payload["artifact_reference_set"],
        by_id,
        kind="artifact-reference-set",
    )
    iterations = [
        _resolve_reference(reference, by_id, kind="iteration-summary")
        for reference in payload["iteration_summaries"]
    ]
    failures = [
        _resolve_reference(reference, by_id, kind="failure-summary")
        for reference in payload["failure_summaries"]
    ]
    if payload["execution_mode"] != environment["payload"]["execution_mode"]:
        raise _error(
            "relationship-mismatch",
            "run and environment execution modes are inconsistent",
        )
    if {item["document_id"] for item in iterations} != {
        item["document_id"] for item in by_kind["iteration-summary"]
    }:
        raise _error("relationship-mismatch", "iteration inventory is incomplete")
    if {item["document_id"] for item in failures} != {
        item["document_id"] for item in by_kind["failure-summary"]
    }:
        raise _error("relationship-mismatch", "failure inventory is incomplete")
    sequences = [item["payload"]["sequence"] for item in iterations]
    if sequences != list(range(1, len(iterations) + 1)):
        raise _error(
            "relationship-mismatch",
            "iteration sequence must be ordered and contiguous",
        )

    artifact_ids = {
        item["artifact_id"] for item in artifact_set["payload"]["artifacts"]
    }
    failure_by_id = {item["document_id"]: item for item in failures}
    failure_owners: dict[str, list[int]] = {
        item["document_id"]: [] for item in failures
    }
    for iteration in iterations:
        if not set(iteration["payload"]["artifact_ids"]).issubset(artifact_ids):
            raise _error("relationship-mismatch", "iteration artifact does not resolve")
        for reference in iteration["payload"]["failure_summaries"]:
            failure = _resolve_reference(reference, by_id, kind="failure-summary")
            if failure["document_id"] not in failure_by_id:
                raise _error(
                    "relationship-mismatch",
                    "iteration failure does not belong to the run",
                )
            failure_owners[failure["document_id"]].append(
                iteration["payload"]["sequence"]
            )
    for failure in failures:
        if not set(failure["payload"]["artifact_ids"]).issubset(artifact_ids):
            raise _error("relationship-mismatch", "failure artifact does not resolve")
        expected_sequence = failure["payload"]["iteration_sequence"]
        owner_sequences = failure_owners[failure["document_id"]]
        if expected_sequence is None and owner_sequences:
            raise _error(
                "relationship-mismatch",
                "run-level failure must not have an iteration owner",
            )
        if expected_sequence is not None and owner_sequences != [expected_sequence]:
            raise _error(
                "relationship-mismatch",
                "failure must have exactly one matching iteration owner",
            )

    return {
        "status": "valid",
        "contract_version": CONTRACT_VERSION,
        "run_id": run["run_id"],
        "document_count": len(documents),
        "set_digest": canonical_digest(
            {"document_digests": sorted(item["document_digest"] for item in documents)}
        ),
        "authority_invariants": authority_invariants(),
    }
