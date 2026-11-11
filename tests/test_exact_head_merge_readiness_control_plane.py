from __future__ import annotations

import importlib.util
import contextlib
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tests.test_exact_head_merge_review import valid_v2_payload


ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "collect-exact-head-merge-readiness.py"
SPEC = importlib.util.spec_from_file_location("exact_head_control_plane", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
control = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(control)


class ExactHeadControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        # Existing tests isolate receipt/check lifecycle faults. The transition
        # tests below separately exercise real policy source checks and drift.
        patch = mock.patch.object(control, "confirm_current_policy")
        self.policy_freshness = patch.start()
        self.addCleanup(patch.stop)

    def exercise_cli_block(self, directory: str, *, collection_error=None,
                           publication_error=None, readback_error=None,
                           latest_error=None, existing_output=False, identity_error=None):
        root = pathlib.Path(directory)
        event = root / "event.json"
        event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
        output = root / "out.json"
        if existing_output:
            output.write_text(json.dumps(valid_v2_payload()), encoding="utf-8")
        argv = [
            "--repository", "jeffery777/codex-dev-skills",
            "--event-path", str(event), "--output", str(output),
            "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
            "--workflow-name", "Exact-Head Merge Readiness Controller",
            "--workflow-run-id", "900",
            "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
            "--expected-head", "b" * 40,
            "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
        ]
        client = mock.Mock()
        client.json.return_value = {"head": {"sha": "b" * 40}}
        stdout, stderr = io.StringIO(), io.StringIO()
        with (
            mock.patch.dict("os.environ", {"EXACT_HEAD_GATE_TOKEN": "app", "REPOSITORY_READ_TOKEN": "reader"}),
            mock.patch.object(control, "GitHubClient", return_value=client) as factory,
            mock.patch.object(control, "find_gate_check", return_value=None),
            mock.patch.object(control, "start_check", return_value={"id": 901, "app": {"id": 100001, "slug": "exact-head-gate"}}) as start,
            mock.patch.object(control, "confirm_gate_check", side_effect=identity_error),
            mock.patch.object(control, "confirm_latest_gate_check", side_effect=[None, None, latest_error]) as latest,
            mock.patch.object(control, "require_unique_open_pr_for_head"),
            mock.patch.object(control, "select_current_receipt", return_value=(None, None), side_effect=collection_error),
            mock.patch.object(control, "set_check_pointer"),
            mock.patch.object(control, "build_envelope") as build,
            mock.patch.object(control, "update_check", side_effect=publication_error) as update,
            mock.patch.object(control, "confirm_completed_gate_check", side_effect=readback_error) as readback,
            contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr),
        ):
            result = control.main(argv)
        build.assert_not_called()
        return result, stdout.getvalue(), stderr.getvalue(), output, update, readback, latest, factory, start

    def test_missing_receipt_exits_zero_only_after_authoritative_failure_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, out, err, output, update, readback, latest, _, _ = self.exercise_cli_block(directory)
            self.assertEqual(0, result)
            self.assertIn("readiness blocked; dedicated App failure verified", out)
            self.assertIn("no current exact-head receipt", out)
            self.assertEqual("", err)
            self.assertFalse(output.exists())
            update.assert_called_once()
            self.assertEqual("failure", update.call_args.args[2])
            readback.assert_called_once()
            self.assertEqual("failure", readback.call_args.args[4])
            self.assertEqual(3, latest.call_count)

    def test_block_publication_and_readback_faults_never_report_success(self) -> None:
        for stage in ("publication_error", "readback_error", "latest_error"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as directory:
                result, out, err, output, update, *_ = self.exercise_cli_block(
                    directory, **{stage: control.ControlPlaneError("injected failure")})
                self.assertEqual(1, result)
                self.assertNotIn("failure verified", out)
                self.assertIn("failed to publish authoritative gate failure", err)
                self.assertFalse(output.exists())
                # No blind retries, and no success conclusion even on ambiguous publication.
                update.assert_called_once()
                self.assertEqual("failure", update.call_args.args[2])

    def test_other_abnormalities_remain_errors_even_after_failure_publication(self) -> None:
        for error in (
            control.ControlPlaneError("API unavailable"),
            control.ControlPlaneError("no current exact-head receipt is bound to this PR head"),
            control.ControlPlaneError("receipt drifted"),
            control.validator.ExactHeadMergeReviewError("invalid receipt schema"),
            OSError(28, "controlled output/storage error"),
        ):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                result, out, err, output, update, readback, *_ = self.exercise_cli_block(directory, collection_error=error)
                self.assertEqual(1, result)
                self.assertNotIn("failure verified", out)
                self.assertIn(str(error), err)
                self.assertFalse(output.exists())
                update.assert_called_once()
                readback.assert_called_once()

    def test_stale_output_is_rejected_before_any_platform_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, _, err, output, update, _, _, factory, start = self.exercise_cli_block(directory, existing_output=True)
            self.assertEqual(1, result)
            self.assertIn("output path already exists", err)
            self.assertEqual(valid_v2_payload(), json.loads(output.read_text()))
            factory.assert_not_called()
            start.assert_not_called()
            update.assert_not_called()

    def test_unverified_block_is_not_a_successful_controller_result(self) -> None:
        with mock.patch.object(control, "parse_args"), mock.patch.object(control, "run", side_effect=control.ReadinessBlocked("unverified")):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(1, control.main([]))

    def test_event_resolution_uses_pr_identity_not_event_sha(self) -> None:
        self.assertEqual(185, control.event_pr_number({"pull_request": {"number": 185}, "after": "a" * 40}))
        self.assertEqual(185, control.event_pr_number({"issue": {"number": 185, "pull_request": {"url": "x"}}}))
        self.assertEqual(185, control.event_pr_number({"workflow_run": {"pull_requests": [{"number": 185}]}}))
        self.assertEqual(185, control.event_pr_number({"inputs": {"pr_number": "185"}}))

    def test_event_resolution_rejects_default_branch_only_context(self) -> None:
        with self.assertRaisesRegex(control.ControlPlaneError, "exactly one pull request"):
            control.event_pr_number({"ref": "refs/heads/main", "after": "a" * 40})
        with self.assertRaisesRegex(control.ControlPlaneError, "exactly one pull request"):
            control.event_pr_number({"workflow_run": {"pull_requests": []}})

    def test_policy_is_strict_bounded_and_has_no_self_dependency(self) -> None:
        policy = control.load_policy(ROOT / ".github/exact-head-merge-readiness-policy.json")
        contexts = [item["check_context"] for item in policy["required_upstream_workflows"]]
        self.assertNotIn(policy["check_context"], contexts)
        self.assertEqual(["Validate repository"], contexts)
        self.assertEqual(
            {"OWNER"},
            set(policy["trusted_receipt_author_associations"]),
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as stream:
            path = pathlib.Path(stream.name)
            self.addCleanup(path.unlink, missing_ok=True)
            value = dict(policy)
            value["unexpected"] = True
            json.dump(value, stream)
        with self.assertRaisesRegex(ValueError, "unknown critical field"):
            control.load_policy(path)

    def test_receipt_body_must_be_whole_strict_json(self) -> None:
        with self.assertRaisesRegex(control.ControlPlaneError, "not strict JSON"):
            control.strict_json(b"```json\n{}\n```", maximum=100, label="receipt body")
        with self.assertRaisesRegex(control.ControlPlaneError, "not strict JSON"):
            control.strict_json(b'{"a":1,"a":2}', maximum=100, label="receipt body")

    def test_diff_and_envelope_digests_are_deterministic(self) -> None:
        self.assertEqual(control.canonical_digest({"b": 2, "a": 1}), control.canonical_digest({"a": 1, "b": 2}))
        self.assertEqual(64, len(control.canonical_digest([])))

    def test_stable_evidence_comparison_ignores_only_readback_time(self) -> None:
        first = {"platform_snapshot": {"platform_readback_at": "one", "head_sha": "a"}, "gate": {"check_run_id": 1}}
        second = {"platform_snapshot": {"platform_readback_at": "two", "head_sha": "a"}, "gate": {"check_run_id": 1}}
        self.assertEqual(control.stable_evidence_identity(first), control.stable_evidence_identity(second))
        second["platform_snapshot"]["head_sha"] = "b"
        self.assertNotEqual(control.stable_evidence_identity(first), control.stable_evidence_identity(second))

    def test_receipt_event_relevance_ignores_ordinary_comments_and_tracks_only_current(self) -> None:
        receipt = valid_v2_payload()["receipt"]
        body = json.dumps(receipt, sort_keys=True)
        common = {
            "current_receipt_id": 321,
            "explicit_receipt_id": None,
            "repository": "jeffery777/codex-dev-skills",
            "pr_number": 185,
            "maximum": 262144,
            "trusted_associations": {"OWNER", "MEMBER", "COLLABORATOR"},
        }
        self.assertEqual(
            (False, 321),
            control.event_receipt_decision(
                {"action": "created", "comment": {"id": 999, "body": "ordinary", "author_association": "OWNER"}},
                **common,
            ),
        )
        self.assertEqual(
            (False, 321),
            control.event_receipt_decision(
                {"action": "created", "comment": {"id": 999, "body": body, "author_association": "NONE"}},
                **common,
            ),
        )
        self.assertEqual(
            (True, 999),
            control.event_receipt_decision(
                {"action": "created", "comment": {"id": 999, "body": body, "author_association": "OWNER"}},
                **common,
            ),
        )
        self.assertEqual(
            (True, 321),
            control.event_receipt_decision(
                {"action": "deleted", "comment": {"id": 321, "body": body, "author_association": "OWNER"}},
                **common,
            ),
        )
        self.assertEqual(
            (False, 321),
            control.event_receipt_decision(
                {"action": "deleted", "comment": {"id": 111, "body": body, "author_association": "OWNER"}},
                **common,
            ),
        )

    def test_pointer_is_strictly_bound_to_repository_pr_head_and_generation(self) -> None:
        value = control.pointer_value("o/r", 5, "a" * 40, 99, 7, 3, "b" * 64)
        self.assertLessEqual(len(value), 255)
        self.assertLessEqual(
            len(control.pointer_value("jeffery777/codex-dev-skills", 185, "a" * 40, 999999999, 999999, 999999, "b" * 64)),
            255,
        )
        self.assertEqual((99, 7, 3, "b" * 64), control.parse_pointer(value, "o/r", 5, "a" * 40))
        self.assertEqual((None, None, 0, None), control.parse_pointer(value, "o/r", 6, "a" * 40))
        self.assertEqual((None, None, 0, None), control.parse_pointer(value, "o/r", 5, "b" * 40))
        exhausted = control.pointer_value(
            "o/r", 5, "a" * 40, 99, 7, control.validator.MAX_RECEIPT_SEQUENCE,
        )
        self.assertEqual((None, None, 0, None), control.parse_pointer(exhausted, "o/r", 5, "a" * 40))
        with self.assertRaisesRegex(control.ControlPlaneError, "bounded integer range"):
            control.pointer_value(
                "o/r", 5, "a" * 40, 99, 7,
                control.validator.MAX_RECEIPT_SEQUENCE + 1,
            )

    def test_live_receipt_sequence_advances_and_deleted_pointer_never_falls_back(self) -> None:
        head = "b" * 40

        def comment(identifier: int, sequence: int) -> dict[str, object]:
            receipt = valid_v2_payload()["receipt"]
            receipt["receipt_sequence"] = sequence  # type: ignore[index]
            return {
                "id": identifier,
                "author_association": "OWNER",
                "body": json.dumps(receipt),
                "html_url": f"https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-{identifier}",
            }

        client = mock.Mock()
        client.repository = "jeffery777/codex-dev-skills"
        client.repo_path.side_effect = lambda suffix: "/repos/jeffery777/codex-dev-skills" + suffix
        client.json_array_pages.return_value = [comment(11, 1), comment(22, 2)]
        self.assertEqual(
            (22, 2),
            control.select_current_receipt(client, 185, head, None, None, 262144, {"OWNER"}),
        )
        client.json_array_pages.return_value = [comment(11, 1)]
        self.assertEqual(
            (22, 2),
            control.select_current_receipt(client, 185, head, 22, 2, 262144, {"OWNER"}),
        )
        client.json_array_pages.return_value = [comment(11, 2), comment(22, 2)]
        with self.assertRaisesRegex(control.ControlPlaneError, "duplicate sequence"):
            control.select_current_receipt(client, 185, head, None, None, 262144, {"OWNER"})

    def test_latest_gate_check_uses_native_bounded_selector(self) -> None:
        client = mock.Mock()
        client.repo_path.side_effect = lambda suffix: "/repos/o/r" + suffix
        latest = {
            "id": 9,
            "name": control.validator.GATE_CONTEXT,
            "head_sha": "a" * 40,
            "app": {"id": 10, "slug": "gate"},
        }
        # Native latest filtering remains bounded even when the head has more
        # than one API page of immutable historical runs.
        client.json_page.return_value = {"total_count": 101, "check_runs": [latest]}
        self.assertEqual(
            latest,
            control.find_gate_check(
                client, "a" * 40, control.validator.GATE_CONTEXT, 10
            ),
        )
        path = client.json_page.call_args.args[0]
        self.assertIn("check_name=Exact-Head+Merge+Readiness", path)
        self.assertIn("app_id=10", path)
        self.assertIn("filter=latest", path)
        self.assertIn("per_page=100", path)
        self.assertNotIn("filter=all", path)

        client.json_page.return_value = {
            "total_count": 2,
            "check_runs": [latest, dict(latest, id=8)],
        }
        with self.assertRaisesRegex(control.ControlPlaneError, "ambiguous or drifted"):
            control.find_gate_check(
                client, "a" * 40, control.validator.GATE_CONTEXT, 10
            )

    def test_each_evaluation_creates_a_fresh_gate_check(self) -> None:
        client = mock.Mock()
        client.repo_path.side_effect = lambda suffix: "/repos/o/r" + suffix
        client.json.return_value = {"id": 9, "app": {"id": 10, "slug": "gate"}}
        result = control.start_check(
            client,
            "a" * 40,
            control.validator.GATE_CONTEXT,
            "https://github.com/o/r/actions/runs/1",
            "pointer",
        )
        self.assertEqual(9, result["id"])
        self.assertEqual("POST", client.json.call_args.args[0])
        self.assertEqual("in_progress", client.json.call_args.kwargs["body"]["status"])
        self.assertEqual("a" * 40, client.json.call_args.kwargs["body"]["head_sha"])

    def test_upstream_workflow_run_name_binds_platform_pr_head(self) -> None:
        policy = control.load_policy(ROOT / ".github/exact-head-merge-readiness-policy.json")
        head = "b" * 40

        class FakeClient:
            repository = "jeffery777/codex-dev-skills"

            def __init__(
                self,
                conclusion: str | None = "success",
                canonical_name: str = "Repository Validation",
            ) -> None:
                self.collection_path = ""
                self.conclusion = conclusion
                self.status = "in_progress" if conclusion is None else "completed"
                self.canonical_name = canonical_name

            def repo_path(self, suffix: str) -> str:
                return f"/repos/{self.repository}{suffix}"

            def json_object_array_pages(self, path: str, key: str, *, maximum_pages: int) -> list[object]:
                self.collection_path = path
                self.assertions = (key, maximum_pages)
                return [
                        {
                            "id": 456,
                            "run_attempt": 1,
                            "workflow_id": 330877463,
                            "name": f"Repository Validation PR #185 @ {head}",
                            "path": ".github/workflows/repository-validation.yml",
                            "event": "pull_request",
                            "display_title": f"Repository Validation PR #185 @ {head}",
                            "head_sha": head,
                            "conclusion": self.conclusion,
                            "status": self.status,
                            "html_url": "https://github.com/jeffery777/codex-dev-skills/actions/runs/456",
                        }
                ]

            def json(self, method: str, path: str, **kwargs: object) -> object:
                if path.endswith("/actions/workflows/330877463"):
                    return {
                        "id": 330877463,
                        "name": self.canonical_name,
                        "path": ".github/workflows/repository-validation.yml",
                        "state": "active",
                    }
                raise AssertionError(f"unexpected App-token endpoint: {path}")

        client = FakeClient()
        repository_read_client = mock.Mock()
        repository_read_client.repo_path.side_effect = (
            lambda suffix: f"/repos/{client.repository}{suffix}"
        )
        repository_read_client.json.return_value = {
            "sha": policy["required_upstream_workflows"][0]["workflow_blob_sha"]
        }
        result = control.collect_upstream_checks(
            client, repository_read_client, 185, "a" * 40, head, policy
        )
        self.assertEqual(head, result[0]["head_sha"])
        self.assertIn(f"head_sha={head}", client.collection_path)
        self.assertEqual(("workflow_runs", 5), client.assertions)
        self.assertEqual("exact-pr-head/v1", result[0]["run_name_contract"])
        self.assertEqual(f"Repository Validation PR #185 @ {head}", result[0]["run_display_title"])
        self.assertEqual("Repository Validation", result[0]["workflow_name"])
        self.assertEqual(2, repository_read_client.json.call_count)
        expected_blob = repository_read_client.json.return_value
        for blobs in ([{"sha": "0" * 40}, expected_blob],
                      [expected_blob, {"sha": "0" * 40}]):
            with self.subTest(blobs=blobs), mock.patch.object(
                repository_read_client, "json", side_effect=blobs,
            ), self.assertRaisesRegex(control.ControlPlaneError, "definition drifted"):
                control.collect_upstream_checks(
                    client, repository_read_client, 185, "a" * 40, head, policy,
                )
        for raw in (None, {}, {"workflow_id": 123}, {"workflow_id": 330877463, "display_title": "bad", "head_sha": "bad"}):
            malformed = FakeClient()
            with mock.patch.object(malformed, "json_object_array_pages", return_value=[raw]):
                with self.subTest(raw=raw), self.assertRaises((control.ControlPlaneError, control.validator.ExactHeadMergeReviewError)) as raised:
                    control.collect_upstream_checks(malformed, repository_read_client, 185, "a" * 40, head, policy)
                self.assertNotIsInstance(raised.exception, control.ReadinessBlocked)
        self.assertTrue(
            all(
                "/contents/" in call.args[1]
                for call in repository_read_client.json.call_args_list
            )
        )
        with self.assertRaisesRegex(control.ControlPlaneError, "no run for the live PR head"):
            control.collect_upstream_checks(
                FakeClient(), repository_read_client, 186, "a" * 40, head, policy
            )
        with self.assertRaisesRegex(control.ControlPlaneError, "not successful"):
            control.collect_upstream_checks(
                FakeClient(conclusion=None),
                repository_read_client,
                185,
                "a" * 40,
                head,
                policy,
            )
        for status, conclusion in ((None, "success"), ("completed", None), ("unknown", None), ("in_progress", "success"), ("completed", "unknown")):
            malformed = FakeClient(conclusion=conclusion)
            malformed.status = status
            with self.subTest(status=status, conclusion=conclusion):
                with self.assertRaises(control.ControlPlaneError) as raised:
                    control.collect_upstream_checks(malformed, repository_read_client, 185, "a" * 40, head, policy)
                self.assertNotIsInstance(raised.exception, control.ReadinessBlocked)
        for change in ("missing_conclusion", "wrong_url"):
            malformed = FakeClient(conclusion=None)
            runs = malformed.json_object_array_pages("", "workflow_runs", maximum_pages=5)
            if change == "missing_conclusion":
                runs[0].pop("conclusion")
            else:
                runs[0]["html_url"] = "https://github.com/other/repo/actions/runs/999"
            with self.subTest(change=change), mock.patch.object(malformed, "json_object_array_pages", return_value=runs):
                with self.assertRaises(control.ControlPlaneError) as raised:
                    control.collect_upstream_checks(malformed, repository_read_client, 185, "a" * 40, head, policy)
                self.assertNotIsInstance(raised.exception, control.ReadinessBlocked)
        for conclusion in ("failure", "cancelled", "timed_out", "skipped", "action_required"):
            with self.subTest(conclusion=conclusion), self.assertRaises(control.ReadinessBlocked):
                control.collect_upstream_checks(FakeClient(conclusion=conclusion), repository_read_client, 185, "a" * 40, head, policy)
        with self.assertRaisesRegex(control.ControlPlaneError, "not successful"):
            control.collect_upstream_checks(
                FakeClient(conclusion="failure"),
                repository_read_client,
                185,
                "a" * 40,
                head,
                policy,
            )
        with self.assertRaisesRegex(control.ControlPlaneError, "does not match policy"):
            control.collect_upstream_checks(
                FakeClient(canonical_name="Impostor Workflow"),
                repository_read_client,
                185,
                "a" * 40,
                head,
                policy,
            )

    def test_live_head_must_belong_to_exactly_one_open_pr(self) -> None:
        head = "b" * 40
        client = mock.Mock()
        client.repo_path.side_effect = lambda suffix: "/repos/o/r" + suffix
        client.json_array_pages.return_value = [
            {"number": 185, "state": "open", "head": {"sha": head}},
        ]
        control.require_unique_open_pr_for_head(client, 185, head)
        self.assertIn(f"/commits/{head}/pulls", client.json_array_pages.call_args.args[0])
        client.json_array_pages.return_value.append(
            {"number": 186, "state": "open", "head": {"sha": head}}
        )
        with self.assertRaisesRegex(control.ControlPlaneError, "exactly this one open pull request"):
            control.require_unique_open_pr_for_head(client, 185, head)

    def test_compare_identity_uses_only_repository_read_client(self) -> None:
        base = "a" * 40
        head = "b" * 40
        merge_base = "c" * 40
        policy = control.load_policy(
            ROOT / ".github/exact-head-merge-readiness-policy.json"
        )
        app_client = mock.Mock()
        app_client.repository = "jeffery777/codex-dev-skills"
        app_client.repo_path.side_effect = (
            lambda suffix: "/repos/jeffery777/codex-dev-skills" + suffix
        )
        app_client.json.return_value = {
            "base": {"sha": base},
            "head": {"sha": head},
            "state": "open",
            "draft": False,
            "mergeable": True,
        }
        repository_read_client = mock.Mock()
        repository_read_client.repo_path.side_effect = (
            lambda suffix: "/repos/jeffery777/codex-dev-skills" + suffix
        )
        repository_read_client.json.return_value = {
            "merge_base_commit": {"sha": merge_base}
        }
        receipt = valid_v2_payload()["receipt"]
        with (
            mock.patch.object(
                control, "select_current_receipt", return_value=(321, 1)
            ),
            mock.patch.object(
                control,
                "get_receipt",
                return_value=(
                    receipt,
                    321,
                    "https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-321",
                ),
            ),
            mock.patch.object(control, "resolve_workflow_policy", return_value=policy),
            mock.patch.object(control, "collect_resolved_upstream_checks", return_value=[]),
            mock.patch.object(
                control,
                "collect_threads",
                return_value=(0, control.canonical_digest([])),
            ),
        ):
            envelope = control.build_envelope(
                app_client,
                repository_read_client,
                185,
                321,
                1,
                policy,
                {},
            )
        self.assertEqual(merge_base, envelope["platform_snapshot"]["merge_base_sha"])
        self.assertEqual(
            "/repos/jeffery777/codex-dev-skills/compare/"
            f"{base}...{head}",
            repository_read_client.json.call_args.args[1],
        )
        self.assertEqual(1, app_client.json.call_count)
        self.assertIn("/pulls/185", app_client.json.call_args.args[1])

    def test_bounded_page_rejects_pagination(self) -> None:
        client = control.GitHubClient("o/r", "token", "https://api.github.com", 1024)
        with mock.patch.object(client, "request", return_value=(b"[]", {"link": '<x>; rel="next"'})):
            with self.assertRaisesRegex(control.ControlPlaneError, "exceeds one bounded page"):
                client.json_page("/repos/o/r/issues/1/comments?per_page=100")

    def test_bounded_array_collection_reads_multiple_pages_and_rejects_overflow(self) -> None:
        client = control.GitHubClient("o/r", "token", "https://api.github.com", 65536)
        pages = [[{"id": index}] * 100 for index in range(5)] + [[{"id": 501}]]
        with mock.patch.object(client, "json", side_effect=pages):
            with self.assertRaisesRegex(control.ControlPlaneError, "exceeds 500 items"):
                client.json_array_pages("/repos/o/r/issues/1/comments", maximum_pages=5)
        with mock.patch.object(client, "json", side_effect=[[{"id": 1}] * 100, [{"id": 2}]]):
            self.assertEqual(
                101,
                len(client.json_array_pages("/repos/o/r/issues/1/comments", maximum_pages=5)),
            )

    def test_bounded_object_collection_reads_multiple_pages_and_rejects_overflow(self) -> None:
        client = control.GitHubClient("o/r", "token", "https://api.github.com", 65536)
        pages = [
            {"workflow_runs": [{"id": index}] * 100} for index in range(5)
        ] + [{"workflow_runs": [{"id": 501}]}]
        with mock.patch.object(client, "json", side_effect=pages):
            with self.assertRaisesRegex(control.ControlPlaneError, "exceeds 500 items"):
                client.json_object_array_pages(
                    "/repos/o/r/actions/workflows/1/runs?head_sha=" + "a" * 40,
                    "workflow_runs",
                    maximum_pages=5,
                )

    def test_client_rejects_cross_origin_and_scheme_relative_paths(self) -> None:
        client = control.GitHubClient("o/r", "token", "https://api.github.com", 1024)
        for path in ("https://example.com/collect", "//example.com/collect", "repos/o/r"):
            with self.subTest(path=path):
                with self.assertRaisesRegex(control.ControlPlaneError, "same-origin"):
                    client.request("GET", path)

    def test_cli_rejects_credentialed_api_and_mismatched_run_url(self) -> None:
        base = [
            "--repository", "o/r", "--event-path", __file__, "--output", __file__,
            "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
            "--workflow-name", "Gate", "--workflow-run-id", "123",
            "--expected-head", "a" * 40,
            "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
        ]
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                control.parse_args(base + ["--run-url", "https://github.com/o/r/actions/runs/123", "--api-url", "https://token@api.github.com"])
            with self.assertRaises(SystemExit):
                control.parse_args(base + ["--run-url", "https://github.com/o/r/actions/runs/123", "--api-url", "https://example.com"])
            with self.assertRaises(SystemExit):
                control.parse_args(base + ["--run-url", "https://github.com/other/r/actions/runs/123"])
            with self.assertRaises(SystemExit):
                control.parse_args(
                    base
                    + [
                        "--run-url",
                        "https://github.com/o/r/actions/runs/123",
                        "--token-env",
                        "SHARED_TOKEN",
                        "--repository-read-token-env",
                        "SHARED_TOKEN",
                    ]
                )

    def test_run_rejects_identical_token_values_before_api_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text(
                '{"pull_request":{"number":185}}', encoding="utf-8"
            )
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event),
                "--output", str(root / "out.json"),
                "--policy", str(
                    ROOT / ".github/exact-head-merge-readiness-policy.json"
                ),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url",
                "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001",
                "--expected-app-slug", "exact-head-gate",
            ])
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "same",
                        "REPOSITORY_READ_TOKEN": "same",
                    },
                ),
                mock.patch.object(control, "GitHubClient") as client_factory,
            ):
                with self.assertRaisesRegex(
                    control.ControlPlaneError, "tokens must be distinct"
                ):
                    control.run(args)
            client_factory.assert_not_called()

    def test_routed_head_drift_fails_before_gate_check_lookup_or_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": "c" * 40}}
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(
                    control, "GitHubClient", return_value=fake
                ) as client_factory,
                mock.patch.object(control, "find_gate_check") as find,
                mock.patch.object(control, "start_check") as start,
            ):
                with self.assertRaisesRegex(control.ControlPlaneError, "routed PR head drifted"):
                    control.run(args)
            find.assert_not_called()
            start.assert_not_called()
            self.assertEqual(
                ["secret", "read-only"],
                [call.args[1] for call in client_factory.call_args_list],
            )

    def test_existing_latest_check_with_invalid_pointer_publishes_fresh_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": "b" * 40}}
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(
                    control,
                    "find_gate_check",
                    return_value={"id": 901, "external_id": "malformed"},
                ),
                mock.patch.object(control, "start_check", return_value={
                    "id": 902,
                    "app": {"id": 100001, "slug": "exact-head-gate"},
                }) as start,
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check") as confirm_latest,
                mock.patch.object(control, "confirm_completed_gate_check") as confirm_completed,
                mock.patch.object(control, "update_check") as update,
            ):
                with self.assertRaisesRegex(
                    control.ControlPlaneError, "invalid pointer"
                ):
                    control.run(args)
            start.assert_called_once()
            self.assertEqual("failure", update.call_args.args[2])
            self.assertEqual("failure", confirm_completed.call_args.args[4])
            self.assertEqual(2, confirm_latest.call_count)

    def test_failure_publication_error_preserves_evaluation_and_readback_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": "b" * 40}}
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(
                    control, "find_gate_check",
                    return_value={"id": 901, "external_id": "malformed"},
                ),
                mock.patch.object(control, "start_check", return_value={
                    "id": 902,
                    "app": {"id": 100001, "slug": "exact-head-gate"},
                }),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check"),
                mock.patch.object(control, "update_check"),
                mock.patch.object(
                    control,
                    "confirm_completed_gate_check",
                    side_effect=control.ControlPlaneError("failure readback drifted"),
                ),
            ):
                with self.assertRaisesRegex(
                    control.ControlPlaneError,
                    "invalid pointer: failure readback drifted",
                ):
                    control.run(args)

    def test_same_receipt_sequence_cannot_replace_bound_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            head = "b" * 40
            prior_digest = "c" * 64
            pointer = control.pointer_value(
                "jeffery777/codex-dev-skills", 185, head, 321, 1, 7,
                prior_digest,
            )
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": head}}
            set_pointer = mock.Mock()
            update = mock.Mock()
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(control, "find_gate_check", return_value={
                    "id": 901, "status": "completed", "conclusion": "success",
                    "external_id": pointer,
                }),
                mock.patch.object(control, "start_check", return_value={
                    "id": 902,
                    "app": {"id": 100001, "slug": "exact-head-gate"},
                }),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check"),
                mock.patch.object(control, "confirm_completed_gate_check") as confirm_completed,
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "select_current_receipt", return_value=(321, 1)),
                mock.patch.object(control, "get_receipt", return_value=(
                    valid_v2_payload()["receipt"], 321,
                    "https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-321",
                )),
                mock.patch.object(control, "set_check_pointer", set_pointer),
                mock.patch.object(control, "update_check", update),
            ):
                with self.assertRaisesRegex(
                    control.ControlPlaneError, "without a higher receipt sequence"
                ):
                    control.run(args)
            set_pointer.assert_called_once()
            self.assertTrue(
                str(set_pointer.call_args.args[3]).endswith(":" + prior_digest)
            )
            self.assertEqual("failure", update.call_args.args[2])
            self.assertTrue(str(update.call_args.args[5]).endswith(":" + prior_digest))
            self.assertEqual("failure", confirm_completed.call_args.args[4])

    def test_higher_sequence_is_tombstoned_before_direct_receipt_readback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            head = "b" * 40
            pointer = control.pointer_value(
                "jeffery777/codex-dev-skills", 185, head, 321, 1, 7,
                "c" * 64,
            )
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": head}}
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(control, "find_gate_check", return_value={
                    "id": 901, "external_id": pointer,
                }),
                mock.patch.object(control, "start_check", return_value={
                    "id": 902,
                    "app": {"id": 100001, "slug": "exact-head-gate"},
                }),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check"),
                mock.patch.object(control, "confirm_completed_gate_check"),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "select_current_receipt", return_value=(322, 2)),
                mock.patch.object(
                    control, "get_receipt",
                    side_effect=control.ControlPlaneError("receipt disappeared"),
                ),
                mock.patch.object(control, "set_check_pointer") as set_pointer,
                mock.patch.object(control, "update_check") as update,
            ):
                with self.assertRaisesRegex(
                    control.ControlPlaneError, "receipt disappeared"
                ):
                    control.run(args)
            tombstone = set_pointer.call_args.args[3]
            self.assertEqual(
                (322, 2, 8, None),
                control.parse_pointer(
                    tombstone,
                    "jeffery777/codex-dev-skills",
                    185,
                    head,
                ),
            )
            self.assertEqual(tombstone, update.call_args.args[5])
            self.assertEqual("failure", update.call_args.args[2])

    def test_locked_receipt_digest_rejects_envelope_body_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            original = valid_v2_payload()
            drifted = json.loads(json.dumps(original))
            drifted["receipt"]["residual_risk"] = "edited without a new sequence"
            drifted["platform_snapshot"]["receipt_digest"] = (
                control.validator.canonical_receipt_digest(drifted["receipt"])
            )
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": "b" * 40}}
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(control, "find_gate_check", return_value=None),
                mock.patch.object(control, "start_check", return_value={
                    "id": 902,
                    "app": {"id": 100001, "slug": "exact-head-gate"},
                }),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check"),
                mock.patch.object(control, "confirm_completed_gate_check"),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "select_current_receipt", return_value=(321, 1)),
                mock.patch.object(control, "get_receipt", return_value=(
                    original["receipt"], 321,
                    "https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-321",
                )),
                mock.patch.object(control, "set_check_pointer") as set_pointer,
                mock.patch.object(control, "build_envelope", return_value=drifted) as collect,
                mock.patch.object(control, "update_check") as update,
            ):
                with self.assertRaisesRegex(
                    control.ControlPlaneError, "drifted after its digest was locked"
                ):
                    control.run(args)
            self.assertEqual(1, collect.call_count)
            self.assertEqual(2, set_pointer.call_count)
            locked_pointer = set_pointer.call_args_list[-1].args[3]
            self.assertEqual(locked_pointer, update.call_args.args[5])
            self.assertEqual("failure", update.call_args.args[2])

    def test_run_collects_twice_and_publishes_only_stable_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            output = root / "evidence.json"
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(output),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
                "--receipt-id", "321",
            ])

            class FakeClient:
                def repo_path(self, suffix: str) -> str:
                    return "/repos/jeffery777/codex-dev-skills" + suffix

                def json(self, method: str, path: str, **kwargs: object) -> object:
                    self.last = (method, path, kwargs)
                    return {"head": {"sha": "b" * 40}}

            fake = FakeClient()
            created = {"id": 901, "app": {"id": 100001, "slug": "exact-head-gate"}}
            first = valid_v2_payload()
            second = json.loads(json.dumps(first))
            second["platform_snapshot"]["platform_readback_at"] = "2026-08-25T12:00:01Z"
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(control, "find_gate_check", return_value=None),
                mock.patch.object(control, "select_current_receipt", return_value=(321, 1)),
                mock.patch.object(control, "get_receipt", return_value=(
                    first["receipt"], 321,
                    "https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-321",
                )),
                mock.patch.object(control, "start_check", return_value=created),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "set_check_pointer") as set_pointer,
                mock.patch.object(control, "build_envelope", side_effect=[first, second]) as collect,
                mock.patch.object(control, "confirm_gate_check") as confirm,
                mock.patch.object(control, "confirm_latest_gate_check") as confirm_latest,
                mock.patch.object(control, "confirm_completed_gate_check") as confirm_completed,
                mock.patch.object(control, "update_check") as update,
            ):
                result = control.run(args)
            self.assertEqual(second, result)
            self.assertEqual(2, collect.call_count)
            self.assertEqual(5, confirm.call_count)
            self.assertEqual(5, confirm_latest.call_count)
            self.assertEqual(2, set_pointer.call_count)
            confirm_completed.assert_called_once()
            self.assertEqual("success", confirm_completed.call_args.args[4])
            update.assert_called_once()
            self.assertEqual("success", update.call_args.args[2])
            self.assertTrue(output.is_file())

    def test_run_fails_check_when_second_snapshot_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
                "--receipt-id", "321",
            ])
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": "b" * 40}}
            created = {"id": 901, "app": {"id": 100001, "slug": "exact-head-gate"}}
            first = valid_v2_payload()
            second = json.loads(json.dumps(first))
            second["platform_snapshot"]["receipt_id"] = 999
            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(control, "find_gate_check", return_value=None),
                mock.patch.object(control, "select_current_receipt", return_value=(321, 1)),
                mock.patch.object(control, "get_receipt", return_value=(
                    first["receipt"], 321,
                    "https://github.com/jeffery777/codex-dev-skills/pull/185#issuecomment-321",
                )),
                mock.patch.object(control, "start_check", return_value=created),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "set_check_pointer"),
                mock.patch.object(control, "build_envelope", side_effect=[first, second]),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check"),
                mock.patch.object(control, "confirm_completed_gate_check") as confirm_completed,
                mock.patch.object(control, "update_check") as update,
            ):
                with self.assertRaises(control.validator.ExactHeadMergeReviewError):
                    control.run(args)
            self.assertEqual("failure", update.call_args.args[2])
            self.assertEqual("failure", confirm_completed.call_args.args[4])

    def test_existing_success_is_invalidated_before_receipt_collection_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            event = root / "event.json"
            event.write_text('{"pull_request":{"number":185}}', encoding="utf-8")
            args = control.parse_args([
                "--repository", "jeffery777/codex-dev-skills",
                "--event-path", str(event), "--output", str(root / "out.json"),
                "--policy", str(ROOT / ".github/exact-head-merge-readiness-policy.json"),
                "--workflow-name", "Exact-Head Merge Readiness Controller",
                "--workflow-run-id", "900",
                "--run-url", "https://github.com/jeffery777/codex-dev-skills/actions/runs/900",
                "--expected-head", "b" * 40,
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ])
            head = "b" * 40
            pointer = control.pointer_value(
                "jeffery777/codex-dev-skills", 185, head, 321, 1, 7, "c" * 64,
            )
            fake = mock.Mock()
            fake.json.return_value = {"head": {"sha": head}}
            order: list[str] = []

            def start(*unused: object, **unused_kwargs: object) -> dict[str, object]:
                order.append("invalidate")
                self.assertTrue(str(unused[-1]).endswith(":" + "c" * 64))
                return {"id": 902, "app": {"id": 100001, "slug": "exact-head-gate"}}

            def select(*unused: object, **unused_kwargs: object) -> tuple[None, None]:
                order.append("collect")
                raise control.ControlPlaneError("comment collection exceeds 500 items")

            def update(*unused: object, **unused_kwargs: object) -> dict[str, object]:
                order.append("fail")
                return {}

            with (
                mock.patch.dict(
                    "os.environ",
                    {
                        "EXACT_HEAD_GATE_TOKEN": "secret",
                        "REPOSITORY_READ_TOKEN": "read-only",
                    },
                ),
                mock.patch.object(control, "GitHubClient", return_value=fake),
                mock.patch.object(control, "find_gate_check", return_value={
                    "id": 901, "status": "completed", "conclusion": "success",
                    "external_id": pointer,
                }),
                mock.patch.object(control, "start_check", side_effect=start),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check"),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "select_current_receipt", side_effect=select),
                mock.patch.object(control, "update_check", side_effect=update),
                mock.patch.object(control, "confirm_completed_gate_check"),
            ):
                with self.assertRaisesRegex(control.ControlPlaneError, "exceeds 500"):
                    control.run(args)
            self.assertEqual(["invalidate", "collect", "fail"], order)

    def identity_fixture(self):
        head = "a" * 40
        pointer = control.pointer_value("o/r", 185, head, None, None, 1)
        live = {"id": 9, "name": control.validator.GATE_CONTEXT, "head_sha": head,
                "app": {"id": 10, "slug": "gate-app"}, "status": "in_progress",
                "external_id": pointer}
        gate = {"check_run_id": 9, "check_app_id": 10, "check_app_slug": "gate-app"}
        client = mock.Mock()
        client.repo_path.side_effect = lambda suffix: "/repos/o/r" + suffix
        client.json.return_value = live
        return client, gate, head, pointer

    def test_identity_diagnostics_preserve_matching_json_and_single_get(self) -> None:
        client, gate, head, pointer = self.identity_fixture()
        live = client.json.return_value
        encoded = json.dumps(dict(reversed(list(live.items()))), indent=3).replace("Exact-Head", r"Exact\u002dHead")
        client.json.return_value = json.loads(encoded)
        control.confirm_gate_check(client, gate, head, pointer)
        client.json.assert_called_once_with("GET", "/repos/o/r/check-runs/9")

    def test_identity_diagnostics_reject_each_changed_field_without_normalizing(self) -> None:
        cases = [("id", "9"), ("name", "different-context"), ("head_sha", "b" * 40),
                 ("app_id", 11), ("app_slug", "different-app"), ("status", "queued"),
                 ("external_id", "different-pointer")]
        for field, value in cases:
            with self.subTest(field=field):
                client, gate, head, pointer = self.identity_fixture()
                live = client.json.return_value
                if field == "app_id":
                    live["app"]["id"] = value
                elif field == "app_slug":
                    live["app"]["slug"] = value
                else:
                    live[field] = value
                with self.assertRaises(control.ControlPlaneError) as caught:
                    control.confirm_gate_check(client, gate, head, pointer)
                detail = json.loads(str(caught.exception).split("; diagnostics=", 1)[1])
                self.assertEqual([field], list(detail))
                self.assertIn("type", detail[field]["actual"])
                client.json.assert_called_once_with("GET", "/repos/o/r/check-runs/9")

    def test_pointer_diagnostics_compare_segments_without_printing_them(self) -> None:
        client, gate, head, old_pointer = self.identity_fixture()
        expected = control.pointer_value("o/r", 185, head, 71, 2, 3, "c" * 64)
        with self.assertRaises(control.ControlPlaneError) as caught:
            control.confirm_gate_check(client, gate, head, expected)
        message = str(caught.exception)
        detail = json.loads(message.split("; diagnostics=", 1)[1])["external_id"]
        self.assertEqual({"repository_marker": True, "pr_number": True, "head_sha": True,
                          "receipt_id": False, "receipt_sequence": False,
                          "generation": False, "receipt_digest": False}, detail["component_equal"])
        self.assertTrue(detail["expected"]["digest_present"])
        self.assertFalse(detail["actual"]["digest_present"])
        for text in (expected, old_pointer, head, "c" * 64):
            self.assertNotIn(text, message)

    def test_identity_diagnostics_redact_both_sides_and_bound_arbitrary_values(self) -> None:
        secret = "not-for-public-logs\n" + "private-fixture-text" * 10000
        fields = ("id", "name", "head_sha", "app_id", "app_slug", "status", "external_id")
        for value in (secret, {"Authorization": secret}, [secret], None, True, 1.25):
            with self.subTest(kind=type(value).__name__):
                expected = {field: secret + "expected" for field in fields}
                actual = {field: value for field in fields}
                expected["unrecognized-field"] = secret
                actual["unrecognized-field"] = secret
                diagnostic = control.identity_mismatch_diagnostics(expected, actual)
                text = json.dumps(diagnostic, sort_keys=True)
                self.assertLess(len(text), 4096)
                for forbidden in ("not-for-public-logs", "private-fixture-text", "Authorization", "unrecognized-field",
                                  control.hashlib.sha256(secret.encode()).hexdigest()):
                    self.assertNotIn(forbidden, text)
                self.assertEqual(set(fields), set(diagnostic))
                self.assertEqual("string", diagnostic["external_id"]["expected"]["type"])
                self.assertFalse(diagnostic["external_id"]["expected"]["pointer_shape"])

    def test_identity_diagnostic_failure_is_safe_in_app_summary_and_stderr(self) -> None:
        client, gate, head, pointer = self.identity_fixture()
        sensitive = "not-for-public-logs" * 1000
        client.json.return_value["status"] = sensitive
        with self.assertRaises(control.ControlPlaneError) as caught:
            control.confirm_gate_check(client, gate, head, pointer)
        with tempfile.TemporaryDirectory() as directory:
            result, out, err, output, update, *_ = self.exercise_cli_block(
                directory, identity_error=caught.exception,
            )
        self.assertEqual(1, result)
        self.assertEqual("", out)
        self.assertFalse(output.exists())
        self.assertNotIn("not-for-public-logs", err)
        self.assertNotIn("not-for-public-logs", update.call_args.args[4])
        self.assertIn("diagnostics=", err)
        self.assertIn("diagnostics=", update.call_args.args[4])
        self.assertEqual("failure", update.call_args.args[2])

    def test_identity_diagnostic_preserves_existing_numeric_equality(self) -> None:
        for expected_id, actual_id in ((9, 9.0), (1, True)):
            with self.subTest(expected=expected_id, actual_type=type(actual_id).__name__):
                client, gate, head, pointer = self.identity_fixture()
                gate["check_run_id"] = expected_id
                client.json.return_value["id"] = actual_id
                control.confirm_gate_check(client, gate, head, pointer)
                self.assertEqual(1, client.json.call_count)

    def test_pointer_diagnostic_checks_length_before_shape_without_normalizing(self) -> None:
        suffix = ":" + "b" * 40 + ":1:1:1:" + "c" * 64
        prefix = "ehr1:" + "a" * 16 + ":"
        at_limit = prefix + "1" * (255 - len(prefix) - len(suffix)) + suffix
        self.assertEqual(255, len(at_limit))
        client, gate, head, pointer = self.identity_fixture()
        expected = {"id": 9, "name": control.validator.GATE_CONTEXT, "head_sha": head,
                    "app_id": 10, "app_slug": "gate-app", "status": "in_progress",
                    "external_id": pointer}
        for value, shape in ((at_limit, True), (at_limit + "d", False)):
            with self.subTest(length=len(value)):
                actual = dict(expected, external_id=value)
                detail = control.identity_mismatch_diagnostics(expected, actual)["external_id"]
                self.assertEqual(shape, detail["actual"]["pointer_shape"])
                self.assertNotIn(value, json.dumps(detail))
                self.assertLess(len(json.dumps(detail)), 4096)

    def test_completed_check_requires_exact_success_and_failure_readback(self) -> None:
        client = mock.Mock()
        client.repo_path.side_effect = lambda suffix: "/repos/o/r" + suffix
        client.json.return_value = {
            "id": 9, "name": control.validator.GATE_CONTEXT, "head_sha": "a" * 40,
            "app": {"id": 10, "slug": "gate"}, "status": "completed",
            "conclusion": "success", "external_id": "pointer",
            "details_url": "https://github.com/o/r/actions/runs/1",
            "output": {"title": "ready", "summary": "digest"},
        }
        gate = {
            "check_run_id": 9, "check_app_id": 10, "check_app_slug": "gate",
            "details_url": "https://github.com/o/r/actions/runs/1",
        }
        control.confirm_completed_gate_check(
            client, gate, "a" * 40, "pointer", "success", "ready", "digest",
        )
        client.json.return_value["conclusion"] = "failure"
        control.confirm_completed_gate_check(
            client, gate, "a" * 40, "pointer", "failure", "ready", "digest",
        )
        client.json.return_value["external_id"] = "drifted"
        with self.assertRaisesRegex(control.ControlPlaneError, "did not survive"):
            control.confirm_completed_gate_check(
                client, gate, "a" * 40, "pointer", "success", "ready", "digest",
            )

    def test_fresh_check_must_remain_authoritative_latest(self) -> None:
        gate = {
            "check_run_id": 9,
            "check_app_id": 10,
            "check_app_slug": "gate",
        }
        client = mock.Mock()
        with mock.patch.object(
            control, "find_gate_check", return_value={"id": 9}
        ):
            control.confirm_latest_gate_check(client, gate, "a" * 40)
        with mock.patch.object(
            control, "find_gate_check", return_value={"id": 8}
        ):
            with self.assertRaisesRegex(
                control.ControlPlaneError, "authoritative latest"
            ):
                control.confirm_latest_gate_check(client, gate, "a" * 40)


