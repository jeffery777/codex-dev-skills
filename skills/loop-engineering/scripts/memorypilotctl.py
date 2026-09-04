#!/usr/bin/env python3
"""Explicit, local Memory M1 pilot control surface (no automatic operation)."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import memory_pilot_off


def _root(value: str) -> pathlib.Path:
    path = pathlib.Path(value)
    if not path.is_absolute():
        raise ValueError("root must be absolute")
    return path


def _mutation(memory_pilot: object, command: str, bundle: dict, state: pathlib.Path, repository: pathlib.Path) -> dict:
    required = {
        "envelope", "authority", "candidate", "eligibility",
        "accepted_authority_receipts", "accepted_eligibility_receipts", "trusted_time",
        "accepted_trusted_time_receipts", "expected_pre_state_digest",
    }
    if set(bundle) != required:
        raise ValueError("invalid bundle")
    operation = getattr(memory_pilot, command)
    return operation(
        bundle["envelope"], bundle["authority"], bundle["candidate"], bundle["eligibility"],
        accepted_authority_receipts=bundle["accepted_authority_receipts"],
        accepted_eligibility_receipts=bundle["accepted_eligibility_receipts"],
        trusted_time=bundle["trusted_time"],
        accepted_trusted_time_receipts=bundle["accepted_trusted_time_receipts"],
        expected_pre_state_digest=bundle["expected_pre_state_digest"],
        state_root=state, repository_root=repository,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("off")
    check = sub.add_parser("validate-envelope")
    check.add_argument("action", choices=("remember", "recall", "invalidate"))
    check.add_argument("envelope", type=pathlib.Path)
    for command in ("remember", "recall", "invalidate"):
        child = sub.add_parser(command)
        child.add_argument("bundle", type=pathlib.Path)
        child.add_argument("--state-root", required=True)
        child.add_argument("--repository-root", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "off":
            result = memory_pilot_off.no_memory()
        else:
            # Keep the default-off CLI route free of the M1 adapter import.
            import memory_pilot
            if args.command == "validate-envelope":
                result = memory_pilot.validate_envelope(memory_pilot.load_json(args.envelope), action=args.action)
            else:
                bundle = memory_pilot.load_json(args.bundle)
                state = _root(args.state_root)
                repository = _root(args.repository_root)
                if args.command == "recall":
                    required = {
                        "envelope", "query_request", "retrieval_context",
                        "trusted_conformance_receipts", "trusted_source_digests",
                    }
                    if set(bundle) != required:
                        raise ValueError("invalid bundle")
                    result = memory_pilot.recall(
                        bundle["envelope"], bundle["query_request"], bundle["retrieval_context"],
                        trusted_conformance_receipts=bundle["trusted_conformance_receipts"],
                        trusted_source_digests=bundle["trusted_source_digests"],
                        state_root=state, repository_root=repository,
                    )
                else:
                    result = _mutation(memory_pilot, args.command, bundle, state, repository)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError):
        print('{"status":"rejected"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
