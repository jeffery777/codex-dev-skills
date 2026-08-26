from __future__ import annotations

import ast
import copy
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate-exact-head-merge-review.py"
SPEC = importlib.util.spec_from_file_location("exact_head_merge_review", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)

BASE = "a" * 40
HEAD = "b" * 40
MERGE_BASE = "c" * 40
DIGEST = "d" * 64


def valid_payload() -> dict[str, object]:
    range_digest = review.canonical_range_identity_digest(
        "jeffery777/codex-dev-skills", 183, BASE, HEAD, MERGE_BASE
    )
    required_ci = [
        {
            "name": "Repository Validation",
            "status": "success",
            "head_sha": HEAD,
            "run_id": 123,
        }
    ]
    required_ci_policy = {
        "source": "github_ruleset",
        "reference": "main protection",
        "required_names": ["Repository Validation"],
    }
    receipt = {
        "repository": "jeffery777/codex-dev-skills",
        "pr_number": 183,
        "review_mode": "merge-review",
        "reviewed_base_sha": BASE,
        "reviewed_head_sha": HEAD,
        "reviewed_merge_base_sha": MERGE_BASE,
        "reviewed_diff_digest": range_digest,
        "receipt_authority": "advisory_review_evidence",
        "merge_authorized": False,
        "findings": {"must_fix_open": 0, "should_fix_open": 0, "nit_open": 0},
        "dispositions": [{"finding_id": "R183-CR-001", "severity": "MUST-FIX", "disposition": "fixed", "evidence": "commit dc4d8b7"}],
        "residual_risk": "GitHub platform state remains subject to final live readback.",
        "pre_commit_evidence": [{"kind": "code-review-deep", "evidence_id": "deep-review-dc4d8b7", "reviewed_content_digest": "e" * 64, "result": "no_findings", "applicability_rationale": "The final range retains the reviewed implementation boundary."}],
        "required_ci": required_ci,
        "required_ci_policy": required_ci_policy,
    }
    return {
        "contract": "exact-head-merge-review/v1",
        "receipt": receipt,
        "platform_snapshot": {
            "repository": "jeffery777/codex-dev-skills", "pr_number": 183,
            "base_sha": BASE, "head_sha": HEAD, "merge_base_sha": MERGE_BASE,
            "diff_digest": range_digest, "readback": {"source": "github", "confirmed": True},
            "state": "open", "draft": False, "mergeable": True, "receipt_id": 123,
            "receipt_url": "https://github.com/jeffery777/codex-dev-skills/pull/183#issuecomment-123",
            "platform_readback_at": "2026-08-25T12:00:00Z",
            "receipt_digest": review.canonical_receipt_digest(receipt),
            "required_ci": required_ci, "required_ci_policy": required_ci_policy,
            "unresolved_review_threads": 0,
        },
    }


