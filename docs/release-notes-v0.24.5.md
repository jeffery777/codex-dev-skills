# Release Notes: v0.24.5

Status: release candidate prepared through Issue #261.

此點時紀錄描述 source/package 準備；annotated tag 與正式 GitHub Release 的
讀回才是發布證據。本文不證明合併、發布、安裝或部署完成。
Commit、push、PR、merge、tag、Release 與 deploy 保留 separate human gates；
依當次有效授權及前置執行，已有授權不因內部階段切換而重問。

## 共享 GitHub 操作政策

- 正當 `gh` fallback 優先使用單純 API 命令，本地保存輸出另行處理；說明
  shell 重導向可能改變前綴比對範圍。
- 反覆提示先核對實際 argv、相關保存／載入規則與公開診斷，不持續重複同一
  寫法，不把靜態匹配當成完整授權結果。
- 保留 connector-first、必要授權與最小權限；不得擴大規則或重送 mutation
  只為取得輸出。規範同時供 CLI 與 Desktop 入口使用。

## Desktop 相容性

新增 Desktop 26.908.70816（build 9275）、bundled CLI 0.154.0-alpha.6.2 與
standalone CLI 0.154.0 的點時證據，更新 active pointers 與兩版均未提供
`mcp-server` 的公開 help 觀測。原生 Desktop schema 比對未發現需修改
adapter payload 的差異；詳細覆蓋與未驗證範圍見
[相容性證據](codex-runtime-compatibility-evidence-2026-09-16.md)。

## Compatibility And Boundaries

版本判斷：值得發行向後相容的 patch，因共用且可安裝的 GitHub 操作指引已改變，
可減少因命令形狀造成的可避免授權重複；不承諾消除所有提示。單純歷史版本
紀錄本身不構成發行理由。catalog、installer 與 plugin manifest 同步 0.24.5。

CLI／Desktop 保持獨立入口與共享分層。本次沒有改 executor、installer 邏輯、
模型配置、全域 AGENTS、approval rules、sandbox 或 private runtime state。
沒有新增 live session／遠端 caller 驗收，未宣稱已修復既有 fork／SSH 問題。
舊相容性與 release notes 保留歷史角色。

## Verification And Release Gate

發行前必須通過必要 verification、獨立 review、Security Diff Scan、完整
exact-head Merge Review、hosted CI、receipt readback、dedicated App 及 ruleset
gates，再核對 exact commit／tag／Release payload。實際結果以 PR 證據為準。
候選準備不證明發布；發行也不自動安裝或部署。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Traceability

Issue #261: <https://github.com/jeffery777/codex-dev-skills/issues/261>

授權提示的觀測與推論限制見 [GitHub fallback 稽核](gh-fallback-approval-evidence-2026-09-16.md)。
