# Issue #271：有界實體儲存驗收

> 2026-09-20 範圍更新：使用者已同意改以[儲存失敗處理驗收](failure-handling-acceptance.md)
> 為 Issue #271／PR #272 的現行 DoD，APFS 實體耗盡研究不列入需求或後續待辦。
> 下方保留最初實體試驗的計畫、額度與當時 gate，屬歷史紀錄，不再定義本包結案條件。

## 基準與順序

2026-09-20 透過 GitHub connector 重新讀回 open Issue #271 與遠端
`codex/issue-271-g1-physical-recovery`，基準皆為
`aedfdb124b996eb1626999bcbdda0f31abe2382d`。獨立乾淨 worktree 由 detached HEAD
正常切換至既存分支並設定 origin upstream，之後才修改 tracked 檔案。
本任務為唯一 implementation writer；父任務與 reviewer 不修改本包檔案。

## 檔案與驗證計畫

- `tests/fixtures/memory-governance/enospc_image.py`：新增唯讀 preflight，先確認
  公開磁碟管理查詢、host headroom 與必要工具；失敗不得進入映像建立。
- `tests/test_memory_governance_storage_faults.py`：驗證 preflight 的拒絕與無寫入邊界，
  沿用 mount/image/filler 身分、單次恢復與 unknown 停止規則。
- `storage_fault_case.py`／`storage_fault_worker.py`／核心：只根據可重現缺陷修正；
  不為取得成功而改分類、跳過 journal 拒絕、放寬資格或新增 recovery。
- `docs/loops/issue-271/`：保存去識別的新觀察與交付限制；直接同步 milestone／roadmap。
  不改寫 #245／#253／#265 的歷史觀察。

先完成固定 Python 3.12.9 venv、focused tests 與唯讀環境對照，才執行最多一次
全新 256 MiB APFS image 的故障試驗。只填寫／截短 originating own filler；
建立前／後取樣核對 host 至少 1 GiB headroom，並非 OS 容量 reservation。
每個外部命令 60 秒、writer 90 秒、fill loop 30 秒，
fresh reader/control/restore 各 30 秒；正常 detach、保留映像與原始證據。
恢復未證明、身分不明或非空 journal 均保留 incomplete，不重試實驗。

儲存相關變更在 PR readiness 前執行 checks-only repo validation、全部 shards、
package parity、release-state、diff hygiene；獨立 deep/code/docs review 與 Security
Diff Scan 之後，再以 PR 最新完整 base-to-head 執行 exact-head Merge Review、CI、
strict receipt 發布讀回與 dedicated App／ruleset gates。

## 發版與完成邊界

source/package 由 catalog 定義；候選紀錄與平台發布狀態分開核對。僅 fixture、
tests 或證據變更原則不另發版；若實證需要 installed 修正才依最終 diff 重評。
default-off、空 production registry、G2/G3 與真實資料邊界保持原契約。
局部試驗不表示完整 G1/MG1 qualification；環境受阻或實體驗收未完成時，
Issue 保持未完成，不以診斷或合成對照取代實體證據。
