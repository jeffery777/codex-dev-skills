#!/usr/bin/env python3
"""Run deterministic production-backed Operational Evidence V0 evaluations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import stat
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import operational_evidence as evidence  # noqa: E402


MAX_SUITE_BYTES = 64 * 1024
MAX_FIXTURE_BYTES = evidence.MAX_DOCUMENT_BYTES
EXPECTED_THRESHOLDS = {
    "decision_correctness_rate": 1.0,
    "false_authority_or_completion_count": 0,
    "evidence_completeness_rate": 1.0,
    "deterministic_behavior_rate": 1.0,
    "privacy_safe_rejection_rate": 1.0,
}
EXPECTED_CASES = {
    "valid-set": (
        "fixtures/positive-valid-set.json",
        "set",
        "valid",
        None,
    ),
    "valid-run-receipt": (
        "fixtures/positive-run-receipt.json",
        "document",
        "valid",
        None,
    ),
    "tampered-digest": (
        "fixtures/negative-tampered-digest.json",
        "document",
        "rejected",
        "digest-mismatch",
    ),
    "duplicate-key": (
        "fixtures/negative-duplicate-key.json",
        "document",
        "rejected",
        "duplicate-key",
    ),
    "unknown-field": (
        "fixtures/negative-unknown-field.json",
        "document",
        "rejected",
        "invalid-structure",
    ),
    "synthetic-secret": (
        "fixtures/negative-synthetic-secret.json",
        "document",
        "rejected",
        "privacy-violation",
    ),
    "synthetic-token": (
        "fixtures/negative-synthetic-token.json",
        "document",
        "rejected",
        "privacy-violation",
    ),
    "private-path": (
        "fixtures/negative-private-path.json",
        "document",
        "rejected",
        "privacy-violation",
    ),
    "raw-log": (
        "fixtures/negative-raw-log.json",
        "document",
        "rejected",
        "privacy-violation",
    ),
    "invalid-reference": (
        "fixtures/negative-invalid-reference.json",
        "set",
        "rejected",
        "relationship-mismatch",
    ),
    "duplicate-document-id": (
        "fixtures/negative-duplicate-document-id.json",
        "set",
        "rejected",
        "relationship-mismatch",
    ),
    "cross-record-mismatch": (
        "fixtures/negative-cross-record-mismatch.json",
        "set",
        "rejected",
        "relationship-mismatch",
    ),
}
EXPECTED_REJECTION_MESSAGES = {
    "tampered-digest": "document digest does not match canonical content",
    "duplicate-key": "document contains a duplicate object key",
    "unknown-field": "object has missing or unknown fields",
    "synthetic-secret": "document contains prohibited sensitive data",
    "synthetic-token": "document contains prohibited sensitive data",
    "private-path": "document contains prohibited sensitive data",
    "raw-log": "document contains prohibited raw log data",
    "invalid-reference": "document reference does not resolve",
    "duplicate-document-id": "document ids must be unique",
    "cross-record-mismatch": "document set identity is inconsistent",
}


class EvalConfigurationError(ValueError):
    """The checked-in eval inventory is incomplete or malformed."""


def _read_bounded_bytes(
    path: pathlib.Path, *, limit: int, label: str
) -> bytes:
    try:
        before = path.lstat()
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            raise EvalConfigurationError(
                f"{label} must be a regular non-symlink file"
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
                raise EvalConfigurationError(
                    f"{label} must be a stable regular non-symlink file"
                )
            chunks = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(descriptor, min(65_536, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
        finally:
            os.close(descriptor)
    except EvalConfigurationError:
        raise
    except OSError as exc:
        raise EvalConfigurationError(f"{label} cannot be read") from exc
    if len(raw) > limit:
        raise EvalConfigurationError(f"{label} exceeds the encoded size bound")
    return raw


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvalConfigurationError("suite contains a duplicate object key")
        result[key] = value
    return result


def _reject_nonfinite(_value: str) -> None:
    raise EvalConfigurationError("suite contains a non-finite number")


def _fixture_path(suite_path: pathlib.Path, relative: str) -> pathlib.Path:
    relative_path = pathlib.PurePosixPath(relative)
    if (
        relative_path.is_absolute()
        or not relative_path.parts
        or "." in relative_path.parts
        or ".." in relative_path.parts
    ):
        raise EvalConfigurationError("fixture path must stay inside the suite directory")
    try:
        suite_root = suite_path.resolve().parent
        candidate = suite_root.joinpath(*relative_path.parts)
        for component in candidate.parents:
            if component == suite_root:
                break
            metadata = component.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise EvalConfigurationError(
                    "fixture path parent must be a real directory"
                )
    except (OSError, RuntimeError) as exc:
        raise EvalConfigurationError(
            "fixture path cannot be resolved safely"
        ) from exc
    return candidate


def load_suite(path: pathlib.Path) -> dict[str, Any]:
    raw = _read_bounded_bytes(path, limit=MAX_SUITE_BYTES, label="suite")
    try:
        suite = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except EvalConfigurationError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise EvalConfigurationError("suite must be readable UTF-8 JSON") from exc
    if not isinstance(suite, dict) or set(suite) != {
        "schema_version",
        "thresholds",
        "cases",
    }:
        raise EvalConfigurationError("suite has an invalid top-level shape")
    if suite["schema_version"] != 1:
        raise EvalConfigurationError("unsupported suite schema version")
    if suite["thresholds"] != EXPECTED_THRESHOLDS:
        raise EvalConfigurationError("suite thresholds must match the fail-closed oracle")
    if not isinstance(suite["cases"], list) or not suite["cases"]:
        raise EvalConfigurationError("suite requires a non-empty case inventory")
    supplied: dict[str, tuple[str, str, str, str | None]] = {}
    expected_fields = {
        "id",
        "fixture",
        "mode",
        "expected_status",
        "expected_code",
    }
    for index, case in enumerate(suite["cases"]):
        if not isinstance(case, dict) or set(case) != expected_fields:
            raise EvalConfigurationError(f"suite case {index} has an invalid shape")
        if not all(
            isinstance(case[field], str) and case[field]
            for field in ("id", "fixture", "mode", "expected_status")
        ) or not (
            case["expected_code"] is None
            or isinstance(case["expected_code"], str)
            and case["expected_code"]
        ):
            raise EvalConfigurationError(f"suite case {index} has invalid fields")
        supplied[case["id"]] = (
            case["fixture"],
            case["mode"],
            case["expected_status"],
            case["expected_code"],
        )
    if len(supplied) != len(suite["cases"]):
        raise EvalConfigurationError("suite case ids must be unique")
    if supplied != EXPECTED_CASES:
        raise EvalConfigurationError("suite cases must match the mandatory inventory")
    return suite


def _run(case: dict[str, Any], raw: bytes) -> dict[str, Any]:
    if case["mode"] == "document":
        return evidence.validate_document(evidence.load_json_bytes(raw))
    if case["mode"] == "set":
        wrapper = evidence.load_json_bytes(raw)
        if set(wrapper) != {"documents"} or not isinstance(
            wrapper["documents"], list
        ):
            raise EvalConfigurationError("set fixture must contain only documents")
        return evidence.validate_set(wrapper["documents"])
    raise EvalConfigurationError("case mode is unsupported")


def evaluate(case: dict[str, Any], suite_path: pathlib.Path) -> dict[str, Any]:
    fixture = _fixture_path(suite_path, case["fixture"])
    raw = _read_bounded_bytes(
        fixture,
        limit=MAX_FIXTURE_BYTES,
        label="fixture",
    )
    fixture_digest = hashlib.sha256(raw).hexdigest()

    observations = []
    for _ in range(2):
        try:
            result = _run(case, raw)
            observations.append(
                {
                    "status": "valid",
                    "code": None,
                    "result_digest": evidence.canonical_digest(result),
                    "authority_invariants": result["authority_invariants"],
                    "message": None,
                }
            )
        except evidence.OperationalEvidenceError as exc:
            observations.append(
                {
                    "status": "rejected",
                    "code": exc.code,
                    "result_digest": None,
                    "authority_invariants": evidence.authority_invariants(),
                    "message": exc.message,
                }
            )

    first, second = observations
    correct = (
        first["status"] == case["expected_status"]
        and first["code"] == case["expected_code"]
    )
    false_authority = (
        first["authority_invariants"] != evidence.authority_invariants()
    )
    deterministic = first == second
    safe_rejection = _is_safe_rejection(
        case["id"],
        first["status"],
        first["message"],
    )
    evidence_complete = (
        len(fixture_digest) == 64
        and case["fixture"].startswith("fixtures/")
        and first["status"] in {"valid", "rejected"}
        and first["authority_invariants"] == evidence.authority_invariants()
    )
    return {
        "id": case["id"],
        "actual_status": first["status"],
        "expected_status": case["expected_status"],
        "actual_code": first["code"],
        "expected_code": case["expected_code"],
        "fixture_sha256": fixture_digest,
        "correct": correct,
        "false_authority_or_completion": false_authority,
        "evidence_complete": evidence_complete,
        "deterministic": deterministic,
        "privacy_safe_rejection": safe_rejection,
    }


def _is_safe_rejection(
    case_id: str,
    status: str,
    message: str | None,
) -> bool:
    if status == "valid":
        return True
    expected = EXPECTED_REJECTION_MESSAGES.get(case_id)
    return (
        expected is not None
        and message == expected
        and message.isascii()
        and len(message) <= 96
    )


def evaluate_suite(
    suite_path: pathlib.Path | None = None,
    *,
    selected_id: str | None = None,
) -> dict[str, Any]:
    suite_path = suite_path or ROOT / "evals" / "operational-evidence" / "suite.json"
    suite = load_suite(suite_path)
    cases = suite["cases"]
    if selected_id is not None:
        cases = [case for case in cases if case["id"] == selected_id]
        if not cases:
            raise EvalConfigurationError("selected case is not in the suite")
    results = [evaluate(case, suite_path) for case in cases]
    total = len(results)
    metrics = {
        "total_cases": total,
        "decision_correctness_rate": sum(item["correct"] for item in results)
        / total,
        "false_authority_or_completion_count": sum(
            item["false_authority_or_completion"] for item in results
        ),
        "evidence_completeness_rate": sum(
            item["evidence_complete"] for item in results
        )
        / total,
        "deterministic_behavior_rate": sum(
            item["deterministic"] for item in results
        )
        / total,
        "privacy_safe_rejection_rate": sum(
            item["privacy_safe_rejection"] for item in results
        )
        / total,
    }
    thresholds = EXPECTED_THRESHOLDS if selected_id is None else {
        key: value
        for key, value in EXPECTED_THRESHOLDS.items()
        if key != "false_authority_or_completion_count"
    }
    failures = {
        key: {"expected": expected, "actual": metrics[key]}
        for key, expected in thresholds.items()
        if metrics[key] != expected
    }
    if selected_id is not None and metrics["false_authority_or_completion_count"] != 0:
        failures["false_authority_or_completion_count"] = {
            "expected": 0,
            "actual": metrics["false_authority_or_completion_count"],
        }
    return {
        "schema_version": 1,
        "status": "passed" if not failures else "failed",
        "metrics": metrics,
        "threshold_failures": failures,
        "cases": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suite",
        type=pathlib.Path,
        default=ROOT / "evals" / "operational-evidence" / "suite.json",
    )
    parser.add_argument("--case")
    args = parser.parse_args(argv)
    try:
        result = evaluate_suite(args.suite, selected_id=args.case)
    except EvalConfigurationError as exc:
        print(
            json.dumps(
                {"schema_version": 1, "status": "error", "error": str(exc)},
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
