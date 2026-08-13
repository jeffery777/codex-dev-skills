#!/usr/bin/env python3
"""Deterministic production-backed eval for Memory M0 qualification."""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import memory_qualification as qualification  # noqa: E402
from tests import test_memory_qualification as fixtures  # noqa: E402


def load(relative: str) -> object:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def rejected(callable_value: object) -> str:
    try:
        callable_value()  # type: ignore[operator]
    except qualification.MemoryQualificationError:
        return "rejected"
    return "accepted"


def surface_closed() -> bool:
    forbidden_modules = {"sqlite3", "subprocess", "socket", "requests"}
    forbidden_calls = {"open", "mkdir", "touch", "write_text", "write_bytes", "unlink", "remove"}
    for name in ("memory_qualification.py", "qualificationctl.py"):
        tree = ast.parse((SCRIPT_DIR / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import) and {item.name.split(".", 1)[0] for item in node.names} & forbidden_modules:
                return False
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".", 1)[0] in forbidden_modules:
                return False
            if isinstance(node, ast.Call):
                call = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
                if call in forbidden_calls:
                    return False
    return True


def build(source: dict, result: dict, verified: dict, **extra: object) -> dict:
    return qualification.build_qualification_result(
        source, result, verified,
        accepted_v3b_receipts=fixtures.accepted(result, verified), **extra,
    )


