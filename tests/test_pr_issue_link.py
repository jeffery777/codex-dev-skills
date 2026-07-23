from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate-pr-issue-link.py"
SPEC = importlib.util.spec_from_file_location("validate_pr_issue_link", SCRIPT)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


REPOSITORY = "example/project"


def event(
    body: object = "Closes #109",
    *,
    draft: object = False,
    number: object = 110,
    repository: str = REPOSITORY,
    base_repository: str | None = None,
) -> dict[str, object]:
    return {
        "repository": {"full_name": repository},
        "pull_request": {
            "base": {"repo": {"full_name": base_repository or repository}},
            "body": body,
            "draft": draft,
            "number": number,
        },
    }


class PullRequestIssueLinkTests(unittest.TestCase):
    def fetcher(self, states: dict[int, str] | None = None):
        values = {109: "open"} if states is None else states

        def fetch(_repository: str, number: int) -> dict[str, object]:
            if number not in values:
                raise VALIDATOR.PullRequestLinkError(f"#{number} does not exist")
            return {"number": number, "state": values[number]}

        return fetch

    def test_supported_closing_keywords_and_multiple_references(self) -> None:
        body = "Fixes #109\nResolves #111.\ncloses #109"
        result = VALIDATOR.validate_event(
            event(body),
            REPOSITORY,
            self.fetcher({109: "open", 111: "open"}),
        )
        self.assertEqual("valid", result["status"])
        self.assertEqual([109, 111], result["issue_numbers"])

    def test_draft_is_skipped_without_lookup(self) -> None:
        def unexpected(_repository: str, _number: int) -> dict[str, object]:
            self.fail("draft validation must not query Issue metadata")

        result = VALIDATOR.validate_event(
            event("", draft=True),
            REPOSITORY,
            unexpected,
        )
        self.assertEqual("skipped", result["status"])

    def test_missing_placeholder_and_external_reference_fail(self) -> None:
        missing_bodies = (
            "",
            "Closes #ISSUE_NUMBER",
            "Related to #109",
            "Text before Closes #109 on one line",
        )
        for body in missing_bodies:
            with self.subTest(body=body), self.assertRaisesRegex(
                VALIDATOR.PullRequestLinkError,
                "standalone",
            ):
                VALIDATOR.validate_event(event(body), REPOSITORY, self.fetcher())

        external_bodies = (
            "Closes example/project#109",
            "Closes https://example.test/owner/repository/issues/109",
            "Closes #109\nFixes another/project#111",
        )
        for body in external_bodies:
            with self.subTest(body=body), self.assertRaisesRegex(
                VALIDATOR.PullRequestLinkError,
                "same-repository",
            ):
                VALIDATOR.validate_event(event(body), REPOSITORY, self.fetcher())

    def test_closed_missing_and_pull_request_numbers_fail(self) -> None:
        with self.assertRaisesRegex(VALIDATOR.PullRequestLinkError, "not an open"):
            VALIDATOR.validate_event(
                event(),
                REPOSITORY,
                self.fetcher({109: "closed"}),
            )

        with self.assertRaisesRegex(VALIDATOR.PullRequestLinkError, "does not exist"):
            VALIDATOR.validate_event(event(), REPOSITORY, self.fetcher({}))

        def pull_request(_repository: str, number: int) -> dict[str, object]:
            return {"number": number, "state": "open", "pull_request": {}}

        with self.assertRaisesRegex(VALIDATOR.PullRequestLinkError, "pull request"):
            VALIDATOR.validate_event(event(), REPOSITORY, pull_request)

    def test_issue_reference_count_is_bounded_before_lookup(self) -> None:
        body = "\n".join(
            f"Closes #{number}"
            for number in range(1, VALIDATOR.MAX_ISSUE_REFERENCES + 2)
        )

        def unexpected(_repository: str, _number: int) -> dict[str, object]:
            self.fail("an oversized reference set must fail before API lookup")

        with self.assertRaisesRegex(
            VALIDATOR.PullRequestLinkError,
            "exceeds",
        ):
            VALIDATOR.validate_event(event(body), REPOSITORY, unexpected)

    def test_repository_identity_and_event_shapes_fail_closed(self) -> None:
        cases = (
            (event(repository="other/project"), "event repository"),
            (event(base_repository="other/project"), "base repository"),
            (event(draft="false"), "draft state"),
            (event(number=True), "positive integer"),
            (event(body=None), "body must be a string"),
            ({"repository": {"full_name": REPOSITORY}}, "must contain"),
        )
        for document, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(
                VALIDATOR.PullRequestLinkError,
                message,
            ):
                VALIDATOR.validate_event(document, REPOSITORY, self.fetcher())

    def test_cli_malformed_event_fails_without_traceback(self) -> None:
        document = {
            "repository": {"full_name": REPOSITORY},
            "pull_request": [],
        }
        with tempfile.TemporaryDirectory() as temporary:
            event_path = pathlib.Path(temporary) / "event.json"
            event_path.write_text(json.dumps(document), encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                result = VALIDATOR.main(
                    [
                        "--event-path",
                        str(event_path),
                        "--repository",
                        REPOSITORY,
                    ]
                )
        self.assertEqual(1, result)
        self.assertIn('"status":"invalid"', stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_api_url_must_be_a_credential_free_https_origin(self) -> None:
        invalid_urls = (
            "http://api.example.test",
            "https://user@api.example.test",
            "https://:password@api.example.test",
            "https://api.example.test/v3",
            "https://api.example.test?query=yes",
            "https://api.example.test#fragment",
        )
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaisesRegex(
                VALIDATOR.PullRequestLinkError,
                "HTTPS origin",
            ):
                VALIDATOR.github_issue_fetcher("not-a-real-token", url)

    def test_template_policy_and_workflow_preserve_boundary(self) -> None:
        template = (ROOT / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
        policy = (ROOT / "policies" / "pull-request-issue-linkage-policy.md").read_text(
            encoding="utf-8"
        )
        workflow = (
            ROOT / ".github" / "workflows" / "pr-issue-link.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("Closes #ISSUE_NUMBER", template)
        self.assertIn("traceability only", policy)
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("github.event.pull_request.base.sha", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("timeout-minutes: 5", workflow)
        self.assertNotIn("github.event.pull_request.head.sha", workflow)
        self.assertNotIn("write", "\n".join(line for line in workflow.splitlines() if ": " in line))


if __name__ == "__main__":
    unittest.main()
