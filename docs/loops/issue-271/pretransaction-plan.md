# Issue #271：追加一次交易前實體試驗

## 授權與既有證據

使用者在第一包結果與下一次試驗須新增授權的說明後明確回覆「同意」。
本包據此追加最多一次全新映像試驗；第一包已耗用的次數不重設，兩包合計
最多兩次。既有 before-commit 觀察與未完成審查維持歷史紀錄，不改寫為成功。
沿用同一 Issue／PR #272、分支與單一 implementation writer；接續基準為
`d3ed9385b5e4a5ed918a5b517b48b3c97e442674`，修改前工作樹乾淨，平台 refs 相符。

## 方法與檔案範圍

第一包 filler ENOSPC 發生時 journal 已有 41,552 bytes，SQLite 仍成功提交。
這只能支持較早施加容量壓力的新假設，不能證明 APFS 原因或保證 SQLITE_FULL。
本包只將 test-only physical filler 移至 core 既有 `before-transaction` checkpoint，
位於目標 writer connection／BEGIN 之前；正常 baseline add 已先完成。

- `storage_fault_worker.py`：提前 checkpoint、如實記錄 stage，區分 journal
  absent／bytes null 與 present／實測大小；其他查讀失敗、非 regular 或非空
  journal 均拒絕填充。checkpoint 外的 fixture RuntimeError 保留結構化診斷，
  不將例外推論為交易未提交。
- `enospc_image.py`：dry-run 預覽同步新時點。
- storage-fault tests：以獨立子程序驗證時點、quota 不變、journal 邊界、
  filler／writer-open 失敗後先恢復再 readback，且不啟動 recovery control。
- 新增本包去識別觀察與審查紀錄，直接同步 milestone／roadmap；不修改舊觀察。

不修改 core、SQL、page quota、錯誤分類、production registry 或可安裝內容。
writer-open 前未取得 quota 時保留 origin-unproven；不能為取得成功放寬分類。

## 執行與驗證邊界

先完成負面回歸與獨立 safety review，才進入新增的一次物理試驗。公開受支援的
preflight ready 不代表 create 成功；精確新 root／image／mount 預覽留本地並核對
不存在。沿用 256 MiB APFS GPTSPUD UDIF、至少 1 GiB host headroom 取樣、
外部命令 60 秒、writer 90 秒、fill loop 30 秒、restore／reader／control 各 30 秒。
只操作新 image 與 originating own filler；正常 detach、保留映像與原始證據。

非空 journal、未知身分、恢復未證明均停止相依操作。不得 retry、擴容、repair、
force detach、broad kill、重新附掛舊 image、全域配置修改或跨 host。需要 G2 時
保留 incomplete。單次結果仍不足以宣稱完整 G1/MG1、temp envelope 或最壞延遲。

全程使用本 worktree `.venv` 與 tracked resolver，PATH 包含 `.venv/bin`。
必要 focused tests、全部 shards、checks-only、package parity、release-state、
diff hygiene、獨立 code/deep/docs review 及 Security Diff Scan 後，更新既有 PR；
changed head 必須重新完整 exact-head Merge Review、CI 與平台 gates。
若 physical FULL／失敗後 fresh-authority control 仍缺失，Issue open／PR draft；
只有完整前置通過才沿用既有合併授權。不新增可安裝行為時仍不另發版。
