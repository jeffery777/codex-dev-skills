# v0.33.1 維護版相容性證據

追蹤：[Issue #330](https://github.com/jeffery777/codex-dev-skills/issues/330)。
本檔記錄 2026-10-14 的候選範圍、runtime 點時證據與驗證計畫；正式結果以
PR、CI、review／scan、exact-head receipt 與 publication 讀回為準。

## 基底與隔離

已唯讀查證正式 v0.33.0 annotated tag object 為
`95e35eb3d76ef69f75d990b35313ec009ac88cae`，dereferenced commit 與非 draft／
非 prerelease Release target 均為 `ad2e8a0772768b01d6e675a43b23047efc68ea39`。
此為當次 publication 證據，不維護 tracked 最新版本指標。

先讀回重新開啟的 #330 及維護授權，再建立並讀回從該 SHA 起始的遠端
`codex/issue-330-maintenance-v033`（PR base）與
`codex/issue-330-release-v0331`（head），fetch 後核對獨立 worktree 的 branch、
HEAD、upstream 與乾淨度，才開始修改。不同 base 需要隔離工作樹；原 checkout
與其他暫停工作保持原狀，不重置、prune、刪除或同步其分支。

Main 的 PR #331 已交付相容性修正，但 main 含更大的未發布內容。
本維護版只回移該 PR 的直接 hunks，加上 v0.33.0 尚缺的 `orbit` 文件修正；
不複製 main 的完整 Python 模組，不把 0.33 維護分支合回 main，
不納入 0.34 候選、local／第三方模型、Agent Memory 或 Hermes 新投入。
既有 release notes、profile TOML／registry 與 CLI executor bytes 保留。

## 分層證據與必要修正

| 證據面 | 2026-10-14 查證 | 維護版處理與限制 |
| --- | --- | --- |
| Standalone CLI | `0.162.1`；11 組 public help 與 production argv 檢查 | 不改 executor；help 不證明 live lifecycle。 |
| Desktop bundled CLI | `0.162.0-alpha.17.2`；相同 11 組 help stdout 一致 | 獨立受測；不能代替 Desktop mutation。 |
| Desktop app／registry | app `26.1007.30912` build `20156`；`list_projects` schema 2、`list_threads` schema 4 | 當次公開唯讀證據；不保存私人清單或依賴 private internals。 |
| Desktop sidebar | 排序 `manual`／`updated_at`；`projects` 為 `chats` alias；heading 包含 `orbit` | 校正指引及 synthetic 範例；不發送 live mutation。 |
| Shared preflight | Custom agent 繼承 parent sandbox／approvals | 未知 parent 不再推定 readiness；保留原 fallback 與歷史收據。 |
| Shared hooks | 官方文件支援 command／`mcp_tool` handlers | 修正舊文；現有同步 command 範本不改或啟用。 |
| Installer／plugin | 此候選 source/package `0.33.1` | 同步版本與 generated mirrors；不新增安裝內容或部署。 |

Standalone、bundled CLI 的 11 組 help 為 root、exec、exec resume、exec fork、
fork、agents、queue、doctor、mcp、plugin、app-server。這些與 #331 的公開 schema
證據可重用於同日未改的 runtime；維護來源上的 production argv 仍須獨立驗證。
Desktop adapters 以當次 schema 為準，不用 app-server 或私人 API 補缺。

官方 [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
說明 custom agent 檔不能覆寫 `sandbox_mode`、`approval_policy`、`model_provider`
或 `mcp_servers`。Profile／receipt sandbox 僅是 workflow expectation；
`sandbox_non_widening` 只證明保守比較。Writable parent 下的 reviewer 受唯讀
指示約束，但不具獨立技術唯讀 sandbox；若驗收要求技術隔離，需另驗證
read-only parent／公開控制面，否則停止相依操作。

Fresh route 拒絕 `unknown-at-least-read-only`，歷史完整收據仍可驗證；
歷史收據不能取代當次 preflight。官方 [Hooks](https://learn.chatgpt.com/docs/hooks)
不使 hook 成為完整授權、post-merge 攔截或完成保證。

## 驗收與發行界線

驗證採 Python 3.12.9／PyYAML 6.0.3 的 tracked resolver。直接驗證 profiles、
routing、loopctl、native runtime docs、CLI production argv、release-state、
版本與 generated parity；hosted CI 補完整 repository shards。獨立深入審查與
必要安全掃描綁定本維護 diff；PR 建立後另做完整 exact-head Merge Review。
PR base 為維護分支；候選準備時讀回的 ruleset 只涵蓋 main，尚未覆蓋維護
base。合併前須取得對維護 base 適用且生效的 ruleset，以及當次 receipt／
dedicated App 及預期 head merge 檢查；文件與 App success 不取代 branch
protection 的平台讀回，也不能自行豁免 repository 選定的 enforcement profile。

候選準備、publication、安裝與 runtime qualification 分別查證。
只在所有必要 gate 完成後建立、讀回 annotated `v0.33.1` tag 與正式 Release；
本輪不安裝或部署。歷史 notes 原樣保留，不在發布後改寫候選紀錄。
#242／#251／#293、跨平台、live lifecycle 與 OS 隔離未重新資格化。
v0.33.0 的 default-off memory 限制及 D310-V02 Deferred／unknown 仍適用，
不宣稱修復。更多界線見 [候選紀錄](release-notes-v0.33.1.md)。
