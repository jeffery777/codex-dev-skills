# Issue #271：同步後探測與小檔補壓準備

## 來源、假設與授權範圍

[第三次觀察](sync-verification-and-review.md)確認 bulk filler 的 write ENOSPC 與
fsync succeeded，但目標 SQLite 仍 applied，沒有 physical FULL。使用者先要求
研究可行方法，再同意準備有界 fixture、離線驗證及可審查的新資源／恢復方案。
這一包不建立或重新附掛映像，也不重設已用完的三次試驗額度。

已確認的缺口是：原三種 block size 都寫同一 fd，最後同步後沒有再寫入。
目前無法區分同步後同檔可繼續配置，或大檔延伸失敗但其他 inode 仍可配置。
本包提供可區分這兩個假設的固定流程，不能證明 APFS reserve、延遲配置等根因，
也不保證下一次一定得到 physical SQLITE_FULL。

研究對照：

- [SQLite 3.47.1 Unix VFS](https://github.com/sqlite/sqlite/blob/version-3.47.1/src/os_unix.c)
  將 write ENOSPC 對應 FULL；其他 write errno、sync 或 open 失敗可能對應不同錯誤。
- [LTP 滿載測試](https://github.com/linux-test-project/ltp/blob/master/lib/tst_fill_fs.c)
  有 ENOSPC 後同步並縮小寫入再探測的設計；這是 Linux 參考，不是 APFS 成功證據。
- [SQLite journal 文件](https://www.sqlite.org/tempfiles.html)說明 MEMORY temp_store
  不會取消 rollback journal 的磁碟寫入。現有 DELETE／MEMORY 與主檔／journal 觀測保留。
- 頁數限制的 FULL、VFS 注入、AUTOINCREMENT 上限、Linux tmpfs、WAL 增長及 VACUUM
  有各自用途，不能直接替代此 APFS／既有核心交易的物理驗收。單份 payload 仍限 16 KiB。

## 固定補壓與恢復契約

只新增 repository-only helper、fixture、測試及文件，不修改 core、SQL、page quota、
錯誤分類、production registry 或可安裝套件。

1. 在已確認的新 mount 中、managed／SQLite temporary 目錄之外，預先建立三個空檔：
   一個 bulk、兩個 small。fd／inode 不得重複；每檔是本使用者擁有的 0600 regular file，
   nlink=1、與 mount 同裝置，且與 host parent 不同裝置。只傳遞已綁定 fd，不重新按路徑開啟。
2. bulk 保留 1 MiB／64 KiB／4 KiB 的 write；每種尺寸第一次 ENOSPC 即換下一階段。
   同步後，以 4 KiB pwrite 連續延伸 bulk 尾端，最多額外 8 MiB；再依序延伸兩個 small，
   各最多 4 MiB。offset 只依實際寫入量前進，零進度、size 漂移及非 ENOSPC 錯誤均中止。
   pwrite 本身不代表更強壓力，觀測重點是同步後及不同 inode 的配置差異。
3. **全體共用** 256 MiB 累計寫入上限、70,000 次 write/pwrite 上限與同一個 30 秒
   SIGALRM deadline；每階段同步一次，期限包含 metadata 查讀、同步及輸出。沒有
   per-file 額度重設、背景填充或無限重試。既有 writer 90 秒 kill/wait 上限保持。
4. 只有最後 small_2 實際 pwrite 得到 ENOSPC、全部同步與觀察完成後，才交給唯一一次
   目標交易。若只達 total/stage/write/time 預算就保持 incomplete；不能借 bulk 的
   ENOSPC 旗標啟動目標。這個前提不是全域容量耗盡或目標 FULL 的證明。
5. 最多九個有序 progress frames：原三個快照，加 tail／small_1／small_2 各自同步前後。
   記錄每檔 logical／allocated bytes、可用容量、每階段 offset／短寫次數／實寫量／errno／
   sync。短寫採計數，不保存逐筆無界清單；整個 worker 輸出仍受 256 KiB envelope 限制。
   異常退出仍只捨棄最後未完成 frame，保留先前 prepared 及完整快照。
6. 所有 filler fd 都從 SQLite 檔案占用統計排除，壓力持續至 writer 已確認退出。
   之後一個最多 30 秒的 restore worker 依序截短／同步全部已綁定 filler；某檔失敗不
   妨礙其餘身分仍安全的檔案恢復。逐檔結果、最終零 size／allocated 及整組容量增加都需
   核對，不能要求每個極小檔都獨自造成可見容量增加。任一失敗或未證明仍禁止讀回與 control。
7. 第 2／3 檔建立失敗時只恢復已核實子集；已開啟但身分未核實的 fd 只關閉，不截短。
   partial pool 不進入目標交易。維持正常 detach、保留映像及原始證據；不修復 journal、
   force detach、清理舊映像或操作既有 volume。

## 驗證與審查

離線案例使用幾 KiB 的 test-owned 一般檔案及明示的 syscall／mount stubs，沒有
APFS create／attach 或真正滿碟。涵蓋短寫／EOF、各層預算、最後階段 ENOSPC 來源、
write/sync/size/identity 失敗、所有 fd 的傳遞與統計排除、完整輸出大小、partial pool
建立及逐檔恢復失敗。既有 timer 中止、截斷輸出、page-quota FULL、CANTOPEN、
reply loss、非空 journal 拒絕與 fresh read/control 回歸保持。

全程使用 worktree venv、tracked `scripts/project-python`、Python 3.12.9／PyYAML 6.0.3。
正式交付需 focused tests、完整 shards、checks-only、package parity、release-state、
獨立 deep/code/docs review、Security Diff Scan，以及新 head 的完整 Merge Review／CI。
測試及 gate 結果綁定 PR #272 最終版本紀錄，不以此準備文件宣告全部通過。

## 下一次精確方案與完成邊界

完成準備與審查後，本機預覽須列出尚不存在的單一 root／image／mount、三個 filler、
精確建立命令、來源 HEAD／所有消費來源摘要、單次 marker、各預算及恢復流程。
取得使用者對該精確方案的新增單次授權才可實測，不自動開始第四次。

驗收仍為：目標 physical SQLite FULL → writer 退出 → own pool 容量恢復 →
失敗交易的新程序讀回 → 新 preview／confirmation 正常 control → 正常卸載。
若結果仍 applied、CANTOPEN／IOERR 或非空 journal，保留原分類及 incomplete；
非空 journal 需要 G2，不新增 repair。不得以 OS ENOSPC、pressure_ready、CI 或 mocks
替代物理證據，亦不無限追加試驗。

MR-272-01 仍為 Needs Human Decision，owner 為 G1 storage／Issue #271 delivery owner。
它阻擋完整 Issue／merge readiness；本包只交付候選方法準備。Issue open／PR draft、
default-off／空 production registry／unqualified 保持。不另發版：沒有可安裝改動，
source/package 仍由 catalog 0.24.7 定義，沒有新增 candidate、tag 或 Release。
