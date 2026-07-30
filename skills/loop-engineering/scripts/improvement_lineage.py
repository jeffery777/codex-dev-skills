#!/usr/bin/env python3
"""Strict offline V2d-B improvement-lineage and projection contracts."""

from __future__ import annotations

import copy
import hashlib
import pathlib
import re
from collections.abc import Iterable, Mapping
from typing import Any

import operational_evidence as oe


LINEAGE_CONTRACT_VERSION = "loop-improvement-lineage/v0"
PROJECTION_CONTRACT_VERSION = "loop-evidence-projection/v0"
RECORD_KIND = "improvement-record"
HUMAN_KIND = "human-readable-projection-manifest"
GRAPH_KIND = "typed-graph-projection-manifest"
MAX_RECORDS = 128
V2DB_PRIVATE_PATTERNS = (
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,255}\b"),
)
DISPOSITIONS = frozenset({"proposed", "evaluated", "verified", "rejected"})
ROLES = (
    "proposer",
    "evaluator",
    "independent_verifier",
    "promoter",
)
NODE_TYPES = frozenset(
    {
        "improvement",
        "evidence-snapshot",
        "operational-document",
        "artifact",
        "role-assignment",
    }
)
EDGE_TYPES = frozenset(
    {
        "predecessor-of",
        "baseline-of",
        "candidate-of",
        "references-document",
        "references-artifact",
        "proposed-by",
        "evaluated-by",
        "verified-by",
        "promotion-owned-by",
    }
)
ROLE_EDGES = {
    "proposer": "proposed-by",
    "evaluator": "evaluated-by",
    "independent_verifier": "verified-by",
    "promoter": "promotion-owned-by",
}


