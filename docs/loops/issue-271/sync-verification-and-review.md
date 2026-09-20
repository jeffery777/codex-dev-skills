# Issue #271：第三次同步後壓力觀察

## 結果與範圍

2026-09-20，使用者在[同步準備](filler-sync-preparation.md)交付、完整測試及精確
資源／恢復方案預審後，另行授權一次全新 256 MiB APFS 試驗。執行來源為
`53444093b5ba1d064809583ddee4a7fdd8ce17a6`；18 份消費來源與核准方案摘要
在執行前核對一致，使用 worktree `.venv`、tracked `./scripts/project-python`、
Python 3.12.9／PyYAML 6.0.3。方案摘要與精確資源、原始觀察留本機。

本次只執行一次，累計三次額度均已使用。結果為 **incomplete／os-enospc-only**：
write ENOSPC 後的 `fsync` 成功，但 SQLite update 仍 applied／revision 2，
SQLite errors 為空；沒有 physical SQLite FULL，沒有該失敗後的新確認正常 control。
去識別證據見 [sync-observation.json](sync-observation.json)。前兩次紀錄保持不變。

## 已觀察事實

- 在目標交易前、journal absent 時填充；三種 block size 的 write 均收到 errno 28。
  累計寫入 260,046,848 bytes、251 次 write，低於 256 MiB 上限。
- 完整收到 before_fill／before_sync／after_sync 三階段觀察。同步成功，同步前後
  filler logical／allocated bytes 相等；同步後的可用容量取樣仍大於零。
  這些是瞬間檔案系統觀察，不是容量 reservation、配置唯一性或 APFS 根因證明。
- writer 正常退出、未逾時；保持原 SQL／核心／page quota，max_page_count 仍
  1,048,576、交易前 page_count 12。不能以 page-quota FULL 代替物理 FULL。
- 只截短並同步本次已綁定的 own filler，容量增加且恢復成功。新 reader 的
  `fresh_attempt` 讀回 applied／revision 2 與 writer update proof；`fresh_normal`
  保留舊 add proof 且回 state-unknown。兩者目前 audit／projection 為 revision 2、
  相同 state digest 與 green projection，檔案不變、重播拒絕。
- 正常 detach 後，以唯讀附掛清單及 mount 狀態再次確認該映像沒有附掛；映像仍為
  原身分的 regular file 且在上限內。映像與原始診斷保留，不 repair、不 force detach。

沒有執行第四次、擴容、重掛舊映像、換 filesystem 或修改全域設定。
`fresh_normal` 是既有 add proof 的只讀查證，不是失敗後的新 confirmation control；
本次沒有符合 failed-transaction 的前置條件，因此沒有啟動該 control。

## 方法重評與剩餘門檻

同步缺口已修正，實測也確實執行同步；但本方法仍未讓目標 SQLite 操作失敗。
因此「補同步足以觸發 FULL」不能作為下一次試跑的依據。單一 filler 的 write
ENOSPC 與 SQLite 仍可寫入並存，原因尚未證實；不推定為 APFS reserve、延遲配置、
SQLite 缺陷或資料損壞。

MR-272-01 保持 Needs Human Decision，owner 為 G1 storage／Issue #271 delivery owner。
原驗收仍要求 physical SQLite FULL → 容量恢復後的失敗交易 fresh readback →
新 preview／confirmation 的正常 control。它阻擋整體 Issue 完成及 merge readiness，
不以同步成功、OS ENOSPC、更多 mocks 或單純成功交易的讀回替代。

下一步應先進行唯讀方法分析，找出能說明 filler 與目標交易配置差異的可驗證假設，
再提出有界 workload／故障位置及精確資源、停止條件與恢復方案。這是後續候選方向，
不是第四次試驗方案或授權；不得原樣重跑或持續測到 FULL。若改為拆分／縮小 Issue
驗收，也必須另外明確決定，不能默認移除原 DoD。

## 驗證、審查與版本界線

執行來源的完整 12 shards／1,247 tests、15 個 hosted CI jobs 已通過，
見 [來源驗證 run 35491743151](https://github.com/jeffery777/codex-dev-skills/actions/runs/35491743151)。
這些是該來源的證據，不冒充本次文件提交後的 CI。原始觀察與映像旁的紀錄逐項一致；
另核對實際資源身分、恢復、readback、quota、沒有 control 及正常卸載。

本次追加只更新去識別證據與 active docs，沒有程式、測試、SQL 或可安裝內容變更。
檢查來源指紋後沿用既有程式測試，另執行文件／JSON／連結／隱私檢查、repository
checks、獨立文件審查與對應安全掃描。最終 commit、完整 base-to-head Merge Review
與 GitHub gates 依 [PR #272](https://github.com/jeffery777/codex-dev-skills/pull/272)
最新版本紀錄，不由本文件自行宣告通過。

Issue 保持 open、PR 保持 draft，不發布成功 strict receipt、不合併。不另發版：
source/package 維持 catalog 0.24.7，沒有 candidate、tag 或 Release；default-off、
空 production registry、完整 G1/MG1 未完成與 unqualified 界線不變。
