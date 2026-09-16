# Release Notes: v0.24.4

Status: release candidate prepared through Issue #259.

此點時紀錄描述 source/package 準備；annotated tag 與正式 GitHub Release 的
讀回才是發布證據。本文不證明合併、發布、安裝或部署完成。
Commit、push、PR、merge、tag、Release 與 deploy 保留 separate human gates；
依當次有效授權及各項前置執行，已有授權不因內部階段切換而重問。

## 整合審查與驗證證據

- code-review 與 code-review-deep 在受影響路徑涉及外部命令、環境傳遞、
  loader/builder 或 producer/consumer 時，按需載入同一份整合接點參考表。
  檢查涵蓋輔助 version probes、mock 的主機依賴、啟動前有效環境、strict
  input 契約、文字／二進位產物，以及部分成功與安全重試。
- Agent task brief 增加可選的執行與邊界證據提示：必要 suite／情境實際
  run/skip/fail、原因、mock 範圍、真實或代表性環境／input、未驗證範圍。
  可沿用既有報告；skip 依適用判準解讀，不一律算失敗。
- 不增加例行 approval gate、全套 CI 矩陣、強制格式或 attestation，也不要求
  所有 mock 改成真環境測試。共享 reference 隨 source 與 plugin 一起封裝。

## 驗證與量測範圍

Reference 可達性與 package parity 有 deterministic checks；合成 oracle
以真實本機 Python／shell／subprocess 驗證四個接點缺口及獨立控制情境。
這些驗證不是實際公司 Runner 或任意外部工具的相容性證明。

Astra 配對 pilot 的預先設計、原始結果摘要與限制記於
[Issue #259 結果](loops/issue-259/pilot-results.md)：A/B 各五次 terminal responses，
缺陷辨識持平，十份磁碟工作包全為 partial。新版未證明品質或成本提升。
提示組合比較不構成正式 profile
資格、其他 effort／模型排名或跨 runtime 結論；未可靠量得 subscription
credit，也不把 API dollar estimate 當成 credit。沒有節費或普遍效率宣稱。

## Compatibility And Boundaries

候選完整範圍為 v0.24.3 起點至本候選：上述 installable review／brief 補強、
可達性檢查、去識別 fixture 與量測紀錄、catalog／installer／plugin 版本同步。
這是向後相容的 patch；沒有修改 routing、test sharding、installer 邏輯、
runtime harness、模型預設、qualification store 或記憶 backend。
版本判斷見 [交付計畫](loops/issue-259/plan.md)。

## Verification And Release Gate

發行前必須通過必要 verification、獨立 review、Security Diff Scan、完整
exact-head Merge Review、hosted CI、receipt readback、dedicated App 及 ruleset
gates，再核对 exact commit／tag／Release payload。實際結果以 PR 證據為準。
發行不會自動安裝或部署到任何機器。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Traceability

Issue #259: <https://github.com/jeffery777/codex-dev-skills/issues/259>
