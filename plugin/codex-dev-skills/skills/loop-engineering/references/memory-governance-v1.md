# MG1 G1 單專案管理核心與本機組合介面

此 reference 對應 Issue #235／#245／#247；它是尚未完成 production qualification 的開發核心，
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
- `memory_governance_local.py`：POSIX 本機 UTC／monotonic／process clock、單 root
  host-owned RAM registry、初始化後獨立 identity readback 與 LocalHost port 組合。
  RepositorySource 每次重讀完整 repo-artifact、核對 scope/revision/path/SHA-256；
  每個 artifact 最多 64 KiB，沿用最多 8 筆 provenance。不快取或自行授予 eligibility。
  reader 必須在 I/O 前限制範圍、bytes 與時間，source reviewer 另驗支持／敏感性。
  缺 authority／qualification 就拒絕；source 缺失仍可依 G0 做精確 stop。
  沒有通用 Git reader、human-decision attestation、production factory 或持久 registry。
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
目錄／主檔／協作鎖的 device/inode。新建 synthetic root metadata 綁 `mg1-managed-content/v2`、
完整 scope、epoch/reject_before；schema fingerprint 綁固定 DDL 及 proof-v2 家族。新的程式或資料
格式不可自動採納現存 SQLite/M1 庫。source port 必須獨立驗完整 version/provenance、
來源 revision、適用性、撤銷、敏感性與 policy，不能只回候選自述的 eligible。

Host 另須以目前 SQLite source ID、compile options、Python/OS、固定 schema/SQL、
profile、adapter 與 filesystem/temp 範圍核對 qualification，從實測前態重算 J/T/G。
`qualification_id` 或 runtime 指紋相同仍不是 peak/維護空間的證明。根目錄檔案的
實際 stat/hash、可用空間與 `ceil((J+T+G)/4096)*4096` 准入條件由 core 再比對；
host 須扣除其承諾的並行工作預算。兩個切片均尚無任何 production 資格記錄。

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
item revision/status 及當時 projection，還原當時 current version 尚未退休的摘要，
並逐步重算完整 logical after-state digest；相鄰 proof 串接一致本身不算完整性證據。
restore proof 另比對指定 retained source 的語意／來源與新 validation，所有 proof
時間均不得早於對應版本的 validation.verified_at，不能只靠相鄰時間遞增自證。
readback 將固定 schema/G1-only binding 內 snapshot 的持久契約失敗統一回
integrity-failed，包含不相容的 epoch／G2 rows；不提供向前相容讀取。host、clock、
外部副本與 I/O 的未知狀態仍分開處理，不以資料錯誤碼清單代替此驗證邊界。
重播只保存 item／version digest descriptors，不保留全庫版本原文；每筆 proof
仍需雜湊當時完整 item 集合，其 CPU 成本隨 proof 數乘 item 數成長，最大 profile
的延遲資格尚未通過。完成重播後再量測檔案及 source。
state digest 不含 proof、檔案布局或自身摘要，避免循環。例外不能推定未提交：
有匹配 proof/後態才 applied；無 proof 且完整前態匹配才 not-applied；其餘 unknown。
較晚合法操作使全庫狀態前進時，早先 readback 可回 unknown，不能重播原 mutation。
來源在 commit 後失效回 committed-but-not-adoptable；後態容量無法證明保留 proof、
回 committed-capacity-unproven。後續操作仍需重新量測及資格准入。
此容量結果與已證明完整／未超限的後態互斥；外部副本觀察失敗回 state-unknown，
保留 proof。#247 新增 `mg1-operation-proof/v2` 的固定 `readback_basis`：scope digest、
host 實體 binding digest、原副本 coverage/集合 digest、原觀察時間與
`recorded_at + proof_seconds` 的讀回期限。basis 與原 proof 同交易／同名額／同保留期，
總 proof 仍最多 2 KiB，不保存原 preview、外部副本 ID 清單或另一份內容。
`mg1-readback/v2` 在新程序取得 fresh authority、驗明受信任庫的最新 proof／完整後態／
來源／容量後，重算 fresh 副本 commitment；相符且未到期才可回 applied。
只有 ID/digest 的 caller 不提供 basis 或 proof，亦不能用 preview 補齊損壞的 v2 proof。
過期、實體 binding 或副本漂移、後續合法提交保留 proof／state-unknown；
即使 stop/resume 往返得到相同 state digest，也不能將舊 operation 再判為 applied。
proof/basis 格式損壞回 integrity-failed，readback 不寫檔、不修復、不延長期限。
原 v1 純 validators 保留，v1 applied 仍需原 preview；core 拒絕 v1 root／proof，
不 migration、混用或自動採納。production proposal/G0/M1 格式不變。
proof payload 上界仍為 33,792 × 2,048 bytes，頁面／索引／J/T/G 另計；
新 fingerprint 必須重新取得 storage qualification，舊觀察不能自動沿用。
caller 的錯誤 digest 回 readback-binding，不把請求不匹配說成持久 proof 已損壞。

## 盤點與限制

`audit()` 返回必須關閉的 context manager。每頁最多 256 項、整次最多 40 頁／
10,000 項；cursor 綁仍存活的 connection、snapshot、process 與期限，不接受 offset。
持 shared lock 期間 writer 立即 busy，不靠新 snapshot 拼接「完整」結果。
item 列舉完整性與每頁 source coverage 分開；source 不可採用時遮蔽 summary，
不寫回 stored status。一般查詢結果受數量／輸出 bytes 上限約束，超出明列 incomplete。

合成 tests 在隔離 test-owned roots 注入 host；來源批准、confirmation、qualification
均為 synthetic。#245 的 repository-only runner 記錄小型 workload 的檔案取樣及
鎖定時間，不能把觀測最大值視為 J/T/G 上界；temp=0 只涵蓋該 test-owned 目錄，
外部或 unnamed temp 覆蓋仍 unknown。實際 APFS image 已觀察 filler ENOSPC，
SQLite 則為 CANTOPEN／not-applied；truncate filler 失敗但正常 detach 成功，
實驗仍 incomplete。另有 test-only page quota 觸發 SQLITE_FULL，不能混稱物理磁碟滿。
subprocess interruption 只證明所測 SQLite/process 邊界。沒有 power-loss、完整 temp、
maintenance reserve、4 GiB 最壞 latency、共享主機隔離或人類授權 adapter 資格。
G2/G3 仍須獨立完成上述對應資格；未完成前不開放真實入口。

#253 的 repository-only storage fixtures 補上 fresh-process 故障對照與完整 flock
持有區間的 syscall bracketing，並取樣 named sidecars／temp 及測試子程序的 bounded
fd metadata。數值仍限小型 workload；取樣間隙、記憶體 temp 與完整 J/T/G 上界未證明。
新 APFS 嘗試在 image-create 階段失敗，沒有新的物理 ENOSPC／SQLite FULL 恢復證據。
非空 journal 的新程序讀回維持 unknown／recovery-required，不自行 repair。

原生記憶、對話、匯出與備份是外部副本，coverage unknown 不等於沒有副本。
本專案 memory-off 只表示這些管理核心操作不碰本專案 root／backend；不聲稱
Codex 原生記憶或 context management 已關閉。不得把本 reference 用作私有資料存取授權。
