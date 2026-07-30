#!/usr/bin/env python3
"""Bounded offline CLI for V2d-B lineage and projection contracts."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import improvement_lineage as lineage


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        file=stream,
    )


def _args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate V2d-B improvement lineage and deterministic projections."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_record = subparsers.add_parser("validate-record")
    validate_record.add_argument("record", type=pathlib.Path)
    validate_record.add_argument(
        "--evidence", nargs="+", required=True, type=pathlib.Path
    )

    for command in ("validate-set", "project-human", "project-graph"):
        item = subparsers.add_parser(command)
        item.add_argument("records", nargs="+", type=pathlib.Path)
        item.add_argument("--evidence", nargs="+", required=True, type=pathlib.Path)

    validate_projection = subparsers.add_parser("validate-projection")
    validate_projection.add_argument("manifest", type=pathlib.Path)
    validate_projection.add_argument("records", nargs="+", type=pathlib.Path)
    validate_projection.add_argument(
        "--evidence", nargs="+", required=True, type=pathlib.Path
    )
    return parser.parse_args(argv)


def _load(
    paths: list[pathlib.Path],
    *,
    limit: int,
    code: str,
    message: str,
) -> list[dict[str, object]]:
    if not paths or len(paths) > limit:
        raise lineage.ImprovementContractError(code, message)
    return [lineage.load_json(path) for path in paths]


def main(argv: list[str] | None = None) -> int:
    args = _args(list(sys.argv[1:] if argv is None else argv))
    try:
        evidence = _load(
            args.evidence,
            limit=lineage.oe.MAX_SET_DOCUMENTS,
            code="document-count",
            message="evidence input exceeds the document count bound",
        )
        if args.command == "validate-record":
            record = lineage.load_json(args.record)
            validated = lineage.validate_record(record, evidence)
            _render(
                {
                    "status": "valid",
                    "contract_version": lineage.LINEAGE_CONTRACT_VERSION,
                    "record_id": validated["record_id"],
                    "improvement_id": validated["improvement_id"],
                    "record_digest": validated["record_digest"],
                    "authority_invariants": lineage.oe.authority_invariants(),
                }
            )
            return 0
        records = _load(
            args.records,
            limit=lineage.MAX_RECORDS,
            code="record-count",
            message="lineage set has an unsupported record count",
        )
        if args.command == "validate-set":
            result = lineage.validate_lineage(records, evidence)
            result.pop("ordered_records", None)
            result.pop("lineage_depths", None)
            _render(result)
            return 0
        if args.command == "project-human":
            _render(lineage.build_human_projection(records, evidence))
            return 0
        if args.command == "project-graph":
            _render(lineage.build_graph_projection(records, evidence))
            return 0
        manifest = lineage.load_json(args.manifest)
        validated = lineage.validate_projection(manifest, records, evidence)
        _render(
            {
                "status": "valid",
                "contract_version": lineage.PROJECTION_CONTRACT_VERSION,
                "kind": validated["kind"],
                "projection_id": validated["projection_id"],
                "projection_digest": validated["projection_digest"],
                "authority_invariants": lineage.oe.authority_invariants(),
            }
        )
        return 0
    except (OSError, lineage.ImprovementContractError) as error:
        code = getattr(error, "code", "io-error")
        message = getattr(error, "message", "input could not be read")
        _render(
            {"status": "rejected", "code": code, "message": message},
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
