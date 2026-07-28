#!/usr/bin/env python3
"""Validate Code Mode tool policy ownership, references, and packaging."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml


VALIDATOR_REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_SOURCE = Path("policies/code-mode-tool-orchestration-policy.md")
INSTALLED_POLICY = Path(
    "orchestration/policies/code-mode-tool-orchestration-policy.md"
)
SOURCE_REFERENCE = "`policies/code-mode-tool-orchestration-policy.md`"
INSTALLED_REFERENCE = (
    "`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/"
    "code-mode-tool-orchestration-policy.md`"
)
POLICY_GROUP = "shared-review-gates"
MANIFEST_TIMEOUT_SECONDS = 10
MANIFEST_MAX_OUTPUT_BYTES = 1_048_576
SOURCE_MAX_FILE_BYTES = 1_048_576
SOURCE_MAX_MARKDOWN_FILES = 2_048
SOURCE_MAX_MARKDOWN_BYTES = 16_777_216
AFFECTED_SKILLS = (
    "closure-triage",
    "code-review",
    "code-review-deep",
    "docs-review",
    "implementation-slice",
    "loop-engineering",
    "merge-review",
    "merge-review-deep",
    "milestone-continuation",
    "planning",
    "project-delivery",
    "project-orchestrator",
    "task-continuation",
)
REQUIRED_POLICY_MARKERS = (
    "functions.exec",
    "Promise.allSettled",
    "Promise.all",
    "A bounded stage is",
    "sequential fallback",
    "adaptive investigation",
    "wait/resume",
    "approval-gated calls",
    "Git index",
    "outer tool round trips",
    "total token use",
    "Project Overlays",
)


def catalog_pairs(catalog: dict) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for group_name, group in catalog.get("groups", {}).items():
        for kind in ("skills", "templates", "agent_profiles"):
            for entry in group.get(kind, []):
                pairs.add((group_name, entry["source"]))
    return pairs


def dependency_closure(groups: dict, group_name: str) -> set[str]:
    seen: set[str] = set()
    pending = list(groups[group_name].get("depends_on", []))
    while pending:
        dependency = pending.pop()
        if dependency in seen:
            continue
        if dependency not in groups:
            raise ValueError(
                f"catalog group {group_name} depends on missing group {dependency}"
            )
        seen.add(dependency)
        pending.extend(groups[dependency].get("depends_on", []))
    return seen


def installer_pairs() -> set[tuple[str, str]]:
    """Read the manifest only from the validator's trusted source checkout."""
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        try:
            result = subprocess.run(
                [str(VALIDATOR_REPO_ROOT / "install.sh"), "manifest"],
                cwd=VALIDATOR_REPO_ROOT,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=MANIFEST_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError(
                "trusted install.sh manifest timed out after "
                f"{MANIFEST_TIMEOUT_SECONDS} seconds"
            ) from error

        stdout_size = stdout_file.tell()
        stderr_size = stderr_file.tell()
        if stdout_size + stderr_size > MANIFEST_MAX_OUTPUT_BYTES:
            raise ValueError(
                "trusted install.sh manifest output exceeds "
                f"{MANIFEST_MAX_OUTPUT_BYTES} bytes"
            )
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode("utf-8", errors="replace")
        stderr = stderr_file.read().decode("utf-8", errors="replace")

    if result.returncode != 0:
        raise ValueError(
            "install.sh manifest failed: "
            + (stderr.strip() or stdout.strip())
        )
    pairs: set[tuple[str, str]] = set()
    for line in stdout.splitlines():
        if " source: " not in line:
            raise ValueError(f"unexpected installer manifest line: {line}")
        group_name, source = line.split(" source: ", 1)
        pair = (group_name, source)
        if pair in pairs:
            raise ValueError(f"duplicate installer manifest entry: {line}")
        pairs.add(pair)
    return pairs


def read_bounded_text(path: Path, label: str) -> tuple[str, int]:
    """Read one regular, non-symlink source file within a fixed byte bound."""
    try:
        before = path.lstat()
    except OSError as error:
        raise ValueError(f"cannot inspect {label}: {error}") from error
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink file")
    if before.st_size > SOURCE_MAX_FILE_BYTES:
        raise ValueError(
            f"{label} exceeds {SOURCE_MAX_FILE_BYTES} bytes"
        )

    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"cannot open {label} safely: {error}") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"{label} must be a regular file")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"{label} changed while being opened")
        if opened.st_size > SOURCE_MAX_FILE_BYTES:
            raise ValueError(
                f"{label} exceeds {SOURCE_MAX_FILE_BYTES} bytes"
            )
        chunks: list[bytes] = []
        bytes_read = 0
        while bytes_read <= SOURCE_MAX_FILE_BYTES:
            chunk = os.read(
                descriptor,
                min(65_536, SOURCE_MAX_FILE_BYTES + 1 - bytes_read),
            )
            if not chunk:
                break
            chunks.append(chunk)
            bytes_read += len(chunk)
        if bytes_read > SOURCE_MAX_FILE_BYTES:
            raise ValueError(
                f"{label} exceeds {SOURCE_MAX_FILE_BYTES} bytes"
            )
        data = b"".join(chunks)
    finally:
        os.close(descriptor)
    try:
        return data.decode("utf-8"), len(data)
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} is not valid UTF-8: {error}") from error


