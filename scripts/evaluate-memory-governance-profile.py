#!/usr/bin/env python3
"""計算明確合成 G0 profile 提案；不量測儲存、不接受參數、不授權操作。"""

import argparse
import json
import sys

from memory_governance_g0 import ContractError, fields, identifier, integer, read_json, require


VERSION = "mg1-production-profile-proposal/v0"
PROFILE_FIELDS = {
    "max_items", "max_versions", "history_seconds", "max_payload_bytes", "max_proofs",
    "maintenance_proof_reserve", "proof_seconds", "marker_seconds", "confirmation_seconds",
    "max_scan_items", "data_limit_bytes", "maintenance_max_bytes",
}
MODEL_FIELDS = {
    "kind", "journal_copies", "temp_bytes", "growth_bytes", "warning_percent", "index_kind",
    "proof_bytes_ceiling", "witness_bytes_ceiling", "item_metadata_bytes_ceiling", "other_overhead_bytes",
}
WORKLOAD_FIELDS = {
    "case_id", "active_items", "stopped_items", "erased_markers", "versions_per_item",
    "version_bytes", "index_bytes_per_active_item", "proof_count", "witness_count",
}


def evaluate(value: object) -> dict:
    """純算術估算；只接受 proposed 合成文件，結果不是 production conformance。"""
    value = fields(value, {"contract_version", "profile_id", "status", "profile", "model", "workloads"})
    require(value["contract_version"] == VERSION, "unsupported-proposal")
    identifier(value["profile_id"])
    require(value["status"] == "proposed", "proposal-status-required")
    profile = fields(value["profile"], PROFILE_FIELDS)
    for number in profile.values():
        integer(number, 1)
    require(profile["data_limit_bytes"] % 4096 == 0, "invalid-page-alignment")
    require(profile["confirmation_seconds"] <= profile["proof_seconds"], "invalid-window")
    require(profile["max_scan_items"] <= profile["max_items"], "invalid-scan-limit")
    require(profile["max_payload_bytes"] <= profile["data_limit_bytes"], "invalid-payload-limit")
    model = fields(value["model"], MODEL_FIELDS)
    require(model["kind"] == "synthetic-planning-estimate", "synthetic-model-required")
    require(model["index_kind"] == "ordinary-current-only-projection", "unsupported-index-model")
    for key in MODEL_FIELDS - {"kind", "index_kind"}:
        integer(model[key], 1)
    require(model["warning_percent"] < 100, "invalid-warning-percent")
    steady_limit = profile["data_limit_bytes"]
    workloads = value["workloads"]
    require(type(workloads) is list and 1 <= len(workloads) <= 16, "invalid-workloads")
    result = []
    seen = set()
    for raw in workloads:
        case = fields(raw, WORKLOAD_FIELDS)
        identifier(case["case_id"])
        require(case["case_id"] not in seen, "duplicate-case")
        seen.add(case["case_id"])
        for key in WORKLOAD_FIELDS - {"case_id"}:
            integer(case[key], 0)
        retained_items = case["active_items"] + case["stopped_items"]
        all_items = retained_items + case["erased_markers"]
        require(all_items <= profile["max_items"], "item-count-limit")
        require(1 <= case["versions_per_item"] <= profile["max_versions"], "version-count-limit")
        require(1 <= case["version_bytes"] <= profile["max_payload_bytes"], "payload-limit")
        require(case["proof_count"] <= profile["max_proofs"] + profile["maintenance_proof_reserve"],
                "proof-count-limit")
        require(case["witness_count"] <= min(case["proof_count"], profile["maintenance_proof_reserve"]),
                "witness-count-limit")
        parts = {
            "retained_version_bytes": retained_items * case["versions_per_item"] * case["version_bytes"],
            "current_index_bytes": case["active_items"] * case["index_bytes_per_active_item"],
            "proof_bytes": case["proof_count"] * model["proof_bytes_ceiling"],
            "witness_bytes": case["witness_count"] * model["witness_bytes_ceiling"],
            "item_metadata_bytes": all_items * model["item_metadata_bytes_ceiling"],
            "other_overhead_bytes": model["other_overhead_bytes"],
        }
        estimated = sum(parts.values())
        work_parts = {
            "journal_bytes": estimated * model["journal_copies"],
            "temp_bytes": model["temp_bytes"],
            "growth_bytes": model["growth_bytes"],
        }
        work_total = integer(sum(work_parts.values()))
        work_pages = work_total // 4096 + (1 if work_total % 4096 else 0)
        required_work = work_pages * 4096
        peak = estimated + required_work
        for number in (*parts.values(), *work_parts.values(), estimated, required_work, peak):
            integer(number)
        # 精確整數比較；不將檔案估算當實測，也不執行任何清除。
        result.append({
            "case_id": case["case_id"],
            "estimated_parts": parts,
            "estimated_steady_bytes": estimated,
            "estimated_peak_bytes": peak,
            "estimated_work_parts": work_parts,
            "estimated_required_work_bytes": required_work,
            "within_steady_model": estimated <= steady_limit,
            "within_growth_model": estimated + model["growth_bytes"] <= steady_limit,
            "within_work_model": required_work <= profile["maintenance_max_bytes"],
            "warning_in_model": estimated * 100 >= steady_limit * model["warning_percent"],
            "uses_maintenance_proof_slots": case["proof_count"] > profile["max_proofs"],
        })
    return {
        "contract_version": VERSION,
        "profile_id": value["profile_id"],
        "model_kind": model["kind"],
        "steady_limit_bytes": steady_limit,
        "maintenance_max_bytes": profile["maintenance_max_bytes"],
        "max_audit_pages": (profile["max_items"] + profile["max_scan_items"] - 1) // profile["max_scan_items"],
        "workloads": result,
        "production_parameters_accepted": False,
        "runtime_proven": False,
        "operation_authorized": False,
        "write_performed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", help="明確的合成 profile 提案 JSON regular file")
    args = parser.parse_args()
    try:
        result = evaluate(read_json(args.proposal))
    except ContractError as error:
        print(json.dumps({"status": "rejected", "code": str(error), "operation_authorized": False}),
              file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
