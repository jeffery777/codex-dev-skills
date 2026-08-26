#!/usr/bin/env python3
"""Fail-closed, offline validation for exact-head merge-review evidence."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from datetime import datetime


MAX_INPUT_BYTES = 256 * 1024
V1_CONTRACT = "exact-head-merge-review/v1"
V2_CONTRACT = "exact-head-merge-readiness/v2"
CONTRACT = V1_CONTRACT
SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
GITHUB_URL = re.compile(r"https://github\.com/[^\s]+\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
RFC3339_UTC = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z\Z"
)
REVIEW_MODES = frozenset(("merge-review", "merge-review-deep"))


class ExactHeadMergeReviewError(ValueError):
    """A deterministic failure of the exact-head merge-review contract."""


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build JSON objects while rejecting duplicate keys before values are lost."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ExactHeadMergeReviewError(
                f"JSON object contains duplicate key: {key!r}"
            )
        result[key] = value
    return result


def reject_json_constant(value: str) -> object:
    raise ExactHeadMergeReviewError(f"JSON contains unsupported constant: {value}")


def load_json(data: bytes) -> object:
    """Decode bounded, strict-UTF-8 JSON without permissive duplicate semantics."""
    if len(data) > MAX_INPUT_BYTES:
        raise ExactHeadMergeReviewError("input exceeds size limit")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExactHeadMergeReviewError("input is not strict UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=reject_duplicate_json_keys,
            parse_constant=reject_json_constant,
        )
    except (json.JSONDecodeError, RecursionError) as exc:
        raise ExactHeadMergeReviewError("input is not valid JSON") from exc


def read_input(argument: str, stdin: object | None = None) -> bytes:
    """Read one bounded regular-file input, or bounded bytes from explicit stdin."""
    if argument == "-":
        source = sys.stdin.buffer if stdin is None else stdin
        data = source.read(MAX_INPUT_BYTES + 1)
        if not isinstance(data, bytes):
            raise ExactHeadMergeReviewError("stdin must provide bytes")
        if len(data) > MAX_INPUT_BYTES:
            raise ExactHeadMergeReviewError("input exceeds size limit")
        return data
    path = pathlib.Path(argument)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    nonblock = getattr(os, "O_NONBLOCK", None)
    if nofollow is None or nonblock is None:
        raise ExactHeadMergeReviewError(
            "regular-file input requires no-follow and nonblocking support"
        )
    try:
        descriptor = os.open(path, os.O_RDONLY | nofollow | nonblock)
    except ValueError as exc:
        raise ExactHeadMergeReviewError("input file path is invalid") from exc
    except OSError as exc:
        if isinstance(exc, FileNotFoundError):
            raise ExactHeadMergeReviewError("input file is missing") from exc
        raise ExactHeadMergeReviewError(
            "input file must be a regular non-symlink file"
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ExactHeadMergeReviewError(
                "input file must be a regular non-symlink file"
            )
        with os.fdopen(descriptor, "rb", closefd=False) as source:
            data = source.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise ExactHeadMergeReviewError("input exceeds size limit")
        return data
    except OSError as exc:
        raise ExactHeadMergeReviewError("input file cannot be read") from exc
    finally:
        os.close(descriptor)


def require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ExactHeadMergeReviewError(f"{label} must be an object")
    return value


def require_exact_fields(
    value: object, label: str, fields: frozenset[str]
) -> dict[str, object]:
    result = require_object(value, label)
    present = frozenset(result)
    missing = sorted(fields - present)
    unknown = sorted(present - fields)
    if missing:
        raise ExactHeadMergeReviewError(
            f"{label} is missing required field: {missing[0]}"
        )
    if unknown:
        raise ExactHeadMergeReviewError(
            f"{label} contains unknown critical field: {unknown[0]}"
        )
    return result


def require_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExactHeadMergeReviewError(f"{label} must be a non-empty string")
    return value


def require_repository(value: object, label: str) -> str:
    result = require_string(value, label)
    if REPOSITORY.fullmatch(result) is None:
        raise ExactHeadMergeReviewError(
            f"{label} must be a GitHub owner/repository identifier"
        )
    return result


def require_positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ExactHeadMergeReviewError(f"{label} must be a positive integer")
    return value


def require_zero_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != 0:
        raise ExactHeadMergeReviewError(f"{label} must be zero")
    return value


def require_false(value: object, label: str) -> bool:
    if value is not False:
        raise ExactHeadMergeReviewError(f"{label} must be false")
    return False


def require_sha(value: object, label: str) -> str:
    result = require_string(value, label)
    if SHA.fullmatch(result) is None:
        raise ExactHeadMergeReviewError(
            f"{label} must be a lowercase 40-character hexadecimal SHA"
        )
    return result


def require_digest(value: object, label: str) -> str:
    result = require_string(value, label)
    if DIGEST.fullmatch(result) is None:
        raise ExactHeadMergeReviewError(
            f"{label} must be a lowercase 64-character hexadecimal digest"
        )
    return result


def require_true(value: object, label: str) -> bool:
    if value is not True:
        raise ExactHeadMergeReviewError(f"{label} must be true")
    return True


def require_github_url(value: object, label: str) -> str:
    result = require_string(value, label)
    if GITHUB_URL.fullmatch(result) is None:
        raise ExactHeadMergeReviewError(f"{label} must be an HTTPS GitHub URL")
    return result


def require_rfc3339_utc(value: object, label: str) -> str:
    result = require_string(value, label)
    if RFC3339_UTC.fullmatch(result) is None:
        raise ExactHeadMergeReviewError(f"{label} must be an RFC3339 UTC timestamp")
    try:
        datetime.fromisoformat(result[:-1] + "+00:00")
    except ValueError as exc:
        raise ExactHeadMergeReviewError(
            f"{label} must be an RFC3339 UTC timestamp"
        ) from exc
    return result


def canonical_receipt_digest(receipt: dict[str, object]) -> str:
    """Return the SHA-256 of the complete receipt under deterministic JSON encoding."""
    encoded = json.dumps(
        receipt,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_digest(value: object) -> str:
    """Return the digest used to seal normalized v2 control-plane values."""
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_range_identity_digest(
    repository: str,
    pr_number: int,
    base_sha: str,
    head_sha: str,
    merge_base_sha: str,
) -> str:
    """Return the deterministic SHA-256 for the reviewed base-to-head range."""
    encoded = json.dumps(
        {
            "repository": repository,
            "pr_number": pr_number,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "merge_base_sha": merge_base_sha,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_required_ci(
    value: object, label: str, reviewed_head: str
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ExactHeadMergeReviewError(f"{label} must contain at least one check")
    ci_names: set[str] = set()
    ci_run_ids: set[int] = set()
    checks: list[dict[str, object]] = []
    for index, check in enumerate(value):
        item = require_exact_fields(
            check,
            f"{label}[{index}]",
            frozenset(("name", "status", "head_sha", "run_id")),
        )
        name = require_string(item["name"], f"{label}[{index}].name")
        run_id = require_positive_integer(item["run_id"], f"{label}[{index}].run_id")
        if name in ci_names:
            raise ExactHeadMergeReviewError(f"{label} contains duplicate name: {name!r}")
        if run_id in ci_run_ids:
            raise ExactHeadMergeReviewError(f"{label} contains duplicate run_id: {run_id}")
        if item["status"] != "success":
            raise ExactHeadMergeReviewError(
                f"{label}[{index}].status must equal 'success'"
            )
        require_equal(
            reviewed_head,
            require_sha(item["head_sha"], f"{label}[{index}].head_sha"),
            f"{label}[{index}].head_sha",
        )
        ci_names.add(name)
        ci_run_ids.add(run_id)
        checks.append(item)
    return checks


def validate_required_ci_policy(
    value: object, label: str, ci_names: set[str]
) -> dict[str, object]:
    policy = require_exact_fields(
        value,
        label,
        frozenset(("source", "reference", "required_names")),
    )
    source = require_string(policy["source"], f"{label}.source")
    if source not in {"github_ruleset", "repository_policy"}:
        raise ExactHeadMergeReviewError(
            f"{label}.source must equal github_ruleset or repository_policy"
        )
    require_string(policy["reference"], f"{label}.reference")
    required_names = policy["required_names"]
    if not isinstance(required_names, list) or not required_names:
        raise ExactHeadMergeReviewError(f"{label}.required_names must be a non-empty list")
    normalized_names: list[str] = []
    for index, name in enumerate(required_names):
        normalized = require_string(name, f"{label}.required_names[{index}]")
        if normalized in normalized_names:
            raise ExactHeadMergeReviewError(
                f"{label}.required_names contains duplicate name: {normalized!r}"
            )
        normalized_names.append(normalized)
    if set(normalized_names) != ci_names:
        raise ExactHeadMergeReviewError(
            f"{label}.required_names must exactly equal the required CI name set"
        )
    return policy


def validate_dispositions(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ExactHeadMergeReviewError("receipt.dispositions must be a list")
    finding_ids: set[str] = set()
    dispositions: list[dict[str, object]] = []
    for index, finding in enumerate(value):
        item = require_exact_fields(
            finding,
            f"receipt.dispositions[{index}]",
            frozenset(("finding_id", "severity", "disposition", "evidence")),
        )
        finding_id = require_string(
            item["finding_id"], f"receipt.dispositions[{index}].finding_id"
        )
        if finding_id in finding_ids:
            raise ExactHeadMergeReviewError(
                f"receipt.dispositions contains duplicate finding_id: {finding_id!r}"
            )
        severity = require_string(
            item["severity"], f"receipt.dispositions[{index}].severity"
        )
        if severity not in {"MUST-FIX", "SHOULD-FIX", "NIT"}:
            raise ExactHeadMergeReviewError(
                f"receipt.dispositions[{index}].severity is invalid"
            )
        disposition = require_string(
            item["disposition"], f"receipt.dispositions[{index}].disposition"
        )
        if disposition not in {"fixed", "rejected", "deferred"}:
            raise ExactHeadMergeReviewError(
                f"receipt.dispositions[{index}].disposition is invalid"
            )
        require_string(item["evidence"], f"receipt.dispositions[{index}].evidence")
        finding_ids.add(finding_id)
        dispositions.append(item)
    return dispositions


def validate_pre_commit_evidence(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise ExactHeadMergeReviewError("receipt.pre_commit_evidence must be a list")
    evidence_ids: set[str] = set()
    evidence_items: list[dict[str, object]] = []
    allowed_kinds = {
        "code-review",
        "code-review-deep",
        "docs-review",
        "security-diff-scan",
    }
    for index, evidence in enumerate(value):
        item = require_exact_fields(
            evidence,
            f"receipt.pre_commit_evidence[{index}]",
            frozenset(
                (
                    "kind",
                    "evidence_id",
                    "reviewed_content_digest",
                    "result",
                    "applicability_rationale",
                )
            ),
        )
        kind = require_string(
            item["kind"], f"receipt.pre_commit_evidence[{index}].kind"
        )
        if kind not in allowed_kinds:
            raise ExactHeadMergeReviewError(
                f"receipt.pre_commit_evidence[{index}].kind is invalid"
            )
        evidence_id = require_string(
            item["evidence_id"], f"receipt.pre_commit_evidence[{index}].evidence_id"
        )
        if evidence_id in evidence_ids:
            raise ExactHeadMergeReviewError(
                "receipt.pre_commit_evidence contains duplicate evidence_id: "
                f"{evidence_id!r}"
            )
        require_digest(
            item["reviewed_content_digest"],
            f"receipt.pre_commit_evidence[{index}].reviewed_content_digest",
        )
        if item["result"] != "no_findings":
            raise ExactHeadMergeReviewError(
                f"receipt.pre_commit_evidence[{index}].result must equal 'no_findings'"
            )
        require_string(
            item["applicability_rationale"],
            f"receipt.pre_commit_evidence[{index}].applicability_rationale",
        )
        evidence_ids.add(evidence_id)
        evidence_items.append(item)
    return evidence_items


def require_equal(receipt: object, snapshot: object, label: str) -> None:
    if receipt != snapshot:
        raise ExactHeadMergeReviewError(f"receipt {label} does not match platform snapshot")


def validate_v1_payload(payload: object) -> tuple[str, int]:
    """Validate all receipt evidence against a same-identity platform readback."""
    top = require_exact_fields(
        payload,
        "input",
        frozenset(("contract", "receipt", "platform_snapshot")),
    )
    if top["contract"] != V1_CONTRACT:
        raise ExactHeadMergeReviewError(f"contract must equal {V1_CONTRACT!r}")
    receipt = require_exact_fields(
        top["receipt"],
        "receipt",
        frozenset(
            (
                "repository",
                "pr_number",
                "review_mode",
                "reviewed_base_sha",
                "reviewed_head_sha",
                "reviewed_merge_base_sha",
                "reviewed_diff_digest",
                "receipt_authority",
                "merge_authorized",
                "findings",
                "dispositions",
                "residual_risk",
                "pre_commit_evidence",
                "required_ci",
                "required_ci_policy",
            )
        ),
    )
    snapshot = require_exact_fields(
        top["platform_snapshot"],
        "platform_snapshot",
        frozenset(
            (
                "repository",
                "pr_number",
                "base_sha",
                "head_sha",
                "merge_base_sha",
                "diff_digest",
                "readback",
                "state",
                "draft",
                "mergeable",
                "receipt_id",
                "receipt_url",
                "platform_readback_at",
                "receipt_digest",
                "required_ci",
                "required_ci_policy",
                "unresolved_review_threads",
            )
        ),
    )

    repository = require_repository(receipt["repository"], "receipt.repository")
    pr_number = require_positive_integer(receipt["pr_number"], "receipt.pr_number")
    review_mode = require_string(receipt["review_mode"], "receipt.review_mode")
    if review_mode not in REVIEW_MODES:
        raise ExactHeadMergeReviewError(
            "receipt.review_mode must be one of: merge-review, merge-review-deep"
        )
    if receipt["receipt_authority"] != "advisory_review_evidence":
        raise ExactHeadMergeReviewError(
            "receipt.receipt_authority must equal 'advisory_review_evidence'"
        )
    require_false(receipt["merge_authorized"], "receipt.merge_authorized")

    reviewed_base = require_sha(
        receipt["reviewed_base_sha"], "receipt.reviewed_base_sha"
    )
    reviewed_head = require_sha(
        receipt["reviewed_head_sha"], "receipt.reviewed_head_sha"
    )
    reviewed_merge_base = require_sha(
        receipt["reviewed_merge_base_sha"], "receipt.reviewed_merge_base_sha"
    )
    reviewed_digest = require_digest(
        receipt["reviewed_diff_digest"], "receipt.reviewed_diff_digest"
    )
    expected_range_digest = canonical_range_identity_digest(
        repository,
        pr_number,
        reviewed_base,
        reviewed_head,
        reviewed_merge_base,
    )
    if reviewed_digest != expected_range_digest:
        raise ExactHeadMergeReviewError(
            "receipt.reviewed_diff_digest must equal the canonical range identity digest"
        )
    findings = require_exact_fields(
        receipt["findings"],
        "receipt.findings",
        frozenset(("must_fix_open", "should_fix_open", "nit_open")),
    )
    for name in ("must_fix_open", "should_fix_open", "nit_open"):
        require_zero_integer(findings[name], f"receipt.findings.{name}")
    validate_dispositions(receipt["dispositions"])
    require_string(receipt["residual_risk"], "receipt.residual_risk")
    validate_pre_commit_evidence(receipt["pre_commit_evidence"])
    receipt_ci = validate_required_ci(
        receipt["required_ci"], "receipt.required_ci", reviewed_head
    )
    receipt_ci_names = {item["name"] for item in receipt_ci}
    validate_required_ci_policy(
        receipt["required_ci_policy"],
        "receipt.required_ci_policy",
        receipt_ci_names,
    )

    require_equal(
        repository,
        require_repository(
            snapshot["repository"], "platform_snapshot.repository"
        ),
        "repository",
    )
    require_equal(
        pr_number,
        require_positive_integer(
            snapshot["pr_number"], "platform_snapshot.pr_number"
        ),
        "pr_number",
    )
    require_equal(
        reviewed_base,
        require_sha(snapshot["base_sha"], "platform_snapshot.base_sha"),
        "base_sha",
    )
    require_equal(
        reviewed_head,
        require_sha(snapshot["head_sha"], "platform_snapshot.head_sha"),
        "head_sha",
    )
    require_equal(
        reviewed_merge_base,
        require_sha(snapshot["merge_base_sha"], "platform_snapshot.merge_base_sha"),
        "merge_base_sha",
    )
    require_equal(
        reviewed_digest,
        require_digest(snapshot["diff_digest"], "platform_snapshot.diff_digest"),
        "diff_digest",
    )
    if snapshot["diff_digest"] != expected_range_digest:
        raise ExactHeadMergeReviewError(
            "platform_snapshot.diff_digest must equal the canonical range identity digest"
        )

    readback = require_exact_fields(
        snapshot["readback"],
        "platform_snapshot.readback",
        frozenset(("source", "confirmed")),
    )
    if readback["source"] != "github" or readback["confirmed"] is not True:
        raise ExactHeadMergeReviewError(
            "platform_snapshot.readback must confirm GitHub platform readback"
        )
    if snapshot["state"] != "open":
        raise ExactHeadMergeReviewError("platform_snapshot.state must equal 'open'")
    require_false(snapshot["draft"], "platform_snapshot.draft")
    require_true(snapshot["mergeable"], "platform_snapshot.mergeable")
    receipt_id = require_positive_integer(
        snapshot["receipt_id"], "platform_snapshot.receipt_id"
    )
    receipt_url = require_github_url(
        snapshot["receipt_url"], "platform_snapshot.receipt_url"
    )
    pr_url = f"https://github.com/{repository}/pull/{pr_number}"
    expected_receipt_urls = frozenset(
        (
            f"{pr_url}#issuecomment-{receipt_id}",
            f"{pr_url}#pullrequestreview-{receipt_id}",
        )
    )
    if receipt_url not in expected_receipt_urls:
        raise ExactHeadMergeReviewError(
            "platform_snapshot.receipt_url must bind the receipt ID to its repository and PR"
        )
    require_rfc3339_utc(
        snapshot["platform_readback_at"], "platform_snapshot.platform_readback_at"
    )
    supplied_receipt_digest = require_digest(
        snapshot["receipt_digest"], "platform_snapshot.receipt_digest"
    )
    if supplied_receipt_digest != canonical_receipt_digest(receipt):
        raise ExactHeadMergeReviewError(
            "platform_snapshot.receipt_digest does not match canonical receipt digest"
        )
    snapshot_ci = validate_required_ci(
        snapshot["required_ci"], "platform_snapshot.required_ci", reviewed_head
    )
    snapshot_ci_names = {item["name"] for item in snapshot_ci}
    snapshot_policy = validate_required_ci_policy(
        snapshot["required_ci_policy"],
        "platform_snapshot.required_ci_policy",
        snapshot_ci_names,
    )
    if receipt_ci != snapshot_ci:
        raise ExactHeadMergeReviewError(
            "receipt.required_ci does not exactly match platform_snapshot.required_ci"
        )
    if receipt["required_ci_policy"] != snapshot_policy:
        raise ExactHeadMergeReviewError(
            "receipt.required_ci_policy does not exactly match platform_snapshot.required_ci_policy"
        )
    require_zero_integer(
        snapshot["unresolved_review_threads"],
        "platform_snapshot.unresolved_review_threads",
    )
    return repository, pr_number


V2_CI_FIELDS = frozenset(
    (
        "workflow_name",
        "workflow_run_id",
        "workflow_attempt",
        "workflow_id",
        "workflow_path",
        "event",
        "run_name_contract",
        "run_display_title",
        "workflow_blob_sha",
        "check_context",
        "head_sha",
        "conclusion",
        "details_url",
    )
)
V2_GATE_FIELDS = frozenset(
    (
        "workflow_name",
        "workflow_run_id",
        "check_context",
        "check_run_id",
        "check_app_id",
        "check_app_slug",
        "details_url",
        "head_sha",
        "conclusion",
    )
)
GATE_CONTEXT = "Exact-Head Merge Readiness"
MAX_RECEIPT_SEQUENCE = 9_223_372_036_854_775_807


def require_receipt_sequence(value: object, label: str) -> int:
    sequence = require_positive_integer(value, label)
    if sequence > MAX_RECEIPT_SEQUENCE:
        raise ExactHeadMergeReviewError(
            f"{label} must not exceed {MAX_RECEIPT_SEQUENCE}"
        )
    return sequence


def validate_v2_ci(value: object, label: str, repository: str, pr_number: int, head_sha: str) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise ExactHeadMergeReviewError(f"{label} must contain at least one check")
    contexts: set[str] = set()
    check_ids: set[int] = set()
    result: list[dict[str, object]] = []
    for index, raw in enumerate(value):
        item_label = f"{label}[{index}]"
        item = require_exact_fields(raw, item_label, V2_CI_FIELDS)
        for field in ("workflow_name", "workflow_path", "event", "run_name_contract", "run_display_title", "check_context"):
            require_string(item[field], f"{item_label}.{field}")
        require_sha(item["workflow_blob_sha"], f"{item_label}.workflow_blob_sha")
        if item["event"] != "pull_request" or item["run_name_contract"] != "exact-pr-head/v1":
            raise ExactHeadMergeReviewError(f"{item_label} must use trusted exact-PR-head run naming")
        expected_title = f"{item['workflow_name']} PR #{pr_number} @ {head_sha}"
        if item["run_display_title"] != expected_title:
            raise ExactHeadMergeReviewError(f"{item_label}.run_display_title does not bind repository PR head")
        context = item["check_context"]
        if context == GATE_CONTEXT:
            raise ExactHeadMergeReviewError(
                f"{label} must not contain the readiness gate context"
            )
        check_id = require_positive_integer(item["workflow_run_id"], f"{item_label}.workflow_run_id")
        for field in ("workflow_attempt", "workflow_id"):
            require_positive_integer(item[field], f"{item_label}.{field}")
        if context in contexts:
            raise ExactHeadMergeReviewError(f"{label} contains duplicate check_context: {context!r}")
        if check_id in check_ids:
            raise ExactHeadMergeReviewError(f"{label} contains duplicate workflow_run_id: {check_id}")
        require_equal(
            head_sha,
            require_sha(item["head_sha"], f"{item_label}.head_sha"),
            f"{item_label}.head_sha",
        )
        if item["conclusion"] != "success":
            raise ExactHeadMergeReviewError(f"{item_label}.conclusion must equal 'success'")
        details_url = require_github_url(item["details_url"], f"{item_label}.details_url")
        expected_url = f"https://github.com/{repository}/actions/runs/{item['workflow_run_id']}"
        if details_url != expected_url:
            raise ExactHeadMergeReviewError(f"{item_label}.details_url does not bind repository and workflow run ID")
        contexts.add(context)  # type: ignore[arg-type]
        check_ids.add(check_id)
        result.append(item)
    return result


def validate_v2_ci_policy(value: object, label: str, ci: list[dict[str, object]]) -> dict[str, object]:
    policy = require_exact_fields(
        value, label, frozenset(("source", "reference", "required_workflows"))
    )
    if policy["source"] not in {"github_ruleset", "repository_policy"}:
        raise ExactHeadMergeReviewError(
            f"{label}.source must equal github_ruleset or repository_policy"
        )
    require_string(policy["reference"], f"{label}.reference")
    required = policy["required_workflows"]
    if not isinstance(required, list) or not required:
        raise ExactHeadMergeReviewError(f"{label}.required_workflows must be a non-empty list")
    fields = frozenset(("check_context", "workflow_name", "workflow_id", "workflow_path", "event", "run_name_contract", "workflow_blob_sha"))
    normalized: list[dict[str, object]] = []
    contexts: set[str] = set()
    for index, raw in enumerate(required):
        item_label = f"{label}.required_workflows[{index}]"
        item = require_exact_fields(raw, item_label, fields)
        for field in ("check_context", "workflow_name", "workflow_path", "event", "run_name_contract"):
            require_string(item[field], f"{item_label}.{field}")
        require_sha(item["workflow_blob_sha"], f"{item_label}.workflow_blob_sha")
        if item["event"] != "pull_request" or item["run_name_contract"] != "exact-pr-head/v1":
            raise ExactHeadMergeReviewError(f"{item_label} must use trusted exact-PR-head run naming")
        require_positive_integer(item["workflow_id"], f"{item_label}.workflow_id")
        context = item["check_context"]
        if context == GATE_CONTEXT or context in contexts:
            raise ExactHeadMergeReviewError(f"{label}.required_workflows contains a duplicate or self-dependency")
        contexts.add(context)  # type: ignore[arg-type]
        normalized.append(item)
    actual = [{field: item[field] for field in fields} for item in ci]
    if normalized != actual:
        raise ExactHeadMergeReviewError(
            f"{label}.required_workflows must exactly equal the hosted CI provenance"
        )
    return policy


def validate_v2_payload(payload: object) -> tuple[str, int]:
    """Validate a bounded snapshot normalized by the networked control plane."""
    top = require_exact_fields(
        payload,
        "input",
        frozenset(("contract", "receipt", "platform_snapshot", "gate")),
    )
    if top["contract"] != V2_CONTRACT:
        raise ExactHeadMergeReviewError(f"contract must equal {V2_CONTRACT!r}")
    receipt_fields = frozenset(
        (
            "repository", "pr_number", "receipt_sequence", "review_mode", "reviewed_base_sha",
            "reviewed_head_sha", "reviewed_merge_base_sha", "reviewed_range_identity_digest",
            "reviewed_review_threads_digest", "reviewed_findings_digest",
            "receipt_authority", "merge_authorized", "findings", "dispositions",
            "residual_risk", "pre_commit_evidence", "required_ci", "required_ci_policy",
        )
    )
    receipt = require_exact_fields(top["receipt"], "receipt", receipt_fields)
    snapshot = require_exact_fields(
        top["platform_snapshot"],
        "platform_snapshot",
        frozenset(
            (
                "repository", "pr_number", "base_sha", "head_sha", "merge_base_sha",
                "range_identity_digest", "readback", "state", "draft", "mergeable", "receipt_id",
                "receipt_url", "platform_readback_at", "receipt_digest", "required_ci",
                "required_ci_policy", "unresolved_review_threads", "review_threads_digest",
                "findings_digest",
            )
        ),
    )
    repository = require_repository(receipt["repository"], "receipt.repository")
    pr_number = require_positive_integer(receipt["pr_number"], "receipt.pr_number")
    require_receipt_sequence(receipt["receipt_sequence"], "receipt.receipt_sequence")
    review_mode = require_string(receipt["review_mode"], "receipt.review_mode")
    if review_mode not in REVIEW_MODES:
        raise ExactHeadMergeReviewError("receipt.review_mode must be one of: merge-review, merge-review-deep")
    if receipt["receipt_authority"] != "advisory_review_evidence":
        raise ExactHeadMergeReviewError("receipt.receipt_authority must equal 'advisory_review_evidence'")
    require_false(receipt["merge_authorized"], "receipt.merge_authorized")
    base = require_sha(receipt["reviewed_base_sha"], "receipt.reviewed_base_sha")
    head = require_sha(receipt["reviewed_head_sha"], "receipt.reviewed_head_sha")
    merge_base = require_sha(receipt["reviewed_merge_base_sha"], "receipt.reviewed_merge_base_sha")
    range_identity_digest = require_digest(receipt["reviewed_range_identity_digest"], "receipt.reviewed_range_identity_digest")
    expected_range_digest = canonical_range_identity_digest(repository, pr_number, base, head, merge_base)
    require_equal(expected_range_digest, range_identity_digest, "reviewed_range_identity_digest")
    threads_digest = require_digest(receipt["reviewed_review_threads_digest"], "receipt.reviewed_review_threads_digest")
    findings_digest = require_digest(receipt["reviewed_findings_digest"], "receipt.reviewed_findings_digest")
    findings = require_exact_fields(
        receipt["findings"], "receipt.findings",
        frozenset(("must_fix_open", "should_fix_open", "nit_open")),
    )
    for name in ("must_fix_open", "should_fix_open", "nit_open"):
        require_zero_integer(findings[name], f"receipt.findings.{name}")
    dispositions = validate_dispositions(receipt["dispositions"])
    if findings_digest != canonical_digest({"findings": findings, "dispositions": dispositions}):
        raise ExactHeadMergeReviewError("receipt.reviewed_findings_digest does not match findings and dispositions")
    require_string(receipt["residual_risk"], "receipt.residual_risk")
    validate_pre_commit_evidence(receipt["pre_commit_evidence"])
    receipt_ci = validate_v2_ci(receipt["required_ci"], "receipt.required_ci", repository, pr_number, head)
    receipt_policy = validate_v2_ci_policy(receipt["required_ci_policy"], "receipt.required_ci_policy", receipt_ci)

    for receipt_value, snapshot_field, validator, label in (
        (repository, "repository", require_repository, "repository"),
        (pr_number, "pr_number", require_positive_integer, "pr_number"),
        (base, "base_sha", require_sha, "base_sha"),
        (head, "head_sha", require_sha, "head_sha"),
        (merge_base, "merge_base_sha", require_sha, "merge_base_sha"),
        (range_identity_digest, "range_identity_digest", require_digest, "range_identity_digest"),
    ):
        require_equal(receipt_value, validator(snapshot[snapshot_field], f"platform_snapshot.{snapshot_field}"), label)
    readback = require_exact_fields(snapshot["readback"], "platform_snapshot.readback", frozenset(("source", "confirmed")))
    if readback != {"source": "github", "confirmed": True}:
        raise ExactHeadMergeReviewError("platform_snapshot.readback must confirm GitHub platform readback")
    if snapshot["state"] != "open":
        raise ExactHeadMergeReviewError("platform_snapshot.state must equal 'open'")
    require_false(snapshot["draft"], "platform_snapshot.draft")
    require_true(snapshot["mergeable"], "platform_snapshot.mergeable")
    receipt_id = require_positive_integer(snapshot["receipt_id"], "platform_snapshot.receipt_id")
    receipt_url = require_github_url(snapshot["receipt_url"], "platform_snapshot.receipt_url")
    expected_url = f"https://github.com/{repository}/pull/{pr_number}#issuecomment-{receipt_id}"
    if receipt_url != expected_url:
        raise ExactHeadMergeReviewError("platform_snapshot.receipt_url must bind the receipt ID to its repository and PR")
    require_rfc3339_utc(snapshot["platform_readback_at"], "platform_snapshot.platform_readback_at")
    if require_digest(snapshot["receipt_digest"], "platform_snapshot.receipt_digest") != canonical_receipt_digest(receipt):
        raise ExactHeadMergeReviewError("platform_snapshot.receipt_digest does not match canonical receipt digest")
    snapshot_ci = validate_v2_ci(snapshot["required_ci"], "platform_snapshot.required_ci", repository, pr_number, head)
    snapshot_policy = validate_v2_ci_policy(snapshot["required_ci_policy"], "platform_snapshot.required_ci_policy", snapshot_ci)
    if receipt_ci != snapshot_ci:
        raise ExactHeadMergeReviewError("receipt.required_ci does not exactly match platform_snapshot.required_ci")
    if receipt_policy != snapshot_policy:
        raise ExactHeadMergeReviewError("receipt.required_ci_policy does not exactly match platform_snapshot.required_ci_policy")
    require_zero_integer(snapshot["unresolved_review_threads"], "platform_snapshot.unresolved_review_threads")
    require_equal(threads_digest, require_digest(snapshot["review_threads_digest"], "platform_snapshot.review_threads_digest"), "review_threads_digest")
    require_equal(findings_digest, require_digest(snapshot["findings_digest"], "platform_snapshot.findings_digest"), "findings_digest")

    gate = require_exact_fields(top["gate"], "gate", V2_GATE_FIELDS)
    require_string(gate["workflow_name"], "gate.workflow_name")
    require_positive_integer(gate["workflow_run_id"], "gate.workflow_run_id")
    if gate["check_context"] != GATE_CONTEXT:
        raise ExactHeadMergeReviewError(f"gate.check_context must equal {GATE_CONTEXT!r}")
    require_positive_integer(gate["check_run_id"], "gate.check_run_id")
    require_positive_integer(gate["check_app_id"], "gate.check_app_id")
    require_string(gate["check_app_slug"], "gate.check_app_slug")
    gate_details_url = require_github_url(gate["details_url"], "gate.details_url")
    expected_gate_url = f"https://github.com/{repository}/actions/runs/{gate['workflow_run_id']}"
    if gate_details_url != expected_gate_url:
        raise ExactHeadMergeReviewError("gate.details_url does not bind repository and workflow run ID")
    require_equal(head, require_sha(gate["head_sha"], "gate.head_sha"), "gate.head_sha")
    if gate["conclusion"] != "success":
        raise ExactHeadMergeReviewError("gate.conclusion must equal 'success'")
    return repository, pr_number


def validate_payload(payload: object) -> tuple[str, int]:
    """Dispatch explicitly between the stable v1 and hosted-readiness v2 contracts."""
    value = require_object(payload, "input")
    contract = value.get("contract")
    if contract == V1_CONTRACT:
        return validate_v1_payload(payload)
    if contract == V2_CONTRACT:
        return validate_v2_payload(payload)
    raise ExactHeadMergeReviewError(
        f"contract must equal {V1_CONTRACT!r} or {V2_CONTRACT!r}"
    )


def validate_input(argument: str, stdin: object | None = None) -> tuple[str, int]:
    """Read and validate a single explicit offline evidence input."""
    return validate_payload(load_json(read_input(argument, stdin)))


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print(
            "validate-exact-head-merge-review.py requires exactly one JSON input path or '-'",
            file=sys.stderr,
        )
        return 2
    try:
        repository, pr_number = validate_input(arguments[0])
    except (OSError, ExactHeadMergeReviewError) as exc:
        print(f"exact-head merge-review validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"exact-head merge-review evidence valid for {repository} PR #{pr_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
