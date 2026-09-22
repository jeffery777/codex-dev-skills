# Issue #288：synthetic memory-maintenance 操作入口

Issue #288 讀回 open；在任何 tracked edits 前核對既有已推送分支
`codex/issue-288-memory-maintenance-pilot`，HEAD/upstream 均為
`e711b3568e8228352addd9a2625ec069834fd229`。本任務為唯一 writer。

## 範圍與設計

新增 installed `memory_maintenance_pilot.py`，重用固定 synthetic source/seed helpers、
LocalHost、PinnedGitReader／RepositorySource 及 GovernanceCore。獨立 maintenance
ports 只接受固定 item 的 stop/resume；audit authority provider 不提供 mutation 權限。
先確認建立新 fixture，再由 authority port 顯示完整 preview 並接受精確 digest 字串；
等待後由 core 重驗 TTL、root、前態、來源、容量。每個 handle 只執行一次。

stop 保留版本、移除一般搜尋投影；resume 重驗固定 Git source，不新增 revision。
每步檢查 durable proof／state／projection，再用新 core 讀回及一般 recall 比對。
任何未知、取消、非 applied 或輸出失敗都停止，不自動重試或執行下一個 mutation。
CLI 不接受既有 root／JSON／import／舊 grant，fixture 保留且無清理入口。

## 驗收計畫

- 預設零觸及、取消各階段、兩次獨立確認、stop 查無／resume revision 不變。
- 受控 clock 到期、來源／root／state 漂移、重播與鎖衝突。
- 實際核心交易路徑注入儲存、proof／receipt、readback、輸出與程序中斷；
  新讀回核對一致性，提交不明維持 unknown，僅新接受才允許新操作。
- 聚焦回歸、offline repo／release／package checks、隔離 fresh install／upgrade。
- 獨立 code/data deep review、docs gate、Security Diff Scan，修復後比例複審；
  PR 後完整 base-to-head Merge Review、CI、strict receipt／App。

## 版本與權限

新增可安裝操作能力適合 pre-1.0 minor `0.26.0`。同步 catalog／installer／plugin，
新增 release note；保留 `0.25.0` 歷史 note。2026-09-22 Release 清單讀回最新三筆
為 v0.24.7／v0.24.6／v0.24.5，清單本身不證明特定 tag 不存在；發布 gate 另查精確 tag。
GitHub connector 缺 tag／Release 精確操作時採 `connector-operation-unavailable`
唯讀 gh fallback。候選 PR readiness 不授予 merge、tag／Release、真實安裝或 memory 啟用。

預計 payload：tag/title `v0.26.0`，annotated tag 指向候選 PR 合併後重新核對的 commit，
Release body 為本版 release note、draft=false、prerelease=false。正式 target 尚未產生，
不以 branch head 預填合併 commit。完整 G1、production、物理耗盡及 power-loss 均未 qualified。
