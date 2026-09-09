# MG1 G1 單專案管理核心第一切片

此 reference 對應 Issue #235；它是尚未完成 production qualification 的開發核心，
不是新的自然語言記憶技能、已啟用 backend 或完整 MG1。production adapter registry
是不可變空映射。不得因 import、合成 port 回傳 true、SQLite 測試或本文件而啟用真實記憶。

## 邊界與介面

- `memory_governance_contract.py`：嚴格 content/profile 與 G1 subset 的
  `g1_preview`、`confirmation`、`g1_proof`、`g1_readback` validators。
  已接受 v1 operation enum 保留 G2 名稱；G1 subset 對它們回 `capability-unavailable`。
  純 schema 一致性不證明來源、敏感性、人類確認或執行。
- `memory_governance_host.py`：host 擁有的 root/source/clock/confirmation/readback
  protocols 與空 `PRODUCTION_ADAPTERS`。沒有資料驅動的 registration 或 import-path。
- `memory_governance_storage.py`：core 內部的嚴格新庫、檔案 identity、協作鎖、
  SQLite connection、串流 logical digest、版本／projection／proof 一致性機制。
- `memory_governance_core.py`：預設 `enabled=False`；`initialize`、`audit`、
  `preview`、`authorize`、`execute`、`readback` 與人工 exact-cue `recall`。
  呼叫端只能提議 candidate，不能提供自己的 confirmation 當授權。
- `governancectl.py`：預設 off；`--enabled audit` 因缺合格 adapter 明確 unavailable。
  `--enabled proposal` 只讀有界 stdin 的 `{scope, profile, candidate}`，回 shape-only
  `proposal-only`，來源／敏感性仍 unavailable；不產生可執行 `mg1-preview/v1`。
  不接受 root/path、adapter import、confirmation 檔案或 mutation flags。

以上為 additive、未 qualified 的 G1 程式介面；既有 M0/M1/V2b 與 M1 logical delete
沒有變更。沒有 migration、repair、erase/prune/purge/compact/retention/recovery、
跨儲存管理、全域 backend、native dual-write、自動 recall/write、背景服務或外部 provider。

## 資料與可信輸入

所有 JSON 拒絕缺漏／額外欄位、重複鍵、float/nonfinite、surrogate、bool-as-integer、
超範圍整數，以及超出編碼／深度／節點上限的輸入。完整 version 上限 16 KiB，
包括 provenance、procedure、validation；proof 2 KiB、preview/readback 256 KiB、
confirmation 4 KiB。內容保持 advisory data，不能提升為指令或取得額外讀取範圍。

十二欄 profile 保留已接受的 10,000 items、10 versions、32,768 一般 proofs、
1,024 maintenance reserve、30 日歷史／proof／marker 門檻、300 秒確認及 256 筆分頁。
容量 preset 是 256 MiB／1 GiB／4 GiB，工作上限各為 `5D/4`；完整 profile 在 root
建立時固定。首切片不裁剪歷史；超過版本／proof／容量上限就拒寫，不自動刪除。
`stop` 可使用已接受的 maintenance proof reserve；其餘 G1 mutation 不可。

RootBinding 由可信 host 保有 canonical scope/profile bytes、實體 root 與 owner-only
目錄／主檔／協作鎖的 device/inode。root metadata 綁 `mg1-managed-content/v1`、
完整 scope、epoch/reject_before；schema fingerprint 來自固定 DDL。新的程式或資料
格式不可自動採納現存 SQLite/M1 庫。source port 必須獨立驗完整 version/provenance、
來源 revision、適用性、撤銷、敏感性與 policy，不能只回候選自述的 eligible。

Host 另須以目前 SQLite source ID、compile options、Python/OS、固定 schema/SQL、
profile、adapter 與 filesystem/temp 範圍核對 qualification，從實測前態重算 J/T/G。
`qualification_id` 或 runtime 指紋相同仍不是 peak/維護空間的證明。根目錄檔案的
實際 stat/hash、可用空間與 `ceil((J+T+G)/4096)*4096` 准入條件由 core 再比對；
host 須扣除其承諾的並行工作預算。此首切片尚無任何 production 資格記錄。

