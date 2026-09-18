# Codex runtime 相容性證據 — 2026-09-17

追蹤：[Issue #263](https://github.com/jeffery777/codex-dev-skills/issues/263)。
本紀錄整理 2026-09-17 的本機 macOS 唯讀稽核；2026-09-18 補核對發行與
安裝來源。保留 [2026-09-16 紀錄](codex-runtime-compatibility-evidence-2026-09-16.md)
及更早的 evidence／release notes 原貌。

稽核來源為 `bca521adc5678290bc4ab44fd46564a7a806ac92`；後續確認其 tree
與已合併的 `f9c0da84d4d683b56f3275203fb589d92ab17733` 相同。Issue #263
先建立並讀回，再從後者建立及推送 `codex/issue-263-desktop-compat-evidence`，
之後才更新本次文件。

## 版本與公開介面

| 入口 | 2026-09-17 觀測 | 驗證來源／限制 |
| --- | --- | --- |
| 獨立 CLI | `codex-cli 0.154.0` | 明確選定 binary 的公開 version／help |
| Desktop application | `26.911.61220`，build `9647` | application bundle 公開 version metadata；9 月 18 日讀回未變 |
| Desktop bundled CLI | `codex-cli 0.155.0-alpha.2.6` | 與獨立 CLI 分開選定 binary |
| Desktop 原生工具 | 31 個 `mcp__codex_app__` callable | 當次正式清單與完整輸入契約；不是跨 host 的穩定 API 保證 |
| Project registry | `schemaVersion 2` | `list_projects` 實際唯讀回傳，含 project／host identity 與 `isGitRepository` |
| Task registry | `schemaVersion 4` | `list_threads` 實際唯讀回傳，分開 `pinnedThreads`、`threads` 與 `sections` |

These descriptions are current-session evidence, not a published stable schema.
工具可用性仍須依當次入口、正式清單、schema 與權限判斷；本機工具清單不能
證明 Desktop SSH 遠端 caller 或 CLI/TUI 有相同能力。

兩個選定 CLI 的 root、`exec`、`exec resume`、`exec fork`、`agents`、
`queue`、`doctor` help 逐項比對相同。`codex mcp-server --help` 也都 exit 0，
但只顯示 root usage，不能據此認定該 subcommand 仍受支援。這不移除外部
MCP client 設定、plugins、connectors 或 Desktop 原生工具，也不授權改用
app-server client、wrapper 或未公開介面。

稽核時的 [官方 changelog](https://learn.chatgpt.com/docs/changelog) 未列出
精確的 `26.911.61220`／`0.155.0-alpha.2.6` 更新項目，因此沒有由版本號
推論新增或修復行為；本次結論以選定 executable 與公開 callable 的實測為準。

## 獨立入口與共享分層

| 分層／操作 | 本次核對結果 |
| --- | --- |
| 共享工作流 | `project-delivery`、`project-orchestrator` 與共同政策維持選路、權限、驗證、review 及完成語意；subagent delegation 仍是共享能力 |
| CLI 獨立入口 | `cli-session-handoff` 保留 shell executor 與原生 TUI reference 分流；`codex exec --json` 的既有 argv 通過公開 help 檢查 |
| Desktop 獨立入口 | `desktop-project-delivery`、`desktop-thread-delegation`、`desktop-sidebar-organization` 保持 thin adapters；不承接共享層的任務選擇或完成判定 |
| Create／fork | `prompt`／`target`、project environment／startingState、completed history、ready `threadId`／queued `clientThreadId` 與 host 讀回邊界相符 |
| Observe／handoff | `read_thread`、一至八個 `wait_threads` targets、cursor、`hostId`、handoff `operationId` 與 revision-aware 等待語意相符 |
| Sidebar | 精確 identity、特殊 destination、完整 section reorder 及 project partial-list reorder 語意相符 |
| 其他 Desktop 控制 | automation、sharing、navigation 與 account／workspace helpers 保留各自授權；沒有因工具可見而執行 mutation |

在上述覆蓋範圍內，沒有發現需要修改 runtime payload、CLI executor 或共享
架構的差異。這是契約與唯讀回傳的相容性結果，不是 live mutation 成功證明。
Sidebar mutation 等未實際呼叫的成功／錯誤回傳結構仍以當次公開契約及操作後
讀回為準；不補造未觀察的 response 欄位。

## 已執行驗證與重跑

2026-09-17 以 `scripts/project-python` 選定 Python 3.12.9／PyYAML 6.0.3：

| 驗證 | 結果與覆蓋 |
| --- | --- |
| bundled `test_cli_session_handoff.py` | 64 PASS；其中 3 項公開 version／help／plugin JSON，其餘為 fake executables、synthetic process mocks 或離線契約 |
| standalone `CodexPublicHelpCompatibilityTests` | 3 PASS；選定 binary 的公開 surface |
| `test_native_runtime_contract_docs.py` | 39 PASS；既有文件契約 |
| `test_runtime_compatibility_release_docs.py` | 12 PASS；既有 runtime／release 文件契約 |
| `test_installer_runtime_groups.py` | 53 PASS；隔離安裝、入口依賴及交易保護，不是實際安裝 |
| `scripts/sync-plugin-package.py` | 124 generated files parity PASS |

合計 171 項測試通過。這些結果綁定稽核時的來源；Issue #263 新文件的驗證與
review 另以本 Issue／PR 的交付證據為準，不能把舊 PASS 當成新 diff 的驗收。

```bash
CODEX_PUBLIC_HELP_EXECUTABLE=/Applications/ChatGPT.app/Contents/Resources/codex ./scripts/project-python -m unittest discover -s tests -p 'test_cli_session_handoff.py'
PYTHONPATH=tests CODEX_PUBLIC_HELP_EXECUTABLE=/opt/homebrew/bin/codex ./scripts/project-python -m unittest test_cli_session_handoff.CodexPublicHelpCompatibilityTests
PYTHONPATH=tests ./scripts/project-python -m unittest test_native_runtime_contract_docs test_runtime_compatibility_release_docs test_installer_runtime_groups
./scripts/project-python scripts/sync-plugin-package.py
git diff --check
```

Executable paths 是該次本機重跑輸入；其他環境應先選定自己的 binary。公開
help 測試使用臨時 runtime roots，不建立 live model session。安裝測試使用
隔離目錄；實際安裝的預覽、授權、備份與讀回是另一組證據。

## 安裝差異與發行判斷（2026-09-18）

9 月 17 日比對 15 份相關來源與安裝檔案，13 份 byte-identical；安裝副本的
`cli-session-handoff/references/dashboard-queue.md` 與
`docs/native-runtime-capabilities.md` 仍保留舊 bundled CLI／`mcp-server`
敘述。這兩項修正已包含在 Issue #261／PR #262。

9 月 18 日以既有 installer 預覽 `codex-cli-session-handoff` 及其共享依賴，
另外找到同一已發行版本的 `github-control-plane-policy.md` 文案差異，內容為
已審查的 shell 命令形狀與重複授權排查指引。預覽本身不是安裝完成證據。
已有備份槽衝突時，必須依 [安裝復原指引](troubleshooting.md#managed-backup-collisions)
保留原檔，完成精確封存方案及另項授權，不得覆寫或刪除舊備份。

發行來源的點時讀回：

- annotated `v0.24.5` tag object：`4557a44af10fed64daee3543b7dbef0294516698`；
  dereferenced commit：`f9c0da84d4d683b56f3275203fb589d92ab17733`。
- [v0.24.5 GitHub Release](https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.24.5)
  ID `389701607`，`draft=false`、`prerelease=false`，target 與該 commit 相同。

依 [Release-State Contract](../policies/release-state-contract.md)，本 Issue
只新增 repository 相容性紀錄與文件指向；不改可安裝的技能／契約、installer、
catalog 或 generated plugin 內容。因此**不另發新版本**；安裝同步使用已核對
的 v0.24.5 來源即可。這是本 Issue 的範圍判斷，不是永久的目前發布版本宣告；
後續若出現實質可安裝變更，仍須在同一 Issue 重新評估並通過發行 gates。

## 尚未驗證的範圍

本次沒有 live model start／resume／fork，也沒有 Desktop create／fork／handoff
或 sidebar mutation smoke。先前的 `stage=child-identity; errno=1` 原因及
修復狀態仍未驗證；公開 help PASS 不代表執行成功。Desktop SSH 遠端 caller
與遠端 CLI/TUI 未納入本次測試，不能據此關閉
[#242](https://github.com/jeffery777/codex-dev-skills/issues/242) 或
[#251](https://github.com/jeffery777/codex-dev-skills/issues/251)。

沒有讀寫 private runtime state、修改全域 AGENTS／模型設定／approval rules、
啟用 Memory backend 或建立排程。安裝同步的最終結果另記於 Issue／PR；本份
相容性紀錄不宣稱安裝、合併或其他外部寫入完成。
