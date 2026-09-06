# Issue #222：原始註記與現行來源分析

2026-09-06 於 #225 執行有界追溯。來源為
[PR #210 owner receipt](https://github.com/jeffery777/codex-dev-skills/pull/210#issuecomment-5534705615)、
原 head `7b7442e4d7fb988b38b7f4b37ad3a86d3e7cf649` 與目前基準
`4524e2b4c7076c2c8afdbaaeab1cfd01379665e5`。

## 已證實與尚不能確認

原 receipt 將 MRD-NIT-001 列為 NIT/deferred，稱為「annotation mismatch」，
並引用 `docs/loops/issue-209/follow-ups.md`。此次透過 GitHub connector
讀回合併 PR 的完整 discussion timeline，只有這份 JSON 收據，沒有該 finding
原始檔案、行號或 reviewer 註解。因此不能還原原作者的精確指涉。

原 head 與目前基準的 follow-ups blob 都是
`77f0371` 前綴，內容只有 class-crowding 等既有追蹤，未列 annotation mismatch。
原收據中的檔案追蹤聲明與該版本內容不一致。本次保留原收據，不補寫或改寫歷史
finding，不把 class-crowding 當成同一缺陷或宣稱它已修正。

可重現的最強候選是 `scripts/eval-memory-pilot.py` 的私有 `_observe_cases`：

- 原 head 與此次修改前，第 92 行宣告 `tuple[list[dict], int, bool]`。
- 第 166 行只回傳 `observations, 1`，實際是二元 tuple。
- 唯一呼叫點第 212 行解構為 `observations, backend_touches`，與實際值一致。
- 這三處均在原 head 已存在；後續只有合成測試內容改從 catalog 取得版本，
  不影響回傳及呼叫者。

執行 introspection 證實原註記為三個型別、實際為長度 2 的 list/int tuple。
這與 receipt 描述相符，但 **它就是 MRD-NIT-001 仍屬推論**。

## 處置

已確認來源層級 NIT，不是執行期 blocker。#225 將私有 helper 註記最小修正為
`tuple[list[dict], int]`，沒有修改函式內容、呼叫者或 M1 公開 return/type contract。
即使原 finding 指的是別處，此修正也有獨立來源證據，不依賴猜測歷史身份。

檢查範圍包含 PR #210 的 31-file range、兩個核心模組與全部直接 importer/caller。
`memory_pilot` 的 remember/invalidate/recall 與 `memory_sqlite` 相關公開函式
皆符合 dict return；內部 `_open_checked` 的三元 tuple 與實際一致。
source/package 核心模組在原 head 至本次基準相同；本次 patch 也沒有改動它們。
沒有證據把這個私有 eval 註記問題升為 runtime blocker。

追溯 disposition：`source-analysis-complete; original-finding-identity-unresolved`。
已確認候選：`fixed-in-working-patch; NIT; runtime-blocker=false`。
這不表示 patch 已提交、合併或 Issue 已關閉。

剩餘歷史身份追蹤由 maintainer 持有；若找到原始 finding 或未來改動 M1 公開型別
契約，重新對照並評估。此前不為缺少原始資料而捏造一一對映。
class-crowding 仍依 [原 follow-up](../issue-209/follow-ups.md) 的獨立產品觸發條件追蹤。

## 可重跑來源與驗證

```bash
git diff --stat c0e03d2..7b7442e4d7fb988b38b7f4b37ad3a86d3e7cf649
git grep -n '_observe_cases' 7b7442e4d7fb988b38b7f4b37ad3a86d3e7cf649 -- '*.py'
git show 7b7442e4d7fb988b38b7f4b37ad3a86d3e7cf649:docs/loops/issue-209/follow-ups.md
git diff 7b7442e4d7fb988b38b7f4b37ad3a86d3e7cf649 -- scripts/eval-memory-pilot.py
./scripts/project-python -c 'from tests.test_memory_pilot import load_eval_module; import typing; m=load_eval_module(); r=m._observe_cases(); print(typing.get_type_hints(m._observe_cases)["return"]); print(type(r).__name__, len(r), [type(x).__name__ for x in r])'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_pilot tests.test_memory_sqlite tests.test_sqlitectl tests.test_eval_memory_sqlite
./scripts/project-python scripts/eval-memory-pilot.py
```

修正後 introspection 應顯示二元 tuple 註記與二元 list/int 實際值；
synthetic eval 必須繼續通過。未安裝靜態型別 checker，未改用其他 Python 環境。
最終實際驗證結果見 [#225 驗證紀錄](../issue-225/verification-and-review.md)。
