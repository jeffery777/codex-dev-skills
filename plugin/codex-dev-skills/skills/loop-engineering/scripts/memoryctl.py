#!/usr/bin/env python3
"""Validate and evaluate the Loop Engineering V2b memory contract offline."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import memory_contract


def render(value: object, *, stream: object = sys.stdout) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True), file=stream)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "decide-retrieval", "decide-write", "conformance"):
        child = subparsers.add_parser(command)
        child.add_argument("document", type=pathlib.Path)
        if command == "decide-retrieval":
            child.add_argument("--trusted-conformance-receipts", type=pathlib.Path)
            child.add_argument("--trusted-source-digests", type=pathlib.Path)
        if command == "conformance":
            child.add_argument("--trusted-source-digests", type=pathlib.Path, required=True)
            child.add_argument(
                "--trusted-acceptance-receipt-digests",
                type=pathlib.Path,
                required=True,
            )
        if command == "decide-write":
            child.add_argument("--trusted-acceptance-receipt-digests", type=pathlib.Path)
    digest = subparsers.add_parser("digest")
    digest.add_argument("document", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        document = memory_contract.load_json(args.document)
        if args.command == "validate":
            result = memory_contract.validate_document(document)
        elif args.command == "decide-retrieval":
            trusted = (
                memory_contract.load_json(args.trusted_conformance_receipts)
                if args.trusted_conformance_receipts
                else {}
            )
            trusted_sources = (
                memory_contract.load_json(args.trusted_source_digests)
                if args.trusted_source_digests
                else {}
            )
            result = memory_contract.decide_retrieval(
                document,
                trusted_conformance_receipts=trusted,
                trusted_source_digests=trusted_sources,
            )
        elif args.command == "decide-write":
            trusted_acceptance = []
            if args.trusted_acceptance_receipt_digests:
                trusted_document = memory_contract.load_json(args.trusted_acceptance_receipt_digests)
                if set(trusted_document) != {"receipt_digests"}:
                    raise memory_contract.MemoryContractError(
                        "trusted acceptance input requires only receipt_digests"
                    )
                trusted_acceptance = trusted_document["receipt_digests"]
            result = memory_contract.decide_write_eligibility(
                document,
                trusted_acceptance_receipt_digests=trusted_acceptance,
            )
        elif args.command == "conformance":
            trusted_sources = memory_contract.load_json(args.trusted_source_digests)
            trusted_acceptance_document = memory_contract.load_json(
                args.trusted_acceptance_receipt_digests
            )
            if set(trusted_acceptance_document) != {"receipt_digests"}:
                raise memory_contract.MemoryContractError(
                    "trusted acceptance input requires only receipt_digests"
                )
            result = memory_contract.validate_conformance(
                document,
                trusted_source_digests=trusted_sources,
                trusted_acceptance_receipt_digests=trusted_acceptance_document[
                    "receipt_digests"
                ],
            )
        else:
            result = {
                "status": "digested",
                "canonical_sha256": memory_contract.canonical_digest(document),
            }
        render(result)
        return 1 if args.command == "conformance" and result.get("passed") is not True else 0
    except (OSError, memory_contract.MemoryContractError) as exc:
        render({"status": "rejected", "errors": [str(exc)]}, stream=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
