from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/exact-head-merge-readiness.yml"
UPSTREAM_WORKFLOW = ROOT / ".github/workflows/repository-validation.yml"
UPSTREAM_POLICY = ROOT / ".github/exact-head-merge-readiness-policy.json"
SHARD_MANIFEST = ROOT / "tests/test-shards.yaml"
ROLLOUT_GUIDE = ROOT / "docs/exact-head-merge-gate-app.md"


class ExactHeadRouteExecutionTests(unittest.TestCase):
    """Run the actual route shell with fixture API pages and the real jq parser."""

    HEAD = "a" * 40

    @staticmethod
    def pull(number: int, *, head: str = HEAD, state: str = "open", body: str = "") -> dict:
        return {"number": number, "head": {"sha": head}, "state": state, "body": body}

    def route(self, event_name: str, pages: list, *, event: dict | None = None,
              script: str | None = None) -> tuple[subprocess.CompletedProcess, list, list]:
        real_jq = shutil.which("jq")
        self.assertIsNotNone(real_jq, "jq is required to verify the hosted route shell")
        if script is None:
            script = yaml.safe_load(WORKFLOW.read_text())["jobs"]["route"]["steps"][0]["run"]
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "event.json").write_text(json.dumps(event or {
                "workflow_run": {"head_sha": self.HEAD, "workflow_id": 330877463}}))
            (root / "pages.json").write_text(json.dumps(pages))
            (root / "route.sh").write_text(script)
            # Enforce Linux's 128 KiB single-argument ceiling on macOS too.
            # JSON evaluation remains the real jq executable, never a parser mock.
            (root / "jq").write_text(
                f"#!{sys.executable}\nimport os, sys\n"
                "if any(len(os.fsencode(arg)) >= 131072 for arg in sys.argv[1:]):\n"
                "    sys.stderr.write('jq: Argument list too long (Linux argv ceiling)\\n')\n"
                "    sys.exit(126)\n"
                f"os.execv({real_jq!r}, ['jq', *sys.argv[1:]])\n")
            (root / "gh").write_text(
                f"#!{sys.executable}\nimport json, os, pathlib, re, subprocess, sys\n"
                "root = pathlib.Path(os.environ['FIXTURE_ROOT'])\n"
                "endpoint = next(arg for arg in sys.argv if arg.startswith('/repos/'))\n"
                "expected = '/repos/fixture/repo/'\n"
                "assert endpoint.startswith(expected), endpoint\n"
                "with (root / 'calls').open('a') as stream: stream.write(endpoint + '\\n')\n"
                "match = re.search(r'[?&]page=(\\d+)', endpoint)\n"
                "page = int(match[1]) if match else 1\n"
                "value = json.loads((root / 'pages.json').read_text())[page - 1]\n"
                "if isinstance(value, dict) and 'api_error' in value:\n"
                "    sys.stderr.write('fixture API failure\\n'); sys.exit(1)\n"
                "payload = value if isinstance(value, str) else json.dumps(value)\n"
                "if '--jq' in sys.argv:\n"
                "    result = subprocess.run(['jq', sys.argv[sys.argv.index('--jq') + 1]],\n"
                "                            input=payload, text=True)\n"
                "    sys.exit(result.returncode)\n"
                "print(payload)\n")
            for name in ("jq", "gh"):
                (root / name).chmod(0o700)
            environment = dict(os.environ, PATH=str(root) + os.pathsep + os.environ["PATH"],
                               FIXTURE_ROOT=str(root), EVENT_NAME=event_name,
                               GITHUB_REPOSITORY="fixture/repo", GH_TOKEN="fixture",
                               GITHUB_EVENT_PATH=str(root / "event.json"),
                               GITHUB_OUTPUT=str(root / "output"))
            result = subprocess.run(
                ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", str(root / "route.sh")],
                env=environment, capture_output=True, text=True, timeout=30, check=False)
            output = (root / "output").read_text() if (root / "output").exists() else ""
            targets = json.loads(output.removeprefix("pr_targets=")) if output else []
            calls = (root / "calls").read_text().splitlines() if (root / "calls").exists() else []
            return result, targets, calls

    def test_large_page_routes_without_passing_payload_in_argv(self) -> None:
        for entry in ("schedule", "workflow_run"):
            with self.subTest(entry=entry):
                result, targets, calls = self.route(entry, [[self.pull(377, body="x" * 300_000)]])
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual([{"pr_number": 377, "head_sha": self.HEAD}], targets)
                self.assertEqual(1, len(calls))

    def test_schedule_pagination_capacity_and_empty_collection(self) -> None:
        for count in (0, 1, 100, 200, 250, 251, 300):
            pulls = [self.pull(i + 1) for i in range(count)]
            pages = [pulls[i:i + 100] for i in range(0, count, 100)]
            if count % 100 == 0:
                pages.append([])
            with self.subTest(count=count):
                result, targets, calls = self.route("schedule", pages)
                if count > 250:
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("250-open-PR", result.stderr)
                    self.assertEqual([], targets)
                else:
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual([{"pr_number": i + 1, "head_sha": self.HEAD}
                                      for i in range(count)], targets)
                self.assertEqual(min(count // 100 + 1, 3), len(calls))

    def test_large_pages_keep_pagination_before_projection(self) -> None:
        for entry in ("schedule", "workflow_run"):
            with self.subTest(entry=entry):
                first = [self.pull(i + 1, state="closed" if entry == "workflow_run" else "open",
                                   body="x" * 4_000) for i in range(100)]
                result, targets, calls = self.route(entry, [first, [self.pull(101, body="y" * 300_000)]])
                self.assertEqual(0, result.returncode, result.stderr)
                numbers = list(range(1, 102)) if entry == "schedule" else [101]
                self.assertEqual([{"pr_number": number, "head_sha": self.HEAD}
                                  for number in numbers], targets)
                self.assertEqual(2, len(calls))

    def test_workflow_run_uses_raw_page_length_and_proves_completion(self) -> None:
        # Matching PR occurs only on the final page; earlier pages filter to empty.
        for count in (0, 100, 200, 499, 500, 501):
            pulls = [self.pull(i + 1, state="closed") for i in range(count)]
            if count:
                pulls[-1] = self.pull(count)
            pages = [pulls[i:i + 100] for i in range(0, count, 100)]
            if count % 100 == 0:
                pages.append([])
            with self.subTest(count=count):
                result, targets, calls = self.route("workflow_run", pages)
                self.assertEqual(min(count // 100 + 1, 6), len(calls))
                if count > 500:
                    self.assertNotEqual(0, result.returncode)
                    self.assertEqual([], targets)
                else:
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertEqual([{"pr_number": count, "head_sha": self.HEAD}]
                                     if count else [], targets)

    def test_workflow_run_filters_and_keeps_one_job_per_head(self) -> None:
        page = [self.pull(1, state="closed"), self.pull(2, head="b" * 40),
                self.pull(3), self.pull(4)]
        result, targets, _ = self.route("workflow_run", [page])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([{"pr_number": 3, "head_sha": self.HEAD}], targets)

    def test_page_faults_fail_without_publishing_targets(self) -> None:
        for entry in ("schedule", "workflow_run"):
            for bad in ("{", "", "null", "{}", "[]\n[]", {"api_error": True},
                        [self.pull(-1)]):
                with self.subTest(entry=entry, bad=bad):
                    result, targets, _ = self.route(entry, [bad])
                    self.assertNotEqual(0, result.returncode, result.stderr)
                    self.assertEqual([], targets)

    def test_malformed_rows_fail_before_filtering_or_accumulating(self) -> None:
        valid = self.pull(377)
        for entry in ("schedule", "workflow_run"):
            for bad in (None, {}, {key: value for key, value in valid.items() if key != "state"},
                        {**valid, "state": "unknown"}, {**valid, "number": 1.5},
                        {**valid, "number": "x" * 300_000},
                        {**valid, "head": {"sha": "b" * 300_000}},
                        {**valid, "head": {"sha": self.HEAD + "\n"}},
                        {**valid, "head": {"sha": "invalid"}}, {**valid, "head": None}):
                with self.subTest(entry=entry, bad_type=type(bad).__name__):
                    result, targets, _ = self.route(entry, [[valid, bad]])
                    self.assertNotEqual(0, result.returncode)
                    self.assertNotIn("Argument list too long", result.stderr)
                    self.assertEqual([], targets)

    def test_large_numeric_representation_is_canonical_before_next_page(self) -> None:
        pulls = [self.pull(i + 1) for i in range(100)]
        pulls[0]["number"] = "numeric-placeholder"
        page = json.dumps(pulls).replace('"numeric-placeholder"', "377." + "0" * 300_000)
        for entry in ("schedule", "workflow_run"):
            with self.subTest(entry=entry):
                result, targets, calls = self.route(entry, [page, []])
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(2, len(calls))
                self.assertEqual(377, targets[0]["pr_number"])
                self.assertIs(type(targets[0]["pr_number"]), int)
                self.assertLess(len(json.dumps(targets)), 20_000)

    def test_out_of_range_numeric_ids_fail_before_accumulation(self) -> None:
        for entry in ("schedule", "workflow_run"):
            for literal in ("9" * 300_000, "1E+10000", "9007199254740992"):
                page = '[{"number":' + literal + ',"state":"open","head":{"sha":"' + self.HEAD + '"}}]'
                with self.subTest(entry=entry, literal_bytes=len(literal)):
                    result, targets, _ = self.route(entry, [page])
                    self.assertNotEqual(0, result.returncode)
                    self.assertNotIn("Argument list too long", result.stderr)
                    self.assertEqual([], targets)

    def test_other_entries_reject_sha_with_trailing_newline(self) -> None:
        pull = self.pull(377, head=self.HEAD + "\n")
        for entry, event, pages in (
            ("pull_request_target", {"pull_request": pull}, []),
            ("issue_comment", {"issue": {"number": 377, "pull_request": {}}}, [pull]),
            ("workflow_dispatch", {"inputs": {"pr_number": "377"}}, [pull]),
        ):
            with self.subTest(entry=entry):
                result, targets, _ = self.route(entry, pages, event=event)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], targets)

    def test_later_page_api_and_parse_faults_fail_closed(self) -> None:
        for entry in ("schedule", "workflow_run"):
            for bad in ("{", {"api_error": True}):
                with self.subTest(entry=entry, bad=bad):
                    result, targets, calls = self.route(entry, [[self.pull(i + 1) for i in range(100)], bad])
                    self.assertNotEqual(0, result.returncode)
                    self.assertEqual([], targets)
                    self.assertEqual(2, len(calls))

    def test_workflow_run_completion_probe_faults_fail_closed(self) -> None:
        full = [self.pull(i + 1, state="closed") for i in range(100)]
        for bad in ("{", "", "null", "{}", "[]\n[]", {"api_error": True}):
            with self.subTest(bad=bad):
                result, targets, calls = self.route("workflow_run", [full] * 5 + [bad])
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], targets)
                self.assertEqual(6, len(calls))

    def test_other_entry_points_preserve_canonical_identity(self) -> None:
        pull = self.pull(377)
        for entry, event, pages, expected in (
            ("pull_request_target", {"pull_request": pull}, [], True),
            ("issue_comment", {"issue": {"number": 377, "pull_request": {}}}, [pull], True),
            ("issue_comment", {"issue": {"number": 377}}, [], False),
            ("workflow_dispatch", {"inputs": {"pr_number": "377"}}, [pull], True),
        ):
            with self.subTest(entry=entry, event=event):
                result, targets, calls = self.route(entry, pages, event=event)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual([{"pr_number": 377, "head_sha": self.HEAD}] if expected else [], targets)
                self.assertEqual(len(pages), len(calls))

    def test_untrusted_workflow_fails_before_api_call(self) -> None:
        result, targets, calls = self.route("workflow_run", [], event={
            "workflow_run": {"head_sha": self.HEAD, "workflow_id": 1}})
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], targets)
        self.assertEqual([], calls)

    @unittest.skipUnless(sys.platform == "linux", "hosted Bash errexit semantics; macOS Bash 3.2 differs")
    def test_noncanonical_manual_number_fails_before_api_call(self) -> None:
        result, targets, calls = self.route("workflow_dispatch", [], event={
            "inputs": {"pr_number": "377; echo injected"}})
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], targets)
        self.assertEqual([], calls)


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

    def test_collector_step_preserves_fault_exit_and_validates_only_ready_output(self) -> None:
        steps = self.workflow["jobs"]["evaluate"]["steps"]
        collect = next(step for step in steps if step.get("id") == "collect")
        validate = steps[-1]
        self.assertEqual("steps.collect.outputs.evaluated == 'true'", validate["if"])
        self.assertNotIn("continue-on-error", self.text)
        self.assertIn("validate-exact-head-merge-review.py", validate["run"])
        # Execute the workflow's actual shell with a bounded fake collector;
        # network/publication semantics are tested in the controller suite.
        script = re.sub(r"\$\{\{.*?\}\}", "fixture", collect["run"])
        for outcome, expected_exit, evaluated in (
            ("ready", 0, "true"), ("blocked", 0, "false"),
            ("noop", 0, "false"), ("error", 1, None),
        ):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                (root / "scripts").mkdir()
                runner = root / "scripts/project-python"
                runner.write_text(
                    '#!/bin/bash\n'
                    'case "$FIXTURE_OUTCOME" in\n'
                    'ready) echo "{}" > "$RUNNER_TEMP/exact-head-merge-readiness.json" ;;\n'
                    'blocked|noop) ;;\n'
                    '*) exit 1 ;;\nesac\n', encoding="utf-8")
                runner.chmod(0o700)
                environment = dict(os.environ, FIXTURE_OUTCOME=outcome,
                                   RUNNER_TEMP=str(root), GITHUB_OUTPUT=str(root / "outputs"))
                result = subprocess.run(["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", script],
                                        cwd=root, env=environment, capture_output=True, text=True, check=False)
                self.assertEqual(expected_exit, result.returncode, result.stderr)
                if evaluated is None:
                    self.assertFalse((root / "outputs").exists())
                else:
                    self.assertEqual(f"evaluated={evaluated}\n", (root / "outputs").read_text())

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
