# Codex runtime 相容性證據 — 2026-09-11

追蹤：[Issue #249](https://github.com/jeffery777/codex-dev-skills/issues/249)。
本紀錄區分獨立 CLI、ChatGPT desktop app 與 bundled CLI；三者的入口與版本
must not collapse。原 [2026-09-04 紀錄](codex-runtime-compatibility-evidence-2026-09-04.md)
保留原貌。此為本機 macOS 點時證據，不代表遠端 caller 或所有平台可用。

## 版本與公開介面

| 入口 | 本次觀測 | 驗證來源／限制 |
| --- | --- | --- |
| 獨立 CLI | `codex-cli 0.154.0` | 選定執行檔 `--version`、公開 help、隔離測試及下列 live smoke |
| Desktop application | `26.903.71938`，build `8576` | application bundle 的公開 version metadata |
| Desktop bundled CLI | `codex-cli 0.153.4` | 與獨立 CLI 分開選定執行檔及驗證 |
| Desktop 原生工具 | 31 個 `mcp__codex_app__` callable | 當次完整 metadata；`list_projects` 讀回 schemaVersion 2，`list_threads` 讀回 4 |

These descriptions are current-session evidence, not a published stable schema.

Standalone CLI 0.154.0 已移除 deprecated `codex mcp-server`；bundled 0.153.4
仍回傳該 subcommand 的 help。Standalone 的相同請求 exit 0 但顯示 root help，
因此能力判斷必須核對完整 usage shape。這不代表 external MCP servers、
client configuration、plugins、connectors 或 native Desktop task/thread tools
遭到移除。[官方 changelog](https://learn.chatgpt.com/docs/changelog#github-release-385887902)

`codex exec` 與原生 Desktop callable 是不同契約；Codex app-server 亦為獨立
JSON-RPC 家族。本次不建立 app-server client、wrapper、daemon 或 sidecar。

## Desktop schema 比對

| 契約 | 本次核對重點 |
| --- | --- |
| `list_projects`／`create_thread` | 使用正式 projectId 與 isGitRepository；target／environment／startingState 分流 |
| `fork_thread`／send／read | completed history、續行需明確 follow-up；ready threadId 與 queued clientThreadId 分別處理 |
| `wait_threads`／handoff | cursor、hostId、bounded wait 與 operationId；工具結果是協調證據 |
| Sidebar | `create_sidebar_section`、`move_thread_to_sidebar_section`、`reorder_sidebar_sections` 等由獨立 `desktop-sidebar-organization` 契約處理 |
| Metadata／helpers | `set_thread_archived`、`get_usage_limits`、`load_workspace_dependencies` 等不授予新的交付權限 |
| `automation_update` | 排程另有明確授權；本次沒有建立排程 |

比對既有 Desktop adapter 文件未發現需改寫的 payload。這是 schema 與兩項
唯讀讀回證據，不是上述所有 mutation 的真實操作驗收。
Desktop SSH 遠端 caller 仍由 [#242](https://github.com/jeffery777/codex-dev-skills/issues/242)
追蹤；本機成功、bundled version 或 CLI 成功不代表該遠端問題已修復。

## 測試與重跑

先用 `./scripts/project-python` 確認 pinned Python 3.12.9／PyYAML 6.0.3。
執行檔路徑是本機輸入，不寫入個人配置。下列兩次均為 **64 tests PASS**：

```bash
CODEX_PUBLIC_HELP_EXECUTABLE=/opt/homebrew/bin/codex ./scripts/project-python -m unittest discover -s tests -p 'test_cli_session_handoff.py'
CODEX_PUBLIC_HELP_EXECUTABLE=/Applications/ChatGPT.app/Contents/Resources/codex ./scripts/project-python -m unittest discover -s tests -p 'test_cli_session_handoff.py'
```

其中 3 項檢查所選 binary 的公開 version／help／plugin JSON；其餘使用 fake
executables、synthetic process mocks 或離線契約。測試不呼叫 live model。
明確指定的執行檔不存在／不可執行會失敗，不退回 PATH；只有未指定且 PATH
沒有 CLI 時，公開 help 部分可 skip。負向案例拒絕 exit 0 的 root／parent help。

`codex exec fork` 仍是 observed and locally qualified public-help surface，
不是官方承諾永久穩定的介面。兩版上游 `exec_events.rs` 與
`event_processor_with_jsonl_output.rs` 比較為 byte-identical；TUI dynamic tool
唯一差異為 internal list request 增加 `originators: None`，未改 create/fork
payload。來源：[0.154.0 exec events](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/exec/src/exec_events.rs)、
[JSONL emitter](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/exec/src/event_processor_with_jsonl_output.rs)、
[TUI source](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/tui/src/dynamic_tools.rs)。

Experimental `--worktree` 並非現有 private-clone adapter 的直接替代：0.154.0
source 拒絕與 `--ignore-user-config`、`--ephemeral` 或 `exec resume` 組合，
且有 feature／local execution 條件。本次沒有添加此旗標。
[官方 source](https://github.com/openai/codex/blob/rust-v0.154.0/codex-rs/exec/src/lib.rs)

## 真實 smoke 與程序觀測

每組使用獨立的 synthetic Git workspace，經既有 adapter 順序執行 start、
resume(start UUID)、fork(start UUID)。request 維持 read-only、240 秒上限、
`--ignore-user-config` 與 private clone；以公開 receipt 核對 resume 同 UUID、
fork 新 UUID、turn.completed、exit 0、來源 HEAD／檔案 digest 不變。
官方 `login status` 確認既有 ChatGPT 登入；沒有複製或讀取憑證／session files。

| 測試 revision | CLI | 結果 |
| --- | --- | --- |
| 原 adapter | 0.153.4 | start 通過；resume 回報 termination_error／Process-tree inventory became unavailable；fork 未執行 |
| 原 adapter | 0.154.0 | start／resume／fork 通過 |
| 補強後 adapter | 0.153.4 | start／resume／fork 通過 |
| 補強後 adapter | 0.154.0 | start／resume 通過；fork 回報 termination_error，stage=child-identity; errno=1 |

原 adapter SHA-256：`ecd5ac31cf1cec3e677e85f5c7e61e341fed020390301ed4276c17c7632c38ea`。
補強後 SHA-256：`eb60cb6ce74e0e39ee1ebbef0112fbe873e33412d77ea5e89275d123637d198a`。
Executable SHA-256：standalone `4f85982624b3898c8991cb80c0981b2aa71070e3537046c9a95950318a95afcc`；
bundled `87a08119b8effa519f0ecb552dc98043f58a8200bf2ec5da60f76890c33e9c3a`。

首輪 fixture 因全域 AGENTS.md ignore 規則在準備時停止，尚未呼叫 session；
只在 synthetic Git 命令指定空 excludesFile 後繼續，沒有改個人 Git 配置。
Resume 的原始通用錯誤未保留底層原因，不能判定 CLI 回歸或模型 turn 失敗。
後續觀測成功不能還原原故障；原錯誤與下列缺口的因果尚未建立。

補強後 standalone fork 的診斷確認 child identity 觀測收到 EPERM（errno 1）。
Receipt 的 session_call_performed 為 true，但 exit／terminal 為 null；只能證明
程序觀測未完成，不能判定模型 turn 成敗或宣稱本輪三項全部驗收。Synthetic
source 的 HEAD／檔案 digest 仍相符。沒有忽略 EPERM、提高權限或盲目重試；
OS 為何拒絕該次查詢仍未知，原 generic incident 也不能據此回溯歸因。

Production adapter hardening：Apple libproc wrapper 可能以 0 + errno 回報
inventory 失敗。本次先清除 errno，再區分空集合、已消失程序與觀測錯誤；
滿 buffer 無法證明完整覆蓋時亦停止。新增固定 stage／numeric errno 診斷，
保留第一個錯誤，不輸出原生錯誤文字、PID、路徑或原始 transcript。
六項 synthetic tests 覆蓋權限拒絕、stale errno、程序消失、容量及 sticky failure。
[Apple 官方 wrapper](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c)

Live receipt 刻意省略 child summary，所以不證明實際模型／effort、history
內容正確性或任務品質。來源完整性與程序完成也不是 repository 交付完成。
Shared core 與 Desktop adapter 語意保持原樣；沒有放寬 sandbox、吞掉觀測錯誤
或移除 termination gate。日後 live 重跑須重新核對操作授權、binary／adapter
digest，使用 `cli_session_handoff.py --example` 的正式 request，再逐項檢查
receipt 與 synthetic source；不能把普通 tests 改成自動 live 呼叫。

## 配置追蹤

Custom-agent model／effort 的官方解析優先序已同步至
[設定文件](main-agent-and-subagent-settings.md)。維護者採用 Astra／xhigh 的
舊值註解、資格限制及回復條件見[配置決策](astra-xhigh-profile-decision.md)。
本次沒有安裝、部署、發布、啟用資格 store 或改寫歷史用量證據。
