#!/usr/bin/env python3
"""MG1 G1 有界人工／CI 入口；production adapter 未取得資格時明確不可用。"""
from __future__ import annotations

import argparse
import json
import sys

import memory_governance_contract as contract
from memory_audit import audit_report, render_report
from memory_governance_storage import SCHEMA_FINGERPRINT


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="MG1 G1 default-off governance boundary")
    parser.add_argument("command", choices=("status", "audit", "proposal"), nargs="?", default="status")
    parser.add_argument("--enabled", action="store_true")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    if args.command == "audit":
        report = audit_report(enabled=args.enabled)
        if args.format == "text":
            print(render_report(report), end="")
        else:
            print(contract.canonical(report).decode("utf-8"))
        return 0 if report["status"] in {"complete", "disabled"} else 2
    result = {"operation_authorized": False, "runtime_proven": False, "write_performed": False}
    if not args.enabled:
        result["status"] = "disabled"
    elif args.command == "status":
        result["status"] = "adapter-unavailable"
    else:
        try:
            if args.command == "proposal":
                # 只讀明確 stdin；與可執行 mg1-preview/v1 分開，不讀取任何 root。
                value = contract.decode(sys.stdin.buffer.read(contract.MAX_ENVELOPE + 1))
                contract.fields(value, {"scope", "profile", "candidate"})
                limits = contract.profile(value["profile"])
                scope = contract.scope(value["scope"], contract.digest(limits), contract.digest(contract.POLICY))
                contract.require(scope["schema_fingerprint"] == SCHEMA_FINGERPRINT, "schema-mismatch")
                contract.validate_version(value["candidate"], scope, limits, candidate=True)
                result.update(status="proposal-only", schema_consistent=True,
                              source_verification="unavailable", sensitivity_verification="unavailable")
        except contract.ContractError as exc:
            result.update(status="unavailable", reason=str(exc))
            print(json.dumps(result, sort_keys=True))
            return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
