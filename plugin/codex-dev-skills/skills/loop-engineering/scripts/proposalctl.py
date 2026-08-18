#!/usr/bin/env python3
"""Bounded stdout-only CLI for V3-A evidence-to-proposal contracts."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import improvement_proposal as proposal


class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise proposal.ProposalContractError(
            "wrong-route",
            "proposal command or arguments are unsupported",
        )


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        file=stream,
    )


def _args(argv: list[str]) -> argparse.Namespace:
    parser = StrictArgumentParser(
        description="Generate or validate deterministic proposal-only V3-A manifests."
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=StrictArgumentParser,
    )
    generate = subparsers.add_parser("generate")
    generate.add_argument("--record", action="append", required=True, type=pathlib.Path)
    generate.add_argument("--evidence", action="append", required=True, type=pathlib.Path)

    validate = subparsers.add_parser("validate")
    validate.add_argument("proposal_set", type=pathlib.Path)
    validate.add_argument("--record", action="append", required=True, type=pathlib.Path)
    validate.add_argument("--evidence", action="append", required=True, type=pathlib.Path)
    return parser.parse_args(argv)


def _load(
    paths: list[pathlib.Path],
    *,
    limit: int,
    code: str,
    message: str,
) -> list[dict[str, object]]:
    if not paths or len(paths) > limit:
        raise proposal.ProposalContractError(code, message)
    if any(".." in path.parts for path in paths):
        raise proposal.ProposalContractError(
            "file-boundary",
            "input path must not traverse a parent directory",
        )
    return [proposal.load_json(path) for path in paths]


def main(argv: list[str] | None = None) -> int:
    try:
        args = _args(list(sys.argv[1:] if argv is None else argv))
        records = _load(
            args.record,
            limit=proposal.lineage.MAX_RECORDS,
            code="record-count",
            message="proposal source has an unsupported record count",
        )
        evidence = _load(
            args.evidence,
            limit=proposal.oe.MAX_SET_DOCUMENTS,
            code="document-count",
            message="proposal evidence exceeds the document count bound",
        )
        if args.command == "generate":
            _render(proposal.build_proposal_set(records, evidence))
            return 0
        manifest = proposal.load_json(args.proposal_set)
        validated = proposal.validate_proposal_set(manifest, records, evidence)
        _render(
            {
                "status": "valid",
                "contract_version": proposal.CONTRACT_VERSION,
                "kind": proposal.KIND,
                "proposal_set_id": validated["proposal_set_id"],
                "proposal_set_digest": validated["proposal_set_digest"],
                "authority_invariants": proposal.oe.authority_invariants(),
            }
        )
        return 0
    except (OSError, proposal.ProposalContractError) as error:
        code = getattr(error, "code", "io-error")
        message = getattr(error, "message", "input could not be read")
        _render(
            {"status": "rejected", "code": code, "message": message},
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
