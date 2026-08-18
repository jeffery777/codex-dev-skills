#!/usr/bin/env python3
"""Offline CLI for provider-neutral Memory M0 operation contracts."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import memory_operation as operation


class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise operation.MemoryOperationError("wrong-route", "memory operation command is unsupported")


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True), file=stream)


def _args(argv: list[str]) -> argparse.Namespace:
    parser = StrictArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=StrictArgumentParser)
    validate = sub.add_parser("validate")
    validate.add_argument("document", type=pathlib.Path)
    request = sub.add_parser("validate-request")
    request.add_argument("authorized_request", type=pathlib.Path)
    authorize = sub.add_parser("authorize")
    authorize.add_argument("authority", type=pathlib.Path)
    authorize.add_argument("mutation_candidate", type=pathlib.Path)
    authorize.add_argument("eligibility_receipt", type=pathlib.Path)
    authorize.add_argument("--accepted-authority-receipts", required=True, type=pathlib.Path)
    authorize.add_argument("--accepted-eligibility-receipts", required=True, type=pathlib.Path)
    authorize.add_argument("--trusted-time", required=True, type=pathlib.Path)
    authorize.add_argument("--accepted-trusted-time-receipts", required=True, type=pathlib.Path)
    authorize.add_argument("--expected-pre-state-digest")
    receipt = sub.add_parser("validate-receipt")
    receipt.add_argument("receipt", type=pathlib.Path)
    receipt.add_argument("authorized_request", type=pathlib.Path)
    receipt.add_argument("--original-applied-receipt", type=pathlib.Path)
    for command in (request, receipt):
        command.add_argument("--authority", required=True, type=pathlib.Path)
        command.add_argument("--mutation-candidate", required=True, type=pathlib.Path)
        command.add_argument("--eligibility-receipt", required=True, type=pathlib.Path)
        command.add_argument("--accepted-authority-receipts", required=True, type=pathlib.Path)
        command.add_argument("--accepted-eligibility-receipts", required=True, type=pathlib.Path)
        command.add_argument("--trusted-time", required=True, type=pathlib.Path)
        command.add_argument("--accepted-trusted-time-receipts", required=True, type=pathlib.Path)
        command.add_argument("--expected-pre-state-digest")
    return parser.parse_args(argv)


def _safe(paths: list[pathlib.Path]) -> None:
    if any(".." in path.parts for path in paths):
        raise operation.MemoryOperationError("file-boundary", "input path must not traverse a parent directory")


def main(argv: list[str] | None = None) -> int:
    try:
        args = _args(list(sys.argv[1:] if argv is None else argv))
        paths = [value for value in vars(args).values() if isinstance(value, pathlib.Path)]
        _safe(paths)
        if args.command == "validate":
            document = operation.load_json(args.document)
            kind = document.get("kind")
            if kind == operation.AUTHORITY_KIND:
                result = operation.validate_operation_authority(document)
            else:
                raise operation.MemoryOperationError("caller-context-required", "request and receipt validation require caller-owned evidence")
            _render({
                "status": "valid", "contract_version": operation.CONTRACT_VERSION,
                "kind": result["kind"], "document_id": result["document_id"],
                "document_digest": result["document_digest"],
                "authority_invariants": operation.authority_invariants(),
            })
            return 0
        if args.command == "authorize":
            result = operation.build_authorized_request(
                operation.load_json(args.authority),
                operation.load_json(args.mutation_candidate),
                operation.load_json(args.eligibility_receipt),
                accepted_authority_receipts=operation.load_json(args.accepted_authority_receipts),
                accepted_eligibility_receipts=operation.load_json(args.accepted_eligibility_receipts),
                trusted_time_value=operation.load_json(args.trusted_time),
                accepted_trusted_time_receipts=operation.load_json(args.accepted_trusted_time_receipts),
                expected_pre_state_digest=args.expected_pre_state_digest,
            )
            _render(result)
            return 0
        context = {
            "authority_value": operation.load_json(args.authority),
            "mutation_candidate_value": operation.load_json(args.mutation_candidate),
            "eligibility_receipt_value": operation.load_json(args.eligibility_receipt),
            "accepted_authority_receipts": operation.load_json(args.accepted_authority_receipts),
            "accepted_eligibility_receipts": operation.load_json(args.accepted_eligibility_receipts),
            "trusted_time_value": operation.load_json(args.trusted_time),
            "accepted_trusted_time_receipts": operation.load_json(args.accepted_trusted_time_receipts),
            "expected_pre_state_digest": args.expected_pre_state_digest,
        }
        if args.command == "validate-request":
            result = operation.validate_authorized_request(
                operation.load_json(args.authorized_request), **context,
            )
            _render({
                "status": "valid", "contract_version": operation.CONTRACT_VERSION,
                "kind": result["kind"], "document_id": result["document_id"],
                "document_digest": result["document_digest"],
                "authority_invariants": operation.authority_invariants(),
            })
            return 0
        original = (
            operation.load_json(args.original_applied_receipt)
            if args.original_applied_receipt is not None else None
        )
        result = operation.validate_execution_receipt(
            operation.load_json(args.receipt),
            operation.load_json(args.authorized_request),
            **context,
            original_applied_receipt=original,
        )
        _render({
            "status": "valid", "contract_version": operation.CONTRACT_VERSION,
            "kind": operation.RECEIPT_KIND, "document_id": result["document_id"],
            "document_digest": result["document_digest"],
            "outcome": result["payload"]["outcome"],
            "authority_invariants": operation.authority_invariants(),
        })
        return 0
    except (OSError, operation.MemoryOperationError) as error:
        _render({
            "status": "rejected",
            "code": getattr(error, "code", "io-error"),
            "message": getattr(error, "message", "input could not be read"),
        }, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
