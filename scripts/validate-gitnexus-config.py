#!/usr/bin/env python3
"""Fail-closed validation for the repository GitNexus analyze defaults."""

from __future__ import annotations

import argparse
import json
import pathlib
import stat
import sys
from typing import Any


MAX_CONFIG_BYTES = 4096
EXPECTED_TOP_LEVEL_KEYS = {"analyze"}
EXPECTED_ANALYZE_KEYS = {"indexOnly"}


class GitNexusConfigError(ValueError):
    """Raised when the repository GitNexus configuration is unsafe."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GitNexusConfigError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def validate(path: pathlib.Path) -> dict[str, Any]:
    """Validate one exact, regular, bounded `.gitnexusrc` file."""

    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise GitNexusConfigError(".gitnexusrc is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise GitNexusConfigError(".gitnexusrc must be a regular non-symlink file")
    if metadata.st_size > MAX_CONFIG_BYTES:
        raise GitNexusConfigError(".gitnexusrc exceeds the size limit")

    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise GitNexusConfigError(".gitnexusrc must be strict UTF-8") from error

    try:
        document = json.loads(text, object_pairs_hook=_object_without_duplicates)
    except GitNexusConfigError:
        raise
    except (json.JSONDecodeError, TypeError) as error:
        raise GitNexusConfigError(".gitnexusrc must contain valid JSON") from error

    if not isinstance(document, dict):
        raise GitNexusConfigError(".gitnexusrc must contain a JSON object")
    if set(document) != EXPECTED_TOP_LEVEL_KEYS:
        raise GitNexusConfigError(".gitnexusrc must contain only the analyze key")

    analyze = document["analyze"]
    if not isinstance(analyze, dict):
        raise GitNexusConfigError("analyze must be an object")
    if set(analyze) != EXPECTED_ANALYZE_KEYS:
        raise GitNexusConfigError("analyze must contain only indexOnly")
    if analyze["indexOnly"] is not True:
        raise GitNexusConfigError("analyze.indexOnly must be true")

    return {
        "index_only": True,
        "kind": "gitnexus-repository-config-status",
        "path": ".gitnexusrc",
        "status": "valid",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=pathlib.Path, default=pathlib.Path(".gitnexusrc"))
    arguments = parser.parse_args(argv)
    try:
        result = validate(arguments.path)
    except GitNexusConfigError as error:
        print(
            json.dumps(
                {
                    "kind": "gitnexus-repository-config-status",
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
