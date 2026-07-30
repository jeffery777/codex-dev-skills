from __future__ import annotations

import copy
import importlib
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPTS))
evidence = importlib.import_module("operational_evidence")
lineage = importlib.import_module("improvement_lineage")

REPOSITORY_ID = "github.com.jeffery777.codex-dev-skills"
AUTHORITY = {
    "used_as_authorization": False,
    "used_as_completion_evidence": False,
    "external_write_authorized": False,
    "promotion_authorized": False,
}


def operational_document(
    *,
    kind: str,
    document_id: str,
    run_id: str,
    commit: str,
    producer: str,
    payload: dict,
) -> dict:
    return evidence.seal_document(
        {
            "contract_version": evidence.CONTRACT_VERSION,
            "kind": kind,
            "document_id": document_id,
            "run_id": run_id,
            "objective_id": "issue-124",
            "source_revision": {
                "repository_id": REPOSITORY_ID,
                "commit_sha": commit,
            },
            "observed_at": "2026-07-30T04:00:00Z",
            "producer": {"kind": "agent", "id": producer},
            "payload": payload,
            "authority_invariants": copy.deepcopy(AUTHORITY),
        }
    )


def document_ref(value: dict) -> dict:
    return {
        "document_id": value["document_id"],
        "document_digest": value["document_digest"],
    }


def cross_family_ref(value: dict) -> dict:
    return {
        "contract_version": value["contract_version"],
        "kind": value["kind"],
        "document_id": value["document_id"],
        "document_digest": value["document_digest"],
    }


def evidence_bundle(index: int, *, environment_surface: str = "codex-cli") -> list[dict]:
    run_id = f"run-{index}"
    commit = format(index, "040x")
    producer = f"candidate-runner-{index}"
    artifacts = [
        {
            "artifact_id": f"review-{index}",
            "artifact_kind": "review",
            "locator_kind": "repository-relative-path",
            "locator": f"docs/loops/issue-124/review-{index}.md",
            "content_sha256": format(index + 100, "064x"),
            "media_type": "text/markdown",
        },
        {
            "artifact_id": f"verification-{index}",
            "artifact_kind": "verification",
            "locator_kind": "repository-relative-path",
            "locator": f"docs/loops/issue-124/verification-{index}.md",
            "content_sha256": format(index + 200, "064x"),
            "media_type": "text/markdown",
        },
    ]
    artifact_set = operational_document(
        kind="artifact-reference-set",
        document_id=f"artifacts-{index}",
        run_id=run_id,
        commit=commit,
        producer=producer,
        payload={"artifacts": artifacts},
    )
    environment = operational_document(
        kind="environment-fingerprint",
        document_id=f"environment-{index}",
        run_id=run_id,
        commit=commit,
        producer=producer,
        payload={
            "runtime_surface": environment_surface,
            "os_family": "macos",
            "architecture": "arm64",
            "python": {"major": 3, "minor": 12},
            "execution_mode": "current-session",
            "sandbox_mode": "workspace-write",
            "redaction_applied": True,
            "prohibited_fields_present": False,
        },
    )
    failure = operational_document(
        kind="failure-summary",
        document_id=f"failure-{index}",
        run_id=run_id,
        commit=commit,
        producer=producer,
        payload={
            "iteration_sequence": None,
            "phase": "review",
            "category": "review",
            "code": "review-incomplete",
            "retry": "manual",
            "artifact_ids": [f"review-{index}"],
        },
    )
    run = operational_document(
        kind="run-receipt",
        document_id=f"receipt-{index}",
        run_id=run_id,
        commit=commit,
        producer=producer,
        payload={
            "started_at": "2026-07-30T03:00:00Z",
            "ended_at": "2026-07-30T04:00:00Z",
            "execution_mode": "current-session",
            "outcome": "work-recorded",
            "iteration_summaries": [],
            "environment_fingerprint": document_ref(environment),
            "artifact_reference_set": document_ref(artifact_set),
            "failure_summaries": [document_ref(failure)],
            "verification_observation": "passed",
            "review_observation": "passed",
            "human_gate_observation": "not-required",
        },
    )
    return [run, failure, environment, artifact_set]


