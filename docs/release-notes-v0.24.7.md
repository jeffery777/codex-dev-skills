# Release Notes: v0.24.7

Status: release candidate prepared through Issue #269.

這是 source/package 候選準備的點時紀錄；annotated tag 與非 draft、非 prerelease
GitHub Release 的讀回才證明發布。Commit、push、PR、merge、tag、Release
與 deploy 保留 separate human gates，依各自有效授權及適用 gate 執行。

## Desktop 接口

- 修正 sidebar 排序指引：完整自訂區塊 IDs 加上選填的受支援內建 headings，
  省略內建 headings 時保留位置；不混用 registry 分類或其他操作的特殊值。
- 新增 `desktop-project-delivery` 按需載入的目前任務工作樹 reference：
  `create_worktree` 附加隔離 checkout，不建立新任務或複製歷史；不複製未提交
  修改、不跑環境設定、不改 cwd／permissions。建立後登錄失敗不得重複建立。
- 保留當次 callable 查核、公開讀回、repo 環境驗證與 CLI／手動 fallback。

## CLI 與相容性證據

補充 CLI 0.155.0 dashboard 的 hide／archive／delete 與 managed-worktree
deletion 分類，保留精確目標、刪除 preview、復原條件及明確授權。
不擴大 private-clone executor，不把 dashboard 動作當作驗證或完成證據。

[2026-09-19 相容性證據](codex-runtime-compatibility-evidence-2026-09-19.md)
分開記錄 standalone CLI 0.155.1、Desktop 26.915.31945（build 9922）及 bundled
CLI 0.155.0-alpha.9.2。公開 help／schema／離線測試不證明 live mutation 或
遠端／TUI caller 已驗收，也不關閉 #242／#251 的既有未解問題。

## Compatibility And Boundaries

值得發行 patch：修正及補齊的是可安裝、向後相容的 runtime adapter 指引，
讓安裝者取得新接口的正確使用方式；單純版本觀察本身不是發版理由。
catalog、installer 與 plugin manifest 同步 0.24.7，reference 隨既有 Desktop
群組與 generated plugin 部署，沒有新增群組、共享任務模式或 migration。

CLI／Desktop 獨立入口、共享選路／ownership／verification／review／completion
語意維持不變。沒有 CLI executor、installer 邏輯、模型、approval rules、
sandbox、private state 或排程變更。使用者安裝不會自動更新；發版不等於部署。
歷史 release notes 與相容性紀錄保持原貌。

## Verification And Release Gate

候選須通過離線驗證、必要 tests、generated parity、獨立 review 與 Security
Diff Scan。若建立 PR／發版，完整 exact-head Merge Review、hosted CI、receipt
readback、dedicated App 及 merge／publication gates 仍適用；實際結果以同一
Issue／PR 及 tag／Release 的精確讀回為準。

```bash
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/test-shards.py run-all
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/validate-release-state.py
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

## Traceability

Issue #269: <https://github.com/jeffery777/codex-dev-skills/issues/269>

此紀錄不宣稱合併、發布、live runtime qualification、使用者安裝或部署完成。
