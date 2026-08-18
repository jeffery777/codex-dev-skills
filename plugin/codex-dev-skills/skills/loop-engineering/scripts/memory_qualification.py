"""Paired Memory M0 safety/conformance qualification over released V3-B.

The wrapper never executes a backend and never changes a V3-B result.  A
wrapper ``memory-on`` arm is admitted only by separate caller-owned future M1
qualification evidence.
"""

from __future__ import annotations

import copy
from typing import Any, Mapping

import candidate_evaluation as evaluation
import operational_evidence as oe


CONTRACT_VERSION = "loop-memory-qualification/v0"
INPUT_KIND = "qualification-input"
RESULT_KIND = "qualification-result"
M1_RECEIPT_KIND = "m1-qualification-receipt"
FAILURE_FIELDS = (
    "authority_failures", "identity_failures", "atomicity_failures",
    "idempotency_failures", "lifecycle_failures", "privacy_failures",
    "recovery_failures", "schema_drift_failures",
)


class MemoryQualificationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> MemoryQualificationError:
    return MemoryQualificationError(code, message)


def _translate(error: Exception) -> MemoryQualificationError:
    return _error(getattr(error, "code", "invalid-structure"), "memory qualification input is invalid")


def authority_invariants() -> dict[str, bool]:
    return {
        "used_as_authorization": False,
        "used_as_completion_evidence": False,
        "external_write_authorized": False,
        "efficacy_claimed": False,
        "promotion_authorized": False,
        "merge_authorized": False,
        "release_authorized": False,
        "deploy_authorized": False,
        "activation_authorized": False,
    }


def _body(value: Mapping[str, Any], digest_field: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key != digest_field}


