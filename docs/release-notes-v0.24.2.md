# Release Notes: v0.24.2

Status: release candidate prepared through Issue #237.

此點時紀錄描述 source/package 準備。發布真相另由 annotated tag 與正式
GitHub Release 讀回確認；本文件不證明合併、發布、安裝或部署完成。
Commit、merge、tag、Release 與部署保留 separate human gates；依當時有效
使用者授權及各項前置證據執行，已有授權不因階段切換要求重複確認。

## 依角色與當次需求組合提示詞

- 共用契約與 delivery／orchestration／implementation／continuation 入口
  明確區分事實來源、指令優先序、已授權續行及真正未解決的停止條件。
- Task brief 與交接範本補齊角色、ownership、授權來源、必要驗證與升級條件；
  reviewer 保持唯讀，子代理不繼承主代理平台寫入權。
- 已授權 receipt 發布／讀回先於該 receipt 的 App verdict；merge 仍須完整
  exact-head gate。不修改或繞過 Codex runtime 的自動核准機制。
- 模型／effort 維持既有分層；保留 baseline、candidate qualification 與 digest
  邊界。指南提供固定配置比較提示詞，再固定提示詞比較配置的評估方式。

## 自 v0.24.1 累積的來源

本候選也包含先前已合併的 #231 scope/lifecycle 合成契約，以及 #235 G1
contract/host/storage/core、governancectl 與 reference。G1 來源會隨既有
package allowlist 安裝；預設仍關閉、production registry 仍空，proposal 僅
提供有界 schema 檢查，無合格真實資料管理 adapter。這些是合成與內部核心
成果，不能宣稱完整 MG1、真實資料操作、G2 清除／維護或 G3 資格已完成。

## Compatibility And Boundaries

本 Issue 修正可安裝 workflow 的指令歧義，沿用模型／route／receipt schema、
權限、獨立審查、fallback 與必要 gates；沒有啟用新的生產記憶 backend 或
修改 M1 public API。以相容指引修正準備 patch，完整版本判斷見
`docs/loops/issue-237/plan.md`。沒有新真實模型 benchmark，不宣稱改善速度、
成本或品質；安裝與部署不包含於本次交付。

## Verification And Release Gate

實際驗證、獨立審查及限制記於 `docs/loops/issue-237/verification-and-review.md`。
候選版本的三個來源為 catalog、installer、plugin manifest；既有 release notes
保持歷史原文。發布前另核對完整 release range、精確合併 SHA 與 tag／Release 衝突。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Traceability

Issue #237: <https://github.com/jeffery777/codex-dev-skills/issues/237>
先前合併來源：#231 / PR #234；#235 / PR #236。
