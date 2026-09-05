"""Load opt-in qualification data from a protected user store; never runtime facts."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import stat

MAX_STORE_BYTES = 65536
MAX_EVIDENCE_BYTES = 1048576
RECORD_KEYS = {"profile", "profile_sha256", "capability_class", "capability_tier", "task_scopes", "runtimes", "quality_evidence", "quality_evidence_sha256", "expires_on", "enabled"}
SHA = re.compile(r"[0-9a-f]{64}\Z")


class Untrusted(ValueError):
    pass


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Untrusted("duplicate-key")
        result[key] = value
    return result


def _check(st, *, directory=False, ancestor=False):
    if not (stat.S_ISDIR(st.st_mode) if directory else stat.S_ISREG(st.st_mode)):
        raise Untrusted("non-regular-path")
    allowed = {os.getuid(), 0} if ancestor else {os.getuid()}
    if st.st_uid not in allowed:
        raise Untrusted("unowned-path")
    if st.st_mode & 0o022:
        # A root-owned sticky ancestor cannot replace another user's protected child.
        if not (ancestor and directory and st.st_uid == 0 and st.st_mode & stat.S_ISVTX):
            raise Untrusted("writable-path")


def _directory(path):
    if not path.is_absolute() or ".." in path.parts:
        raise Untrusted("unsafe-store-root")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for i, part in enumerate(path.parts[1:]):
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
            _check(os.fstat(fd), directory=True, ancestor=i < len(path.parts) - 2)
            try:
                os.stat(".git", dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise Untrusted("repository-controlled-store")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read(root_fd, relative, limit):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise Untrusted("unsafe-evidence-path")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise Untrusted("unsafe-evidence-path")
    fd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
            _check(os.fstat(fd), directory=True)
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        try:
            before = os.fstat(file_fd)
            _check(before)
            if before.st_size > limit:
                raise Untrusted("oversize-file")
            chunks, size = [], 0
            while size <= limit:
                chunk = os.read(file_fd, min(65536, limit + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            after = os.fstat(file_fd)
            if size > limit:
                raise Untrusted("oversize-file")
            if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise Untrusted("changed-during-read")
            return b"".join(chunks)
        finally:
            os.close(file_fd)
    finally:
        os.close(fd)


def _strings(value):
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x.strip() for x in value) and len(value) == len(set(value))


def discover(facts, *, role, entries, scope, today=None):
    """Return candidate facts plus an audit record. Never alter supplied facts."""
    audit = {"status": "baseline", "reasons": [], "store_sha256": None, "scope": scope}
    if "enabled_candidates" in facts:
        audit.update(status="explicit-override", reasons=["explicit-enabled-candidates"])
        return facts, audit
    enabled = {}
    output = {**facts, "enabled_candidates": enabled}
    fd = None
    if os.name != "posix" or any(not hasattr(os, key) for key in ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK", "getuid")):
        audit["reasons"].append("unsupported-platform")
        return output, audit
    try:
        root = pathlib.Path(os.environ.get("CODEX_HOME", str(pathlib.Path.home() / ".codex")))
        fd = _directory(root)
        raw = _read(fd, "agent-qualifications.json", MAX_STORE_BYTES)
        audit["store_sha256"] = hashlib.sha256(raw).hexdigest()
        def invalid_constant(_):
            raise Untrusted("nonfinite-json")
        data = json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid_constant)
        if not isinstance(data, dict) or set(data) != {"schema_version", "enabled", "qualifications"} or type(data["schema_version"]) is not int or data["schema_version"] != 1 or type(data["enabled"]) is not bool or not isinstance(data["qualifications"], list):
            raise Untrusted("invalid-schema")
        seen = set()
        for record in data["qualifications"]:
            if not isinstance(record, dict) or set(record) != RECORD_KEYS:
                raise Untrusted("invalid-record")
            if any(not isinstance(record[k], str) or not record[k].strip() for k in RECORD_KEYS - {"enabled", "task_scopes", "runtimes"}):
                raise Untrusted("invalid-record")
            if type(record["enabled"]) is not bool or not _strings(record["task_scopes"]) or not _strings(record["runtimes"]) or set(record["runtimes"]) - {"cli", "desktop", "api"}:
                raise Untrusted("invalid-record")
            if not SHA.fullmatch(record["profile_sha256"]) or not SHA.fullmatch(record["quality_evidence_sha256"]) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["expires_on"]):
                raise Untrusted("invalid-record")
            dt.date.fromisoformat(record["expires_on"])
            if record["profile"] in seen:
                raise Untrusted("duplicate-profile")
            seen.add(record["profile"])
        if not data["enabled"]:
            raise Untrusted("store-disabled")
        if not isinstance(scope, str) or not scope.strip():
            raise Untrusted("scope-missing")
        surface = facts.get("model_surface") or {}
        runtime = surface.get("runtime")
        if runtime not in {"cli", "desktop", "api"}:
            raise Untrusted("current-runtime-missing")
        for record in data["qualifications"]:
            name = record["profile"]
            entry = entries.get(name, {})
            reason = None
            if not record["enabled"]:
                reason = "record-disabled"
            elif entry.get("candidate_for") != role:
                reason = "role-mismatch"
            elif any(record[k] != entry.get(k) for k in ("capability_class", "capability_tier")) or record["profile_sha256"] != entry.get("_profile_digest"):
                reason = "profile-mismatch"
            elif scope not in record["task_scopes"]:
                reason = "scope-mismatch"
            elif runtime not in record["runtimes"]:
                reason = "runtime-mismatch"
            elif dt.date.fromisoformat(record["expires_on"]) < (today or dt.date.today()):
                reason = "expired"
            else:
                evidence = _read(fd, record["quality_evidence"], MAX_EVIDENCE_BYTES)
                if hashlib.sha256(evidence).hexdigest() != record["quality_evidence_sha256"]:
                    reason = "evidence-mismatch"
            if reason:
                audit["reasons"].append(reason)
                continue
            enabled[name] = {"profile_sha256": record["profile_sha256"], "quality_evidence": "qualification-evidence-sha256:" + record["quality_evidence_sha256"]}
        audit["status"] = "qualified" if enabled else "baseline"
        if not enabled and not audit["reasons"]:
            audit["reasons"].append("no-applicable-record")
    except FileNotFoundError:
        enabled.clear()
        audit["reasons"].append("store-or-evidence-missing")
    except (OSError, ValueError, UnicodeError, RecursionError) as exc:
        enabled.clear()
        audit["reasons"].append(str(exc) if isinstance(exc, Untrusted) else "invalid-or-untrusted-store")
    finally:
        if fd is not None:
            os.close(fd)
    return output, audit