def snapshot(bundle: list[dict], *, snapshot_id: str) -> dict:
    run = next(item for item in bundle if item["kind"] == "run-receipt")
    environment = next(
        item for item in bundle if item["kind"] == "environment-fingerprint"
    )
    artifact_set = next(
        item for item in bundle if item["kind"] == "artifact-reference-set"
    )
    result = evidence.validate_set(bundle)
    return {
        "snapshot_id": snapshot_id,
        "run_receipt": cross_family_ref(run),
        "environment_fingerprint": cross_family_ref(environment),
        "artifact_reference_set": cross_family_ref(artifact_set),
        "evidence_set_digest": result["set_digest"],
        "environment_key": evidence.canonical_digest(environment["payload"]),
        "source_revision": copy.deepcopy(run["source_revision"]),
    }


def evaluation_artifacts(bundle: list[dict]) -> list[dict]:
    artifact_set = next(
        item for item in bundle if item["kind"] == "artifact-reference-set"
    )
    return [
        {"snapshot_role": "candidate", "artifact": copy.deepcopy(item)}
        for item in artifact_set["payload"]["artifacts"]
    ]


def failure_references(bundle: list[dict]) -> list[dict]:
    return [
        cross_family_ref(item)
        for item in bundle
        if item["kind"] == "failure-summary"
    ]


def improvement_record(
    index: int,
    *,
    baseline: list[dict],
    candidate: list[dict],
    predecessor: dict | None = None,
) -> dict:
    roles = {
        "proposer": {"actor_kind": "agent", "actor_id": f"proposer-{index}"},
        "evaluator": {"actor_kind": "ci", "actor_id": f"evaluator-{index}"},
        "independent_verifier": {
            "actor_kind": "human",
            "actor_id": f"verifier-{index}",
        },
        "promoter": {"actor_kind": "human", "actor_id": f"promoter-{index}"},
    }
    predecessor_ref = (
        None
        if predecessor is None
        else {
            "record_id": predecessor["record_id"],
            "improvement_id": predecessor["improvement_id"],
            "record_digest": predecessor["record_digest"],
        }
    )
    return lineage.seal_record(
        {
            "contract_version": lineage.LINEAGE_CONTRACT_VERSION,
            "kind": lineage.RECORD_KIND,
            "record_id": f"record-{index}",
            "improvement_id": f"improvement-{index}",
            "objective_id": "issue-124",
            "repository": {"repository_id": REPOSITORY_ID},
            "recorded_at": f"2026-07-30T04:0{index}:00Z",
            "producer": {"kind": "agent", "id": f"proposer-{index}"},
            "payload": {
                "predecessor": predecessor_ref,
                "baseline": snapshot(baseline, snapshot_id=f"baseline-{index}"),
                "candidate": snapshot(candidate, snapshot_id=f"candidate-{index}"),
                "source_failures": failure_references(candidate),
                "evaluation_artifacts": evaluation_artifacts(candidate),
                "role_assignments": roles,
                "candidate_disposition": "verified",
            },
            "authority_invariants": copy.deepcopy(AUTHORITY),
        }
    )


def valid_lineage() -> tuple[list[dict], list[dict]]:
    first, second, third = evidence_bundle(1), evidence_bundle(2), evidence_bundle(3)
    root = improvement_record(1, baseline=first, candidate=second)
    child = improvement_record(
        2,
        baseline=second,
        candidate=third,
        predecessor=root,
    )
    return [child, root], first + second + third


