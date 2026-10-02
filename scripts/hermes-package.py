#!/usr/bin/env python3
"""Offline, explicit, no-overwrite Hermes baseline package installation."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAMESPACE = "codex-dev-skills"
SKILLS = ("hermes-project-delivery", "hermes-review-gate", "hermes-task-continuation")
MARKER = ".install-incomplete"
RECEIPT = ".package.json"


class PackageError(ValueError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject ambiguous mappings instead of accepting PyYAML's last key wins."""


def unique_mapping(loader: UniqueKeyLoader, node, deep=False):
    loader.flatten_mapping(node)
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            if key in seen:
                raise PackageError("duplicate skill frontmatter key")
            seen.add(key)
        except TypeError as exc:
            raise PackageError("unhashable skill frontmatter key") from exc
    return loader.construct_mapping(node, deep=deep)


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def no_symlinks(path: pathlib.Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink():
            raise PackageError(f"symlink path component: {part}")


def regular_bytes(path: pathlib.Path) -> bytes:
    no_symlinks(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise PackageError(f"source must be a regular file: {path}")
    return path.read_bytes()


def safe_relative(value: object) -> pathlib.PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PackageError("invalid resource path")
    path = pathlib.PurePosixPath(value)
    if path.is_absolute() or any(p in {"", ".", ".."} for p in value.split("/")):
        raise PackageError("unsafe resource path")
    return path


def skill_name(content: bytes) -> object:
    """Match native BOM/fence semantics; reject malformed YAML rather than guess."""
    text = content.decode("utf-8").removeprefix("\ufeff")
    end = re.search(r"\n---\s*\n", text[3:]) if text.startswith("---") else None
    if not end:
        return None
    try:
        value = yaml.load(text[3:end.start() + 3], Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise PackageError("unparseable skill frontmatter") from exc
    if value is not None and not isinstance(value, dict):
        raise PackageError("skill frontmatter must be a mapping")
    name = value.get("name") if value else None
    if name is not None and not isinstance(name, str):
        raise PackageError("skill name must be a string")
    return name


def package(root: pathlib.Path = ROOT) -> dict[str, bytes]:
    catalog = json.loads(regular_bytes(root / "hermes/catalog.json"))
    if set(catalog) != {"schema_version", "runtime", "namespace", "skills", "resources"}:
        raise PackageError("invalid Hermes catalog shape")
    if (catalog["schema_version"] != 1 or catalog["runtime"] != "hermes"
            or catalog["namespace"] != NAMESPACE or catalog["skills"] != list(SKILLS)):
        raise PackageError("unsupported Hermes catalog")
    files: dict[str, bytes] = {}
    for name in SKILLS:
        source = root / "hermes/skills" / name
        no_symlinks(source)
        if not source.is_dir():
            raise PackageError(f"missing skill: {name}")
        # The baseline ships only SKILL.md. Inventory names before any read;
        # local .env/cache/support material must never enter captured bytes.
        for path in source.iterdir():
            no_symlinks(path)
            if path.name != "SKILL.md":
                raise PackageError(f"unlisted skill entry: {path.name}")
        key = f"skills/{name}/SKILL.md"
        files[key] = regular_bytes(source / "SKILL.md")
        if skill_name(files[key]) != name:
            raise PackageError(f"invalid skill frontmatter: {name}")
    if not isinstance(catalog["resources"], list):
        raise PackageError("resources must be a list")
    for value in catalog["resources"]:
        relative = safe_relative(value)
        if relative.parts[0] not in {"policies", "templates", "scripts", "docs"}:
            raise PackageError("resource outside supported dependency roots")
        if str(relative) in files:
            raise PackageError("duplicate resource")
        files[str(relative)] = regular_bytes(root / str(relative))
    if len(set(catalog["resources"])) != len(catalog["resources"]):
        raise PackageError("duplicate resource")
    return files


def target_root(raw: str, root: pathlib.Path = ROOT) -> pathlib.Path:
    path = pathlib.Path(raw)
    if not path.is_absolute() or ".." in path.parts or path.name != "skills":
        raise PackageError("--skills-dir must be an absolute path ending in skills without ..")
    no_symlinks(path)
    forbidden = (root.resolve(), pathlib.Path.home() / ".agents/skills",
                 pathlib.Path.home() / ".codex/skills",
                 pathlib.Path(os.environ.get("CODEX_HOME", str(pathlib.Path.home() / ".codex")))
                 .expanduser().resolve() / "skills")
    for other in forbidden:
        other = other.resolve()
        aliases = any(a.exists() and b.exists() and a.samefile(b)
                      for a in (path, *path.parents)
                      for b in (other,)) or any(path.exists() and b.exists() and path.samefile(b)
                                               for b in other.parents)
        if path == other or other in path.parents or path in other.parents or aliases:
            raise PackageError("destination overlaps repository or Codex discovery root")
    if not path.is_dir():
        raise PackageError("create a dedicated owned skills directory before planning")
    st = path.stat()
    if st.st_uid != os.getuid() or stat.S_IMODE(st.st_mode) & 0o022:
        raise PackageError("skills directory must be owned by current user and not group/world writable")
    child = path
    for parent in path.parents:
        info = parent.stat()
        # Root-owned sticky temporary roots cannot rename another UID's child.
        sticky_root = (info.st_uid == 0 and info.st_mode & stat.S_ISVTX
                       and child.stat().st_uid in {0, os.getuid()})
        if info.st_uid not in {0, os.getuid()} or (info.st_mode & 0o022 and not sticky_root):
            raise PackageError("destination ancestor is not trusted or is writable by others")
        child = parent
    return path


def collisions(skills_root: pathlib.Path) -> None:
    # Refuse ambiguous names throughout the selected native discovery tree.
    for path in skills_root.rglob("*"):
        no_symlinks(path)
        if path.name != "SKILL.md":
            continue
        name = skill_name(regular_bytes(path))
        if path.parent.name in SKILLS or name in SKILLS:
            raise PackageError(f"existing same-name Hermes skill: {path}")


def receipt(files: dict[str, bytes]) -> bytes:
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
    return (json.dumps({"schema_version": 1, "runtime": "hermes", "files": hashes},
                       sort_keys=True, indent=2) + "\n").encode()


def compare(target: pathlib.Path, files: dict[str, bytes], *, installing: bool = False) -> list[str]:
    no_symlinks(target)
    if not target.is_dir():
        return ["package is not installed"]
    expected = dict(files)
    expected[RECEIPT] = receipt(files)
    if installing:
        expected[MARKER] = b"Installation incomplete; preserve for diagnosis.\n"
    expected_dirs = {str(parent) for name in expected for parent in pathlib.PurePosixPath(name).parents
                     if str(parent) != "."}
    actual: set[str] = set()
    errors: list[str] = []
    for path in target.rglob("*"):
        no_symlinks(path)
        relative = path.relative_to(target).as_posix()
        if path.is_dir():
            if relative not in expected_dirs:
                errors.append(f"unexpected directory: {relative}")
        else:
            actual.add(relative)
            if relative not in expected:
                errors.append(f"unexpected file: {relative}")
            elif regular_bytes(path) != expected[relative]:
                errors.append(f"different bytes: {relative}")
    errors.extend(f"missing file: {name}" for name in sorted(set(expected) - actual))
    return sorted(errors)


def install(target: pathlib.Path, files: dict[str, bytes]) -> None:
    # Exclusive creation is the no-overwrite commit point. No rollback deletes.
    target.mkdir(mode=0o700, exist_ok=False)
    (target / MARKER).write_text("Installation incomplete; preserve for diagnosis.\n")
    for name, data in {**files, RECEIPT: receipt(files)}.items():
        path = target / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)
        path.chmod(0o600)
    errors = compare(target, files, installing=True)
    if errors:
        raise PackageError("post-install readback failed: " + "; ".join(errors))
    (target / MARKER).unlink()  # Readback passed; only the new transaction marker.


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "install", "diff"))
    parser.add_argument("--skills-dir", required=True,
                        help="explicit, owned Hermes skills directory (never inferred from private config)")
    args = parser.parse_args()
    try:
        files = package()
        skills_root = target_root(args.skills_dir)
        target = skills_root / NAMESPACE
        if args.action == "diff":
            errors = compare(target, files)
            print(json.dumps({"status": "different" if errors else "identical", "errors": errors}))
            return int(bool(errors))
        if target.exists():
            raise PackageError("namespace already exists; use diff; replacement is not supported")
        collisions(skills_root)
        if args.action == "install":
            install(target, files)
        print(json.dumps({"status": "installed" if args.action == "install" else "plan",
                          "target": str(target), "skills": list(SKILLS),
                          "files": len(files), "package_sha256": hashlib.sha256(receipt(files)).hexdigest(),
                          "runtime_qualified": False}))
        return 0
    except (PackageError, OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
