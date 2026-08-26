from __future__ import annotations

import pathlib
import re
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/exact-head-merge-readiness.yml"
UPSTREAM_WORKFLOW = ROOT / ".github/workflows/repository-validation.yml"


class ExactHeadReadinessWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")
        self.workflow = yaml.safe_load(self.text)

    def test_uses_trusted_default_branch_and_never_pr_head(self) -> None:
        self.assertIn("ref: refs/heads/${{ github.event.repository.default_branch }}", self.text)
        self.assertNotIn("ref: ${{ github.event.pull_request.head.sha }}", self.text)
        self.assertNotIn("github.sha", self.text.lower())
        self.assertNotRegex(self.text, r"(?m)^\s*(run|uses):.*pull_request\.(head|body|title)")

    def test_dedicated_app_token_is_environment_protected_and_least_privilege(self) -> None:
        job = self.workflow["jobs"]["evaluate"]
        self.assertEqual("exact-head-merge-gate", job["environment"])
        self.assertEqual({"contents": "read", "pull-requests": "read"}, self.workflow["permissions"])
        self.assertIn("permission-checks: write", self.text)
        self.assertIn("permission-actions: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("pull-requests: write", self.text)

    def test_actions_are_immutable_and_controller_publishes_explicit_check(self) -> None:
        uses = re.findall(r"uses:\s+[^@\s]+@([^\s]+)", self.text)
        self.assertTrue(uses)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in uses))
        self.assertIn("collect-exact-head-merge-readiness.py", self.text)
        self.assertIn("validate-exact-head-merge-review.py", self.text)
        self.assertNotIn("pull_request_review:", self.text)
        self.assertNotIn("pull_request_review_comment:", self.text)
        self.assertIn("cancel-in-progress: false", self.text)
        self.assertNotIn("workflow_run.pull_requests[0].number", self.text)
        self.assertIn("workflow_run.head_sha", self.text)
        self.assertIn("group: exact-head-readiness-${{ matrix.target.head_sha }}", self.text)
        self.assertEqual("route", self.workflow["jobs"]["evaluate"]["needs"])
        self.assertEqual(
            ["in_progress", "completed"], self.workflow[True]["workflow_run"]["types"]
        )

    def test_receipt_id_is_passed_as_quoted_environment_data(self) -> None:
        self.assertIn("RECEIPT_ID: ${{ inputs.receipt_id || '' }}", self.text)
        self.assertIn('--receipt-id "$RECEIPT_ID"', self.text)
        self.assertNotIn("format('--receipt-id", self.text)

    def test_manual_and_scheduled_routing_are_canonical_and_bounded(self) -> None:
        self.assertIn('[[ "$raw_pr_number" =~ ^[1-9][0-9]*$ ]]', self.text)
        self.assertNotIn("pr_numbers=\"[$(jq -er '.inputs.pr_number'", self.text)
        self.assertIn("for page in 1 2 3", self.text)
        self.assertIn("-gt 250", self.text)
        self.assertIn("explicit 250-open-PR matrix capacity", self.text)
        self.assertIn("pr_targets", self.text)
        self.assertIn("matrix.target.pr_number", self.text)
        self.assertIn('--expected-head "${{ matrix.target.head_sha }}"', self.text)
        self.assertIn("commits/$head_sha/pulls?per_page=100&page=$page", self.text)
        self.assertIn("commits/$head_sha/pulls?per_page=100&page=6", self.text)

    def test_upstream_validation_uses_trusted_definition_without_secrets(self) -> None:
        text = UPSTREAM_WORKFLOW.read_text(encoding="utf-8")
        workflow = yaml.safe_load(text)
        self.assertIn("pull_request", workflow[True])
        self.assertNotIn("pull_request_target", workflow[True])
        self.assertEqual(
            "Repository Validation PR #${{ github.event.pull_request.number }} @ ${{ github.event.pull_request.head.sha }}",
            workflow["run-name"],
        )
        self.assertEqual({"contents": "read"}, workflow["permissions"])
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", text)
        self.assertIn("persist-credentials: false", text)
        self.assertNotIn("secrets.", text)
        self.assertNotIn("environment:", text)
        self.assertNotIn("actions/cache", text)
        self.assertNotIn("upload-artifact", text)


if __name__ == "__main__":
    unittest.main()