def seal_input(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    document["qualification_input_digest"] = oe.canonical_digest(_body(document, "qualification_input_digest"))
    return document


def seal_result(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    document["qualification_result_digest"] = oe.canonical_digest(_body(document, "qualification_result_digest"))
    return document


def seal_m1_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    document = copy.deepcopy(dict(value))
    document["receipt_digest"] = oe.canonical_digest(_body(document, "receipt_digest"))
    return document


def _adapter(value: Any) -> dict[str, Any]:
    adapter = oe._object(value)
    oe._exact(adapter, required={
        "adapter_id", "adapter_version", "schema_fingerprint",
        "capability_fingerprint", "platform_fingerprint",
    })
    oe._identifier(adapter["adapter_id"])
    oe._identifier(adapter["adapter_version"])
    for field in ("schema_fingerprint", "capability_fingerprint", "platform_fingerprint"):
        oe._digest(adapter[field])
    return copy.deepcopy(adapter)


def _safety(value: Any) -> dict[str, Any]:
    safety = oe._object(value)
    oe._exact(safety, required={*FAILURE_FIELDS, "backend_touch_count", "execution_receipt_digests"})
    for field in (*FAILURE_FIELDS, "backend_touch_count"):
        oe._integer(safety[field], minimum=0, maximum=1_000_000)
    receipts = oe._array(safety["execution_receipt_digests"], maximum=256)
    for digest in receipts:
        oe._digest(digest)
    if receipts != sorted(set(receipts)) or not receipts:
        raise _error("invalid-structure", "execution receipt digests must be sorted and unique")
    if safety["backend_touch_count"] < 1:
        raise _error("invalid-structure", "memory-on safety observation requires a backend touch")
    return copy.deepcopy(safety)


def _off_arm(value: Any) -> dict[str, Any]:
    arm = oe._object(value)
    oe._exact(arm, required={
        "mode", "evaluation_result_digest", "verification_result_digest",
        "backend_touch_count", "zero_backend_filesystem_touch_verified",
    })
    if arm["mode"] != "memory-off":
        raise _error("invalid-structure", "off arm mode is invalid")
    oe._digest(arm["evaluation_result_digest"])
    oe._digest(arm["verification_result_digest"])
    if arm["backend_touch_count"] != 0 or arm["zero_backend_filesystem_touch_verified"] is not True:
        raise _error("zero-touch-violation", "memory-off must prove zero backend/filesystem touch")
    return copy.deepcopy(arm)


def _on_arm(value: Any) -> dict[str, Any]:
    arm = oe._object(value)
    oe._exact(arm, required={
        "mode", "evaluation_result_digest", "verification_result_digest",
        "m1_qualification_receipt_digest", "adapter", "safety_observation",
    })
    if arm["mode"] != "memory-on":
        raise _error("invalid-structure", "on arm mode is invalid")
    oe._digest(arm["evaluation_result_digest"])
    oe._digest(arm["verification_result_digest"])
    oe._digest(arm["m1_qualification_receipt_digest"])
    _adapter(arm["adapter"])
    _safety(arm["safety_observation"])
    return copy.deepcopy(arm)


def _document_size(document: Any) -> None:
    if len(oe.canonical_json(document).encode("utf-8")) > oe.MAX_DOCUMENT_BYTES:
        raise _error("document-size", "memory qualification document exceeds the size bound")


def _validate_common_bindings(value: Any) -> dict[str, Any]:
    bindings = oe._object(value)
    oe._exact(bindings, required={
        "proposal", "source_lineage_digest", "evaluation_input_digest",
        "policy_digest", "comparison_digest",
        "verifier_digest",
    })
    proposal = oe._object(bindings["proposal"])
    oe._exact(proposal, required={"proposal_id", "proposal_set_digest", "source_record_set_digest"})
    oe._identifier(proposal["proposal_id"])
    oe._digest(proposal["proposal_set_digest"])
    oe._digest(proposal["source_record_set_digest"])
    for field in ("source_lineage_digest", "evaluation_input_digest", "policy_digest", "comparison_digest", "verifier_digest"):
        oe._digest(bindings[field])
    return copy.deepcopy(bindings)


def validate_qualification_input(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._finite(document)
        _document_size(document)
        oe._exact(document, required={
            "contract_version", "kind", "qualification_id", "common_v3b_bindings",
            "off_arm", "on_arm",
            "efficacy_claimed", "authority_invariants", "qualification_input_digest",
        })
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != INPUT_KIND:
            raise _error("unsupported-contract", "memory qualification contract is unsupported")
        oe._identifier(document["qualification_id"])
        _validate_common_bindings(document["common_v3b_bindings"])
        _off_arm(document["off_arm"])
        if document["on_arm"] is not None:
            _on_arm(document["on_arm"])
        if document["efficacy_claimed"] is not False or document["authority_invariants"] != authority_invariants():
            raise _error("authority-violation", "qualification authority or efficacy boundary changed")
        declared = oe._digest(document["qualification_input_digest"])
        if declared != oe.canonical_digest(_body(document, "qualification_input_digest")):
            raise _error("digest-mismatch", "qualification input digest does not match")
    except (MemoryQualificationError, evaluation.CandidateEvaluationError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryQualificationError):
            raise
        raise _translate(error) from error
    return copy.deepcopy(document)


def _digest_set(value: Any, field: str) -> set[str]:
    document = oe._object(value)
    oe._exact(document, required={field})
    values = oe._array(document[field], maximum=256)
    for digest in values:
        oe._digest(digest)
    if values != sorted(set(values)) or not values:
        raise _error("caller-evidence-rejected", "caller receipt set must be sorted, unique, and non-empty")
    return set(values)


def _validated_pair(result_value: Any, verification_value: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        result = evaluation.validate_evaluation_result(result_value)
        verification = evaluation.validate_verification_result(verification_value)
    except evaluation.CandidateEvaluationError as error:
        raise _translate(error) from error
    if (
        verification["status"] != "passed"
        or verification["observed_evaluation_result_digest"] != result["evaluation_result_digest"]
        or verification["expected_evaluation_result_digest"] != result["evaluation_result_digest"]
        or verification["proposal_id"] != result["proposal"]["proposal_id"]
        or verification["source_record_set_digest"] != result["proposal"]["source_record_set_digest"]
        or verification["evaluation_input_digest"] != result["evaluation_input_digest"]
    ):
        raise _error("v3b-rejected", "V3-B result and verification are not an exact passing pair")
    return result, verification


def _common_bindings(result: Mapping[str, Any], verification: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proposal": copy.deepcopy(result["proposal"]),
        "source_lineage_digest": oe.canonical_digest(result["source_lineage"]),
        "evaluation_input_digest": result["evaluation_input_digest"],
        "policy_digest": result["policy_digest"],
        "comparison_digest": oe.canonical_digest(result["comparison"]),
        "verifier_digest": oe.canonical_digest(verification["verifier"]),
    }


def validate_m1_qualification_receipt(value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        oe._finite(document)
        _document_size(document)
        oe._exact(document, required={
            "contract_version", "kind", "qualification_id", "common_v3b_bindings",
            "adapter", "safety_observation_digest", "execution_receipt_digests",
            "status", "receipt_digest",
        })
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != M1_RECEIPT_KIND:
            raise _error("unsupported-contract", "M1 qualification receipt is unsupported")
        oe._identifier(document["qualification_id"])
        _validate_common_bindings(document["common_v3b_bindings"])
        _adapter(document["adapter"])
        oe._digest(document["safety_observation_digest"])
        receipts = oe._array(document["execution_receipt_digests"], maximum=256)
        for digest in receipts:
            oe._digest(digest)
        if not receipts or receipts != sorted(set(receipts)):
            raise _error("invalid-structure", "M1 execution receipt digests must be sorted and unique")
        if document["status"] != "passed":
            raise _error("m1-rejected", "M1 qualification receipt did not pass")
        declared = oe._digest(document["receipt_digest"])
        if declared != oe.canonical_digest(_body(document, "receipt_digest")):
            raise _error("digest-mismatch", "M1 qualification receipt digest does not match")
    except (MemoryQualificationError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryQualificationError):
            raise
        raise _translate(error) from error
    return copy.deepcopy(document)


def build_qualification_result(
    input_value: Any,
    off_result_value: Any,
    off_verification_value: Any,
    *,
    accepted_v3b_receipts: Any,
    on_result_value: Any | None = None,
    on_verification_value: Any | None = None,
    m1_qualification_receipt_value: Any | None = None,
    accepted_m1_qualification_receipts: Any | None = None,
) -> dict[str, Any]:
    document = validate_qualification_input(input_value)
    accepted_v3b = _digest_set(accepted_v3b_receipts, "receipt_digests")
    off_result, off_verification = _validated_pair(off_result_value, off_verification_value)
    if document["common_v3b_bindings"] != _common_bindings(off_result, off_verification):
        raise _error("pair-mismatch", "qualification input common bindings do not match V3-B")
    off_ref = document["off_arm"]
    if off_result["context"]["mode"] != "memory-off":
        raise _error("zero-touch-violation", "off arm V3-B context is not memory-off")
    if (
        off_ref["evaluation_result_digest"] != off_result["evaluation_result_digest"]
        or off_ref["verification_result_digest"] != off_verification["verification_result_digest"]
        or not {off_result["evaluation_result_digest"], off_verification["verification_result_digest"]}.issubset(accepted_v3b)
    ):
        raise _error("caller-evidence-rejected", "off arm V3-B evidence is not caller-accepted")
    on_ref = document["on_arm"]
    if on_ref is None:
        if (
            on_result_value is not None
            or on_verification_value is not None
            or m1_qualification_receipt_value is not None
            or accepted_m1_qualification_receipts is not None
        ):
            raise _error("invalid-structure", "memory-off-only qualification cannot accept M1 inputs")
        status = "memory-on-unavailable"
        on_summary = None
    else:
        if on_result_value is None or on_verification_value is None or m1_qualification_receipt_value is None or accepted_m1_qualification_receipts is None:
            raise _error("invalid-structure", "memory-on qualification inputs are incomplete")
        accepted_m1 = _digest_set(accepted_m1_qualification_receipts, "qualification_receipt_digests")
        m1_receipt = validate_m1_qualification_receipt(m1_qualification_receipt_value)
        on_result, on_verification = _validated_pair(on_result_value, on_verification_value)
        if (
            on_ref["evaluation_result_digest"] != on_result["evaluation_result_digest"]
            or on_ref["verification_result_digest"] != on_verification["verification_result_digest"]
            or not {on_result["evaluation_result_digest"], on_verification["verification_result_digest"]}.issubset(accepted_v3b)
            or on_ref["m1_qualification_receipt_digest"] not in accepted_m1
            or m1_receipt["receipt_digest"] != on_ref["m1_qualification_receipt_digest"]
        ):
            raise _error("caller-evidence-rejected", "memory-on evidence is not caller-accepted")
        common = _common_bindings(off_result, off_verification)
        if common != _common_bindings(on_result, on_verification):
            raise _error("pair-mismatch", "qualification arms do not share exact V3-B bindings")
        safety = _safety(on_ref["safety_observation"])
        expected_receipt_scope = {
            "qualification_id": document["qualification_id"],
            "common_v3b_bindings": common,
            "adapter": on_ref["adapter"],
            "safety_observation_digest": oe.canonical_digest(safety),
            "execution_receipt_digests": safety["execution_receipt_digests"],
        }
        if any(m1_receipt[key] != item for key, item in expected_receipt_scope.items()):
            raise _error("binding-mismatch", "M1 qualification receipt does not bind the exact qualification scope")
        failures = sum(safety[field] for field in FAILURE_FIELDS)
        status = "conformant-awaiting-human-decision" if failures == 0 else "not-conformant"
        on_summary = {
            "evaluation_result_digest": on_result["evaluation_result_digest"],
            "verification_result_digest": on_verification["verification_result_digest"],
            "m1_qualification_receipt_digest": on_ref["m1_qualification_receipt_digest"],
            "adapter": copy.deepcopy(on_ref["adapter"]),
            "safety_observation_digest": oe.canonical_digest(safety),
            "failure_count": failures,
        }
    result = seal_result({
        "contract_version": CONTRACT_VERSION,
        "kind": RESULT_KIND,
        "qualification_id": document["qualification_id"],
        "qualification_input_digest": document["qualification_input_digest"],
        "common_v3b_bindings": _common_bindings(off_result, off_verification),
        "off_arm": {
            "evaluation_result_digest": off_result["evaluation_result_digest"],
            "verification_result_digest": off_verification["verification_result_digest"],
            "backend_touch_count": 0,
            "zero_backend_filesystem_touch_verified": True,
        },
        "on_arm": on_summary,
        "status": status,
        "efficacy_claimed": False,
        "promotion_gate": {"required": True, "status": "pending", "kind": "independent-human-platform"},
        "authority_invariants": authority_invariants(),
    })
    return _validate_qualification_result_shape(result, document)


def _validate_qualification_result_shape(value: Any, input_value: Any) -> dict[str, Any]:
    try:
        document = oe._object(value)
        source = validate_qualification_input(input_value)
        oe._finite(document)
        _document_size(document)
        oe._exact(document, required={
            "contract_version", "kind", "qualification_id", "qualification_input_digest",
            "common_v3b_bindings", "off_arm", "on_arm", "status", "efficacy_claimed",
            "promotion_gate", "authority_invariants", "qualification_result_digest",
        })
        if document["contract_version"] != CONTRACT_VERSION or document["kind"] != RESULT_KIND:
            raise _error("unsupported-contract", "memory qualification result is unsupported")
        if document["qualification_id"] != source["qualification_id"] or document["qualification_input_digest"] != source["qualification_input_digest"]:
            raise _error("binding-mismatch", "qualification result does not bind its input")
        if _validate_common_bindings(document["common_v3b_bindings"]) != source["common_v3b_bindings"]:
            raise _error("binding-mismatch", "qualification result common bindings changed")
        off = oe._object(document["off_arm"])
        oe._exact(off, required={"evaluation_result_digest", "verification_result_digest", "backend_touch_count", "zero_backend_filesystem_touch_verified"})
        for field in ("evaluation_result_digest", "verification_result_digest"):
            oe._digest(off[field])
        if (
            off["evaluation_result_digest"] != source["off_arm"]["evaluation_result_digest"]
            or off["verification_result_digest"] != source["off_arm"]["verification_result_digest"]
        ):
            raise _error("binding-mismatch", "qualification result off arm changed")
        if off["backend_touch_count"] != 0 or off["zero_backend_filesystem_touch_verified"] is not True:
            raise _error("zero-touch-violation", "qualification result changed memory-off zero-touch")
        status = oe._enum(document["status"], {"conformant-awaiting-human-decision", "not-conformant", "memory-on-unavailable"})
        if (status == "memory-on-unavailable") != (document["on_arm"] is None):
            raise _error("invalid-structure", "qualification status contradicts memory-on evidence")
        if (source["on_arm"] is None) != (document["on_arm"] is None):
            raise _error("binding-mismatch", "qualification result changed memory-on evidence presence")
        if document["on_arm"] is not None:
            on = oe._object(document["on_arm"])
            oe._exact(on, required={
                "evaluation_result_digest", "verification_result_digest",
                "m1_qualification_receipt_digest", "adapter",
                "safety_observation_digest", "failure_count",
            })
            for field in (
                "evaluation_result_digest", "verification_result_digest",
                "m1_qualification_receipt_digest", "safety_observation_digest",
            ):
                oe._digest(on[field])
            _adapter(on["adapter"])
            oe._integer(on["failure_count"], minimum=0, maximum=8_000_000)
            source_on = _on_arm(source["on_arm"])
            source_safety = _safety(source_on["safety_observation"])
            expected_on = {
                "evaluation_result_digest": source_on["evaluation_result_digest"],
                "verification_result_digest": source_on["verification_result_digest"],
                "m1_qualification_receipt_digest": source_on["m1_qualification_receipt_digest"],
                "adapter": source_on["adapter"],
                "safety_observation_digest": oe.canonical_digest(source_safety),
                "failure_count": sum(source_safety[field] for field in FAILURE_FIELDS),
            }
            if on != expected_on:
                raise _error("binding-mismatch", "qualification result on arm changed")
            if (status == "conformant-awaiting-human-decision") != (on["failure_count"] == 0):
                raise _error("invalid-structure", "qualification status contradicts failure count")
        gate = oe._object(document["promotion_gate"])
        if gate != {"required": True, "status": "pending", "kind": "independent-human-platform"}:
            raise _error("authority-violation", "qualification promotion gate changed")
        if document["efficacy_claimed"] is not False or document["authority_invariants"] != authority_invariants():
            raise _error("authority-violation", "qualification result overstates authority or efficacy")
        declared = oe._digest(document["qualification_result_digest"])
        if declared != oe.canonical_digest(_body(document, "qualification_result_digest")):
            raise _error("digest-mismatch", "qualification result digest does not match")
    except (MemoryQualificationError, evaluation.CandidateEvaluationError, oe.OperationalEvidenceError) as error:
        if isinstance(error, MemoryQualificationError):
            raise
        raise _translate(error) from error
    return copy.deepcopy(document)


def validate_qualification_result(
    value: Any,
    input_value: Any,
    off_result_value: Any,
    off_verification_value: Any,
    *,
    accepted_v3b_receipts: Any,
    on_result_value: Any | None = None,
    on_verification_value: Any | None = None,
    m1_qualification_receipt_value: Any | None = None,
    accepted_m1_qualification_receipts: Any | None = None,
) -> dict[str, Any]:
    document = _validate_qualification_result_shape(value, input_value)
    expected = build_qualification_result(
        input_value,
        off_result_value,
        off_verification_value,
        accepted_v3b_receipts=accepted_v3b_receipts,
        on_result_value=on_result_value,
        on_verification_value=on_verification_value,
        m1_qualification_receipt_value=m1_qualification_receipt_value,
        accepted_m1_qualification_receipts=accepted_m1_qualification_receipts,
    )
    if document != expected:
        raise _error("binding-mismatch", "qualification result does not match reconstructed caller-owned evidence")
    return document


def load_json(path: Any) -> dict[str, Any]:
    try:
        return oe.load_json(path)
    except oe.OperationalEvidenceError as error:
        raise _translate(error) from error
