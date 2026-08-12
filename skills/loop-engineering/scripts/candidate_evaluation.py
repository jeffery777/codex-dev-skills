#!/usr/bin/env python3
"""Strict offline Loop Engineering V3-B isolated candidate evaluation."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

import improvement_proposal as proposal
import memory_contract as memory
import operational_evidence as oe


CONTRACT_VERSION = "loop-candidate-evaluation/v0"
INPUT_KIND = "evaluation-input"
RESULT_KIND = "evaluation-result"
VERIFICATION_KIND = "independent-verification-result"
PACKET_KIND = "promotion-packet"
POLICY_VERSION = "loop-candidate-acceptance/v0"
MAX_SCENARIOS = 128
MAX_DURATION_MS = 60_000
MAX_RESOURCE_UNITS = 1_000_000
MAX_REGRESSION_BPS = 2_000

OUTCOMES = frozenset(
    {"passed", "failed", "timeout", "resource-bound", "interrupted", "uncertain"}
)
UNCERTAIN_OUTCOMES = frozenset(
    {"timeout", "resource-bound", "interrupted", "uncertain"}
)


class CandidateEvaluationError(ValueError):
    """Stable, non-echoing V3-B contract rejection."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> CandidateEvaluationError:
    return CandidateEvaluationError(code, message)


def _translate(error: Exception) -> CandidateEvaluationError:
    return _error(
        getattr(error, "code", "source-invalid"),
        getattr(error, "message", "source input is invalid"),
    )


def authority_invariants() -> dict[str, bool]:
    return oe.authority_invariants()


def packet_only_invariants() -> dict[str, bool]:
    return {
        "packet_only": True,
        "runtime_action_performed": False,
        "external_write_performed": False,
        "approval_performed": False,
        "promotion_performed": False,
        "merge_performed": False,
        "release_performed": False,
        "deploy_performed": False,
        "activation_performed": False,
    }


def fixed_policy() -> dict[str, Any]:
    return {
        "policy_version": POLICY_VERSION,
        "scenario_pass_basis_points": 10_000,
        "maximum_failure_count": 0,
        "maximum_duration_regression_basis_points": MAX_REGRESSION_BPS,
        "maximum_resource_regression_basis_points": MAX_REGRESSION_BPS,
        "environment_equivalence": "exact-public-fingerprint",
        "independent_verification_required": True,
        "authority_invariants": authority_invariants(),
    }


