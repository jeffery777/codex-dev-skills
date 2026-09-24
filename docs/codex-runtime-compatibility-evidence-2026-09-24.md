# Codex runtime 相容性證據 — 2026-09-24

追蹤：[Issue #295](https://github.com/jeffery777/codex-dev-skills/issues/295)。
本次先建立並讀回 Issue，再在 GitHub 從已核對的遠端 main
`7100b3bfe3ada80b7ccfdda7133c4ac6e7d2d194` 建立
`codex/issue-295-runtime-index-workflow`，讀回遠端 SHA，取得並驗證本機分支
後才修改檔案。原始唯讀稽核基於 `75c2568`；實作前已重讀最新來源，沒有
直接更新本機 main。歷史相容性證據及 release notes 保留原貌。

## 入口與範圍

| 證據面 | 本次觀測 | 限制 |
| --- | --- | --- |
| Desktop application | `26.917.62051`，build `10789`，`prod`；updater 回報 `up_to_date` | 已安裝 app 的 update tool，不表示全球最新版本或所有帳號 rollout |
| Desktop bundled CLI | `codex-cli 0.155.0-alpha.16.3` | 明確選定 bundled executable 的 version／help |
| Standalone CLI | `codex-cli 0.156.1` | 與 bundled 分別選定 executable |
| Desktop callables | 38 個 `mcp__codex_app__`；依當次完整 schema 比對 | current-session evidence，不是 published stable schema 或遠端 caller 保證 |
| Registry | `list_projects` schema 2；`list_threads` schema 4 | 支援唯讀 schema／kind／host 觀測，不等於 mutation 驗收 |
| Attachments | `list_artifacts` 為空集合 | 不證明非空或 mutation response |

create／fork 的 ready `threadId` 與 queued `clientThreadId`、worktree 的
cwd／permissions、handoff 與排程核心契約仍適用。共享 delivery／orchestrator
保留選路、ownership、驗證、review 與完成判定；CLI executor 與 Desktop
adapters 維持獨立入口，不新增 wrapper 或 app-server client。

## 本次指引補強

- `move_thread_to_sidebar_section` 依 registry `kind` 明確傳入 `source`；
  預設 Codex 不得代替 ChatGPT，`hostId` 只傳給 Codex。Readback 保留 kind／
  host／ID，其他 callable 不盲目套用這組欄位。
- 混合清單不表示 fork／handoff／wait 支援 ChatGPT。ChatGPT archive 查詢
  需要 local Desktop、`source: "chatgpt"` 並省略 host。當次 archive listing
  與 restore tool 說明有支援範圍差異，保留 restore 未驗證，不推定可恢復。
- `open_in_codex.threadId` 僅在明確要求其他 ready 任務時使用。隱藏目標
  回傳 `queued` 時，須待同一視窗再次顯示目標才開啟面板；不能宣稱已顯示、
  自動導航或重送。Terminal panel 需要 local task。

這些是可安裝指引的契約補強，不是 live mutation 的 bug reproduction。
[官方 non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)
仍記錄 `thread.started`／`thread_id`、`item.completed`／`agent_message`、
`turn.completed`／`turn.failed` JSONL 契約。
[官方 changelog](https://learn.chatgpt.com/docs/changelog) 列出 CLI 0.156.1，
本次未找到精確 Desktop build 的對應條目，故以本機公開工具證據為準。

## GitNexus 落後原因與恢復

初始 MCP registry 指向本機 checkout 的舊索引，落後當時本機 HEAD 55 commits；
同名的另一個 worktree 也在 registry 中。之後確認遠端 main 已前進，而本機
main 尚未同步。兩者均不能由「GitHub 已合併」推定本機索引即時更新。
索引落後的判定是相對於當時本機 HEAD，不是相對於遠端 main；本機保留較舊
revision 本身不是缺陷，多人協作時可能是必要的工作狀態。

唯讀檢查顯示沒有生效的原生 Git post-merge／post-commit hook；本機有 Codex
`SessionStart`／`PostToolUse` GitNexus hook 與信任紀錄，但 machine-local
設定為 `notify-only`。這直接解釋為何它不會自動刷新；沒有存取私有 runtime
logs，因此不宣稱已驗證每次事件實際觸發、通知送達或當前 app 的 hook 載入。
既有範本預設不啟用，自動模式亦需另外 opt-in，不能把安裝當作啟用。

完成 Issue／遠端分支前置後，使用既有 GitNexus `1.6.9` 公開 help 確認
`--index-only`，在精確 checkout 執行 `gitnexus analyze --index-only`。
此次增量刷新約 28 秒，metadata `lastCommit` 與分支 HEAD `7100b3b` 一致；
MCP 以完整 repository 路徑執行 query／context，成功定位 `_probe_version`
與 `validate_request`／process-tracker 接點，沒有採用同名 worktree 的索引。

刷新前後核對 1,179 個受追蹤／保護檔案檢查項，digest 與存在狀態一致，
Git status 乾淨；`AGENTS.md` 未改。這是人工 index-only 探索證據，不是
V2c qualified controller／sidecar 的驗收。後續內容修改使該索引僅能作為
相應未變來源的定位輔助，不能以相同 HEAD 宣稱 dirty working tree 仍 exact。

實作後的增量刷新另遇到 `FTS index 'file_fts' is inconsistent`，不是遠端
同步問題。公開的 `gitnexus analyze --repair-fts --index-only` 回報修復成功；
失敗與修復前後 1,187 個檔案檢查項、status、diff、branch／HEAD 均未改變。
FTS repair 只修搜尋結構，仍須再完成 analyze 與 query readback 才能採用索引；
收尾的索引結果另以當次讀回為準，不以 repair exit 0 推定全部內容已更新。

本 repository 的 [CONTRIBUTING.md](../CONTRIBUTING.md) 現在規範
Issue → 遠端 Issue 分支 → 本機身分核對 → tracked edits，及相對於當前
checkout 的 stale index → 就地安全刷新 → 保護檔案／metadata／query 讀回。
遠端 merge 只觸發重新評估；本機同步另依協作狀態、工作進度與授權決定，
不是刷新索引的前提。它不在安裝 catalog 或
plugin allowlist，不把 GitHub 流程施加給使用共享技能的 GitLab／其他專案。
不啟用自動 hook，不修改 `AGENTS.md`，也不聲稱未量測的 token 節省。

## 驗證與限制

原始稽核的 CLI suite 64 項有 1 項失敗：fake version-probe 的 timeout／
stdout-overflow 測試期待 `fallback`，卻收到 `stopped`；單獨重跑仍失敗。
獨立診斷在 overflow fake 快速退出的重複實驗中捕捉到 `os.killpg` 的
`PermissionError (EPERM)`，receipt 為 `stopped / termination_error`，未呼叫
session。底層權限拒絕原因仍未知，也不能以這次重現替沒有詳細 receipt 的
最初失敗定因，或歸因於 Desktop 更新。

同時確認原測試有覆蓋缺口：兩種模式共用 0.1 秒 deadline、assertions 在
subtest 外，overflow fake 立即退出可能只測到 version-format rejection。
把 stdout limit 放寬到 16,384 bytes，原測試仍通過，證明未必驗到超限。
本次僅修改 fixture／測試：overflow flush 後等待 controller 終止，獨立使用
2 秒 deadline，並在終止前確認 capture 的 `overflow_stream`。放寬 limit
的記憶體 mutation 現在會使 overflow assertion 失敗。另加入 root identity
與 process-group signal 的 EPERM 注入，確認仍回報 `stopped / termination_error`
且沒有 session call。沒有放寬 production executor 的權限或終止判定。

變更後驗證：CLI 66 項與 plugin packaging 16 項合計 82 項通過；明確選定
Desktop bundled executable 的 public-help 3 項通過。文件契約與 GitNexus
config guard 59 項通過；generated package 140 檔 parity 通過；repository
validation 的 `--skip-unit-tests` 模式通過，未以它宣稱全套 unit tests 通過。
這些結果證明本次測試與指引變更，不證明底層 EPERM 已消失。

後續同 Issue 的 [killpg EPERM 調查](diagnostics/killpg-eperm-2026-09-24.md)
保留快速退出 fixture，逐層縮減至 stdlib，並取得使用者執行的一般 Terminal
同程式對照。自然 EPERM 仍可重現；調查、觀測機制與仍未知的精確因果見該文件，
不把本節較早的測試通過當成 EPERM remediation。

原始 bundled public-help 3 項、文件契約 55 項及 140-file package parity
通過；15 份相關已安裝指引與當時來源一致。這不是本 Issue 新內容的安裝證據。
本 Issue 不修改版本號、historical release notes 或發布狀態；可安裝契約更新
值得在後續 patch release gate 評估，不能當作已發版、已安裝或合併授權。

重跑使用 repo 的 pinned Python；分別選定 standalone／bundled executable：

```bash
./scripts/project-python -m unittest tests.test_cli_session_handoff
./scripts/project-python -m unittest tests.test_plugin_packaging
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs tests.test_runtime_compatibility_release_docs tests.test_gitnexus_config_guard
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

本次沒有 live start／resume／fork、Desktop create／fork／handoff／sidebar
mutation、遠端 caller 或原生 CLI/TUI 驗收，不能以 help、synthetic 或文件
測試取代。#242／#251 的獨立未解範圍不因本文件而關閉。