def validate_source(repo_root: Path) -> list[str]:
    errors: list[str] = []
    policy_path = repo_root / POLICY_SOURCE
    if not policy_path.is_file() or policy_path.is_symlink():
        return [f"missing or unsafe policy source: {POLICY_SOURCE}"]

    try:
        policy_text, _ = read_bounded_text(policy_path, POLICY_SOURCE.as_posix())
    except ValueError as error:
        return [str(error)]
    for marker in REQUIRED_POLICY_MARKERS:
        if marker not in policy_text:
            errors.append(f"policy source lacks required marker: {marker}")

    duplicated_title = []
    markdown_paths: list[Path] = []
    for markdown in repo_root.rglob("*.md"):
        if markdown == policy_path or ".git" in markdown.parts:
            continue
        markdown_paths.append(markdown)
        if len(markdown_paths) > SOURCE_MAX_MARKDOWN_FILES:
            errors.append(
                "markdown source count exceeds "
                f"{SOURCE_MAX_MARKDOWN_FILES}"
            )
            return errors
    markdown_bytes = 0
    for markdown in sorted(markdown_paths):
        relative = markdown.relative_to(repo_root).as_posix()
        try:
            markdown_text, size = read_bounded_text(markdown, relative)
        except ValueError as error:
            errors.append(str(error))
            continue
        markdown_bytes += size
        if markdown_bytes > SOURCE_MAX_MARKDOWN_BYTES:
            errors.append(
                "aggregate markdown source size exceeds "
                f"{SOURCE_MAX_MARKDOWN_BYTES} bytes"
            )
            return errors
        if "# Code Mode Tool Orchestration Policy" in markdown_text:
            duplicated_title.append(markdown.relative_to(repo_root).as_posix())
    if duplicated_title:
        errors.append(
            "policy title duplicated outside authoritative source: "
            + ", ".join(sorted(duplicated_title))
        )

    expected = set(AFFECTED_SKILLS)
    actual: set[str] = set()
    for skill_path in sorted((repo_root / "skills").glob("*/SKILL.md")):
        skill_name = skill_path.parent.name
        try:
            text, _ = read_bounded_text(
                skill_path, skill_path.relative_to(repo_root).as_posix()
            )
        except ValueError as error:
            errors.append(str(error))
            continue
        has_source = SOURCE_REFERENCE in text
        has_installed = INSTALLED_REFERENCE in text
        if has_source or has_installed:
            actual.add(skill_name)
        if has_source != has_installed:
            errors.append(
                f"incomplete Code Mode policy reference pair: "
                f"{skill_path.relative_to(repo_root)}"
            )
        if has_source and text.count(SOURCE_REFERENCE) != 1:
            errors.append(
                f"source policy reference must appear once: "
                f"{skill_path.relative_to(repo_root)}"
            )
        if has_installed and text.count(INSTALLED_REFERENCE) != 1:
            errors.append(
                f"installed policy reference must appear once: "
                f"{skill_path.relative_to(repo_root)}"
            )
    missing_references = sorted(expected - actual)
    unexpected_references = sorted(actual - expected)
    if missing_references:
        errors.append(
            "affected skills missing policy references: "
            + ", ".join(missing_references)
        )
    if unexpected_references:
        errors.append(
            "unclassified skills reference the policy: "
            + ", ".join(unexpected_references)
        )

    catalog_path = repo_root / "catalog.yaml"
    try:
        catalog_text, _ = read_bounded_text(catalog_path, "catalog.yaml")
        catalog = yaml.safe_load(catalog_text)
    except (ValueError, yaml.YAMLError) as error:
        errors.append(f"cannot read catalog.yaml: {error}")
        return errors
    groups = catalog.get("groups", {})
    if POLICY_GROUP not in groups:
        errors.append(f"catalog lacks policy group: {POLICY_GROUP}")
        return errors

    source_string = POLICY_SOURCE.as_posix()
    policy_sources = [
        entry["source"]
        for entry in groups[POLICY_GROUP].get("templates", [])
    ]
    if policy_sources.count(source_string) != 1:
        errors.append(
            f"catalog {POLICY_GROUP} templates must contain exactly one "
            f"policy source: {source_string}"
        )

    skill_groups: dict[str, str] = {}
    for group_name, group in groups.items():
        for entry in group.get("skills", []):
            skill_groups[Path(entry["source"]).name] = group_name
    for skill_name in AFFECTED_SKILLS:
        group_name = skill_groups.get(skill_name)
        if group_name is None:
            errors.append(f"affected skill missing from catalog: {skill_name}")
            continue
        try:
            reachable = dependency_closure(groups, group_name)
        except ValueError as error:
            errors.append(str(error))
            continue
        if group_name != POLICY_GROUP and POLICY_GROUP not in reachable:
            errors.append(
                f"catalog group {group_name} does not deploy the policy "
                f"required by {skill_name}"
            )

    try:
        manifest_pairs = installer_pairs()
    except ValueError as error:
        errors.append(str(error))
    else:
        expected_pairs = catalog_pairs(catalog)
        if manifest_pairs != expected_pairs:
            missing = sorted(expected_pairs - manifest_pairs)
            extra = sorted(manifest_pairs - expected_pairs)
            if missing:
                errors.append(f"installer manifest missing catalog entries: {missing}")
            if extra:
                errors.append(f"installer manifest has extra entries: {extra}")
        if (POLICY_GROUP, source_string) not in manifest_pairs:
            errors.append(
                f"installer manifest lacks {POLICY_GROUP} policy source: "
                f"{source_string}"
            )
    return errors


