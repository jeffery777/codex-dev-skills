#!/usr/bin/env python3
"""Validate that a ready pull request closes an open Issue in this repository."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any


MAX_EVENT_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
MAX_ISSUE_REFERENCES = 20
API_TIMEOUT_SECONDS = 10.0
CLOSING_LINE = re.compile(
    r"(?im)^[ \t]*(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)[ \t]+"
    r"#([1-9][0-9]*)[ \t]*[.!]?[ \t]*$"
)
EXTERNAL_CLOSING_LINE = re.compile(
    r"(?im)^[ \t]*(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)[ \t]+"
    r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#[1-9][0-9]*|"
    r"https://[^ \t]+/issues/[1-9][0-9]*)[ \t]*[.!]?[ \t]*$"
)
IssueFetcher = Callable[[str, int], dict[str, Any]]


class PullRequestLinkError(ValueError):
    """Raised when PR-to-Issue linkage is missing or invalid."""


def extract_issue_numbers(body: str) -> tuple[int, ...]:
    """Return unique same-repository closing references in source order."""

    seen: set[int] = set()
    result: list[int] = []
    for match in CLOSING_LINE.finditer(body):
        number = int(match.group(1))
        if number not in seen:
            seen.add(number)
            result.append(number)
    return tuple(result)


def load_event(path: pathlib.Path) -> dict[str, Any]:
    try:
        metadata = path.stat()
    except FileNotFoundError as error:
        raise PullRequestLinkError("event payload is missing") from error
    if not path.is_file() or path.is_symlink():
        raise PullRequestLinkError("event payload must be a regular non-symlink file")
    if metadata.st_size > MAX_EVENT_BYTES:
        raise PullRequestLinkError("event payload exceeds the size limit")
    try:
        document = json.loads(path.read_bytes().decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PullRequestLinkError("event payload must be strict UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise PullRequestLinkError("event payload must be a JSON object")
    return document


def validate_event(
    event: dict[str, Any],
    expected_repository: str,
    fetch_issue: IssueFetcher,
) -> dict[str, Any]:
    repository = event.get("repository")
    pull_request = event.get("pull_request")
    if not isinstance(repository, dict) or not isinstance(pull_request, dict):
        raise PullRequestLinkError("payload must contain repository and pull_request objects")
    repository_name = repository.get("full_name")
    if repository_name != expected_repository:
        raise PullRequestLinkError("event repository does not match the expected repository")

    base = pull_request.get("base")
    if not isinstance(base, dict):
        raise PullRequestLinkError("pull request base is missing")
    base_repository = base.get("repo")
    if not isinstance(base_repository, dict) or base_repository.get("full_name") != expected_repository:
        raise PullRequestLinkError("pull request base repository does not match")

    draft = pull_request.get("draft")
    if not isinstance(draft, bool):
        raise PullRequestLinkError("pull request draft state must be boolean")
    number = pull_request.get("number")
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise PullRequestLinkError("pull request number must be a positive integer")
    if draft:
        return {
            "kind": "pr-issue-link-status",
            "pr_number": number,
            "reason": "draft-pull-request",
            "repository": expected_repository,
            "status": "skipped",
        }

    body = pull_request.get("body")
    if not isinstance(body, str):
        raise PullRequestLinkError("ready pull request body must be a string")
    if EXTERNAL_CLOSING_LINE.search(body):
        raise PullRequestLinkError(
            "closing Issue references must use same-repository #<issue> form"
        )
    issue_numbers = extract_issue_numbers(body)
    if not issue_numbers:
        raise PullRequestLinkError(
            "ready pull request must contain a standalone Closes/Fixes/Resolves #<issue> line"
        )
    if len(issue_numbers) > MAX_ISSUE_REFERENCES:
        raise PullRequestLinkError(
            f"ready pull request exceeds {MAX_ISSUE_REFERENCES} unique Issue references"
        )

    for issue_number in issue_numbers:
        issue = fetch_issue(expected_repository, issue_number)
        if not isinstance(issue, dict):
            raise PullRequestLinkError(f"#{issue_number} did not return an Issue object")
        if issue.get("number") != issue_number:
            raise PullRequestLinkError(f"#{issue_number} identity does not match the response")
        if "pull_request" in issue:
            raise PullRequestLinkError(f"#{issue_number} is a pull request, not an Issue")
        if issue.get("state") != "open":
            raise PullRequestLinkError(f"#{issue_number} is not an open Issue")

    return {
        "issue_numbers": list(issue_numbers),
        "kind": "pr-issue-link-status",
        "pr_number": number,
        "repository": expected_repository,
        "status": "valid",
    }


def github_issue_fetcher(token: str, api_url: str) -> IssueFetcher:
    if not token:
        raise PullRequestLinkError("GITHUB_TOKEN is required for ready pull requests")
    parsed_api = urllib.parse.urlsplit(api_url)
    if (
        parsed_api.scheme != "https"
        or not parsed_api.hostname
        or parsed_api.username is not None
        or parsed_api.password is not None
        or parsed_api.path not in ("", "/")
        or parsed_api.query
        or parsed_api.fragment
    ):
        raise PullRequestLinkError("GitHub API URL must be an HTTPS origin")
    origin = urllib.parse.urlunsplit((parsed_api.scheme, parsed_api.netloc, "", "", ""))

    def fetch(repository: str, issue_number: int) -> dict[str, Any]:
        owner, separator, name = repository.partition("/")
        if not separator or not owner or not name or "/" in name:
            raise PullRequestLinkError("repository must use owner/name form")
        url = (
            f"{origin}/repos/{urllib.parse.quote(owner, safe='')}/"
            f"{urllib.parse.quote(name, safe='')}/issues/{issue_number}"
        )
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "codex-dev-skills-pr-link-validator",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=API_TIMEOUT_SECONDS) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                raise PullRequestLinkError(f"#{issue_number} does not exist") from error
            raise PullRequestLinkError(
                f"GitHub API rejected Issue #{issue_number} lookup with HTTP {error.code}"
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise PullRequestLinkError(
                f"GitHub API lookup failed for Issue #{issue_number}"
            ) from error
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PullRequestLinkError(f"GitHub API response for #{issue_number} is too large")
        try:
            document = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PullRequestLinkError(
                f"GitHub API response for #{issue_number} is invalid"
            ) from error
        if not isinstance(document, dict):
            raise PullRequestLinkError(f"GitHub API response for #{issue_number} is not an object")
        return document

    return fetch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", required=True, type=pathlib.Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--api-url", default="https://api.github.com")
    arguments = parser.parse_args(argv)
    try:
        event = load_event(arguments.event_path)
        pull_request = event.get("pull_request")
        draft = pull_request.get("draft") if isinstance(pull_request, dict) else None
        token = os.environ.get("GITHUB_TOKEN", "") if draft is False else ""
        fetch_issue = (
            github_issue_fetcher(token, arguments.api_url)
            if draft is False
            else lambda _repository, _number: {}
        )
        result = validate_event(event, arguments.repository, fetch_issue)
    except PullRequestLinkError as error:
        print(
            json.dumps(
                {
                    "kind": "pr-issue-link-status",
                    "reason": str(error),
                    "status": "invalid",
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
