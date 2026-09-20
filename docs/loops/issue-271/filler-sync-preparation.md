# Issue #271：填充同步與下一次試驗準備

## 本包範圍與新證據

在[兩次未完成觀察](pretransaction-verification-and-review.md)之後，使用者同意
先補足 fixture 的同步與觀測、完成回歸及獨立審查，再準備具體資源／恢復預覽。
**這不是第三次實測授權**，兩次既有試驗額度不重設；本包沒有建立或重新附掛映像。

重新查讀發現：原本 `fill_owned_image` 的 `fsync` 位於 write loop 後、相同 try 內，
write 提早 ENOSPC 會直接進入 except 而跳過同步。以原函式及純記憶體 OS stubs
重現一次 partial write 加三種 block-size ENOSPC，觀察四次 write、零次 fsync。
這證明觀測缺口，不證明 APFS 根因、SQLite 資料損壞或補同步必定得到 FULL。
兩次歷史 OS ENOSPC／SQLite applied／incomplete 紀錄保持不變。

## 最小修正

- 三種既有 block size 與 256 MiB 累計上限不變。預期 write ENOSPC 後，對 originating
  own fd 執行一次 `fsync`；write error 與 sync result／errno 分開。其他 write error、
  零進度或身分漂移直接停止，不強行同步；sync ENOSPC／EIO 亦停止目標 writer。
- 記錄 before_fill／before_sync／after_sync 三個快照，區分 logical bytes、
  allocated bytes 與 available bytes；容量取自 own fd，並重新核對 mount／fd 身分。
  這些是瞬間觀測，不是容量 reservation、唯一實體配置、持久性或 worst-case 證明。
- 同一既有 create worker 使用一次 30 秒 ITIMER_REAL／default SIGALRM，涵蓋 fill、
  sampling、progress emit 與可能阻塞的 sync。主執行緒、default handler、inactive timer、
  未 blocked／pending 都是前提；不解除 signal mask、不替換 handler，不取消他人的 timer。
  正常／例外返回取消本函式 timer；default signal 終止由父程序確認 child 已退出後才 restore。
  外層 writer 的 90 秒 kill/wait 仍保留；不新增可能繼續寫入的 thread／grandchild。
- Python 例外保留 shared partial observation；signal 終止只保留已完整輸出的 frames。
  parser 仍受 MAX_ENVELOPE 限制，只捨棄異常退出時沒有 newline 的最後截斷片段並記錄大小；
  正常退出時未以 newline 結束的尾段或完整 malformed frame 仍拒絕。最多三個有序 progress snapshot
  不參與 completed／FULL 分類，不能宣稱被中斷的 sync 已完成。

沒有 core、SQL、page quota、SQLite error classifier、production registry 或可安裝內容
變更；`--run` 仍須明確使用。sync 失敗／無 completed 仍 incomplete，恢復未證明停止
相依讀回；缺少真實 failed-transaction 前置時不啟動新的 confirmation control。
這套 timeout 機制不是一般 kernel／設備失效下的精確 wall-clock 保證；未確認 child
停止時不能並行 restore。

## 驗證與審查範圍

無物理回歸涵蓋 partial write 後一次 sync、byte cap 而無 ENOSPC、sync 28／EIO、
write EIO／零進度、身分漂移、timer／handler／mask／pending 拒絕及 timer 取消。
真正的訊號與阻塞 I/O 對照只在 fresh subprocess 使用 mock blocking syscall；
一般檔案對照最多寫入 1 KiB，不建立 APFS image 或填滿 host。

另以 fresh child 在 progress frame 中途被 SIGALRM 終止，核對完整 prepared 仍保留、
先 restore 一次再 fresh readback、交易狀態不升格、沒有 control；完整 malformed frame、
異常 progress 次序或過量仍拒絕。正常與其他既有 fault modes 亦需完成原模組回歸。

獨立設計審查的 SYNC-DESIGN-01（inherited blocked/pending signal）與
SYNC-DESIGN-02（截斷 progress frame）均納入實作與回歸；最終修正判定、測試數量、
code/docs review、Security Diff Scan 及 changed-head Merge Review／CI 綁定 PR #272
的最後版本證據，不以本文件代替任何 gate。全程沿用 worktree `.venv`、tracked
`./scripts/project-python`，PATH 前置 `.venv/bin`。

## 下一次實測候選與決策

候選假設只限於：同步後的填充配置與容量觀測，是否不同於前兩次沒有該同步證據的
情境，以及相同 SQLite 操作是否真的遭遇 physical FULL。新增同步並不保證结果。
先完成本包驗證與安全審查，再提供全新且尚不存在的精確 root／image／mount、一次
256 MiB APFS、至少 1 GiB host headroom、各步驟期限、own filler 身分與恢復預覽。
取得使用者新增單次授權後才執行；不自動重試、擴容、換 filesystem、reattach 或 repair。

MR-272-01 仍由 G1 storage／Issue #271 delivery owner 負責，阻擋整體 Issue 完成與
merge readiness：必須取得真實 physical FULL、失敗後容量恢復與 fresh readback、
新 preview／confirmation 正常 control，再完成其餘 gates。若結果仍未達成，保留
incomplete 並重評，不以 OS ENOSPC、quota FULL、sync success 或 mocks 代替。

PR draft／Issue open、default-off／空 production registry／unqualified 保持。
本包只有 repository-only fixtures／tests／文件，不另發版；source/package 由 catalog
保持 0.24.7，不新增 candidate 或 tag／Release，也不改寫歷史 release notes。
