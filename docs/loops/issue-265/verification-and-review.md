# Issue #265：儲存可靠性、量測與限制

本文件與[去識別觀察](controlled-observations.json)只涵蓋新建 synthetic roots。
原始診斷、容量數值與機器身分留在本地；公開摘要使用固定欄位，不含本機路徑、
主機／OS 版本、device／mount／inode、PID、runtime 身分或完整原始命令輸出。
舊 #245／#247／#253 證據保留原貌；本包不更動 production core／空 registry。

## 實證修正

| Finding | Disposition | 修改與證據 |
| --- | --- | --- |
| PF-265-01 / MUST-FIX | Fixed | 原協調器在 filler 恢復 failed/refused/unproven 後仍呼叫 fresh reader，可能對未確認 mount 做遍歷，並覆蓋原失敗理由。現於 reader 前停止；三種結果的負例確認 reader/control 均未啟動。 |
| PF-265-02 / SHOULD-FIX | Fixed | 原診斷只存前四個 argv 及 stderr 前段，遺失配置、stdout 與 timeout 階段。現本地保存完整 argv、階段、exit/timeout、stdout/stderr 各最多 8 KiB 及截斷旗標；create/attach timeout 與 stdout-only 負例可重跑。 |

| CR-265-01 / MUST-FIX | Fixed | 量測 gate 不能只信 coverage flags；現要求完整 payload、有效型別／數值、capacity 順序與實際 acquire/close 時序及 held bracket 一致。reader/control 刪除 connections、lock_intervals、maxima 或破壞區間均 incomplete；開庫前拒絕仍可有空 connections。 |
| CR-265-02 / SHOULD-FIX | Fixed | pragma 明示為 db.connect 返回、fixture fault override 前的快照；公開摘要另列故障注入後 quota。page-quota 正例比對 profile snapshot 與实际縮小 quota，避免把不同時點混為一談。 |
| AR-265-01 / SHOULD-FIX | Fixed | temp 驗證未保存 originating inode；修正文案，明示只驗證當前目錄屬性，私有 trial 不被同權限程序替換是前提，不宣稱 inode 連續性或跨使用者隔離。 |

映像使用文件列出的 GPTSPUD／UDIF 配置與 verbose 診斷。實際寫入前保存新資源
preview，檢查目的 image／mount 不存在；attach 後除了原有獨立 filesystem／容量／
mount 驗證，再確認 image inode 未變及 exact-image attachment 關聯。未知關聯時
不建 filler、不猜測 detach 目標。正常 detach 不使用 force。

## 故障與恢復對照

| 案例 | 新程序讀回與判定 |
| --- | --- |
| 正常 add/update | 最新 update applied，revision 2、green current projection 與 proof 一致；歷史 add 為 unknown 且保留 proof。 |
| Page quota FULL | 真正 SQLite code 13；完整前態、revision 1、blue projection 與原 proof 一致，無部分寫入。失敗 operation 的 ID-only reader 為 unknown，不能當 not-applied。 |
| Missing-path CANTOPEN | 真正 SQLite code 14；獨立的缺路徑對照，前態一致，不代表物理 FULL。 |
| 注入 reply-loss errno 28 | 提交後的例外不改變已提交結果；fresh reader 核對 applied、revision 2 與 proof，不重播。 |
| Before-commit process loss | 非空 journal 保留；reader 在開庫前拒絕 recovery-required，無 DB connections；unknown／incomplete，未做 G2 recovery。 |

quota/CANTOPEN 後，另一 control process 取得新 preview／confirmation，以新 operation
ID 完成更新，再由第三次 fresh reader 核對 revision 2/proof。原 handle 與重建 handle
均拒絕；readback 不呼叫 accept。每次 fresh read 前後完整 fixture 檔案 bytes／identity
比對不變；機器相關數值不公開。這些對照不取代物理容量耗盡或恢復驗收。

## Reader／control 量測

writer、reader、control 各用 originating trial 建立的獨立 sibling temp directory；
reader/control 不新建目錄，檢查預先指定路徑，拒絕 symlink、mode/owner/filesystem
不符。此檢查未保存 originating temp inode；私有 trial 未被同權限程序替換是前提，
不能宣稱 temp inode 連續性或跨使用者隔離。
TMPDIR／SQLITE_TMPDIR 均指向該 trial 目錄；它們是設定與取樣證據，不保證 SQLite
所有暫存都走該目錄。沒有修改 production reader 的 pragma。

每條成功 `db.connect` 返回、fixture fault override 前讀回 temp_store、query_only、journal_mode、
page_size、synchronous、max_page_count。樣本 reader 為 temp_store=0、query_only=1，
writer 為 temp_store=2、query_only=0；0 表示使用 build 預設，不能宣稱 reader 採 MEMORY。
pragma 只描述該連線在該時點的設定；page-quota 的 writer 快照仍是 profile 值，
後續注入會縮小 max_page_count。公開 JSON 的 `writer_quota_after_fault_override`
另列 page_count_before、profile_max_page_count 及 effective_max_page_count；錯誤
分類使用這份注入後證據。不能將不同時點或另一連線的設定互相替代。

