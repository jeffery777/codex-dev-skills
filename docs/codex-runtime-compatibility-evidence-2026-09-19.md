# Codex runtime 相容性證據 — 2026-09-19

追蹤：[Issue #269](https://github.com/jeffery777/codex-dev-skills/issues/269)。
先建立並讀回 Issue，再從已核對的 main `32931c98ba400939066a2af6f4716791d095a1a6`
建立 `codex/issue-269-runtime-interface-refresh`。原評估來源為 `b3c195b`；兩個
來源的 CLI／Desktop 接口檔案相同。歷史 [9 月 17 日紀錄](codex-runtime-compatibility-evidence-2026-09-17.md)
與 release notes 保持原貌。

## 獨立入口與證據

| 入口／能力 | 本次觀測 | 限制 |
| --- | --- | --- |
| Standalone CLI | `codex-cli 0.155.1` | 明確選定 executable 的公開 version／help |
| Desktop application | `26.915.31945`，build `9922` | application bundle 公開 version metadata |
| Desktop bundled CLI | `codex-cli 0.155.0-alpha.9.2` | 與 standalone 分開選定 executable |
| Desktop 原生工具 | 35 個 `mcp__codex_app__` callable | 當次正式清單及完整 schema，不是遠端 caller 保證 |
| Project／task registry | `list_projects` schema 2；`list_threads` schema 4 | 公開唯讀讀回，保留 project／host 與 ready／queued 身分分流 |
| 附件 | `list_artifacts` 回傳空集合 | 只證明目前 task 沒有已登錄附件，不證明非空或 mutation response |

這些是 current-session evidence，不是 published stable schema。`create_thread`、
`fork_thread`、wait／handoff 及排程既有契約在本次比對範圍內相符；工具數目
與版本號本身不證明新增功能、修復或所有 host 能力相同。

## 需要更新的 adapter 指引

1. `reorder_sidebar_sections` 接受全部自訂 IDs 恰好一次，另可指定
   `pinned`／`agents`／`chats`／`projects` 內建 headings；省略內建 headings
   保留位置。舊指引將 reorder 一律要求解析為自訂 section，需局部修正。
   本次 registry 的 `sections` 分類含 `pinned`／`threads`／`chats`，因此不能
   原樣當成該排序操作的 IDs；缺少可驗證順序時保持未驗證。
2. `create_worktree` 是目前 task 的隔離 checkout 操作：選填 `ref`／`name`，
   default HEAD，不複製未提交修改、不跑 setup、不改 cwd／permissions；
   建立後 registration 失敗沿用回傳目錄。新增 Desktop delivery reference，
   與另開 task、history fork、handoff 及共享任務模式分開。
3. CLI dashboard 新增整理／刪除操作的分類說明；不擴大 shell executor。

共享 `project-delivery`／`project-orchestrator` 仍負責選路、ownership、驗證、
review 與完成判定。工具 dispatch／附件／task 狀態不是 repository 完成證據。

## 官方與本機驗證範圍

[官方 changelog](https://learn.chatgpt.com/docs/changelog) 列出 CLI 0.155.0 的
dashboard hide／archive／delete／managed-worktree deletion，以及 0.155.1
對 TUI reasoning-summary 預設值的修正。現有 adapter 不依賴該顯示預設。
查核時未找到精確 Desktop build 的更新條目，故以本次公開 callable 為準。
[非互動模式文件](https://learn.chatgpt.com/docs/non-interactive-mode) 仍記錄
既有 `thread.started`／`thread_id`、`item.completed`／`agent_message` 及
`turn.completed`／`turn.failed` JSONL 契約。

原評估完成 standalone CLI suite 64 項、bundled public-help 3 項、文件契約
51 項；全部通過。完整 installer suite 因耗時中止，不列 PASS。16 份相關
已安裝 Markdown 與原本機來源一致；這不是本 Issue 新變更的安裝證據。
本 Issue 修改後的驗證與 review 另以當前 diff／PR 證據為準。

重跑時先選定自己的 standalone／bundled executable，再分別傳入
`CODEX_PUBLIC_HELP_EXECUTABLE`；repo Python 使用 `scripts/project-python`。

```bash
./scripts/project-python -m unittest tests.test_cli_session_handoff
./scripts/project-python -m unittest tests.test_native_runtime_contract_docs tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

沒有 live model start／resume／fork、Desktop create／fork／worktree／sidebar
mutation、遠端 caller 或原生 CLI/TUI callable 驗收。公開 help、synthetic
與文件測試不能替代這些證據；#242／#251 仍是獨立未解範圍。沒有存取 private
runtime state 或修改全域設定。本次可安裝契約變更值得準備 patch；發版判斷
及邊界見 [v0.24.7 候選紀錄](release-notes-v0.24.7.md)，不以本文件證明發布。
