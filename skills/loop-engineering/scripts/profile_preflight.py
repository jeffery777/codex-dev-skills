#!/usr/bin/env python3
"""Validate Loop Engineering V2a custom-agent profiles and runtime facts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import tomllib
from typing import Any


SKILL_DIR = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_DIR.parents[1]
DEFAULT_PROFILE_DIR = REPO_ROOT / "agent-profiles"
DEFAULT_REGISTRY = SKILL_DIR / "references" / "agent-profile-registry.json"

PROFILE_KEYS = {"name", "description", "developer_instructions", "nickname_candidates", "model", "model_reasoning_effort", "sandbox_mode"}
REQUIRED_PROFILE_KEYS = {"name", "description", "developer_instructions"}
REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"}
SAFE_SANDBOX_MODES = {"read-only", "workspace-write"}
PARENT_SANDBOX_MODES = {"read-only", "workspace-write", "danger-full-access"}
SANDBOX_RANK = {"read-only": 0, "workspace-write": 1, "danger-full-access": 2}
PROFILE_NAME = re.compile(r"^loop_v2a_[a-z0-9_]+$")
NICKNAME = re.compile(r"^[A-Za-z0-9 _-]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
UNSAFE_TEXT = (
    re.compile(r"(?:^|[\s\"'])(?:/" + "Users/|/home/|[A-Za-z]:\\\\" + r"Users\\|~[/\\])"),
    re.compile(r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)\s*[:=]"),
    re.compile(r"(?i)(?:desktop|codex)[-_ ](?:database|db|session|log|cache|auth|app[-_ ]state)"),
)
REGISTRY_TOP_KEYS = {"schema_version", "namespace", "official_surface", "profiles"}
REGISTRY_PROFILE_KEYS = {"name", "file", "profile_sha256", "capability_class", "capability_tier", "tier_rank", "intended_task_class", "sandbox_expectation", "allowed_workflow_scope", "output_contract", "runtime_mapping", "fallback"}
MAPPING_KEYS = {"model", "reasoning_effort", "availability", "last_verified", "replaceable"}
FALLBACK_KEYS = {"same_capability_first", "allow_parent_default", "allow_sequential", "human_gate_if_unresolved"}
COMPATIBLE_PROFILE_KEYS = {"name", "profile_path", "capability_class", "capability_tier", "config_valid", "model_available", "reasoning_available", "sandbox", "allowed_workflow_scope", "profile_digest"}
CAPABILITY_TIERS = ("mechanical", "efficient", "everyday", "advanced", "deep", "exceptional")
TIER_RANK = {tier: index for index, tier in enumerate(CAPABILITY_TIERS)}
ROLE_CONTRACTS = {
    "loop_v2a_mechanical_reader": ("fast-read-explorer", "mechanical", 0, "read-only", {"read", "search", "summarize", "report-receipt"}),
    "loop_v2a_fast_explorer": ("fast-read-explorer", "efficient", 1, "read-only", {"read", "search", "summarize", "report-receipt"}),
    "loop_v2a_balanced_worker": ("balanced-worker", "everyday", 2, "workspace-write", {"read", "search", "bounded-edit", "focused-verify", "report-receipt"}),
    "loop_v2a_advanced_worker": ("balanced-worker", "advanced", 3, "workspace-write", {"read", "search", "bounded-edit", "focused-verify", "report-receipt"}),
    "loop_v2a_deep_reviewer": ("deep-reviewer", "deep", 4, "read-only", {"read", "search", "verify", "report-findings", "report-receipt"}),
    "loop_v2a_exceptional_researcher": ("deep-reviewer", "exceptional", 5, "read-only", {"read", "search", "verify", "report-findings", "report-receipt"}),
    "loop_v2a_security_reviewer": ("security-reviewer", "deep", 4, "read-only", {"read", "search", "validate", "defensive-control-analysis", "report-findings", "report-receipt"}),
}


class ProfileValidationError(ValueError):
    pass


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProfileValidationError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProfileValidationError(f"{label} must be a non-empty string")
    return value


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise ProfileValidationError(f"{label} must be a non-empty string list")
    if len(value) != len(set(value)):
        raise ProfileValidationError(f"{label} must contain unique values")
    return value


def _exact(value: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ProfileValidationError(f"{label} has unsupported key(s): {', '.join(unknown)}")


def _safe(value: Any, label: str) -> None:
    serialized = json.dumps(value, sort_keys=True)
    if any(pattern.search(serialized) for pattern in UNSAFE_TEXT):
        raise ProfileValidationError(f"{label} contains a machine-local, credential, or private-runtime reference")


def _date(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise ProfileValidationError(f"{label} must be YYYY-MM-DD")
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise ProfileValidationError(f"{label} must be a valid YYYY-MM-DD date") from exc
    if parsed > dt.date.today():
        raise ProfileValidationError(f"{label} must not be in the future")


def load_profile(path: pathlib.Path, *, require_filename_match: bool = True) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ProfileValidationError(f"profile must be a regular non-symlink file: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ProfileValidationError(f"invalid TOML profile {path}: {exc}") from exc
    _exact(data, PROFILE_KEYS, f"profile {path.name}")
    missing = sorted(REQUIRED_PROFILE_KEYS - set(data))
    if missing:
        raise ProfileValidationError(f"profile {path.name} missing required key(s): {', '.join(missing)}")
    for key in REQUIRED_PROFILE_KEYS:
        _string(data[key], f"profile {path.name}.{key}")
    name = data["name"]
    if not PROFILE_NAME.fullmatch(name):
        raise ProfileValidationError(f"profile {path.name}.name must use the loop_v2a_ namespace")
    if require_filename_match and path.stem != name:
        raise ProfileValidationError(f"profile filename {path.stem!r} must match name {name!r}")
    if "model" in data:
        _string(data["model"], f"profile {path.name}.model")
    if data.get("model_reasoning_effort") not in REASONING_EFFORTS:
        raise ProfileValidationError(f"profile {path.name} has unsupported or missing reasoning effort")
    if data.get("sandbox_mode") not in SAFE_SANDBOX_MODES:
        raise ProfileValidationError(f"profile {path.name} has unsafe sandbox mode or is missing sandbox_mode")
    if "nickname_candidates" in data:
        if any(not NICKNAME.fullmatch(item) for item in _strings(data["nickname_candidates"], f"profile {path.name}.nickname_candidates")):
            raise ProfileValidationError(f"profile {path.name} has an invalid nickname candidate")
    _safe(data, f"profile {path.name}")
    return data


def load_registry(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ProfileValidationError(f"registry must be a regular non-symlink file: {path}")
    try:
        data = _object(json.loads(path.read_text(encoding="utf-8")), "registry")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileValidationError(f"invalid JSON registry {path}: {exc}") from exc
    _exact(data, REGISTRY_TOP_KEYS, "registry")
    if data.get("schema_version") != 2 or data.get("namespace") != "loop_v2a_":
        raise ProfileValidationError("registry must declare schema_version 2 and namespace loop_v2a_")
    surface = _object(data.get("official_surface"), "registry.official_surface")
    _exact(surface, {"documentation", "last_verified", "format_stability"}, "registry.official_surface")
    if surface.get("documentation") != "https://learn.chatgpt.com/docs/agent-configuration/subagents" or surface.get("format_stability") != "runtime-dependent":
        raise ProfileValidationError("registry official custom-agent surface metadata is invalid")
    _date(surface.get("last_verified"), "registry.official_surface.last_verified")
    if not isinstance(data.get("profiles"), list) or not data["profiles"]:
        raise ProfileValidationError("registry.profiles must be a non-empty list")
    _safe(data, "registry")
    return data


def validate(profile_dir: pathlib.Path, registry_path: pathlib.Path = DEFAULT_REGISTRY) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    registry = load_registry(registry_path)
    sources: dict[str, dict[str, Any]] = {}
    toml_files = sorted(profile_dir.glob("loop_v2a_*.toml"))
    for path in toml_files:
        profile = load_profile(path)
        if profile["name"] in sources:
            raise ProfileValidationError(f"duplicate profile name: {profile['name']}")
        sources[profile["name"]] = profile
    entries: dict[str, dict[str, Any]] = {}
    files: set[str] = set()
    for index, raw in enumerate(registry["profiles"]):
        entry = _object(raw, f"registry.profiles[{index}]")
        _exact(entry, REGISTRY_PROFILE_KEYS, f"registry.profiles[{index}]")
        name = _string(entry.get("name"), f"registry.profiles[{index}].name")
        filename = _string(entry.get("file"), f"registry profile {name}.file")
        if not PROFILE_NAME.fullmatch(name) or name in entries:
            raise ProfileValidationError(f"registry profile name is invalid or duplicated: {name!r}")
        if pathlib.PurePosixPath(filename).name != filename or filename != f"{name}.toml" or filename in files:
            raise ProfileValidationError(f"registry profile {name} has an unsafe or duplicate file")
        files.add(filename)
        trusted_digest = entry.get("profile_sha256")
        if not isinstance(trusted_digest, str) or not SHA256.fullmatch(trusted_digest):
            raise ProfileValidationError(f"registry profile {name} requires profile_sha256")
        _string(entry.get("capability_class"), f"registry profile {name}.capability_class")
        tier = entry.get("capability_tier")
        if tier not in TIER_RANK or entry.get("tier_rank") != TIER_RANK.get(tier):
            raise ProfileValidationError(
                f"registry profile {name} has invalid capability tier or rank"
            )
        for key in ("intended_task_class", "allowed_workflow_scope", "output_contract"):
            _strings(entry.get(key), f"registry profile {name}.{key}")
        if entry.get("sandbox_expectation") not in SAFE_SANDBOX_MODES:
            raise ProfileValidationError(f"registry profile {name} has unsafe sandbox expectation")
        expected_contract = ROLE_CONTRACTS.get(name)
        if expected_contract is None or (
            entry.get("capability_class"),
            entry.get("capability_tier"),
            entry.get("tier_rank"),
            entry.get("sandbox_expectation"),
            set(entry.get("allowed_workflow_scope") or []),
        ) != expected_contract:
            raise ProfileValidationError(f"registry profile {name} differs from the canonical role contract")
        mapping = _object(entry.get("runtime_mapping"), f"registry profile {name}.runtime_mapping")
        _exact(mapping, MAPPING_KEYS, f"registry profile {name}.runtime_mapping")
        _string(mapping.get("model"), f"registry profile {name}.runtime_mapping.model")
        if mapping.get("replaceable") is not True:
            raise ProfileValidationError(f"registry profile {name} runtime mapping must be replaceable")
        if mapping.get("reasoning_effort") not in REASONING_EFFORTS or mapping.get("availability") != "runtime-dependent":
            raise ProfileValidationError(f"registry profile {name} runtime mapping metadata is invalid")
        _date(mapping.get("last_verified"), f"registry profile {name}.runtime_mapping.last_verified")
        fallback = _object(entry.get("fallback"), f"registry profile {name}.fallback")
        _exact(fallback, FALLBACK_KEYS, f"registry profile {name}.fallback")
        if any(not isinstance(fallback.get(key), bool) for key in FALLBACK_KEYS) or fallback["same_capability_first"] is not True:
            raise ProfileValidationError(f"registry profile {name} fallback contract is invalid")
        profile = sources.get(name)
        if (
            profile is None
            or profile_digest(profile_dir / filename) != trusted_digest
            or profile.get("model") != mapping["model"]
            or profile.get("model_reasoning_effort") != mapping["reasoning_effort"]
            or profile.get("sandbox_mode") != entry["sandbox_expectation"]
        ):
            raise ProfileValidationError(f"registry profile {name} differs from its TOML source")
        entries[name] = {**entry, "_profile_digest": trusted_digest}
    if set(entries) != set(sources) or files != {path.name for path in toml_files}:
        raise ProfileValidationError("registry coverage must exactly match all profile TOML files")
    return registry, entries


def profile_digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_collisions(profile_dir: pathlib.Path, roots: list[pathlib.Path], destination_root: pathlib.Path | None = None) -> dict[str, list[dict[str, str]]]:
    sources = {path.stem: path for path in profile_dir.glob("loop_v2a_*.toml")}
    expected: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    seen: dict[str, pathlib.Path] = {}
    destination = destination_root.resolve() if destination_root else None
    for root in roots:
        if not root.exists():
            continue
        if root.is_symlink() or not root.is_dir():
            raise ProfileValidationError(f"agent root must be a non-symlink directory: {root}")
        resolved_root = root.resolve()
        for path in sorted(root.glob("*.toml")):
            try:
                name = load_profile(path, require_filename_match=False)["name"]
            except ProfileValidationError:
                name = _external_name(path)
            source = sources.get(name)
            if source:
                identical = path.name == source.name and path.read_bytes() == source.read_bytes()
                if destination == resolved_root and identical:
                    expected.append({"name": name, "path": str(path), "profile_digest": profile_digest(path)})
                else:
                    reason = "cross-root-name-collision" if destination != resolved_root else "destination-content-conflict"
                    conflicts.append({"name": name, "path": str(path), "reason": reason})
            if source:
                if name in seen and seen[name].resolve() != path.resolve():
                    conflicts.append({"name": name, "path": str(path), "other_path": str(seen[name]), "reason": "duplicate-name-across-roots"})
                else:
                    seen[name] = path
    return {"expected_instances": expected, "conflicts": conflicts}


def _external_name(path: pathlib.Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise ProfileValidationError(f"external agent must be a regular non-symlink file: {path}")
    try:
        return _string(tomllib.loads(path.read_text(encoding="utf-8")).get("name"), f"external agent {path}.name")
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ProfileValidationError(f"cannot inspect external agent {path}: {exc}") from exc


def runtime_facts(path: pathlib.Path) -> dict[str, Any]:
    try:
        facts = _object(json.loads(path.read_text(encoding="utf-8")), "runtime facts")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileValidationError(f"invalid runtime facts {path}: {exc}") from exc
    _exact(facts, {"custom_agent_surface", "available_models", "reasoning_efforts", "compatible_profiles", "parent_default", "sequential", "parent_sandbox_mode"}, "runtime facts")
    surface = facts.get("custom_agent_surface")
    if surface is not None and (
        not isinstance(surface, str)
        or surface not in {"available", "unavailable", "unknown"}
    ):
        raise ProfileValidationError(
            "runtime facts custom_agent_surface must be available, unavailable, or unknown"
        )
    models = facts.get("available_models")
    if models is not None and (
        not isinstance(models, list)
        or any(not isinstance(model, str) for model in models)
    ):
        raise ProfileValidationError(
            "runtime facts available_models must be a string list"
        )
    efforts = facts.get("reasoning_efforts")
    if efforts is not None and (
        not isinstance(efforts, dict)
        or any(
            not isinstance(model, str)
            or not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for model, values in efforts.items()
        )
    ):
        raise ProfileValidationError(
            "runtime facts reasoning_efforts must map models to string lists"
        )
    parent_sandbox = facts.get("parent_sandbox_mode")
    if parent_sandbox is not None and (
        not isinstance(parent_sandbox, str)
        or parent_sandbox not in PARENT_SANDBOX_MODES
    ):
        raise ProfileValidationError(
            "runtime facts parent_sandbox_mode must be read-only, workspace-write, or danger-full-access"
        )
    known_classes = {contract[0] for contract in ROLE_CONTRACTS.values()}
    for key in ("parent_default", "sequential"):
        evidence = facts.get(key)
        if evidence is None:
            continue
        evidence = _object(evidence, f"runtime facts {key}")
        _exact(
            evidence,
            {"available", "capability_classes", "capability_tiers"},
            f"runtime facts {key}",
        )
        if not isinstance(evidence.get("available"), bool):
            raise ProfileValidationError(
                f"runtime facts {key}.available must be boolean"
            )
        classes = evidence.get("capability_classes", [])
        if not isinstance(classes, list) or any(
            not isinstance(item, str) or item not in known_classes
            for item in classes
        ):
            raise ProfileValidationError(
                f"runtime facts {key}.capability_classes must contain known classes"
            )
        tiers = evidence.get("capability_tiers", {})
        if not isinstance(tiers, dict) or any(
            not isinstance(capability, str)
            or capability not in known_classes
            or not isinstance(values, list)
            or any(
                not isinstance(value, str) or value not in TIER_RANK
                for value in values
            )
            for capability, values in tiers.items()
        ):
            raise ProfileValidationError(
                f"runtime facts {key}.capability_tiers must map known classes to known tiers"
            )
    return facts


def _sandbox_evidence(profile_sandbox: str, facts: dict[str, Any]) -> dict[str, Any] | None:
    """Return evidence only when a custom profile cannot widen the parent sandbox."""
    if not isinstance(profile_sandbox, str) or profile_sandbox not in SANDBOX_RANK:
        return None
    parent_sandbox = facts.get("parent_sandbox_mode")
    if profile_sandbox == "read-only" and parent_sandbox is None:
        parent_sandbox = "unknown-at-least-read-only"
    elif (
        not isinstance(parent_sandbox, str)
        or parent_sandbox not in PARENT_SANDBOX_MODES
    ):
        return None
    elif SANDBOX_RANK[profile_sandbox] > SANDBOX_RANK[parent_sandbox]:
        return None
    return {
        "parent_sandbox_mode": parent_sandbox,
        "sandbox_non_widening": True,
    }


def _validated_same_class(
    entry: dict[str, Any],
    facts: dict[str, Any],
    *,
    enforce_tier: bool,
    trusted_profiles: dict[str, dict[str, Any]] | None,
) -> dict[str, Any] | None:
    compatible = facts.get("compatible_profiles", {})
    if not isinstance(compatible, dict):
        raise ProfileValidationError("runtime facts compatible_profiles must be an object")
    candidates = compatible.get(entry["capability_class"], [])
    if not isinstance(candidates, list):
        raise ProfileValidationError("compatible profile class must contain a list")
    valid: list[dict[str, Any]] = []
    available_models = facts.get("available_models")
    reasoning_efforts = facts.get("reasoning_efforts")
    if (
        not isinstance(available_models, list)
        or any(not isinstance(model, str) for model in available_models)
        or not isinstance(reasoning_efforts, dict)
        or any(
            not isinstance(model, str)
            or not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for model, values in reasoning_efforts.items()
        )
    ):
        return None
    for index, raw in enumerate(candidates):
        candidate = _object(raw, f"compatible profile evidence[{index}]")
        _exact(candidate, COMPATIBLE_PROFILE_KEYS, f"compatible profile evidence[{index}]")
        name = _string(candidate.get("name"), f"compatible profile evidence[{index}].name")
        digest = candidate.get("profile_digest")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ProfileValidationError("compatible profile evidence requires a lowercase SHA-256 profile_digest")
        raw_path = candidate.get("profile_path")
        if not isinstance(raw_path, str) or not raw_path or not pathlib.Path(raw_path).is_absolute():
            raise ProfileValidationError("compatible profile evidence requires an absolute profile_path")
        candidate_path = pathlib.Path(raw_path)
        loaded = load_profile(candidate_path, require_filename_match=False)
        candidate_scope = candidate.get("allowed_workflow_scope")
        trusted = (
            trusted_profiles.get(name)
            if isinstance(trusted_profiles, dict)
            else None
        )
        trusted_tier_evidence = (
            not enforce_tier
            or (
                isinstance(trusted, dict)
                and candidate.get("capability_class")
                == trusted.get("capability_class")
                and candidate.get("capability_tier")
                == trusted.get("capability_tier")
                and candidate.get("profile_digest")
                == trusted.get("_profile_digest")
                and loaded.get("model")
                == trusted.get("runtime_mapping", {}).get("model")
                and loaded.get("model_reasoning_effort")
                == trusted.get("runtime_mapping", {}).get("reasoning_effort")
                and candidate.get("sandbox")
                == trusted.get("sandbox_expectation")
                and isinstance(candidate_scope, list)
                and all(isinstance(item, str) for item in candidate_scope)
                and set(candidate_scope)
                == set(trusted.get("allowed_workflow_scope") or [])
            )
        )
        checks = (candidate.get("config_valid"), candidate.get("model_available"), candidate.get("reasoning_available"))
        sandbox_evidence = _sandbox_evidence(candidate.get("sandbox"), facts)
        if (
            checks == (True, True, True)
            and trusted_tier_evidence
            and sandbox_evidence is not None
            and loaded.get("name") == name
            and loaded.get("sandbox_mode") == candidate.get("sandbox")
            and profile_digest(candidate_path) == digest
            and loaded.get("model") in available_models
            and loaded.get("model_reasoning_effort")
            in reasoning_efforts.get(loaded.get("model"), [])
            and candidate.get("capability_class") == entry["capability_class"]
            and (
                not enforce_tier
                or (
                    isinstance(candidate.get("capability_tier"), str)
                    and candidate.get("capability_tier") in TIER_RANK
                    and TIER_RANK[candidate["capability_tier"]]
                    >= TIER_RANK[entry["capability_tier"]]
                )
            )
            and candidate.get("sandbox") == entry["sandbox_expectation"]
            and isinstance(candidate.get("allowed_workflow_scope"), list)
            and all(
                isinstance(item, str)
                for item in candidate.get("allowed_workflow_scope", [])
            )
            and set(candidate.get("allowed_workflow_scope") or [])
            == set(entry["allowed_workflow_scope"])
            and name != entry["name"]
        ):
            valid.append({**candidate, **sandbox_evidence})
    return sorted(
        valid,
        key=(
            (lambda item: (TIER_RANK[item["capability_tier"]], item["name"]))
            if enforce_tier
            else (lambda item: item["name"])
        ),
    )[0] if valid else None


def _tier_evidence_satisfies(
    evidence: dict[str, Any], capability: str, required_tier: str
) -> bool:
    tiers = evidence.get("capability_tiers", {})
    return isinstance(tiers, dict) and any(
        isinstance(tier, str)
        and tier in TIER_RANK
        and TIER_RANK[tier] >= TIER_RANK[required_tier]
        for tier in tiers.get(capability, [])
    )


def _fallback(
    entry: dict[str, Any],
    facts: dict[str, Any],
    *,
    custom_surface_available: bool,
    enforce_tier: bool,
    trusted_profiles: dict[str, dict[str, Any]] | None,
) -> tuple[str, str | None, str, dict[str, Any] | None]:
    capability = entry["capability_class"]
    if custom_surface_available:
        candidate = _validated_same_class(
            entry,
            facts,
            enforce_tier=enforce_tier,
            trusted_profiles=trusted_profiles,
        )
        if candidate:
            return "fallback-safe", candidate["name"], "same-capability-profile", {**candidate, "available": True}
    fallback = entry["fallback"]
    for fact_key, allowed_key, selected, tier in (
        ("parent_default", "allow_parent_default", "parent/default", "parent-default"),
        ("sequential", "allow_sequential", "current-session", "sequential-current-session"),
    ):
        evidence = facts.get(fact_key, {})
        classes = evidence.get("capability_classes", []) if isinstance(evidence, dict) else []
        compatible = (
            capability in classes
            and _tier_evidence_satisfies(
                evidence, capability, entry["capability_tier"]
            )
            if enforce_tier
            else (not fallback["human_gate_if_unresolved"] or capability in classes)
        )
        if fallback[allowed_key] and isinstance(evidence, dict) and evidence.get("available") is True and compatible:
            return "fallback-safe", selected, tier, evidence
    return "human-gate", None, "stop-for-human-gate", None


def preflight(
    entry: dict[str, Any],
    facts: dict[str, Any],
    collision_report: dict[str, list[dict[str, str]]] | list[dict[str, str]],
    *,
    enforce_tier: bool = True,
    trusted_profiles: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    conflicts = collision_report.get("conflicts", []) if isinstance(collision_report, dict) else collision_report
    base = {"profile": entry["name"], "capability_class": entry["capability_class"], "capability_tier": entry["capability_tier"], "tier_rank": entry["tier_rank"], "runtime_mapping": entry["runtime_mapping"], "collisions": conflicts}
    if conflicts:
        return {**base, "state": "human-gate", "decision": "human-gate", "reason": "profile-name-collision"}
    surface = facts.get("custom_agent_surface", "unknown")
    if not isinstance(surface, str) or surface not in {"available", "unavailable", "unknown"}:
        raise ProfileValidationError("runtime facts custom_agent_surface must be available, unavailable, or unknown")
    if surface != "available":
        decision, selected, tier, evidence = _fallback(
            entry, facts, custom_surface_available=False, enforce_tier=enforce_tier,
            trusted_profiles=trusted_profiles,
        )
        return {**base, "state": "custom-surface-unavailable" if surface == "unavailable" else "unknown", "decision": decision, "selected": selected, "fallback_tier": tier, "fallback_evidence": evidence}
    models, efforts = facts.get("available_models"), facts.get("reasoning_efforts")
    if models is None or efforts is None:
        decision, selected, tier, evidence = _fallback(
            entry, facts, custom_surface_available=True, enforce_tier=enforce_tier,
            trusted_profiles=trusted_profiles,
        )
        return {**base, "state": "unknown", "decision": decision, "selected": selected, "fallback_tier": tier, "fallback_evidence": evidence}
    if (
        not isinstance(models, list)
        or any(not isinstance(item, str) for item in models)
        or not isinstance(efforts, dict)
        or any(
            not isinstance(model_name, str)
            or not isinstance(values, list)
            or any(not isinstance(value, str) for value in values)
            for model_name, values in efforts.items()
        )
    ):
        raise ProfileValidationError("runtime model/reasoning facts have invalid types")
    model, effort = entry["runtime_mapping"]["model"], entry["runtime_mapping"]["reasoning_effort"]
    if model not in models or effort not in efforts.get(model, []):
        decision, selected, tier, evidence = _fallback(
            entry, facts, custom_surface_available=True, enforce_tier=enforce_tier,
            trusted_profiles=trusted_profiles,
        )
        return {**base, "state": "unavailable", "decision": decision, "selected": selected, "fallback_tier": tier, "fallback_evidence": evidence}
    sandbox_evidence = _sandbox_evidence(entry["sandbox_expectation"], facts)
    if sandbox_evidence is None:
        decision, selected, tier, evidence = _fallback(
            entry, facts, custom_surface_available=True, enforce_tier=enforce_tier,
            trusted_profiles=trusted_profiles,
        )
        return {**base, "state": "sandbox-constraint-unknown-or-widening", "decision": decision, "selected": selected, "fallback_tier": tier, "fallback_evidence": evidence}
    route_profile_evidence = {
        "name": entry["name"],
        "capability_class": entry["capability_class"],
        "capability_tier": entry["capability_tier"],
        "available": True,
        "config_valid": True,
        "model_available": True,
        "reasoning_available": True,
        "profile_digest": entry["_profile_digest"],
        "sandbox": entry["sandbox_expectation"],
        "allowed_workflow_scope": entry["allowed_workflow_scope"],
        **sandbox_evidence,
    }
    return {**base, "state": "ready", "decision": "ready", "selected": entry["name"], "fallback_tier": None, "route_profile_evidence": route_profile_evidence}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("validate", "preflight"), default="validate")
    parser.add_argument("--profile-dir", type=pathlib.Path, default=DEFAULT_PROFILE_DIR)
    parser.add_argument("--registry", type=pathlib.Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--role")
    parser.add_argument("--runtime-facts", type=pathlib.Path)
    parser.add_argument("--agent-root", action="append", default=[], type=pathlib.Path)
    parser.add_argument("--destination-root", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        registry, entries = validate(args.profile_dir, args.registry)
        roots = list(args.agent_root)
        if args.destination_root and args.destination_root not in roots:
            roots.append(args.destination_root)
        collisions = detect_collisions(args.profile_dir, roots, args.destination_root)
        if args.command == "validate":
            if collisions["conflicts"]:
                raise ProfileValidationError(f"profile-name collision(s): {json.dumps(collisions['conflicts'], sort_keys=True)}")
            print(json.dumps({"status": "valid", "schema_version": registry["schema_version"], "profiles": sorted(entries), **collisions}, sort_keys=True))
            return 0
        if not args.role or not args.runtime_facts or args.role not in entries:
            raise ProfileValidationError("preflight requires a known --role and --runtime-facts")
        result = preflight(
            entries[args.role],
            runtime_facts(args.runtime_facts),
            collisions,
            trusted_profiles=entries,
        )
        print(json.dumps(result, sort_keys=True))
        return 2 if result["decision"] == "human-gate" else 0
    except ProfileValidationError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