class ImprovementLineageTests(unittest.TestCase):
    def test_valid_lineage_is_deterministic_and_preserves_v2d_a(self):
        records, documents = valid_lineage()
        first = lineage.validate_lineage(records, documents)
        second = lineage.validate_lineage(reversed(records), reversed(documents))
        self.assertEqual(["record-1", "record-2"], first["ordered_record_ids"])
        self.assertEqual(
            first["source_record_set_digest"],
            second["source_record_set_digest"],
        )
        self.assertEqual(AUTHORITY, first["authority_invariants"])
        for bundle_index in (1, 2, 3):
            bundle = evidence_bundle(bundle_index)
            self.assertEqual("valid", evidence.validate_set(bundle)["status"])

    def test_stale_baseline_and_cycle_fail_closed(self):
        records, documents = valid_lineage()
        child, root = records
        stale = copy.deepcopy(child)
        stale["payload"]["baseline"] = snapshot(
            evidence_bundle(1), snapshot_id="stale-baseline"
        )
        stale = lineage.seal_record(stale)
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_lineage([root, stale], documents)
        self.assertEqual("stale-baseline", caught.exception.code)

        cyclic_root = copy.deepcopy(root)
        cyclic_root["payload"]["predecessor"] = {
            "record_id": child["record_id"],
            "improvement_id": child["improvement_id"],
            "record_digest": child["record_digest"],
        }
        cyclic_root = lineage.seal_record(cyclic_root)
        cyclic_child = copy.deepcopy(child)
        cyclic_child["payload"]["predecessor"] = {
            "record_id": cyclic_root["record_id"],
            "improvement_id": cyclic_root["improvement_id"],
            "record_digest": cyclic_root["record_digest"],
        }
        cyclic_child["payload"]["baseline"] = copy.deepcopy(
            cyclic_root["payload"]["candidate"]
        )
        cyclic_child = lineage.seal_record(cyclic_child)
        with self.assertRaises(lineage.ImprovementContractError):
            lineage.validate_lineage([cyclic_root, cyclic_child], documents)

    def test_role_collision_and_authority_escalation_are_rejected(self):
        records, documents = valid_lineage()
        for mutation in ("role", "authority"):
            candidate = copy.deepcopy(records[1])
            if mutation == "role":
                candidate["payload"]["role_assignments"]["promoter"] = copy.deepcopy(
                    candidate["payload"]["role_assignments"]["proposer"]
                )
            else:
                candidate["authority_invariants"]["promotion_authorized"] = True
            candidate = lineage.seal_record(candidate)
            with self.subTest(mutation=mutation):
                with self.assertRaises(lineage.ImprovementContractError):
                    lineage.validate_record(candidate, documents)

    def test_candidate_producer_id_cannot_reappear_under_another_actor_kind(self):
        records, documents = valid_lineage()
        candidate = copy.deepcopy(records[1])
        candidate["payload"]["role_assignments"]["independent_verifier"] = {
            "actor_kind": "human",
            "actor_id": "candidate-runner-2",
        }
        candidate = lineage.seal_record(candidate)
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_record(candidate, documents)
        self.assertEqual("role-conflict", caught.exception.code)

    def test_v2db_rejects_gitlab_token_shaped_identifiers(self):
        records, documents = valid_lineage()
        candidate = copy.deepcopy(records[1])
        marker = "glpat-abcdefghijklmnopqrstuvwxyz"
        candidate["producer"]["id"] = marker
        candidate["payload"]["role_assignments"]["proposer"]["actor_id"] = marker
        candidate = lineage.seal_record(candidate)
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_record(candidate, documents)
        self.assertEqual("privacy-violation", caught.exception.code)

    def test_iterable_counts_are_bounded_before_full_materialization(self):
        records, documents = valid_lineage()
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_lineage(
                (records[0] for _ in range(lineage.MAX_RECORDS + 1)),
                documents,
            )
        self.assertEqual("record-count", caught.exception.code)

        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_lineage(
                records,
                (documents[0] for _ in range(evidence.MAX_SET_DOCUMENTS + 1)),
            )
        self.assertEqual("document-count", caught.exception.code)

    def test_environment_mismatch_is_rejected(self):
        baseline = evidence_bundle(1)
        candidate = evidence_bundle(2, environment_surface="ci")
        record = improvement_record(1, baseline=baseline, candidate=candidate)
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_record(record, baseline + candidate)
        self.assertEqual("environment-mismatch", caught.exception.code)

    def test_duplicate_identity_conflict_is_rejected(self):
        records, documents = valid_lineage()
        duplicate = copy.deepcopy(records[1])
        duplicate["record_id"] = "different-record"
        duplicate = lineage.seal_record(duplicate)
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_lineage([records[1], duplicate], documents)
        self.assertEqual("identity-conflict", caught.exception.code)

    def test_all_dispositions_and_branched_lineage_validate(self):
        first, second, third = evidence_bundle(1), evidence_bundle(2), evidence_bundle(3)
        root = improvement_record(1, baseline=first, candidate=second)
        evidence_documents = first + second + third
        for disposition in ("proposed", "evaluated", "verified", "rejected"):
            candidate = copy.deepcopy(root)
            candidate["payload"]["candidate_disposition"] = disposition
            candidate = lineage.seal_record(candidate)
            with self.subTest(disposition=disposition):
                lineage.validate_record(candidate, evidence_documents)
        branch_a = improvement_record(
            2, baseline=second, candidate=third, predecessor=root
        )
        fourth = evidence_bundle(4)
        branch_b = improvement_record(
            3, baseline=second, candidate=fourth, predecessor=root
        )
        result = lineage.validate_lineage(
            [branch_b, root, branch_a],
            evidence_documents + fourth,
        )
        self.assertEqual(["record-1", "record-2", "record-3"], result["ordered_record_ids"])