def main() -> int:
    suite = load("evals/memory-qualification/suite.json")
    cases = load("evals/memory-qualification/negative-cases.json")
    expected = {item["name"]: item["expected"] for item in cases}  # type: ignore[index]
    result, verified = fixtures.v3b_pair()
    off = fixtures.qualification_input(result, verified, with_on=False)
    off_result = build(off, result, verified)
    on = fixtures.qualification_input(result, verified, with_on=True)
    if load("evals/memory-qualification/" + suite["positive_fixture"]) != on:
        raise SystemExit("memory qualification positive fixture drifted")
    on_args = dict(
        on_result_value=result, on_verification_value=verified,
        **fixtures.m1_args(on),
    )
    on_result = build(on, result, verified, **on_args)
    safety = copy.deepcopy(on)
    safety["on_arm"]["safety_observation"]["privacy_failures"] = 1
    safety_receipt = fixtures.m1_receipt(safety)
    safety["on_arm"]["m1_qualification_receipt_digest"] = safety_receipt["receipt_digest"]
    safety = qualification.seal_input(safety)
    outcomes: dict[str, str] = {
        "memory-off-complete": off_result["status"],
        "paired-conformant": on_result["status"],
        "safety-failure": build(
            safety, result, verified,
            on_result_value=result, on_verification_value=verified,
            m1_qualification_receipt_value=safety_receipt,
            accepted_m1_qualification_receipts={"qualification_receipt_digests": [safety_receipt["receipt_digest"]]},
        )["status"],
        "backend-surface": "closed" if surface_closed() else "open",
    }
    outcomes["untrusted-m1"] = rejected(lambda: build(
        on, result, verified, on_result_value=result, on_verification_value=verified,
        m1_qualification_receipt_value=fixtures.m1_receipt(on),
        accepted_m1_qualification_receipts={"qualification_receipt_digests": ["0" * 64]},
    ))
    outcomes["untrusted-v3b"] = rejected(lambda: qualification.build_qualification_result(
        on, result, verified, accepted_v3b_receipts={"receipt_digests": ["0" * 64]}, **on_args
    ))
    efficacy = copy.deepcopy(on)
    efficacy["efficacy_claimed"] = True
    efficacy = qualification.seal_input(efficacy)
    outcomes["false-efficacy"] = rejected(lambda: qualification.validate_qualification_input(efficacy))
    changed = copy.deepcopy(result)
    changed["evaluation_result_digest"] = "0" * 64
    outcomes["pair-mismatch"] = rejected(lambda: build(
        on, result, verified, on_result_value=changed, on_verification_value=verified,
        **fixtures.m1_args(on),
    ))
    touched = copy.deepcopy(off)
    touched["off_arm"]["backend_touch_count"] = 1
    touched = qualification.seal_input(touched)
    outcomes["memory-off-backend-touch"] = rejected(lambda: qualification.validate_qualification_input(touched))
    untouched_on = copy.deepcopy(on)
    untouched_on["on_arm"]["safety_observation"]["backend_touch_count"] = 0
    untouched_on = qualification.seal_input(untouched_on)
    outcomes["memory-on-without-backend-touch"] = rejected(
        lambda: qualification.validate_qualification_input(untouched_on)
    )
    changed_verifier = copy.deepcopy(verified)
    changed_verifier["verifier"] = {"role": "different-verifier"}
    changed_verifier = qualification.evaluation.seal_verification_result(changed_verifier)
    verifier_source = copy.deepcopy(on)
    verifier_source["on_arm"]["verification_result_digest"] = changed_verifier["verification_result_digest"]
    verifier_source = qualification.seal_input(verifier_source)
    all_v3b = {"receipt_digests": sorted({
        result["evaluation_result_digest"], verified["verification_result_digest"],
        changed_verifier["verification_result_digest"],
    })}
    outcomes["verifier-mismatch"] = rejected(lambda: qualification.build_qualification_result(
        verifier_source, result, verified, accepted_v3b_receipts=all_v3b,
        on_result_value=result, on_verification_value=changed_verifier,
        **fixtures.m1_args(on),
    ))
    replayed = copy.deepcopy(on)
    replayed["qualification_id"] = "qualification-2"
    replayed = qualification.seal_input(replayed)
    outcomes["m1-receipt-id-replay"] = rejected(lambda: build(
        replayed, result, verified, **on_args,
    ))
    fingerprint_replayed = copy.deepcopy(on)
    fingerprint_replayed["on_arm"]["adapter"] = {
        "adapter_id": "future-adapter-2",
        "adapter_version": "m1-candidate-2",
        "schema_fingerprint": "1" * 64,
        "capability_fingerprint": "2" * 64,
        "platform_fingerprint": "3" * 64,
    }
    fingerprint_replayed = qualification.seal_input(fingerprint_replayed)
    outcomes["m1-receipt-fingerprint-replay"] = rejected(lambda: build(
        fingerprint_replayed, result, verified, **on_args,
    ))
    cli = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "qualificationctl.py"), "promote"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    outcomes["promotion-route"] = "rejected" if cli.returncode == 2 else "accepted"
    correct = sum(outcomes.get(name) == value for name, value in expected.items())
    metrics = {
        "cases": len(outcomes),
        "decision_accuracy": correct / len(expected),
        "pair_binding": 1.0 if outcomes["verifier-mismatch"] == "rejected" else 0.0,
        "determinism": 1.0 if build(on, result, verified, **on_args) == on_result else 0.0,
        "zero_touch_off": 1.0 if off_result["off_arm"]["backend_touch_count"] == 0 else 0.0,
        "safety_conformance": 1.0 if outcomes["safety-failure"] == "not-conformant" else 0.0,
        "privacy_safe_rejection": 1.0 if "traceback" not in cli.stderr.lower() else 0.0,
        "false_efficacy": int(outcomes["false-efficacy"] != "rejected"),
        "false_authority": sum(outcomes[name] != "rejected" for name in (
            "untrusted-m1", "untrusted-v3b", "m1-receipt-id-replay",
            "m1-receipt-fingerprint-replay",
        )),
        "backend_execution": int(outcomes["backend-surface"] != "closed"),
        "promotion": int(outcomes["promotion-route"] != "rejected"),
    }
    if metrics != suite["expected"]:
        raise SystemExit("memory qualification eval thresholds failed")
    print(json.dumps({"status": "passed", "metrics": metrics}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
