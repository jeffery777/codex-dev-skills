#!/usr/bin/env python3
"""Validate and execute the repository's stable unittest shard manifest."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tests" / "test-shards.yaml"
SHARD_ID_RE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
MODULE_RE = re.compile(r"tests\.test_[a-z0-9_]+\Z")
TOP_LEVEL_KEYS = {"schema_version", "test_root", "test_pattern", "shards"}
SHARD_KEYS = {"id", "modules"}


class ManifestError(ValueError):
    """Raised when the shard manifest is not an exact inventory partition."""


class UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.nodes.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ManifestError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


@dataclass(frozen=True)
class ShardManifest:
    shards: dict[str, tuple[str, ...]]

    @property
    def shard_ids(self) -> tuple[str, ...]:
        return tuple(self.shards)


def _require_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ManifestError(f"{label} keys differ; missing={missing}, extra={extra}")


def _module_path(repo_root: pathlib.Path, module: str) -> pathlib.Path:
    return repo_root.joinpath(*module.split(".")).with_suffix(".py")


def _discover_modules(repo_root: pathlib.Path) -> set[str]:
    test_root = repo_root / "tests"
    if not test_root.is_dir() or test_root.is_symlink():
        raise ManifestError("test root must be a regular directory: tests")
    modules: set[str] = set()
    for path in test_root.rglob("test_*.py"):
        if path.is_symlink() or not path.is_file():
            raise ManifestError(f"discovered test entry must be a regular file: {path}")
        if path.parent != test_root:
            raise ManifestError(
                f"nested test modules require an explicit manifest-contract update: {path}"
            )
        modules.add(f"tests.{path.stem}")
    if not modules:
        raise ManifestError("no repository test modules were discovered")
    return modules


def load_manifest(
    manifest_path: pathlib.Path = DEFAULT_MANIFEST,
    repo_root: pathlib.Path = ROOT,
) -> ShardManifest:
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ManifestError(f"manifest must be a regular file: {manifest_path}")
    try:
        document = yaml.load(
            manifest_path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ManifestError(f"cannot read shard manifest: {exc}") from exc
    if not isinstance(document, dict):
        raise ManifestError("manifest root must be a mapping")
    _require_exact_keys(document, TOP_LEVEL_KEYS, "manifest")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ManifestError("schema_version must be integer 1")
    if document["test_root"] != "tests":
        raise ManifestError("test_root must be exactly 'tests'")
    if document["test_pattern"] != "test_*.py":
        raise ManifestError("test_pattern must be exactly 'test_*.py'")
    raw_shards = document["shards"]
    if not isinstance(raw_shards, list) or not raw_shards:
        raise ManifestError("shards must be a non-empty list")

    shards: dict[str, tuple[str, ...]] = {}
    module_owners: dict[str, str] = {}
    shard_ids: list[str] = []
    for index, raw_shard in enumerate(raw_shards):
        if not isinstance(raw_shard, dict):
            raise ManifestError(f"shard {index} must be a mapping")
        _require_exact_keys(raw_shard, SHARD_KEYS, f"shard {index}")
        shard_id = raw_shard["id"]
        modules = raw_shard["modules"]
        if not isinstance(shard_id, str) or not SHARD_ID_RE.fullmatch(shard_id):
            raise ManifestError(f"invalid shard id: {shard_id!r}")
        if shard_id in shards:
            raise ManifestError(f"duplicate shard id: {shard_id}")
        if not isinstance(modules, list) or not modules:
            raise ManifestError(f"shard {shard_id} must contain modules")
        if modules != sorted(modules):
            raise ManifestError(f"shard {shard_id} modules must be lexically sorted")
        checked_modules: list[str] = []
        for module in modules:
            if not isinstance(module, str) or not MODULE_RE.fullmatch(module):
                raise ManifestError(f"invalid test module in {shard_id}: {module!r}")
            if module in module_owners:
                raise ManifestError(
                    f"duplicate module {module}: {module_owners[module]} and {shard_id}"
                )
            path = _module_path(repo_root, module)
            if path.is_symlink() or not path.is_file():
                raise ManifestError(f"manifest module must be a regular file: {module}")
            module_owners[module] = shard_id
            checked_modules.append(module)
        shard_ids.append(shard_id)
        shards[shard_id] = tuple(checked_modules)

    if shard_ids != sorted(shard_ids):
        raise ManifestError("shard ids must be lexically sorted")
    discovered = _discover_modules(repo_root)
    assigned = set(module_owners)
    if assigned != discovered:
        raise ManifestError(
            "test inventory differs; "
            f"unassigned={sorted(discovered - assigned)}, "
            f"not_discovered={sorted(assigned - discovered)}"
        )
    return ShardManifest(shards=shards)


def run_shard(manifest: ShardManifest, shard_id: str, repo_root: pathlib.Path) -> int:
    modules = manifest.shards.get(shard_id)
    if modules is None:
        raise ManifestError(f"unknown shard: {shard_id}")
    print(f"[INFO] Running shard {shard_id} ({len(modules)} modules)", flush=True)
    return subprocess.run(
        [sys.executable, "-m", "unittest", *modules], cwd=repo_root, check=False
    ).returncode


def run_all(manifest: ShardManifest, repo_root: pathlib.Path) -> int:
    """Run every shard in manifest order and report all failures."""
    failed: list[str] = []
    for shard_id in manifest.shard_ids:
        if run_shard(manifest, shard_id, repo_root) != 0:
            failed.append(shard_id)
    if failed:
        print(f"[FAIL] Failed shards: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="validate exact shard inventory")
    list_parser = subparsers.add_parser("list", help="list shard identifiers")
    list_parser.add_argument("--format", choices=("plain", "json"), default="plain")
    run_parser = subparsers.add_parser("run", help="run one validated shard")
    run_parser.add_argument("shard")
    subparsers.add_parser("run-all", help="run every validated shard sequentially")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        manifest = load_manifest(arguments.manifest, ROOT)
        if arguments.command == "validate":
            module_count = sum(len(modules) for modules in manifest.shards.values())
            print(
                f"Validated {len(manifest.shards)} shards and {module_count} test modules."
            )
            return 0
        if arguments.command == "list":
            if arguments.format == "json":
                print(json.dumps(manifest.shard_ids, separators=(",", ":")))
            else:
                print("\n".join(manifest.shard_ids))
            return 0
        if arguments.command == "run":
            return run_shard(manifest, arguments.shard, ROOT)
        return run_all(manifest, ROOT)
    except ManifestError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