class ImprovementProjectionTests(unittest.TestCase):
    def test_human_projection_is_byte_deterministic_and_validates(self):
        records, documents = valid_lineage()
        first = lineage.build_human_projection(records, documents)
        second = lineage.build_human_projection(
            reversed(records), reversed(documents)
        )
        self.assertEqual(first, second)
        self.assertEqual(
            first["manifest"],
            lineage.validate_projection(first["manifest"], records, documents),
        )
        self.assertTrue(first["rendered_markdown"].endswith("\n"))
        self.assertNotIn("promotion_authorized: true", first["rendered_markdown"])

    def test_graph_projection_is_deterministic_and_resolved(self):
        records, documents = valid_lineage()
        first = lineage.build_graph_projection(records, documents)
        second = lineage.build_graph_projection(
            reversed(records), reversed(documents)
        )
        self.assertEqual(first, second)
        node_ids = {item["node_id"] for item in first["payload"]["nodes"]}
        for edge in first["payload"]["edges"]:
            self.assertIn(edge["from_node_id"], node_ids)
            self.assertIn(edge["to_node_id"], node_ids)
        self.assertEqual(
            first,
            lineage.validate_projection(first, records, documents),
        )

    def test_graph_projection_bounds_evidence_iterables(self):
        records, documents = valid_lineage()
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.build_graph_projection(
                records,
                (documents[0] for _ in range(evidence.MAX_SET_DOCUMENTS + 1)),
            )
        self.assertEqual("document-count", caught.exception.code)

    def test_projection_tamper_and_source_mismatch_are_rejected(self):
        records, documents = valid_lineage()
        manifest = lineage.build_graph_projection(records, documents)
        tampered = copy.deepcopy(manifest)
        tampered["payload"]["edges"][0]["edge_type"] = "promoted-by"
        tampered = lineage.seal_projection(tampered)
        with self.assertRaises(lineage.ImprovementContractError) as caught:
            lineage.validate_projection(tampered, records, documents)
        self.assertEqual("projection-mismatch", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
