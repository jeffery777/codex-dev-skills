from __future__ import annotations

import os
import pathlib
import hashlib
import json
import copy
import datetime as dt
import shutil
import stat
import sys
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "loop-engineering" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import loop_yaml
import loopctl
import loop_core
import git_source


def valid_v1() -> dict:
    return {
        "ledger": {
            "schema_version": 1,
            "objective_id": "issue-81",
            "objective": "deliver loop core",
            "source_revision": {
                "branch": "codex/issue-81",
                "head_sha": "abc123",
                "updated_at": "2026-07-10T00:00:00Z",
                "ledger_sha256": "legacy-self-hash",
            },
        },
        "tasks": [
            {
                "id": "T1",
                "status": "ready",
                "dependencies": [],
                "evidence": {
                    "verification": {"status": "not_run"},
                    "review": {"status": "not_required"},
                },
            }
        ],
    }


def valid_v2() -> dict:
    return {
        "ledger": {
            "schema_version": 2,
            "objective_id": "issue-81",
            "objective": "integration",
            "loop_spec": "loop-spec.md",
            "task_manifest": "task-manifest.yaml",
            "source_revision": {
                "branch": "branch",
                "head_sha": "abc123",
                "spec_sha256": "replace",
                "task_manifest_sha256": "replace",
                "previous_ledger_sha256": "",
                "updated_at": "2026-07-10T00:00:00Z",
            },
            "state_revision": {"sequence": 0, "last_event_hash": ""},
        },
        "tasks": [{"id": "T1", "status": "ready", "evidence": {}}],
        "claims": [],
        "events": [],
        "human_gates": [],
    }


def write_contract(root: pathlib.Path, document: dict) -> pathlib.Path:
    spec_path = root / "loop-spec.md"
    spec_path.write_text("# Integration loop spec\n", encoding="utf-8")
    manifest_path = root / "task-manifest.yaml"
    manifest = {
        "project": {"schema_version": 2, "name": "integration", "objective_id": "issue-81"},
        "tasks": [
            {
                "id": "T1",
                "initial_status": "ready",
                "dependencies": [],
                "scope": {"in": ["x"], "out": []},
                "dod": ["done"],
                "verification": ["test"],
            }
        ],
    }
    manifest_path.write_text(loop_yaml.dump_yaml(manifest), encoding="utf-8")
    source = document["ledger"]["source_revision"]
    source["spec_sha256"] = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    source["task_manifest_sha256"] = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Loop Test"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "loop@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "add", spec_path.name, manifest_path.name], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "test contract"], check=True)
    source["head_sha"] = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    source["branch"] = subprocess.run(
        ["git", "-C", str(root), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return manifest_path


def materialized_claim_contract(
    root: pathlib.Path,
    *,
    lease_expires_at: str = "2026-07-10T00:10:00Z",
) -> tuple[dict, pathlib.Path, dict, dict]:
    document = valid_v2()
    manifest_path = write_contract(root, document)
    definitions = loop_yaml.manifest_definitions(
        loop_yaml.load_yaml(manifest_path),
        expected_objective_id=document["ledger"]["objective_id"],
    )
    state = loop_yaml.state_from_ledger(document, definitions)
    claim = {
        "task_id": "T1",
        "status": "active",
        "owner": {"type": "subagent", "id": "worker-1"},
        "fencing_token": {"generation": 1, "nonce": "precommit"},
        "expected_state_revision": 0,
        "source_revision": copy.deepcopy(state["source_revision"]),
        "claimed_at": "2026-07-10T00:00:00Z",
        "lease_expires_at": lease_expires_at,
    }
    acquired = {
        "sequence": 1,
        "event_id": "claim-before-precommit",
        "occurred_at": "2026-07-10T00:00:00Z",
        "actor": "worker-1",
        "type": "claim_acquired",
        "task_id": "T1",
        "idempotency_key": "claim-before-precommit",
        "expected_state_revision": 0,
        "previous_event_hash": "",
        "payload": {"claim": claim},
    }
    acquired["event_hash"] = loop_core.calculate_event_hash(acquired)
    state, _ = loop_core.replay_event(state, acquired)
    return loop_yaml.update_ledger_view(document, state), manifest_path, claim, acquired


def init_git_repository(root: pathlib.Path) -> dict[str, str]:
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Loop Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "loop@example.invalid"],
        check=True,
    )
    (root / "tracked.txt").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "-m", "initial"],
        check=True,
    )
    return {
        "branch": subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "head_sha": subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
    }


def completed_v2_contract(
    root: pathlib.Path,
) -> tuple[pathlib.Path, pathlib.Path, str]:
    """Write a semantically valid terminal ledger anchored to the first commit."""

    document = valid_v2()
    manifest_path = write_contract(root, document)
    definitions = loop_yaml.manifest_definitions(
        loop_yaml.load_yaml(manifest_path),
        expected_objective_id=document["ledger"]["objective_id"],
    )
    state = loop_yaml.state_from_ledger(document, definitions)
    cancelled = {
        "sequence": 1,
        "event_id": "cancel-task",
        "actor": "test",
        "occurred_at": "2026-07-10T00:01:00Z",
        "expected_state_revision": 0,
        "previous_event_hash": "",
        "idempotency_key": "cancel-task",
        "type": "task_transition",
        "task_id": "T1",
        "payload": {"target_status": "cancelled", "evidence": {}},
    }
    cancelled["event_hash"] = loop_core.calculate_event_hash(cancelled)
    state, _ = loop_core.apply_event(state, cancelled)

    completed = {
        "sequence": 2,
        "event_id": "complete-objective",
        "actor": "maintainer",
        "occurred_at": "2026-07-10T00:02:00Z",
        "expected_state_revision": 1,
        "previous_event_hash": state["last_event_hash"],
        "idempotency_key": "complete-objective",
        "type": "objective_completed",
        "task_id": "",
        "payload": {
            "verification": "passed",
            "review": "not_required",
            "human_gate": "not_required",
            "evidence": {"artifact": "completion-receipt"},
        },
    }
    authorization = {
        "action": "objective_completion",
        "principal": {"type": "user", "id": "maintainer"},
        "objective_id": state["objective_id"],
        "artifact": "completion-receipt",
        "source_revision_sha256": loop_core.source_revision_digest(
            state["source_revision"]
        ),
    }
    completed["payload"]["authorization"] = authorization
    authorization["protected_payload_sha256"] = loop_core.protected_payload_digest(
        completed["payload"]
    )
    completed["event_hash"] = loop_core.calculate_event_hash(completed)
    state, _ = loop_core.apply_event(
        state,
        completed,
        trusted_authority={
            "action": "objective_completion",
            "authorization_receipt_sha256": loop_core.digest(authorization),
        },
    )
    document = loop_yaml.update_ledger_view(document, state)
    ledger_path = root / "loop-state-ledger.yaml"
    ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
    return ledger_path, manifest_path, document["ledger"]["source_revision"]["head_sha"]


def agent_route_document(source_revision: dict[str, str]) -> dict:
    return {
        "agent_route": {
            "contract_version": 1,
            "task": {
                "id": "P1",
                "factors": {
                    "ambiguity": "moderate",
                    "reasoning_depth": "balanced",
                    "code_context_volume": "medium",
                    "security_data_migration_public_contract_risk": "routine",
                    "write_blast_radius": "bounded",
                    "latency_sensitivity": "medium",
                    "cost_token_sensitivity": "medium",
                    "independence_parallelizability": "independent",
                    "verification_burden": "medium",
                },
            },
            "profile_preflight": {
                "profile_dir": str(ROOT / "agent-profiles"),
                "registry": str(
                    ROOT
                    / "skills"
                    / "loop-engineering"
                    / "references"
                    / "agent-profile-registry.json"
                ),
                "role": "loop_v2a_balanced_worker",
                "agent_roots": [],
                "destination_root": str(ROOT / "agent-profiles"),
            },
            "assignment": {
                "scope": ["skills/loop-engineering/scripts/agent_routing.py"],
                "ownership": {"owner": "worker-p1", "disjoint": True},
                "source_revision": source_revision,
                "authority_contract": {
                    "external_write_authorized": False,
                    "human_gates": ["merge"],
                    "completion_criteria": ["tests"],
                },
            },
        }
    }


def agent_integration_document(
    receipt: dict,
    *,
    artifact: str,
    artifact_digest: str,
    verification_artifact: str,
    verification_digest: str,
) -> dict:
    return {
        "agent_integration": {
            "contract_version": 1,
            "route_receipt": receipt,
            "worker_receipt": {
                "route_receipt_id": receipt["route_receipt_id"],
                "task_id": receipt["task_id"],
                "assigned_scope_sha256": receipt["assigned_scope_sha256"],
                "source_revision_sha256": receipt["source_revision_sha256"],
                "status": "complete",
                "output_artifacts": [artifact],
                "artifact_digests": {artifact: artifact_digest},
                "conflicts": [],
            },
            "disposition": {
                "route_receipt_id": receipt["route_receipt_id"],
                "disposition": "accepted",
                "verification": {
                    "status": "passed",
                    "artifacts": [verification_artifact],
                    "artifact_digests": {
                        verification_artifact: verification_digest
                    },
                },
            },
        }
    }


class StructuredYamlTests(unittest.TestCase):
    def test_external_memory_ledger_metadata_is_fail_closed(self):
        document = valid_v2()
        document["external_memory"] = {
            "contract_version": "loop-memory/v1",
            "mode": "disabled",
            "backend_status": "disabled",
            "adapter": None,
            "receipt_digests": [],
            "authority": "advisory-only",
            "used_as_authorization": False,
            "used_as_completion_evidence": False,
            "notes": "Memory remains advisory-only.",
        }
        self.assertEqual([], loop_yaml.validate_ledger(document))
        invalid_values = {
            "contract_version": "bogus",
            "backend_status": {},
            "authority": "authoritative-completion",
            "used_as_authorization": True,
            "used_as_completion_evidence": True,
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field):
                invalid = copy.deepcopy(document)
                invalid["external_memory"][field] = value
                self.assertTrue(loop_yaml.validate_ledger(invalid))
        unknown = copy.deepcopy(document)
        unknown["external_memory"]["unknown_field"] = True
        self.assertTrue(loop_yaml.validate_ledger(unknown))
        invalid_digest = copy.deepcopy(document)
        invalid_digest["external_memory"].update({
            "mode": "advisory-cache",
            "backend_status": "used",
            "adapter": "adapter-1",
            "receipt_digests": ["not-a-digest"],
        })
        self.assertTrue(loop_yaml.validate_ledger(invalid_digest))
        contradictory = copy.deepcopy(document)
        contradictory["external_memory"].update({
            "backend_status": "used",
            "adapter": "adapter-1",
            "receipt_digests": ["a" * 64],
        })
        self.assertTrue(loop_yaml.validate_ledger(contradictory))
        unavailable = copy.deepcopy(document)
        unavailable["external_memory"].update({
            "mode": "coordination",
            "backend_status": "unavailable",
            "adapter": "adapter-1",
        })
        self.assertEqual([], loop_yaml.validate_ledger(unavailable))
        for status in ("used", "degraded"):
            with self.subTest(status=status):
                active = copy.deepcopy(document)
                active["external_memory"].update({
                    "mode": "advisory-cache",
                    "backend_status": status,
                    "adapter": "adapter-1",
                    "receipt_digests": ["a" * 64],
                })
                self.assertEqual([], loop_yaml.validate_ledger(active))
        for adapter in (None, "", "   ", "../adapter", "https://example.com/adapter"):
            with self.subTest(adapter=adapter):
                invalid_adapter = copy.deepcopy(document)
                invalid_adapter["external_memory"].update({
                    "mode": "coordination",
                    "backend_status": "used",
                    "adapter": adapter,
                    "receipt_digests": ["a" * 64],
                })
                self.assertTrue(loop_yaml.validate_ledger(invalid_adapter))
        duplicate_receipt = copy.deepcopy(document)
        duplicate_receipt["external_memory"].update({
            "mode": "coordination",
            "backend_status": "used",
            "adapter": "adapter-1",
            "receipt_digests": ["a" * 64, "a" * 64],
        })
        self.assertTrue(loop_yaml.validate_ledger(duplicate_receipt))

    def test_malformed_yaml_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "ledger.yaml"
            path.write_text("ledger: [unterminated", encoding="utf-8")
            with self.assertRaises(loop_yaml.LedgerValidationError):
                loop_yaml.load_yaml(path)

    def test_duplicate_yaml_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "ledger.yaml"
            path.write_text("ledger:\n  schema_version: 1\n  schema_version: 2\n", encoding="utf-8")
            with self.assertRaises(loop_yaml.LedgerValidationError):
                loop_yaml.load_yaml(path)

    def test_failed_verification_cannot_bleed_into_passed_review(self):
        document = valid_v1()
        task = document["tasks"][0]
        task["status"] = "done"
        task["evidence"]["verification"]["status"] = "failed"
        task["evidence"]["review"]["status"] = "passed"
        errors = loop_yaml.validate_ledger(document)
        self.assertTrue(any("passed verification" in error for error in errors))

    def test_unknown_dependency_is_rejected(self):
        document = valid_v1()
        document["tasks"][0]["dependencies"] = ["missing"]
        self.assertTrue(any("unknown dependency" in error for error in loop_yaml.validate_ledger(document)))

    def test_dependency_cycle_is_rejected(self):
        document = valid_v1()
        document["tasks"].append(
            {"id": "T2", "status": "ready", "dependencies": ["T1"], "evidence": {}}
        )
        document["tasks"][0]["dependencies"] = ["T2"]
        self.assertTrue(any("cycle" in error for error in loop_yaml.validate_ledger(document)))

    def test_valid_v1_passes(self):
        self.assertEqual([], loop_yaml.validate_ledger(valid_v1()))

    def test_ledger_schema_version_rejects_boolean(self):
        document = valid_v1()
        document["ledger"]["schema_version"] = True
        self.assertTrue(
            any("schema_version" in error for error in loop_yaml.validate_ledger(document))
        )

    def test_v2_in_progress_requires_active_claim(self):
        document = valid_v2()
        document["tasks"][0]["status"] = "in_progress"
        self.assertTrue(any("active fenced claim" in item for item in loop_yaml.validate_ledger(document)))

    def test_v2_accepted_requires_acceptance_artifact(self):
        document = valid_v2()
        document["tasks"][0].update(
            {
                "status": "accepted",
                "evidence": {
                    "verification": {"status": "passed"},
                    "review": {"status": "passed"},
                    "acceptance": {"status": "satisfied", "artifact": ""},
                },
            }
        )
        self.assertTrue(any("acceptance evidence" in item for item in loop_yaml.validate_ledger(document)))

    def test_event_expected_revision_rejects_boolean(self):
        document = valid_v2()
        event = {
            "sequence": 1,
            "event_id": "event-1",
            "occurred_at": "2026-07-10T00:00:00Z",
            "actor": "test",
            "type": "gate_updated",
            "task_id": "",
            "idempotency_key": "event-1",
            "expected_state_revision": False,
            "previous_event_hash": "",
            "payload": {"gate": "publish", "status": "pending"},
        }
        event["event_hash"] = loop_core.calculate_event_hash(event)
        document["events"] = [event]
        document["human_gates"] = [copy.deepcopy(event["payload"])]
        document["ledger"]["state_revision"] = {
            "sequence": 1,
            "last_event_hash": event["event_hash"],
        }
        errors = loop_yaml.validate_ledger(document)
        self.assertTrue(any("non-negative integer" in error for error in errors))

    def test_manifest_rejects_unreplayable_initial_blocked_state(self):
        manifest = {
            "project": {
                "schema_version": 2,
                "name": "integration",
                "objective_id": "issue-81",
            },
            "tasks": [
                {
                    "id": "T1",
                    "initial_status": "blocked",
                    "dependencies": [],
                    "scope": {"in": ["x"]},
                    "dod": ["done"],
                    "verification": ["test"],
                }
            ]
        }
        with self.assertRaises(loop_yaml.LedgerValidationError):
            loop_yaml.manifest_definitions(manifest)

    def test_manifest_dependency_validation_handles_deep_acyclic_graph(self):
        tasks = []
        for index in range(1500):
            tasks.append(
                {
                    "id": f"T{index}",
                    "initial_status": "planned",
                    "dependencies": [f"T{index + 1}"] if index < 1499 else [],
                    "scope": {"in": ["x"]},
                    "dod": ["done"],
                    "verification": ["test"],
                }
            )

        definitions = loop_yaml.manifest_definitions(
            {
                "project": {
                    "schema_version": 2,
                    "name": "integration",
                    "objective_id": "issue-81",
                },
                "tasks": tasks,
            }
        )

        self.assertEqual(1500, len(definitions))

    def test_manifest_enforces_schema_objective_and_required_gates(self):
        manifest = {
            "project": {
                "schema_version": 2,
                "name": "integration",
                "objective_id": "issue-81",
            },
            "tasks": [
                {
                    "id": "T1",
                    "initial_status": "ready",
                    "dependencies": [],
                    "scope": {"in": ["x"]},
                    "dod": ["done"],
                    "verification": ["test"],
                    "review": {"required": True, "mode": "code-review-deep"},
                    "human_gate": {"required": True, "gate": "publish"},
                }
            ],
        }
        definitions = loop_yaml.manifest_definitions(
            manifest, expected_objective_id="issue-81"
        )
        self.assertTrue(definitions["T1"]["review_required"])
        self.assertEqual("code-review-deep", definitions["T1"]["review_mode"])
        self.assertTrue(definitions["T1"]["human_gate_required"])
        self.assertEqual("publish", definitions["T1"]["human_gate_name"])

        for value in (True, 1, "2"):
            with self.subTest(schema_version=value):
                invalid = copy.deepcopy(manifest)
                invalid["project"]["schema_version"] = value
                with self.assertRaisesRegex(
                    loop_yaml.LedgerValidationError, "schema_version"
                ):
                    loop_yaml.manifest_definitions(invalid)
        with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "objective_id"):
            loop_yaml.manifest_definitions(
                manifest, expected_objective_id="other-objective"
            )

        missing_mode = copy.deepcopy(manifest)
        missing_mode["tasks"][0]["review"].pop("mode")
        with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "review.mode"):
            loop_yaml.manifest_definitions(missing_mode)

        missing_gate = copy.deepcopy(manifest)
        missing_gate["tasks"][0]["human_gate"].pop("gate")
        with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "human_gate.gate"):
            loop_yaml.manifest_definitions(missing_gate)