def valid_v2_payload() -> dict[str, object]:
    findings = {"must_fix_open": 0, "should_fix_open": 0, "nit_open": 0}
    dispositions: list[dict[str, object]] = []
    threads_digest = review.canonical_digest([])
    findings_digest = review.canonical_digest(
        {"findings": findings, "dispositions": dispositions}
    )
    checks = [
        {
            "workflow_name": "Repository Validation",
            "workflow_run_id": 456,
            "workflow_attempt": 1,
            "workflow_id": 12,
            "workflow_path": ".github/workflows/repository-validation.yml",
            "event": "pull_request",
            "run_name_contract": "exact-pr-head/v1",
            "run_display_title": f"Repository Validation PR #185 @ {HEAD}",
            "workflow_blob_sha": "f" * 40,
            "check_context": "Validate repository",
            "head_sha": HEAD,
            "conclusion": "success",
            "details_url": "https://github.com/jeffery777/codex-dev-skills/actions/runs/456",
        }
    ]
    ci_policy = {
        "source": "repository_policy",
        "reference": ".github/exact-head-merge-readiness-policy.json",
        "required_workflows": [
            {
                "check_context": "Validate repository",
                "workflow_name": "Repository Validation",
                "workflow_id": 12,
                "workflow_path": ".github/workflows/repository-validation.yml",
                "event": "pull_request",
                "run_name_contract": "exact-pr-head/v1",
                "workflow_blob_sha": "f" * 40,
            }
        ],
    }
    range_identity_digest = review.canonical_range_identity_digest(
        "jeffery777/codex-dev-skills", 185, BASE, HEAD, MERGE_BASE
    )
    receipt = {
        "repository": "jeffery777/codex-dev-skills",
        "pr_number": 185,
        "receipt_sequence": 1,
        "review_mode": "merge-review-deep",
        "reviewed_base_sha": BASE,
        "reviewed_head_sha": HEAD,
        "reviewed_merge_base_sha": MERGE_BASE,
        "reviewed_range_identity_digest": range_identity_digest,
        "reviewed_review_threads_digest": threads_digest,
        "reviewed_findings_digest": findings_digest,
        "receipt_authority": "advisory_review_evidence",
        "merge_authorized": False,
        "findings": findings,
        "dispositions": dispositions,
        "residual_risk": "Platform state is re-read immediately before success.",
        "pre_commit_evidence": [],
        "required_ci": checks,
        "required_ci_policy": ci_policy,
    }
    return {
        "contract": "exact-head-merge-readiness/v2",
        "receipt": receipt,
        "platform_snapshot": {
            "repository": "jeffery777/codex-dev-skills",
            "pr_number": 185,
            "base_sha": BASE,
            "head_sha": HEAD,
            "merge_base_sha": MERGE_BASE,
            "range_identity_digest": range_identity_digest,
            "readback": {"source": "github", "confirmed": True},
            "state": "open",
            "draft": False,
            "mergeable": True,
            "receipt_id": 321,
            "receipt_url": "https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-321",
            "platform_readback_at": "2026-08-25T12:00:00Z",
            "receipt_digest": review.canonical_receipt_digest(receipt),
            "required_ci": copy.deepcopy(checks),
            "required_ci_policy": copy.deepcopy(ci_policy),
            "unresolved_review_threads": 0,
            "review_threads_digest": threads_digest,
            "findings_digest": findings_digest,
        },
        "gate": {
            "workflow_name": "Exact-Head Merge Readiness Controller",
            "workflow_run_id": 900,
            "check_context": "Exact-Head Merge Readiness",
            "check_run_id": 901,
            "check_app_id": 100001,
            "check_app_slug": "exact-head-gate",
            "details_url": "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
            "head_sha": HEAD,
            "conclusion": "success",
        },
    }


