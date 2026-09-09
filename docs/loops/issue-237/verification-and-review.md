# Issue #237：驗證與審查紀錄

## 範圍

基準 `ea461332da1fb06b188ecf56498c01ca93df74ee`；本地分支
`codex/issue-237-contextual-prompts`。主代理依 project-delivery／implementation-slice
執行；獨立 code/deep/docs reviewer 使用已預檢的 baseline Sol-high 唯讀角色。
路由依 active Desktop callable 能力，未將 CLI scope 的候選資格套用到 Desktop。

本文件保留 pre-commit 驗證與 finding 處置的點時紀錄。最終不可變內容、
複審、安全掃描及平台證據由本 Issue 對應 PR 的 exact-head receipt 讀回核對；
本文件不單獨宣告 merge readiness 或發布完成。

## 驗證

- Python：tracked project-python 選取 Python 3.12.9；PyYAML 6.0.3 可匯入。
- Source/plugin：120 個 generated files 同步；package-reference test 納入
  task-continuation 的 source/plugin/filesystem 政策入口。
- 完整 test shards：12 組、1,135 tests，全部通過。
- Repository offline validation、release-state `0.24.2`、package parity 與
  `git diff --check` 通過。命令見 release note，全部 Python 使用 tracked resolver。
- 十七個語意案例是獨立逐項 review oracle，不作真實模型行為證明。

完整 shards 的初次 snapshot patch SHA-256：
`e7f59b7a0d38d7d6087010008b04e8e978ed4ea864b75d18d4f75af1c243a355`。
後續修正只涉及共用提示詞、delivery 停止條件、案例、文件及 generated copies；
不改 runtime、installer 邏輯、route/profile 或測試程式。重用未受影響的完整
shards，補跑 package tests、offline validation、release-state、parity 及 diff
檢查；語意由獨立複審、安全差異覆核及 PR 後完整 exact-head review 判定。

## 審查與後續

| Finding | 處置 |
| --- | --- |
| CR-MF-001-stop-condition-conflict | 對齊 project-delivery：僅停止仍需決策或驗證不足的相依操作；保留破壞性 safeguards；補 P17。 |
| DOC-MF-002-precommit-release-range-omits-working-tree | plan 分開 pre-commit 的 tag-to-working-tree 與 commit 後 tag-to-HEAD，前者另附新增檔與內容 digest。 |
| PROMPT-SF-003-mid-turn-status-response-underspecified | 明定中途狀態／旁支問題先簡短回答，再續行；明確取消／替換目標才改變續行。 |

初次 Security Diff Scan `cb641cbd-4c08-4d2d-a58e-7d714e274679` 已完成及讀回，
父代理與獨立安全 reviewer 覆蓋 29 個變更檔，無候選或 findings。其 snapshot
digest 為 `61e0c4e5cf7bf170df42dff7bd6acf0e7cd74f1ab20f1fc280aaa98ff5c902bb`；
此結果只綁初次內容，後續修正需覆核，不能由相同 Git HEAD 推定仍有效。
沒有候選，故無 validation／attack-path 工作包可執行。

PR 後保留完整 base-to-head exact-head Merge Review、required CI、已授權
receipt 發布／讀回及 dedicated App；合併前另查當前平台狀態。乾淨內部結果
可續行已授權階段，不能替代這些 gates。

## 限制

無新真實模型 A/B 實驗，不宣稱提升模型品質、速度或成本；agent profiles、
registry、qualification schema 未改。G1 來源承接已合併 #235，仍 default-off，
沒有合格真實 adapter。完整 release range 包含 #231/#235 既有成果；五類版本
角色與 patch 理由見 [plan.md](plan.md)。發布／安裝狀態不能由本文件推定。