## 操作、原子性與讀回

新增／修改／恢復版本把完整 version、current pointer、active-only summary/cue
投影與 proof 放在同一交易。停止項目没有一般投影；修改或 restore stopped item
保持 stopped。resume 重驗目前版本來源，不新增 revision。restore 產生更大 revision，
精確保留來源語意與 provenance identity/order，重新驗證並更換 evidence ID／human token。
cue 採 NFC/casefold/strip、最多 16 個，普通 SQL 相等 AND 查詢且依 item ID 排序；
不使用 FTS、全文／模糊／語意搜尋，舊 cue 不會從歷史版本重新命中。

preview 的完整 bytes、nonce、scope、前態／後態 digest、來源、檔案／容量、外部副本
coverage 與有效期限一起確認。`ExecutionHandle` 只在同一 core/process RAM 存在，
只消耗一次；raw JSON、複製物件、程序重開與過期均不能恢復接受權限。`cancel` 只
丟棄 RAM。確認後 source/state/files/profile/budget/coverage 漂移須新預覽。

新庫固定 DELETE journal、EXTRA sync、4096-byte pages、INCREMENTAL auto-vacuum、
secure_delete=ON、temp_store=MEMORY、foreign_keys=ON、trusted_schema=OFF。
初始化及每個 writer 設定後讀回；audit 使用真正 `mode=ro&cache=private`，不修改
持久 pragma、不建立缺少的 lock。未知檔案、WAL/SHM、非 regular 或 symlink 拒絕。
非空 journal 在開 DB 前回 recovery-required；readback 保持 state-unknown，不偷偷復原。

writer 持 exclusive root lock 至獨立 readback 完成。新唯讀 connection 重算完整
logical state、current projection、版本／proof 鏈與當次 proof；逐筆 proof replay
item revision/status 及當時 projection，再量測檔案及 source。
state digest 不含 proof、檔案布局或自身摘要，避免循環。例外不能推定未提交：
有匹配 proof/後態才 applied；無 proof 且完整前態匹配才 not-applied；其餘 unknown。
較晚合法操作使全庫狀態前進時，早先 readback 可回 unknown，不能重播原 mutation。
來源在 commit 後失效回 committed-but-not-adoptable；後態容量無法證明保留 proof、
回 committed-capacity-unproven。後續操作仍需重新量測及資格准入。
此容量結果與已證明完整／未超限的後態互斥；外部副本觀察失敗回 state-unknown，
保留 proof。只有提供原始 preview 並核對 fresh external-copy 集合相符才能回 applied；
只有 operation ID／preview digest 時無法還原原集合，回 proof／state-unknown。
caller 的錯誤 digest 回 readback-binding，不把請求不匹配說成持久 proof 已損壞。

## 盤點與限制

`audit()` 返回必須關閉的 context manager。每頁最多 256 項、整次最多 40 頁／
10,000 項；cursor 綁仍存活的 connection、snapshot、process 與期限，不接受 offset。
持 shared lock 期間 writer 立即 busy，不靠新 snapshot 拼接「完整」結果。
item 列舉完整性與每頁 source coverage 分開；source 不可採用時遮蔽 summary，
不寫回 stored status。一般查詢結果受數量／輸出 bytes 上限約束，超出明列 incomplete。

合成 tests 在隔離 test-owned roots 注入 host；來源批准、confirmation、qualification
均為 synthetic。subprocess interruption 只證明所測 SQLite/process 邊界，不證明
power-loss、真實 ENOSPC、temp peak、維護預留、4 GiB 最壞 latency、共享主機隔離
或人類授權 adapter。G2/G3 仍須獨立完成上述對應資格；未完成前不開放真實入口。

原生記憶、對話、匯出與備份是外部副本，coverage unknown 不等於沒有副本。
本專案 memory-off 只表示這些管理核心操作不碰本專案 root／backend；不聲稱
Codex 原生記憶或 context management 已關閉。不得把本 reference 用作私有資料存取授權。
