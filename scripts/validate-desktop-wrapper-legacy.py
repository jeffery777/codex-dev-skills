#!/usr/bin/env python3
"""Validate the frozen historical Desktop runtime wrapper inventory."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


SCHEMA_VERSION = "desktop-runtime-wrapper-legacy-inventory/v1"
INVENTORY_PATH = Path("docs/desktop-runtime-wrapper-v1-inventory.yaml")
MAX_INVENTORY_BYTES = 131_072
MAX_SOURCE_FILE_BYTES = 2_097_152
MAX_SCANNED_FILES = 4_096
MAX_SCANNED_SOURCE_BYTES = 67_108_864
REFERENCE_TOKEN = "desktop_runtime_"
IGNORED_REFERENCE_PATHS = {
    INVENTORY_PATH.as_posix(),
    "scripts/validate-desktop-wrapper-legacy.py",
    "tests/test_desktop_wrapper_legacy.py",
}
EXPECTED_TOP_LEVEL_KEYS = {
    "active_entrypoints",
    "artifact_globs",
    "artifacts",
    "canonical_source_only",
    "classified_reference_files",
    "generated_reference_roots",
    "prohibited_active_roots",
    "prohibited_runnable_reference",
    "schema_version",
    "status",
    "sunset_requirements",
}
EXPECTED_ARTIFACT_GLOBS = {
    "scripts": "scripts/desktop_runtime_*.py",
    "tests": "tests/test_desktop_runtime_*.py",
}
EXPECTED_GENERATED_ROOTS = ["plugin/codex-dev-skills"]
EXPECTED_PROHIBITED_ROOTS = [
    ".agents/plugins",
    ".codex",
    ".codex-plugin",
    "CONTRIBUTING.md",
    "README.md",
    "catalog.yaml",
    "docs/desktop-runtime-wrapper-v1-deprecation.md",
    "docs/native-runtime-capabilities.md",
    "docs/release-notes-v0.16.3.md",
    "docs/release-readiness.md",
    "docs/roadmap.md",
    "docs/runtime-compatibility.md",
    "docs/skill-selection-guide.md",
    "docs/source-classification.md",
    "examples",
    "install.sh",
    "policies",
    "skills",
]
EXPECTED_SUNSET_REQUIREMENTS = [
    "zero-active-runnable-consumers",
    "native-adapter-coverage-for-retained-current-behavior",
    "historical-security-fixtures-independent-of-wrapper-entrypoints",
    "no-executable-legacy-guidance",
    "separately-reviewed-exact-deletion-plan",
    "explicit-destructive-action-authorization",
]
SCANNED_SUFFIXES = {".md", ".py", ".sh", ".yaml", ".yml"}
GUIDANCE_SUFFIXES = {".md", ".yaml", ".yml"}
IGNORED_SOURCE_DIRECTORIES = {"__pycache__"}
EXPLICIT_ACTIVE_FILES = (
    ".agents/plugins/marketplace.json",
    ".codex-plugin/plugin.json",
    ".codex/hooks.json",
)
ALLOWED_ACTIVE_REFERENCE_MARKERS = (
    "compatibility evidence",
    "historical",
    "legacy",
)
FORBIDDEN_ACTIVE_IMPORT_PATTERNS = (
    re.compile(
        r"^\s*import\s+(?:scripts\.)?desktop_runtime_",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*from\s+scripts(?:\.desktop_runtime_|\s+import\s+desktop_runtime_)",
        re.IGNORECASE | re.MULTILINE,
    ),
)
FORBIDDEN_ACTIVE_REFERENCE_PATTERNS = (
    re.compile(r"desktop_runtime_[A-Za-z0-9_*-]*\.py", re.IGNORECASE),
    re.compile(r"scripts\.desktop_runtime_", re.IGNORECASE),
    *FORBIDDEN_ACTIVE_IMPORT_PATTERNS,
)
EXECUTABLE_LEGACY_GUIDANCE_PATTERNS = (
    re.compile(
        r"(?:(?:uv\s+run\s+)?"
        r"(?:python(?:3)?|\./scripts/project-python|pytest))\b[^\n]*"
        r"(?:scripts[/.]desktop_runtime_|test_desktop_runtime_)",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*(?:[-*]\s*|\d+\.\s*)?(?:`+\s*)?(?:\$\s*)?"
        r"\./scripts/desktop_runtime_[A-Za-z0-9_-]*\.py\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*(?:[-*]\s*|\d+\.\s*)?"
        r"(?:to\s+[^,\n]+,\s*)?(?:run|execute|invoke|inject)\b[^\n]*"
        r"desktop_runtime_",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"^\s*\d+\.[^\n]*\b(?:run|execute|invoke|inject)\b[^\n]*desktop_runtime_",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"\bexecute_create_thread_with_injected_adapter\s*\(",
        re.IGNORECASE | re.MULTILINE,
    ),
)


class LegacyInventoryError(ValueError):
    """Raised when the legacy inventory or retained surface is invalid."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError as error:
            raise LegacyInventoryError("YAML mapping keys must be scalar") from error
        if key in mapping:
            raise LegacyInventoryError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _safe_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise LegacyInventoryError(f"{label} must be a non-empty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise LegacyInventoryError(f"{label} must be a safe relative POSIX path: {value}")
    if value != path.as_posix():
        raise LegacyInventoryError(f"{label} must use normalized POSIX syntax: {value}")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise LegacyInventoryError(f"{label} must be {qualifier}")
    result = [_safe_relative_path(item, f"{label} entry") for item in value]
    if len(result) != len(set(result)):
        raise LegacyInventoryError(f"{label} contains duplicate entries")
    if result != sorted(result):
        raise LegacyInventoryError(f"{label} must be sorted")
    return result


def _read_regular_text(path: Path, label: str, limit: int) -> str:
    try:
        before = path.lstat()
    except OSError as error:
        raise LegacyInventoryError(f"cannot inspect {label}: {error}") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise LegacyInventoryError(f"{label} must be a regular non-symlink file")
    if before.st_size > limit:
        raise LegacyInventoryError(f"{label} exceeds {limit} bytes")

    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise LegacyInventoryError(f"cannot open {label} safely: {error}") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise LegacyInventoryError(f"{label} must be a regular file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise LegacyInventoryError(f"{label} changed while being opened")
        chunks: list[bytes] = []
        total = 0
        while total <= limit:
            chunk = os.read(descriptor, min(65_536, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
        if total > limit:
            raise LegacyInventoryError(f"{label} exceeds {limit} bytes")
    finally:
        os.close(descriptor)
    try:
        return b"".join(chunks).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise LegacyInventoryError(f"{label} must be strict UTF-8") from error


def _load_inventory(repo_root: Path) -> dict[str, Any]:
    text = _read_regular_text(
        repo_root / INVENTORY_PATH,
        INVENTORY_PATH.as_posix(),
        MAX_INVENTORY_BYTES,
    )
    try:
        document = yaml.load(text, Loader=UniqueKeyLoader)
    except LegacyInventoryError:
        raise
    except yaml.YAMLError as error:
        raise LegacyInventoryError(f"inventory must contain valid YAML: {error}") from error
    if not isinstance(document, dict):
        raise LegacyInventoryError("inventory must contain a YAML mapping")
    if set(document) != EXPECTED_TOP_LEVEL_KEYS:
        missing = sorted(EXPECTED_TOP_LEVEL_KEYS - set(document))
        extra = sorted(set(document) - EXPECTED_TOP_LEVEL_KEYS)
        raise LegacyInventoryError(
            f"inventory keys mismatch; missing={missing}, extra={extra}"
        )
    return document


def _is_under(relative: str, roots: list[str]) -> bool:
    path = PurePosixPath(relative)
    return any(path == PurePosixPath(root) or PurePosixPath(root) in path.parents for root in roots)


def _is_guidance_file(path: Path) -> bool:
    return path.name in {"README", "README.md"} or path.suffix in GUIDANCE_SUFFIXES


def _candidate_source_files(repo_root: Path, generated_roots: list[str]) -> list[Path]:
    candidates: list[Path] = []

    def fail_walk(error: OSError) -> None:
        raise LegacyInventoryError(f"cannot scan canonical source tree: {error}")

    for directory, child_directories, filenames in os.walk(
        repo_root, topdown=True, onerror=fail_walk, followlinks=False
    ):
        directory_path = Path(directory)
        retained_directories: list[str] = []
        for name in sorted(child_directories):
            child = directory_path / name
            relative = child.relative_to(repo_root).as_posix()
            if (name.startswith(".") and name != ".github") or name in (
                IGNORED_SOURCE_DIRECTORIES
            ):
                continue
            if child.is_symlink() or _is_under(relative, generated_roots):
                continue
            retained_directories.append(name)
        child_directories[:] = retained_directories
        for name in sorted(filenames):
            path = directory_path / name
            relative_text = path.relative_to(repo_root).as_posix()
            if _is_under(relative_text, generated_roots):
                continue
            if name not in {"README", "README.md"} and path.suffix not in SCANNED_SUFFIXES:
                continue
            candidates.append(path)
            if len(candidates) > MAX_SCANNED_FILES:
                raise LegacyInventoryError(
                    f"canonical source scan exceeds {MAX_SCANNED_FILES} files"
                )
    for relative in EXPLICIT_ACTIVE_FILES:
        path = repo_root / relative
        if path.exists() and path not in candidates:
            candidates.append(path)
    return sorted(candidates)


def _candidate_generated_documentation_files(
    repo_root: Path, generated_roots: list[str]
) -> list[Path]:
    candidates: list[Path] = []

    def fail_walk(error: OSError) -> None:
        raise LegacyInventoryError(f"cannot scan generated documentation: {error}")

    for relative_root in generated_roots:
        root = repo_root / relative_root
        if not root.exists():
            raise LegacyInventoryError(
                f"generated documentation root is missing: {relative_root}"
            )
        try:
            root_status = root.lstat()
        except OSError as error:
            raise LegacyInventoryError(
                f"cannot inspect generated documentation root {relative_root}: {error}"
            ) from error
        if stat.S_ISLNK(root_status.st_mode) or not stat.S_ISDIR(root_status.st_mode):
            raise LegacyInventoryError(
                f"generated documentation root must be a non-symlink directory: {relative_root}"
            )
        for directory, child_directories, filenames in os.walk(
            root, topdown=True, onerror=fail_walk, followlinks=False
        ):
            directory_path = Path(directory)
            retained_directories: list[str] = []
            for name in sorted(child_directories):
                child = directory_path / name
                if child.is_symlink():
                    relative = child.relative_to(repo_root).as_posix()
                    raise LegacyInventoryError(
                        "generated documentation directory must not be a symlink: "
                        f"{relative}"
                    )
                retained_directories.append(name)
            child_directories[:] = retained_directories
            for name in sorted(filenames):
                path = directory_path / name
                if not _is_guidance_file(path):
                    continue
                candidates.append(path)
                if len(candidates) > MAX_SCANNED_FILES:
                    raise LegacyInventoryError(
                        f"generated documentation scan exceeds {MAX_SCANNED_FILES} files"
                    )
    return sorted(candidates)


def _validate_active_reference(relative: str, text: str, runnable: str) -> None:
    if runnable.casefold() in text.casefold() or any(
        pattern.search(text) for pattern in FORBIDDEN_ACTIVE_REFERENCE_PATTERNS
    ):
        raise LegacyInventoryError(
            f"active surface contains runnable legacy wrapper reference: {relative}"
        )
    for line_number, line in enumerate(text.splitlines(), start=1):
        if REFERENCE_TOKEN.casefold() not in line.casefold():
            continue
        normalized = line.casefold()
        if not any(marker in normalized for marker in ALLOWED_ACTIVE_REFERENCE_MARKERS):
            raise LegacyInventoryError(
                "active surface contains unqualified legacy wrapper reference: "
                f"{relative}:{line_number}"
            )


def _validate_test_import(relative: str, text: str) -> None:
    if any(pattern.search(text) for pattern in FORBIDDEN_ACTIVE_IMPORT_PATTERNS):
        raise LegacyInventoryError(
            f"active test contains legacy wrapper import: {relative}"
        )


def _validate_no_executable_legacy_guidance(relative: str, text: str) -> None:
    normalized = re.sub(r"\\\s*\n\s*", " ", text)
    if any(
        pattern.search(normalized)
        for pattern in EXECUTABLE_LEGACY_GUIDANCE_PATTERNS
    ):
        raise LegacyInventoryError(
            f"documentation contains executable legacy wrapper guidance: {relative}"
        )


def validate(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    document = _load_inventory(root)
    if document["schema_version"] != SCHEMA_VERSION:
        raise LegacyInventoryError(f"schema_version must be {SCHEMA_VERSION}")
    if document["status"] != "frozen-historical-only":
        raise LegacyInventoryError("status must be frozen-historical-only")
    if document["canonical_source_only"] is not True:
        raise LegacyInventoryError("canonical_source_only must be true")
    if document["active_entrypoints"] != []:
        raise LegacyInventoryError("active_entrypoints must remain empty")
    if document["artifact_globs"] != EXPECTED_ARTIFACT_GLOBS:
        raise LegacyInventoryError("artifact_globs must match the fixed wrapper patterns")
    if document["prohibited_runnable_reference"] != "scripts/desktop_runtime_":
        raise LegacyInventoryError(
            "prohibited_runnable_reference must be scripts/desktop_runtime_"
        )
    if document["sunset_requirements"] != EXPECTED_SUNSET_REQUIREMENTS:
        raise LegacyInventoryError("sunset_requirements do not match the required gate")

    artifacts = document["artifacts"]
    if not isinstance(artifacts, dict) or set(artifacts) != {"scripts", "tests"}:
        raise LegacyInventoryError("artifacts must contain only scripts and tests")
    script_paths = _string_list(artifacts["scripts"], "artifacts.scripts")
    test_paths = _string_list(artifacts["tests"], "artifacts.tests")
    classified = _string_list(
        document["classified_reference_files"], "classified_reference_files"
    )
    generated_roots = _string_list(
        document["generated_reference_roots"], "generated_reference_roots"
    )
    prohibited_roots = _string_list(
        document["prohibited_active_roots"], "prohibited_active_roots"
    )
    if generated_roots != EXPECTED_GENERATED_ROOTS:
        raise LegacyInventoryError(
            f"generated_reference_roots must be {EXPECTED_GENERATED_ROOTS}"
        )
    if prohibited_roots != EXPECTED_PROHIBITED_ROOTS:
        raise LegacyInventoryError(
            f"prohibited_active_roots must be {EXPECTED_PROHIBITED_ROOTS}"
        )
    if any(_is_under(path, generated_roots) for path in script_paths + test_paths + classified):
        raise LegacyInventoryError("canonical inventory must not list generated plugin paths")

    expected_scripts = sorted(
        path.relative_to(root).as_posix()
        for path in root.glob(EXPECTED_ARTIFACT_GLOBS["scripts"])
    )
    expected_tests = sorted(
        path.relative_to(root).as_posix()
        for path in root.glob(EXPECTED_ARTIFACT_GLOBS["tests"])
    )
    if script_paths != expected_scripts:
        raise LegacyInventoryError(
            f"wrapper script inventory mismatch; expected={expected_scripts}, actual={script_paths}"
        )
    if test_paths != expected_tests:
        raise LegacyInventoryError(
            f"wrapper test inventory mismatch; expected={expected_tests}, actual={test_paths}"
        )

    artifact_set = set(script_paths + test_paths)
    for relative in sorted(artifact_set):
        _read_regular_text(root / relative, relative, MAX_SOURCE_FILE_BYTES)
    actual_references: set[str] = set()
    scanned_source_bytes = 0
    for path in _candidate_source_files(root, generated_roots):
        relative = path.relative_to(root).as_posix()
        if relative in IGNORED_REFERENCE_PATHS:
            continue
        text = _read_regular_text(path, relative, MAX_SOURCE_FILE_BYTES)
        scanned_source_bytes += len(text.encode("utf-8"))
        if scanned_source_bytes > MAX_SCANNED_SOURCE_BYTES:
            raise LegacyInventoryError(
                "aggregate canonical source scan exceeds "
                f"{MAX_SCANNED_SOURCE_BYTES} bytes"
            )
        has_reference = REFERENCE_TOKEN.casefold() in text.casefold()
        if has_reference:
            if relative not in artifact_set:
                actual_references.add(relative)
            is_inventory_artifact = relative in artifact_set
            if _is_under(relative, prohibited_roots) or (
                _is_under(relative, ["scripts"]) and not is_inventory_artifact
            ):
                _validate_active_reference(
                    relative,
                    text,
                    document["prohibited_runnable_reference"],
                )
            elif _is_under(relative, ["tests"]) and not is_inventory_artifact:
                _validate_test_import(relative, text)
        if _is_guidance_file(path):
            _validate_no_executable_legacy_guidance(relative, text)
    if classified != sorted(actual_references):
        raise LegacyInventoryError(
            "classified reference inventory mismatch; "
            f"expected={sorted(actual_references)}, actual={classified}"
        )

    generated_documentation_bytes = 0
    for path in _candidate_generated_documentation_files(root, generated_roots):
        relative = path.relative_to(root).as_posix()
        text = _read_regular_text(path, relative, MAX_SOURCE_FILE_BYTES)
        generated_documentation_bytes += len(text.encode("utf-8"))
        if generated_documentation_bytes > MAX_SCANNED_SOURCE_BYTES:
            raise LegacyInventoryError(
                "aggregate generated documentation scan exceeds "
                f"{MAX_SCANNED_SOURCE_BYTES} bytes"
            )
        _validate_no_executable_legacy_guidance(relative, text)

    return {
        "artifact_count": len(artifact_set),
        "active_entrypoint_count": 0,
        "classified_reference_count": len(classified),
        "kind": "desktop-runtime-wrapper-legacy-status",
        "schema_version": SCHEMA_VERSION,
        "status": "valid",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)
    try:
        result = validate(arguments.repo_root)
    except LegacyInventoryError as error:
        print(
            json.dumps(
                {
                    "kind": "desktop-runtime-wrapper-legacy-status",
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
