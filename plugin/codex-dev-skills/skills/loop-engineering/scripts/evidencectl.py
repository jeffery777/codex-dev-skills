#!/usr/bin/env python3
"""Validate Loop Engineering Operational Evidence V0 documents offline."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import operational_evidence as evidence


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True),
        file=stream,
    )


def _args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("document", type=pathlib.Path)
    validate_set = subparsers.add_parser("validate-set")
    validate_set.add_argument("documents", nargs="+", type=pathlib.Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _args(sys.argv[1:] if argv is None else argv)
    try:
        if args.command == "validate":
            document = evidence.validate_document(evidence.load_json(args.document))
            result = {
                "status": "valid",
                "contract_version": document["contract_version"],
                "kind": document["kind"],
                "document_id": document["document_id"],
                "document_digest": document["document_digest"],
                "authority_invariants": evidence.authority_invariants(),
            }
        else:
            result = evidence.validate_set(
                evidence.load_json(path) for path in args.documents
            )
        _render(result)
        return 0
    except evidence.OperationalEvidenceError as exc:
        _render(
            {"status": "rejected", "code": exc.code, "message": exc.message},
            stream=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
