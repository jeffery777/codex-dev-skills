"""Unintegrated Core #22 prototype: bounded PR text checks, no network client.

The caller supplies the native connector callbacks and exact action authority.
Local inspection bindings are not secret-detection or authorization evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Awaitable, Callable

MAX_INPUT_BYTES = 256 * 1024
MAX_BODY_BYTES = 64 * 1024
REQUEST_FIELDS = {"repository", "pr_number", "title", "body"}
SNAPSHOT_FIELDS = {
    "repository", "repository_id", "pr_number", "pr_id", "api_url", "html_url",
    "state", "draft", "base_sha", "head_sha", "base_ref", "head_ref",
    "head_repository", "updated_at", "title", "body",
}
Read = Callable[[dict], Awaitable[dict]]
Update = Callable[[dict], Awaitable[object]]
Checkpoint = Callable[[dict], Awaitable[None]]
SAFE_CODES = frozenset({
    "DUPLICATE_JSON_KEY", "NONFINITE_JSON", "INPUT_SIZE_OR_TYPE", "INVALID_JSON",
    "INVALID_VALUE", "UNSUPPORTED_FIELDS", "INVALID_ID", "INVALID_REPOSITORY",
    "INVALID_TITLE", "INVALID_BODY", "BODY_SIZE", "INVALID_TEXT_ENCODING",
    "DESTINATION_MISMATCH", "NOT_OPEN_DRAFT", "INVALID_REVISION", "INVALID_REF",
    "INVALID_TIMESTAMP", "CONTENT_REVIEW_NOT_CLEAR", "INSPECTION_REFERENCE_SIZE",
    "INVALID_INSPECTION", "INSPECTION_DRIFT", "BASELINE_DRIFT", "INVALID_REST_SHAPE",
})


class Blocked(ValueError):
    """A bounded code only; do not include caller text or provider errors."""

    def __init__(self, code):
        super().__init__(code if isinstance(code, str) and code in SAFE_CODES else "CHECK_FAILED")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Blocked("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _constant(_):
    raise Blocked("NONFINITE_JSON")


def strict_json(raw: bytes) -> object:
    if not isinstance(raw, bytes) or len(raw) > MAX_INPUT_BYTES:
        raise Blocked("INPUT_SIZE_OR_TYPE")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                          parse_constant=_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, Blocked):
            raise
        raise Blocked("INVALID_JSON") from None


def canonical(value: object) -> str:
    try:
        result = json.dumps(value, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False, allow_nan=False)
        if len(result.encode("utf-8")) > MAX_INPUT_BYTES:
            raise Blocked("INPUT_SIZE_OR_TYPE")
        return result
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise Blocked("INVALID_VALUE") from None


def _fields(value, fields):
    if not isinstance(value, dict) or set(value) != fields:
        raise Blocked("UNSUPPORTED_FIELDS")


def _positive(value):
    if type(value) is not int or not 0 < value <= 9_007_199_254_740_991:
        raise Blocked("INVALID_ID")


def _repository(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value):
        raise Blocked("INVALID_REPOSITORY")


def _text(title, body):
    if not isinstance(title, str) or not title or len(title) > 256:
        raise Blocked("INVALID_TITLE")
    if any(ord(c) < 32 or ord(c) == 127 for c in title):
        raise Blocked("INVALID_TITLE")
    if not isinstance(body, str):
        raise Blocked("INVALID_BODY")
    try:
        if len(body.encode("utf-8")) > MAX_BODY_BYTES:
            raise Blocked("BODY_SIZE")
        title.encode("utf-8")
    except UnicodeError:
        raise Blocked("INVALID_TEXT_ENCODING") from None
    if "\x00" in body:
        raise Blocked("INVALID_BODY")


def request(value: object) -> dict:
    _fields(value, REQUEST_FIELDS)
    _repository(value["repository"])
    _positive(value["pr_number"])
    _text(value["title"], value["body"])
    # Detach caller-owned mutable objects. No trimming or Unicode normalization.
    return strict_json(canonical(value).encode("utf-8"))


def snapshot(value: object) -> dict:
    _fields(value, SNAPSHOT_FIELDS)
    request({key: value[key] for key in REQUEST_FIELDS})
    for key in ("repository_id", "pr_id"):
        _positive(value[key])
    repo, number = value["repository"], value["pr_number"]
    if value["api_url"] != f"https://api.github.com/repos/{repo}/pulls/{number}":
        raise Blocked("DESTINATION_MISMATCH")
    if value["html_url"] != f"https://github.com/{repo}/pull/{number}":
        raise Blocked("DESTINATION_MISMATCH")
    if value["state"] != "open" or value["draft"] is not True:
        raise Blocked("NOT_OPEN_DRAFT")
    for key in ("base_sha", "head_sha"):
        if not isinstance(value[key], str) or not re.fullmatch(r"[0-9a-f]{40}", value[key]):
            raise Blocked("INVALID_REVISION")
    _repository(value["head_repository"])
    for key in ("base_ref", "head_ref"):
        if not isinstance(value[key], str) or not value[key] or len(value[key]) > 255:
            raise Blocked("INVALID_REF")
    if not isinstance(value["updated_at"], str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value["updated_at"]):
        raise Blocked("INVALID_TIMESTAMP")
    return strict_json(canonical(value).encode("utf-8"))


def normalize_rest_pull(raw: dict) -> dict:
    """Read only the declared public REST fields; inspect no unlisted metadata."""
    try:
        normalized = {
            "repository": raw["base"]["repo"]["full_name"],
            "repository_id": raw["base"]["repo"]["id"],
            "pr_number": raw["number"], "pr_id": raw["id"],
            "api_url": raw["url"], "html_url": raw["html_url"],
            "state": raw["state"], "draft": raw["draft"],
            "base_sha": raw["base"]["sha"], "head_sha": raw["head"]["sha"],
            "base_ref": raw["base"]["ref"], "head_ref": raw["head"]["ref"],
            "head_repository": raw["head"]["repo"]["full_name"],
            "updated_at": raw["updated_at"], "title": raw["title"], "body": raw["body"],
        }
    except (KeyError, TypeError):
        raise Blocked("INVALID_REST_SHAPE") from None
    return snapshot(normalized)


@dataclass(frozen=True)
class Inspected:
    request_json: str
    baseline_json: str
    inspection_reference: str
    binding: str


def inspect(proposed: dict, baseline: dict, *, verdict: str,
            inspection_reference: str) -> Inspected:
    """Bind an actual prior content review; this function does not perform it."""
    proposed, baseline = request(proposed), snapshot(baseline)
    if verdict != "clear" or not isinstance(inspection_reference, str) or not inspection_reference:
        raise Blocked("CONTENT_REVIEW_NOT_CLEAR")
    if len(inspection_reference) > 256:
        raise Blocked("INSPECTION_REFERENCE_SIZE")
    if any(proposed[k] != baseline[k] for k in ("repository", "pr_number")):
        raise Blocked("DESTINATION_MISMATCH")
    req, base = canonical(proposed), canonical(baseline)
    digest = hashlib.sha256(canonical([req, base, inspection_reference]).encode("utf-8")).hexdigest()
    return Inspected(req, base, inspection_reference, digest)


@dataclass
class Attempt:
    # Caller durably saves UNKNOWN before the native update callback is invoked.
    phase: str = "NOT_ATTEMPTED"


@dataclass(frozen=True)
class Outcome:
    phase: str
    code: str


def _prepared(inspected: Inspected, proposed: dict):
    if not isinstance(inspected, Inspected):
        raise Blocked("INVALID_INSPECTION")
    base = snapshot(strict_json(inspected.baseline_json.encode("utf-8")))
    req = request(strict_json(inspected.request_json.encode("utf-8")))
    expected = inspect(req, base, verdict="clear", inspection_reference=inspected.inspection_reference)
    if expected != inspected or canonical(request(proposed)) != inspected.request_json:
        raise Blocked("INSPECTION_DRIFT")
    return req, base


def _matches_result(expected: dict, base: dict, observed: dict) -> bool:
    expected_result = dict(base, title=expected["title"], body=expected["body"])
    return all(observed[k] == v for k, v in expected_result.items() if k != "updated_at")


async def publish(inspected: Inspected, proposed: dict, *, read: Read,
                  update: Update, checkpoint: Checkpoint, attempt: Attempt) -> Outcome:
    """One guarded native callback; no network, credentials, retries or fallback."""
    if attempt.phase != "NOT_ATTEMPTED":
        return Outcome("BLOCKED", "ALREADY_ATTEMPTED_RECONCILE_ONLY")
    # Reserve synchronously, before any callback can yield to another publisher.
    # This guards one Attempt in one event loop, not different processes/objects.
    attempt.phase = "PREPARING"
    try:
        req, base = _prepared(inspected, proposed)
        target = {"repository_full_name": req["repository"], "pr_number": req["pr_number"]}
        live = snapshot(await read(dict(target)))
        if live != base:
            raise Blocked("BASELINE_DRIFT")
        # This is a checkpoint, not an authorization or secret-safety verdict.
        await checkpoint({"phase": "UNKNOWN", "binding": inspected.binding,
                          "repository": req["repository"], "pr_number": req["pr_number"]})
    except Blocked as exc:
        attempt.phase = "NOT_ATTEMPTED"  # No update callback has been invoked.
        return Outcome("BLOCKED", str(exc))
    except Exception:
        attempt.phase = "NOT_ATTEMPTED"  # No update callback has been invoked.
        return Outcome("BLOCKED", "PREFLIGHT_OR_CHECKPOINT_FAILED")
    attempt.phase = "UNKNOWN"
    try:
        # Both fields come from the frozen inspection, never the caller's mutable input.
        response = await update(dict(target, title=req["title"], body=req["body"]))
        if response is not True:
            return Outcome("UNKNOWN", "UPDATE_RESULT_UNKNOWN")
        observed = snapshot(await read(dict(target)))
        if not _matches_result(req, base, observed):
            return Outcome("UNKNOWN", "READBACK_MISMATCH")
    except Exception:
        return Outcome("UNKNOWN", "UPDATE_OR_READBACK_FAILED")
    attempt.phase = "VERIFIED"
    return Outcome("VERIFIED", "EXACT_READBACK")


async def reconcile(inspected: Inspected, *, read: Read) -> Outcome:
    """Read-only after an uncertain attempt. No update callback is accepted."""
    try:
        proposed = strict_json(inspected.request_json.encode("utf-8"))
        req, base = _prepared(inspected, proposed)
        live = snapshot(await read({"repository_full_name": req["repository"],
                                    "pr_number": req["pr_number"]}))
        if _matches_result(req, base, live):
            return Outcome("OBSERVED", "DESIRED_TEXT_PRESENT_AFTER_UNKNOWN")
        return Outcome("UNKNOWN", "NO_AUTOMATIC_RETRY_OR_RESTORE")
    except Exception:
        return Outcome("UNKNOWN", "RECONCILIATION_FAILED")