class MigrationTests(unittest.TestCase):
    def test_claimed_becomes_ready_plus_active_fenced_claim(self):
        document = valid_v1()
        task = document["tasks"][0]
        task.update(
            {
                "status": "claimed",
                "owner": {"type": "worker", "id": "worker-1"},
                "claim": {"lease_id": "lease-1", "lease_expires_at": "2026-07-11T00:00:00Z"},
            }
        )
        migrated, report = loop_yaml.migrate_v1(document)
        self.assertEqual("ready", migrated["tasks"][0]["status"])
        self.assertEqual(1, migrated["claims"][0]["fencing_token"]["generation"])
        self.assertFalse(report["writes_performed"])

    def test_unsafe_becomes_safety_blocked(self):
        document = valid_v1()
        document["tasks"][0]["status"] = "unsafe"
        migrated, _ = loop_yaml.migrate_v1(document)
        self.assertEqual("blocked", migrated["tasks"][0]["status"])
        self.assertEqual("safety", migrated["tasks"][0]["blocker"]["kind"])

    def test_migrate_rejects_v2_input(self):
        document = valid_v1()
        document["ledger"]["schema_version"] = 2
        with self.assertRaises(loop_yaml.LedgerValidationError):
            loop_yaml.migrate_v1(document)

    def test_in_progress_migration_preserves_fenced_owner(self):
        document = valid_v1()
        task = document["tasks"][0]
        task.update(
            {
                "status": "in_progress",
                "owner": {"type": "subagent", "id": "worker-1"},
                "claim": {"lease_id": "lease-1", "lease_expires_at": "2026-07-11T00:00:00Z"},
            }
        )
        migrated, _ = loop_yaml.migrate_v1(document)
        self.assertEqual("in_progress", migrated["tasks"][0]["status"])
        self.assertEqual("worker-1", migrated["claims"][0]["owner"]["id"])
        self.assertEqual([], loop_yaml.validate_ledger(migrated))

    def test_migrated_in_progress_state_replays_and_accepts_a_followup_event(self):
        document = valid_v1()
        document["tasks"][0].update(
            {
                "status": "in_progress",
                "owner": {"type": "subagent", "id": "worker-1"},
                "claim": {
                    "lease_id": "lease-1",
                    "lease_expires_at": "2026-07-11T00:00:00Z",
                },
            }
        )
        migrated, _ = loop_yaml.migrate_v1(document)
        definitions = {
            "T1": {
                "initial_status": "ready",
                "dependencies": [],
                "scope": ["x"],
                "dod": ["done"],
                "verification": ["test"],
            }
        }
        self.assertEqual([], loop_yaml.semantic_audit(migrated, definitions))
        state = loop_yaml.state_from_ledger(migrated, definitions)
        token = migrated["claims"][0]["fencing_token"]
        event = {
            "sequence": 2,
            "event_id": "migration-followup",
            "occurred_at": "2026-07-10T00:01:00Z",
            "actor": "worker-1",
            "type": "task_transition",
            "task_id": "T1",
            "idempotency_key": "migration-followup",
            "expected_state_revision": 1,
            "previous_event_hash": state["last_event_hash"],
            "payload": {
                "target_status": "blocked",
                "fencing_token": token,
                "evidence": {},
                "blocker": {"kind": "test", "reason": "prove continuation"},
            },
        }
        event["event_hash"] = loop_core.calculate_event_hash(event)
        updated, replayed = loop_core.apply_event(
            state,
            event,
            trusted_time=dt.datetime.fromisoformat("2026-07-10T00:02:00+00:00"),
        )
        self.assertFalse(replayed)
        materialized = loop_yaml.update_ledger_view(migrated, updated)
        self.assertEqual("blocked", materialized["tasks"][0]["status"])
        self.assertEqual([], loop_yaml.semantic_audit(materialized, definitions))

    def test_migration_anchor_rejects_tampered_embedded_source(self):
        migrated, _ = loop_yaml.migrate_v1(valid_v1())
        migrated["events"][0]["payload"]["source_ledger"]["tasks"][0]["status"] = "done"
        errors = loop_yaml.validate_ledger(migrated)
        self.assertTrue(any("source hash mismatch" in error for error in errors))

    def test_reviewing_migration_blocks_until_a_new_fenced_claim(self):
        document = valid_v1()
        document["tasks"][0]["status"] = "reviewing"
        migrated, report = loop_yaml.migrate_v1(document)
        self.assertEqual("blocked", migrated["tasks"][0]["status"])
        self.assertEqual("migration", migrated["tasks"][0]["blocker"]["kind"])
        self.assertTrue(any("reviewing task" in warning for warning in report["warnings"]))

    def test_cli_write_after_migration_keeps_anchor_replayable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            contract_document = valid_v2()
            manifest_path = write_contract(root, contract_document)
            v1 = valid_v1()
            for field in ("branch", "head_sha"):
                v1["ledger"]["source_revision"][field] = contract_document["ledger"][
                    "source_revision"
                ][field]
            migrated, _ = loop_yaml.migrate_v1(v1)
            migrated["ledger"]["loop_spec"] = "loop-spec.md"
            migrated["ledger"]["task_manifest"] = "task-manifest.yaml"
            for field in ("spec_sha256", "task_manifest_sha256"):
                migrated["ledger"]["source_revision"][field] = contract_document["ledger"][
                    "source_revision"
                ][field]
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(migrated), encoding="utf-8")
            event = {
                "sequence": 2,
                "event_id": "post-migration-gate",
                "occurred_at": "2026-07-10T00:01:00Z",
                "actor": "maintainer",
                "type": "gate_updated",
                "task_id": "",
                "idempotency_key": "post-migration-gate",
                "expected_state_revision": 1,
                "previous_event_hash": migrated["ledger"]["state_revision"]["last_event_hash"],
                "payload": {"gate": "publish", "status": "pending"},
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
            written = loop_yaml.load_yaml(ledger_path)
            self.assertNotEqual(
                written["ledger"]["source_revision"]["previous_ledger_sha256"],
                written["ledger"]["source_revision"]["migration_source_sha256"],
            )
            definitions = loop_yaml.manifest_definitions(loop_yaml.load_yaml(manifest_path))
            self.assertEqual([], loop_yaml.semantic_audit(written, definitions))

    def test_bound_in_progress_migration_rebinds_claim_and_accepts_cli_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            contract_document = valid_v2()
            manifest_path = write_contract(root, contract_document)
            spec_path = root / "loop-spec.md"
            v1 = valid_v1()
            for field in ("branch", "head_sha"):
                v1["ledger"]["source_revision"][field] = contract_document["ledger"][
                    "source_revision"
                ][field]
            v1["tasks"][0].update(
                {
                    "status": "in_progress",
                    "owner": {"type": "subagent", "id": "worker-1"},
                    "claim": {
                        "lease_id": "lease-1",
                        "lease_expires_at": "2099-07-11T00:00:00Z",
                    },
                }
            )
            v1_path = root / "v1.yaml"
            v1_path.write_text(loop_yaml.dump_yaml(v1), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.command_migrate(
                        v1_path,
                        spec_path=spec_path,
                        manifest_path=manifest_path,
                        repo_root=root,
                    ),
                )
            rendered = json.loads(output.getvalue())
            migrated = rendered["preview"]
            self.assertTrue(rendered["report"]["contract_bound"])
            self.assertEqual("loop-spec.md", migrated["ledger"]["loop_spec"])
            self.assertEqual("task-manifest.yaml", migrated["ledger"]["task_manifest"])
            self.assertEqual(
                migrated["ledger"]["source_revision"]["spec_sha256"],
                migrated["claims"][0]["source_revision"]["spec_sha256"],
            )
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(migrated), encoding="utf-8")
            token = migrated["claims"][0]["fencing_token"]
            event = {
                "sequence": 2,
                "event_id": "bound-migration-followup",
                "occurred_at": "2026-07-10T00:01:00Z",
                "actor": "worker-1",
                "type": "task_transition",
                "task_id": "T1",
                "idempotency_key": "bound-migration-followup",
                "expected_state_revision": 1,
                "previous_event_hash": migrated["ledger"]["state_revision"]["last_event_hash"],
                "payload": {
                    "target_status": "blocked",
                    "fencing_token": token,
                    "evidence": {},
                    "blocker": {"kind": "test", "reason": "bound migration continued"},
                },
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
            definitions = loop_yaml.manifest_definitions(loop_yaml.load_yaml(manifest_path))
            written = loop_yaml.load_yaml(ledger_path)
            self.assertEqual("blocked", written["tasks"][0]["status"])
            self.assertEqual([], loop_yaml.semantic_audit(written, definitions))

    def test_bound_migration_rejects_contract_path_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = pathlib.Path(directory)
            contract_document = valid_v2()
            manifest_path = write_contract(root, contract_document)
            outside_spec = pathlib.Path(outside) / "loop-spec.md"
            outside_spec.write_text("# Outside\n", encoding="utf-8")
            v1 = valid_v1()
            for field in ("branch", "head_sha"):
                v1["ledger"]["source_revision"][field] = contract_document["ledger"][
                    "source_revision"
                ][field]
            v1_path = root / "v1.yaml"
            v1_path.write_text(loop_yaml.dump_yaml(v1), encoding="utf-8")
            with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "inside the target repository"):
                loopctl.command_migrate(
                    v1_path,
                    spec_path=outside_spec,
                    manifest_path=manifest_path,
                    repo_root=root,
                )

    def test_bound_migration_rejects_manifest_task_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            contract_document = valid_v2()
            manifest_path = write_contract(root, contract_document)
            manifest = loop_yaml.load_yaml(manifest_path)
            manifest["tasks"][0]["id"] = "OTHER"
            manifest_path.write_text(loop_yaml.dump_yaml(manifest), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", manifest_path.name], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "change manifest"],
                check=True,
            )
            v1 = valid_v1()
            v1["ledger"]["source_revision"]["branch"] = subprocess.run(
                ["git", "-C", str(root), "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            v1["ledger"]["source_revision"]["head_sha"] = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            v1_path = root / "v1.yaml"
            v1_path.write_text(loop_yaml.dump_yaml(v1), encoding="utf-8")
            with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "not executable"):
                loopctl.command_migrate(
                    v1_path,
                    spec_path=root / "loop-spec.md",
                    manifest_path=manifest_path,
                    repo_root=root,
                )

    def test_migration_anchor_rejects_in_progress_with_incomplete_dependency(self):
        document = valid_v1()
        document["tasks"].insert(
            0,
            {
                "id": "T0",
                "status": "ready",
                "dependencies": [],
                "evidence": {
                    "verification": {"status": "not_run"},
                    "review": {"status": "not_required"},
                },
            },
        )
        document["tasks"][1].update(
            {
                "status": "in_progress",
                "owner": {"type": "subagent", "id": "worker-1"},
                "claim": {
                    "lease_id": "lease-1",
                    "lease_expires_at": "2026-07-11T00:00:00Z",
                },
            }
        )
        migrated, _ = loop_yaml.migrate_v1(document)
        definitions = {
            "T0": {
                "initial_status": "ready",
                "dependencies": [],
                "scope": ["base"],
                "dod": ["done"],
                "verification": ["test"],
            },
            "T1": {
                "initial_status": "planned",
                "dependencies": ["T0"],
                "scope": ["dependent"],
                "dod": ["done"],
                "verification": ["test"],
            },
        }
        errors = loop_yaml.semantic_audit(migrated, definitions)
        self.assertTrue(any("incomplete dependencies" in error for error in errors))

    def test_bound_command_rejects_incomplete_dependency_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            contract_document = valid_v2()
            manifest_path = write_contract(root, contract_document)
            manifest = loop_yaml.load_yaml(manifest_path)
            manifest["tasks"] = [
                {
                    "id": "T0",
                    "initial_status": "ready",
                    "dependencies": [],
                    "scope": {"in": ["base"], "out": []},
                    "dod": ["done"],
                    "verification": ["test"],
                },
                {
                    "id": "T1",
                    "initial_status": "planned",
                    "dependencies": ["T0"],
                    "scope": {"in": ["dependent"], "out": []},
                    "dod": ["done"],
                    "verification": ["test"],
                },
            ]
            manifest_path.write_text(loop_yaml.dump_yaml(manifest), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", manifest_path.name], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "add dependency"],
                check=True,
            )
            v1 = valid_v1()
            v1["tasks"].insert(
                0,
                {
                    "id": "T0",
                    "status": "ready",
                    "dependencies": [],
                    "evidence": {
                        "verification": {"status": "not_run"},
                        "review": {"status": "not_required"},
                    },
                },
            )
            v1["tasks"][1].update(
                {
                    "status": "in_progress",
                    "dependencies": ["T0"],
                    "owner": {"type": "subagent", "id": "worker-1"},
                    "claim": {
                        "lease_id": "lease-1",
                        "lease_expires_at": "2026-07-11T00:00:00Z",
                    },
                }
            )
            v1["ledger"]["source_revision"]["branch"] = subprocess.run(
                ["git", "-C", str(root), "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            v1["ledger"]["source_revision"]["head_sha"] = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            v1_path = root / "v1.yaml"
            v1_path.write_text(loop_yaml.dump_yaml(v1), encoding="utf-8")
            with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "incomplete dependencies"):
                loopctl.command_migrate(
                    v1_path,
                    spec_path=root / "loop-spec.md",
                    manifest_path=manifest_path,
                    repo_root=root,
                )


class CliTests(unittest.TestCase):
    def test_claim_acquisition_crossing_deadline_before_replace_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            claim = {
                "task_id": "T1",
                "status": "active",
                "owner": {"type": "subagent", "id": "worker-1"},
                "fencing_token": {"generation": 1, "nonce": "acquire-race"},
                "expected_state_revision": 0,
                "source_revision": {
                    field: document["ledger"]["source_revision"][field]
                    for field in (
                        "branch",
                        "head_sha",
                        "spec_sha256",
                        "task_manifest_sha256",
                    )
                },
                "claimed_at": "2026-07-10T00:00:00Z",
                "lease_expires_at": "2026-07-10T00:10:00Z",
            }
            event = {
                "sequence": 1,
                "event_id": "acquire-race",
                "occurred_at": "2026-07-10T00:05:00Z",
                "actor": "worker-1",
                "type": "claim_acquired",
                "task_id": "T1",
                "idempotency_key": "acquire-race",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"claim": claim},
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            original = ledger_path.read_bytes()

            output = StringIO()
            with mock.patch.object(
                loopctl,
                "_trusted_current_time",
                side_effect=(
                    dt.datetime.fromisoformat("2026-07-10T00:09:00+00:00"),
                    dt.datetime.fromisoformat("2026-07-10T00:10:00+00:00"),
                ),
            ) as trusted_time:
                with redirect_stdout(output):
                    self.assertEqual(
                        1,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                            repo_root=root,
                        ),
                    )
            self.assertEqual(2, trusted_time.call_count)
            self.assertIn("expired at trusted current time", output.getvalue())
            self.assertEqual(original, ledger_path.read_bytes())

    def test_active_transition_crossing_deadline_before_replace_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document, manifest_path, claim, acquired = materialized_claim_contract(root)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            event = {
                "sequence": 2,
                "event_id": "transition-race",
                "occurred_at": "2026-07-10T00:05:00Z",
                "actor": "worker-1",
                "type": "task_transition",
                "task_id": "T1",
                "idempotency_key": "transition-race",
                "expected_state_revision": 1,
                "previous_event_hash": acquired["event_hash"],
                "payload": {
                    "target_status": "in_progress",
                    "fencing_token": claim["fencing_token"],
                    "evidence": {},
                },
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            original = ledger_path.read_bytes()

            output = StringIO()
            with mock.patch.object(
                loopctl,
                "_trusted_current_time",
                side_effect=(
                    dt.datetime.fromisoformat("2026-07-10T00:09:00+00:00"),
                    dt.datetime.fromisoformat("2026-07-10T00:10:00+00:00"),
                ),
            ) as trusted_time:
                with redirect_stdout(output):
                    self.assertEqual(
                        1,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                            repo_root=root,
                        ),
                    )
            self.assertEqual(2, trusted_time.call_count)
            self.assertIn("unexpired claim lease at trusted current time", output.getvalue())
            self.assertEqual(original, ledger_path.read_bytes())

    def test_source_rebound_crossing_deadline_before_replace_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            document, manifest_path, claim, acquired = materialized_claim_contract(root)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", ledger_path.name], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "checkpoint claim"],
                check=True,
            )
            checkpoint_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            previous_source = {
                field: document["ledger"]["source_revision"][field]
                for field in (
                    "branch",
                    "head_sha",
                    "spec_sha256",
                    "task_manifest_sha256",
                )
            }
            target_source = {**previous_source, "head_sha": checkpoint_head}
            event = {
                "sequence": 2,
                "event_id": "rebound-race",
                "occurred_at": "2026-07-10T00:05:00Z",
                "actor": "maintainer",
                "type": "source_rebound",
                "task_id": "",
                "idempotency_key": "rebound-race",
                "expected_state_revision": 1,
                "previous_event_hash": acquired["event_hash"],
                "payload": {
                    "previous_source_revision": previous_source,
                    "target_source_revision": target_source,
                    "active_claim_task_ids": ["T1"],
                    "expired_claim_dispositions": {},
                    "evidence": {"artifact": "source-rebound-receipt"},
                },
            }
            authorization = {
                "action": "source_rebound",
                "principal": {"type": "user", "id": "maintainer"},
                "objective_id": document["ledger"]["objective_id"],
                "artifact": "source-rebound-receipt",
                "source_revision_sha256": loop_core.source_revision_digest(
                    previous_source
                ),
                "target_head_sha": checkpoint_head,
            }
            event["payload"]["authorization"] = authorization
            authorization["protected_payload_sha256"] = (
                loop_core.protected_payload_digest(event["payload"])
            )
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path = root / "source-rebound.yaml"
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            original = ledger_path.read_bytes()

            output = StringIO()
            with mock.patch.object(
                loopctl,
                "_trusted_current_time",
                side_effect=(
                    dt.datetime.fromisoformat("2026-07-10T00:09:00+00:00"),
                    dt.datetime.fromisoformat("2026-07-10T00:10:00+00:00"),
                ),
            ) as trusted_time:
                with redirect_stdout(output):
                    self.assertEqual(
                        1,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                            repo_root=root,
                            authorize_action="source_rebound",
                            authorization_receipt_sha256=loop_core.digest(
                                authorization
                            ),
                        ),
                    )
            self.assertEqual(2, trusted_time.call_count)
            self.assertIn("expiry classification changed", output.getvalue())
            self.assertEqual(original, ledger_path.read_bytes())

    def test_source_rebound_advances_clean_checkpointed_active_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", ledger_path.name], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "checkpoint ledger"],
                check=True,
            )
            checkpoint_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            previous_source = {
                field: document["ledger"]["source_revision"][field]
                for field in (
                    "branch",
                    "head_sha",
                    "spec_sha256",
                    "task_manifest_sha256",
                )
            }
            target_source = {**previous_source, "head_sha": checkpoint_head}
            event = {
                "sequence": 1,
                "event_id": "rebind-checkpoint",
                "actor": "test",
                "occurred_at": "2026-07-10T00:01:00Z",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "idempotency_key": "rebind-checkpoint",
                "type": "source_rebound",
                "task_id": "",
                "payload": {
                    "previous_source_revision": previous_source,
                    "target_source_revision": target_source,
                    "active_claim_task_ids": [],
                    "evidence": {"artifact": "source-rebound-receipt"},
                },
            }
            authorization = {
                "action": "source_rebound",
                "principal": {"type": "user", "id": "maintainer"},
                "objective_id": document["ledger"]["objective_id"],
                "artifact": "source-rebound-receipt",
                "source_revision_sha256": loop_core.source_revision_digest(
                    previous_source
                ),
                "target_head_sha": checkpoint_head,
            }
            event["payload"]["authorization"] = authorization
            authorization["protected_payload_sha256"] = (
                loop_core.protected_payload_digest(event["payload"])
            )
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path = root / "source-rebound.yaml"
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")

            output = StringIO()
            with mock.patch.object(
                loopctl,
                "_source_rebound_contract",
                wraps=loopctl._source_rebound_contract,
            ) as contract_preflight:
                with redirect_stdout(output):
                    result = loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                        authorize_action="source_rebound",
                        authorization_receipt_sha256=loop_core.digest(authorization),
                    )
            self.assertEqual(0, result, output.getvalue())
            self.assertEqual(2, contract_preflight.call_count)
            applied = json.loads(output.getvalue())
            self.assertEqual("source_rebound", applied["protected_action"])
            self.assertTrue(applied["live_authorization_verified"])
            self.assertIsNotNone(applied["protected_history_sha256"])
            rebound = loop_yaml.load_yaml(ledger_path)
            self.assertEqual(
                checkpoint_head,
                rebound["ledger"]["source_revision"]["head_sha"],
            )
            self.assertEqual(0o644, stat.S_IMODE(ledger_path.stat().st_mode))
            self.assertEqual([], loop_yaml.semantic_audit(
                rebound,
                loop_yaml.manifest_definitions(
                    loop_yaml.load_yaml(manifest_path),
                    expected_objective_id="issue-81",
                ),
            ))
            audit_output = StringIO()
            with redirect_stdout(audit_output):
                self.assertEqual(
                    0,
                    loopctl.command_audit(
                        ledger_path, manifest_path, repo_root=root
                    ),
                    audit_output.getvalue(),
                )

            protected_history_sha256 = loop_core.protected_history_digest(
                rebound["events"]
            )
            replay_before = ledger_path.read_bytes()
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
            self.assertEqual(replay_before, ledger_path.read_bytes())
            replay_output = StringIO()
            with redirect_stdout(replay_output):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                        protected_history_sha256=protected_history_sha256,
                    ),
                    replay_output.getvalue(),
                )
            self.assertEqual("replayed", json.loads(replay_output.getvalue())["status"])
            self.assertEqual(replay_before, ledger_path.read_bytes())

            later = {
                "sequence": 2,
                "event_id": "later-block",
                "actor": "test",
                "occurred_at": "2026-07-10T00:02:00Z",
                "expected_state_revision": 1,
                "previous_event_hash": rebound["ledger"]["state_revision"][
                    "last_event_hash"
                ],
                "idempotency_key": "later-block",
                "type": "task_transition",
                "task_id": "T1",
                "payload": {
                    "target_status": "blocked",
                    "evidence": {"artifact": "test-receipt"},
                    "blocker": {"kind": "test", "reason": "test blocker"},
                },
            }
            later["event_hash"] = loop_core.calculate_event_hash(later)
            later_path = root / "later.yaml"
            later_path.write_text(loop_yaml.dump_yaml(later), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        later_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                        protected_history_sha256=protected_history_sha256,
                    ),
                )
            after_later = loop_yaml.load_yaml(ledger_path)
            later_history_sha256 = loop_core.protected_history_digest(
                after_later["events"]
            )
            replay_before = ledger_path.read_bytes()
            replay_output = StringIO()
            with redirect_stdout(replay_output):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                        protected_history_sha256=later_history_sha256,
                    ),
                    replay_output.getvalue(),
                )
            self.assertEqual("replayed", json.loads(replay_output.getvalue())["status"])
            self.assertEqual(replay_before, ledger_path.read_bytes())

    def test_source_rebound_rejects_worktree_or_index_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            document = valid_v2()
            write_contract(root, document)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", ledger_path.name], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "checkpoint ledger"],
                check=True,
            )
            outside_manifest = root.parent / "outside-manifest.yaml"
            outside_manifest.write_bytes((root / "task-manifest.yaml").read_bytes())
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError, "inside the target repository"
            ):
                loopctl._source_rebound_contract(
                    ledger_path,
                    document,
                    outside_manifest,
                    root,
                    target_head=subprocess.run(
                        ["git", "-C", str(root), "rev-parse", "HEAD"],
                        check=True,
                        capture_output=True,
                        text=True,
                    ).stdout.strip(),
                )
            ledger_path.write_text(
                ledger_path.read_text(encoding="utf-8") + "\n# tamper\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError,
                "working ledger bytes and mode",
            ):
                loopctl._verified_rebind_source(ledger_path, document, root)

            subprocess.run(
                ["git", "-C", str(root), "restore", ledger_path.name], check=True
            )
            ledger_path.write_text(
                ledger_path.read_text(encoding="utf-8") + "\n# staged tamper\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(root), "add", ledger_path.name], check=True)
            subprocess.run(
                ["git", "-C", str(root), "restore", "--worktree", ledger_path.name],
                check=True,
            )
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError,
                "index and HEAD blob",
            ):
                loopctl._verified_rebind_source(ledger_path, document, root)

    def test_source_rebound_contract_requires_target_head_index_and_worktree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", ledger_path.name], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "checkpoint ledger"],
                check=True,
            )
            target_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            with mock.patch.object(
                loopctl.git_source,
                "run_git",
                side_effect=OSError("bounded probe failed"),
            ):
                with self.assertRaisesRegex(
                    loop_yaml.LedgerValidationError,
                    "task manifest target Git binding cannot be verified",
                ):
                    loopctl._source_rebound_contract(
                        ledger_path,
                        document,
                        manifest_path,
                        root,
                        target_head=target_head,
                    )

            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8") + "\n# modified\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError, "task manifest digest mismatch"
            ):
                loopctl._source_rebound_contract(
                    ledger_path,
                    document,
                    manifest_path,
                    root,
                    target_head=target_head,
                )
            subprocess.run(
                ["git", "-C", str(root), "restore", manifest_path.name], check=True
            )

            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8") + "\n# staged\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "-C", str(root), "add", manifest_path.name], check=True
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "restore",
                    "--source=HEAD",
                    "--worktree",
                    manifest_path.name,
                ],
                check=True,
            )
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError,
                "task manifest index and target HEAD blob",
            ):
                loopctl._source_rebound_contract(
                    ledger_path,
                    document,
                    manifest_path,
                    root,
                    target_head=target_head,
                )
            subprocess.run(
                ["git", "-C", str(root), "restore", "--staged", manifest_path.name],
                check=True,
            )

            untracked = root / "untracked-spec.md"
            untracked.write_text("# untracked\n", encoding="utf-8")
            untracked_document = copy.deepcopy(document)
            untracked_document["ledger"]["loop_spec"] = untracked.name
            untracked_document["ledger"]["source_revision"]["spec_sha256"] = (
                hashlib.sha256(untracked.read_bytes()).hexdigest()
            )
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError, "loop spec must be one tracked"
            ):
                loopctl._source_rebound_contract(
                    ledger_path,
                    untracked_document,
                    manifest_path,
                    root,
                    target_head=target_head,
                )

            spec_path = root / "loop-spec.md"
            expected_spec = spec_path.read_bytes()
            spec_path.write_text("# Changed in target HEAD\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", spec_path.name], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "change spec"],
                check=True,
            )
            divergent_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            spec_path.write_bytes(expected_spec)
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError,
                "loop spec working bytes and mode must match target HEAD",
            ):
                loopctl._source_rebound_contract(
                    ledger_path,
                    document,
                    manifest_path,
                    root,
                    target_head=divergent_head,
                )

    def test_source_rebound_rejects_special_ledger_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            document = valid_v2()
            write_contract(root, document)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", ledger_path.name], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "checkpoint ledger"],
                check=True,
            )
            ledger_path.chmod(0o1644)
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError, "bytes and mode to match HEAD"
            ):
                loopctl._verified_rebind_source(ledger_path, document, root)

    def test_bound_contract_rejects_fifo_device_and_path_swap_without_hanging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            fifo = root / "contract.fifo"
            os.mkfifo(fifo)
            probe = (
                "import pathlib,sys;"
                f"sys.path.insert(0,{str(SCRIPT_DIR)!r});"
                "import loopctl;"
                f"loopctl._bound_contract_bytes(pathlib.Path({str(fifo)!r}),"
                f"pathlib.Path({str(root)!r}),None,'fifo contract')"
            )
            completed = subprocess.run(
                [sys.executable, "-c", probe],
                capture_output=True,
                text=True,
                timeout=2,
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("single-link regular file", completed.stderr)

            event_path = root / "event.yaml"
            event_path.write_text("type: source_rebound\n", encoding="utf-8")
            apply_probe = (
                "import pathlib,sys;"
                f"sys.path.insert(0,{str(SCRIPT_DIR)!r});"
                "import loopctl;"
                f"loopctl.command_apply_event(pathlib.Path({str(fifo)!r}),"
                f"pathlib.Path({str(event_path)!r}),manifest_path=None,write=False,"
                f"repo_root=pathlib.Path({str(root)!r}))"
            )
            completed = subprocess.run(
                [sys.executable, "-c", apply_probe],
                capture_output=True,
                text=True,
                timeout=2,
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("single-link regular file", completed.stderr)

            if pathlib.Path("/dev/null").exists():
                with self.assertRaisesRegex(
                    loop_yaml.LedgerValidationError, "single-link regular file"
                ):
                    loopctl._bound_contract_bytes(
                        pathlib.Path("/dev/null"), pathlib.Path("/dev"), None, "device"
                    )

            artifact = root / "contract.yaml"
            replacement = root / "replacement.yaml"
            artifact.write_bytes(b"original\n")
            replacement.write_bytes(b"replacement\n")
            real_read = loopctl.os.read
            swapped = False

            def swap_after_read(descriptor: int, amount: int) -> bytes:
                nonlocal swapped
                chunk = real_read(descriptor, amount)
                if not swapped:
                    os.replace(replacement, artifact)
                    swapped = True
                return chunk

            with mock.patch.object(loopctl.os, "read", side_effect=swap_after_read):
                with self.assertRaisesRegex(
                    loop_yaml.LedgerValidationError,
                    "changed while it was read|path binding changed",
                ):
                    loopctl._bound_contract_bytes(
                        artifact, root, None, "swapped contract"
                    )

    def test_source_rebound_requires_matching_live_and_event_time_expiry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory).resolve()
            document = valid_v2()
            manifest_path = write_contract(root, document)
            definitions = loop_yaml.manifest_definitions(
                loop_yaml.load_yaml(manifest_path), expected_objective_id="issue-81"
            )
            state = loop_yaml.state_from_ledger(document, definitions)
            source = copy.deepcopy(state["source_revision"])
            state["claims"]["T1"] = {
                "task_id": "T1",
                "owner": {"type": "agent", "id": "worker"},
                "fencing_token": {"generation": 1, "nonce": "lease-1"},
                "status": "active",
                "claimed_at": "2026-07-10T00:00:00Z",
                "lease_expires_at": "2026-07-10T00:02:00Z",
                "source_revision": copy.deepcopy(source),
            }

            def rebound(occurred_at: str, *, expired: bool) -> tuple[dict, dict]:
                target = {**source, "head_sha": "f" * 40}
                claim_payload = (
                    {
                        "active_claim_task_ids": [],
                        "expired_claim_dispositions": {
                            "T1": {
                                "status": "expired",
                                "fencing_token": {
                                    "generation": 1,
                                    "nonce": "lease-1",
                                },
                                "blocker": {"reason": "lease expired"},
                            }
                        },
                    }
                    if expired
                    else {
                        "active_claim_task_ids": ["T1"],
                        "expired_claim_dispositions": {},
                    }
                )
                event = {
                    "sequence": 1,
                    "event_id": f"rebound-{occurred_at}",
                    "actor": "maintainer",
                    "occurred_at": occurred_at,
                    "expected_state_revision": 0,
                    "previous_event_hash": "",
                    "idempotency_key": f"rebound-{occurred_at}",
                    "type": "source_rebound",
                    "task_id": "",
                    "payload": {
                        "previous_source_revision": source,
                        "target_source_revision": target,
                        **claim_payload,
                        "evidence": {"artifact": "source-rebound-receipt"},
                    },
                }
                authorization = {
                    "action": "source_rebound",
                    "principal": {"type": "user", "id": "maintainer"},
                    "objective_id": "issue-81",
                    "artifact": "source-rebound-receipt",
                    "source_revision_sha256": loop_core.source_revision_digest(source),
                    "target_head_sha": target["head_sha"],
                }
                event["payload"]["authorization"] = authorization
                authorization["protected_payload_sha256"] = (
                    loop_core.protected_payload_digest(event["payload"])
                )
                event["event_hash"] = loop_core.calculate_event_hash(event)
                return event, authorization

            event, authorization = rebound(
                "2026-07-10T00:01:00Z", expired=False
            )
            trusted = {
                "action": "source_rebound",
                "authorization_receipt_sha256": loop_core.digest(authorization),
            }
            with self.assertRaisesRegex(
                loop_core.LoopContractError, "expiry classification changed"
            ):
                loop_core.apply_event(
                    state,
                    event,
                    trusted_authority=trusted,
                    trusted_time=dt.datetime.fromisoformat(
                        "2026-07-10T00:03:00+00:00"
                    ),
                )
            live, _ = loop_core.apply_event(
                state,
                event,
                trusted_authority=trusted,
                trusted_time=dt.datetime.fromisoformat(
                    "2026-07-10T00:01:30+00:00"
                ),
            )
            replayed, _ = loop_core.replay_event(state, event)
            self.assertEqual(live, replayed)
            self.assertEqual("active", replayed["claims"]["T1"]["status"])

            expired_event, expired_authorization = rebound(
                "2026-07-10T00:02:00Z", expired=True
            )
            expired_live, _ = loop_core.apply_event(
                state,
                expired_event,
                trusted_authority={
                    "action": "source_rebound",
                    "authorization_receipt_sha256": loop_core.digest(
                        expired_authorization
                    ),
                },
                trusted_time=dt.datetime.fromisoformat(
                    "2026-07-10T00:03:00+00:00"
                ),
            )
            expired_replay, _ = loop_core.replay_event(state, expired_event)
            self.assertEqual(expired_live, expired_replay)
            self.assertEqual(
                "expired", expired_live["claims"]["T1"]["status"]
            )

            future, future_authorization = rebound(
                "2100-01-01T00:00:00Z", expired=True
            )
            with self.assertRaisesRegex(loop_core.LoopContractError, "future"):
                loop_core.apply_event(
                    state,
                    future,
                    trusted_authority={
                        "action": "source_rebound",
                        "authorization_receipt_sha256": loop_core.digest(
                            future_authorization
                        ),
                    },
                    trusted_time=dt.datetime.fromisoformat(
                        "2026-07-10T00:03:00+00:00"
                    ),
                )

    def test_live_task_transition_requires_fresh_lease_and_matches_replay(self):
        document = valid_v2()
        definitions = {
            "T1": {
                "initial_status": "ready",
                "dependencies": [],
                "scope": {"in": ["x"], "out": []},
                "dod": ["done"],
                "verification": ["test"],
                "review_required": False,
                "human_gate_required": False,
            }
        }
        state = loop_yaml.state_from_ledger(document, definitions)
        state["claims"]["T1"] = {
            "task_id": "T1",
            "owner": {"type": "agent", "id": "worker"},
            "fencing_token": {"generation": 1, "nonce": "lease-1"},
            "status": "active",
            "claimed_at": "2026-07-10T00:00:00Z",
            "lease_expires_at": "2026-07-10T00:02:00Z",
            "source_revision": copy.deepcopy(state["source_revision"]),
        }
        event = {
            "sequence": 1,
            "event_id": "backdated-transition",
            "actor": "worker",
            "occurred_at": "2026-07-10T00:01:00Z",
            "expected_state_revision": 0,
            "previous_event_hash": "",
            "idempotency_key": "backdated-transition",
            "type": "task_transition",
            "task_id": "T1",
            "payload": {
                "target_status": "in_progress",
                "fencing_token": {"generation": 1, "nonce": "lease-1"},
                "evidence": {},
            },
        }
        event["event_hash"] = loop_core.calculate_event_hash(event)
        with self.assertRaisesRegex(
            loop_core.LoopContractError, "trusted current time"
        ):
            loop_core.apply_event(
                state,
                event,
                trusted_time=dt.datetime.fromisoformat(
                    "2026-07-10T00:03:00+00:00"
                ),
            )
        live, _ = loop_core.apply_event(
            state,
            event,
            trusted_time=dt.datetime.fromisoformat(
                "2026-07-10T00:01:30+00:00"
            ),
        )
        replayed, _ = loop_core.replay_event(state, event)
        self.assertEqual(live, replayed)
        self.assertEqual("in_progress", live["tasks"]["T1"]["status"])

    def test_verified_git_head_disables_promisor_lazy_fetch(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            root = base / "repo"
            initial = init_git_repository(root)
            marker = base / "remote-helper-executed"
            helper = base / "remote-helper.py"
            helper.write_text(
                f"#!{sys.executable}\n"
                "import pathlib\n"
                f"pathlib.Path({str(marker)!r}).write_text('executed\\n', encoding='utf-8')\n",
                encoding="utf-8",
            )
            helper.chmod(0o700)
            subprocess.run(
                ["git", "-C", str(root), "config", "extensions.partialClone", "origin"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "remote.origin.promisor", "true"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "config",
                    "remote.origin.partialclonefilter",
                    "blob:none",
                ],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "remote.origin.url", f"ext::{helper}"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "protocol.ext.allow", "always"],
                check=True,
            )
            fake_head = "a" * 40
            (root / ".git" / "refs" / "heads" / initial["branch"]).write_text(
                fake_head + "\n", encoding="ascii"
            )
            with self.assertRaises(subprocess.CalledProcessError):
                git_source.verified_git_head(root)
            self.assertFalse(marker.exists())
            self.assertEqual(
                "1", git_source.sanitized_git_environment()["GIT_NO_LAZY_FETCH"]
            )

    def test_source_head_relation_allows_only_terminal_completed_ancestor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory) / "repo"
            initial = init_git_repository(root)
            source_head = initial["head_sha"]
            branch = initial["branch"]
            (root / "tracked.txt").write_text("second\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "second"],
                check=True,
            )
            current_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            completed = {
                "ledger": {"source_revision": {"head_sha": source_head}},
                "current_loop": {"lifecycle": "complete"},
                "events": [{"type": "objective_completed"}],
            }
            self.assertEqual(
                "ancestor",
                git_source.source_head_relation(root, completed, current_head),
            )

            active = copy.deepcopy(completed)
            active["current_loop"]["lifecycle"] = "active"
            self.assertEqual(
                "mismatch",
                git_source.source_head_relation(root, active, current_head),
            )
            incomplete = copy.deepcopy(completed)
            incomplete["events"] = [{"type": "task_transition"}]
            self.assertEqual(
                "mismatch",
                git_source.source_head_relation(root, incomplete, current_head),
            )
            self.assertEqual(
                "unknown",
                git_source.source_head_relation(
                    root,
                    {
                        **completed,
                        "ledger": {"source_revision": {"head_sha": "0" * 40}},
                    },
                    current_head,
                ),
            )
            self.assertEqual(
                "unknown",
                git_source.source_head_relation(
                    root,
                    {**completed, "ledger": {"source_revision": {}}},
                    current_head,
                ),
            )
            for malformed in ("A" * 40, "a" * 39, "a" * 41, "not-a-sha"):
                with self.subTest(malformed=malformed):
                    self.assertEqual(
                        "unknown",
                        git_source.source_head_relation(
                            root,
                            {
                                **completed,
                                "ledger": {
                                    "source_revision": {"head_sha": malformed}
                                },
                            },
                            current_head,
                        ),
                    )
            self.assertEqual(
                "unknown",
                git_source.source_head_relation(root, active, source_head),
            )
            exact = copy.deepcopy(active)
            exact["ledger"]["source_revision"]["head_sha"] = current_head
            self.assertEqual(
                "exact",
                git_source.source_head_relation(root, exact, current_head),
            )

            fake_head = "a" * 40
            (root / ".git" / "refs" / "heads" / branch).write_text(
                fake_head + "\n", encoding="ascii"
            )
            broken = copy.deepcopy(active)
            broken["ledger"]["source_revision"]["head_sha"] = fake_head
            self.assertEqual(
                "unknown",
                git_source.source_head_relation(root, broken, fake_head),
            )
            subprocess.run(
                ["git", "-C", str(root), "update-ref", f"refs/heads/{branch}", current_head],
                check=False,
                capture_output=True,
            )
            (root / ".git" / "refs" / "heads" / branch).write_text(
                current_head + "\n", encoding="ascii"
            )

            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "diverged", source_head],
                check=True,
            )
            (root / "tracked.txt").write_text("diverged\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "diverged"],
                check=True,
            )
            diverged_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", branch],
                check=True,
            )
            diverged = copy.deepcopy(completed)
            diverged["ledger"]["source_revision"]["head_sha"] = diverged_head
            self.assertEqual(
                "mismatch",
                git_source.source_head_relation(root, diverged, current_head),
            )
            grafts = root / ".git" / "info" / "grafts"
            grafts.write_text(
                f"{current_head} {diverged_head}\n",
                encoding="utf-8",
            )
            self.assertEqual(
                0,
                subprocess.run(
                    [
                        "git",
                        "--no-replace-objects",
                        "-C",
                        str(root),
                        "merge-base",
                        "--is-ancestor",
                        diverged_head,
                        current_head,
                    ],
                    check=False,
                    capture_output=True,
                ).returncode,
            )
            self.assertEqual(
                "mismatch",
                git_source.source_head_relation(root, diverged, current_head),
            )
            grafts.unlink()
            inherited_grafts = root / "inherited-grafts"
            inherited_grafts.write_text(
                f"{current_head} {diverged_head}\n",
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ,
                {"GIT_GRAFT_FILE": str(inherited_grafts)},
                clear=False,
            ):
                self.assertEqual(
                    "mismatch",
                    git_source.source_head_relation(root, diverged, current_head),
                )

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "switch",
                    "-q",
                    "-c",
                    "replacement-target",
                    diverged_head,
                ],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "commit",
                    "-q",
                    "--allow-empty",
                    "-m",
                    "replacement",
                ],
                check=True,
            )
            replacement_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(["git", "-C", str(root), "switch", "-q", branch], check=True)
            subprocess.run(
                ["git", "-C", str(root), "replace", current_head, replacement_head],
                check=True,
            )
            self.assertEqual(
                0,
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(root),
                        "merge-base",
                        "--is-ancestor",
                        diverged_head,
                        current_head,
                    ],
                    check=False,
                ).returncode,
            )
            self.assertEqual(
                "mismatch",
                git_source.source_head_relation(root, diverged, current_head),
            )

    def test_git_source_and_loopctl_ignore_repository_selector_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            target = base / "target"
            decoy = base / "decoy"
            target_state = init_git_repository(target)
            decoy_state = init_git_repository(decoy)
            subprocess.run(
                ["git", "-C", str(decoy), "switch", "-q", "-c", "decoy-branch"],
                check=True,
            )
            decoy_state["branch"] = "decoy-branch"
            (decoy / "later.txt").write_text("later\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(decoy), "add", "later.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(decoy), "commit", "-q", "-m", "later"],
                check=True,
            )
            decoy_head = subprocess.run(
                ["git", "-C", str(decoy), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            document = {
                "ledger": {
                    "source_revision": {
                        "branch": decoy_state["branch"],
                        "head_sha": decoy_state["head_sha"],
                    }
                },
                "current_loop": {"lifecycle": "complete"},
                "events": [{"type": "objective_completed"}],
            }
            ledger_path = target / "loop-state-ledger.yaml"
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {"GIT_DIR": str(decoy / ".git")},
                clear=False,
            ):
                self.assertEqual(
                    "unknown",
                    git_source.source_head_relation(target, document, decoy_head),
                )
                with self.assertRaisesRegex(
                    loop_yaml.LedgerValidationError,
                    "git branch mismatch|git HEAD mismatch",
                ):
                    loopctl._verify_git_source(ledger_path, document, target)
            self.assertNotEqual(target_state["head_sha"], decoy_head)

    def test_git_marker_bounded_reader_rejects_swap_fifo_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            marker = base / "marker"
            marker.write_text("gitdir: admin\n", encoding="utf-8")
            expected_identity = git_source._stat_identity(marker.lstat())
            replacement = base / "replacement"
            replacement.write_text("gitdir: other\n", encoding="utf-8")
            os.replace(replacement, marker)
            with self.assertRaisesRegex(OSError, "cannot be read safely"):
                git_source._read_bounded_single_line(
                    marker,
                    "test marker",
                    expected_identity=expected_identity,
                )

            fifo = base / "marker-fifo"
            os.mkfifo(fifo)
            started = time.monotonic()
            with self.assertRaisesRegex(OSError, "cannot be read safely"):
                git_source._read_bounded_single_line(fifo, "test FIFO")
            self.assertLess(time.monotonic() - started, 1.0)

            oversized = base / "oversized-marker"
            oversized.write_bytes(b"x" * 4097)
            with self.assertRaisesRegex(OSError, "cannot be read safely"):
                git_source._read_bounded_single_line(oversized, "oversized marker")

    def test_git_probe_timeout_and_output_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            slow = base / "slow-git"
            slow.write_text("#!/bin/sh\n/bin/sleep 2\n", encoding="utf-8")
            slow.chmod(0o700)
            with (
                mock.patch.object(
                    git_source, "_resolved_git_executable", return_value=slow
                ),
                self.assertRaisesRegex(OSError, "exceeded its timeout"),
            ):
                git_source.run_git(base, ["status"], timeout_seconds=0.1)

            noisy = base / "noisy-git"
            noisy.write_text(
                "#!/bin/sh\n/usr/bin/printf '0123456789abcdef'\n",
                encoding="utf-8",
            )
            noisy.chmod(0o700)
            with (
                mock.patch.object(
                    git_source, "_resolved_git_executable", return_value=noisy
                ),
                self.assertRaisesRegex(OSError, "exceeded its output limit"),
            ):
                git_source.run_git(base, ["status"], output_limit_bytes=8)

    def test_git_executable_discovery_ignores_ambient_path(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            fake_git = base / "git"
            fake_git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_git.chmod(0o700)
            trusted = shutil.which("git", path=os.defpath)
            self.assertIsNotNone(trusted)
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": str(base),
                    "CODEX_LOOP_GIT_EXECUTABLE": str(fake_git),
                },
                clear=False,
            ):
                selected = git_source._resolved_git_executable()
            self.assertEqual(pathlib.Path(trusted).resolve(strict=True), selected)
            self.assertNotEqual(fake_git, selected)

    def test_git_executable_default_discovery_skips_usrmerge_symlink_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve()
            safe_bin = base / "usr-bin"
            safe_bin.mkdir()
            safe_git = safe_bin / "git"
            safe_git.write_bytes(b"\x7fELF-test-native-git")
            safe_git.chmod(0o700)
            linked_bin = base / "bin"
            linked_bin.symlink_to(safe_bin, target_is_directory=True)

            with mock.patch.object(
                git_source.os,
                "defpath",
                os.pathsep.join((str(linked_bin), str(safe_bin))),
            ):
                selected = git_source._resolved_git_executable()

            self.assertEqual(safe_git, selected)

    def test_git_executable_explicit_script_wrapper_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve()
            explicit_git = base / "operator-selected-git"
            explicit_git.write_text(
                "#!/bin/sh\nprintf 'trusted-explicit-git\\n'\n",
                encoding="utf-8",
            )
            explicit_git.chmod(0o700)
            with mock.patch.dict(os.environ, {}, clear=False):
                with self.assertRaisesRegex(OSError, "script wrappers"):
                    git_source._resolved_git_executable(explicit_git)
                self.assertNotIn(
                    "CODEX_LOOP_GIT_EXECUTABLE",
                    git_source.sanitized_git_environment(),
                )

    def test_git_executable_explicit_override_rejects_relative_and_symlink_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve()
            executable = base / "git-real"
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            executable.chmod(0o700)
            link = base / "git-link"
            link.symlink_to(executable)
            with self.assertRaisesRegex(OSError, "absolute"):
                git_source._resolved_git_executable("relative/git")
            with self.assertRaisesRegex(OSError, "regular file"):
                git_source._resolved_git_executable(pathlib.Path("/"))
            with self.assertRaisesRegex(OSError, "symlink"):
                git_source._resolved_git_executable(link)

            real_parent = base.resolve() / "real-parent"
            real_parent.mkdir()
            parent_git = real_parent / "git"
            parent_git.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            parent_git.chmod(0o700)
            parent_link = base.resolve() / "parent-link"
            parent_link.symlink_to(real_parent, target_is_directory=True)
            with self.assertRaisesRegex(OSError, "symlink"):
                git_source._resolved_git_executable(parent_link / "git")

    def test_git_probe_environment_is_allowlisted_and_rejects_unsafe_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory).resolve()
            hostile = {
                "PATH": str(base),
                "DEVELOPER_DIR": str(base / "missing-developer"),
                "SDKROOT": str(base / "missing-sdk"),
                "LD_PRELOAD": str(base / "fake-loader.so"),
                "LD_LIBRARY_PATH": str(base),
                "DYLD_INSERT_LIBRARIES": str(base / "fake-dyld.dylib"),
                "CODEX_LOOP_GIT_EXECUTABLE": str(base / "fake-git"),
            }
            with mock.patch.dict(os.environ, hostile, clear=False):
                safe = git_source.sanitized_git_environment()
                for key in hostile:
                    self.assertNotIn(key, safe)
                result = git_source.run_git(base, ["--version"])
                self.assertEqual(0, result.returncode)
                with self.assertRaisesRegex(ValueError, "unsupported keys"):
                    git_source.run_git(
                        base,
                        ["--version"],
                        environment={**safe, "LD_PRELOAD": hostile["LD_PRELOAD"]},
                    )

    def test_git_probe_timeout_cleans_descendants_after_parent_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            marker = base / "late-descendant"
            fake_git = base / "descendant-git"
            child = (
                "import pathlib,time; time.sleep(0.4); "
                f"pathlib.Path({str(marker)!r}).write_text('late')"
            )
            fake_git.write_text(
                f"#!{sys.executable}\n"
                "import subprocess,sys\n"
                f"subprocess.Popen([sys.executable, '-c', {child!r}])\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o700)
            with (
                mock.patch.object(
                    git_source, "_resolved_git_executable", return_value=fake_git
                ),
                self.assertRaisesRegex(OSError, "exceeded its timeout"),
            ):
                git_source.run_git(base, ["status"], timeout_seconds=0.1)
            time.sleep(0.6)
            self.assertFalse(marker.exists())

    def test_successful_git_probe_cleans_detached_output_descendants(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            marker = base / "late-success-descendant"
            fake_git = base / "successful-descendant-git"
            child = (
                "import pathlib,time; time.sleep(0.4); "
                f"pathlib.Path({str(marker)!r}).write_text('late')"
            )
            fake_git.write_text(
                f"#!{sys.executable}\n"
                "import subprocess,sys\n"
                "with open('/dev/null', 'wb') as sink:\n"
                f"    subprocess.Popen([sys.executable, '-c', {child!r}], "
                "stdout=sink, stderr=sink)\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o700)
            with mock.patch.object(
                git_source, "_resolved_git_executable", return_value=fake_git
            ):
                result = git_source.run_git(base, ["status"], timeout_seconds=2)
            self.assertEqual(0, result.returncode)
            self.assertFalse(marker.exists())
            time.sleep(0.6)
            self.assertFalse(marker.exists())

    def test_git_probe_interrupt_cleans_process_group_and_reraises(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            fake_git = base / "interruptible-git"
            fake_git.write_text(
                "#!/bin/sh\n/bin/sleep 2\n",
                encoding="utf-8",
            )
            fake_git.chmod(0o700)
            original_cleanup = git_source._terminate_process_group
            with (
                mock.patch.object(
                    git_source, "_resolved_git_executable", return_value=fake_git
                ),
                mock.patch.object(
                    git_source.selectors.DefaultSelector,
                    "select",
                    side_effect=KeyboardInterrupt,
                ),
                mock.patch.object(
                    git_source,
                    "_terminate_process_group",
                    wraps=original_cleanup,
                ) as cleanup,
                self.assertRaises(KeyboardInterrupt),
            ):
                git_source.run_git(base, ["status"], timeout_seconds=2)
            cleanup.assert_called_once()

    def test_git_marker_accepts_valid_linked_worktree_and_rejects_bad_backref(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            root = base / "repo"
            init_git_repository(root)
            linked = base / "linked"
            subprocess.run(
                ["git", "-C", str(root), "worktree", "add", "-q", "-b", "linked", str(linked)],
                check=True,
            )
            evidence = git_source.validated_git_marker(linked)
            self.assertTrue(evidence.git_dir.is_dir())
            self.assertEqual(linked.resolve(), git_source.verified_git_root(linked))

            marker_line = (linked / ".git").read_text(encoding="utf-8").strip()
            admin = pathlib.Path(marker_line.removeprefix("gitdir: "))
            (admin / "gitdir").write_text(str(root / ".git") + "\n", encoding="utf-8")
            with self.assertRaises(OSError):
                git_source.validated_git_marker(linked)

    def test_loopctl_rejects_enclosing_repository_core_worktree_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            outer = base / "outer"
            source = init_git_repository(outer)
            nested = outer / "nested"
            nested.mkdir()
            subprocess.run(
                ["git", "-C", str(outer), "config", "--local", "core.worktree", str(nested)],
                check=True,
            )
            document = {
                "ledger": {"source_revision": source},
                "current_loop": {"lifecycle": "active"},
                "events": [{"type": "task_transition"}],
            }
            ledger_path = nested / "loop-state-ledger.yaml"
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError,
                "could not verify git source revision|exact target Git repository root",
            ):
                loopctl._verify_git_source(ledger_path, document, nested)

            with self.assertRaises(OSError):
                git_source.verified_git_root(nested)
            (nested / ".git").write_text("gitdir: ../.git\n", encoding="utf-8")
            with self.assertRaises(OSError):
                git_source.verified_git_root(nested)

    def test_terminal_contract_audit_accepts_ancestor_but_transition_rejects(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path, manifest_path, source_head = completed_v2_contract(root)

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.command_audit(ledger_path, manifest_path, repo_root=root),
                )
            self.assertIn('"status": "valid"', output.getvalue())

            for reopen in (False, True):
                with self.subTest(reopen=reopen):
                    output = StringIO()
                    with redirect_stdout(output):
                        result = loopctl.command_transition(
                            ledger_path,
                            "T1",
                            "ready",
                            manifest_path=manifest_path,
                            repo_root=root,
                            reopen=reopen,
                        )
                    self.assertEqual(1, result)
                    self.assertIn("objective completion is terminal", output.getvalue())

            (root / "later.txt").write_text("later\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "later.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "later"],
                check=True,
            )
            current_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertNotEqual(source_head, current_head)
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.command_audit(ledger_path, manifest_path, repo_root=root),
                )
            self.assertIn('"status": "valid"', output.getvalue())

            document = loop_yaml.load_yaml(ledger_path)
            document["current_loop"]["lifecycle"] = "active"
            active_path = root / "active-ledger.yaml"
            active_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "git HEAD mismatch"):
                loopctl.command_audit(active_path, manifest_path, repo_root=root)

            branch = subprocess.run(
                ["git", "-C", str(root), "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "wrong-branch"],
                check=True,
            )
            with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "git branch mismatch"):
                loopctl.command_audit(ledger_path, manifest_path, repo_root=root)
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", branch],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "--detach"],
                check=True,
            )
            with self.assertRaisesRegex(loop_yaml.LedgerValidationError, "git branch mismatch"):
                loopctl.command_audit(ledger_path, manifest_path, repo_root=root)
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", branch],
                check=True,
            )

    def test_transition_preview_rejects_non_replayable_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            document["tasks"][0].update(
                {
                    "status": "blocked",
                    "blocker": {"kind": "test", "reason": "tampered view"},
                }
            )
            ledger_path = root / "ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                result = loopctl.command_transition(
                    ledger_path,
                    "T1",
                    "cancelled",
                    manifest_path=manifest_path,
                    repo_root=root,
                )
            self.assertEqual(1, result)
            self.assertIn("does not match event replay", output.getvalue())

    def test_contract_source_mismatches_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            document["ledger"]["loop_spec"] = "loop-spec.md"
            document["ledger"]["task_manifest"] = "task-manifest.yaml"
            ledger_path = root / "ledger.yaml"
            cases = (
                ("branch", "wrong-branch", "git branch mismatch"),
                ("head_sha", "0" * 40, "git HEAD mismatch"),
                ("spec_sha256", "0" * 64, "loop spec digest mismatch"),
                ("task_manifest_sha256", "0" * 64, "task manifest digest mismatch"),
            )
            for field, value, message in cases:
                with self.subTest(field=field):
                    candidate = copy.deepcopy(document)
                    candidate["ledger"]["source_revision"][field] = value
                    ledger_path.write_text(loop_yaml.dump_yaml(candidate), encoding="utf-8")
                    with self.assertRaisesRegex(loop_yaml.LedgerValidationError, message):
                        loopctl._definitions(
                            ledger_path,
                            candidate,
                            manifest_path,
                            require_contract=True,
                            repo_root=root,
                        )

    def test_validate_command_returns_zero_for_valid_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "ledger.yaml"
            path.write_text(
                """ledger:\n  schema_version: 1\n  objective_id: issue-81\n  objective: deliver loop core\n  source_revision:\n    branch: branch\n    head_sha: abc123\n    updated_at: 2026-07-10T00:00:00Z\ntasks:\n  - id: T1\n    status: ready\n    dependencies: []\n    evidence:\n      verification:\n        status: not_run\n      review:\n        status: not_required\n""",
                encoding="utf-8",
            )
            with redirect_stdout(StringIO()):
                self.assertEqual(0, loopctl.main(["validate", str(path)]))

    def test_hash_event_prints_production_hash_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "event.yaml"
            event = {
                "sequence": 1,
                "event_id": "event-1",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "worker-1",
                "type": "gate_updated",
                "task_id": "",
                "idempotency_key": "event-1",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"gate": "publish", "status": "pending"},
                "event_hash": "replace-me",
            }
            path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(0, loopctl.main(["hash-event", str(path)]))
            self.assertIn(loop_core.calculate_event_hash({k: v for k, v in event.items() if k != "event_hash"}), output.getvalue())
            self.assertIn("replace-me", path.read_text(encoding="utf-8"))

    def test_decide_command_calls_production_router(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            decision = {
                "id": "docs-route",
                "input": {
                    "request": {"kind": "docs", "risk": "routine"},
                    "objective": {"clear": True, "complete": False},
                    "state": {
                        "source_conflict": False,
                        "verification": "not_run",
                        "review": "not_required",
                        "human_gate": "not_required",
                        "task_status": "ready",
                    },
                    "runtime": {"surface": "cli", "capabilities": {}},
                    "work": {},
                },
                "expect": {},
            }
            path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        ["decide", str(path), "--protected-history-sha256", "none"]
                    ),
                )
            self.assertIn('"route": "docs-update"', output.getvalue())


    def test_agent_route_and_integrate_use_trusted_current_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo_root = root / "repo"
            document = agent_route_document(init_git_repository(repo_root))
            route_path = root / "route.json"
            facts_path = root / "facts.json"
            facts_path.write_text(
                json.dumps(
                    {
                        "custom_agent_surface": "available",
                        "parent_sandbox_mode": "workspace-write",
                        "available_models": ["gpt-5.6-terra"],
                        "reasoning_efforts": {"gpt-5.6-terra": ["medium"]},
                    }
                ),
                encoding="utf-8",
            )
            route_path.write_text(json.dumps(document), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "agent-route",
                            str(route_path),
                            "--runtime-facts",
                            str(facts_path),
                        ]
                    ),
                )
            receipt = json.loads(output.getvalue())["route_receipt"]
            profile_path = ROOT / "agent-profiles" / "loop_v2a_balanced_worker.toml"
            self.assertEqual(
                hashlib.sha256(profile_path.read_bytes()).hexdigest(),
                receipt["selected_profile_digest"],
            )

            artifact_root = root / "artifacts"
            verification_root = root / "verification"
            artifact_root.mkdir()
            verification_root.mkdir()
            result_path = artifact_root / "result.txt"
            result_path.write_text("worker output\n", encoding="utf-8")
            verification_path = verification_root / "tests.txt"
            verification_path.write_text("tests passed\n", encoding="utf-8")
            integration_path = root / "integration.json"
            integration_path.write_text(
                json.dumps(
                    agent_integration_document(
                        receipt,
                        artifact=result_path.name,
                        artifact_digest=hashlib.sha256(
                            result_path.read_bytes()
                        ).hexdigest(),
                        verification_artifact=verification_path.name,
                        verification_digest=hashlib.sha256(
                            verification_path.read_bytes()
                        ).hexdigest(),
                    )
                ),
                encoding="utf-8",
            )
            integration_output = StringIO()
            with redirect_stdout(integration_output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "agent-integrate",
                            str(integration_path),
                            "--repo-root",
                            str(repo_root),
                            "--artifact-root",
                            str(artifact_root),
                            "--verification-root",
                            str(verification_root),
                            "--assignment-fresh",
                            "--profile-path",
                            str(profile_path),
                        ]
                    ),
                )
            integrated = json.loads(integration_output.getvalue())
            self.assertEqual("accepted", integrated["status"])
            self.assertFalse(integrated["integration"]["completion_proven"])

            empty_agents = root / "empty-agents"
            empty_agents.mkdir()
            fallback_document = copy.deepcopy(document)
            fallback_document["agent_route"]["profile_preflight"][
                "destination_root"
            ] = str(empty_agents)
            route_path.write_text(json.dumps(fallback_document), encoding="utf-8")
            facts_path.write_text(
                json.dumps(
                    {
                        "custom_agent_surface": "available",
                        "available_models": [],
                        "reasoning_efforts": {},
                        "parent_default": {"available": True},
                    }
                ),
                encoding="utf-8",
            )
            fallback_output = StringIO()
            with redirect_stdout(fallback_output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "agent-route",
                            str(route_path),
                            "--runtime-facts",
                            str(facts_path),
                        ]
                    ),
                )
            fallback_receipt = json.loads(fallback_output.getvalue())["route_receipt"]
            self.assertIsNone(fallback_receipt["selected_profile_digest"])
            integration_path.write_text(
                json.dumps(
                    agent_integration_document(
                        fallback_receipt,
                        artifact=result_path.name,
                        artifact_digest=hashlib.sha256(
                            result_path.read_bytes()
                        ).hexdigest(),
                        verification_artifact=verification_path.name,
                        verification_digest=hashlib.sha256(
                            verification_path.read_bytes()
                        ).hexdigest(),
                    )
                ),
                encoding="utf-8",
            )
            no_profile_output = StringIO()
            with redirect_stdout(no_profile_output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "agent-integrate",
                            str(integration_path),
                            "--repo-root",
                            str(repo_root),
                            "--artifact-root",
                            str(artifact_root),
                            "--verification-root",
                            str(verification_root),
                            "--assignment-fresh",
                        ]
                    ),
                )
            self.assertEqual(
                "accepted", json.loads(no_profile_output.getvalue())["status"]
            )

    def test_agent_routing_trusted_boundaries_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo_root = root / "repo"
            source_revision = init_git_repository(repo_root)
            document = agent_route_document(source_revision)
            route_path = root / "route.json"
            facts_path = root / "facts.json"
            facts_path.write_text(
                json.dumps(
                    {
                        "custom_agent_surface": "available",
                        "parent_sandbox_mode": "workspace-write",
                        "available_models": ["gpt-5.6-terra"],
                        "reasoning_efforts": {"gpt-5.6-terra": ["medium"]},
                    }
                ),
                encoding="utf-8",
            )

            route_path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(SystemExit):
                with redirect_stderr(StringIO()):
                    loopctl.main(["agent-route", str(route_path)])

            head_only = copy.deepcopy(document)
            head_only["agent_route"]["assignment"]["source_revision"].pop("branch")
            route_path.write_text(json.dumps(head_only), encoding="utf-8")
            head_only_output = StringIO()
            with redirect_stdout(head_only_output):
                self.assertEqual(
                    1,
                    loopctl.main(
                        [
                            "agent-route",
                            str(route_path),
                            "--runtime-facts",
                            str(facts_path),
                        ]
                    ),
                )
            self.assertIn("exact branch", head_only_output.getvalue())

            embedded = copy.deepcopy(document)
            embedded["agent_route"]["profile_preflight"]["runtime_facts"] = str(
                facts_path
            )
            route_path.write_text(json.dumps(embedded), encoding="utf-8")
            embedded_output = StringIO()
            with redirect_stdout(embedded_output):
                self.assertEqual(
                    1,
                    loopctl.main(
                        [
                            "agent-route",
                            str(route_path),
                            "--runtime-facts",
                            str(facts_path),
                        ]
                    ),
                )
            self.assertIn("unknown fields: runtime_facts", embedded_output.getvalue())

            alternate_registry = root / "alternate-registry.json"
            alternate_registry.write_bytes(
                loopctl.CANONICAL_PROFILE_REGISTRY.read_bytes()
            )
            alternate = copy.deepcopy(document)
            alternate["agent_route"]["profile_preflight"]["registry"] = str(
                alternate_registry
            )
            route_path.write_text(json.dumps(alternate), encoding="utf-8")
            alternate_output = StringIO()
            with redirect_stdout(alternate_output):
                self.assertEqual(
                    1,
                    loopctl.main(
                        [
                            "agent-route",
                            str(route_path),
                            "--runtime-facts",
                            str(facts_path),
                        ]
                    ),
                )
            self.assertIn(
                "canonical installed skill registry", alternate_output.getvalue()
            )

            route_path.write_text(json.dumps(document), encoding="utf-8")
            routed_output = StringIO()
            with redirect_stdout(routed_output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "agent-route",
                            str(route_path),
                            "--runtime-facts",
                            str(facts_path),
                        ]
                    ),
                )
            receipt = json.loads(routed_output.getvalue())["route_receipt"]
            profile_path = ROOT / "agent-profiles" / "loop_v2a_balanced_worker.toml"
            artifact_root = root / "artifacts"
            verification_root = root / "verification"
            artifact_root.mkdir()
            verification_root.mkdir()
            result_path = artifact_root / "result.txt"
            result_path.write_text("worker output\n", encoding="utf-8")
            verification_path = verification_root / "tests.txt"
            verification_path.write_text("tests passed\n", encoding="utf-8")
            valid_digest = hashlib.sha256(result_path.read_bytes()).hexdigest()
            integration = agent_integration_document(
                receipt,
                artifact=result_path.name,
                artifact_digest=valid_digest,
                verification_artifact=verification_path.name,
                verification_digest=hashlib.sha256(
                    verification_path.read_bytes()
                ).hexdigest(),
            )
            integration_path = root / "integration.json"
            common_args = [
                "agent-integrate",
                str(integration_path),
                "--repo-root",
                str(repo_root),
                "--artifact-root",
                str(artifact_root),
                "--verification-root",
                str(verification_root),
                "--assignment-fresh",
                "--profile-path",
                str(profile_path),
            ]

            malformed = copy.deepcopy(integration)
            malformed["agent_integration"]["route_receipt"][
                "contract_version"
            ] = 2
            malformed["agent_integration"]["route_receipt"][
                "classification"
            ] = None
            integration_path.write_text(json.dumps(malformed), encoding="utf-8")
            malformed_output = StringIO()
            with redirect_stdout(malformed_output):
                self.assertEqual(1, loopctl.main(common_args))
            malformed_result = json.loads(malformed_output.getvalue())
            self.assertEqual("rejected", malformed_result["status"])
            self.assertIn(
                "classification-semantic-mismatch",
                malformed_result["worker_validation"]["issues"],
            )

            with_current = copy.deepcopy(integration)
            with_current["agent_integration"]["current"] = {
                "source_revision": source_revision,
                "profile_digest": receipt["selected_profile_digest"],
                "assignment_fresh": True,
            }
            integration_path.write_text(json.dumps(with_current), encoding="utf-8")
            current_output = StringIO()
            with redirect_stdout(current_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn("unknown fields: current", current_output.getvalue())

            missing = agent_integration_document(
                receipt,
                artifact="missing.txt",
                artifact_digest="a" * 64,
                verification_artifact=verification_path.name,
                verification_digest=hashlib.sha256(
                    verification_path.read_bytes()
                ).hexdigest(),
            )
            integration_path.write_text(json.dumps(missing), encoding="utf-8")
            missing_output = StringIO()
            with redirect_stdout(missing_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn("regular non-symlink file", missing_output.getvalue())

            integration_path.write_text(json.dumps(integration), encoding="utf-8")
            result_path.write_text("tampered\n", encoding="utf-8")
            tampered_output = StringIO()
            with redirect_stdout(tampered_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn("digest mismatch", tampered_output.getvalue())
            result_path.write_text("worker output\n", encoding="utf-8")

            missing_verification = agent_integration_document(
                receipt,
                artifact=result_path.name,
                artifact_digest=valid_digest,
                verification_artifact="missing-tests.txt",
                verification_digest="a" * 64,
            )
            integration_path.write_text(
                json.dumps(missing_verification), encoding="utf-8"
            )
            verification_output = StringIO()
            with redirect_stdout(verification_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn(
                "regular non-symlink file", verification_output.getvalue()
            )

            tampered_verification = copy.deepcopy(integration)
            verification_path.write_text("tampered verification\n", encoding="utf-8")
            integration_path.write_text(
                json.dumps(tampered_verification), encoding="utf-8"
            )
            verification_digest_output = StringIO()
            with redirect_stdout(verification_digest_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn(
                "verification artifact digest mismatch",
                verification_digest_output.getvalue(),
            )
            verification_path.write_text("tests passed\n", encoding="utf-8")

            symlink_path = artifact_root / "linked-result.txt"
            symlink_path.symlink_to(result_path)
            symlinked = agent_integration_document(
                receipt,
                artifact=symlink_path.name,
                artifact_digest=valid_digest,
                verification_artifact=verification_path.name,
                verification_digest=hashlib.sha256(
                    verification_path.read_bytes()
                ).hexdigest(),
            )
            integration_path.write_text(json.dumps(symlinked), encoding="utf-8")
            symlink_output = StringIO()
            with redirect_stdout(symlink_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn("regular non-symlink file", symlink_output.getvalue())

            integration_path.write_text(json.dumps(integration), encoding="utf-8")
            alternate_profile_args = common_args[:-1] + [
                str(ROOT / "agent-profiles" / "loop_v2a_fast_explorer.toml")
            ]
            alternate_profile_output = StringIO()
            with redirect_stdout(alternate_profile_output):
                self.assertEqual(1, loopctl.main(alternate_profile_args))
            self.assertIn(
                "selected profile does not match",
                alternate_profile_output.getvalue(),
            )

            integration_path.write_text(json.dumps(integration), encoding="utf-8")
            without_assignment_flag = common_args[:]
            without_assignment_flag.remove("--assignment-fresh")
            with self.assertRaises(SystemExit):
                with redirect_stderr(StringIO()):
                    loopctl.main(without_assignment_flag)

            without_profile = common_args[:-2]
            profile_output = StringIO()
            with redirect_stdout(profile_output):
                self.assertEqual(1, loopctl.main(without_profile))
            self.assertIn("requires --profile-path", profile_output.getvalue())

            subprocess.run(
                ["git", "-C", str(repo_root), "switch", "-q", "-c", "same-head"],
                check=True,
            )
            same_head_output = StringIO()
            with redirect_stdout(same_head_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn("stale-source-revision", same_head_output.getvalue())
            subprocess.run(
                ["git", "-C", str(repo_root), "switch", "-q", source_revision["branch"]],
                check=True,
            )

            (repo_root / "later.txt").write_text("later\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo_root), "add", "later.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(repo_root), "commit", "-q", "-m", "later"],
                check=True,
            )
            stale_output = StringIO()
            with redirect_stdout(stale_output):
                self.assertEqual(1, loopctl.main(common_args))
            self.assertIn("stale-source-revision", stale_output.getvalue())

    def test_agent_route_command_rejects_incomplete_factor_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "agent-route.json"
            facts = pathlib.Path(directory) / "facts.json"
            facts.write_text(json.dumps({"custom_agent_surface": "unknown"}), encoding="utf-8")
            document = {
                "contract_version": 1,
                "task": {"id": "P1", "factors": {"ambiguity": "low"}},
                "profile_preflight": {
                    "profile_dir": str(ROOT / "agent-profiles"),
                    "registry": str(ROOT / "skills" / "loop-engineering" / "references" / "agent-profile-registry.json"),
                    "role": "loop_v2a_balanced_worker",
                },
                "assignment": {
                    "scope": ["owned.py"],
                    "ownership": {"owner": "worker", "disjoint": True},
                    "source_revision": {"head_sha": "abc123"},
                    "authority_contract": {"external_write_authorized": False},
                },
            }
            path.write_text(json.dumps(document), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    1,
                    loopctl.main(
                        [
                            "agent-route",
                            str(path),
                            "--runtime-facts",
                            str(facts),
                        ]
                    ),
                )
            self.assertIn("missing required fields", output.getvalue())

    def test_agent_route_v2_selects_deterministic_advanced_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo_root = root / "repo"
            document = agent_route_document(init_git_repository(repo_root))
            payload = document["agent_route"]
            payload["contract_version"] = 2
            payload["task"]["workload_kind"] = "implementation"
            payload["task"]["factors"]["reasoning_depth"] = "deep"
            payload["profile_preflight"]["role"] = "loop_v2a_advanced_worker"
            path = root / "route-v2.json"
            facts = root / "facts-v2.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            facts.write_text(
                json.dumps(
                    {
                        "custom_agent_surface": "available",
                        "parent_sandbox_mode": "workspace-write",
                        "available_models": ["gpt-5.6-sol"],
                        "reasoning_efforts": {"gpt-5.6-sol": ["medium"]},
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        ["agent-route", str(path), "--runtime-facts", str(facts)]
                    ),
                )
            receipt = json.loads(output.getvalue())["route_receipt"]
            self.assertEqual(2, receipt["contract_version"])
            self.assertEqual("advanced", receipt["classification"]["capability_tier"])
            self.assertEqual("loop_v2a_advanced_worker", receipt["runtime_mapping"])

            payload["profile_preflight"]["role"] = "loop_v2a_balanced_worker"
            path.write_text(json.dumps(document), encoding="utf-8")
            rejected = StringIO()
            with redirect_stdout(rejected):
                self.assertEqual(
                    1,
                    loopctl.main(
                        ["agent-route", str(path), "--runtime-facts", str(facts)]
                    ),
                )
            self.assertIn("must match the deterministic", rejected.getvalue())

    def test_agent_route_v2_automatically_uses_installed_higher_tier(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            repo_root = root / "repo"
            document = agent_route_document(init_git_repository(repo_root))
            payload = document["agent_route"]
            payload["contract_version"] = 2
            payload["task"]["workload_kind"] = "mechanical"
            payload["task"]["factors"].update(
                {
                    "ambiguity": "low",
                    "reasoning_depth": "shallow",
                    "code_context_volume": "small",
                    "security_data_migration_public_contract_risk": "none",
                    "write_blast_radius": "none",
                    "verification_burden": "low",
                }
            )
            payload["profile_preflight"]["role"] = "loop_v2a_mechanical_reader"
            path = root / "route-v2-fallback.json"
            facts = root / "facts-v2-fallback.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            facts.write_text(
                json.dumps(
                    {
                        "custom_agent_surface": "available",
                        "available_models": ["gpt-5.6-terra"],
                        "reasoning_efforts": {"gpt-5.6-terra": ["low"]},
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        ["agent-route", str(path), "--runtime-facts", str(facts)]
                    ),
                )
            rendered = json.loads(output.getvalue())
            receipt = rendered["route_receipt"]
            self.assertEqual("loop_v2a_fast_explorer", receipt["runtime_mapping"])
            self.assertEqual("mechanical", receipt["required_capability_tier"])
            self.assertEqual("efficient", receipt["selected_capability_tier"])
            self.assertEqual("same-class-higher-tier", receipt["fallback"])
            self.assertTrue(receipt["cost_degraded"])
            self.assertEqual(
                "loop_v2a_mechanical_reader",
                rendered["profile_preflight"]["requested_profile"],
            )

    def test_agent_route_command_rejects_unknown_contract_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "agent-route.json"
            facts = pathlib.Path(directory) / "facts.json"
            facts.write_text(
                json.dumps({"custom_agent_surface": "unknown"}), encoding="utf-8"
            )
            path.write_text(
                json.dumps(
                    {
                        "contract_version": 1,
                        "task": {"id": "P1", "factors": {}, "permission": "write-all"},
                        "profile_preflight": {
                            "profile_dir": "profiles",
                            "registry": "registry.json",
                            "role": "loop_v2a_balanced_worker",
                        },
                        "assignment": {},
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    1,
                    loopctl.main(
                        [
                            "agent-route",
                            str(path),
                            "--runtime-facts",
                            str(facts),
                        ]
                    ),
                )
            self.assertIn("unknown fields: permission", output.getvalue())

    def test_decide_ignores_repo_asserted_external_write_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            decision = {
                "id": "external-write",
                "input": {
                    "request": {
                        "kind": "delivery",
                        "risk": "routine",
                        "requires_external_write": True,
                    },
                    "objective": {"clear": True, "complete": False},
                    "state": {
                        "source_conflict": False,
                        "verification": "not_run",
                        "review": "not_required",
                        "human_gate": "not_required",
                        "task_status": "ready",
                    },
                    "authority": {"external_write_authorized": True},
                    "runtime": {"surface": "cli", "capabilities": {}},
                    "work": {},
                },
                "expect": {},
            }
            path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        ["decide", str(path), "--protected-history-sha256", "none"]
                    ),
                )
            self.assertIn('"route": "human-gate"', output.getvalue())

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "decide",
                            str(path),
                            "--external-write-authorized",
                            "--protected-history-sha256",
                            "none",
                        ]
                    ),
                )
            self.assertIn('"route": "project-delivery"', output.getvalue())

    def test_decide_parent_report_fallback_requires_trusted_cli_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            decision = {
                "id": "parent-report-fallback",
                "input": {
                    "request": {"kind": "continuation", "risk": "high"},
                    "objective": {"clear": True, "complete": False},
                    "state": {
                        "source_conflict": False,
                        "verification": "not_run",
                        "review": "required",
                        "human_gate": "not_required",
                        "task_status": "reviewing",
                        "security_scan": {
                            "status": "running",
                            "phase": "reporting",
                            "worker_failure_kind": "safety_refused",
                            "reporting_retry_count": 2,
                        },
                    },
                    "runtime": {"surface": "desktop", "capabilities": {}},
                    "work": {},
                },
                "expect": {},
            }
            path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        ["decide", str(path), "--protected-history-sha256", "none"]
                    ),
                )
            self.assertIn("security-report-parent-fallback-not-authorized", output.getvalue())

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "decide",
                            str(path),
                            "--parent-security-report-fallback-authorized",
                            "--protected-history-sha256",
                            "none",
                        ]
                    ),
                )
            self.assertIn('"execution_mode": "parent-report-fallback"', output.getvalue())

    def test_decide_legacy_report_fallback_flag_does_not_authorize_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            decision = {
                "id": "legacy-report-fallback-discovery",
                "input": {
                    "request": {"kind": "continuation", "risk": "high"},
                    "objective": {"clear": True, "complete": False},
                    "state": {
                        "source_conflict": False,
                        "verification": "not_run",
                        "review": "required",
                        "human_gate": "not_required",
                        "task_status": "reviewing",
                        "security_scan": {
                            "status": "running",
                            "phase": "discovery",
                            "worker_failure_kind": "safety_refused",
                            "worker_retry_count": 2,
                        },
                    },
                    "runtime": {"surface": "desktop", "capabilities": {}},
                    "work": {},
                },
                "expect": {},
            }
            path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "decide",
                            str(path),
                            "--parent-security-report-fallback-authorized",
                            "--protected-history-sha256",
                            "none",
                        ]
                    ),
                )
            rendered = output.getvalue()
            self.assertIn('"execution_mode": "stop-for-human-gate"', rendered)
            self.assertIn("security-parent-fallback-not-authorized", rendered)

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "decide",
                            str(path),
                            "--parent-security-scan-fallback-authorized",
                            "--protected-history-sha256",
                            "none",
                        ]
                    ),
                )
            self.assertIn(
                '"execution_mode": "parent-scan-phase-fallback"',
                output.getvalue(),
            )

    def test_decide_ignores_legacy_reporting_retry_count_during_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            decision = {
                "id": "legacy-reporting-retry-discovery",
                "input": {
                    "request": {"kind": "continuation", "risk": "high"},
                    "objective": {"clear": True, "complete": False},
                    "state": {
                        "source_conflict": False,
                        "verification": "not_run",
                        "review": "required",
                        "human_gate": "not_required",
                        "task_status": "reviewing",
                        "security_scan": {
                            "status": "running",
                            "phase": "discovery",
                            "worker_failure_kind": "safety_refused",
                            "reporting_retry_count": 2,
                        },
                    },
                    "runtime": {
                        "surface": "desktop",
                        "capabilities": {"subagents": True},
                    },
                    "work": {},
                },
                "expect": {},
            }
            path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "decide",
                            str(path),
                            "--parent-security-scan-fallback-authorized",
                            "--protected-history-sha256",
                            "none",
                        ]
                    ),
                )
            rendered = output.getvalue()
            self.assertIn('"execution_mode": "replacement-worker"', rendered)
            self.assertNotIn("parent-scan-phase-fallback", rendered)

    def test_decide_worker_refusal_is_resumable_in_every_scan_phase(self):
        phases = ("preflight", "threat_model", "discovery", "validation", "attack_path", "reporting")
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            for phase in phases:
                with self.subTest(phase=phase, step="current-session"):
                    decision = {
                        "id": f"refusal-{phase}",
                        "input": {
                            "request": {"kind": "continuation", "risk": "high"},
                            "objective": {"clear": True, "complete": False},
                            "state": {
                                "source_conflict": False,
                                "verification": "not_run",
                                "review": "required",
                                "human_gate": "not_required",
                                "task_status": "reviewing",
                                "goal_status": "blocked",
                                "security_scan": {
                                    "status": "running",
                                    "phase": phase,
                                    "worker_failure_kind": "safety_refused",
                                    "worker_retry_count": 1,
                                },
                            },
                            "runtime": {
                                "surface": "desktop",
                                "capabilities": {"subagents": False},
                            },
                            "work": {},
                        },
                        "expect": {},
                    }
                    path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")
                    output = StringIO()
                    with redirect_stdout(output):
                        self.assertEqual(
                            0,
                            loopctl.main(
                                [
                                    "decide",
                                    str(path),
                                    "--protected-history-sha256",
                                    "none",
                                ]
                            ),
                        )
                    result = json.loads(output.getvalue())["decision"]
                    self.assertEqual("current-session", result["execution_mode"])
                    self.assertEqual("continue", result["next_decision"])
                    self.assertIn("security-scan-remains-running", result["notices"])
                    self.assertIn("goal-projection-conflict", result["notices"])

                with self.subTest(phase=phase, step="parent-fallback"):
                    decision["input"]["state"]["security_scan"]["worker_retry_count"] = 2
                    path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")
                    output = StringIO()
                    with redirect_stdout(output):
                        self.assertEqual(
                            0,
                            loopctl.main(
                                [
                                    "decide",
                                    str(path),
                                    "--parent-security-scan-fallback-authorized",
                                    "--protected-history-sha256",
                                    "none",
                                ]
                            ),
                        )
                    result = json.loads(output.getvalue())["decision"]
                    expected_mode = (
                        "parent-report-fallback"
                        if phase == "reporting"
                        else "parent-scan-phase-fallback"
                    )
                    self.assertEqual(expected_mode, result["execution_mode"])
                    self.assertEqual("continue", result["next_decision"])

    def test_decide_protected_history_requires_matching_cli_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / "decision.yaml"
            decision = {
                "id": "protected-history",
                "input": {
                    "request": {"kind": "docs", "risk": "routine"},
                    "objective": {"clear": True, "complete": False},
                    "state": {
                        "source_conflict": False,
                        "verification": "not_run",
                        "review": "not_required",
                        "human_gate": "not_required",
                        "task_status": "ready",
                        "protected_history_sha256": "verified-history",
                    },
                    "runtime": {"surface": "cli", "capabilities": {}},
                    "work": {},
                },
                "expect": {},
            }
            path.write_text(loop_yaml.dump_yaml(decision), encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(1, loopctl.main(["decide", str(path)]))
            self.assertIn("requires explicit current-session", output.getvalue())

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "decide",
                            str(path),
                            "--protected-history-sha256",
                            "verified-history",
                        ]
                    ),
                )
            self.assertIn('"route": "docs-update"', output.getvalue())

    def test_protected_cli_write_requires_exact_out_of_band_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            payload = {
                "gate": "publish",
                "status": "satisfied",
                "evidence": {"artifact": "approval-record"},
            }
            authorization = {
                "action": "gate_satisfaction",
                "principal": {"type": "user", "id": "maintainer"},
                "objective_id": document["ledger"]["objective_id"],
                "artifact": "approval-record",
                "source_revision_sha256": loop_core.source_revision_digest(
                    document["ledger"]["source_revision"]
                ),
                "gate": "publish",
            }
            payload["authorization"] = authorization
            authorization["protected_payload_sha256"] = (
                loop_core.protected_payload_digest(payload)
            )
            event = {
                "sequence": 1,
                "event_id": "approve-publish",
                "occurred_at": "2026-07-10T00:01:00Z",
                "actor": "maintainer",
                "type": "gate_updated",
                "task_id": "",
                "idempotency_key": "approve-publish",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": payload,
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            receipt_digest = loop_core.digest(authorization)

            preview_output = StringIO()
            with redirect_stdout(preview_output):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=False,
                        repo_root=root,
                    ),
                )
            preview = json.loads(preview_output.getvalue())
            self.assertEqual("preview", preview["status"])
            self.assertEqual("gate_satisfaction", preview["protected_action"])
            self.assertEqual(receipt_digest, preview["authorization_receipt_sha256"])
            self.assertFalse(preview["live_authorization_verified"])

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                        authorize_action="gate_satisfaction",
                        authorization_receipt_sha256="forged",
                    ),
                )
            self.assertEqual(0, loop_yaml.load_yaml(ledger_path)["ledger"]["state_revision"]["sequence"])

            output = StringIO()
            real_fsync = loopctl.os.fsync
            with mock.patch.object(loopctl.os, "fsync", wraps=real_fsync) as fsync:
                with redirect_stdout(output):
                    self.assertEqual(
                        0,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                            repo_root=root,
                            authorize_action="gate_satisfaction",
                            authorization_receipt_sha256=receipt_digest,
                        ),
                    )
                self.assertGreaterEqual(fsync.call_count, 2)
            applied = json.loads(output.getvalue())
            self.assertEqual("applied", applied["status"])
            self.assertTrue(applied["live_authorization_verified"])
            self.assertEqual(
                "satisfied",
                loop_yaml.load_yaml(ledger_path)["human_gates"][0]["status"],
            )

            written = loop_yaml.load_yaml(ledger_path)
            history_digest = loop_core.protected_history_digest(written["events"])
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    1,
                    loopctl.command_transition(
                        ledger_path,
                        "T1",
                        "cancelled",
                        manifest_path,
                        root,
                    ),
                )
                self.assertEqual(
                    0,
                    loopctl.command_transition(
                        ledger_path,
                        "T1",
                        "cancelled",
                        manifest_path,
                        root,
                        protected_history_sha256=history_digest,
                    ),
                )
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
            replay_output = StringIO()
            with redirect_stdout(replay_output):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                        protected_history_sha256=history_digest,
                    ),
                )
            replayed = json.loads(replay_output.getvalue())
            self.assertEqual("replayed", replayed["status"])
            self.assertFalse(replayed["live_authorization_verified"])
            self.assertTrue(replayed["protected_history_re_attested"])

    def test_audit_rejects_contract_references_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            outside_root = pathlib.Path(outside)
            outside_spec = outside_root / "loop-spec.md"
            outside_spec.write_text("# Outside spec\n", encoding="utf-8")
            document["ledger"]["loop_spec"] = str(outside_spec)
            document["ledger"]["source_revision"]["spec_sha256"] = hashlib.sha256(
                outside_spec.read_bytes()
            ).hexdigest()
            ledger_path = root / "ledger.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError, "inside the target repository"
            ):
                loopctl.command_audit(
                    ledger_path,
                    manifest_path=manifest_path,
                    repo_root=root,
                )

            repository_spec = root / "loop-spec.md"
            document["ledger"]["loop_spec"] = "loop-spec.md"
            document["ledger"]["source_revision"]["spec_sha256"] = hashlib.sha256(
                repository_spec.read_bytes()
            ).hexdigest()
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            outside_manifest = outside_root / "task-manifest.yaml"
            outside_manifest.write_text(
                loop_yaml.dump_yaml(loop_yaml.load_yaml(manifest_path)),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                loop_yaml.LedgerValidationError, "inside the target repository"
            ):
                loopctl.command_audit(
                    ledger_path,
                    manifest_path=outside_manifest,
                    repo_root=root,
                )

    def test_v2_apply_event_uses_public_ledger_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            document = valid_v2()
            manifest_path = write_contract(root, document)
            claim = {
                "task_id": "T1",
                "status": "active",
                "owner": {"type": "subagent", "id": "worker-1"},
                "fencing_token": {"generation": 1, "nonce": "nonce-1"},
                "expected_state_revision": 0,
                "source_revision": {
                    key: document["ledger"]["source_revision"][key]
                    for key in ("branch", "head_sha", "spec_sha256", "task_manifest_sha256")
                },
                "claimed_at": "2026-07-10T00:00:00Z",
                "lease_expires_at": "2099-07-11T00:00:00Z",
            }
            event = {
                "sequence": 1,
                "event_id": "event-1",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "worker-1",
                "type": "claim_acquired",
                "task_id": "T1",
                "idempotency_key": "event-1",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"claim": claim},
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")

            with redirect_stdout(StringIO()):
                self.assertEqual(
                    0,
                    loopctl.main(
                        [
                            "apply-event",
                            str(ledger_path),
                            str(event_path),
                            "--manifest",
                            str(manifest_path),
                            "--write",
                        ]
                    ),
                )
            materialized = loop_yaml.load_yaml(ledger_path)
            self.assertEqual(1, materialized["ledger"]["state_revision"]["sequence"])
            self.assertEqual("active", materialized["claims"][0]["status"])
            self.assertEqual([], loop_yaml.validate_ledger(materialized))

            for sequence, event_id, target, evidence in (
                (2, "start-1", "in_progress", {}),
                (
                    3,
                    "review-1",
                    "reviewing",
                    {
                        "verification": {"status": "passed", "artifacts": ["test-output"]},
                        "review": {"status": "required", "artifacts": ["diff"]},
                        "acceptance": {"status": "not_required", "artifact": ""},
                    },
                ),
            ):
                current = loop_yaml.load_yaml(ledger_path)
                transition = {
                    "sequence": sequence,
                    "event_id": event_id,
                    "occurred_at": f"2026-07-10T00:0{sequence}:00Z",
                    "actor": "worker-1",
                    "type": "task_transition",
                    "task_id": "T1",
                    "idempotency_key": event_id,
                    "expected_state_revision": sequence - 1,
                    "previous_event_hash": current["ledger"]["state_revision"]["last_event_hash"],
                    "payload": {
                        "target_status": target,
                        "fencing_token": claim["fencing_token"],
                        "evidence": evidence,
                    },
                }
                transition["event_hash"] = loop_core.calculate_event_hash(transition)
                event_path.write_text(loop_yaml.dump_yaml(transition), encoding="utf-8")
                with redirect_stdout(StringIO()):
                    self.assertEqual(
                        0,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                        ),
                    )
            final = loop_yaml.load_yaml(ledger_path)
            self.assertEqual("reviewing", final["tasks"][0]["status"])
            self.assertEqual("active", final["claims"][0]["status"])
            self.assertEqual(
                [],
                loop_yaml.semantic_audit(
                    final, loop_yaml.manifest_definitions(loop_yaml.load_yaml(manifest_path))
                ),
            )

    def test_live_future_claim_acquisition_rejects_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            document = valid_v2()
            manifest_path = write_contract(root, document)
            claim = {
                "task_id": "T1",
                "status": "active",
                "owner": {"type": "subagent", "id": "worker-1"},
                "fencing_token": {"generation": 1, "nonce": "future"},
                "expected_state_revision": 0,
                "source_revision": {
                    field: document["ledger"]["source_revision"][field]
                    for field in (
                        "branch",
                        "head_sha",
                        "spec_sha256",
                        "task_manifest_sha256",
                    )
                },
                "claimed_at": "2099-07-10T00:00:00Z",
                "lease_expires_at": "2099-07-10T00:10:00Z",
            }
            event = {
                "sequence": 1,
                "event_id": "future-claim",
                "occurred_at": "2099-07-10T00:00:00Z",
                "actor": "worker-1",
                "type": "claim_acquired",
                "task_id": "T1",
                "idempotency_key": "future-claim",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"claim": claim},
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            original = ledger_path.read_bytes()

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
            self.assertIn("later than trusted current time", output.getvalue())
            self.assertEqual(original, ledger_path.read_bytes())

    def test_live_future_claim_expiry_rejects_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            document = valid_v2()
            manifest_path = write_contract(root, document)
            definitions = loop_yaml.manifest_definitions(
                loop_yaml.load_yaml(manifest_path),
                expected_objective_id=document["ledger"]["objective_id"],
            )
            state = loop_yaml.state_from_ledger(document, definitions)
            claim = {
                "task_id": "T1",
                "status": "active",
                "owner": {"type": "subagent", "id": "worker-1"},
                "fencing_token": {"generation": 1, "nonce": "expiry"},
                "expected_state_revision": 0,
                "source_revision": copy.deepcopy(state["source_revision"]),
                "claimed_at": "2026-07-10T00:00:00Z",
                "lease_expires_at": "2098-07-10T00:00:00Z",
            }
            acquired = {
                "sequence": 1,
                "event_id": "claim-for-expiry",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "worker-1",
                "type": "claim_acquired",
                "task_id": "T1",
                "idempotency_key": "claim-for-expiry",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"claim": claim},
            }
            acquired["event_hash"] = loop_core.calculate_event_hash(acquired)
            state, _ = loop_core.replay_event(state, acquired)
            document = loop_yaml.update_ledger_view(document, state)
            expiry = {
                "sequence": 2,
                "event_id": "future-expiry",
                "occurred_at": "2099-07-10T00:00:00Z",
                "actor": "coordinator",
                "type": "claim_expired",
                "task_id": "T1",
                "idempotency_key": "future-expiry",
                "expected_state_revision": 1,
                "previous_event_hash": acquired["event_hash"],
                "payload": {
                    "fencing_token": claim["fencing_token"],
                    "blocker": {"reason": "lease expired"},
                },
            }
            expiry["event_hash"] = loop_core.calculate_event_hash(expiry)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(loop_yaml.dump_yaml(expiry), encoding="utf-8")
            original = ledger_path.read_bytes()

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                )
            self.assertIn("later than trusted current time", output.getvalue())
            self.assertEqual(original, ledger_path.read_bytes())

    def test_live_claim_expiry_materializes_a_replayable_event(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            document = valid_v2()
            manifest_path = write_contract(root, document)
            definitions = loop_yaml.manifest_definitions(
                loop_yaml.load_yaml(manifest_path),
                expected_objective_id=document["ledger"]["objective_id"],
            )
            state = loop_yaml.state_from_ledger(document, definitions)
            claim = {
                "task_id": "T1",
                "status": "active",
                "owner": {"type": "subagent", "id": "worker-1"},
                "fencing_token": {"generation": 1, "nonce": "replayable"},
                "expected_state_revision": 0,
                "source_revision": copy.deepcopy(state["source_revision"]),
                "claimed_at": "2026-07-10T00:00:00Z",
                "lease_expires_at": "2026-07-10T00:02:00Z",
            }
            acquired = {
                "sequence": 1,
                "event_id": "claim-before-expiry",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "worker-1",
                "type": "claim_acquired",
                "task_id": "T1",
                "idempotency_key": "claim-before-expiry",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"claim": claim},
            }
            acquired["event_hash"] = loop_core.calculate_event_hash(acquired)
            state, _ = loop_core.replay_event(state, acquired)
            document = loop_yaml.update_ledger_view(document, state)
            expiry = {
                "sequence": 2,
                "event_id": "replayable-expiry",
                "occurred_at": claim["lease_expires_at"],
                "actor": "coordinator",
                "type": "claim_expired",
                "task_id": "T1",
                "idempotency_key": "replayable-expiry",
                "expected_state_revision": 1,
                "previous_event_hash": acquired["event_hash"],
                "payload": {
                    "fencing_token": claim["fencing_token"],
                    "blocker": {"reason": "lease expired"},
                },
            }
            expiry["event_hash"] = loop_core.calculate_event_hash(expiry)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(loop_yaml.dump_yaml(expiry), encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                        repo_root=root,
                    ),
                    output.getvalue(),
                )
            materialized = loop_yaml.load_yaml(ledger_path)
            self.assertEqual("expired", materialized["claims"][0]["status"])
            self.assertEqual([], loop_yaml.semantic_audit(materialized, definitions))

    def test_semantic_audit_detects_missing_gate_materialization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            event = {
                "sequence": 1,
                "event_id": "gate-1",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "maintainer",
                "type": "gate_updated",
                "task_id": "",
                "idempotency_key": "gate-1",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"gate": "publish", "required": True, "reason": "approval", "status": "pending", "evidence": ""},
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            document["events"] = [event]
            document["ledger"]["state_revision"] = {"sequence": 1, "last_event_hash": event["event_hash"]}
            self.assertTrue(
                any("human gate" in item for item in loop_yaml.semantic_audit(document, loop_yaml.manifest_definitions(loop_yaml.load_yaml(manifest_path))))
            )

    def test_apply_event_serializes_nested_evidence_and_blocker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event = {
                "sequence": 1,
                "event_id": "block-1",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "maintainer",
                "type": "task_transition",
                "task_id": "T1",
                "idempotency_key": "block-1",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {
                    "target_status": "blocked",
                    "evidence": {
                        "verification": {"status": "not_run", "artifacts": []},
                        "review": {"status": "not_required", "artifacts": []},
                        "acceptance": {"status": "not_required", "artifact": ""},
                    },
                    "blocker": {"kind": "human-decision", "reason": "need human"},
                },
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            with redirect_stdout(StringIO()):
                self.assertEqual(
                    0,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                    ),
                )
            materialized = loop_yaml.load_yaml(ledger_path)["tasks"][0]
            self.assertEqual("blocked", materialized["status"])
            self.assertEqual("need human", materialized["blocker"]["reason"])
            self.assertEqual("not_run", materialized["evidence"]["verification"]["status"])

    def test_semantic_audit_rejects_illegal_direct_acceptance(self):
        document = valid_v2()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            manifest_path = write_contract(root, document)
            event = {
                "sequence": 1,
                "event_id": "accept-1",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "maintainer",
                "type": "task_transition",
                "task_id": "T1",
                "idempotency_key": "accept-1",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {
                    "target_status": "accepted",
                    "evidence": {
                        "verification": {"status": "passed", "artifacts": ["test"]},
                        "review": {"status": "passed", "artifacts": ["review"]},
                        "acceptance": {"status": "satisfied", "artifact": "approval"},
                    },
                },
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            document["events"] = [event]
            document["ledger"]["state_revision"] = {"sequence": 1, "last_event_hash": event["event_hash"]}
            document["tasks"][0] = {
                "id": "T1",
                "status": "accepted",
                "evidence": event["payload"]["evidence"],
            }
            self.assertTrue(
                any(
                    "replay failed" in item
                    for item in loop_yaml.semantic_audit(
                        document,
                        loop_yaml.manifest_definitions(loop_yaml.load_yaml(manifest_path)),
                    )
                )
            )

    def test_write_lock_prevents_two_revision_zero_writers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "ledger.yaml"
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_paths = []
            for suffix in ("a", "b"):
                event = {
                    "sequence": 1,
                    "event_id": suffix,
                    "occurred_at": "2026-07-10T00:00:00Z",
                    "actor": "maintainer",
                    "type": "gate_updated",
                    "task_id": "",
                    "idempotency_key": suffix,
                    "expected_state_revision": 0,
                    "previous_event_hash": "",
                    "payload": {"gate": suffix, "required": True, "reason": "test", "status": "pending", "evidence": ""},
                }
                event["event_hash"] = loop_core.calculate_event_hash(event)
                event_path = root / f"{suffix}.yaml"
                event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
                event_paths.append(event_path)
            results: list[int] = []

            def apply(event_path: pathlib.Path) -> None:
                results.append(
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=True,
                    )
                )

            threads = [threading.Thread(target=apply, args=(path,)) for path in event_paths]
            with mock.patch.object(loopctl, "render"):
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
            self.assertEqual([0, 1], sorted(results))
            self.assertEqual(1, loop_yaml.load_yaml(ledger_path)["ledger"]["state_revision"]["sequence"])

    def test_apply_event_rejects_malformed_event_history_before_digesting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            document["events"] = {"forged": "scalar"}
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event_path.write_text(
                loop_yaml.dump_yaml(
                    {
                        "sequence": 1,
                        "event_id": "probe",
                        "occurred_at": "2026-07-10T00:00:00Z",
                        "actor": "maintainer",
                        "type": "gate_updated",
                        "task_id": "",
                        "idempotency_key": "probe",
                        "expected_state_revision": 0,
                        "previous_event_hash": "",
                        "payload": {"gate": "publish", "status": "pending"},
                        "event_hash": "invalid-but-unreached",
                    }
                ),
                encoding="utf-8",
            )
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    1,
                    loopctl.command_apply_event(
                        ledger_path,
                        event_path,
                        manifest_path=manifest_path,
                        write=False,
                    ),
                )
            self.assertIn("events must be a list", output.getvalue())

    def test_apply_event_reports_committed_write_when_directory_fsync_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event = {
                "sequence": 1,
                "event_id": "pending-gate",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "maintainer",
                "type": "gate_updated",
                "task_id": "",
                "idempotency_key": "pending-gate",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {
                    "gate": "publish",
                    "required": True,
                    "reason": "approval",
                    "status": "pending",
                    "evidence": "",
                },
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            real_fsync = loopctl.os.fsync
            call_count = 0

            def fail_directory_fsync(descriptor: int) -> None:
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise OSError("simulated directory fsync failure")
                real_fsync(descriptor)

            output = StringIO()
            with mock.patch.object(loopctl.os, "fsync", side_effect=fail_directory_fsync):
                with redirect_stdout(output):
                    self.assertEqual(
                        3,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                        ),
                    )
            result = json.loads(output.getvalue())
            self.assertEqual("applied-durability-uncertain", result["status"])
            self.assertTrue(result["writes_performed"])
            self.assertIn("do not blindly retry", result["durability_warning"])
            self.assertEqual(
                1,
                loop_yaml.load_yaml(ledger_path)["ledger"]["state_revision"]["sequence"],
            )

    def test_apply_event_revalidates_source_immediately_before_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            document = valid_v2()
            manifest_path = write_contract(root, document)
            ledger_path = root / "ledger.yaml"
            event_path = root / "event.yaml"
            ledger_path.write_text(loop_yaml.dump_yaml(document), encoding="utf-8")
            event = {
                "sequence": 1,
                "event_id": "source-race",
                "occurred_at": "2026-07-10T00:00:00Z",
                "actor": "maintainer",
                "type": "gate_updated",
                "task_id": "",
                "idempotency_key": "source-race",
                "expected_state_revision": 0,
                "previous_event_hash": "",
                "payload": {"gate": "publish", "status": "pending"},
            }
            event["event_hash"] = loop_core.calculate_event_hash(event)
            event_path.write_text(loop_yaml.dump_yaml(event), encoding="utf-8")
            original_verify = loopctl._verify_git_source
            calls = 0

            def verify_then_drift(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise loop_yaml.LedgerValidationError("git HEAD source revision mismatch")
                return original_verify(*args, **kwargs)

            output = StringIO()
            with mock.patch.object(
                loopctl, "_verify_git_source", side_effect=verify_then_drift
            ):
                with redirect_stdout(output):
                    self.assertEqual(
                        1,
                        loopctl.command_apply_event(
                            ledger_path,
                            event_path,
                            manifest_path=manifest_path,
                            write=True,
                            repo_root=root,
                        ),
                    )
            self.assertEqual(2, calls)
            self.assertIn("source revision changed before commit", output.getvalue())
            self.assertEqual(
                0,
                loop_yaml.load_yaml(ledger_path)["ledger"]["state_revision"]["sequence"],
            )


if __name__ == "__main__":
    unittest.main()
