#!/usr/bin/env python3
"""Evaluate context continuity decisions and end-to-end cost/quality evidence."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals" / "context-continuity" / "suite.json"
MODULE = ROOT / "skills" / "loop-engineering" / "scripts" / "context_continuity.py"


class EvalError(ValueError):
    pass


def _load_module():
    spec = importlib.util.spec_from_file_location("context_continuity_for_eval", MODULE)
    if spec is None or spec.loader is None:
        raise EvalError("context continuity production module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _merge(target: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def evaluate(suite_path: pathlib.Path = DEFAULT_SUITE) -> dict[str, Any]:
    try:
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError("suite must be valid UTF-8 JSON") from exc
    if not isinstance(suite, dict) or suite.get("contract_version") != "loop-context-continuity-eval/v1":
        raise EvalError("unsupported eval contract")
    provenance = suite.get("measurement_provenance")
    if not isinstance(provenance, dict) or provenance.get("release_evidence_qualified") is not False:
        raise EvalError("synthetic provenance must remain unqualified for release evidence")
    for field in (
        "evidence_kind",
        "paired_objective_id",
        "measurement_method",
        "quality_rubric",
        "raw_results_location",
    ):
        if not isinstance(provenance.get(field), str) or not provenance[field].strip():
            raise EvalError(f"measurement_provenance.{field} must be a non-empty string")
    baseline = suite.get("baseline")
    cases = suite.get("cases")
    if not isinstance(baseline, dict) or not isinstance(cases, list) or not cases:
        raise EvalError("suite requires a baseline and non-empty cases")
    module = _load_module()
    results = []
    ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", "overrides", "expect"}:
            raise EvalError("each case requires only id, overrides, and expect")
        case_id = case["id"]
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise EvalError("case ids must be unique non-empty strings")
        ids.add(case_id)
        if not isinstance(case["overrides"], dict) or not isinstance(case["expect"], dict):
            raise EvalError("case overrides and expect must be objects")
        value = copy.deepcopy(baseline)
        value["assessment_id"] = case_id
        _merge(value, case["overrides"])
        result = module.assess(value)
        actual = {
            "decision": result["decision"],
            "comparison_qualified": result["comparison"]["qualified"],
            "runtime_action_performed": result["runtime_action_performed"],
            "task_created": result["task_created"],
        }
        passed = all(actual.get(key) == expected for key, expected in case["expect"].items())
        if actual["runtime_action_performed"] or actual["task_created"]:
            passed = False
        results.append({"id": case_id, "status": "passed" if passed else "failed", "actual": actual})
    successful = sum(item["status"] == "passed" for item in results)
    baseline_result = module.assess(copy.deepcopy(baseline))
    same = baseline_result["comparison"]["same_context"]
    fresh = baseline_result["comparison"]["fresh_rollover"]
    return {
        "contract_version": suite["contract_version"],
        "status": "passed" if successful == len(results) else "failed",
        "measurement_provenance": provenance,
        "release_evidence_qualified": False,
        "metrics": {
            "total_cases": len(results),
            "task_success_rate": successful / len(results),
            "same_context_objective_total_tokens": same["objective_total_tokens"],
            "fresh_rollover_objective_total_tokens_including_bootstrap": fresh["objective_total_tokens"],
            "fresh_rollover_handoff_bootstrap_tokens": fresh["handoff_bootstrap_tokens"],
            "same_context_quality_score": same["quality_score"],
            "fresh_rollover_quality_score": fresh["quality_score"],
            "same_context_wall_time_seconds": same["wall_time_seconds"],
            "fresh_rollover_wall_time_seconds": fresh["wall_time_seconds"],
            "same_context_repeated_reads": same["repeated_reads"],
            "fresh_rollover_repeated_reads": fresh["repeated_reads"],
            "same_context_review_fix_rounds": same["review_fix_rounds"],
            "fresh_rollover_review_fix_rounds": fresh["review_fix_rounds"],
            "same_context_stale_context_errors": same["stale_context_errors"],
            "fresh_rollover_stale_context_errors": fresh["stale_context_errors"],
            "same_context_blockers": same["blockers"],
            "fresh_rollover_blockers": fresh["blockers"],
            "comparison_qualified": baseline_result["comparison"]["qualified"],
        },
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=pathlib.Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.suite)
    except EvalError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        sys.stdout.write(rendered)
    else:
        args.output.write_text(rendered, encoding="utf-8")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
