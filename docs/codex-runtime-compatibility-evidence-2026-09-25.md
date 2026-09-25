# Codex runtime 相容性證據 — 2026-09-25

追蹤：[Issue #301](https://github.com/jeffery777/codex-dev-skills/issues/301)。
先建立並讀回 Issue，再從遠端 main `d36591afef13019dc25d92989bee8031f733cc2b`
建立及讀回 `codex/issue-301-sidebar-preferences`，核對隔離 worktree 與
pinned Python 後才修改來源。歷史證據及 release notes 保留原貌。

## 本次觀測與調整

| 證據面 | 點時觀測 | 限制 |
| --- | --- | --- |
| Desktop app | `26.917.71314`、build `10954`、`prod` | 原生 updater 回報 up_to_date，僅指該安裝通道。 |
| Bundled CLI | `0.155.0-alpha.16.4` | 與 standalone 分別選定 executable。 |
| Standalone CLI | `0.156.1` | 不推定與 bundled 或 Desktop caller 相同。 |
| Desktop callables | 38 個 `mcp__codex_app__` | current-session evidence，不是 published stable schema。 |
| Registry | `list_projects` schema 2；`list_threads` schema 4 | 成功讀取 sidebarPreferences；未執行偏好 mutation。 |

前置稽核的兩個 CLI 共 11 組 public help 符合現有入口，固定 exec／resume／fork
參數被接受；只有 doctor 相同選項的排列差異。官方
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode) 仍記錄
現有 parser 使用的 JSONL 事件。未發現需改 CLI executor、Desktop 核心任務
接口或共享分層的破壞性差異。

`update_sidebar_preferences` 當次 schema 提供：

- `sorting.chats/projects/pinned`：`manual|priority|updated_at`，共用於 Codex／Work。
- `grouping.mode`：`project|connection|list`，可指定 `surface: codex|work`；省略時
  使用 active surface。
- 省略的偏好保持不變；回應提供 applied preferences，唯讀現況使用 `list_threads`。

本次新增 sidebar 的按需 reference，要求只送指定且需改變的欄位、明確分組
surface、no-op 判定及 fresh readback。排序偏好與項目 reorder 分開，不自動
互相補送；不把專案內任務的 sorting.projects 誤解為專案項目重排。

`list_threads` 當次沒有 surface selector，且 grouping snapshot 帶有自己的
surface。只觀察到一個 surface 時，不能拿來證明另一個的 preflight／結果；
缺少公開觀測就保留手動 fallback。回應未知、讀回不符或未指定欄位漂移，
均回報 unverified，不自動重送、不補償性還原。

共享 delivery／orchestrator 保留選路、ownership、驗證、review 與完成判定；
CLI entrypoint、thread adapter、原有 reorder 與 wrapper retirement 邊界不變。

## 驗證範圍

使用 repository 的 pinned Python 執行 native-runtime 文件契約、runtime
release docs 與 package tests，合計 74 項通過；generated package 141 檔
parity 通過，`validate-repo.sh --skip-unit-tests` 與 `git diff --check` 通過。
Validation 的 skip 模式不代表全套 unit tests 通過；未變更的 CLI executor
及完整 installer suite 沿用前置稽核證據，本次不重跑。
Synthetic 範例涵蓋 sorting-only／grouping-only 最小 payload、共用範圍、no-op、
不相容單一 surface 排序、錯誤 surface、讀回不符及未指定欄位漂移。
文件檢查不是 runtime 攔截器或 live mutation 測試。

前置唯讀稽核另有 196 項相關測試、140 檔 package parity，以及 18 份已安裝
檔案與當時來源一致的結果；它們不代表本次新增 reference 已安裝或本次 diff
已通過全部測試。新增可安裝指引可在後續 release gate 評估，不在本 Issue
修改版本號或宣稱發布。

未執行 live start／resume／fork、Desktop sidebar／task mutation 或 SSH 遠端
caller 驗收；不宣稱所有 surface 可觀察、實際 UI 已重排或歷史 EPERM 已修復。
