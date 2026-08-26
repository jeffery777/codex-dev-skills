#!/usr/bin/env python3
"""Normalize live GitHub state and publish the dedicated exact-head check.

This is intentionally the networked half of the gate.  It never checks out or
executes pull-request content.  The sibling validator remains offline.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-exact-head-merge-review.py"
SPEC = importlib.util.spec_from_file_location("exact_head_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

POLICY_FIELDS = frozenset(
    (
        "contract", "check_context", "receipt_contract",
        "required_upstream_workflows", "required_ci_policy",
        "trusted_receipt_author_associations",
        "max_api_response_bytes", "max_receipt_bytes",
    )
)
UPSTREAM_POLICY_FIELDS = frozenset(
    (
        "check_context", "workflow_name", "workflow_id", "workflow_path", "event",
        "run_name_contract", "workflow_blob_sha",
    )
)


class ControlPlaneError(RuntimeError):
    """A fail-closed GitHub control-plane collection error."""


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def strict_json(data: bytes, *, maximum: int, label: str) -> object:
    if len(data) > maximum:
        raise ControlPlaneError(f"{label} exceeds size limit")
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=validator.reject_duplicate_json_keys,
            parse_constant=validator.reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ControlPlaneError(f"{label} is not strict JSON") from exc


def read_bounded_regular_file(path: pathlib.Path, *, maximum: int, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    descriptor = os.open(path, flags)
    try:
        mode = os.fstat(descriptor).st_mode
        if not stat.S_ISREG(mode):
            raise ControlPlaneError(f"{label} must be a regular file")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > maximum:
            raise ControlPlaneError(f"{label} exceeds size limit")
        return data
    finally:
        os.close(descriptor)


def load_policy(path: pathlib.Path) -> dict[str, object]:
    raw = strict_json(
        read_bounded_regular_file(path, maximum=256 * 1024, label="policy"),
        maximum=256 * 1024,
        label="policy",
    )
    policy = validator.require_exact_fields(raw, "policy", POLICY_FIELDS)
    if policy["contract"] != "exact-head-merge-readiness-policy/v1":
        raise ControlPlaneError("unsupported policy contract")
    if policy["check_context"] != validator.GATE_CONTEXT:
        raise ControlPlaneError("policy check_context is not the fixed gate context")
    if policy["receipt_contract"] != validator.V2_CONTRACT:
        raise ControlPlaneError("policy receipt_contract is not v2")
    checks = policy["required_upstream_workflows"]
    if not isinstance(checks, list) or not checks:
        raise ControlPlaneError("policy requires at least one upstream check")
    contexts: set[str] = set()
    for index, raw_check in enumerate(checks):
        check = validator.require_exact_fields(raw_check, f"policy.required_upstream_workflows[{index}]", UPSTREAM_POLICY_FIELDS)
        for name in ("check_context", "workflow_name", "workflow_path", "event", "run_name_contract"):
            validator.require_string(check[name], f"policy.required_upstream_workflows[{index}].{name}")
        validator.require_sha(check["workflow_blob_sha"], f"policy.required_upstream_workflows[{index}].workflow_blob_sha")
        if re.fullmatch(r"\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml", str(check["workflow_path"])) is None:
            raise ControlPlaneError("upstream workflow path is not a fixed workflow file")
        if check["event"] != "pull_request" or check["run_name_contract"] != "exact-pr-head/v1":
            raise ControlPlaneError("upstream workflow must use trusted exact-PR-head run naming")
        validator.require_positive_integer(check["workflow_id"], f"policy.required_upstream_workflows[{index}].workflow_id")
        context = check["check_context"]
        if context == validator.GATE_CONTEXT or context in contexts:
            raise ControlPlaneError("policy upstream checks are duplicate or self-dependent")
        contexts.add(context)  # type: ignore[arg-type]
    associations = policy["trusted_receipt_author_associations"]
    if not isinstance(associations, list) or not associations:
        raise ControlPlaneError("policy requires trusted receipt author associations")
    allowed_associations = {"OWNER", "MEMBER", "COLLABORATOR"}
    if len(associations) != len(set(associations)) or not set(associations) <= allowed_associations:
        raise ControlPlaneError("policy receipt author associations are invalid")
    for name in ("max_api_response_bytes", "max_receipt_bytes"):
        validator.require_positive_integer(policy[name], f"policy.{name}")
    return policy


class GitHubClient:
    def __init__(self, repository: str, token: str, api_url: str, maximum: int):
        self.repository = repository
        self.token = token
        self.api_url = api_url.rstrip("/")
        self.maximum = maximum

    def request(self, method: str, path: str, *, body: object | None = None, accept: str = "application/vnd.github+json") -> tuple[bytes, dict[str, str]]:
        if not path.startswith("/") or path.startswith("//"):
            raise ControlPlaneError("GitHub API request path must be a same-origin absolute path")
        url = self.api_url + path
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": accept,
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "codex-exact-head-merge-readiness",
                **({"Content-Type": "application/json"} if data is not None else {}),
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read(self.maximum + 1)
                if len(content) > self.maximum:
                    raise ControlPlaneError("GitHub API response exceeds size limit")
                return content, {key.lower(): value for key, value in response.headers.items()}
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", "replace")
            raise ControlPlaneError(f"GitHub API {method} {path} failed with {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ControlPlaneError(f"GitHub API {method} {path} failed: {exc.reason}") from exc

    def json(self, method: str, path: str, *, body: object | None = None) -> object:
        content, _ = self.request(method, path, body=body)
        return strict_json(content, maximum=self.maximum, label=f"GitHub response {path}")

    def json_page(self, path: str) -> object:
        content, headers = self.request("GET", path)
        if 'rel="next"' in headers.get("link", ""):
            raise ControlPlaneError(f"GitHub collection at {path} exceeds one bounded page")
        return strict_json(content, maximum=self.maximum, label=f"GitHub response {path}")

    def json_array_pages(self, path: str, *, maximum_pages: int) -> list[object]:
        """Read a bounded GitHub array collection without silently truncating it."""
        if maximum_pages < 1:
            raise ControlPlaneError("GitHub collection page limit must be positive")
        separator = "&" if "?" in path else "?"
        result: list[object] = []
        for page in range(1, maximum_pages + 2):
            page_path = f"{path}{separator}per_page=100&page={page}"
            value = self.json("GET", page_path)
            if not isinstance(value, list):
                raise ControlPlaneError(f"GitHub collection at {path} is not an array")
            if page > maximum_pages:
                if value:
                    raise ControlPlaneError(
                        f"GitHub collection at {path} exceeds {maximum_pages * 100} items"
                    )
                break
            result.extend(value)
            if len(value) < 100:
                break
        return result

    def json_object_array_pages(self, path: str, key: str, *, maximum_pages: int) -> list[object]:
        """Read a bounded array nested in a paginated GitHub response object."""
        if maximum_pages < 1:
            raise ControlPlaneError("GitHub collection page limit must be positive")
        separator = "&" if "?" in path else "?"
        result: list[object] = []
        for page in range(1, maximum_pages + 2):
            page_path = f"{path}{separator}per_page=100&page={page}"
            value = self.json("GET", page_path)
            items = value.get(key) if isinstance(value, dict) else None
            if not isinstance(items, list):
                raise ControlPlaneError(f"GitHub collection {key!r} at {path} is incomplete")
            if page > maximum_pages:
                if items:
                    raise ControlPlaneError(
                        f"GitHub collection {key!r} at {path} exceeds {maximum_pages * 100} items"
                    )
                break
            result.extend(items)
            if len(items) < 100:
                break
        return result

    def repo_path(self, suffix: str) -> str:
        return f"/repos/{self.repository}{suffix}"


def event_pr_number(event: dict[str, object]) -> int:
    pull = event.get("pull_request")
    if isinstance(pull, dict):
        return validator.require_positive_integer(pull.get("number"), "event.pull_request.number")
    issue = event.get("issue")
    if isinstance(issue, dict) and isinstance(issue.get("pull_request"), dict):
        return validator.require_positive_integer(issue.get("number"), "event.issue.number")
    run = event.get("workflow_run")
    pulls = run.get("pull_requests") if isinstance(run, dict) else None
    if isinstance(pulls, list) and len(pulls) == 1 and isinstance(pulls[0], dict):
        return validator.require_positive_integer(pulls[0].get("number"), "event.workflow_run.pull_requests[0].number")
    inputs = event.get("inputs")
    if isinstance(inputs, dict):
        value = inputs.get("pr_number")
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)
    raise ControlPlaneError("event does not identify exactly one pull request")


def parse_receipt_body(body: object, *, maximum: int, repository: str, pr_number: int) -> dict[str, object] | None:
    if not isinstance(body, str):
        return None
    try:
        value = strict_json(body.encode("utf-8"), maximum=maximum, label="receipt body")
    except ControlPlaneError:
        return None
    if not isinstance(value, dict) or value.get("repository") != repository or value.get("pr_number") != pr_number:
        return None
    if value.get("receipt_authority") != "advisory_review_evidence":
        return None
    return value


def receipt_from_item(item: dict[str, object], *, repository: str, pr_number: int, head: str, maximum: int, trusted_associations: set[str]) -> tuple[dict[str, object], int, int, str] | None:
    if item.get("author_association") not in trusted_associations:
        return None
    receipt = parse_receipt_body(item.get("body"), maximum=maximum, repository=repository, pr_number=pr_number)
    if receipt is None or receipt.get("reviewed_head_sha") != head:
        return None
    identifier = validator.require_positive_integer(item.get("id"), "receipt.id")
    sequence = validator.require_receipt_sequence(receipt.get("receipt_sequence"), "receipt.receipt_sequence")
    url = validator.require_github_url(item.get("html_url"), "receipt.html_url")
    return receipt, identifier, sequence, url


def select_current_receipt(client: GitHubClient, pr_number: int, head: str, pointer_id: int | None, pointer_sequence: int | None, maximum: int, trusted_associations: set[str]) -> tuple[int | None, int | None]:
    items = client.json_array_pages(
        client.repo_path(f"/issues/{pr_number}/comments"), maximum_pages=5,
    )
    candidates: list[tuple[int, int]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ControlPlaneError("pull-request comment collection contains a non-object")
        parsed = receipt_from_item(
            item, repository=client.repository, pr_number=pr_number, head=head,
            maximum=maximum, trusted_associations=trusted_associations,
        )
        if parsed is not None:
            _, identifier, sequence, _ = parsed
            candidates.append((sequence, identifier))
    sequences = [sequence for sequence, _ in candidates]
    if len(sequences) != len(set(sequences)):
        raise ControlPlaneError("trusted exact-head receipts contain a duplicate sequence")
    latest = max(candidates, default=None)
    if pointer_id is not None and pointer_sequence is not None:
        if latest is not None and latest[0] > pointer_sequence:
            return latest[1], latest[0]
        return pointer_id, pointer_sequence
    if latest is None:
        return None, None
    return latest[1], latest[0]


def get_receipt(client: GitHubClient, pr_number: int, head: str, receipt_id: int, receipt_sequence: int, maximum: int, trusted_associations: set[str]) -> tuple[dict[str, object], int, str]:
    item = client.json("GET", client.repo_path(f"/issues/comments/{receipt_id}"))
    if not isinstance(item, dict):
        raise ControlPlaneError("current receipt comment is missing or is no longer trusted")
    parsed = receipt_from_item(
        item, repository=client.repository, pr_number=pr_number, head=head,
        maximum=maximum, trusted_associations=trusted_associations,
    )
    if parsed is None:
        raise ControlPlaneError("current receipt comment is not whole-body strict JSON evidence")
    receipt, identifier, sequence, url = parsed
    if identifier != receipt_id or sequence != receipt_sequence:
        raise ControlPlaneError("current receipt comment identity or sequence drifted")
    return receipt, identifier, url


def collect_threads(client: GitHubClient, owner: str, name: str, pr_number: int) -> tuple[int, str]:
    query = """query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100){nodes{id isResolved} pageInfo{hasNextPage}}}}}"""
    response = client.json("POST", "/graphql", body={"query": query, "variables": {"owner": owner, "name": name, "number": pr_number}})
    try:
        threads = response["data"]["repository"]["pullRequest"]["reviewThreads"]  # type: ignore[index]
        if threads["pageInfo"]["hasNextPage"] is not False:
            raise ControlPlaneError("more than 100 review threads is unsupported")
        nodes = threads["nodes"]
    except (KeyError, TypeError) as exc:
        raise ControlPlaneError("GitHub review-thread response is incomplete") from exc
    if not isinstance(nodes, list):
        raise ControlPlaneError("GitHub review-thread nodes are invalid")
    normalized = sorted(
        ({"id": validator.require_string(node.get("id"), "thread.id"), "is_resolved": node.get("isResolved") is True} for node in nodes if isinstance(node, dict)),
        key=lambda value: value["id"],
    )
    if len(normalized) != len(nodes):
        raise ControlPlaneError("GitHub review-thread node is invalid")
    return sum(not item["is_resolved"] for item in normalized), canonical_digest(normalized)


def require_unique_open_pr_for_head(client: GitHubClient, pr_number: int, head: str) -> None:
    pulls = client.json_array_pages(
        client.repo_path(f"/commits/{head}/pulls"), maximum_pages=5,
    )
    matches: list[int] = []
    for raw_pull in pulls:
        if not isinstance(raw_pull, dict):
            raise ControlPlaneError("commit pull-request collection contains a non-object")
        raw_head = raw_pull.get("head")
        if raw_pull.get("state") == "open" and isinstance(raw_head, dict) and raw_head.get("sha") == head:
            matches.append(validator.require_positive_integer(raw_pull.get("number"), "commit pull request.number"))
    if matches != [pr_number]:
        raise ControlPlaneError(
            "live head must belong to exactly this one open pull request before readiness can succeed"
        )


def collect_upstream_checks(client: GitHubClient, pr_number: int, base: str, head: str, policy: dict[str, object]) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for expected_raw in policy["required_upstream_workflows"]:  # type: ignore[union-attr]
        expected = validator.require_exact_fields(expected_raw, "policy.required_upstream_workflows[]", UPSTREAM_POLICY_FIELDS)
        context = expected["check_context"]
        workflow_id = validator.require_positive_integer(expected["workflow_id"], f"workflow {context}.workflow_id")
        workflow_definition = client.json(
            "GET", client.repo_path(f"/actions/workflows/{workflow_id}"),
        )
        if not isinstance(workflow_definition, dict):
            raise ControlPlaneError(f"workflow definition for {context!r} is incomplete")
        workflow_identity = {
            "id": workflow_definition.get("id"),
            "name": workflow_definition.get("name"),
            "path": workflow_definition.get("path"),
            "state": workflow_definition.get("state"),
        }
        expected_workflow_identity = {
            "id": workflow_id,
            "name": expected["workflow_name"],
            "path": expected["workflow_path"],
            "state": "active",
        }
        if workflow_identity != expected_workflow_identity:
            raise ControlPlaneError(f"workflow definition for {context!r} does not match policy")
        event = urllib.parse.quote(str(expected["event"]), safe="")
        encoded_head = urllib.parse.quote(head, safe="")
        runs = client.json_object_array_pages(
            client.repo_path(
                f"/actions/workflows/{workflow_id}/runs?event={event}&head_sha={encoded_head}"
            ),
            "workflow_runs",
            maximum_pages=5,
        )
        candidates: list[dict[str, object]] = []
        expected_title = f"{expected['workflow_name']} PR #{pr_number} @ {head}"
        for raw_run in runs:
            if not isinstance(raw_run, dict) or raw_run.get("workflow_id") != workflow_id:
                continue
            if raw_run.get("display_title") == expected_title and raw_run.get("head_sha") == head:
                candidates.append(raw_run)
        if not candidates:
            raise ControlPlaneError(f"required upstream workflow {context!r} has no run for the live PR head")
        workflow_run = max(candidates, key=lambda value: validator.require_positive_integer(value.get("id"), f"workflow {context}.id"))
        details_url = validator.require_github_url(workflow_run.get("html_url"), f"workflow {context}.html_url")
        workflow_path = str(expected["workflow_path"])
        encoded_path = "/".join(urllib.parse.quote(part, safe="") for part in workflow_path.split("/"))
        for revision in (base, head):
            content = client.json("GET", client.repo_path(f"/contents/{encoded_path}?ref={revision}"))
            if not isinstance(content, dict) or content.get("sha") != expected["workflow_blob_sha"]:
                raise ControlPlaneError(f"required upstream workflow {context!r} definition drifted at {revision}")
        item = {
            "workflow_name": validator.require_string(workflow_definition.get("name"), f"check {context}.workflow_name"),
            "workflow_run_id": validator.require_positive_integer(workflow_run.get("id"), f"check {context}.workflow_run_id"),
            "workflow_attempt": validator.require_positive_integer(workflow_run.get("run_attempt"), f"check {context}.workflow_attempt"),
            "workflow_id": validator.require_positive_integer(workflow_run.get("workflow_id"), f"check {context}.workflow_id"),
            "workflow_path": validator.require_string(workflow_run.get("path"), f"check {context}.workflow_path"),
            "event": validator.require_string(workflow_run.get("event"), f"check {context}.event"),
            "run_name_contract": expected["run_name_contract"],
            "run_display_title": validator.require_string(workflow_run.get("display_title"), f"check {context}.run_display_title"),
            "workflow_blob_sha": expected["workflow_blob_sha"],
            "check_context": context,
            "head_sha": head,
            "conclusion": workflow_run.get("conclusion"),
            "details_url": details_url,
        }
        actual_policy = {name: item[name] for name in UPSTREAM_POLICY_FIELDS}
        if actual_policy != expected:
            raise ControlPlaneError(f"required upstream workflow {context!r} provenance does not match policy")
        if workflow_run.get("conclusion") != "success":
            raise ControlPlaneError(f"latest workflow run for {context!r} is not successful on the live head")
        result.append(item)
    return result


def pointer_value(repository: str, pr_number: int, head: str, receipt_id: int | None, receipt_sequence: int | None, generation: int, receipt_digest: str | None = None) -> str:
    if generation < 1 or generation > validator.MAX_RECEIPT_SEQUENCE:
        raise ControlPlaneError("check pointer generation is outside the bounded integer range")
    if receipt_id is not None and receipt_id > validator.MAX_RECEIPT_SEQUENCE:
        raise ControlPlaneError("receipt ID is outside the bounded integer range")
    if receipt_sequence is not None:
        validator.require_receipt_sequence(receipt_sequence, "check pointer receipt sequence")
    repository_digest = hashlib.sha256(repository.encode("utf-8")).hexdigest()[:16]
    value = ":".join((
        "ehr1", repository_digest, str(pr_number), head, str(receipt_id or 0),
        str(receipt_sequence or 0), str(generation), receipt_digest or "-",
    ))
    if len(value) > 255:
        raise ControlPlaneError("check external_id exceeds GitHub's 255-character limit")
    return value


def parse_pointer(value: object, repository: str, pr_number: int, head: str) -> tuple[int | None, int | None, int]:
    if not isinstance(value, str):
        return None, None, 0
    match = re.fullmatch(r"ehr1:([0-9a-f]{16}):([1-9][0-9]*):([0-9a-f]{40}):([0-9]+):([0-9]+):([1-9][0-9]*):(-|[0-9a-f]{64})", value)
    if match is None:
        return None, None, 0
    expected_repository = hashlib.sha256(repository.encode("utf-8")).hexdigest()[:16]
    if match.group(1) != expected_repository or int(match.group(2)) != pr_number or match.group(3) != head:
        return None, None, 0
    receipt_id = int(match.group(4)) or None
    receipt_sequence = int(match.group(5)) or None
    generation = int(match.group(6))
    if (
        (receipt_id is not None and receipt_id > validator.MAX_RECEIPT_SEQUENCE)
        or (receipt_sequence is not None and receipt_sequence > validator.MAX_RECEIPT_SEQUENCE)
        or generation >= validator.MAX_RECEIPT_SEQUENCE
    ):
        return None, None, 0
    if (receipt_id is None) != (receipt_sequence is None):
        return None, None, 0
    return receipt_id, receipt_sequence, generation


def find_gate_check(client: GitHubClient, head: str, context: str, app_id: int) -> dict[str, object] | None:
    response = client.json_page(client.repo_path(f"/commits/{head}/check-runs?filter=all&per_page=100"))
    runs = response.get("check_runs") if isinstance(response, dict) else None
    if not isinstance(runs, list):
        raise ControlPlaneError("GitHub check-runs response is incomplete")
    matches = [run for run in runs if isinstance(run, dict) and run.get("name") == context and isinstance(run.get("app"), dict) and run["app"].get("id") == app_id]
    if len(matches) > 1:
        raise ControlPlaneError("dedicated readiness check is ambiguous for the live head")
    return matches[0] if matches else None


def start_check(client: GitHubClient, existing: dict[str, object] | None, head: str, context: str, details_url: str, external_id: str) -> dict[str, object]:
    body = {
        "name": context, "status": "in_progress", "details_url": details_url, "external_id": external_id,
        "output": {"title": "Exact-head evidence is being evaluated", "summary": "Trusted default-branch control plane is reading live GitHub state."},
    }
    if existing is None:
        body["head_sha"] = head
        value = client.json("POST", client.repo_path("/check-runs"), body=body)
    else:
        check_id = validator.require_positive_integer(existing.get("id"), "existing check.id")
        value = client.json("PATCH", client.repo_path(f"/check-runs/{check_id}"), body=body)
    if not isinstance(value, dict):
        raise ControlPlaneError("created check-run response is invalid")
    return value


def set_check_pointer(client: GitHubClient, check_id: int, details_url: str, external_id: str) -> dict[str, object]:
    value = client.json("PATCH", client.repo_path(f"/check-runs/{check_id}"), body={
        "status": "in_progress", "details_url": details_url, "external_id": external_id,
        "output": {"title": "Exact-head evidence is being evaluated", "summary": "Trusted default-branch control plane is reading live GitHub state."},
    })
    if not isinstance(value, dict):
        raise ControlPlaneError("updated check-run response is invalid")
    return value


def update_check(client: GitHubClient, check_id: int, conclusion: str, title: str, summary: str, external_id: str) -> dict[str, object]:
    value = client.json("PATCH", client.repo_path(f"/check-runs/{check_id}"), body={
        "status": "completed", "conclusion": conclusion, "external_id": external_id,
        "completed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "output": {"title": title[:255], "summary": summary[:65535]},
    })
    if not isinstance(value, dict):
        raise ControlPlaneError("completed check-run response is invalid")
    return value


def confirm_gate_check(client: GitHubClient, gate: dict[str, object], expected_head: str, expected_external_id: str) -> None:
    check_id = validator.require_positive_integer(gate["check_run_id"], "gate.check_run_id")
    live = client.json("GET", client.repo_path(f"/check-runs/{check_id}"))
    if not isinstance(live, dict) or not isinstance(live.get("app"), dict):
        raise ControlPlaneError("gate check readback is incomplete")
    expected = {
        "id": check_id,
        "name": validator.GATE_CONTEXT,
        "head_sha": expected_head,
        "app_id": gate["check_app_id"],
        "app_slug": gate["check_app_slug"],
        "status": "in_progress",
        "external_id": expected_external_id,
    }
    actual = {
        "id": live.get("id"), "name": live.get("name"), "head_sha": live.get("head_sha"),
        "app_id": live["app"].get("id"), "app_slug": live["app"].get("slug"),
        "status": live.get("status"),
        "external_id": live.get("external_id"),
    }
    if actual != expected:
        raise ControlPlaneError("gate check identity drifted before success publication")


def confirm_completed_gate_check(
    client: GitHubClient,
    gate: dict[str, object],
    expected_head: str,
    expected_external_id: str,
    expected_title: str,
    expected_summary: str,
) -> None:
    check_id = validator.require_positive_integer(gate["check_run_id"], "gate.check_run_id")
    live = client.json("GET", client.repo_path(f"/check-runs/{check_id}"))
    if not isinstance(live, dict) or not isinstance(live.get("app"), dict) or not isinstance(live.get("output"), dict):
        raise ControlPlaneError("completed gate check readback is incomplete")
    expected = {
        "id": check_id, "name": validator.GATE_CONTEXT, "head_sha": expected_head,
        "app_id": gate["check_app_id"], "app_slug": gate["check_app_slug"],
        "status": "completed", "conclusion": "success", "external_id": expected_external_id,
        "details_url": gate["details_url"], "title": expected_title[:255],
        "summary": expected_summary[:65535],
    }
    actual = {
        "id": live.get("id"), "name": live.get("name"), "head_sha": live.get("head_sha"),
        "app_id": live["app"].get("id"), "app_slug": live["app"].get("slug"),
        "status": live.get("status"), "conclusion": live.get("conclusion"),
        "external_id": live.get("external_id"), "details_url": live.get("details_url"),
        "title": live["output"].get("title"), "summary": live["output"].get("summary"),
    }
    if actual != expected:
        raise ControlPlaneError("completed success check did not survive exact platform readback")


def stable_evidence_identity(envelope: dict[str, object]) -> str:
    value = json.loads(json.dumps(envelope))
    value["platform_snapshot"].pop("platform_readback_at", None)
    return canonical_digest(value)


def read_mergeable_pull(client: GitHubClient, pr_number: int) -> dict[str, object]:
    for attempt in range(3):
        pull = client.json("GET", client.repo_path(f"/pulls/{pr_number}"))
        if not isinstance(pull, dict):
            raise ControlPlaneError("pull request response is invalid")
        if pull.get("mergeable") is not None:
            return pull
        if attempt < 2:
            time.sleep(2)
    raise ControlPlaneError("pull request mergeability remained indeterminate after bounded retry")


def build_envelope(client: GitHubClient, pr_number: int, receipt_id: int, receipt_sequence: int, policy: dict[str, object], gate: dict[str, object]) -> dict[str, object]:
    pull = read_mergeable_pull(client, pr_number)
    if not isinstance(pull, dict):
        raise ControlPlaneError("pull request response is invalid")
    base = validator.require_sha(pull.get("base", {}).get("sha") if isinstance(pull.get("base"), dict) else None, "pull.base.sha")
    head = validator.require_sha(pull.get("head", {}).get("sha") if isinstance(pull.get("head"), dict) else None, "pull.head.sha")
    compare_path = client.repo_path(f"/compare/{base}...{head}")
    comparison = client.json("GET", compare_path)
    try:
        merge_base = validator.require_sha(comparison["merge_base_commit"]["sha"], "compare.merge_base_commit.sha")  # type: ignore[index]
    except (KeyError, TypeError) as exc:
        raise ControlPlaneError("compare response has no merge-base identity") from exc
    range_identity_digest = validator.canonical_range_identity_digest(client.repository, pr_number, base, head, merge_base)
    selected_id, selected_sequence = select_current_receipt(
        client, pr_number, head, receipt_id, receipt_sequence,
        int(policy["max_receipt_bytes"]),
        set(policy["trusted_receipt_author_associations"]),  # type: ignore[arg-type]
    )
    if selected_id != receipt_id or selected_sequence != receipt_sequence:
        raise ControlPlaneError("current receipt advanced during readiness evaluation")
    receipt, actual_receipt_id, receipt_url = get_receipt(
        client,
        pr_number,
        head,
        receipt_id,
        receipt_sequence,
        int(policy["max_receipt_bytes"]),
        set(policy["trusted_receipt_author_associations"]),  # type: ignore[arg-type]
    )
    upstream = collect_upstream_checks(client, pr_number, base, head, policy)
    owner, name = client.repository.split("/", 1)
    unresolved, threads_digest = collect_threads(client, owner, name, pr_number)
    findings_digest = canonical_digest({"findings": receipt.get("findings"), "dispositions": receipt.get("dispositions")})
    ci_policy = {**policy["required_ci_policy"], "required_workflows": policy["required_upstream_workflows"]}  # type: ignore[arg-type]
    snapshot = {
        "repository": client.repository, "pr_number": pr_number,
        "base_sha": base, "head_sha": head, "merge_base_sha": merge_base,
        "range_identity_digest": range_identity_digest, "readback": {"source": "github", "confirmed": True},
        "state": pull.get("state"), "draft": pull.get("draft"), "mergeable": pull.get("mergeable"),
        "receipt_id": actual_receipt_id, "receipt_url": receipt_url,
        "platform_readback_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "receipt_digest": validator.canonical_receipt_digest(receipt),
        "required_ci": upstream, "required_ci_policy": ci_policy,
        "unresolved_review_threads": unresolved, "review_threads_digest": threads_digest,
        "findings_digest": findings_digest,
    }
    gate = {**gate, "head_sha": head, "conclusion": "success"}
    return {"contract": validator.V2_CONTRACT, "receipt": receipt, "platform_snapshot": snapshot, "gate": gate}


def event_receipt_decision(event: dict[str, object], *, current_receipt_id: int | None, explicit_receipt_id: int | None, repository: str, pr_number: int, maximum: int, trusted_associations: set[str]) -> tuple[bool, int | None]:
    if explicit_receipt_id is not None:
        return True, explicit_receipt_id
    comment = event.get("comment")
    if not isinstance(comment, dict):
        return True, current_receipt_id
    comment_id = validator.require_positive_integer(comment.get("id"), "event.comment.id")
    action = event.get("action")
    current = parse_receipt_body(comment.get("body"), maximum=maximum, repository=repository, pr_number=pr_number)
    association = comment.get("author_association")
    if current is not None and association in trusted_associations and action in {"created", "edited"}:
        return True, comment_id
    previous_body = event.get("changes", {}).get("body", {}).get("from") if isinstance(event.get("changes"), dict) and isinstance(event["changes"].get("body"), dict) else None  # type: ignore[index]
    previous = parse_receipt_body(previous_body, maximum=maximum, repository=repository, pr_number=pr_number)
    if comment_id == current_receipt_id and (action == "deleted" or previous is not None):
        return True, current_receipt_id
    return False, current_receipt_id


def run(args: argparse.Namespace) -> dict[str, object] | None:
    policy = load_policy(args.policy)
    event_raw = strict_json(
        read_bounded_regular_file(args.event_path, maximum=1024 * 1024, label="event"),
        maximum=1024 * 1024,
        label="event",
    )
    if not isinstance(event_raw, dict):
        raise ControlPlaneError("event must be an object")
    pr_number = args.pr_number or event_pr_number(event_raw)
    token = os.environ.get(args.token_env)
    if not token:
        raise ControlPlaneError(f"{args.token_env} is required")
    client = GitHubClient(args.repository, token, args.api_url, int(policy["max_api_response_bytes"]))
    live = client.json("GET", client.repo_path(f"/pulls/{pr_number}"))
    if not isinstance(live, dict) or not isinstance(live.get("head"), dict):
        raise ControlPlaneError("live pull request identity is unavailable")
    head = validator.require_sha(live["head"].get("sha"), "pull.head.sha")
    if head != args.expected_head:
        raise ControlPlaneError("routed PR head drifted before the head-scoped controller started")
    existing = find_gate_check(client, head, str(policy["check_context"]), args.expected_app_id)
    existing_receipt_id, existing_receipt_sequence, generation = parse_pointer(
        existing.get("external_id") if existing else None, args.repository, pr_number, head,
    )
    relevant, _ = event_receipt_decision(
        event_raw, current_receipt_id=existing_receipt_id, explicit_receipt_id=args.receipt_id,
        repository=args.repository, pr_number=pr_number, maximum=int(policy["max_receipt_bytes"]),
        trusted_associations=set(policy["trusted_receipt_author_associations"]),  # type: ignore[arg-type]
    )
    if not relevant:
        return None
    external_id = pointer_value(
        args.repository, pr_number, head,
        existing_receipt_id, existing_receipt_sequence, generation + 1,
    )
    check = start_check(client, existing, head, str(policy["check_context"]), args.run_url, external_id)
    check_id = validator.require_positive_integer(check.get("id"), "check.id")
    app = check.get("app")
    if not isinstance(app, dict):
        raise ControlPlaneError("dedicated check response has no App identity")
    if app.get("id") != args.expected_app_id or app.get("slug") != args.expected_app_slug:
        raise ControlPlaneError("dedicated check App identity does not match configured policy")
    gate = {
        "workflow_name": args.workflow_name,
        "workflow_run_id": args.workflow_run_id,
        "check_context": policy["check_context"],
        "check_run_id": check_id,
        "check_app_id": validator.require_positive_integer(app.get("id"), "check.app.id"),
        "check_app_slug": validator.require_string(app.get("slug"), "check.app.slug"),
        "details_url": args.run_url,
    }
    try:
        require_unique_open_pr_for_head(client, pr_number, head)
        receipt_id, receipt_sequence = select_current_receipt(
            client, pr_number, head, existing_receipt_id, existing_receipt_sequence,
            int(policy["max_receipt_bytes"]),
            set(policy["trusted_receipt_author_associations"]),  # type: ignore[arg-type]
        )
        external_id = pointer_value(
            args.repository, pr_number, head, receipt_id, receipt_sequence, generation + 1,
        )
        set_check_pointer(client, check_id, args.run_url, external_id)
        confirm_gate_check(client, gate, head, external_id)
        if receipt_id is None or receipt_sequence is None:
            raise ControlPlaneError("no current exact-head receipt is bound to this PR head")
        if args.receipt_id is not None and args.receipt_id != receipt_id:
            raise ControlPlaneError("requested receipt ID is not the authoritative current receipt")
        first = build_envelope(client, pr_number, receipt_id, receipt_sequence, policy, gate)
        validator.validate_payload(first)
        confirm_gate_check(client, gate, first["platform_snapshot"]["head_sha"], external_id)  # type: ignore[index]
        envelope = build_envelope(client, pr_number, receipt_id, receipt_sequence, policy, gate)
        validator.validate_payload(envelope)
        confirm_gate_check(client, gate, envelope["platform_snapshot"]["head_sha"], external_id)  # type: ignore[index]
        if stable_evidence_identity(first) != stable_evidence_identity(envelope):
            raise ControlPlaneError("live evidence drifted during success publication")
        digest = canonical_digest(envelope)
        completed_external_id = pointer_value(
            args.repository, pr_number, head, receipt_id, receipt_sequence, generation + 1,
            validator.canonical_receipt_digest(envelope["receipt"]),
        )
        success_title = "Exact-head merge evidence is current"
        success_summary = f"Evidence digest: `{digest}`\n\nHead: `{head}`"
        update_check(client, check_id, "success", success_title, success_summary, completed_external_id)
        confirm_completed_gate_check(
            client, gate, head, completed_external_id, success_title, success_summary,
        )
        args.output.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return envelope
    except Exception as exc:
        update_check(client, check_id, "failure", "Exact-head merge evidence is not current", str(exc), external_id)
        raise


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--event-path", type=pathlib.Path, required=True)
    parser.add_argument("--policy", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--pr-number", type=int)
    parser.add_argument(
        "--receipt-id",
        type=lambda value: None if value == "" else int(value),
    )
    parser.add_argument("--api-url", default="https://api.github.com")
    parser.add_argument("--token-env", default="EXACT_HEAD_GATE_TOKEN")
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--workflow-run-id", required=True, type=int)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--expected-head", required=True, type=lambda value: validator.require_sha(value, "--expected-head"))
    parser.add_argument("--expected-app-id", required=True, type=int)
    parser.add_argument("--expected-app-slug", required=True)
    args = parser.parse_args(argv)
    if validator.REPOSITORY.fullmatch(args.repository) is None:
        parser.error("--repository must be an owner/repository identifier")
    parsed_api = urllib.parse.urlsplit(args.api_url)
    if (
        parsed_api.scheme != "https" or not parsed_api.hostname
        or parsed_api.username is not None or parsed_api.password is not None
        or parsed_api.path not in {"", "/"} or parsed_api.query or parsed_api.fragment
    ):
        parser.error("--api-url must be a credential-free HTTPS origin")
    if args.api_url.rstrip("/") != "https://api.github.com":
        parser.error("--api-url must be the public GitHub API origin")
    expected_run_url = f"https://github.com/{args.repository}/actions/runs/{args.workflow_run_id}"
    if args.run_url != expected_run_url:
        parser.error("--run-url must bind repository and workflow run ID")
    if args.expected_app_id < 1 or not args.expected_app_slug:
        parser.error("dedicated App identity must be explicit")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        run(parse_args(argv))
    except (ControlPlaneError, validator.ExactHeadMergeReviewError, OSError) as exc:
        print(f"exact-head merge readiness failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
