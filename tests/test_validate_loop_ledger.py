import importlib.util
import copy
import hashlib
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-loop-ledger.py"

spec = importlib.util.spec_from_file_location("validate_loop_ledger", SCRIPT)
validate_loop_ledger = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_loop_ledger)


class ValidateLoopLedgerTests(unittest.TestCase):
    def test_project_validator_rejects_non_commit_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Loop Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(root), "config", "user.email", "loop@example.invalid"],
                check=True,
            )
            spec_path = root / "loop-spec.md"
            manifest_path = root / "task-manifest.yaml"
            ledger_path = root / "loop-state-ledger.yaml"
            spec_path.write_text("# Spec\n", encoding="utf-8")
            manifest_path.write_text("project: {}\n", encoding="utf-8")
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "initial"], check=True
            )
            fake_head = "a" * 40
            (root / ".git" / "refs" / "heads" / "main").write_text(
                fake_head + "\n", encoding="ascii"
            )
            document = {
                "ledger": {
                    "schema_version": 2,
                    "objective_id": "test",
                    "loop_spec": spec_path.name,
                    "task_manifest": manifest_path.name,
                    "source_revision": {
                        "branch": "main",
                        "head_sha": fake_head,
                        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                        "task_manifest_sha256": hashlib.sha256(
                            manifest_path.read_bytes()
                        ).hexdigest(),
                    },
                },
                "current_loop": {"lifecycle": "active"},
                "events": [{"type": "task_transition"}],
            }
            with (
                mock.patch.object(validate_loop_ledger, "ROOT", root),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "load_yaml", return_value=document
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "validate_ledger", return_value=[]
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "manifest_definitions", return_value={}
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "semantic_audit", return_value=[]
                ),
            ):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(
                any("could not verify git source revision" in error for error in errors)
            )

    def test_project_validator_rejects_enclosing_repository_core_worktree_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            outer = pathlib.Path(directory)
            snapshot = outer / "snapshot"
            snapshot.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main", str(outer)], check=True)
            subprocess.run(
                ["git", "-C", str(outer), "config", "user.name", "Loop Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(outer), "config", "user.email", "loop@example.invalid"],
                check=True,
            )
            spec_path = snapshot / "loop-spec.md"
            manifest_path = snapshot / "task-manifest.yaml"
            ledger_path = snapshot / "loop-state-ledger.yaml"
            spec_path.write_text("# Spec\n", encoding="utf-8")
            manifest_path.write_text("project: {}\n", encoding="utf-8")
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(outer), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(outer), "commit", "-q", "-m", "initial"], check=True
            )
            subprocess.run(
                ["git", "-C", str(outer), "config", "--local", "core.worktree", str(snapshot)],
                check=True,
            )
            head = subprocess.run(
                ["git", "-C", str(outer), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            document = {
                "ledger": {
                    "schema_version": 2,
                    "objective_id": "test",
                    "loop_spec": spec_path.name,
                    "task_manifest": manifest_path.name,
                    "source_revision": {
                        "branch": "main",
                        "head_sha": head,
                        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                        "task_manifest_sha256": hashlib.sha256(
                            manifest_path.read_bytes()
                        ).hexdigest(),
                    },
                },
                "current_loop": {"lifecycle": "active"},
                "events": [{"type": "task_transition"}],
            }
            with (
                mock.patch.object(validate_loop_ledger, "ROOT", snapshot),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "load_yaml", return_value=document
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "validate_ledger", return_value=[]
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "manifest_definitions", return_value={}
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "semantic_audit", return_value=[]
                ),
            ):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(
                any("repository root mismatch" in error for error in errors)
            )

    def test_project_validator_ignores_repository_selector_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            target = base / "target"
            decoy = base / "decoy"
            target.mkdir()
            decoy.mkdir()
            for root in (target, decoy):
                subprocess.run(
                    ["git", "init", "-q", "-b", "main", str(root)], check=True
                )
                subprocess.run(
                    ["git", "-C", str(root), "config", "user.name", "Loop Test"],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(root), "config", "user.email", "loop@example.invalid"],
                    check=True,
                )
                (root / "tracked.txt").write_text(root.name + "\n", encoding="utf-8")
                subprocess.run(
                    ["git", "-C", str(root), "add", "tracked.txt"], check=True
                )
                subprocess.run(
                    ["git", "-C", str(root), "commit", "-q", "-m", "initial"],
                    check=True,
                )
            decoy_source = subprocess.run(
                ["git", "-C", str(decoy), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(decoy), "commit", "-q", "--allow-empty", "-m", "later"],
                check=True,
            )
            decoy_head = subprocess.run(
                ["git", "-C", str(decoy), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            spec_path = target / "loop-spec.md"
            manifest_path = target / "task-manifest.yaml"
            ledger_path = target / "loop-state-ledger.yaml"
            spec_path.write_text("# Spec\n", encoding="utf-8")
            manifest_path.write_text("project: {}\n", encoding="utf-8")
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            document = {
                "ledger": {
                    "schema_version": 2,
                    "objective_id": "test",
                    "loop_spec": spec_path.name,
                    "task_manifest": manifest_path.name,
                    "source_revision": {
                        "branch": "main",
                        "head_sha": decoy_source,
                        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                        "task_manifest_sha256": hashlib.sha256(
                            manifest_path.read_bytes()
                        ).hexdigest(),
                    },
                },
                "current_loop": {"lifecycle": "complete"},
                "events": [{"type": "objective_completed"}],
            }
            with (
                mock.patch.object(validate_loop_ledger, "ROOT", target),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "load_yaml", return_value=document
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "validate_ledger", return_value=[]
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "manifest_definitions", return_value={}
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml, "semantic_audit", return_value=[]
                ),
                mock.patch.dict(
                    os.environ, {"GIT_DIR": str(decoy / ".git")}, clear=False
                ),
            ):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(
                any("git HEAD source revision mismatch" in error for error in errors)
            )
            self.assertNotEqual(
                decoy_head,
                subprocess.run(
                    ["git", "-C", str(target), "rev-parse", "HEAD"],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
            )

    def test_project_validator_terminal_ancestor_matrix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(
                ["git", "-C", str(root), "config", "user.name", "Loop Test"],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "config",
                    "user.email",
                    "loop@example.invalid",
                ],
                check=True,
            )
            spec_path = root / "loop-spec.md"
            manifest_path = root / "task-manifest.yaml"
            ledger_path = root / "loop-state-ledger.yaml"
            spec_path.write_text("# Spec\n", encoding="utf-8")
            manifest_path.write_text("project: {}\n", encoding="utf-8")
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(root), "add", spec_path.name, manifest_path.name],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "source"],
                check=True,
            )
            source_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            branch = subprocess.run(
                ["git", "-C", str(root), "branch", "--show-current"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (root / "later.txt").write_text("later\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "later.txt"], check=True)
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "-m", "later"],
                check=True,
            )
            document = {
                "ledger": {
                    "schema_version": 2,
                    "objective_id": "test",
                    "loop_spec": spec_path.name,
                    "task_manifest": manifest_path.name,
                    "source_revision": {
                        "branch": branch,
                        "head_sha": source_head,
                        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
                        "task_manifest_sha256": hashlib.sha256(
                            manifest_path.read_bytes()
                        ).hexdigest(),
                    },
                },
                "current_loop": {"lifecycle": "complete"},
                "events": [{"type": "objective_completed"}],
            }

            def validate(candidate):
                with (
                    mock.patch.object(validate_loop_ledger, "ROOT", root),
                    mock.patch.object(
                        validate_loop_ledger.loop_yaml,
                        "load_yaml",
                        return_value=candidate,
                    ),
                    mock.patch.object(
                        validate_loop_ledger.loop_yaml,
                        "validate_ledger",
                        return_value=[],
                    ),
                    mock.patch.object(
                        validate_loop_ledger.loop_yaml,
                        "manifest_definitions",
                        return_value={},
                    ),
                    mock.patch.object(
                        validate_loop_ledger.loop_yaml,
                        "semantic_audit",
                        return_value=[],
                    ),
                ):
                    return validate_loop_ledger.validate_project_ledger(ledger_path)

            self.assertEqual([], validate(document))
            active = copy.deepcopy(document)
            active["current_loop"]["lifecycle"] = "active"
            self.assertTrue(
                any("git HEAD source revision mismatch" in error for error in validate(active))
            )
            nonterminal = copy.deepcopy(document)
            nonterminal["events"] = [{"type": "task_transition"}]
            self.assertTrue(
                any(
                    "git HEAD source revision mismatch" in error
                    for error in validate(nonterminal)
                )
            )
            malformed = copy.deepcopy(document)
            malformed["ledger"]["source_revision"]["head_sha"] = "A" * 40
            self.assertTrue(
                any(
                    "git HEAD source revision mismatch" in error
                    for error in validate(malformed)
                )
            )
            current_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "replace-source", source_head],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "--allow-empty", "-m", "diverged"],
                check=True,
            )
            diverged_head = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "replacement-target"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "commit", "-q", "--allow-empty", "-m", "replacement"],
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
            replacement_document = copy.deepcopy(document)
            replacement_document["ledger"]["source_revision"]["head_sha"] = diverged_head
            self.assertTrue(
                any(
                    "git HEAD source revision mismatch" in error
                    for error in validate(replacement_document)
                )
            )
            subprocess.run(
                ["git", "-C", str(root), "replace", "-d", current_head],
                check=True,
                capture_output=True,
            )
            grafts = root / ".git" / "info" / "grafts"
            grafts.write_text(
                f"{current_head} {diverged_head}\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any(
                    "git HEAD source revision mismatch" in error
                    for error in validate(replacement_document)
                )
            )
            grafts.unlink()
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "-c", "wrong-branch"],
                check=True,
            )
            self.assertEqual([], validate(document))
            active_wrong_branch = copy.deepcopy(document)
            active_wrong_branch["current_loop"]["lifecycle"] = "active"
            self.assertTrue(
                any(
                    "git branch source revision mismatch" in error
                    for error in validate(active_wrong_branch)
                )
            )
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", branch],
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(root),
                    "switch",
                    "-q",
                    "-c",
                    "exact-wrong-branch",
                    source_head,
                ],
                check=True,
            )
            self.assertTrue(
                any(
                    "git branch source revision mismatch" in error
                    for error in validate(document)
                )
            )
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", branch],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(root), "switch", "-q", "--detach"],
                check=True,
            )
            self.assertTrue(
                any(
                    "git branch source revision mismatch" in error
                    for error in validate(document)
                )
            )

    def test_project_validator_rejects_contract_paths_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            root = base / "repo"
            root.mkdir()
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text("ledger: {}\n", encoding="utf-8")
            external = base / "external.yaml"
            external.write_text("project: {}\n", encoding="utf-8")
            document = {
                "ledger": {
                    "schema_version": 2,
                    "objective_id": "test",
                    "loop_spec": str(external),
                    "task_manifest": str(external),
                    "source_revision": {},
                }
            }
            with (
                mock.patch.object(validate_loop_ledger, "ROOT", root),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml,
                    "load_yaml",
                    return_value=document,
                ),
                mock.patch.object(
                    validate_loop_ledger.loop_yaml,
                    "validate_ledger",
                    return_value=[],
                ),
            ):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(any("task manifest must stay within" in error for error in errors))
            self.assertTrue(any("loop spec must stay within" in error for error in errors))

    def test_project_validator_rejects_valid_v1_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            ledger_path = root / "loop-state-ledger.yaml"
            ledger_path.write_text(
                """ledger:\n  schema_version: 1\n  objective_id: test\n  objective: test\n  source_revision:\n    branch: branch\n    head_sha: abc\n    updated_at: 2026-07-10T00:00:00Z\ntasks:\n  - id: T1\n    status: ready\n    dependencies: []\n    evidence: {}\n""",
                encoding="utf-8",
            )
            with mock.patch.object(validate_loop_ledger, "ROOT", root):
                errors = validate_loop_ledger.validate_project_ledger(ledger_path)
            self.assertTrue(any("requires schema_version 2" in error for error in errors))

    def test_quoted_done_status_requires_passed_verification(self):
        block = """
  - id: "T1"
    status: "done"
    evidence:
      verification:
        status: "not_run"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertTrue(any("requires passed verification" in error for error in errors))

    def test_done_status_accepts_task_scoped_passed_verification(self):
        block = """
  - id: "T1"
    status: "done"
    evidence:
      verification:
        status: "passed"
      review:
        status: "not_required"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertEqual([], errors)

    def test_claimed_status_requires_claim_and_lease(self):
        block = """
  - id: "T1"
    status: "claimed"
    owner:
      type: "worker"
      id: "worker-1"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertTrue(any("requires owner and lease fields" in error for error in errors))

    def test_blocked_status_requires_non_placeholder_reason(self):
        block = """
  - id: "T1"
    status: "blocked"
    blocker:
      reason: "<reason-or-empty>"
"""
        errors = validate_loop_ledger.validate_task_block(pathlib.Path("ledger.yaml"), block)
        self.assertTrue(any("requires blocker reason" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
