#!/usr/bin/env python3
"""顯式合成檔案的離線 MG1 G0 checker；結果不提供授權。"""

import argparse
import json
import sys

from memory_governance_g0 import ContractError, read_json, validate_case


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", help="合成 case JSON regular file")
    parser.add_argument("--context", help="獨立的合成 caller context JSON")
    args = parser.parse_args()
    try:
        case = read_json(args.case)
        # off 不讀取、不探測 --context；case 檔是顯式測試輸入，不是記憶儲存。
        ctx = None if case.get("mode") == "off" else read_json(args.context) if args.context else None
        result = validate_case(case, ctx)
    except ContractError as exc:
        print(json.dumps({"status": "rejected", "code": str(exc), "operation_authorized": False}), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