class WorkflowTransitionTests(unittest.TestCase):
    POLICY = ROOT / ".github/exact-head-merge-readiness-policy.json"

    def setUp(self) -> None:
        # A bridge fixture is independent of the deployed phase: after rollout
        # the repository policy is ordinary v1 and has no transition object.
        self.policy = control.parse_policy(json.dumps({
            "contract": "exact-head-merge-readiness-policy/v2",
            "check_context": "Exact-Head Merge Readiness",
            "receipt_contract": "exact-head-merge-readiness/v2",
            "required_upstream_workflows": [{
                "check_context": "Validate repository", "workflow_name": "Repository Validation",
                "workflow_id": 330877463, "workflow_path": ".github/workflows/repository-validation.yml",
                "event": "pull_request", "run_name_contract": "exact-pr-head/v1",
                "workflow_blob_sha": "0c84c54137596641b6096c0c10abe2c85f74ffaa",
            }],
            "required_ci_policy": {"source": "repository_policy", "reference": ".github/exact-head-merge-readiness-policy.json"},
            "trusted_receipt_author_associations": ["OWNER"],
            "max_api_response_bytes": 10485760, "max_receipt_bytes": 262144,
            "workflow_transition": {
                "contract": "exact-head-workflow-transition/v1", "repository": "jeffery777/codex-dev-skills",
                "pr_number": 388, "workflow_id": 330877463,
                "workflow_path": ".github/workflows/repository-validation.yml", "event": "pull_request",
                "old_workflow_blob_sha": "0c84c54137596641b6096c0c10abe2c85f74ffaa",
                "new_workflow_blob_sha": "7d5d362bf83444554f0a25d9974e09fc22c6d194",
            },
        }).encode())
        self.transition = self.policy["workflow_transition"]
        self.old = self.transition["old_workflow_blob_sha"]
        self.new = self.transition["new_workflow_blob_sha"]
        self.repository = self.transition["repository"]

    def test_active_policy_matches_its_workflow_in_either_deployed_phase(self) -> None:
        active = control.load_policy(self.POLICY)
        blob = control.policy_blob_sha((ROOT / ".github/workflows/repository-validation.yml").read_bytes())
        self.assertEqual(blob, active["required_upstream_workflows"][0]["workflow_blob_sha"])
        if active["contract"] == "exact-head-merge-readiness-policy/v2":
            self.assertEqual(self.transition, active["workflow_transition"])
        else:
            self.assertEqual("exact-head-merge-readiness-policy/v1", active["contract"])
            self.assertNotIn("workflow_transition", active)

    def test_policy_versions_remain_strict(self) -> None:
        normal = dict(self.policy)
        normal.pop("workflow_transition")
        normal["contract"] = "exact-head-merge-readiness-policy/v1"
        self.assertEqual(normal, control.parse_policy(json.dumps(normal).encode()))
        cases = []
        for key, value in (("pr_number", True), ("pr_number", 0), ("pr_number", "388"),
                           ("workflow_id", True), ("workflow_id", 1), ("repository", "bad"),
                           ("workflow_path", "other.yml"), ("event", "push"),
                           ("old_workflow_blob_sha", self.new), ("new_workflow_blob_sha", self.old),
                           ("new_workflow_blob_sha", "unknown"), ("extra", True)):
            candidate = json.loads(json.dumps(self.policy))
            candidate["workflow_transition"][key] = value
            cases.append(candidate)
        for value in (None, [], {}):
            cases.append({**self.policy, "workflow_transition": value})
        cases.extend(({**normal, "workflow_transition": self.transition},
                      {**self.policy, "extra": True},
                      {**normal, "contract": "exact-head-merge-readiness-policy/v2"}))
        for candidate in cases:
            with self.subTest(candidate=candidate), self.assertRaises((ValueError, control.ControlPlaneError)):
                control.parse_policy(json.dumps(candidate).encode())
        duplicate = json.dumps(self.policy).replace('"pr_number": 388', '"pr_number": 388, "pr_number": 389')
        with self.assertRaisesRegex(control.ControlPlaneError, "strict JSON"):
            control.parse_policy(duplicate.encode())

    def resolve(self, pair, *, pr=388, repository=None, policy=None):
        reader = mock.Mock()
        reader.repo_path.side_effect = lambda suffix: suffix
        reader.json.side_effect = [{"sha": value} for value in pair]
        return control.resolve_workflow_policy(reader, repository or self.repository, pr,
                                               "a" * 40, "b" * 40, policy or self.policy)

    def test_pair_admission_and_digest_are_bounded_without_mutation(self) -> None:
        original = json.dumps(self.policy, sort_keys=True)
        normal = self.resolve([self.old, self.old], pr=999)
        self.assertEqual(self.policy["required_ci_policy"], normal["required_ci_policy"])
        effective = self.resolve([self.old, self.new])
        self.assertEqual(self.new, effective["required_upstream_workflows"][0]["workflow_blob_sha"])
        self.assertEqual(
            self.policy["required_ci_policy"]["reference"] + "#transition-sha256=" + control.canonical_digest(self.transition),
            effective["required_ci_policy"]["reference"],
        )
        self.assertEqual(original, json.dumps(self.policy, sort_keys=True))
        for pair, pr, repository in (([self.old, self.new], 389, self.repository),
                                     ([self.new, self.new], 388, self.repository),
                                     ([self.new, self.old], 388, self.repository),
                                     ([self.old, "0" * 40], 388, self.repository),
                                     (["0" * 40, self.new], 388, self.repository),
                                     ([self.old, self.old], 388, "other/repo")):
            with self.subTest(pair=pair, pr=pr), self.assertRaises(control.ControlPlaneError):
                self.resolve(pair, pr=pr, repository=repository)
        final = json.loads(json.dumps(self.policy))
        final.pop("workflow_transition")
        final["contract"] = "exact-head-merge-readiness-policy/v1"
        final["required_upstream_workflows"][0]["workflow_blob_sha"] = self.new
        final = control.parse_policy(json.dumps(final).encode())
        self.assertEqual(self.new, self.resolve([self.new, self.new], policy=final)["required_upstream_workflows"][0]["workflow_blob_sha"])
        with self.assertRaises(control.ControlPlaneError):
            self.resolve([self.old, self.new], policy=final)

    def test_current_policy_uses_repository_read_source_and_exact_bytes(self) -> None:
        data = self.POLICY.read_bytes()
        blob = control.policy_blob_sha(data)
        self.assertNotEqual(blob, control.policy_blob_sha(data + b"\n"))
        path = "policies/custom-policy.json"
        reader = mock.Mock()
        reader.repo_path.side_effect = lambda suffix: "/repos/other/project" + suffix
        metadata = {"full_name": "other/project", "default_branch": "release/main"}
        content = {"type": "file", "path": path, "sha": blob}
        reader.json.side_effect = [metadata, content]
        control.confirm_current_policy(reader, "other/project", path, blob)
        self.assertEqual("/repos/other/project/contents/policies/custom-policy.json?ref=refs%2Fheads%2Frelease%2Fmain", reader.json.call_args.args[1])
        for responses in ([{}, content], [{**metadata, "full_name": "wrong/repo"}, content],
                          [{**metadata, "default_branch": None}, content], [metadata, None],
                          [metadata, {**content, "type": "symlink"}],
                          [metadata, {**content, "path": "other.json"}],
                          [metadata, {**content, "sha": "0" * 40}],
                          [control.ControlPlaneError("metadata unavailable")],
                          [metadata, control.ControlPlaneError("contents unavailable")]):
            reader.json.side_effect = responses
            with self.subTest(responses=responses), self.assertRaises((ValueError, control.ControlPlaneError)):
                control.confirm_current_policy(reader, "other/project", path, blob)

    def fixture(self):
        payload = valid_v2_payload()
        receipt = payload["receipt"]
        base, head, merge_base = (receipt[name] for name in ("reviewed_base_sha", "reviewed_head_sha", "reviewed_merge_base_sha"))
        receipt["pr_number"] = 388
        receipt["reviewed_range_identity_digest"] = control.validator.canonical_range_identity_digest(self.repository, 388, base, head, merge_base)
        expected = dict(self.policy["required_upstream_workflows"][0], workflow_blob_sha=self.new)
        receipt["required_ci"][0].update(expected)
        receipt["required_ci"][0]["run_display_title"] = f"Repository Validation PR #388 @ {head}"
        receipt["required_ci_policy"] = {
            **self.policy["required_ci_policy"], "required_workflows": [expected],
            "reference": self.policy["required_ci_policy"]["reference"] + "#transition-sha256=" + control.canonical_digest(self.transition),
        }
        app, reader = mock.Mock(), mock.Mock()
        app.repository = reader.repository = self.repository
        app.repo_path.side_effect = reader.repo_path.side_effect = lambda suffix: "/repos/" + self.repository + suffix
        def app_json(method, path, **kwargs):
            if path.endswith("/pulls/388"):
                return {"base": {"sha": base}, "head": {"sha": head}, "state": "open", "draft": False, "mergeable": True}
            if "/actions/workflows/" in path:
                return {"id": expected["workflow_id"], "name": expected["workflow_name"], "path": expected["workflow_path"], "state": "active"}
            raise AssertionError("unexpected App endpoint " + path)
        def reader_json(method, path, **kwargs):
            if "/compare/" in path:
                return {"merge_base_commit": {"sha": merge_base}}
            if "/contents/" in path:
                return {"sha": self.old if path.endswith(base) else self.new}
            raise AssertionError("unexpected reader endpoint " + path)
        app.json.side_effect, reader.json.side_effect = app_json, reader_json
        app.json_object_array_pages.return_value = [{
            "id": 456, "run_attempt": 1, "workflow_id": expected["workflow_id"],
            "display_title": receipt["required_ci"][0]["run_display_title"], "head_sha": head,
            "html_url": receipt["required_ci"][0]["details_url"], "path": expected["workflow_path"],
            "event": "pull_request", "status": "completed", "conclusion": "success",
        }]
        return payload, app, reader

    def build(self, payload, app, reader):
        with (mock.patch.object(control, "select_current_receipt", return_value=(321, 1)),
              mock.patch.object(control, "get_receipt", return_value=(payload["receipt"], 321,
                  f"https://github.com/{self.repository}/pull/388#issuecomment-321")),
              mock.patch.object(control, "collect_threads", return_value=(0, control.canonical_digest([])))):
            return control.build_envelope(app, reader, 388, 321, 1, self.policy, payload["gate"])

    def test_real_loader_builder_and_v2_validator_share_effective_policy(self) -> None:
        payload, app, reader = self.fixture()
        envelope = self.build(payload, app, reader)
        control.validator.validate_payload(envelope)
        self.assertEqual(payload["receipt"]["required_ci_policy"], envelope["platform_snapshot"]["required_ci_policy"])
        self.assertEqual(2, sum("/contents/" in call.args[1] for call in reader.json.call_args_list))
        payload["receipt"]["required_ci_policy"]["reference"] += "stale"
        with self.assertRaises(ValueError):
            control.validator.validate_payload(self.build(payload, app, reader))
        payload, app, reader = self.fixture()
        payload["receipt"]["required_ci"][0]["workflow_blob_sha"] = self.old
        with self.assertRaises(ValueError):
            control.validator.validate_payload(self.build(payload, app, reader))

    def test_latest_failure_and_missing_run_never_reuse_success(self) -> None:
        payload, app, reader = self.fixture()
        success = app.json_object_array_pages.return_value[0]
        app.json_object_array_pages.return_value = [success, {**success, "id": 457,
            "html_url": f"https://github.com/{self.repository}/actions/runs/457", "conclusion": "failure"}]
        with self.assertRaises(control.ReadinessBlocked):
            self.build(payload, app, reader)

        app.json_object_array_pages.return_value = []
        with self.assertRaises(control.ReadinessBlocked):
            self.build(payload, app, reader)

    def exercise_run(self, *, fault_stage=None, fault="retired", normal=False,
                     publication_fault=False, readback_fault=False):
        payload, app, reader = self.fixture()
        policy = json.loads(json.dumps(self.policy))
        if normal:
            policy.pop("workflow_transition")
            policy["contract"] = "exact-head-merge-readiness-policy/v1"
            policy["required_upstream_workflows"][0]["workflow_blob_sha"] = self.new
            payload["receipt"]["required_ci_policy"]["reference"] = policy["required_ci_policy"]["reference"]
        data = (json.dumps(policy, indent=2) + "\n").encode()
        policy_blob = control.policy_blob_sha(data)
        reference = policy["required_ci_policy"]["reference"]
        trace = []
        stage = 0
        ordinary_reader = reader.json.side_effect

        def read(method, path, **kwargs):
            nonlocal stage
            if path == f"/repos/{self.repository}":
                stage += 1
                trace.append(f"metadata:{stage}")
                if stage == fault_stage and fault == "metadata":
                    raise control.ControlPlaneError("metadata unavailable")
                return {"full_name": self.repository, "default_branch": "main"}
            if f"/contents/{reference}?ref=" in path:
                trace.append(f"policy:{stage}")
                self.assertTrue(path.endswith("?ref=refs%2Fheads%2Fmain"))
                if stage == fault_stage and fault == "contents":
                    raise control.ControlPlaneError("contents unavailable")
                blob = policy_blob
                if stage == fault_stage and fault == "retired":
                    blob = "0" * 40
                if stage == fault_stage and fault == "same_json_different_bytes":
                    blob = control.policy_blob_sha(json.dumps(policy).encode())
                return {"type": "file", "path": reference, "sha": blob}
            if normal and "/contents/" in path:
                return {"sha": self.new}
            return ordinary_reader(method, path, **kwargs)

        def start(*args):
            trace.append("start")
            return {"id": 901, "app": {"id": 100001, "slug": "exact-head-gate"}}

        def update(*args):
            trace.append("publish:" + args[2])
            if args[2] == "failure" and publication_fault:
                raise control.ControlPlaneError("failure publication unavailable")

        def completed(*args):
            trace.append("completed:" + args[4])
            if args[4] == "failure" and readback_fault:
                raise control.ControlPlaneError("failure readback unavailable")

        reader.json.side_effect = read
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            policy_path, event_path, output = root / "policy.json", root / "event.json", root / "output.json"
            policy_path.write_bytes(data)
            event_path.write_text('{"pull_request":{"number":388}}')
            argv = [
                "--repository", self.repository, "--pr-number", "388",
                "--policy", str(policy_path), "--event-path", str(event_path), "--output", str(output),
                "--workflow-name", "Exact-Head Merge Readiness Controller", "--workflow-run-id", "900",
                "--run-url", f"https://github.com/{self.repository}/actions/runs/900",
                "--expected-head", payload["receipt"]["reviewed_head_sha"],
                "--expected-app-id", "100001", "--expected-app-slug", "exact-head-gate",
            ]
            stdout, stderr = io.StringIO(), io.StringIO()
            with (
                mock.patch.dict("os.environ", {"EXACT_HEAD_GATE_TOKEN": "app", "REPOSITORY_READ_TOKEN": "reader"}),
                mock.patch.object(control, "GitHubClient", side_effect=[app, reader]) as clients,
                mock.patch.object(control, "read_bounded_regular_file", wraps=control.read_bounded_regular_file) as reads,
                mock.patch.object(control, "find_gate_check", return_value=None),
                mock.patch.object(control, "start_check", side_effect=start),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_latest_gate_check", side_effect=lambda *args: trace.append("latest")),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "select_current_receipt", return_value=(321, 1)),
                mock.patch.object(control, "get_receipt", return_value=(payload["receipt"], 321,
                    f"https://github.com/{self.repository}/pull/388#issuecomment-321")),
                mock.patch.object(control, "collect_threads", return_value=(0, control.canonical_digest([]))),
                mock.patch.object(control, "set_check_pointer"),
                mock.patch.object(control, "update_check", side_effect=update),
                mock.patch.object(control, "confirm_completed_gate_check", side_effect=completed),
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr),
            ):
                result = control.main(argv)
            self.assertEqual(["app", "reader"], [call.args[1] for call in clients.call_args_list])
            self.assertEqual(1, sum(call.args[0] == policy_path for call in reads.call_args_list))
            self.assertFalse(any("/contents/" in call.args[1] or call.args[1] == f"/repos/{self.repository}"
                                 for call in app.json.call_args_list))
            self.assertLess(trace.index("start"), trace.index("metadata:1"))
            emitted = json.loads(output.read_text()) if output.exists() else None
            return result, stdout.getvalue(), stderr.getvalue(), emitted, trace

    def test_run_checks_real_policy_source_three_times_in_both_modes(self) -> None:
        for normal in (False, True):
            with self.subTest(normal=normal):
                result, _, error, emitted, trace = self.exercise_run(normal=normal)
                self.assertEqual(0, result, error)
                control.validator.validate_payload(emitted)
                self.assertEqual(["metadata:1", "policy:1", "metadata:2", "policy:2", "metadata:3", "policy:3"],
                                 [item for item in trace if item.startswith(("metadata:", "policy:"))])
                self.assertLess(trace.index("policy:2"), trace.index("publish:success"))
                self.assertLess(trace.index("publish:success"), trace.index("completed:success"))
                self.assertEqual("latest", trace[trace.index("metadata:3") - 1])
                self.assertLess(trace.index("completed:success"), trace.index("metadata:3"))
                self.assertNotIn("publish:failure", trace)
                reference = emitted["platform_snapshot"]["required_ci_policy"]["reference"]
                self.assertEqual(not normal, "#transition-sha256=" in reference)

    def test_run_policy_drift_or_api_fault_fails_at_every_freshness_boundary(self) -> None:
        for stage in (1, 2, 3):
            for fault in ("retired", "metadata", "contents", "same_json_different_bytes"):
                with self.subTest(stage=stage, fault=fault):
                    result, _, error, emitted, trace = self.exercise_run(fault_stage=stage, fault=fault)
                    self.assertEqual(1, result)
                    self.assertIsNone(emitted)
                    self.assertTrue(error)
                    self.assertIn("publish:failure", trace)
                    self.assertEqual(["completed:failure", "latest"], trace[-2:])
                    self.assertEqual(stage == 3, "publish:success" in trace)
                    self.assertEqual(stage, sum(item.startswith("metadata:") for item in trace))

    def test_run_freshness_failure_does_not_hide_publication_or_readback_fault(self) -> None:
        for name in ("publication_fault", "readback_fault"):
            with self.subTest(name=name):
                result, _, error, emitted, trace = self.exercise_run(fault_stage=3, **{name: True})
                self.assertEqual(1, result)
                self.assertIsNone(emitted)
                self.assertIn("failed to publish authoritative gate failure", error)
                self.assertEqual(1, trace.count("publish:failure"))
if __name__ == "__main__":
    unittest.main()
