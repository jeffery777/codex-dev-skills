#!/usr/bin/env python3
"""Strict offline Loop Engineering V3-A evidence-to-proposal contract."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

import improvement_lineage as lineage
import operational_evidence as oe


CONTRACT_VERSION = "loop-improvement-proposal/v0"
KIND = "proposal-set"
SCORE_POLICY_VERSION = "loop-proposal-score/v0"
MAX_PROPOSALS = 128
MAX_DUPLICATE_GROUPS = 128

ELIGIBLE_DISPOSITIONS = frozenset({"proposed", "evaluated", "verified"})
FAILURE_CATEGORY_ORDER = (
    "authority-boundary",
    "privacy-redaction",
    "source-conflict",
    "contract-validation",
    "verification",
    "review",
    "integration",
    "external-action-gate",
    "capability",
    "tooling",
    "resource-bound",
    "unclassified",
)
OUTPUT_INTENT_BY_PHASE = {
    "bootstrap": "patch-suggestion",
    "planning": "patch-suggestion",
    "implementation": "patch-suggestion",
    "verification": "artifact-suggestion",
    "review": "patch-suggestion",
    "integration": "branch-suggestion",
    "release-preparation": "draft-pr-suggestion",
}
DISPOSITION_SCORE = {"proposed": 100, "evaluated": 200, "verified": 300}


class ProposalContractError(ValueError):
    """Stable, non-echoing V3-A contract rejection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> ProposalContractError:
    return ProposalContractError(code, message)


def _translate(error: Exception) -> ProposalContractError:
    return _error(
        getattr(error, "code", "source-invalid"),
        getattr(error, "message", "source evidence is invalid"),
    )


def _bounded_items(
    values: Iterable[Any],
    *,
    limit: int,
    code: str,
    message: str,
) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if len(result) >= limit:
            raise _error(code, message)
        result.append(value)
    if not result:
        raise _error(code, message)
    return result


def proposal_only_invariants() -> dict[str, Any]:
    return {
        "proposal_only": True,
        "runtime_action_performed": False,
        "external_write_performed": False,
        "promotion_decision": "not-authorized",
    }


def proposal_set_body(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key != "proposal_set_digest"
    }


def seal_proposal_set(value: Mapping[str, Any]) -> dict[str, Any]:
    sealed = proposal_set_body(value)
    sealed["proposal_set_digest"] = oe.canonical_digest(sealed)
    return sealed


def _record_ref(record: Mapping[str, Any]) -> dict[str, str]:
    return {
        "record_id": record["record_id"],
        "improvement_id": record["improvement_id"],
        "record_digest": record["record_digest"],
    }


