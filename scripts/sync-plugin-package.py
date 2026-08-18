#!/usr/bin/env python3
"""Build or verify the tracked, allowlisted Codex plugin package."""

from __future__ import annotations

import argparse
import filecmp
import pathlib
import shutil
import stat
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "plugin" / "codex-dev-skills"
MANIFEST_PATH = ".codex-plugin/plugin.json"
SHARED_FILES = {
    "policies/code-mode-tool-orchestration-policy.md",
    "docs/native-runtime-capabilities.md",
}
SHARED_PREFIXES = ("templates/orchestration/",)


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "skills", "policies", "templates", "docs"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    paths = result.stdout.decode("utf-8").split("\0")
    return {path for path in paths if path}


def package_sources() -> set[str]:
    tracked = tracked_files()
    selected = {
        path
        for path in tracked
        if path.startswith("skills/")
        or path in SHARED_FILES
        or path.startswith(SHARED_PREFIXES)
    }
    missing = SHARED_FILES - selected
    if missing:
        raise RuntimeError(f"missing tracked plugin resources: {sorted(missing)}")
    return selected


def require_regular_source(path: pathlib.Path) -> None:
    mode = path.lstat().st_mode
    if not stat.S_ISREG(mode):
        raise RuntimeError(f"plugin source must be a regular non-symlink file: {path}")


def expected_inventory(expected_sources: set[str]) -> tuple[set[str], set[str]]:
    files = expected_sources | {MANIFEST_PATH}
    directories: set[str] = set()
    for relative in files:
        parent = pathlib.PurePosixPath(relative).parent
        while parent != pathlib.PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return files, directories


def actual_inventory(package_root: pathlib.Path) -> tuple[dict[str, str], list[str]]:
    entries: dict[str, str] = {}
    errors: list[str] = []
    try:
        root_mode = package_root.lstat().st_mode
    except FileNotFoundError:
        return entries, [f"plugin package root is missing: {package_root}"]
    if stat.S_ISLNK(root_mode) or not stat.S_ISDIR(root_mode):
        return entries, [f"plugin package root must be a regular directory: {package_root}"]
    for path in package_root.rglob("*"):
        relative = path.relative_to(package_root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISREG(mode):
            entries[relative] = "file"
        elif stat.S_ISDIR(mode):
            entries[relative] = "directory"
        elif stat.S_ISLNK(mode):
            entries[relative] = "symlink"
        else:
            entries[relative] = "special"
    return entries, errors


def verify(expected: set[str], package_root: pathlib.Path = PACKAGE_ROOT) -> list[str]:
    expected_files, expected_directories = expected_inventory(expected)
    inventory, errors = actual_inventory(package_root)
    actual_files = {path for path, kind in inventory.items() if kind == "file"}
    actual_directories = {path for path, kind in inventory.items() if kind == "directory"}
    for path in sorted(expected_files - actual_files):
        errors.append(f"missing generated plugin file: {path}")
    for path in sorted(expected_directories - actual_directories):
        errors.append(f"missing generated plugin directory: {path}")
    for path in sorted(actual_files - expected_files):
        errors.append(f"unexpected plugin file: {path}")
    for path in sorted(actual_directories - expected_directories):
        errors.append(f"unexpected plugin directory: {path}")
    for path, kind in sorted(inventory.items()):
        if kind not in {"file", "directory"}:
            errors.append(f"unexpected plugin {kind}: {path}")
    for relative in sorted(expected & actual_files):
        source = ROOT / relative
        target = package_root / relative
        require_regular_source(source)
        if target.is_symlink() or not target.is_file():
            errors.append(f"generated plugin path is not a regular file: {relative}")
        elif not filecmp.cmp(source, target, shallow=False):
            errors.append(f"generated plugin file differs from canonical source: {relative}")
        elif stat.S_IMODE(source.stat().st_mode) != stat.S_IMODE(target.stat().st_mode):
            errors.append(f"generated plugin file mode differs from canonical source: {relative}")
    return errors


def write(expected: set[str]) -> None:
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    for relative in sorted(expected):
        source = ROOT / relative
        require_regular_source(source)
        target = PACKAGE_ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="synchronize the generated package before verifying it",
    )
    parser.add_argument(
        "--package-root",
        type=pathlib.Path,
        default=PACKAGE_ROOT,
        help="verify an alternate package root (not supported with --write)",
    )
    args = parser.parse_args()
    package_root = args.package_root.resolve()
    if args.write and package_root != PACKAGE_ROOT.resolve():
        parser.error("--write cannot be combined with an alternate --package-root")
    expected = package_sources()
    if args.write:
        write(expected)
    errors = verify(expected, package_root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"plugin package verified: {len(expected)} generated files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
