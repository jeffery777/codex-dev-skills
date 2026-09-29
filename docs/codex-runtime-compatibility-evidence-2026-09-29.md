# Codex runtime 相容性證據 — 2026-09-29

追蹤：[Issue #306](https://github.com/jeffery777/codex-dev-skills/issues/306)。
先建立並讀回 Issue，再從遠端 main `79bc6eedf6f21f2af9889741ed3208679bec3945`
建立及讀回 `codex/issue-306-runtime-checkout-contracts`；確認 local checkout
乾淨、HEAD 與 upstream 一致後才修改。本次沿用 local，符合本專案單一進行中
話題與單一 writer 的偏好；歷史證據及 release notes 保留原貌。

## 點時觀測與必要修正

| 證據面 | 2026-09-29 觀測 | 判定與限制 |
| --- | --- | --- |
| Standalone CLI | `0.158.0` | 與 bundled CLI 分別選定 executable，未發現需修改 executor 的參數／事件契約差異。 |
| Desktop app | `26.924.22138`，build `11645` | Desktop callable 與 CLI help 分開核對，不從版本推定能力相同。 |
| Bundled CLI | `0.158.0-alpha.2.1` | 公開 help 相容不證明 Desktop task mutation 可用。 |
| `create_thread` | Git／非 Git 專案均預設 local；worktree 要有明確使用者要求且是 Git 專案 | 修正舊指引的 Git 預設 worktree；限制僅適用此 callable。 |
| `create_worktree` | 必填 `allowAsync: true`；省略 ref 使用 remote default branch；可回傳 pending `operationId` | 補上 active worktree 重用、精確來源及 status 完成讀回，不再把起點說成目前 HEAD。 |
| `fork_thread` | conversation history 可包含 interrupted active turn | 移除 Desktop／共享層僅複製已完成回合的保證，要求操作結果與 writer 狀態讀回。 |

Callable 證據來自當次正式暴露的工具描述與 schema，不是 published stable
schema，也不是 live mutation 驗收。兩個 CLI 各檢查 11 組 public help：root、
exec、exec resume、exec fork、fork、agents、queue、doctor、mcp、plugin、
app-server；現有 exec／resume／fork argv 被公開 parser 接受。
官方 [non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)
仍記錄現有 parser 處理的 thread／turn／item／error JSONL 事件；
[CLI 0.158.0 更新紀錄](https://learn.chatgpt.com/docs/changelog#github-release-397962047)
不能單獨證明所有歷史故障或 live continuation 已修復。

## 分層與情境檢查

共享 orchestrator 按使用者／repo 偏好、既有修改、writer、base 與隔離需求選擇
local 或 worktree，偏離偏好時說明原因。Git、新話題或 MIT 授權本身不是建立
worktree 的理由。專案的 local 偏好放在 repo AGENTS；可重用共享技能不假定
所有使用者都是單一維護者。選擇位置不增加新話題、外部寫入或破壞性操作授權。

| 情境 | 契約要求 |
| --- | --- |
| 單一 writer 可安全沿用現有 local | 沿用 checkout；不因新對話本身建立 worktree。 |
| 修改衝突、並行 writer 或不同 base 需要隔離 | 說明偏離偏好的原因，先找可重用 worktree，再依所選操作的授權及 callable 建立。 |
| `create_thread` 需要隔離但欠缺其必要 worktree 意圖 | 準備 handoff、不 dispatch；不暗換操作繞過限制。 |
| 目前任務 `create_worktree` 回 pending | 用同一 `operationId` 查到 completed 與路徑再使用；不重複建立、不猜路徑。 |
| Desktop fork 含中斷回合 | 複製文字不是完成證據；先讀回 Git、操作結果及來源 writer，再決定後續。 |
| Desktop local fresh rollover | saved checkout 已乾淨且符合 checkpoint branch／HEAD、exclusive ownership；目的端先唯讀核對，才取得 writer。 |
| CLI manual fork／native TUI | 依各自 cwd 契約選既有 checkout；不套 Desktop target/environment payload。 |
| CLI non-interactive handoff | 來源可為 local 或 worktree；private clone、clean-source、exact-head 與 integration checks 維持必要。 |

CLI 未發現與 Desktop 相同的強制 worktree 預設。補強入口與按需 references 的
位置選擇說明即可；不修改 executor、request schema、mode 或 retry 行為。
CLI 的已觀測 fork 契約仍保留 CLI 專屬描述，不拿 Desktop 中斷回合語意代換。

## 驗證與未驗證範圍

使用 repository pinned Python `3.12.9`、PyYAML `6.0.3`。前置唯讀稽核共
199 項相關測試通過，涵蓋 CLI handoff、兩個 executable 的 public-help 相容性、
native runtime 文件契約、runtime release docs、installer runtime groups 與
plugin packaging；測試入口名稱更正後通過。這些是前置稽核證據，不代替本次
修改後的文件契約與 package 驗證。

本次修改後 native-runtime／runtime-release／context-continuity 文件與行為
測試 77 項、plugin packaging 16 項，共 **93 項通過**；generated package
**147 檔 parity**、`validate-repo.sh --skip-unit-tests` 及 `git diff --check`
通過。skip 模式不代表全套 unit tests 通過。CLI executor、installer 實作與
release version 未變，不重跑完整 installer suite；既有安全測試證據不擴張為
本次 live runtime 驗收。文件檢查保護可安裝指引，不是 runtime 攔截器。

獨立審查指出維護中的 `examples/runtime-adapter-boundary.md` 仍有兩處舊
worktree 預設指示（D306-R1）；已同步修正並納入同一回歸檢查，避免入口與
範例給出相反建議。

未執行 live start／resume／fork、Desktop task／worktree mutation 或 SSH
caller 驗收；本 Desktop session 不能驗證 CLI TUI 的當次 callable 可用性。
不宣稱歷史 process-tracking 或 sandbox failure event 問題已修復。

## 發行評估

2026-09-29 唯讀核對：本次來源 `catalog.yaml` 為 `0.31.0`；GitHub
[v0.31.0 Release](https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.31.0)
的 `draft=false`、`prerelease=false`，target commit 為
`79bc6eedf6f21f2af9889741ed3208679bec3945`；annotated tag object
`5a8e6aa7df38f323b965dc3978ec76ffd076dbee` 也指向該 commit。
這是評估時的 publication 證據，不是持續更新的「目前已發布版本」指標。

建議本修正通過審查及合併後，單獨準備 **patch `v0.31.1`**，不等待後續功能：
受影響內容是會被安裝、直接指導 agent 呼叫介面的契約；錯誤預設、缺少必填
參數、錯誤起點或 fork 完成假設都可能影響實際操作。此次沒有新增公開 mode、
executor 功能或不相容 request schema，無須因此升為 minor `v0.32.0`。

上述是初次稽核的發行建議，不是發布結果。使用者後續授權同一 Issue 準備
`v0.31.1`、完成必要審查且零剩餘 findings 後發行，再部署及清理本次舊版套件
備份；候選範圍記錄於 [v0.31.1 release notes](release-notes-v0.31.1.md)。
發行仍須依 [release-state contract](../policies/release-state-contract.md)
重新核對版本、exact head、tag／Release 衝突與授權；候選文件不證明發布完成。
