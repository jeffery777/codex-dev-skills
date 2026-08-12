#!/usr/bin/env python3
"""Deterministic offline eval for the V3-B candidate-evaluation contract."""

from __future__ import annotations

import ast
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

import candidate_evaluation as evaluation  # noqa: E402
import memory_contract as memory  # noqa: E402
from tests import test_candidate_evaluation as fixtures  # noqa: E402
from tests import test_memory_contract as memory_fixtures  # noqa: E402


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def context_inputs(value: dict) -> tuple[dict, dict, dict]:
    handshake = value["handshake"]
    conformance = {
        handshake["adapter"]["adapter_id"]: {
            "receipt_digest": "c" * 64,
            "adapter_fingerprint": memory.canonical_digest(
                {"adapter": handshake["adapter"], "capabilities": handshake["capabilities"]}
            ),
        }
    }
    sources = {
        ref["locator"]: ref["digest"]
        for record in value["response"]["records"]
        for ref in record.get("provenance", {}).get("source_refs", [])
        if ref.get("kind") == "repository-artifact"
    }
    return value, conformance, sources


def production_action_surface_is_closed() -> bool:
    """Reject production source that introduces an action or mutation surface."""
    forbidden_modules = {
        "asyncio", "ftplib", "http", "importlib", "multiprocessing", "os", "requests",
        "shutil", "socket", "subprocess", "urllib",
    }
    forbidden_calls = {
        "__import__", "compile", "eval", "exec", "import_module", "open",
        "chmod", "chown", "connect", "fork", "forkpty", "link", "mkdir",
        "mkfifo", "mknod", "posix_spawn", "remove", "rename", "replace",
        "rmdir", "spawn", "symlink", "system", "touch", "truncate", "unlink",
        "utime", "write_bytes", "write_text", "symlink_to", "hardlink_to",
    }
    for path in (
        SCRIPT_DIR / "candidate_evaluation.py",
        SCRIPT_DIR / "evaluationctl.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name.split(".", 1)[0] in forbidden_modules for alias in node.names):
                    return False
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".", 1)[0] in forbidden_modules:
                    return False
            elif isinstance(node, ast.Call):
                name = (
                    node.func.id if isinstance(node.func, ast.Name)
                    else node.func.attr if isinstance(node.func, ast.Attribute)
                    else ""
                )
                if name in forbidden_calls:
                    return False
    return True


