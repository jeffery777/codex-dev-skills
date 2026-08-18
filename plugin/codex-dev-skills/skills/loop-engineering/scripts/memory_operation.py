"""Strict provider-neutral Memory M0 operation contracts.

This module validates and composes offline documents only.  It contains no
adapter dispatch, backend, database, persistence, network, or platform path.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

import memory_contract as memory
import operational_evidence as oe


CONTRACT_VERSION = "loop-memory-operation/v0"
AUTHORITY_KIND = "operation-authority"
REQUEST_KIND = "authorized-operation-request"
RECEIPT_KIND = "execution-receipt"
TRUSTED_TIME_KIND = "trusted-time-receipt"
OPERATIONS = frozenset({"upsert", "invalidate", "tombstone", "delete"})
OUTCOMES = frozenset({"applied", "idempotent-replay", "failed"})
FAILURE_CODES = frozenset({
    "authority-rejected", "capability-drift", "schema-mismatch",
    "platform-mismatch", "lock-timeout", "interrupted", "disk-full",
    "integrity-failure", "transaction-failure", "commit-uncertain",
    "conflicting-replay", "unsupported",
})


class MemoryOperationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> MemoryOperationError:
    return MemoryOperationError(code, message)


def _translate(error: Exception) -> MemoryOperationError:
    return _error(
        getattr(error, "code", "invalid-structure"),
        "memory operation input is invalid",
    )


def authority_invariants() -> dict[str, bool]:
    return {
        "used_as_general_authorization": False,
        "used_as_completion_evidence": False,
        "unrelated_external_write_authorized": False,
        "verification_performed": False,
        "review_performed": False,
        "acceptance_performed": False,
        "promotion_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        "deploy_authorized": False,
        "activation_authorized": False,
        "validator_runtime_action_performed": False,
    }


def _body(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != "document_digest"}


def seal_document(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    document["document_digest"] = oe.canonical_digest(_body(document))
    return document


def seal_trusted_time(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    document["receipt_digest"] = oe.canonical_digest({
        key: copy.deepcopy(item) for key, item in document.items() if key != "receipt_digest"
    })
    return document


def _digest_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return oe._digest(value)


def _validate_receipt_set(value: Any, label: str) -> list[str]:
    document = oe._object(value)
    oe._exact(document, required={"receipt_digests"})
    digests = oe._array(document["receipt_digests"], maximum=64)
    for digest in digests:
        oe._digest(digest)
    if not digests or digests != sorted(set(digests)):
        raise _error("caller-evidence-rejected", f"{label} must be a sorted unique non-empty digest set")
    return list(digests)


def _adapter(value: Any) -> dict[str, Any]:
    adapter = oe._object(value)
    oe._exact(adapter, required={
        "adapter_id", "adapter_version", "schema_fingerprint",
        "capability_fingerprint", "required_capabilities",
    })
    oe._identifier(adapter["adapter_id"])
    oe._identifier(adapter["adapter_version"])
    oe._digest(adapter["schema_fingerprint"])
    oe._digest(adapter["capability_fingerprint"])
    required = oe._array(adapter["required_capabilities"], maximum=len(memory.CAPABILITIES))
    if required != sorted(set(required)) or not required:
        raise _error("invalid-structure", "adapter capabilities must be sorted and unique")
    for capability in required:
        oe._enum(capability, set(memory.CAPABILITIES))
    return copy.deepcopy(adapter)


def _repository_and_namespace(document: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    repository = memory.validate_repository_identity(document["repository"])
    namespace = oe._string(document["namespace"], maximum=128)
    if not memory.NAMESPACE.fullmatch(namespace):
        raise _error("invalid-structure", "namespace syntax is invalid")
    return repository, namespace


def _validate_common(value: Any, kind: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    document = oe._object(value)
    oe._finite(document)
    if len(oe.canonical_json(document).encode("utf-8")) > oe.MAX_DOCUMENT_BYTES:
        raise _error("document-size", "memory operation document exceeds the size bound")
    oe._exact(document, required={
        "contract_version", "kind", "document_id", "repository", "namespace",
        "payload", "authority_invariants", "document_digest",
    })
    if document["contract_version"] != CONTRACT_VERSION or document["kind"] != kind:
        raise _error("unsupported-contract", "memory operation contract is unsupported")
    oe._identifier(document["document_id"])
    repository, namespace = _repository_and_namespace(document)
    if document["authority_invariants"] != authority_invariants():
        raise _error("authority-violation", "memory operation authority invariants changed")
    declared = oe._digest(document["document_digest"])
    if declared != oe.canonical_digest(_body(document)):
        raise _error("digest-mismatch", "memory operation document digest does not match")
    return copy.deepcopy(document), repository, namespace


def _validate_eligibility_receipt(value: Any) -> dict[str, Any]:
    receipt = oe._object(value)
    oe._exact(receipt, required={
        "contract_version", "kind", "record_id", "record_digest", "eligible",
        "reasons", "authority_invariants", "receipt_digest",
    })
    if receipt["contract_version"] != memory.CONTRACT_VERSION or receipt["kind"] != "memory-write-eligibility-receipt":
        raise _error("eligibility-rejected", "eligibility receipt contract is unsupported")
    oe._identifier(receipt["record_id"])
    oe._digest(receipt["record_digest"])
    reasons = oe._array(receipt["reasons"], maximum=64)
    if receipt["eligible"] is not True or reasons:
        raise _error("eligibility-rejected", "eligibility receipt is not accepted")
    expected = {
        "candidate_only": True,
        "write_performed": False,
        "external_write_authorized": False,
        "completion_proven": False,
    }
    if receipt["authority_invariants"] != expected:
        raise _error("authority-violation", "eligibility authority invariants changed")
    declared = oe._digest(receipt["receipt_digest"])
    body = {key: copy.deepcopy(item) for key, item in receipt.items() if key != "receipt_digest"}
    if declared != memory.canonical_digest(body):
        raise _error("digest-mismatch", "eligibility receipt digest does not match")
    return copy.deepcopy(receipt)


def validate_operation_authority(value: Any) -> dict[str, Any]:
    try:
        document, _, _ = _validate_common(value, AUTHORITY_KIND)
        payload = oe._object(document["payload"])
        oe._exact(payload, required={
            "authority_id", "issuer_principal", "issued_at", "expires_at", "nonce",
            "operation", "operation_id", "request_id", "idempotency_key",
            "target_record_id", "target_before_digest", "candidate_record_digest",
            "mutation_candidate_digest", "eligibility_receipt_digests",
            "lifecycle_effect", "adapter", "state_root", "authority_receipt_digest",
            "memory_operation_authorized",
        })
        for field in ("authority_id", "nonce", "operation_id", "request_id", "idempotency_key", "target_record_id"):
            oe._identifier(payload[field])
        issuer = oe._object(payload["issuer_principal"])
        oe._exact(issuer, required={"kind", "id"})
        oe._enum(issuer["kind"], {"human", "platform"})
        oe._identifier(issuer["id"])
        issued = oe._timestamp(payload["issued_at"])
        expires = oe._timestamp(payload["expires_at"])
        if expires <= issued:
            raise _error("authority-rejected", "authority expiry must follow issuance")
        operation = oe._enum(payload["operation"], set(OPERATIONS))
        _digest_or_none(payload["target_before_digest"])
        oe._digest(payload["candidate_record_digest"])
        oe._digest(payload["mutation_candidate_digest"])
        eligibility = oe._array(payload["eligibility_receipt_digests"], maximum=64)
        for digest in eligibility:
            oe._digest(digest)
        if eligibility != sorted(set(eligibility)) or not eligibility:
            raise _error("invalid-structure", "eligibility receipt digests must be sorted and unique")
        expected_effect = "logical-delete" if operation == "delete" else operation
        if payload["lifecycle_effect"] != expected_effect:
            raise _error("lifecycle-rejected", "operation lifecycle effect is invalid")
        _adapter(payload["adapter"])
        state_root = oe._object(payload["state_root"])
        oe._exact(state_root, required={"state_root_class", "identity_digest"})
        if state_root["state_root_class"] != "approved-machine-local":
            raise _error("placement-rejected", "state root class is unsupported")
        oe._digest(state_root["identity_digest"])
        oe._digest(payload["authority_receipt_digest"])
        if payload["memory_operation_authorized"] is not True:
            raise _error("authority-rejected", "exact memory operation authority is absent")
    except (MemoryOperationError, memory.MemoryContractError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryOperationError):
            raise
        raise _translate(error) from error
    return document


def validate_trusted_time(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._exact(document, required={
            "contract_version", "kind", "clock_id", "observed_at", "receipt_digest",
        })
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != TRUSTED_TIME_KIND:
            raise _error("unsupported-contract", "trusted time receipt is unsupported")
        oe._identifier(document["clock_id"])
        oe._timestamp(document["observed_at"])
        declared = oe._digest(document["receipt_digest"])
        body = {key: copy.deepcopy(item) for key, item in document.items() if key != "receipt_digest"}
        if declared != oe.canonical_digest(body):
            raise _error("digest-mismatch", "trusted time receipt digest does not match")
    except (MemoryOperationError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryOperationError):
            raise
        raise _translate(error) from error
    return copy.deepcopy(document)


def _validate_authorized_request_shape(value: Any) -> dict[str, Any]:
    try:
        document, _, _ = _validate_common(value, REQUEST_KIND)
        payload = oe._object(document["payload"])
        oe._exact(payload, required={
            "authority_document_digest", "authority_receipt_digest",
            "mutation_candidate_digest", "eligibility_receipt_digest",
            "operation", "operation_id", "request_id", "idempotency_key",
            "target_record_id", "target_before_digest", "candidate_record_digest",
            "lifecycle_effect", "adapter", "expected_pre_state_digest",
            "authority_id", "issuer_principal", "issued_at", "expires_at", "nonce",
            "state_root", "trusted_time_receipt_digest", "authority_observed_at",
            "authority_verified_for_exact_request", "execution_performed",
        })
        for field in ("authority_document_digest", "authority_receipt_digest", "mutation_candidate_digest", "eligibility_receipt_digest", "candidate_record_digest"):
            oe._digest(payload[field])
        _digest_or_none(payload["target_before_digest"])
        _digest_or_none(payload["expected_pre_state_digest"])
        oe._enum(payload["operation"], set(OPERATIONS))
        for field in ("operation_id", "request_id", "idempotency_key", "target_record_id"):
            oe._identifier(payload[field])
        oe._identifier(payload["authority_id"])
        issuer = oe._object(payload["issuer_principal"])
        oe._exact(issuer, required={"kind", "id"})
        oe._enum(issuer["kind"], {"human", "platform"})
        oe._identifier(issuer["id"])
        issued = oe._timestamp(payload["issued_at"])
        expires = oe._timestamp(payload["expires_at"])
        observed = oe._timestamp(payload["authority_observed_at"])
        if expires <= issued or not (issued <= observed < expires):
            raise _error("authority-expired", "authorized request lifecycle binding is invalid")
        oe._identifier(payload["nonce"])
        state_root = oe._object(payload["state_root"])
        oe._exact(state_root, required={"state_root_class", "identity_digest"})
        if state_root["state_root_class"] != "approved-machine-local":
            raise _error("placement-rejected", "authorized request state root is unsupported")
        oe._digest(state_root["identity_digest"])
        oe._digest(payload["trusted_time_receipt_digest"])
        if payload["lifecycle_effect"] != ("logical-delete" if payload["operation"] == "delete" else payload["operation"]):
            raise _error("lifecycle-rejected", "authorized request lifecycle effect is invalid")
        _adapter(payload["adapter"])
        if payload["authority_verified_for_exact_request"] is not True or payload["execution_performed"] is not False:
            raise _error("authority-violation", "authorized request action boundary changed")
    except (MemoryOperationError, memory.MemoryContractError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryOperationError):
            raise
        raise _translate(error) from error
    return document


def validate_authorized_request(
    value: Any,
    authority_value: Any,
    mutation_candidate_value: Any,
    eligibility_receipt_value: Any,
    *,
    accepted_authority_receipts: Any,
    accepted_eligibility_receipts: Any,
    trusted_time_value: Any,
    accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str | None,
) -> dict[str, Any]:
    document = _validate_authorized_request_shape(value)
    expected = build_authorized_request(
        authority_value,
        mutation_candidate_value,
        eligibility_receipt_value,
        accepted_authority_receipts=accepted_authority_receipts,
        accepted_eligibility_receipts=accepted_eligibility_receipts,
        trusted_time_value=trusted_time_value,
        accepted_trusted_time_receipts=accepted_trusted_time_receipts,
        expected_pre_state_digest=expected_pre_state_digest,
    )
    if document != expected:
        raise _error("binding-mismatch", "authorized request does not match reconstructed caller-owned evidence")
    return document


def build_authorized_request(
    authority_value: Any,
    mutation_candidate_value: Any,
    eligibility_receipt_value: Any,
    *,
    accepted_authority_receipts: Any,
    accepted_eligibility_receipts: Any,
    trusted_time_value: Any,
    accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str | None,
) -> dict[str, Any]:
    try:
        authority = validate_operation_authority(authority_value)
        candidate = memory.validate_mutation_candidate(mutation_candidate_value)
        receipt = _validate_eligibility_receipt(eligibility_receipt_value)
        accepted_authority = set(_validate_receipt_set(accepted_authority_receipts, "accepted authority receipts"))
        accepted_eligibility = set(_validate_receipt_set(accepted_eligibility_receipts, "accepted eligibility receipts"))
        trusted_time = validate_trusted_time(trusted_time_value)
        accepted_time = set(_validate_receipt_set(accepted_trusted_time_receipts, "accepted trusted time receipts"))
        payload = authority["payload"]
        if trusted_time["receipt_digest"] not in accepted_time:
            raise _error("caller-evidence-rejected", "trusted time receipt is not caller-accepted")
        now = oe._timestamp(trusted_time["observed_at"])
        if not (oe._timestamp(payload["issued_at"]) <= now < oe._timestamp(payload["expires_at"])):
            raise _error("authority-expired", "operation authority is not currently valid")
        if payload["authority_receipt_digest"] not in accepted_authority:
            raise _error("caller-evidence-rejected", "authority receipt is not caller-accepted")
        if receipt["receipt_digest"] not in accepted_eligibility or set(payload["eligibility_receipt_digests"]) != {receipt["receipt_digest"]}:
            raise _error("caller-evidence-rejected", "eligibility receipt is not caller-accepted")
        candidate_digest = memory.canonical_digest(candidate)
        if payload["mutation_candidate_digest"] != candidate_digest:
            raise _error("binding-mismatch", "mutation candidate binding does not match")
        if candidate["eligibility_receipt_digest"] != receipt["receipt_digest"]:
            raise _error("binding-mismatch", "candidate eligibility binding does not match")
        if receipt["record_id"] != candidate["target_record_id"] or receipt["record_digest"] != payload["candidate_record_digest"]:
            raise _error("binding-mismatch", "candidate record binding does not match")
        for field in ("operation", "operation_id", "request_id", "idempotency_key", "target_record_id"):
            if payload[field] != candidate[field]:
                raise _error("binding-mismatch", "candidate operation identity does not match authority")
        if candidate["repository"] != authority["repository"] or candidate["namespace"] != authority["namespace"]:
            raise _error("identity-mismatch", "candidate scope does not match authority")
        if candidate["record"] is not None and (
            candidate["record"]["repository"] != candidate["repository"]
            or candidate["record"]["namespace"] != candidate["namespace"]
        ):
            raise _error("identity-mismatch", "candidate record scope does not match candidate envelope")
        expected_capability = {"upsert": "write_upsert", "invalidate": "invalidate", "tombstone": "tombstone", "delete": "delete"}[candidate["operation"]]
        if expected_capability not in payload["adapter"]["required_capabilities"] or set(candidate["required_capabilities"]) != set(payload["adapter"]["required_capabilities"]):
            raise _error("capability-mismatch", "candidate capabilities do not match authority")
        _digest_or_none(expected_pre_state_digest)
        if candidate["operation"] != "upsert" and expected_pre_state_digest is None:
            raise _error("binding-mismatch", "lifecycle operation requires an expected pre-state")
        if payload["target_before_digest"] != expected_pre_state_digest:
            raise _error("binding-mismatch", "expected pre-state does not match authority")
        request = seal_document({
            "contract_version": CONTRACT_VERSION,
            "kind": REQUEST_KIND,
            "document_id": f"authorized:{authority['document_digest']}",
            "repository": copy.deepcopy(authority["repository"]),
            "namespace": authority["namespace"],
            "payload": {
                "authority_document_digest": authority["document_digest"],
                "authority_receipt_digest": payload["authority_receipt_digest"],
                "mutation_candidate_digest": candidate_digest,
                "eligibility_receipt_digest": receipt["receipt_digest"],
                "operation": candidate["operation"],
                "operation_id": candidate["operation_id"],
                "request_id": candidate["request_id"],
                "idempotency_key": candidate["idempotency_key"],
                "target_record_id": candidate["target_record_id"],
                "target_before_digest": payload["target_before_digest"],
                "candidate_record_digest": receipt["record_digest"],
                "lifecycle_effect": payload["lifecycle_effect"],
                "adapter": copy.deepcopy(payload["adapter"]),
                "expected_pre_state_digest": expected_pre_state_digest,
                "authority_id": payload["authority_id"],
                "issuer_principal": copy.deepcopy(payload["issuer_principal"]),
                "issued_at": payload["issued_at"],
                "expires_at": payload["expires_at"],
                "nonce": payload["nonce"],
                "state_root": copy.deepcopy(payload["state_root"]),
                "trusted_time_receipt_digest": trusted_time["receipt_digest"],
                "authority_observed_at": trusted_time["observed_at"],
                "authority_verified_for_exact_request": True,
                "execution_performed": False,
            },
            "authority_invariants": authority_invariants(),
        })
        return _validate_authorized_request_shape(request)
    except (MemoryOperationError, memory.MemoryContractError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryOperationError):
            raise
        raise _translate(error) from error


def validate_execution_receipt(
    value: Any,
    authorized_request_value: Any,
    *,
    authority_value: Any,
    mutation_candidate_value: Any,
    eligibility_receipt_value: Any,
    accepted_authority_receipts: Any,
    accepted_eligibility_receipts: Any,
    trusted_time_value: Any,
    accepted_trusted_time_receipts: Any,
    expected_pre_state_digest: str | None,
    original_applied_receipt: Any | None = None,
) -> dict[str, Any]:
    try:
        document, repository, namespace = _validate_common(value, RECEIPT_KIND)
        request = validate_authorized_request(
            authorized_request_value,
            authority_value,
            mutation_candidate_value,
            eligibility_receipt_value,
            accepted_authority_receipts=accepted_authority_receipts,
            accepted_eligibility_receipts=accepted_eligibility_receipts,
            trusted_time_value=trusted_time_value,
            accepted_trusted_time_receipts=accepted_trusted_time_receipts,
            expected_pre_state_digest=expected_pre_state_digest,
        )
        if repository != request["repository"] or namespace != request["namespace"]:
            raise _error("identity-mismatch", "execution receipt scope does not match request")
        payload = oe._object(document["payload"])
        oe._exact(payload, required={
            "authorized_request_digest", "authority_document_digest",
            "authority_receipt_digest", "eligibility_receipt_digest",
            "mutation_candidate_digest", "operation", "operation_id", "request_id",
            "idempotency_key", "target_record_id", "adapter", "platform_fingerprint",
            "transaction_id", "outcome", "failure_code", "pre_state_digest",
            "post_state_digest", "original_applied_receipt_digest",
            "atomic_state_and_receipt_committed", "no_partial_success",
            "no_uncertain_success", "no_second_application",
        })
        expected = request["payload"]
        bindings = {
            "authorized_request_digest": request["document_digest"],
            "authority_document_digest": expected["authority_document_digest"],
            "authority_receipt_digest": expected["authority_receipt_digest"],
            "eligibility_receipt_digest": expected["eligibility_receipt_digest"],
            "mutation_candidate_digest": expected["mutation_candidate_digest"],
            "operation": expected["operation"], "operation_id": expected["operation_id"],
            "request_id": expected["request_id"], "idempotency_key": expected["idempotency_key"],
            "target_record_id": expected["target_record_id"], "adapter": expected["adapter"],
        }
        if any(payload[key] != item for key, item in bindings.items()):
            raise _error("binding-mismatch", "execution receipt binding does not match request")
        oe._digest(payload["platform_fingerprint"])
        oe._identifier(payload["transaction_id"])
        outcome = oe._enum(payload["outcome"], set(OUTCOMES))
        _digest_or_none(payload["pre_state_digest"])
        _digest_or_none(payload["post_state_digest"])
        _digest_or_none(payload["original_applied_receipt_digest"])
        if payload["pre_state_digest"] != expected["expected_pre_state_digest"]:
            raise _error("binding-mismatch", "execution receipt pre-state does not match request")
        for field in ("atomic_state_and_receipt_committed", "no_partial_success", "no_uncertain_success", "no_second_application"):
            if not isinstance(payload[field], bool):
                raise _error("invalid-structure", "execution receipt assertions must be booleans")
        if not payload["no_partial_success"] or not payload["no_uncertain_success"] or not payload["no_second_application"]:
            raise _error("authority-violation", "execution receipt safety assertions changed")
        if outcome == "applied":
            if payload["failure_code"] is not None or payload["post_state_digest"] is None or payload["original_applied_receipt_digest"] is not None or payload["atomic_state_and_receipt_committed"] is not True:
                raise _error("receipt-rejected", "applied receipt is not atomically complete")
        elif outcome == "idempotent-replay":
            if payload["failure_code"] is not None or payload["original_applied_receipt_digest"] is None or payload["atomic_state_and_receipt_committed"] is not True:
                raise _error("receipt-rejected", "replay receipt is incomplete")
            if original_applied_receipt is None:
                raise _error("receipt-rejected", "replay requires the original applied receipt")
            original = validate_execution_receipt(
                original_applied_receipt, request,
                authority_value=authority_value,
                mutation_candidate_value=mutation_candidate_value,
                eligibility_receipt_value=eligibility_receipt_value,
                accepted_authority_receipts=accepted_authority_receipts,
                accepted_eligibility_receipts=accepted_eligibility_receipts,
                trusted_time_value=trusted_time_value,
                accepted_trusted_time_receipts=accepted_trusted_time_receipts,
                expected_pre_state_digest=expected_pre_state_digest,
            )
            if original["payload"]["outcome"] != "applied" or original["document_digest"] != payload["original_applied_receipt_digest"]:
                raise _error("receipt-rejected", "replay does not bind the original applied receipt")
            if original["payload"]["post_state_digest"] != payload["post_state_digest"]:
                raise _error("receipt-rejected", "replay post-state differs from the original")
        else:
            oe._enum(payload["failure_code"], set(FAILURE_CODES))
            if payload["post_state_digest"] is not None or payload["original_applied_receipt_digest"] is not None or payload["atomic_state_and_receipt_committed"] is not False:
                raise _error("receipt-rejected", "failed receipt cannot claim committed state")
    except (MemoryOperationError, memory.MemoryContractError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryOperationError):
            raise
        raise _translate(error) from error
    return document


def load_json(path: Any) -> dict[str, Any]:
    try:
        return oe.load_json(path)
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error