def validate_installed(
    repo_root: Path, skills_root: Path, templates_root: Path
) -> list[str]:
    errors: list[str] = []
    source_policy = repo_root / POLICY_SOURCE
    installed_policy = templates_root / INSTALLED_POLICY
    if not installed_policy.is_file() or installed_policy.is_symlink():
        errors.append(f"missing or unsafe installed policy: {installed_policy}")
    elif not source_policy.is_file() or source_policy.is_symlink():
        errors.append(
            f"cannot compare installed policy without safe source: {source_policy}"
        )
    elif installed_policy.read_bytes() != source_policy.read_bytes():
        errors.append(f"installed policy differs from source: {installed_policy}")

    for skill_name in AFFECTED_SKILLS:
        skill_path = skills_root / skill_name / "SKILL.md"
        if not skill_path.is_file() or skill_path.is_symlink():
            errors.append(f"missing or unsafe installed skill: {skill_path}")
            continue
        text = skill_path.read_text(encoding="utf-8")
        if INSTALLED_REFERENCE not in text:
            errors.append(
                f"installed skill lacks deployable policy reference: {skill_path}"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=VALIDATOR_REPO_ROOT,
        help=(
            "Read policy, catalog, and skill data from this root. "
            "The validator never executes that root's install.sh."
        ),
    )
    parser.add_argument("--installed-skills-root", type=Path)
    parser.add_argument("--installed-templates-root", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    errors = validate_source(repo_root)
    installed_arguments = (
        args.installed_skills_root,
        args.installed_templates_root,
    )
    if any(installed_arguments) and not all(installed_arguments):
        errors.append(
            "--installed-skills-root and --installed-templates-root "
            "must be supplied together"
        )
    elif all(installed_arguments):
        errors.extend(
            validate_installed(
                repo_root,
                args.installed_skills_root.resolve(),
                args.installed_templates_root.resolve(),
            )
        )

    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print("[OK] Code Mode tool policy ownership, references, and packaging are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
