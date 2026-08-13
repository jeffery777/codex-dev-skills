#!/usr/bin/env python3
"""Offline CLI for paired Memory M0 safety/conformance qualification."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import memory_qualification as qualification


class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise qualification.MemoryQualificationError("wrong-route", "memory qualification command is unsupported")


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True), file=stream)


def _args(argv: list[str]) -> argparse.Namespace:
    parser = StrictArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=StrictArgumentParser)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("qualification_input", type=pathlib.Path)
    evaluate.add_argument("off_result", type=pathlib.Path)
    evaluate.add_argument("off_verification", type=pathlib.Path)
    evaluate.add_argument("--accepted-v3b-receipts", required=True, type=pathlib.Path)
    evaluate.add_argument("--on-result", type=pathlib.Path)
    evaluate.add_argument("--on-verification", type=pathlib.Path)
    evaluate.add_argument("--m1-qualification-receipt", type=pathlib.Path)
    evaluate.add_argument("--accepted-m1-qualification-receipts", type=pathlib.Path)
    validate = sub.add_parser("validate-result")
    validate.add_argument("qualification_result", type=pathlib.Path)
    validate.add_argument("qualification_input", type=pathlib.Path)
    validate.add_argument("off_result", type=pathlib.Path)
    validate.add_argument("off_verification", type=pathlib.Path)
    validate.add_argument("--accepted-v3b-receipts", required=True, type=pathlib.Path)
    validate.add_argument("--on-result", type=pathlib.Path)
    validate.add_argument("--on-verification", type=pathlib.Path)
    validate.add_argument("--m1-qualification-receipt", type=pathlib.Path)
    validate.add_argument("--accepted-m1-qualification-receipts", type=pathlib.Path)
    return parser.parse_args(argv)


def _safe(paths: list[pathlib.Path]) -> None:
    if any(".." in path.parts for path in paths):
        raise qualification.MemoryQualificationError("file-boundary", "input path must not traverse a parent directory")


def main(argv: list[str] | None = None) -> int:
    try:
        args = _args(list(sys.argv[1:] if argv is None else argv))
        paths = [value for value in vars(args).values() if isinstance(value, pathlib.Path)]
        _safe(paths)
        source = qualification.load_json(args.qualification_input)
        if args.command == "evaluate":
            result = qualification.build_qualification_result(
                source,
                qualification.load_json(args.off_result),
                qualification.load_json(args.off_verification),
                accepted_v3b_receipts=qualification.load_json(args.accepted_v3b_receipts),
                on_result_value=(qualification.load_json(args.on_result) if args.on_result else None),
                on_verification_value=(qualification.load_json(args.on_verification) if args.on_verification else None),
                m1_qualification_receipt_value=(
                    qualification.load_json(args.m1_qualification_receipt)
                    if args.m1_qualification_receipt else None
                ),
                accepted_m1_qualification_receipts=(
                    qualification.load_json(args.accepted_m1_qualification_receipts)
                    if args.accepted_m1_qualification_receipts else None
                ),
            )
            _render(result)
            return 0
        result = qualification.validate_qualification_result(
            qualification.load_json(args.qualification_result), source,
            qualification.load_json(args.off_result),
            qualification.load_json(args.off_verification),
            accepted_v3b_receipts=qualification.load_json(args.accepted_v3b_receipts),
            on_result_value=(qualification.load_json(args.on_result) if args.on_result else None),
            on_verification_value=(qualification.load_json(args.on_verification) if args.on_verification else None),
            m1_qualification_receipt_value=(
                qualification.load_json(args.m1_qualification_receipt)
                if args.m1_qualification_receipt else None
            ),
            accepted_m1_qualification_receipts=(
                qualification.load_json(args.accepted_m1_qualification_receipts)
                if args.accepted_m1_qualification_receipts else None
            ),
        )
        _render({
            "status": "valid", "contract_version": qualification.CONTRACT_VERSION,
            "kind": qualification.RESULT_KIND, "qualification_id": result["qualification_id"],
            "qualification_result_digest": result["qualification_result_digest"],
            "qualification_status": result["status"],
            "authority_invariants": qualification.authority_invariants(),
        })
        return 0
    except (OSError, qualification.MemoryQualificationError) as error:
        _render({
            "status": "rejected", "code": getattr(error, "code", "io-error"),
            "message": getattr(error, "message", "input could not be read"),
        }, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
