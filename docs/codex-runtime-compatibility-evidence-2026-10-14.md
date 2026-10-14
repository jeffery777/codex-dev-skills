# Codex runtime 相容性證據 — 2026-10-14

追蹤：[Issue #330](https://github.com/jeffery777/codex-dev-skills/issues/330)。
本次分開核對 standalone CLI、bundled CLI、Desktop native callable 及共享層；
不是全部 lifecycle 或所有平台的重新資格化。

## 基線與 checkout

原 checkout 為乾淨的 `codex/issue-328-candidate-history`，HEAD `5804754`。
GitHub 讀回 #328 已完成關閉、#329 已合併；遠端 main 為
`ee107d346ad92eab54f129a7f46b61b3bf782e60`。先建立並讀回 #330，再從該 SHA
建立、讀回及 fetch `codex/issue-330-runtime-compatibility`，最後核對 local
branch、HEAD、upstream 與乾淨度後才修改。沒有重置、同步、prune 或刪除其他
分支／工作樹，也沒有從最後發行版或 draft PR 衍生。

#323／draft #317 明確暫停；local／第三方模型、Agent Memory 與 Hermes 新投入
不在本案。既有 default-off 程式、歷史候選及資格缺口保留。

## 分層盤點與判定

| 證據面 | 本次查證 | 必要處理與限制 |
| --- | --- | --- |
| Standalone CLI | `0.162.1`；11 組 public help 與 adapter production argv 檢查 | 公開 parser 未發現不相容；不改 CLI executor，不宣稱 start／resume／fork lifecycle 通過。 |
| Bundled CLI | `0.162.0-alpha.17.2`；相同 11 組 help 與 production argv 檢查 | 與 standalone 的 help stdout 完全一致；獨立受測，不能代替 Desktop live 行為。 |
| Desktop application | `26.1007.30912`、build `20156`，來自 ChatGPT desktop app bundle metadata | 專案已有 ChatGPT app 命名與 runtime 能力偵測，不需硬編碼本機 app 路徑。 |
| Desktop registry | `list_projects` schemaVersion 2；`list_threads` schemaVersion 4 | 當次正式唯讀回傳結構可用；只記錄形狀，不保存私人 project／thread 清單。 |
| Desktop sidebar adapter | `update_sidebar_preferences` 只接受 `manual`／`updated_at`；`projects` 是 `chats` 別名 | 修正舊 `priority` 與獨立專案排序指引。兩個別名同時提供須一致；Recents／專案內任務共用排序，不擅自近似使用者要求。 |
| Desktop thread／worktree／automation adapters | 當次 `codex_app` 公開 schema 與各薄層 reference 比對 | 保留 local／worktree 意圖、queued identity、source／host、explicit send、heartbeat／cron 及讀回邊界；未執行 runtime mutation。 |
| Shared subagent／profile preflight | 官方現行文件：子代理繼承 parent sandbox／approvals／provider／MCP | 修正 profile `sandbox_mode` 為技術隔離的錯誤描述；未知 parent 不再產生 custom-profile readiness。 |
| Shared hooks | 官方記載 command 與 `mcp_tool` handlers；`SubagentStart` 的 `continue:false` 仍不能阻擋子代理 | 修正文案；既有同步 command template 不需改動，也不啟用 hook。 |
| Installer／universal plugin | source/package `0.34.0`；正常 generated mirror 同步 | 維持 CLI／Desktop 各自入口及共享依賴，不新增 runtime 功能、不更改 profile TOML 或凍結 digest。 |

當次 schema 是 current-session evidence，並非永久 published stable schema。
原生 Goal、subagent、shell／code-mode 與 Desktop 控制面仍按實際工具偵測；
app-server／bundled executable 不能取代 Desktop 工具，也不作缺失能力的私人
API fallback。SSH、Linux、Windows、TUI 與其他任務的能力未重新驗證。

## 共享 sandbox 證據修正

官方 [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
目前明確說明 custom agent 檔不能覆寫 `sandbox_mode`、`approval_policy`、
`model_provider` 或 `mcp_servers`。因此 profile／receipt 的 `sandbox` 保留為
workflow expectation，`parent_sandbox_mode` 才記錄已觀察的繼承邊界；
`sandbox_non_widening` 只表示保守政策比較，不證明獨立唯讀隔離。

`profile_preflight._sandbox_evidence` 不再從 read-only profile 推定未知 parent
為 `unknown-at-least-read-only`。新選路也拒絕該 sentinel；歷史收據驗證保留
相容性，不改寫舊 bytes。歷史完整性驗證不能代替新派工的當次 preflight。
未知 parent 走已存在且有獨立 class／tier 證據的 fallback，或停在原 human gate；
不降低角色／scope、擴權、啟用第三方模型或改變完成標準。

workspace-write parent 下的 reviewer 仍受唯讀 workflow instructions 約束，
但沒有獨立技術唯讀 sandbox。驗收若要求技術隔離，必須另外驗證唯讀 parent／
公開控制面，否則停止相依操作。保留 profile bytes 不能被解讀成 sandbox
runtime 資格；本次未做寫入探測或宣稱 OS 隔離實測。

官方 [Hooks](https://learn.chatgpt.com/docs/hooks) 記載 `mcp_tool` handler；
現有 command template 保持原狀。Hook 仍是選用 guardrail，不能取代 sandbox、
授權、review、repo completion 或完整 post-merge 攔截。

## 驗證

使用 tracked resolver：Python `3.12.9`、PyYAML `6.0.3`。

- 前置 CLI handoff、native runtime docs、runtime release docs：130 tests 通過。
  Bundled CLI public-help：3 tests 通過。
- 兩入口各 11 組 help：root、exec、exec resume、exec fork、fork、agents、queue、
  doctor、mcp、plugin、app-server；全部 exit 0，stdout 相同。Production argv
  測試使用 disposable config 與 `--help`，不建立 session／JSONL state。
- 修改後 agent profiles、agent routing、loopctl、native runtime docs、runtime
  release docs：245 tests 通過。新增未知 parent 拒絕、已知 parent 保留、fresh
  route 拒 sentinel 與歷史收據可讀測試；相關 fixtures 明確提供 parent facts。
- Generated plugin：158 檔 parity；offline release-state 與 `git diff --check` 通過。
- 資格／資格 CLI、選路 eval、本機模型既有相容性、native runtime 與 release
  文件依賴：91 tests 通過；沒有啟用或增加本機模型功能。
- `validate-repo.sh --skip-unit-tests` 完整離線結構／eval 檢查通過；該模式明確
  略過 embedded unit tests，不當作全套 unit tests 通過。
- 獨立深入審查完成；主代理補查 README 的未知 parent 舊文後完成修正與比例
  重審，沒有未解 findings。Security Diff Scan 完成全部 4 個變更 production
  source 檔，0 findings、0 deferred；之後 README 補文另作安全適用性查核，
  沒有新的安全影響，不擴張 sealed scan 覆蓋宣稱。

安裝相容性測試、hosted CI 與 exact-head gate 另依當前 diff／PR 證據記錄，
不由上列局部 PASS 推定完成。

未執行 live CLI session start／resume／fork、Desktop sidebar／task／worktree／
automation mutation、hook lifecycle、任意 custom provider 或模型資格化。
#242／#251／#293 的上游能力與事件缺口維持各自未解狀態；runtime 更新、help、
schema 或 fixture 成功不證明它們已修復。不存取 private DB/log/session/auth。

## 同一 Issue 的發行評估

依 [release-state contract](../policies/release-state-contract.md)分列：

- **Source/package：** `catalog.yaml`、installer、plugin 一致為 `0.34.0`。
- **Candidate／historical：** `release-notes-v0.34.0.md` 保留 #316 當時準備紀錄，
  #328 已補停止模型新投入的後續決策；不是本案發布計畫，不改寫候選內容。
- **Publication：** 2026-10-14 唯讀核對 latest non-draft/non-prerelease Release
  為 `v0.33.0`，target `ad2e8a0772768b01d6e675a43b23047efc68ea39`；遠端 annotated
  tag dereference 相同，未見 `v0.34.*` tag。Release metadata 使用
  `connector-operation-unavailable` 的窄範圍 `gh` fallback。
- **Active guidance：** 不新增 tracked current-publication 指標或 runtime 完整支援
  宣稱；本案只修正有來源的相容性與證據解讀。

本次共享 preflight 的保守修正有 patch 價值，但**不適合直接發行新的小版本**：
`main` 已含尚未發布的 `0.34.0` 候選與停止新增投入的歷史內容；直接升成
`0.34.1` 或其他版本會把更大的未發布 base-to-head 一併發行，不能當作本案
的局部修正資格。從 `v0.33.0` 做維護分支／backport，或完整重評 main 發布範圍，
是不同的 release objective。本案建議先交付相容性修正，不調整版本、不建立
tag／Release、不安裝或部署；後續選定發布範圍後再走完整 release gate。
