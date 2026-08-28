from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/exact-head-merge-readiness.yml"
UPSTREAM_WORKFLOW = ROOT / ".github/workflows/repository-validation.yml"
UPSTREAM_POLICY = ROOT / ".github/exact-head-merge-readiness-policy.json"
SHARD_MANIFEST = ROOT / "tests/test-shards.yaml"
ROLLOUT_GUIDE = ROOT / "docs/exact-head-merge-gate-app.md"


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
        self.assertNotIn("permission-contents: read", self.text)
        self.assertIn("REPOSITORY_READ_TOKEN: ${{ github.token }}", self.text)
        self.assertIn(
            "--repository-read-token-env REPOSITORY_READ_TOKEN", self.text
        )
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

    def test_non_pr_issue_comments_are_successful_no_ops(self) -> None:
        self.assertIn(
            "if jq -e '.issue.pull_request != null' \"$GITHUB_EVENT_PATH\" >/dev/null; then",
            self.text,
        )
        issue_comment_case = self.text.split("issue_comment)", 1)[1].split(
            "workflow_run)", 1
        )[0]
        self.assertIn("else\n                pr_targets='[]'\n              fi", issue_comment_case)

    def test_ruleset_preview_preserves_all_required_contexts(self) -> None:
        guide = ROLLOUT_GUIDE.read_text(encoding="utf-8")
        payloads = [
            json.loads(body)
            for body in re.findall(r"```json\n(.*?)\n```", guide, re.DOTALL)
            if '"required_status_checks"' in body
        ]
        self.assertEqual(1, len(payloads))
        rules = payloads[0]["rules"]
        required = next(
            rule["parameters"]["required_status_checks"]
            for rule in rules
            if rule["type"] == "required_status_checks"
        )
        self.assertEqual(
            {
                "Validate repository": 15368,
                "Validate closing Issue": 15368,
                "Exact-Head Merge Readiness": "<DEDICATED_APP_INTEGRATION_ID_FROM_CANARY>",
            },
            {item["context"]: item["integration_id"] for item in required},
        )

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

    def test_upstream_shards_behind_one_fail_closed_aggregate_context(self) -> None:
        text = UPSTREAM_WORKFLOW.read_text(encoding="utf-8")
        workflow = yaml.safe_load(text)
        jobs = workflow["jobs"]

        self.assertEqual(
            1,
            sum(job.get("name") == "Validate repository" for job in jobs.values()),
        )
        self.assertEqual("Validate repository", jobs["validate"]["name"])
        self.assertEqual(
            ["plan", "repository_checks", "test_shards"], jobs["validate"]["needs"]
        )
        self.assertEqual("${{ always() }}", jobs["validate"]["if"])
        self.assertFalse(jobs["test_shards"]["strategy"]["fail-fast"])
        self.assertEqual(
            "${{ fromJSON(needs.plan.outputs.shards) }}",
            jobs["test_shards"]["strategy"]["matrix"]["shard"],
        )
        aggregate = jobs["validate"]["steps"][0]
        self.assertEqual(
            {
                "PLAN_RESULT": "${{ needs.plan.result }}",
                "REPOSITORY_CHECKS_RESULT": "${{ needs.repository_checks.result }}",
                "TEST_SHARDS_RESULT": "${{ needs.test_shards.result }}",
            },
            aggregate["env"],
        )
        self.assertEqual(3, aggregate["run"].count('test "$'))
        self.assertEqual(3, aggregate["run"].count('" = success'))
        self.assertIn("scripts/test-shards.py validate", text)
        self.assertIn("scripts/test-shards.py list --format json", text)
        self.assertIn('scripts/test-shards.py run "${{ matrix.shard }}"', text)

    def test_upstream_aggregate_rejects_every_non_success_result(self) -> None:
        workflow = yaml.safe_load(UPSTREAM_WORKFLOW.read_text(encoding="utf-8"))
        aggregate_script = workflow["jobs"]["validate"]["steps"][0]["run"]

        def run(plan: str, repository_checks: str, test_shards: str) -> int:
            environment = os.environ.copy()
            environment.update(
                PLAN_RESULT=plan,
                REPOSITORY_CHECKS_RESULT=repository_checks,
                TEST_SHARDS_RESULT=test_shards,
            )
            return subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", aggregate_script],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            ).returncode

        self.assertEqual(0, run("success", "success", "success"))
        for component in range(3):
            for result in ("", "failure", "cancelled", "skipped"):
                values = ["success", "success", "success"]
                values[component] = result
                with self.subTest(component=component, result=result):
                    self.assertNotEqual(0, run(*values))

    def test_internal_shards_are_not_required_context_contracts(self) -> None:
        policy = json.loads(UPSTREAM_POLICY.read_text(encoding="utf-8"))
        guide = ROLLOUT_GUIDE.read_text(encoding="utf-8")
        manifest = yaml.safe_load(SHARD_MANIFEST.read_text(encoding="utf-8"))
        policy_contexts = {policy["check_context"]} | {
            item["check_context"] for item in policy["required_upstream_workflows"]
        }
        ruleset_contexts = {
            "Validate repository",
            "Validate closing Issue",
            "Exact-Head Merge Readiness",
        }

        for shard in manifest["shards"]:
            self.assertNotIn(shard["id"], policy_contexts)
            self.assertNotIn(shard["id"], ruleset_contexts)
        self.assertIn('"context": "Validate repository"', guide)

    def test_upstream_policy_pins_the_current_workflow_blob(self) -> None:
        workflow_bytes = UPSTREAM_WORKFLOW.read_bytes()
        blob = b"blob " + str(len(workflow_bytes)).encode("ascii") + b"\0" + workflow_bytes
        expected_sha = hashlib.sha1(blob, usedforsecurity=False).hexdigest()
        policy = json.loads(UPSTREAM_POLICY.read_text(encoding="utf-8"))

        self.assertEqual(
            expected_sha,
            policy["required_upstream_workflows"][0]["workflow_blob_sha"],
        )


if __name__ == "__main__":
    unittest.main()