| 固定小型 workload | 取樣／最大值 |
| --- | --- |
| 正常 writer，1 item、2 versions、2 proofs | 330 samples；main 61,440 bytes；journal 41,552 bytes；逐筆去重 file aggregate 90,704 bytes。 |
| 正常 fresh reader | 35 samples；main 61,440 bytes；journal/temp/sidecar/other-fd 均取樣到 0。 |
| Quota 後新確認 control | 35 samples；main 61,440 bytes；journal 33,344 bytes；aggregate 82,496 bytes。 |
| 上述 control exclusive lock | 完整 syscall bracket 174,467,416…174,479,125 ns，含 instrumentation。 |

所有角色均取樣 managed/temp 的可用 filesystem capacity 及是否同 filesystem，
原始可用 bytes 僅留本地。持鎖量測從成功 flock syscall 前後到 lock-fd close 前後，
包含 entry/exit inventory；不是只有 context body。reader 的 shared locks 與 control
的 exclusive lock 分別記錄；非空 journal 的拒絕仍有完整 acquire/close 區間。

量測缺失、payload 型別／數值無效、sample error、未閉合／不一致 lock 或 temp 環境
不符不能回 observed；reader/control 各有缺欄位與損壞區間負例。既有 sidecar/unlinked own-fd 正例與 entry/exit 實際鎖競爭測試保留。
fd census 只查 fresh worker 的有限 descriptors metadata，不讀其他程序或內容。

取樣 maxima 不是連續峰值或已證明上界；stat/fstat 加總不是 atomic snapshot。
未覆蓋 connection initialization 內部、兩次取樣間短生命週期或 memory temp bytes。
依 [SQLite temporary files](https://www.sqlite.org/tempfiles.html)，temp_store 不決定
所有 journal 的磁碟行為。完整 J/T/G、maintenance reserve、4 GiB 最壞延遲、power-loss
与 production qualification 仍未完成，不能寫入 qualification registry。

## APFS 支援條件與失敗分類

[Apple 空白映像指引](https://support.apple.com/guide/disk-utility/create-a-disk-image-dskutl11888/mac)
列出 APFS；同頁關於複製 APFS container 的限制屬既有裝置 imaging，不能當空白映像
不受支援的證據。`hdiutil create -help`／`man hdiutil` 列出 APFS、GPTSPUD、UDIF
與 verbose，並說明 -fs 不會自動調整不合適大小。文件未證明特定環境的 256 MiB
試驗一定成功；也不能由採用 GPTSPUD 推論 #253 的 NONE 就是根因。

#253 的已知失敗位置是 image-create、outer attach 未開始；內部 device／根因
未知。新的單次物理觀察另保存在本 Issue；不把 help/dry-run 或合成 PASS 當物理驗收。

[本次物理摘要](physical-observation.json)記錄：headroom 檢查通過，單次 create
於 image framework server 初始化失敗，exit 1、未 timeout。未建立 image，未進入
outer attach／filler／restore；事後唯讀 exact-image attachment 查核為零匹配。
原始診斷足以將本次嘗試分類為執行環境限制，機器細節僅留本地。沒有重試、detach、
repair 或 sandbox 變更；物理 ENOSPC／SQLite FULL／容量釋放後恢復仍 incomplete。
這個新診斷不能取代 #253 缺失的歷史證據，亦不證明舊 NONE 配置有缺陷。

## 重跑與 gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_memory_governance_storage_faults
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault page-quota
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault missing-path-cantopen
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault none
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault reply-loss
./scripts/project-python tests/fixtures/memory-governance/storage_fault_case.py --fault precommit-loss
./scripts/project-python tests/fixtures/memory-governance/enospc_image.py
./scripts/project-python scripts/test-shards.py run-all
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python scripts/sync-plugin-package.py
./scripts/project-python scripts/validate-release-state.py
git diff --check
```

precommit-loss 預期 exit 2/incomplete，CLI 保留 journal 與原始報告；輸出含本機
資訊，只供本地檢查，不能直接貼入公開材料。image --run 是另項精確資源操作，
上述預設命令只是 dry-run。正式 review／CI／receipt 另綁當次 diff/head。

## 發版與剩餘資格

本 diff 僅變更 repository-only fixtures/tests、去識別證據與 active docs，沒有
可安裝核心／技能行為改變，因此不另發版。source/package 依 catalog 為 0.24.5；
candidate preparation 不新增；publication truth 在 bootstrap 另核對 annotated tag
與正式 Release，並不由本文件維護「目前發布版本」；historical release notes 不改。
若後續發現需改 installed source，必須在本 Issue 重評版本及同步 package。

G1 storage owner 在 production qualification 前仍須補 physical FULL/recovery、
完整 temp/J/T/G、最大負載與鎖時間證據；非空 journal 的恢復由另項 G2 契約處理。
本包保持 default-off／空 registry；不以本 Issue 完成宣称完整 G1/MG1。
