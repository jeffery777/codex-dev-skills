#!/usr/bin/env python3
"""Explicit local/manual/CI CLI for the default-disabled SQLite/FTS5 M1 adapter."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import memory_sqlite as adapter


class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise adapter.MemorySQLiteError("wrong-route")


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True), file=stream)


def _state(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-root", required=True, type=pathlib.Path)
    parser.add_argument("--repository-root", required=True, type=pathlib.Path)


def _authority(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("authority", type=pathlib.Path)
    parser.add_argument("mutation_candidate", type=pathlib.Path)
    parser.add_argument("eligibility_receipt", type=pathlib.Path)
    parser.add_argument("--accepted-authority-receipts", required=True, type=pathlib.Path)
    parser.add_argument("--accepted-eligibility-receipts", required=True, type=pathlib.Path)
    parser.add_argument("--trusted-time", required=True, type=pathlib.Path)
    parser.add_argument("--accepted-trusted-time-receipts", required=True, type=pathlib.Path)
    parser.add_argument("--expected-pre-state-digest")
    _state(parser)


def _args(argv: list[str]) -> argparse.Namespace:
    parser = StrictArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True, parser_class=StrictArgumentParser)
    sub.add_parser("probe")
    initialize = sub.add_parser("initialize")
    _state(initialize)
    query = sub.add_parser("query")
    query.add_argument("request", type=pathlib.Path)
    _state(query)
    execute = sub.add_parser("execute")
    _authority(execute)
    receipt = sub.add_parser("receipt")
    _authority(receipt)
    integrity = sub.add_parser("integrity")
    _state(integrity)
    qualify = sub.add_parser("qualification-receipt")
    qualify.add_argument("qualification_input", type=pathlib.Path)
    qualify.add_argument("safety_observation", type=pathlib.Path)
    qualify.add_argument("execution_evidence", type=pathlib.Path, nargs="+")
    return parser.parse_args(argv)


def _safe(args: argparse.Namespace) -> None:
    paths = [value for value in vars(args).values() if isinstance(value, pathlib.Path)]
    paths.extend(
        item
        for value in vars(args).values()
        if isinstance(value, list)
        for item in value
        if isinstance(item, pathlib.Path)
    )
    if any(".." in path.parts for path in paths):
        raise adapter.MemorySQLiteError("file-boundary")


def main(argv: list[str] | None = None) -> int:
    try:
        args = _args(list(sys.argv[1:] if argv is None else argv))
        _safe(args)
        if args.command == "probe":
            result = adapter.probe()
        elif args.command == "initialize":
            result = adapter.initialize(args.state_root, args.repository_root)
        elif args.command == "query":
            result = adapter.query(
                adapter.load_json(args.request), args.state_root, args.repository_root
            )
        elif args.command == "execute":
            result = adapter.execute_authorized_operation(
                adapter.load_json(args.authority),
                adapter.load_json(args.mutation_candidate),
                adapter.load_json(args.eligibility_receipt),
                accepted_authority_receipts=adapter.load_json(args.accepted_authority_receipts),
                accepted_eligibility_receipts=adapter.load_json(args.accepted_eligibility_receipts),
                trusted_time_value=adapter.load_json(args.trusted_time),
                accepted_trusted_time_receipts=adapter.load_json(args.accepted_trusted_time_receipts),
                expected_pre_state_digest=args.expected_pre_state_digest,
                state_root=args.state_root,
                repository_root=args.repository_root,
            )
        elif args.command == "receipt":
            result = adapter.lookup_receipt(
                adapter.load_json(args.authority),
                adapter.load_json(args.mutation_candidate),
                adapter.load_json(args.eligibility_receipt),
                accepted_authority_receipts=adapter.load_json(args.accepted_authority_receipts),
                accepted_eligibility_receipts=adapter.load_json(args.accepted_eligibility_receipts),
                trusted_time_value=adapter.load_json(args.trusted_time),
                accepted_trusted_time_receipts=adapter.load_json(args.accepted_trusted_time_receipts),
                expected_pre_state_digest=args.expected_pre_state_digest,
                state_root=args.state_root,
                repository_root=args.repository_root,
            )
        elif args.command == "integrity":
            result = adapter.integrity(args.state_root, args.repository_root)
        else:
            result = adapter.build_qualification_receipt(
                adapter.load_json(args.qualification_input),
                adapter.load_json(args.safety_observation),
                [adapter.load_json(path) for path in args.execution_evidence],
            )
        _render(result)
        return 0
    except adapter.CLI_REJECTION_ERRORS as error:
        _render({
            "status": "rejected",
            "code": getattr(error, "code", "io-error"),
            "message": "memory sqlite operation was rejected",
        }, stream=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