class ImprovementContractError(ValueError):
    """Stable, non-sensitive V2d-B validation error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> ImprovementContractError:
    return ImprovementContractError(code, message)


def _translate(error: Exception) -> ImprovementContractError:
    if isinstance(error, ImprovementContractError):
        return error
    if isinstance(error, oe.OperationalEvidenceError):
        return _error(error.code, error.message)
    return _error("invalid-structure", "contract input is invalid")


def _bounded_items(
    values: Iterable[Any],
    *,
    limit: int,
    code: str,
    message: str,
) -> list[Any]:
    items = []
    for value in values:
        if len(items) >= limit:
            raise _error(code, message)
        items.append(value)
    return items


def _v2db_privacy_check(value: Any) -> None:
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in V2DB_PRIVATE_PATTERNS):
            raise _error(
                "privacy-violation",
                "document contains prohibited sensitive data",
            )
        return
    if isinstance(value, dict):
        for child in value.values():
            _v2db_privacy_check(child)
        return
    if isinstance(value, list):
        for child in value:
            _v2db_privacy_check(child)


def _strict_document(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._finite(document)
        _v2db_privacy_check(document)
        if (
            len(oe._canonical_json_unchecked(document).encode("utf-8"))
            > oe.MAX_DOCUMENT_BYTES
        ):
            raise _error("document-size", "document exceeds the encoded size bound")
        return document
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error


def _authority(value: Any) -> None:
    try:
        invariants = oe._object(value)
        expected = oe.authority_invariants()
        if (
            set(invariants) != set(expected)
            or any(
                type(invariants[key]) is not bool or invariants[key] is not False
                for key in expected
            )
        ):
            raise _error(
                "authority-violation",
                "authority invariants are missing or modified",
            )
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error


def _producer(value: Any) -> dict[str, str]:
    try:
        producer = oe._object(value)
        oe._exact(producer, required={"kind", "id"})
        oe._enum(producer["kind"], set(oe.PRODUCER_KINDS))
        oe._identifier(producer["id"])
        return producer
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error


def _repository(value: Any) -> dict[str, str]:
    try:
        repository = oe._object(value)
        oe._exact(repository, required={"repository_id"})
        oe._identifier(repository["repository_id"])
        return repository
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error


def _source_revision(value: Any) -> dict[str, str]:
    try:
        return oe._source_revision(value)
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error


def _record_ref(value: Any) -> dict[str, str]:
    try:
        reference = oe._object(value)
        oe._exact(
            reference,
            required={"record_id", "improvement_id", "record_digest"},
        )
        oe._identifier(reference["record_id"])
        oe._identifier(reference["improvement_id"])
        oe._digest(reference["record_digest"])
        return reference
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error


def _document_ref(value: Any, *, kind: str | None = None) -> dict[str, str]:
    try:
        reference = oe._object(value)
        oe._exact(
            reference,
            required={
                "contract_version",
                "kind",
                "document_id",
                "document_digest",
            },
        )
        if reference["contract_version"] != oe.CONTRACT_VERSION:
            raise _error(
                "unsupported-contract",
                "operational document reference uses an unsupported contract",
            )
        oe._enum(reference["kind"], set(oe.DOCUMENT_KINDS))
        if kind is not None and reference["kind"] != kind:
            raise _error(
                "relationship-mismatch",
                "operational document reference kind does not match",
            )
        oe._identifier(reference["document_id"])
        oe._digest(reference["document_digest"])
        return reference
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error


def _artifact(value: Any) -> dict[str, Any]:
    try:
        artifact = oe._object(value)
        oe._exact(
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
        oe._identifier(artifact["artifact_id"])
        kind = oe._enum(artifact["artifact_kind"], set(oe.ARTIFACT_LOCATORS))
        locator_kind = oe._enum(
            artifact["locator_kind"],
            {"repository-relative-path", "git-commit", "opaque-id"},
        )
        if locator_kind not in oe.ARTIFACT_LOCATORS[kind]:
            raise _error(
                "invalid-structure",
                "artifact kind and locator kind conflict",
            )
        if locator_kind == "repository-relative-path":
            oe._relative_path(artifact["locator"])
        elif locator_kind == "git-commit":
            if (
                not isinstance(artifact["locator"], str)
                or not oe.GIT_COMMIT.fullmatch(artifact["locator"])
            ):
                raise _error(
                    "invalid-structure",
                    "artifact locator must be an exact Git commit",
                )
        else:
            oe._identifier(artifact["locator"])
        oe._digest(artifact["content_sha256"])
        oe._enum(artifact["media_type"], set(oe.MEDIA_TYPES))
        return artifact
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error


def record_body(record: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in record.items() if key != "record_digest"}


def projection_body(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in manifest.items()
        if key != "projection_digest"
    }


def seal_record(record: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(record)
    sealed.pop("record_digest", None)
    sealed["record_digest"] = oe.canonical_digest(sealed)
    return sealed


def seal_projection(manifest: dict[str, Any]) -> dict[str, Any]:
    sealed = copy.deepcopy(manifest)
    sealed.pop("projection_digest", None)
    sealed["projection_digest"] = oe.canonical_digest(sealed)
    return sealed


def _evidence_groups(
    values: Iterable[Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, dict[str, Any]]],
]:
    documents: list[dict[str, Any]] = []
    seen_ids: dict[str, str] = {}
    try:
        for value in values:
            if len(documents) >= oe.MAX_SET_DOCUMENTS:
                raise _error(
                    "relationship-mismatch",
                    "evidence input exceeds the document count bound",
                )
            document = oe.validate_document(value)
            previous = seen_ids.get(document["document_id"])
            if previous is not None:
                if previous != document["document_digest"]:
                    raise _error(
                        "identity-conflict",
                        "one operational document id has conflicting content",
                    )
                raise _error(
                    "relationship-mismatch",
                    "operational evidence input contains a duplicate document",
                )
            seen_ids[document["document_id"]] = document["document_digest"]
            documents.append(document)
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    if not documents:
        raise _error(
            "relationship-mismatch",
            "at least one operational evidence set is required",
        )
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for document in documents:
        key = (
            document["run_id"],
            document["objective_id"],
            oe.canonical_json(document["source_revision"]),
        )
        grouped.setdefault(key, []).append(document)
    set_results: dict[str, dict[str, Any]] = {}
    set_documents: dict[str, dict[str, dict[str, Any]]] = {}
    try:
        for group in grouped.values():
            result = oe.validate_set(group)
            digest = result["set_digest"]
            if digest in set_results:
                raise _error(
                    "identity-conflict",
                    "evidence set digest is not unique",
                )
            set_results[digest] = result
            set_documents[digest] = {item["document_id"]: item for item in group}
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    return set_results, set_documents


def _resolve_document(
    reference: dict[str, str],
    documents: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    target = documents.get(reference["document_id"])
    if (
        target is None
        or target["contract_version"] != reference["contract_version"]
        or target["kind"] != reference["kind"]
        or target["document_digest"] != reference["document_digest"]
    ):
        raise _error(
            "relationship-mismatch",
            "operational document reference does not resolve",
        )
    return target


def _snapshot(
    value: Any,
    *,
    expected_objective: str,
    expected_repository: str,
    set_results: Mapping[str, dict[str, Any]],
    set_documents: Mapping[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    try:
        snapshot = oe._object(value)
        oe._exact(
            snapshot,
            required={
                "snapshot_id",
                "run_receipt",
                "environment_fingerprint",
                "artifact_reference_set",
                "evidence_set_digest",
                "environment_key",
                "source_revision",
            },
        )
        oe._identifier(snapshot["snapshot_id"])
        run_ref = _document_ref(snapshot["run_receipt"], kind="run-receipt")
        environment_ref = _document_ref(
            snapshot["environment_fingerprint"],
            kind="environment-fingerprint",
        )
        artifact_ref = _document_ref(
            snapshot["artifact_reference_set"],
            kind="artifact-reference-set",
        )
        digest = oe._digest(snapshot["evidence_set_digest"])
        environment_key = oe._digest(snapshot["environment_key"])
        source_revision = _source_revision(snapshot["source_revision"])
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    if digest not in set_results:
        raise _error("relationship-mismatch", "evidence set digest does not resolve")
    documents = set_documents[digest]
    run = _resolve_document(run_ref, documents)
    environment = _resolve_document(environment_ref, documents)
    artifact_set = _resolve_document(artifact_ref, documents)
    result = set_results[digest]
    if result["run_id"] != run["run_id"]:
        raise _error("relationship-mismatch", "run receipt does not own evidence set")
    if run["objective_id"] != expected_objective:
        raise _error("relationship-mismatch", "snapshot objective does not match")
    if run["source_revision"] != source_revision:
        raise _error("relationship-mismatch", "snapshot source revision does not match")
    if source_revision["repository_id"] != expected_repository:
        raise _error("relationship-mismatch", "snapshot repository does not match")
    if oe.canonical_digest(environment["payload"]) != environment_key:
        raise _error("digest-mismatch", "environment key does not match")
    return {
        "value": snapshot,
        "run": run,
        "environment": environment,
        "artifact_set": artifact_set,
        "documents": documents,
    }


def _role_assignments(value: Any) -> dict[str, dict[str, str]]:
    try:
        assignments = oe._object(value)
        oe._exact(assignments, required=set(ROLES))
        actor_ids: list[str] = []
        for role in ROLES:
            assignment = oe._object(assignments[role])
            oe._exact(assignment, required={"actor_kind", "actor_id"})
            oe._enum(assignment["actor_kind"], set(oe.PRODUCER_KINDS))
            actor_ids.append(oe._identifier(assignment["actor_id"]))
        if len(actor_ids) != len(set(actor_ids)):
            raise _error(
                "role-conflict",
                "role assignments require distinct actor ids",
            )
        return assignments
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error


def _producer_identity(producer: Mapping[str, str]) -> tuple[str, str]:
    return producer["kind"], producer["id"]


def _assignment_identity(assignment: Mapping[str, str]) -> tuple[str, str]:
    return assignment["actor_kind"], assignment["actor_id"]


def validate_record(
    value: Any,
    evidence_documents: Iterable[Any],
    *,
    _prepared_evidence: tuple[
        dict[str, dict[str, Any]],
        dict[str, dict[str, dict[str, Any]]],
    ]
    | None = None,
) -> dict[str, Any]:
    record = _strict_document(value)
    try:
        oe._exact(
            record,
            required={
                "contract_version",
                "kind",
                "record_id",
                "improvement_id",
                "objective_id",
                "repository",
                "recorded_at",
                "producer",
                "payload",
                "authority_invariants",
                "record_digest",
            },
        )
        if record["contract_version"] != LINEAGE_CONTRACT_VERSION:
            raise _error("unsupported-contract", "lineage contract version is unsupported")
        if record["kind"] != RECORD_KIND:
            raise _error("invalid-structure", "lineage document kind is unsupported")
        oe._identifier(record["record_id"])
        oe._identifier(record["improvement_id"])
        objective_id = oe._identifier(record["objective_id"])
        repository = _repository(record["repository"])
        oe._timestamp(record["recorded_at"])
        producer = _producer(record["producer"])
        payload = oe._object(record["payload"])
        _authority(record["authority_invariants"])
        declared_digest = oe._digest(record["record_digest"])
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    if declared_digest != oe.canonical_digest(record_body(record)):
        raise _error("digest-mismatch", "record digest does not match canonical content")
    try:
        oe._exact(
            payload,
            required={
                "predecessor",
                "baseline",
                "candidate",
                "source_failures",
                "evaluation_artifacts",
                "role_assignments",
                "candidate_disposition",
            },
        )
        predecessor = (
            None if payload["predecessor"] is None else _record_ref(payload["predecessor"])
        )
        disposition = oe._enum(payload["candidate_disposition"], set(DISPOSITIONS))
        failures = oe._array(payload["source_failures"])
        artifacts = oe._array(payload["evaluation_artifacts"])
        if not artifacts:
            raise _error(
                "invalid-structure",
                "improvement record requires an evaluation artifact",
            )
        roles = _role_assignments(payload["role_assignments"])
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    set_results, set_documents = (
        _evidence_groups(evidence_documents)
        if _prepared_evidence is None
        else _prepared_evidence
    )
    baseline = _snapshot(
        payload["baseline"],
        expected_objective=objective_id,
        expected_repository=repository["repository_id"],
        set_results=set_results,
        set_documents=set_documents,
    )
    candidate = _snapshot(
        payload["candidate"],
        expected_objective=objective_id,
        expected_repository=repository["repository_id"],
        set_results=set_results,
        set_documents=set_documents,
    )
    if (
        baseline["value"]["evidence_set_digest"]
        == candidate["value"]["evidence_set_digest"]
    ):
        raise _error(
            "relationship-mismatch",
            "baseline and candidate evidence sets must differ",
        )
    if baseline["value"]["environment_key"] != candidate["value"]["environment_key"]:
        raise _error(
            "environment-mismatch",
            "baseline and candidate environments do not match",
        )
    if _producer_identity(producer) != _assignment_identity(roles["proposer"]):
        raise _error("role-conflict", "record producer must be the assigned proposer")
    candidate_producer_id = candidate["run"]["producer"]["id"]
    if candidate_producer_id in {
        roles["independent_verifier"]["actor_id"],
        roles["promoter"]["actor_id"],
    }:
        raise _error(
            "role-conflict",
            "candidate producer cannot verify or promote the candidate",
        )
    failure_refs = [_document_ref(item, kind="failure-summary") for item in failures]
    failure_keys = [
        (item["document_id"], item["document_digest"]) for item in failure_refs
    ]
    if failure_keys != sorted(failure_keys) or len(failure_keys) != len(set(failure_keys)):
        raise _error(
            "relationship-mismatch",
            "source failure references must be sorted and unique",
        )
    combined_documents = {
        **baseline["documents"],
        **candidate["documents"],
    }
    for reference in failure_refs:
        _resolve_document(reference, combined_documents)
    artifact_entries: list[tuple[str, dict[str, Any]]] = []
    artifact_keys: list[tuple[str, str, str]] = []
    for item in artifacts:
        try:
            entry = oe._object(item)
            oe._exact(entry, required={"snapshot_role", "artifact"})
            role = oe._enum(entry["snapshot_role"], {"baseline", "candidate"})
            artifact = _artifact(entry["artifact"])
        except oe.OperationalEvidenceError as error:
            raise _translate(error) from error
        selected = baseline if role == "baseline" else candidate
        inventory = {
            candidate_item["artifact_id"]: candidate_item
            for candidate_item in selected["artifact_set"]["payload"]["artifacts"]
        }
        if inventory.get(artifact["artifact_id"]) != artifact:
            raise _error(
                "relationship-mismatch",
                "evaluation artifact does not resolve in selected snapshot",
            )
        artifact_entries.append((role, artifact))
        artifact_keys.append(
            (role, artifact["artifact_id"], artifact["content_sha256"])
        )
    if artifact_keys != sorted(artifact_keys) or len(artifact_keys) != len(
        set(artifact_keys)
    ):
        raise _error(
            "relationship-mismatch",
            "evaluation artifacts must be sorted and unique",
        )
    if disposition == "verified":
        candidate_kinds = {
            artifact["artifact_kind"]
            for role, artifact in artifact_entries
            if role == "candidate"
        }
        if not {"verification", "review"}.issubset(candidate_kinds):
            raise _error(
                "role-conflict",
                "verified disposition requires candidate verification and review artifacts",
            )
    if predecessor is not None and predecessor["improvement_id"] == record["improvement_id"]:
        raise _error("lineage-cycle", "improvement cannot precede itself")
    return copy.deepcopy(record)


def validate_lineage(
    values: Iterable[Any],
    evidence_documents: Iterable[Any],
) -> dict[str, Any]:
    raw_records = _bounded_items(
        values,
        limit=MAX_RECORDS,
        code="record-count",
        message="lineage set has an unsupported record count",
    )
    if not raw_records:
        raise _error("record-count", "lineage set has an unsupported record count")
    evidence = _bounded_items(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="evidence input exceeds the document count bound",
    )
    prepared_evidence = _evidence_groups(evidence)
    records = [
        validate_record(
            value,
            evidence,
            _prepared_evidence=prepared_evidence,
        )
        for value in raw_records
    ]
    by_record: dict[str, dict[str, Any]] = {}
    by_improvement: dict[str, dict[str, Any]] = {}
    for record in records:
        if record["record_id"] in by_record:
            raise _error("identity-conflict", "record ids must be unique")
        if record["improvement_id"] in by_improvement:
            raise _error("identity-conflict", "improvement ids must be unique")
        by_record[record["record_id"]] = record
        by_improvement[record["improvement_id"]] = record
    identity = (
        records[0]["objective_id"],
        oe.canonical_json(records[0]["repository"]),
    )
    if any(
        (record["objective_id"], oe.canonical_json(record["repository"])) != identity
        for record in records[1:]
    ):
        raise _error("relationship-mismatch", "lineage repository or objective differs")
    parent_by_id: dict[str, str | None] = {}
    for record in records:
        reference = record["payload"]["predecessor"]
        if reference is None:
            parent_by_id[record["record_id"]] = None
            continue
        parent = by_record.get(reference["record_id"])
        if (
            parent is None
            or parent["improvement_id"] != reference["improvement_id"]
            or parent["record_digest"] != reference["record_digest"]
        ):
            raise _error("missing-predecessor", "predecessor reference does not resolve")
        if (
            record["payload"]["baseline"]["evidence_set_digest"]
            != parent["payload"]["candidate"]["evidence_set_digest"]
        ):
            raise _error("stale-baseline", "baseline does not match predecessor candidate")
        if oe._timestamp(parent["recorded_at"]) > oe._timestamp(record["recorded_at"]):
            raise _error("lineage-order", "predecessor timestamp follows child")
        parent_by_id[record["record_id"]] = parent["record_id"]
    depth_cache: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(record_id: str) -> int:
        if record_id in depth_cache:
            return depth_cache[record_id]
        if record_id in visiting:
            raise _error("lineage-cycle", "lineage contains a predecessor cycle")
        visiting.add(record_id)
        parent = parent_by_id[record_id]
        value = 0 if parent is None else depth(parent) + 1
        visiting.remove(record_id)
        depth_cache[record_id] = value
        return value

    ordered = sorted(
        records,
        key=lambda item: (
            depth(item["record_id"]),
            item["improvement_id"],
            item["record_digest"],
        ),
    )
    digests = [item["record_digest"] for item in ordered]
    set_digest = oe.canonical_digest({"record_digests": digests})
    return {
        "status": "valid",
        "contract_version": LINEAGE_CONTRACT_VERSION,
        "record_count": len(ordered),
        "source_record_set_digest": set_digest,
        "ordered_record_ids": [item["record_id"] for item in ordered],
        "ordered_records": copy.deepcopy(ordered),
        "lineage_depths": {
            item["record_id"]: depth(item["record_id"]) for item in ordered
        },
        "authority_invariants": oe.authority_invariants(),
    }


def _projection_id(kind: str, source_digest: str) -> str:
    return f"{kind}:{source_digest}"


def _source_records(lineage: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "record_id": record["record_id"],
            "improvement_id": record["improvement_id"],
            "record_digest": record["record_digest"],
        }
        for record in lineage["ordered_records"]
    ]


def _render_human(
    source_digest: str,
    sections: Iterable[Mapping[str, Any]],
) -> str:
    lines = [f"# Improvement lineage {source_digest}", ""]
    for index, section in enumerate(sections):
        if index:
            lines.append("")
        predecessor = section["predecessor_improvement_id"] or "none"
        lines.extend(
            [
                f"## {section['improvement_id']}",
                f"- depth: {section['lineage_depth']}",
                f"- record: {section['record_digest']}",
                f"- predecessor: {predecessor}",
                f"- baseline: {section['baseline_evidence_set_digest']}",
                f"- candidate: {section['candidate_evidence_set_digest']}",
                f"- disposition: {section['candidate_disposition']}",
                (
                    "- proposer: "
                    f"{section['proposer']['actor_kind']}:{section['proposer']['actor_id']}"
                ),
                (
                    "- evaluator: "
                    f"{section['evaluator']['actor_kind']}:{section['evaluator']['actor_id']}"
                ),
                (
                    "- independent-verifier: "
                    f"{section['independent_verifier']['actor_kind']}:"
                    f"{section['independent_verifier']['actor_id']}"
                ),
                (
                    "- promoter: "
                    f"{section['promoter']['actor_kind']}:{section['promoter']['actor_id']}"
                ),
            ]
        )
    return "\n".join(lines) + "\n"


def build_human_projection(
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
) -> dict[str, Any]:
    lineage = validate_lineage(records, evidence_documents)
    source_digest = lineage["source_record_set_digest"]
    projection_id = _projection_id(HUMAN_KIND, source_digest)
    sections = []
    for record in lineage["ordered_records"]:
        predecessor = record["payload"]["predecessor"]
        roles = record["payload"]["role_assignments"]
        sections.append(
            {
                "section_id": f"section:improvement:{record['record_digest']}",
                "lineage_depth": lineage["lineage_depths"][record["record_id"]],
                "improvement_id": record["improvement_id"],
                "record_digest": record["record_digest"],
                "predecessor_improvement_id": (
                    None if predecessor is None else predecessor["improvement_id"]
                ),
                "baseline_evidence_set_digest": record["payload"]["baseline"][
                    "evidence_set_digest"
                ],
                "candidate_evidence_set_digest": record["payload"]["candidate"][
                    "evidence_set_digest"
                ],
                "candidate_disposition": record["payload"]["candidate_disposition"],
                **{role: copy.deepcopy(roles[role]) for role in ROLES},
            }
        )
    rendered = _render_human(source_digest, sections)
    manifest = {
        "contract_version": PROJECTION_CONTRACT_VERSION,
        "kind": HUMAN_KIND,
        "projection_id": projection_id,
        "source_record_set_digest": source_digest,
        "source_records": _source_records(lineage),
        "payload": {
            "format": "markdown",
            "ordering": "lineage-depth-improvement-id-record-digest",
            "renderer_version": "loop-human-projection/v0",
            "output_locator": {
                "locator_kind": "opaque-id",
                "locator": projection_id,
            },
            "sections": sections,
            "rendered_content_sha256": hashlib.sha256(
                rendered.encode("utf-8")
            ).hexdigest(),
        },
        "authority_invariants": oe.authority_invariants(),
    }
    sealed = seal_projection(manifest)
    _strict_document(sealed)
    if len(rendered.encode("utf-8")) > oe.MAX_DOCUMENT_BYTES:
        raise _error("document-size", "rendered projection exceeds the size bound")
    return {"manifest": sealed, "rendered_markdown": rendered}


def _record_ref_from_record(record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "record_id": record["record_id"],
        "improvement_id": record["improvement_id"],
        "record_digest": record["record_digest"],
    }


def _node(node_type: str, source_ref: dict[str, Any]) -> dict[str, Any]:
    if node_type not in NODE_TYPES:
        raise _error("invalid-structure", "graph node type is unsupported")
    digest = oe.canonical_digest(source_ref)
    return {
        "node_id": f"node:{node_type}:{digest}",
        "node_type": node_type,
        "source_ref": copy.deepcopy(source_ref),
        "content_sha256": digest,
    }


def _edge(
    edge_type: str,
    from_node_id: str,
    to_node_id: str,
    source_record_digest: str,
) -> dict[str, str]:
    if edge_type not in EDGE_TYPES:
        raise _error("invalid-structure", "graph edge type is unsupported")
    body = {
        "edge_type": edge_type,
        "from_node_id": from_node_id,
        "to_node_id": to_node_id,
        "source_record_digest": source_record_digest,
    }
    return {
        "edge_id": f"edge:{edge_type}:{oe.canonical_digest(body)}",
        **body,
    }


def build_graph_projection(
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
) -> dict[str, Any]:
    evidence = _bounded_items(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="evidence input exceeds the document count bound",
    )
    lineage = validate_lineage(records, evidence)
    _, evidence_sets = _evidence_groups(evidence)
    source_digest = lineage["source_record_set_digest"]
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, str]] = {}

    def add_node(node: dict[str, Any]) -> str:
        existing = nodes.get(node["node_id"])
        if existing is not None and existing != node:
            raise _error("identity-conflict", "graph node id has conflicting content")
        nodes[node["node_id"]] = node
        return node["node_id"]

    def add_edge(edge: dict[str, str]) -> None:
        existing = edges.get(edge["edge_id"])
        if existing is not None and existing != edge:
            raise _error("identity-conflict", "graph edge id has conflicting content")
        edges[edge["edge_id"]] = edge

    improvement_nodes: dict[str, str] = {}
    for record in lineage["ordered_records"]:
        record_ref = _record_ref_from_record(record)
        improvement_id = add_node(
            _node("improvement", {"record_ref": record_ref})
        )
        improvement_nodes[record["record_id"]] = improvement_id
        for snapshot_role in ("baseline", "candidate"):
            snapshot = record["payload"][snapshot_role]
            snapshot_ref = {
                "record_ref": record_ref,
                "snapshot_role": snapshot_role,
                "snapshot_id": snapshot["snapshot_id"],
                "evidence_set_digest": snapshot["evidence_set_digest"],
            }
            snapshot_node = add_node(_node("evidence-snapshot", snapshot_ref))
            add_edge(
                _edge(
                    f"{snapshot_role}-of",
                    snapshot_node,
                    improvement_id,
                    record["record_digest"],
                )
            )
            snapshot_documents = sorted(
                evidence_sets[snapshot["evidence_set_digest"]].values(),
                key=lambda item: (
                    item["kind"],
                    item["document_id"],
                    item["document_digest"],
                ),
            )
            for document in snapshot_documents:
                document_ref = {
                    "contract_version": document["contract_version"],
                    "kind": document["kind"],
                    "document_id": document["document_id"],
                    "document_digest": document["document_digest"],
                }
                document_node = add_node(
                    _node("operational-document", document_ref)
                )
                add_edge(
                    _edge(
                        "references-document",
                        snapshot_node,
                        document_node,
                        record["record_digest"],
                    )
                )
        for failure_ref in record["payload"]["source_failures"]:
            failure_node = add_node(
                _node("operational-document", copy.deepcopy(failure_ref))
            )
            add_edge(
                _edge(
                    "references-document",
                    improvement_id,
                    failure_node,
                    record["record_digest"],
                )
            )
        for entry in record["payload"]["evaluation_artifacts"]:
            artifact_ref = {
                "record_ref": record_ref,
                "snapshot_role": entry["snapshot_role"],
                "artifact": copy.deepcopy(entry["artifact"]),
            }
            artifact_node = add_node(_node("artifact", artifact_ref))
            add_edge(
                _edge(
                    "references-artifact",
                    improvement_id,
                    artifact_node,
                    record["record_digest"],
                )
            )
        for role in ROLES:
            assignment = record["payload"]["role_assignments"][role]
            role_ref = {
                "record_ref": record_ref,
                "role": role,
                "actor_kind": assignment["actor_kind"],
                "actor_id": assignment["actor_id"],
            }
            role_node = add_node(_node("role-assignment", role_ref))
            add_edge(
                _edge(
                    ROLE_EDGES[role],
                    improvement_id,
                    role_node,
                    record["record_digest"],
                )
            )
    for record in lineage["ordered_records"]:
        predecessor = record["payload"]["predecessor"]
        if predecessor is not None:
            add_edge(
                _edge(
                    "predecessor-of",
                    improvement_nodes[predecessor["record_id"]],
                    improvement_nodes[record["record_id"]],
                    record["record_digest"],
                )
            )
    ordered_nodes = sorted(
        nodes.values(), key=lambda item: (item["node_type"], item["node_id"])
    )
    ordered_edges = sorted(
        edges.values(),
        key=lambda item: (
            item["edge_type"],
            item["from_node_id"],
            item["to_node_id"],
            item["edge_id"],
        ),
    )
    manifest = {
        "contract_version": PROJECTION_CONTRACT_VERSION,
        "kind": GRAPH_KIND,
        "projection_id": _projection_id(GRAPH_KIND, source_digest),
        "source_record_set_digest": source_digest,
        "source_records": _source_records(lineage),
        "payload": {
            "schema_version": "loop-typed-graph/v0",
            "ordering": "node-type-node-id-then-edge-type-from-to",
            "nodes": ordered_nodes,
            "edges": ordered_edges,
        },
        "authority_invariants": oe.authority_invariants(),
    }
    sealed = seal_projection(manifest)
    _strict_document(sealed)
    return sealed


def validate_projection(
    value: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
) -> dict[str, Any]:
    manifest = _strict_document(value)
    try:
        oe._exact(
            manifest,
            required={
                "contract_version",
                "kind",
                "projection_id",
                "source_record_set_digest",
                "source_records",
                "payload",
                "authority_invariants",
                "projection_digest",
            },
        )
        if manifest["contract_version"] != PROJECTION_CONTRACT_VERSION:
            raise _error(
                "unsupported-contract",
                "projection contract version is unsupported",
            )
        kind = oe._enum(manifest["kind"], {HUMAN_KIND, GRAPH_KIND})
        oe._identifier(manifest["projection_id"])
        oe._digest(manifest["source_record_set_digest"])
        oe._array(manifest["source_records"])
        oe._object(manifest["payload"])
        _authority(manifest["authority_invariants"])
        declared = oe._digest(manifest["projection_digest"])
    except (ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    if declared != oe.canonical_digest(projection_body(manifest)):
        raise _error(
            "digest-mismatch",
            "projection digest does not match canonical content",
        )
    evidence = _bounded_items(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="evidence input exceeds the document count bound",
    )
    record_values = _bounded_items(
        records,
        limit=MAX_RECORDS,
        code="record-count",
        message="lineage set has an unsupported record count",
    )
    if kind == HUMAN_KIND:
        expected = build_human_projection(record_values, evidence)["manifest"]
    else:
        expected = build_graph_projection(record_values, evidence)
    if oe.canonical_json(manifest) != oe.canonical_json(expected):
        raise _error(
            "projection-mismatch",
            "projection does not match validated source records",
        )
    return copy.deepcopy(manifest)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        return oe.load_json(path)
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error
