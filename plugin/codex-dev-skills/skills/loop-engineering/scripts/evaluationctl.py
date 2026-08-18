#!/usr/bin/env python3
"""Bounded stdout-only CLI for V3-B isolated candidate evaluation."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

import candidate_evaluation as evaluation


class StrictArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        del message
        raise evaluation.CandidateEvaluationError(
            "wrong-route",
            "candidate evaluation command or arguments are unsupported",
        )


def _render(value: object, *, stream: object = sys.stdout) -> None:
    print(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        file=stream,
    )


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--proposal-set", required=True, type=pathlib.Path)
    parser.add_argument("--record", action="append", required=True, type=pathlib.Path)
    parser.add_argument("--evidence", action="append", required=True, type=pathlib.Path)
    parser.add_argument("--memory-decision", type=pathlib.Path)
    parser.add_argument("--trusted-conformance-receipts", type=pathlib.Path)
    parser.add_argument("--trusted-source-digests", type=pathlib.Path)


def _args(argv: list[str]) -> argparse.Namespace:
    parser = StrictArgumentParser(
        description="Evaluate, replay-verify, and packetize isolated V3-B candidates."
    )
    subparsers = parser.add_subparsers(
        dest="command", required=True, parser_class=StrictArgumentParser
    )
    evaluate = subparsers.add_parser("evaluate")
    evaluate.add_argument("evaluation_input", type=pathlib.Path)
    _common(evaluate)
    verify = subparsers.add_parser("verify")
    verify.add_argument("evaluation_result", type=pathlib.Path)
    verify.add_argument("evaluation_input", type=pathlib.Path)
    _common(verify)
    packet = subparsers.add_parser("packet")
    packet.add_argument("evaluation_result", type=pathlib.Path)
    packet.add_argument("verification_result", type=pathlib.Path)
    packet.add_argument("evaluation_input", type=pathlib.Path)
    _common(packet)
    validate = subparsers.add_parser("validate-packet")
    validate.add_argument("promotion_packet", type=pathlib.Path)
    validate.add_argument("evaluation_result", type=pathlib.Path)
    validate.add_argument("verification_result", type=pathlib.Path)
    validate.add_argument("evaluation_input", type=pathlib.Path)
    _common(validate)
    return parser.parse_args(argv)


def _safe_paths(paths: list[pathlib.Path]) -> None:
    if any(".." in path.parts for path in paths):
        raise evaluation.CandidateEvaluationError(
            "file-boundary", "input path must not traverse a parent directory"
        )


def _load_many(
    paths: list[pathlib.Path], *, limit: int, code: str, message: str
) -> list[dict[str, object]]:
    if not paths or len(paths) > limit:
        raise evaluation.CandidateEvaluationError(code, message)
    _safe_paths(paths)
    return [evaluation.load_json(path) for path in paths]


def _load_optional(path: pathlib.Path | None) -> Any | None:
    if path is None:
        return None
    _safe_paths([path])
    return evaluation.load_json(path)


def main(argv: list[str] | None = None) -> int:
    try:
        args = _args(list(sys.argv[1:] if argv is None else argv))
        all_paths = [args.proposal_set, args.evaluation_input, *args.record, *args.evidence]
        for name in (
            "evaluation_result", "verification_result", "promotion_packet",
            "memory_decision", "trusted_conformance_receipts", "trusted_source_digests",
        ):
            value = getattr(args, name, None)
            if value is not None:
                all_paths.append(value)
        _safe_paths(all_paths)
        proposal_set = evaluation.load_json(args.proposal_set)
        evaluation_input = evaluation.load_json(args.evaluation_input)
        records = _load_many(
            args.record,
            limit=evaluation.proposal.lineage.MAX_RECORDS,
            code="record-count",
            message="candidate evaluation source has an unsupported record count",
        )
        evidence = _load_many(
            args.evidence,
            limit=evaluation.oe.MAX_SET_DOCUMENTS,
            code="document-count",
            message="candidate evaluation evidence exceeds the document count bound",
        )
        context = {
            "memory_decision_input": _load_optional(args.memory_decision),
            "trusted_conformance_receipts": _load_optional(args.trusted_conformance_receipts),
            "trusted_source_digests": _load_optional(args.trusted_source_digests),
        }
        if args.command == "evaluate":
            _render(
                evaluation.build_evaluation_result(
                    evaluation_input, proposal_set, records, evidence, **context
                )
            )
            return 0
        evaluation_result = evaluation.load_json(args.evaluation_result)
        if args.command == "verify":
            _render(
                evaluation.verify_evaluation_result(
                    evaluation_result, evaluation_input, proposal_set, records, evidence,
                    **context,
                )
            )
            return 0
        verification_result = evaluation.load_json(args.verification_result)
        if args.command == "packet":
            _render(
                evaluation.build_promotion_packet(
                    evaluation_result, verification_result, evaluation_input,
                    proposal_set, records, evidence, **context,
                )
            )
            return 0
        promotion_packet = evaluation.load_json(args.promotion_packet)
        validated = evaluation.validate_promotion_packet(
            promotion_packet, evaluation_result, verification_result,
            evaluation_input, proposal_set, records, evidence, **context,
        )
        _render(
            {
                "status": "valid",
                "contract_version": evaluation.CONTRACT_VERSION,
                "kind": evaluation.PACKET_KIND,
                "packet_id": validated["packet_id"],
                "promotion_packet_digest": validated["promotion_packet_digest"],
                "packet_only_invariants": evaluation.packet_only_invariants(),
                "authority_invariants": evaluation.authority_invariants(),
            }
        )
        return 0
    except (OSError, evaluation.CandidateEvaluationError) as error:
        _render(
            {
                "status": "rejected",
                "code": getattr(error, "code", "io-error"),
                "message": getattr(error, "message", "input could not be read"),
            },
            stream=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