def main() -> int:
    suite = load("evals/candidate-evaluation/suite.json")
    cases = load("evals/candidate-evaluation/negative-cases.json")
    expected_cases = {item["name"]: item["expected"] for item in cases}
    records, evidence, proposal_set, selected = fixtures.source_bundle()
    base_input = fixtures.evaluation_input(selected)
    fixture_input = load(
        "evals/candidate-evaluation/" + suite["positive_fixture"]
    )
    if fixture_input != base_input:
        raise SystemExit("candidate evaluation positive fixture drifted")
    base_result = evaluation.build_evaluation_result(
        base_input, proposal_set, records, evidence
    )
    outcomes: dict[str, str] = {
        "baseline-pass-candidate-pass": base_result["comparison"]["status"],
        "memory-off-default": base_result["context"]["mode"],
    }

    regressed = fixtures.evaluation_input(
        selected,
        candidate=fixtures.observation(selected, "candidate", resources=121),
    )
    outcomes["candidate-regression"] = evaluation.build_evaluation_result(
        regressed, proposal_set, records, evidence
    )["comparison"]["status"]
    duration_regressed = fixtures.evaluation_input(
        selected,
        candidate=fixtures.observation(selected, "candidate", duration=121),
    )
    outcomes["duration-regression"] = evaluation.build_evaluation_result(
        duration_regressed, proposal_set, records, evidence
    )["comparison"]["status"]
    invalid = fixtures.evaluation_input(
        selected,
        baseline=fixtures.observation(selected, "baseline", outcome="failed"),
    )
    outcomes["baseline-invalid"] = evaluation.build_evaluation_result(
        invalid, proposal_set, records, evidence
    )["comparison"]["status"]

    mismatched = copy.deepcopy(base_result)
    mismatched["comparison"]["status"] = "regressed"
    mismatched = evaluation.seal_evaluation_result(mismatched)
    outcomes["verification-mismatch"] = evaluation.verify_evaluation_result(
        mismatched, base_input, proposal_set, records, evidence
    )["status"]

    env_input = fixtures.evaluation_input(
        selected,
        candidate=fixtures.observation(
            selected,
            "candidate",
            environment_fingerprint=fixtures.environment(mode="current-session"),
        ),
    )
    outcomes["environment-mismatch"] = evaluation.build_evaluation_result(
        env_input, proposal_set, records, evidence
    )["comparison"]["status"]

    for name, source_set, source_evidence in (
        ("missing-lineage", proposal_set, evidence[:-1]),
        (
            "tampered-lineage",
            {**proposal_set, "proposal_set_digest": "0" * 64},
            evidence,
        ),
    ):
        try:
            evaluation.build_evaluation_result(
                base_input, source_set, records, source_evidence
            )
        except evaluation.CandidateEvaluationError:
            outcomes[name] = "rejected"
        else:
            outcomes[name] = "accepted"

    replay = evaluation.build_evaluation_result(
        base_input, proposal_set, reversed(records), reversed(evidence)
    )
    outcomes["deterministic-replay"] = "equivalent" if replay == base_result else "different"

    raised = copy.deepcopy(base_input)
    raised["authority_invariants"]["used_as_completion_evidence"] = True
    raised = evaluation.seal_evaluation_input(raised)
    try:
        evaluation.build_evaluation_result(raised, proposal_set, records, evidence)
    except evaluation.CandidateEvaluationError:
        outcomes["false-authority"] = "rejected"
    else:
        outcomes["false-authority"] = "accepted"

    valid_context = memory_fixtures.retrieval_input()
    decision, conformance, sources = context_inputs(valid_context)
    context_result = evaluation.build_evaluation_result(
        base_input, proposal_set, records, evidence,
        memory_decision_input=decision,
        trusted_conformance_receipts=conformance,
        trusted_source_digests=sources,
    )
    outcomes["valid-synthetic-context"] = context_result["context"]["mode"]

    context_cases: dict[str, tuple[Any, Any, Any]] = {
        "partial-context": (decision, conformance, None),
    }
    stale = copy.deepcopy(valid_context)
    stale["current"]["source_revision_relations"]["record-1"] = "ancestor"
    context_cases["stale-context"] = context_inputs(stale)
    context_cases["untrusted-context"] = (decision, {}, sources)
    sensitive = copy.deepcopy(valid_context)
    sensitive["response"]["records"][0]["content"] = "password=synthetic-secret"
    memory_fixtures.resign_record(sensitive["response"]["records"][0])
    memory_fixtures.resign_response(sensitive["response"])
    context_cases["sensitive-context"] = context_inputs(sensitive)
    conflicting = copy.deepcopy(valid_context)
    conflicting["current"]["conflicting_records"] = ["record-1"]
    context_cases["conflicting-context"] = context_inputs(conflicting)
    unsupported = copy.deepcopy(valid_context)
    unsupported["handshake"]["capabilities"]["read_query"]["state"] = "unsupported"
    context_cases["unsupported-context"] = context_inputs(unsupported)
    context_results: dict[str, dict] = {}
    for name, values in context_cases.items():
        result = evaluation.build_evaluation_result(
            base_input, proposal_set, records, evidence,
            memory_decision_input=values[0],
            trusted_conformance_receipts=values[1],
            trusted_source_digests=values[2],
        )
        context_results[name] = result
        outcomes[name] = result["context"]["mode"]

    for outcome in ("timeout", "resource-bound", "interrupted", "uncertain"):
        uncertain_input = fixtures.evaluation_input(
            selected,
            candidate=fixtures.observation(
                selected, "candidate", outcome=outcome
            ),
        )
        outcomes[outcome] = evaluation.build_evaluation_result(
            uncertain_input, proposal_set, records, evidence
        )["comparison"]["status"]

    verification = evaluation.verify_evaluation_result(
        base_result, base_input, proposal_set, records, evidence
    )
    packet = evaluation.build_promotion_packet(
        base_result, verification, base_input, proposal_set, records, evidence
    )
    outcomes["packet-cannot-promote"] = (
        "bounded"
        if packet["packet_only_invariants"] == evaluation.packet_only_invariants()
        and packet["promotion_gate"]["status"] == "pending"
        else "unbounded"
    )

    with tempfile.TemporaryDirectory() as temporary:
        directory = pathlib.Path(temporary)

        def write(name: str, value: dict) -> pathlib.Path:
            path = directory / name
            path.write_text(json.dumps(value), encoding="utf-8")
            return path

        proposal_path = write("proposal-set.json", proposal_set)
        input_path = write("evaluation-input.json", base_input)
        record_paths = [
            write(f"record-{index}.json", value)
            for index, value in enumerate(records)
        ]
        evidence_paths = [
            write(f"evidence-{index}.json", value)
            for index, value in enumerate(evidence)
        ]
        arguments = [
            "evaluate", str(input_path), "--proposal-set", str(proposal_path),
            *(item for path in record_paths for item in ("--record", str(path))),
            *(item for path in evidence_paths for item in ("--evidence", str(path))),
        ]
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "evaluationctl.py"),
                *arguments,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        expected_stdout = json.dumps(
            base_result, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ) + "\n"
        outcomes["manual-ci-equivalence"] = (
            "equivalent"
            if completed.returncode == 0 and not completed.stderr and completed.stdout == expected_stdout
            else "different"
        )

        action_surface_closed = production_action_surface_is_closed()
        action_rejections = 0
        for route in (
            "apply", "branch", "commit", "push", "draft-pr", "approve",
            "activate", "promote", "merge", "release", "deploy",
        ):
            completed = subprocess.run(
                [sys.executable, str(SCRIPT_DIR / "evaluationctl.py"), route],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            try:
                rejection = json.loads(completed.stderr)
            except json.JSONDecodeError:
                rejection = {}
            if (
                completed.returncode == 2
                and not completed.stdout
                and rejection.get("status") == "rejected"
                and rejection.get("code") == "wrong-route"
            ):
                action_rejections += 1
        outcomes["action-routes"] = (
            "rejected"
            if action_rejections == 11 and action_surface_closed
            else "accepted"
        )

    context_documents = (context_result, *context_results.values())
    all_documents = (base_result, verification, packet, *context_documents)
    completion_bounded = all(
        item["authority_invariants"]["used_as_completion_evidence"] is False
        for item in all_documents
    )
    outcomes["completion-boundary"] = (
        "bounded" if completion_bounded else "unbounded"
    )

    accurate = outcomes == expected_cases
    context_semantics_preserved = all(
        result["policy"] == base_result["policy"]
        and result["comparison"] == base_result["comparison"]
        and result["authority_invariants"] == evaluation.authority_invariants()
        for result in context_documents
    )
    sensitive_text_absent = "synthetic-secret" not in evaluation.oe.canonical_json(
        context_results["sensitive-context"]
    )
    false_authority = sum(
        item["authority_invariants"] != evaluation.authority_invariants()
        for item in all_documents
    )
    false_completion = 0 if completion_bounded else 1
    external_write = 0 if (
        outcomes["action-routes"] == "rejected"
        and packet["packet_only_invariants"]["external_write_performed"] is False
        and all(
            item["authority_invariants"]["external_write_authorized"] is False
            for item in all_documents
        )
    ) else 1
    promotion = 0 if (
        outcomes["action-routes"] == "rejected"
        and packet["packet_only_invariants"]["promotion_performed"] is False
        and packet["promotion_gate"]["required"] is True
        and packet["promotion_gate"]["status"] == "pending"
    ) else 1
    metrics = {
        "cases": len(outcomes),
        "decision_accuracy": 1.0 if accurate else 0.0,
        "evidence_completeness": 1.0 if set(outcomes) == set(expected_cases) else 0.0,
        "environment_handling": 1.0 if outcomes["environment-mismatch"] == "environment-mismatch" else 0.0,
        "verification_replay": 1.0 if outcomes["verification-mismatch"] == "failed" else 0.0,
        "determinism": 1.0 if outcomes["deterministic-replay"] == "equivalent" else 0.0,
        "context_fallback": 1.0 if all(outcomes[name] == "memory-off" for name in context_cases) and context_semantics_preserved else 0.0,
        "lineage_rejection": 1.0 if outcomes["missing-lineage"] == outcomes["tampered-lineage"] == "rejected" else 0.0,
        "privacy_safe_rejection": 1.0 if outcomes["sensitive-context"] == "memory-off" and sensitive_text_absent else 0.0,
        "resource_handling": 1.0 if outcomes["candidate-regression"] == outcomes["duration-regression"] == "regressed" and all(outcomes[name] == "execution-uncertain" for name in ("timeout", "resource-bound", "interrupted", "uncertain")) else 0.0,
        "manual_ci_equivalence": 1.0 if outcomes["manual-ci-equivalence"] == "equivalent" else 0.0,
        "packet_boundary": 1.0 if outcomes["packet-cannot-promote"] == "bounded" else 0.0,
        "false_completion": false_completion,
        "false_authority": false_authority if outcomes["false-authority"] == "rejected" else false_authority + 1,
        "unauthorized_action": 0 if outcomes["action-routes"] == "rejected" else 1,
        "external_write": external_write,
        "promotion": promotion,
    }
    output = {
        "contract_version": suite["contract_version"],
        "status": "passed" if metrics == suite["expected"] else "failed",
        "outcomes": outcomes,
        "metrics": metrics,
        "expected": suite["expected"],
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if output["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
