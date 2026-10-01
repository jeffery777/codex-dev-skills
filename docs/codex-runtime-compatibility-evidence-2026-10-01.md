# Codex runtime 相容性證據 — 2026-10-01

追蹤：[Issue #314](https://github.com/jeffery777/codex-dev-skills/issues/314)。
依使用者指示先 fetch 並以 fast-forward 核對 main；同步後 HEAD 為
`ad2e8a0772768b01d6e675a43b23047efc68ea39`。再建立並讀回 Issue，建立、push
及讀回 `codex/issue-314-desktop-orbit-compatibility`，確認 local HEAD 與
upstream 一致、checkout 乾淨後才修改。沿用本專案單一 writer 的 local 偏好。

## 點時觀測與調整範圍

| 證據面 | 本次觀測 | 判定與限制 |
| --- | --- | --- |
| Standalone CLI | `0.159.3` | 既有 start／resume／fork argv 被 public parser 接受。 |
| Desktop app | `26.928.21956`，build `12404` | 版本來自 app bundle metadata；不由版本推定 callable 語意。 |
| Bundled CLI | `0.159.2` | 與 standalone 分別選定 executable、檢查 help；不能代替 Desktop live 驗收。 |
| Desktop registry | `list_projects` schemaVersion 2；`list_threads` schemaVersion 4 | 正式唯讀回傳結構未發現需調整的差異；不保存私人 registry 內容。 |
| Sidebar 排序 | `reorder_sidebar_sections` 接受 `orbit`（Your dot） | 補上技能、synthetic 範例與 native capability 文件的列舉缺口。 |

兩個 CLI 各查核 root、exec、exec resume、exec fork、fork、agents、queue、
doctor、mcp、plugin、app-server，共 11 組 public help，輸出完全一致，沒有
建立 session／JSONL state。官方
[更新紀錄](https://learn.chatgpt.com/docs/changelog) 記錄 CLI steering、
app-server 分頁及模型預設更新；本專案現有入口沒有相依於這些新增選項，
未發現需要改動 executor 或共享編排的證據。

Callable 依當次正式工具描述與 schema 核對；這不是 stable published schema
或 live mutation qualification。`orbit` 只作為該排序操作的 builtin heading，
不當作 custom section ID，不延伸 move、rename 或 delete 權限。全部 custom
IDs 恰好一次、builtin headings 可省略、讀回不可觀察時維持未驗證等條件不變。

CLI session adapter、Desktop task／worktree adapter 與共享 orchestration
維持獨立分層。新增的 worktree archive／restore 能力屬可選擴充，不在本次
實作範圍；工具可見性不授予封存、還原或清理權限。

## 驗證與限制

前置唯讀稽核使用 pinned Python `3.12.9`、PyYAML `6.0.3`。CLI handoff
69 項、bundled CLI public-help 3 項、native runtime 文件 48 項、runtime
release docs 13 項、installer runtime groups 53 項，共 **186 項通過**；
generated package **153 檔 parity**、offline release-state 與 `git diff --check`
通過。這些是前置證據，不能代替修改後驗證。

修改後 native-runtime 文件 48 項與 runtime-release 文件 13 項，共
**61 項通過**；generated package **153 檔 parity** 與 `git diff --check`
通過。`validate-repo.sh --skip-unit-tests` 完整離線檢查通過；skip 模式不代表
全套 unit tests 通過。CLI executor 與 installer 未修改，不重跑前置的 186
項檢查；必要的修改後文件測試已另行執行。獨立文件審查另列於交付回報。

未執行 live start／resume／fork、Desktop sidebar／task／worktree mutation、
CLI TUI 或 SSH caller 驗收。不宣稱既有 process-tracking、sandbox event 或
遠端工具供應問題已修復。文件檢查保護安裝後指引，不是 runtime 攔截器。

## 同一 Issue 的發行評估

此次來源 `catalog.yaml` 為 `0.33.0`，source／installer／plugin 版本一致。
2026-10-01 唯讀核對
[v0.33.0 Release](https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.33.0)
為 `draft=false`、`prerelease=false`，target commit 為
`ad2e8a0772768b01d6e675a43b23047efc68ea39`；本機 annotated tag 的 dereferenced
commit 相同。Release 讀取使用 `connector-operation-unavailable` 分類後的
窄範圍 `gh` fallback；本機 tag 不取代遠端 tag object 的 publication gate
讀回。本段只是評估時的點時紀錄，不是持續更新的 publication 指標。

本次僅補齊 builtin heading 的文件覆蓋，既有排序仍有效，沒有新增公開 mode、
executor 功能或不相容 request schema。**不建議單獨發行新版**，不調整來源
版本、不準備 release candidate、不改寫歷史 release notes。若同一 Issue
後續包含實質相容性修正，再重評 patch release；任何發行仍需依
[release-state contract](../policies/release-state-contract.md) 核對 exact head、
tag／Release 衝突、必要 review 與各自授權。