def _body(value: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    return {
        key: copy.deepcopy(item)
        for key, item in value.items()
        if key != digest_field
    }


def _seal(value: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    result = _body(value, digest_field)
    result[digest_field] = oe.canonical_digest(result)
    return result


def seal_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    return _seal(value, "observation_digest")


def seal_evaluation_input(value: Mapping[str, Any]) -> dict[str, Any]:
    return _seal(value, "evaluation_input_digest")


def seal_evaluation_result(value: Mapping[str, Any]) -> dict[str, Any]:
    return _seal(value, "evaluation_result_digest")


def seal_verification_result(value: Mapping[str, Any]) -> dict[str, Any]:
    return _seal(value, "verification_result_digest")


def seal_promotion_packet(value: Mapping[str, Any]) -> dict[str, Any]:
    return _seal(value, "promotion_packet_digest")


def _bounded_sources(
    values: Iterable[Any], *, limit: int, code: str, message: str
) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if len(result) >= limit:
            raise _error(code, message)
        result.append(value)
    if not result:
        raise _error(code, message)
    return result


def _document_size(value: Any) -> None:
    if len(oe.canonical_json(value).encode("utf-8")) > oe.MAX_DOCUMENT_BYTES:
        raise _error("document-size", "candidate evaluation document exceeds the size bound")


def _source_revision(value: Any) -> dict[str, Any]:
    source = oe._object(value)
    oe._exact(source, required={"repository_id", "commit_sha"})
    oe._identifier(source["repository_id"])
    commit = source["commit_sha"]
    if not isinstance(commit, str) or not oe.GIT_COMMIT.fullmatch(commit):
        raise _error("invalid-structure", "source revision must be an exact Git commit")
    return source


def _validate_observation(value: Any, role: str) -> dict[str, Any]:
    observation = oe._object(value)
    oe._exact(
        observation,
        required={
            "snapshot_role",
            "evidence_set_digest",
            "source_revision",
            "environment_fingerprint",
            "scenario_set_digest",
            "scenario_count",
            "outcome",
            "passed_scenarios",
            "decision_failures",
            "recovery_failures",
            "determinism_failures",
            "authority_failures",
            "privacy_failures",
            "duration_ms",
            "resource_units",
            "authority_invariants",
            "observation_digest",
        },
    )
    if observation["snapshot_role"] != role:
        raise _error("input-mismatch", "observation snapshot role does not match")
    oe._digest(observation["evidence_set_digest"])
    _source_revision(observation["source_revision"])
    environment = oe._object(observation["environment_fingerprint"])
    oe._validate_environment(environment)
    oe._digest(observation["scenario_set_digest"])
    count = oe._integer(observation["scenario_count"], minimum=1, maximum=MAX_SCENARIOS)
    outcome = oe._enum(observation["outcome"], set(OUTCOMES))
    passed = oe._integer(observation["passed_scenarios"], maximum=count)
    failures = []
    for field in (
        "decision_failures",
        "recovery_failures",
        "determinism_failures",
        "authority_failures",
        "privacy_failures",
    ):
        failures.append(oe._integer(observation[field], maximum=count))
    oe._integer(observation["duration_ms"], maximum=MAX_DURATION_MS)
    oe._integer(observation["resource_units"], maximum=MAX_RESOURCE_UNITS)
    if outcome == "passed" and (passed != count or any(failures)):
        raise _error("invalid-structure", "passed observation contradicts scenario outcomes")
    if outcome != "passed" and passed == count and not any(failures):
        raise _error("invalid-structure", "non-passing observation lacks a bounded failure signal")
    if observation["authority_invariants"] != authority_invariants():
        raise _error("authority-violation", "observation authority invariants changed")
    declared = oe._digest(observation["observation_digest"])
    if declared != oe.canonical_digest(_body(observation, "observation_digest")):
        raise _error("digest-mismatch", "observation digest does not match")
    return copy.deepcopy(observation)


def validate_evaluation_input(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._finite(document)
        _document_size(document)
        oe._exact(
            document,
            required={
                "contract_version",
                "kind",
                "proposal_id",
                "scenario_set_digest",
                "baseline",
                "candidate",
                "authority_invariants",
                "evaluation_input_digest",
            },
        )
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != INPUT_KIND:
            raise _error("unsupported-contract", "evaluation input contract is unsupported")
        oe._identifier(document["proposal_id"])
        scenario_digest = oe._digest(document["scenario_set_digest"])
        baseline = _validate_observation(document["baseline"], "baseline")
        candidate = _validate_observation(document["candidate"], "candidate")
        if baseline["scenario_set_digest"] != scenario_digest or candidate["scenario_set_digest"] != scenario_digest:
            raise _error("input-mismatch", "observation scenario set does not match input")
        if document["authority_invariants"] != authority_invariants():
            raise _error("authority-violation", "evaluation input authority invariants changed")
        declared = oe._digest(document["evaluation_input_digest"])
        if declared != oe.canonical_digest(_body(document, "evaluation_input_digest")):
            raise _error("digest-mismatch", "evaluation input digest does not match")
    except (CandidateEvaluationError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    return copy.deepcopy(document)


def _validated_source(
    proposal_set: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
    evaluation_input: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw_records = _bounded_sources(
        records,
        limit=proposal.lineage.MAX_RECORDS,
        code="record-count",
        message="candidate evaluation source has an unsupported record count",
    )
    raw_evidence = _bounded_sources(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="candidate evaluation evidence exceeds the document count bound",
    )
    try:
        validated_set = proposal.validate_proposal_set(
            proposal_set, raw_records, raw_evidence
        )
    except proposal.ProposalContractError as error:
        raise _translate(error) from error
    matches = [
        item
        for item in validated_set["proposals"]
        if item["proposal_id"] == evaluation_input["proposal_id"]
    ]
    if len(matches) != 1:
        raise _error("source-mismatch", "evaluation proposal does not resolve exactly once")
    selected = matches[0]
    for role in ("baseline", "candidate"):
        observed = evaluation_input[role]
        source = selected["source_lineage"][role]
        if (
            observed["evidence_set_digest"] != source["evidence_set_digest"]
            or observed["source_revision"] != source["source_revision"]
        ):
            raise _error("source-mismatch", "evaluation observation does not match proposal lineage")
    return copy.deepcopy(validated_set), copy.deepcopy(selected)


def _memory_off(reason: str) -> dict[str, Any]:
    return {
        "mode": "memory-off",
        "fallback_reason": reason,
        "retrieval_receipt_digest": None,
        "context_records": [],
        "context_set_digest": oe.canonical_digest([]),
        "record_count": 0,
    }


def _advisory_context(
    decision_input: Any | None,
    trusted_conformance_receipts: Any | None,
    trusted_source_digests: Any | None,
) -> dict[str, Any]:
    supplied = (
        decision_input is not None,
        trusted_conformance_receipts is not None,
        trusted_source_digests is not None,
    )
    if not any(supplied):
        return _memory_off("not-requested")
    if not all(supplied):
        return _memory_off("context-input-incomplete")
    try:
        receipt = memory.decide_retrieval(
            decision_input,
            trusted_conformance_receipts=trusted_conformance_receipts,
            trusted_source_digests=trusted_source_digests,
        )
    except (MemoryError, memory.MemoryContractError, TypeError, ValueError):
        return _memory_off("production-receipt-rejected")
    if receipt["fallback_to_no_memory"]:
        return _memory_off("production-fallback")
    response = decision_input.get("response") if isinstance(decision_input, dict) else None
    records = response.get("records") if isinstance(response, dict) else None
    if not isinstance(records, list) or not records:
        return _memory_off("context-empty")
    dispositions = receipt.get("dispositions")
    if not isinstance(dispositions, list) or len(dispositions) != len(records):
        return _memory_off("context-identity-mismatch")
    accepted: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_digests: set[str] = set()
    by_id = {
        item.get("record_id"): item
        for item in dispositions
        if isinstance(item, dict)
    }
    if len(by_id) != len(dispositions):
        return _memory_off("context-identity-mismatch")
    try:
        for raw in records:
            record = memory.validate_record(raw)
            disposition = by_id.get(record["record_id"])
            if (
                disposition is None
                or disposition.get("disposition") != "adopt-as-context"
                or disposition.get("record_digest") != record["canonical_digest"]
                or record["content"] is None
                or record["record_id"] in seen_ids
                or record["canonical_digest"] in seen_digests
            ):
                return _memory_off("context-not-fully-adopted")
            seen_ids.add(record["record_id"])
            seen_digests.add(record["canonical_digest"])
            accepted.append(
                {
                    "record_id": record["record_id"],
                    "record_digest": record["canonical_digest"],
                }
            )
    except (memory.MemoryContractError, TypeError, ValueError):
        return _memory_off("production-receipt-rejected")
    accepted.sort(key=lambda item: (item["record_digest"], item["record_id"]))
    return {
        "mode": "synthetic-advisory",
        "fallback_reason": None,
        "retrieval_receipt_digest": receipt["receipt_digest"],
        "context_records": accepted,
        "context_set_digest": oe.canonical_digest(accepted),
        "record_count": len(accepted),
    }


def _valid_pass(observation: Mapping[str, Any]) -> bool:
    return (
        observation["outcome"] == "passed"
        and observation["passed_scenarios"] == observation["scenario_count"]
        and all(
            observation[field] == 0
            for field in (
                "decision_failures",
                "recovery_failures",
                "determinism_failures",
                "authority_failures",
                "privacy_failures",
            )
        )
    )


def _within_regression(candidate: int, baseline: int) -> bool:
    return candidate * 10_000 <= baseline * (10_000 + MAX_REGRESSION_BPS)


def _comparison(document: Mapping[str, Any]) -> dict[str, Any]:
    baseline = document["baseline"]
    candidate = document["candidate"]
    baseline_valid = _valid_pass(baseline)
    scenario_equivalent = (
        baseline["scenario_set_digest"] == candidate["scenario_set_digest"]
        and baseline["scenario_count"] == candidate["scenario_count"]
    )
    environment_equivalent = (
        baseline["environment_fingerprint"] == candidate["environment_fingerprint"]
    )
    candidate_valid = _valid_pass(candidate)
    duration_within_limit = _within_regression(
        candidate["duration_ms"], baseline["duration_ms"]
    )
    resource_within_limit = _within_regression(
        candidate["resource_units"], baseline["resource_units"]
    )
    if not baseline_valid:
        status = "baseline-invalid"
    elif not scenario_equivalent:
        status = "input-mismatch"
    elif not environment_equivalent:
        status = "environment-mismatch"
    elif candidate["outcome"] in UNCERTAIN_OUTCOMES:
        status = "execution-uncertain"
    elif not candidate_valid or not duration_within_limit or not resource_within_limit:
        status = "regressed"
    else:
        status = "qualified"
    return {
        "status": status,
        "baseline_valid": baseline_valid,
        "scenario_equivalent": scenario_equivalent,
        "environment_equivalent": environment_equivalent,
        "candidate_valid": candidate_valid,
        "duration_within_limit": duration_within_limit,
        "resource_within_limit": resource_within_limit,
    }


def build_evaluation_result(
    evaluation_input: Any,
    proposal_set: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
    *,
    memory_decision_input: Any | None = None,
    trusted_conformance_receipts: Any | None = None,
    trusted_source_digests: Any | None = None,
) -> dict[str, Any]:
    document = validate_evaluation_input(evaluation_input)
    validated_set, selected = _validated_source(
        proposal_set, records, evidence_documents, document
    )
    policy = fixed_policy()
    context = _advisory_context(
        memory_decision_input,
        trusted_conformance_receipts,
        trusted_source_digests,
    )
    result = seal_evaluation_result(
        {
            "contract_version": CONTRACT_VERSION,
            "kind": RESULT_KIND,
            "evaluation_id": f"evaluation:{document['evaluation_input_digest']}",
            "proposal": {
                "proposal_id": selected["proposal_id"],
                "proposal_set_digest": validated_set["proposal_set_digest"],
                "source_record_set_digest": validated_set["source_record_set_digest"],
            },
            "source_lineage": copy.deepcopy(selected["source_lineage"]),
            "evaluation_input_digest": document["evaluation_input_digest"],
            "policy": policy,
            "policy_digest": oe.canonical_digest(policy),
            "context": context,
            "comparison": _comparison(document),
            "authority_invariants": authority_invariants(),
        }
    )
    _document_size(result)
    return result


def validate_evaluation_result(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._finite(document)
        _document_size(document)
        oe._exact(
            document,
            required={
                "contract_version", "kind", "evaluation_id", "proposal",
                "source_lineage", "evaluation_input_digest", "policy",
                "policy_digest", "context", "comparison", "authority_invariants",
                "evaluation_result_digest",
            },
        )
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != RESULT_KIND:
            raise _error("unsupported-contract", "evaluation result contract is unsupported")
        oe._identifier(document["evaluation_id"])
        proposal_ref = oe._object(document["proposal"])
        oe._exact(proposal_ref, required={"proposal_id", "proposal_set_digest", "source_record_set_digest"})
        oe._identifier(proposal_ref["proposal_id"])
        oe._digest(proposal_ref["proposal_set_digest"])
        oe._digest(proposal_ref["source_record_set_digest"])
        oe._object(document["source_lineage"])
        oe._digest(document["evaluation_input_digest"])
        if document["policy"] != fixed_policy():
            raise _error("policy-mismatch", "evaluation policy changed")
        if document["policy_digest"] != oe.canonical_digest(document["policy"]):
            raise _error("digest-mismatch", "evaluation policy digest does not match")
        context = oe._object(document["context"])
        oe._exact(context, required={"mode", "fallback_reason", "retrieval_receipt_digest", "context_records", "context_set_digest", "record_count"})
        oe._enum(context["mode"], {"memory-off", "synthetic-advisory"})
        if context["fallback_reason"] is not None:
            oe._identifier(context["fallback_reason"])
        if context["retrieval_receipt_digest"] is not None:
            oe._digest(context["retrieval_receipt_digest"])
        records = oe._array(context["context_records"], maximum=memory.MAX_RECORDS)
        for item in records:
            item = oe._object(item)
            oe._exact(item, required={"record_id", "record_digest"})
            oe._identifier(item["record_id"])
            oe._digest(item["record_digest"])
        oe._digest(context["context_set_digest"])
        if context["context_set_digest"] != oe.canonical_digest(records):
            raise _error("digest-mismatch", "context set digest does not match")
        if context["record_count"] != len(records):
            raise _error("invalid-structure", "context record count does not match")
        if context["mode"] == "memory-off" and (records or context["retrieval_receipt_digest"] is not None or context["fallback_reason"] is None):
            raise _error("invalid-structure", "memory-off context is inconsistent")
        if context["mode"] == "synthetic-advisory" and (not records or context["retrieval_receipt_digest"] is None or context["fallback_reason"] is not None):
            raise _error("invalid-structure", "synthetic advisory context is inconsistent")
        comparison = oe._object(document["comparison"])
        oe._exact(comparison, required={"status", "baseline_valid", "scenario_equivalent", "environment_equivalent", "candidate_valid", "duration_within_limit", "resource_within_limit"})
        oe._enum(comparison["status"], {"baseline-invalid", "input-mismatch", "environment-mismatch", "execution-uncertain", "regressed", "qualified"})
        for field in set(comparison) - {"status"}:
            if not isinstance(comparison[field], bool):
                raise _error("invalid-structure", "comparison flags must be booleans")
        if document["authority_invariants"] != authority_invariants():
            raise _error("authority-violation", "evaluation result authority invariants changed")
        declared = oe._digest(document["evaluation_result_digest"])
        if declared != oe.canonical_digest(_body(document, "evaluation_result_digest")):
            raise _error("digest-mismatch", "evaluation result digest does not match")
    except (CandidateEvaluationError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    return copy.deepcopy(document)


def verify_evaluation_result(
    evaluation_result: Any,
    evaluation_input: Any,
    proposal_set: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
    *,
    memory_decision_input: Any | None = None,
    trusted_conformance_receipts: Any | None = None,
    trusted_source_digests: Any | None = None,
) -> dict[str, Any]:
    document = validate_evaluation_input(evaluation_input)
    raw_records = _bounded_sources(
        records,
        limit=proposal.lineage.MAX_RECORDS,
        code="record-count",
        message="candidate evaluation source has an unsupported record count",
    )
    raw_evidence = _bounded_sources(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="candidate evaluation evidence exceeds the document count bound",
    )
    expected = build_evaluation_result(
        document, proposal_set, raw_records, raw_evidence,
        memory_decision_input=memory_decision_input,
        trusted_conformance_receipts=trusted_conformance_receipts,
        trusted_source_digests=trusted_source_digests,
    )
    _, selected = _validated_source(proposal_set, raw_records, raw_evidence, document)
    try:
        observed = validate_evaluation_result(evaluation_result)
    except CandidateEvaluationError:
        observed = None
        status = "failed"
        failure_code = "invalid-evaluation-result"
    else:
        status = "passed" if observed == expected else "failed"
        failure_code = None if status == "passed" else "evaluation-mismatch"
    result = seal_verification_result(
        {
            "contract_version": CONTRACT_VERSION,
            "kind": VERIFICATION_KIND,
            "verification_id": f"verification:{document['evaluation_input_digest']}",
            "proposal_id": selected["proposal_id"],
            "source_record_set_digest": selected["source_lineage"]["source_record_set_digest"],
            "verifier": copy.deepcopy(selected["role_assignments"]["independent_verifier"]),
            "evaluation_input_digest": document["evaluation_input_digest"],
            "observed_evaluation_result_digest": (
                observed["evaluation_result_digest"] if observed is not None else None
            ),
            "expected_evaluation_result_digest": expected["evaluation_result_digest"],
            "status": status,
            "failure_code": failure_code,
            "structural_independence_only": True,
            "authority_invariants": authority_invariants(),
        }
    )
    _document_size(result)
    return result


def validate_verification_result(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._finite(document)
        _document_size(document)
        oe._exact(document, required={
            "contract_version", "kind", "verification_id", "proposal_id",
            "source_record_set_digest", "verifier", "evaluation_input_digest",
            "observed_evaluation_result_digest", "expected_evaluation_result_digest",
            "status", "failure_code", "structural_independence_only",
            "authority_invariants", "verification_result_digest",
        })
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != VERIFICATION_KIND:
            raise _error("unsupported-contract", "verification result contract is unsupported")
        oe._identifier(document["verification_id"])
        oe._identifier(document["proposal_id"])
        oe._digest(document["source_record_set_digest"])
        oe._object(document["verifier"])
        oe._digest(document["evaluation_input_digest"])
        if document["observed_evaluation_result_digest"] is not None:
            oe._digest(document["observed_evaluation_result_digest"])
        oe._digest(document["expected_evaluation_result_digest"])
        status = oe._enum(document["status"], {"passed", "failed"})
        if document["failure_code"] is not None:
            oe._enum(document["failure_code"], {"invalid-evaluation-result", "evaluation-mismatch"})
        if (status == "passed") != (document["failure_code"] is None):
            raise _error("invalid-structure", "verification status contradicts failure code")
        if document["structural_independence_only"] is not True:
            raise _error("authority-violation", "verification overstates actor authentication")
        if document["authority_invariants"] != authority_invariants():
            raise _error("authority-violation", "verification authority invariants changed")
        declared = oe._digest(document["verification_result_digest"])
        if declared != oe.canonical_digest(_body(document, "verification_result_digest")):
            raise _error("digest-mismatch", "verification result digest does not match")
    except (CandidateEvaluationError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    return copy.deepcopy(document)


def build_promotion_packet(
    evaluation_result: Any,
    verification_result: Any,
    evaluation_input: Any,
    proposal_set: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
    *,
    memory_decision_input: Any | None = None,
    trusted_conformance_receipts: Any | None = None,
    trusted_source_digests: Any | None = None,
) -> dict[str, Any]:
    observed = validate_evaluation_result(evaluation_result)
    verified = validate_verification_result(verification_result)
    document = validate_evaluation_input(evaluation_input)
    raw_records = _bounded_sources(
        records,
        limit=proposal.lineage.MAX_RECORDS,
        code="record-count",
        message="candidate evaluation source has an unsupported record count",
    )
    raw_evidence = _bounded_sources(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="candidate evaluation evidence exceeds the document count bound",
    )
    expected_verification = verify_evaluation_result(
        observed, document, proposal_set, raw_records, raw_evidence,
        memory_decision_input=memory_decision_input,
        trusted_conformance_receipts=trusted_conformance_receipts,
        trusted_source_digests=trusted_source_digests,
    )
    if verified != expected_verification:
        raise _error("verification-mismatch", "verification result does not match deterministic replay")
    _, selected = _validated_source(proposal_set, raw_records, raw_evidence, document)
    disposition = (
        "qualified-awaiting-human-decision"
        if observed["comparison"]["status"] == "qualified" and verified["status"] == "passed"
        else "not-qualified"
    )
    packet = seal_promotion_packet(
        {
            "contract_version": CONTRACT_VERSION,
            "kind": PACKET_KIND,
            "packet_id": f"promotion-packet:{verified['verification_result_digest']}",
            "proposal_id": selected["proposal_id"],
            "source_record_set_digest": selected["source_lineage"]["source_record_set_digest"],
            "evaluation_input_digest": document["evaluation_input_digest"],
            "policy_digest": observed["policy_digest"],
            "context_set_digest": observed["context"]["context_set_digest"],
            "comparison_status": observed["comparison"]["status"],
            "evaluation_result_digest": observed["evaluation_result_digest"],
            "verification_result_digest": verified["verification_result_digest"],
            "disposition": disposition,
            "promotion_gate": {
                "gate_kind": "independent-human-platform",
                "required": True,
                "status": "pending",
                "promoter": copy.deepcopy(selected["promotion_gate"]["promoter"]),
            },
            "packet_only_invariants": packet_only_invariants(),
            "authority_invariants": authority_invariants(),
        }
    )
    _document_size(packet)
    return packet


def validate_promotion_packet(
    packet: Any,
    evaluation_result: Any,
    verification_result: Any,
    evaluation_input: Any,
    proposal_set: Any,
    records: Iterable[Any],
    evidence_documents: Iterable[Any],
    **context: Any,
) -> dict[str, Any]:
    raw_records = _bounded_sources(
        records,
        limit=proposal.lineage.MAX_RECORDS,
        code="record-count",
        message="candidate evaluation source has an unsupported record count",
    )
    raw_evidence = _bounded_sources(
        evidence_documents,
        limit=oe.MAX_SET_DOCUMENTS,
        code="document-count",
        message="candidate evaluation evidence exceeds the document count bound",
    )
    expected = build_promotion_packet(
        evaluation_result, verification_result, evaluation_input,
        proposal_set, raw_records, raw_evidence, **context
    )
    try:
        supplied = oe._object(packet)
        oe._finite(supplied)
        _document_size(supplied)
        oe._exact(supplied, required=set(expected))
        if supplied.get("contract_version") != CONTRACT_VERSION or supplied.get("kind") != PACKET_KIND:
            raise _error("unsupported-contract", "promotion packet contract is unsupported")
        if supplied.get("packet_only_invariants") != packet_only_invariants():
            raise _error("authority-violation", "promotion packet action invariants changed")
        if supplied.get("authority_invariants") != authority_invariants():
            raise _error("authority-violation", "promotion packet authority invariants changed")
        declared = oe._digest(supplied.get("promotion_packet_digest"))
        if declared != oe.canonical_digest(_body(supplied, "promotion_packet_digest")):
            raise _error("digest-mismatch", "promotion packet digest does not match")
    except (CandidateEvaluationError, oe.OperationalEvidenceError) as error:
        raise _translate(error) from error
    if supplied != expected:
        raise _error("packet-mismatch", "promotion packet does not match deterministic replay")
    return copy.deepcopy(supplied)


def load_json(path: Any) -> dict[str, Any]:
    try:
        return proposal.load_json(path)
    except proposal.ProposalContractError as error:
        raise _translate(error) from error
