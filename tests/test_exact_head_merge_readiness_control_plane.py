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
        self.assertEqual((99, 7, 3), control.parse_pointer(value, "o/r", 5, "a" * 40))
        self.assertEqual((None, None, 0), control.parse_pointer(value, "o/r", 6, "a" * 40))
        self.assertEqual((None, None, 0), control.parse_pointer(value, "o/r", 5, "b" * 40))
        exhausted = control.pointer_value(
            "o/r", 5, "a" * 40, 99, 7, control.validator.MAX_RECEIPT_SEQUENCE,
        )
        self.assertEqual((None, None, 0), control.parse_pointer(exhausted, "o/r", 5, "a" * 40))
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

    def test_existing_gate_check_is_reopened_instead_of_duplicated(self) -> None:
        client = mock.Mock()
        client.repo_path.side_effect = lambda suffix: "/repos/o/r" + suffix
        client.json.return_value = {"id": 9, "app": {"id": 10, "slug": "gate"}}
        result = control.start_check(
            client,
            {"id": 9},
            "a" * 40,
            control.validator.GATE_CONTEXT,
            "https://github.com/o/r/actions/runs/1",
            "pointer",
        )
        self.assertEqual(9, result["id"])
        self.assertEqual("PATCH", client.json.call_args.args[0])
        self.assertEqual("in_progress", client.json.call_args.kwargs["body"]["status"])
        self.assertNotIn("head_sha", client.json.call_args.kwargs["body"])

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
            "sha": "393848fe55596c4e89969d94f6ba89ce523010d7"
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
            mock.patch.object(control, "collect_upstream_checks", return_value=[]),
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
                mock.patch.object(control, "start_check", return_value=created),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "set_check_pointer"),
                mock.patch.object(control, "build_envelope", side_effect=[first, second]) as collect,
                mock.patch.object(control, "confirm_gate_check") as confirm,
                mock.patch.object(control, "confirm_completed_gate_check") as confirm_completed,
                mock.patch.object(control, "update_check") as update,
            ):
                result = control.run(args)
            self.assertEqual(second, result)
            self.assertEqual(2, collect.call_count)
            self.assertEqual(3, confirm.call_count)
            confirm_completed.assert_called_once()
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
                mock.patch.object(control, "start_check", return_value=created),
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "set_check_pointer"),
                mock.patch.object(control, "build_envelope", side_effect=[first, second]),
                mock.patch.object(control, "confirm_gate_check"),
                mock.patch.object(control, "confirm_completed_gate_check"),
                mock.patch.object(control, "update_check") as update,
            ):
                with self.assertRaises(control.validator.ExactHeadMergeReviewError):
                    control.run(args)
            self.assertEqual("failure", update.call_args.args[2])

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
                return {"id": 901, "app": {"id": 100001, "slug": "exact-head-gate"}}

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
                mock.patch.object(control, "require_unique_open_pr_for_head"),
                mock.patch.object(control, "select_current_receipt", side_effect=select),
                mock.patch.object(control, "update_check", side_effect=update),
            ):
                with self.assertRaisesRegex(control.ControlPlaneError, "exceeds 500"):
                    control.run(args)
            self.assertEqual(["invalidate", "collect", "fail"], order)

    def test_completed_success_requires_exact_platform_readback(self) -> None:
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
            client, gate, "a" * 40, "pointer", "ready", "digest",
        )
        client.json.return_value["external_id"] = "drifted"
        with self.assertRaisesRegex(control.ControlPlaneError, "did not survive"):
            control.confirm_completed_gate_check(
                client, gate, "a" * 40, "pointer", "ready", "digest",
            )


if __name__ == "__main__":
    unittest.main()
