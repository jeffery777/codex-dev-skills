# Codex runtime 相容性證據 — 2026-09-16

追蹤：[Issue #261](https://github.com/jeffery777/codex-dev-skills/issues/261)。
本紀錄為本機 macOS 點時證據；獨立 CLI、Desktop application、bundled CLI
與原生 Desktop callable 各有自己的證據邊界。保留
[2026-09-11 紀錄](codex-runtime-compatibility-evidence-2026-09-11.md) 原貌。

## 版本與公開介面

| 入口 | 本次觀測 | 驗證來源／限制 |
| --- | --- | --- |
| 獨立 CLI | `codex-cli 0.154.0` | 選定 binary 的 `--version` 與公開 help |
| Desktop application | `26.908.70816`，build `9275` | application bundle 公開 version metadata |
| Desktop bundled CLI | `codex-cli 0.154.0-alpha.6.2` | 與獨立 CLI 分開選定 binary |
| Desktop 原生工具 | 31 個 `mcp__codex_app__` callable | 當次完整 callable metadata；`list_projects` schemaVersion 2、`list_threads` schemaVersion 4 唯讀讀回 |

These descriptions are current-session evidence, not a published stable schema.
工具 catalog 可能受 host、授權及 session 影響；版本號本身不授予能力。

兩個 CLI 的 `codex mcp-server --help` 均 exit 0，但顯示 root usage，且 root
command list 沒有 `mcp-server`。不能以 exit code 判定 deprecated subcommand
仍可用；原 bundled 0.153.4 的支援是歷史觀測。兩者仍列出 `mcp`、`agents`
及 experimental `--worktree`，不代表 external MCP servers、plugins、connectors
或 native Desktop task/thread tools 被移除，也不授權替換既有 private-clone
adapter。`codex exec`、原生 Desktop callable 與 Codex app-server JSON-RPC
仍為各自獨立的契約。

## 分層與 Desktop 契約

| 分層 | 本次核對結果 |
| --- | --- |
| Shared workflow／policy | 延續共同的選路、權限、證據與交付 gate；GitHub 命令形狀指引放在共用政策 |
| CLI entrypoint | `cli-session-handoff` 與 executor 保持原樣；只更新 dashboard reference 的公開命令觀測 |
| Desktop entrypoints | `desktop-project-delivery`、`desktop-thread-delegation`、`desktop-sidebar-organization` 維持 thin adapters |
| Create／fork | `create_thread` target、projectId、isGitRepository、environment／startingState；ready `threadId` 與 queued `clientThreadId` 分開處理 |
| Observe／handoff | `wait_threads` cursor／hostId／bounded wait、handoff operationId；協調狀態不能代替交付證據 |
| Sidebar／helpers | section membership、完整 reorder、`set_thread_archived`、`get_usage_limits`、`load_workspace_dependencies` 的現行 schema 相符 |
| Automation | `automation_update` 仍要求該項明確授權；本次沒有建立或變更排程 |

目前 source 的 Desktop entries、create/fork 與 observation references、CLI entry／
executor 及 native capability 文件共 8 個選定檔案，在修改前與安裝副本 byte-identical。
本次 schema 比對未發現需修改 runtime payload 或 executor 的差異；沒有把 CLI
與 Desktop 入口合併，也沒有依賴未公開 Desktop internals。

## 已執行驗證與重跑

Pinned Python 3.12.9／PyYAML 6.0.3 由 `./scripts/project-python` 確認。
修改前的相容性稽核執行下列測試：

| 驗證 | 結果與覆蓋 |
| --- | --- |
| bundled `test_cli_session_handoff.py` | 64 PASS；3 項公開 version／help／plugin JSON，其餘 fake executables、synthetic process mocks 或離線契約 |
| standalone `CodexPublicHelpCompatibilityTests` | 3 PASS；只核對選定 binary 的公開 surface |
| `test_native_runtime_contract_docs.py` | 38 PASS；既有文件契約 |
| `test_runtime_compatibility_release_docs.py` | 12 PASS；既有 runtime／release 文件契約 |
| `test_installer_runtime_groups.py` | 53 PASS；隔離 installer 測試，不是實際部署 |
| `scripts/sync-plugin-package.py` | 124 packaged files parity PASS；修改前狀態 |

```bash
CODEX_PUBLIC_HELP_EXECUTABLE=/Applications/ChatGPT.app/Contents/Resources/codex ./scripts/project-python -m unittest discover -s tests -p 'test_cli_session_handoff.py'
PYTHONPATH=tests CODEX_PUBLIC_HELP_EXECUTABLE=/opt/homebrew/bin/codex ./scripts/project-python -m unittest test_cli_session_handoff.CodexPublicHelpCompatibilityTests
./scripts/project-python -m unittest discover -s tests -p 'test_native_runtime_contract_docs.py'
./scripts/project-python -m unittest discover -s tests -p 'test_runtime_compatibility_release_docs.py'
./scripts/project-python -m unittest discover -s tests -p 'test_installer_runtime_groups.py'
./scripts/project-python scripts/sync-plugin-package.py
```

Executable paths 是本機重跑輸入；其他環境必須先選定自己的 binary。修改後的
檢查與 review 以 Issue／PR 交付證據為準，不能沿用上表當成新 diff 的驗證。

## 尚未驗證的範圍

本次沒有 live model start／resume／fork，也沒有 Desktop create／fork／handoff
mutation smoke。2026-09-11 的 `stage=child-identity; errno=1` 原因及修復狀態
仍未在本次驗證；公開 help PASS 不代表執行成功。Desktop SSH 遠端 caller
也未測試，不能據此關閉 [#242](https://github.com/jeffery777/codex-dev-skills/issues/242)
或 [#251](https://github.com/jeffery777/codex-dev-skills/issues/251)。

GitHub 重複授權的另項稽核見
[去識別證據](gh-fallback-approval-evidence-2026-09-16.md)。本次沒有修改全域
AGENTS、approval rules、sandbox、憑證或個人 runtime state；沒有安裝或部署。
