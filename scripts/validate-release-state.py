#!/usr/bin/env python3
"""Validate the offline, non-recursive repository release-state contract."""

from __future__ import annotations

import json
import pathlib
import re
import stat
import sys
from collections.abc import Iterable

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAX_TEXT_BYTES = 512 * 1024
SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z")
INSTALLER_VERSION = re.compile(r'^VERSION="([^"]+)"$', re.MULTILINE)
MUTABLE_ACTIVE_ASSERTIONS = (
    re.compile(r"(?:current|latest) published (?:version|release)", re.IGNORECASE),
    re.compile(r"current development candidate", re.IGNORECASE),
    re.compile(
        r"(?:current|latest) v[0-9]+\.[0-9]+\.[0-9]+ release notes(?: candidate)?",
        re.IGNORECASE,
    ),
)
ACTIVE_GUIDANCE = (
    "README.md",
    "docs/roadmap.md",
    "docs/release-readiness.md",
)


class ReleaseStateError(ValueError):
    """A deterministic offline release-state validation failure."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    loader.flatten_mapping(node)
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ReleaseStateError("YAML mapping keys must be hashable") from exc
        if duplicate:
            raise ReleaseStateError(f"YAML mapping contains duplicate key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def construct_unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseStateError(f"JSON object contains duplicate key: {key!r}")
        result[key] = value
    return result


def read_regular_text(relative: str) -> str:
    path = ROOT / relative
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise ReleaseStateError(f"required release-state file is missing: {relative}") from exc
    if not stat.S_ISREG(mode):
        raise ReleaseStateError(
            f"release-state file must be a regular non-symlink file: {relative}"
        )
    data = path.read_bytes()
    if len(data) > MAX_TEXT_BYTES:
        raise ReleaseStateError(f"release-state file exceeds size limit: {relative}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReleaseStateError(f"release-state file is not strict UTF-8: {relative}") from exc


def require_exactly_one(values: Iterable[str], label: str) -> str:
    found = list(values)
    if len(found) != 1:
        raise ReleaseStateError(f"{label} must declare exactly one version")
    return found[0]


def source_package_version() -> str:
    catalog_text = read_regular_text("catalog.yaml")
    try:
        catalog = yaml.load(catalog_text, Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise ReleaseStateError("catalog.yaml is not valid YAML") from exc
    if not isinstance(catalog, dict) or not isinstance(catalog.get("version"), str):
        raise ReleaseStateError("catalog.yaml must declare a string version")
    version = catalog["version"]
    if SEMVER.fullmatch(version) is None:
        raise ReleaseStateError(f"catalog.yaml version is not strict SemVer: {version}")
    return version


def validate_version_parity(version: str) -> None:
    installer = read_regular_text("install.sh")
    installer_version = require_exactly_one(
        INSTALLER_VERSION.findall(installer), "install.sh"
    )
    manifest_text = read_regular_text(
        "plugin/codex-dev-skills/.codex-plugin/plugin.json"
    )
    try:
        manifest = json.loads(
            manifest_text,
            object_pairs_hook=construct_unique_json_object,
        )
    except json.JSONDecodeError as exc:
        raise ReleaseStateError("plugin manifest is not valid JSON") from exc
    manifest_version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(manifest_version, str):
        raise ReleaseStateError("plugin manifest must declare a string version")
    mismatches = [
        f"install.sh={installer_version}" if installer_version != version else "",
        f"plugin manifest={manifest_version}" if manifest_version != version else "",
    ]
    mismatches = [entry for entry in mismatches if entry]
    if mismatches:
        raise ReleaseStateError(
            f"source/package version {version} does not match " + ", ".join(mismatches)
        )


def validate_candidate_record(version: str) -> None:
    relative = f"docs/release-notes-v{version}.md"
    notes = read_regular_text(relative)
    heading = f"# Release Notes: v{version}"
    first_content = next((line for line in notes.splitlines() if line.strip()), "")
    if first_content != heading:
        raise ReleaseStateError(f"{relative} must begin with exact heading: {heading}")
    status = re.search(
        r"^Status:[^\n]*\brelease candidate\b[^\n]*\bIssue #([1-9][0-9]*)\b",
        notes,
        re.IGNORECASE | re.MULTILINE,
    )
    if status is None:
        raise ReleaseStateError(
            f"{relative} must declare release-candidate status and an Issue number"
        )
    normalized_notes = " ".join(notes.split())
    if "separate human gates" not in normalized_notes.lower():
        raise ReleaseStateError(f"{relative} must preserve separate human gates")
    required_sections = (
        "## Compatibility And Boundaries",
        "## Verification And Release Gate",
        "## Traceability",
    )
    lines = notes.splitlines()

    def section_body(section: str) -> list[str]:
        try:
            start = lines.index(section) + 1
        except ValueError as exc:
            raise ReleaseStateError(
                f"{relative} lacks required candidate section: {section}"
            ) from exc
        body: list[str] = []
        for line in lines[start:]:
            if line.startswith("## "):
                break
            if line.strip():
                body.append(line)
        if not body:
            raise ReleaseStateError(
                f"{relative} candidate section must not be empty: {section}"
            )
        return body

    for section in required_sections:
        section_body(section)
    scope_sections = [
        line
        for line in lines
        if line.startswith("## ") and line not in required_sections
    ]
    if not scope_sections or not any(section_body(section) for section in scope_sections):
        raise ReleaseStateError(f"{relative} must contain a substantive release-scope section")
    issue = status.group(1)
    issue_link = re.compile(
        rf"Issue #{issue}: <https://github\.com/[^/\s]+/[^/\s]+/issues/{issue}>",
    )
    if issue_link.search(notes) is None:
        raise ReleaseStateError(
            f"{relative} traceability must link its declared Issue #{issue}"
        )


def validate_active_guidance() -> None:
    required = {
        "README.md": (
            "Repository source/package version",
            "GitHub Release metadata",
            "point-in-time",
        ),
        "docs/roadmap.md": (
            "release-state contract",
            "publication truth",
        ),
        "docs/release-readiness.md": (
            "Release-State Contract",
            "Ordinary offline repository validation",
            "GitHub Release metadata",
        ),
    }
    for relative in ACTIVE_GUIDANCE:
        text = read_regular_text(relative)
        for pattern in MUTABLE_ACTIVE_ASSERTIONS:
            if pattern.search(text):
                raise ReleaseStateError(
                    f"active guidance contains mutable release-state assertion: {relative}"
                )
        for phrase in required[relative]:
            if phrase not in text:
                raise ReleaseStateError(
                    f"active guidance lacks release-state contract phrase in {relative}: {phrase}"
                )


def validate_policy() -> None:
    policy = read_regular_text("policies/release-state-contract.md")
    normalized_policy = " ".join(policy.split())
    for phrase in (
        "`catalog.yaml` is the canonical offline source/package version",
        "GitHub Release metadata and the corresponding annotated tag are publication truth",
        "Ordinary repository validation is offline",
        "point-in-time historical record",
        "must not declare readiness only because repository tests pass",
    ):
        if phrase not in normalized_policy:
            raise ReleaseStateError(f"release-state policy lacks required contract: {phrase}")


def validate_repo() -> str:
    version = source_package_version()
    validate_version_parity(version)
    validate_candidate_record(version)
    validate_active_guidance()
    validate_policy()
    return version


def main() -> int:
    if len(sys.argv) != 1:
        print("validate-release-state.py accepts no arguments", file=sys.stderr)
        return 2
    try:
        version = validate_repo()
    except (OSError, ReleaseStateError) as exc:
        print(f"release-state validation failed: {exc}", file=sys.stderr)
        return 1
    print(
        "offline release-state structural checks valid for "
        f"source/package version {version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