def _validated_documents(values: Iterable[Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    try:
        for value in values:
            document = oe.validate_document(value)
            previous = result.get(document["document_id"])
            if previous is not None:
                if previous["document_digest"] != document["document_digest"]:
                    raise _error(
                        "identity-conflict",
                        "one operational document id has conflicting content",
                    )
                raise _error(
                    "relationship-mismatch",
                    "operational evidence contains a duplicate document",
                )
            result[document["document_id"]] = document
    except (ProposalContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    return result


def _resolve_document(
    reference: Mapping[str, Any],
    documents: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    target = documents.get(reference.get("document_id", ""))
    if (
        target is None
        or target["contract_version"] != reference.get("contract_version")
        or target["kind"] != reference.get("kind")
        or target["document_digest"] != reference.get("document_digest")
    ):
        raise _error(
            "relationship-mismatch",
            "operational document reference does not resolve",
        )
    return target


def _proposal_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(
        {
            "evidence_set_digest": snapshot["evidence_set_digest"],
            "run_receipt": snapshot["run_receipt"],
            "environment_fingerprint": snapshot["environment_fingerprint"],
            "artifact_reference_set": snapshot["artifact_reference_set"],
            "environment_key": snapshot["environment_key"],
            "source_revision": snapshot["source_revision"],
        }
    )


def _source_lineage(
    record: Mapping[str, Any],
    source_record_set_digest: str,
) -> dict[str, Any]:
    payload = record["payload"]
    return {
        "source_record_set_digest": source_record_set_digest,
        "improvement_record": _record_ref(record),
        "repository_id": record["repository"]["repository_id"],
        "objective_id": record["objective_id"],
        "baseline": _proposal_snapshot(payload["baseline"]),
        "candidate": _proposal_snapshot(payload["candidate"]),
        "source_failures": copy.deepcopy(payload["source_failures"]),
        "evaluation_artifacts": copy.deepcopy(payload["evaluation_artifacts"]),
        "candidate_disposition": payload["candidate_disposition"],
    }


def _candidate(
    record: Mapping[str, Any],
    source_record_set_digest: str,
    documents: Mapping[str, dict[str, Any]],
) -> dict[str, Any] | None:
    payload = record["payload"]
    disposition = payload["candidate_disposition"]
    failures = payload["source_failures"]
    if disposition not in ELIGIBLE_DISPOSITIONS or not failures:
        return None

    first_failure = _resolve_document(failures[0], documents)
    failure_payload = first_failure["payload"]
    category = failure_payload["category"]
    phase = failure_payload["phase"]
    hypothesis = {
        "code": f"address-{category}",
        "source_failure_category": category,
        "source_failure_code": failure_payload["code"],
        "source_phase": phase,
    }
    output_intent = OUTPUT_INTENT_BY_PHASE[phase]

    candidate_run = _resolve_document(payload["candidate"]["run_receipt"], documents)
    candidate_artifacts = [
        entry["artifact"]
        for entry in payload["evaluation_artifacts"]
        if entry["snapshot_role"] == "candidate"
        and entry["artifact"]["artifact_kind"] in {"verification", "review"}
    ]
    components = {
        "disposition": DISPOSITION_SCORE[disposition],
        "failure_priority": 21 - (FAILURE_CATEGORY_ORDER.index(category) + 1),
        "candidate_observation": (
            (20 if candidate_run["payload"]["verification_observation"] == "passed" else 0)
            + (10 if candidate_run["payload"]["review_observation"] == "passed" else 0)
        ),
        "typed_evaluation_artifacts": min(40, 5 * len(candidate_artifacts)),
        "recovery_signal": (
            20
            if payload["baseline"]["evidence_set_digest"]
            != payload["candidate"]["evidence_set_digest"]
            and candidate_run["payload"]["outcome"] == "work-recorded"
            and candidate_run["payload"]["verification_observation"] == "passed"
            else 0
        ),
    }
    score = {
        "policy_version": SCORE_POLICY_VERSION,
        "components": components,
        "total": sum(components.values()),
    }
    signature_body = {
        "repository_id": record["repository"]["repository_id"],
        "objective_id": record["objective_id"],
        "baseline_evidence_set_digest": payload["baseline"]["evidence_set_digest"],
        "source_failures": copy.deepcopy(failures),
        "hypothesis_code": hypothesis["code"],
        "output_intent": output_intent,
    }
    duplicate_signature = oe.canonical_digest(signature_body)
    return {
        "source_lineage": _source_lineage(record, source_record_set_digest),
        "score": score,
        "duplicate_signature": duplicate_signature,
        "hypothesis": hypothesis,
        "output_intent": output_intent,
        "role_assignments": copy.deepcopy(payload["role_assignments"]),
        "promotion_gate": {
            "gate_kind": "independent-human-platform",
            "required": True,
            "status": "pending",
            "promoter": copy.deepcopy(payload["role_assignments"]["promoter"]),
        },
        "proposal_only_invariants": proposal_only_invariants(),
        "authority_invariants": oe.authority_invariants(),
    }


def _candidate_key(value: Mapping[str, Any]) -> tuple[Any, ...]:
    reference = value["source_lineage"]["improvement_record"]
    return (
        -value["score"]["total"],
        reference["record_digest"],
        reference["improvement_id"],
        reference["record_id"],
    )


def _source_ref_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return value["record_digest"], value["improvement_id"], value["record_id"]


def build_proposal_set(
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
) -> dict[str, Any]:
    raw_records = _bounded_items(
        records,
        limit=lineage.MAX_RECORDS,
        code="record-count",
        message="proposal source has an unsupported record count",
    )
    raw_evidence = _bounded_items(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="proposal evidence exceeds the document count bound",
    )
    try:
        validated_lineage = lineage.validate_lineage(raw_records, raw_evidence)
    except (lineage.ImprovementContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    documents = _validated_documents(raw_evidence)
    source_digest = validated_lineage["source_record_set_digest"]

    candidates: list[dict[str, Any]] = []
    ineligible: list[dict[str, str]] = []
    for record in validated_lineage["ordered_records"]:
        candidate = _candidate(record, source_digest, documents)
        if candidate is None:
            ineligible.append(_record_ref(record))
        else:
            candidates.append(candidate)
    if len(candidates) > MAX_PROPOSALS:
        raise _error("proposal-count", "proposal candidate count exceeds the bound")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate["duplicate_signature"], []).append(candidate)
    if len(grouped) > MAX_DUPLICATE_GROUPS:
        raise _error("duplicate-count", "proposal duplicate group count exceeds the bound")

    selected: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for signature in sorted(grouped):
        group = sorted(grouped[signature], key=_candidate_key)
        winner = group[0]
        selected.append(winner)
        if len(group) > 1:
            suppressed.append(
                {
                    "duplicate_signature": signature,
                    "selected_source_record": copy.deepcopy(
                        winner["source_lineage"]["improvement_record"]
                    ),
                    "suppressed_source_records": sorted(
                        (
                            copy.deepcopy(
                                item["source_lineage"]["improvement_record"]
                            )
                            for item in group[1:]
                        ),
                        key=_source_ref_key,
                    ),
                }
            )

    selected.sort(
        key=lambda item: (
            -item["score"]["total"],
            item["duplicate_signature"],
            item["source_lineage"]["improvement_record"]["record_digest"],
            item["source_lineage"]["improvement_record"]["improvement_id"],
            item["source_lineage"]["improvement_record"]["record_id"],
        )
    )
    proposals: list[dict[str, Any]] = []
    for rank, candidate in enumerate(selected, start=1):
        proposal = copy.deepcopy(candidate)
        reference = proposal["source_lineage"]["improvement_record"]
        proposal_identity = {
            "record_digest": reference["record_digest"],
            "duplicate_signature": proposal["duplicate_signature"],
            "score_policy_version": SCORE_POLICY_VERSION,
        }
        proposal = {
            "proposal_id": f"proposal:{oe.canonical_digest(proposal_identity)}",
            "rank": rank,
            **proposal,
        }
        proposals.append(proposal)

    result = seal_proposal_set(
        {
            "contract_version": CONTRACT_VERSION,
            "kind": KIND,
            "proposal_set_id": f"proposal-set:{source_digest}",
            "source_record_set_digest": source_digest,
            "score_policy_version": SCORE_POLICY_VERSION,
            "proposals": proposals,
            "suppressed_duplicates": suppressed,
            "ineligible_source_records": ineligible,
            "authority_invariants": oe.authority_invariants(),
        }
    )
    try:
        if len(oe.canonical_json(result).encode("utf-8")) > oe.MAX_DOCUMENT_BYTES:
            raise _error("document-size", "proposal set exceeds the encoded size bound")
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error
    return result


def _validate_envelope(value: Any) -> dict[str, Any]:
    try:
        manifest = oe._object(value)
        oe._finite(manifest)
        if len(oe.canonical_json(manifest).encode("utf-8")) > oe.MAX_DOCUMENT_BYTES:
            raise _error("document-size", "proposal set exceeds the encoded size bound")
        oe._exact(
            manifest,
            required={
                "contract_version",
                "kind",
                "proposal_set_id",
                "source_record_set_digest",
                "score_policy_version",
                "proposals",
                "suppressed_duplicates",
                "ineligible_source_records",
                "authority_invariants",
                "proposal_set_digest",
            },
        )
        if manifest["contract_version"] != CONTRACT_VERSION:
            raise _error("unsupported-contract", "proposal contract version is unsupported")
        if manifest["kind"] != KIND:
            raise _error("invalid-structure", "proposal document kind is unsupported")
        oe._identifier(manifest["proposal_set_id"])
        oe._digest(manifest["source_record_set_digest"])
        if manifest["score_policy_version"] != SCORE_POLICY_VERSION:
            raise _error("unsupported-contract", "proposal score policy is unsupported")
        oe._array(manifest["proposals"])
        oe._array(manifest["suppressed_duplicates"])
        oe._array(manifest["ineligible_source_records"])
        if manifest["authority_invariants"] != oe.authority_invariants():
            raise _error("authority-violation", "proposal authority invariants changed")
        declared = oe._digest(manifest["proposal_set_digest"])
        if declared != oe.canonical_digest(proposal_set_body(manifest)):
            raise _error("digest-mismatch", "proposal set digest does not match")
    except (ProposalContractError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    return copy.deepcopy(manifest)


def validate_proposal_set(
    value: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
) -> dict[str, Any]:
    manifest = _validate_envelope(value)
    regenerated = build_proposal_set(records, evidence_documents)
    if manifest != regenerated:
        raise _error(
            "proposal-mismatch",
            "proposal set does not match regenerated validated evidence",
        )
    return manifest


def load_json(path: Any) -> dict[str, Any]:
    try:
        return lineage.load_json(path)
    except (OSError, lineage.ImprovementContractError) as error:
        if isinstance(error, OSError):
            raise
        raise _translate(error) from error