class ExactHeadMergeReviewTests(unittest.TestCase):
    def assert_invalid(self, payload: object, message: str) -> None:
        with self.assertRaisesRegex(review.ExactHeadMergeReviewError, message):
            review.validate_payload(payload)

    def write_payload(self, payload: object) -> pathlib.Path:
        temporary = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
        self.addCleanup(pathlib.Path(temporary.name).unlink, missing_ok=True)
        with temporary:
            json.dump(payload, temporary)
        return pathlib.Path(temporary.name)

    def test_happy_path(self) -> None:
        self.assertEqual(
            ("jeffery777/codex-dev-skills", 183), review.validate_payload(valid_payload())
        )

    def test_v1_and_v2_contracts_are_explicitly_supported(self) -> None:
        self.assertEqual(
            ("jeffery777/codex-dev-skills", 183),
            review.validate_payload(valid_payload()),
        )
        self.assertEqual(
            ("jeffery777/codex-dev-skills", 185),
            review.validate_payload(valid_v2_payload()),
        )

    def test_v2_separates_check_workflow_run_and_app_identities(self) -> None:
        payload = valid_v2_payload()
        payload["receipt"]["required_ci"][0]["workflow_run_id"] = 999  # type: ignore[index]
        payload["receipt"]["required_ci"][0]["details_url"] = (  # type: ignore[index]
            "https://github.com/jeffery777/codex-dev-skills/actions/runs/999"
        )
        payload["platform_snapshot"]["required_ci"] = copy.deepcopy(  # type: ignore[index]
            payload["receipt"]["required_ci"]  # type: ignore[index]
        )
        payload["platform_snapshot"]["receipt_digest"] = review.canonical_receipt_digest(  # type: ignore[index]
            payload["receipt"]  # type: ignore[index]
        )
        self.assertEqual(
            ("jeffery777/codex-dev-skills", 185), review.validate_payload(payload)
        )
        payload["gate"]["check_app_id"] = 0  # type: ignore[index]
        self.assert_invalid(payload, "gate.check_app_id must be a positive integer")

    def test_v2_forbids_gate_self_dependency_and_all_drift(self) -> None:
        payload = valid_v2_payload()
        payload["receipt"]["required_ci"][0]["check_context"] = review.GATE_CONTEXT  # type: ignore[index]
        self.assert_invalid(payload, "must not contain the readiness gate context")
        for field in (
            "base_sha", "head_sha", "merge_base_sha", "range_identity_digest",
            "review_threads_digest", "findings_digest",
        ):
            with self.subTest(field=field):
                payload = valid_v2_payload()
                payload["platform_snapshot"][field] = (  # type: ignore[index]
                    "e" * 40 if field.endswith("sha") else "e" * 64
                )
                self.assert_invalid(payload, "does not match")

    def test_v2_receipt_and_gate_are_strict_and_fail_closed(self) -> None:
        payload = valid_v2_payload()
        payload["receipt"]["unexpected"] = True  # type: ignore[index]
        self.assert_invalid(payload, "unknown critical field")
        payload = valid_v2_payload()
        payload["gate"]["conclusion"] = "neutral"  # type: ignore[index]
        self.assert_invalid(payload, "gate.conclusion must equal 'success'")
        payload = valid_v2_payload()
        payload["platform_snapshot"]["unresolved_review_threads"] = 1  # type: ignore[index]
        self.assert_invalid(payload, "unresolved_review_threads must be zero")
        payload = valid_v2_payload()
        payload["gate"]["details_url"] = "https://github.com/other/repository/actions/runs/900"  # type: ignore[index]
        self.assert_invalid(payload, "gate.details_url does not bind repository")
        payload = valid_v2_payload()
        payload["receipt"]["required_ci"][0]["details_url"] = (  # type: ignore[index]
            "https://github.com/other/repository/actions/runs/456"
        )
        self.assert_invalid(payload, "details_url does not bind repository")
        payload = valid_v2_payload()
        payload["receipt"]["receipt_sequence"] = review.MAX_RECEIPT_SEQUENCE + 1  # type: ignore[index]
        self.assert_invalid(payload, "receipt.receipt_sequence must not exceed")

    def test_range_identity_digest_is_deterministic_and_not_caller_chosen(self) -> None:
        self.assertEqual(
            "817185acb545be344ddb58ad771f08d1862b6df9c6a638001766028ad6b53f5a",
            review.canonical_range_identity_digest(
                "jeffery777/codex-dev-skills", 183, BASE, HEAD, MERGE_BASE
            ),
        )
        payload = valid_payload()
        payload["receipt"]["reviewed_head_sha"] = "f" * 40  # type: ignore[index]
        payload["platform_snapshot"]["head_sha"] = "f" * 40  # type: ignore[index]
        self.assert_invalid(payload, "canonical range identity digest")

    def test_validator_is_offline_and_has_no_dynamic_code_path(self) -> None:
        tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
        imports = set()
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                calls.add(node.func.id)
        self.assertFalse(imports & {"subprocess", "socket", "urllib", "requests", "http"})
        self.assertFalse(calls & {"__import__", "compile", "eval", "exec"})

    def test_stale_base_head_and_merge_base_fail_closed(self) -> None:
        for field, message in (
            ("base_sha", "base_sha does not match"),
            ("head_sha", "head_sha does not match"),
            ("merge_base_sha", "merge_base_sha does not match"),
        ):
            with self.subTest(field=field):
                payload = valid_payload()
                payload["platform_snapshot"][field] = "e" * 40  # type: ignore[index]
                self.assert_invalid(payload, message)

    def test_stale_diff_digest_fails_closed(self) -> None:
        payload = valid_payload()
        payload["platform_snapshot"]["diff_digest"] = "e" * 64  # type: ignore[index]
        self.assert_invalid(payload, "diff_digest does not match")

    def test_missing_or_non_success_ci_fails_closed(self) -> None:
        payload = valid_payload()
        payload["platform_snapshot"]["required_ci"] = []  # type: ignore[index]
        self.assert_invalid(payload, "must contain at least one")
        payload = valid_payload()
        payload["platform_snapshot"]["required_ci"][0]["status"] = "queued"  # type: ignore[index]
        self.assert_invalid(payload, "status must equal 'success'")
        payload = valid_payload()
        payload["platform_snapshot"]["required_ci"][0]["head_sha"] = BASE  # type: ignore[index]
        self.assert_invalid(payload, "required_ci\\[0\\].head_sha does not match")

    def test_required_ci_policy_and_receipt_copy_are_sealed(self) -> None:
        payload = valid_payload()
        del payload["receipt"]["required_ci_policy"]["required_names"]  # type: ignore[index]
        self.assert_invalid(payload, "missing required field: required_names")
        payload = valid_payload()
        payload["receipt"]["required_ci_policy"]["required_names"] = ["Optional Scan"]  # type: ignore[index]
        self.assert_invalid(payload, "must exactly equal")
        payload = valid_payload()
        optional_ci = {
            "name": "Optional Scan",
            "status": "success",
            "head_sha": HEAD,
            "run_id": 456,
        }
        payload["receipt"]["required_ci"].append(optional_ci)  # type: ignore[index]
        self.assert_invalid(payload, "must exactly equal")
        payload = valid_payload()
        snapshot_checks = copy.deepcopy(payload["platform_snapshot"]["required_ci"])  # type: ignore[index]
        snapshot_checks[0]["run_id"] = 124
        payload["platform_snapshot"]["required_ci"] = snapshot_checks  # type: ignore[index]
        self.assert_invalid(payload, "does not exactly match")
        payload = valid_payload()
        payload["receipt"]["required_ci"][0]["run_id"] = 124  # type: ignore[index]
        self.assert_invalid(payload, "does not match canonical receipt digest")

    def test_dispositions_residual_risk_and_reused_evidence_are_strict(self) -> None:
        payload = valid_payload()
        payload["receipt"]["dispositions"][0]["evidence"] = ""  # type: ignore[index]
        self.assert_invalid(payload, "evidence must be a non-empty string")
        payload = valid_payload()
        payload["receipt"]["dispositions"][0]["unexpected"] = "value"  # type: ignore[index]
        self.assert_invalid(payload, "unknown critical field")
        payload = valid_payload()
        payload["receipt"]["dispositions"][0]["severity"] = "BLOCKER"  # type: ignore[index]
        self.assert_invalid(payload, "severity is invalid")
        payload = valid_payload()
        payload["receipt"]["dispositions"][0]["severity"] = []  # type: ignore[index]
        self.assert_invalid(payload, "severity must be a non-empty string")
        payload = valid_payload()
        payload["receipt"]["residual_risk"] = ""  # type: ignore[index]
        self.assert_invalid(payload, "residual_risk must be a non-empty string")
        payload = valid_payload()
        evidence = payload["receipt"]["pre_commit_evidence"]  # type: ignore[index]
        evidence.append(copy.deepcopy(evidence[0]))  # type: ignore[union-attr,index]
        self.assert_invalid(payload, "duplicate evidence_id")
        payload = valid_payload()
        payload["receipt"]["pre_commit_evidence"][0]["result"] = "passed"  # type: ignore[index]
        self.assert_invalid(payload, "result must equal 'no_findings'")
        payload = valid_payload()
        del payload["receipt"]["pre_commit_evidence"]  # type: ignore[index]
        self.assert_invalid(payload, "receipt is missing required field: pre_commit_evidence")

    def test_unresolved_threads_fail_closed(self) -> None:
        payload = valid_payload()
        payload["platform_snapshot"]["unresolved_review_threads"] = 1  # type: ignore[index]
        self.assert_invalid(payload, "unresolved_review_threads must be zero")

    def test_pre_commit_receipt_fails_closed(self) -> None:
        payload = valid_payload()
        payload["receipt"]["review_mode"] = "pre_commit"  # type: ignore[index]
        self.assert_invalid(payload, "review_mode must be one of")

    def test_open_findings_fail_closed(self) -> None:
        for name in ("must_fix_open", "should_fix_open", "nit_open"):
            with self.subTest(name=name):
                payload = valid_payload()
                payload["receipt"]["findings"][name] = 1  # type: ignore[index]
                self.assert_invalid(payload, f"{name} must be zero")

    def test_receipt_cannot_authorize_merge(self) -> None:
        payload = valid_payload()
        payload["receipt"]["merge_authorized"] = True  # type: ignore[index]
        self.assert_invalid(payload, "merge_authorized must be false")

    def test_duplicate_keys_fail_closed(self) -> None:
        duplicate = b'{"contract":"exact-head-merge-review/v1","contract":"exact-head-merge-review/v1"}'
        with self.assertRaisesRegex(review.ExactHeadMergeReviewError, "duplicate key"):
            review.load_json(duplicate)

    def test_strict_utf8_and_bounded_stdin_reader(self) -> None:
        with self.assertRaisesRegex(review.ExactHeadMergeReviewError, "strict UTF-8"):
            review.load_json(b"\xff")
        self.assertEqual(b"{}", review.read_input("-", io.BytesIO(b"{}")))
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(review.ExactHeadMergeReviewError, "regular"):
                review.read_input(directory)

    @unittest.skipUnless(hasattr(__import__("os"), "mkfifo"), "FIFO requires POSIX")
    def test_fifo_is_rejected_without_blocking(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as directory:
            fifo = pathlib.Path(directory) / "input.fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(review.ExactHeadMergeReviewError, "regular"):
                review.read_input(str(fifo))

    def test_regular_file_requires_nonblocking_and_nofollow_support(self) -> None:
        with mock.patch.object(review.os, "O_NONBLOCK", None):
            with self.assertRaisesRegex(
                review.ExactHeadMergeReviewError, "nonblocking support"
            ):
                review.read_input("unused.json")

    def test_malformed_input_and_unknown_fields_fail_closed(self) -> None:
        with self.assertRaisesRegex(review.ExactHeadMergeReviewError, "not valid JSON"):
            review.load_json(b"{")
        payload = valid_payload()
        payload["receipt"]["unexpected"] = "value"  # type: ignore[index]
        self.assert_invalid(payload, "unknown critical field")

    def test_required_top_level_and_platform_receipt_readback_fields_fail_closed(self) -> None:
        payload = valid_payload()
        del payload["receipt"]
        self.assert_invalid(payload, "input is missing required field: receipt")
        for field in ("receipt_id", "receipt_url", "readback"):
            with self.subTest(field=field):
                payload = valid_payload()
                del payload["platform_snapshot"][field]  # type: ignore[index]
                self.assert_invalid(
                    payload,
                    f"platform_snapshot is missing required field: {field}",
                )

    def test_identity_and_readback_mismatch_fail_closed(self) -> None:
        payload = valid_payload()
        payload["platform_snapshot"]["repository"] = "other/repository"  # type: ignore[index]
        self.assert_invalid(payload, "repository does not match")
        payload = valid_payload()
        payload["platform_snapshot"]["readback"]["confirmed"] = False  # type: ignore[index]
        self.assert_invalid(payload, "must confirm GitHub")
        payload = valid_payload()
        payload["platform_snapshot"]["receipt_url"] = "https://github.com/other/repository/pull/1#issuecomment-123"  # type: ignore[index]
        self.assert_invalid(payload, "must bind the receipt ID")
        payload = valid_payload()
        payload["receipt"]["repository"] = "owner/repo/extra"  # type: ignore[index]
        self.assert_invalid(payload, "owner/repository")
        payload = valid_payload()
        payload["platform_snapshot"]["receipt_url"] = "https://github.com/jeffery777/codex-dev-skills/pull/1834#issuecomment-123"  # type: ignore[index]
        self.assert_invalid(payload, "must bind the receipt ID")

    def test_only_open_non_draft_pr_and_bound_receipt_url_pass(self) -> None:
        payload = valid_payload()
        payload["platform_snapshot"]["state"] = "closed"  # type: ignore[index]
        self.assert_invalid(payload, "state must equal 'open'")
        payload = valid_payload()
        payload["platform_snapshot"]["draft"] = True  # type: ignore[index]
        self.assert_invalid(payload, "draft must be false")
        payload = valid_payload()
        payload["platform_snapshot"]["receipt_url"] = "https://github.com/jeffery777/codex-dev-skills/pull/183#issuecomment-124"  # type: ignore[index]
        self.assert_invalid(payload, "must bind the receipt ID")

    def test_required_ci_names_and_run_ids_must_be_unique(self) -> None:
        payload = valid_payload()
        checks = payload["platform_snapshot"]["required_ci"]  # type: ignore[index]
        checks.append(dict(checks[0]))  # type: ignore[union-attr,index]
        self.assert_invalid(payload, "duplicate name")
        payload = valid_payload()
        checks = payload["platform_snapshot"]["required_ci"]  # type: ignore[index]
        checks.append({**checks[0], "name": "Other CI"})  # type: ignore[union-attr,index]
        self.assert_invalid(payload, "duplicate run_id")

    def test_receipt_digest_and_platform_metadata_fail_closed(self) -> None:
        payload = valid_payload()
        payload["platform_snapshot"]["receipt_digest"] = "e" * 64  # type: ignore[index]
        self.assert_invalid(payload, "does not match canonical receipt digest")
        payload = valid_payload()
        payload["platform_snapshot"]["mergeable"] = False  # type: ignore[index]
        self.assert_invalid(payload, "mergeable must be true")
        payload = valid_payload()
        payload["platform_snapshot"]["platform_readback_at"] = "not-a-time"  # type: ignore[index]
        self.assert_invalid(payload, "RFC3339 UTC")

    def test_cli_success_and_failure(self) -> None:
        valid = self.write_payload(valid_payload())
        result = subprocess.run(
            [str(ROOT / "scripts/project-python"), str(MODULE_PATH), str(valid)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("evidence valid", result.stdout)
        failed = valid_payload()
        failed["receipt"]["merge_authorized"] = True  # type: ignore[index]
        invalid = self.write_payload(failed)
        result = subprocess.run(
            [str(ROOT / "scripts/project-python"), str(MODULE_PATH), str(invalid)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(1, result.returncode)
        self.assertIn("merge_authorized must be false", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
