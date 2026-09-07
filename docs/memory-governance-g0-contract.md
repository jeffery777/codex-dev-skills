# MG1 G0：合成契約與拒絕語意

[#225](https://github.com/jeffery777/codex-dev-skills/issues/225) 交付
[#213](https://github.com/jeffery777/codex-dev-skills/issues/213) 的有界離線驗證。
設計來源是 #212／PR #214 的
`e0ffeb4a271961b9b11a279713885f9985da2534`，見
[MG1 里程碑](memory-governance-milestone.md)。本文件是待接受的 G0 契約；
文件、fixture 或 checker 通過都不表示已接受資料契約、啟用記憶或完成 G1／G2。

## 交付與信任邊界

`mg1-g0-synthetic/v0` 是獨立合成格式，不是 M0／M1 的新執行模式。
程式只比較呼叫者提供的 JSON 聲明；沒有資料庫、網路、migration、操作執行、
安裝入口或狀態持久化。`operation_authorized`、`runtime_proven` 及
`write_performed` 永遠為 false。G1／G2 必須另外實作並資格驗證真實儲存與授權。

case 與 caller context 分開輸入。case 不能自行放入 accepted evidence。
context 的 scope、前態與 profile 摘要及 accepted confirmation 集合由合成測試
呼叫者提供；SHA-256 只檢查綁定，不是簽章或身分驗證。
任意人能製作兩個互相一致的合成檔案；因此 conformance 絕不等於真實授權。
未來執行核心須從獨立可信控制面取得身分、來源 eligibility、時鐘、已接受契約、
前態與授權證據，不可把這些 JSON 檔當成授權來源。

本機 scope 只允許單一 principal/root。root 是不透明識別碼，不是可開啟路徑。
item identity 為 `(principal_id, root_id, item_id, identity_epoch)`；跨 root 或世代同名不代表同一資料。
相似摘要或線索不能證明 identity。正文、摘要與線索同屬一個 revision；
摘要與線索不是正文替代品，也不提供新權限或來源正確性保證。

## 精確格式

所有 object 拒絕缺少或額外欄位；未知版本、重複 JSON key、NaN／Infinity、
非整數計數與 bool 冒充整數都拒絕。JSON canonicalization 為 UTF-8、排序 key、
不加空白、保留非 ASCII、禁止非有限數值，摘要為其 SHA-256。
陣列順序屬格式的一部分。所有整數介於 0 與 `2**53 - 1`，個別欄位再收緊。

`synthetic-*` ID 必須符合 `synthetic-[a-z0-9][a-z0-9-]{0,63}`。
body／summary 必須有非空 `synthetic:` 內容。這只是 fixture 標記，**不是 PII／secret
偵測器**；真實或敏感內容不得送入。資料解析與契約拒絕不回顯輸入、正文或路徑。

| 物件 | 精確欄位與約束 |
| --- | --- |
| off case | `contract_version`, `case_id`, `mode: off`；不接受任何 state/context。 |
| 其他 case 共通 | `contract_version`, `case_id`, `mode`, `profile`, `before`, `after`。 |
| maintenance case 額外 | `preview`, `confirmation`, `result`。 |
| audit case 額外 | `inventory`，內含 `item_ids`, `complete`, `reason`, `scanned_count`, `snapshot_digest`。 |
| retention case 額外 | `confirmed_at`；比對顯式接受且仍在窗口內的 proof／marker 裁剪轉換。 |
| continuation case 額外 | `operation_id`, `result`, `confirmed_at`；只處理已有 pending proof 的剩餘階段。 |
| scope | `principal_id`, `root_id`。 |
| state | `scope`, `epoch`, `reject_before`, `items`, `proofs`, `storage`。 |
| item | `item_id`, `identity_epoch`, `erased_at`, `status`, `current_revision`, `indexed_revision`, `versions`。 |
| version | `revision`, `created_at`, `retired_at`, `body`, `summary`, `cues`。 |
| storage | `file_bytes`, `free_bytes`, `reclaimable_bytes`，全部為 bytes。 |
| context | `contract_version`, `scope`, `now`, `before_digest`, `profile_digest`, `accepted_confirmations`, `accepted_retention`, `accepted_continuations`, `capabilities`。 |

`epoch` 與 revision 是正整數。合成時間是非負整數秒，`now` 來自分開提供的
context；不使用作業系統時鐘推定 fixture 有效。真實時間來源尚需 G1 資格驗證。
context 的 `before_digest`、`profile_digest` 必須等於本次完整前態與 profile 摘要。
accepted 集合為不重複的 64 位十六進位摘要，最多 100 個；不是從 case 推導授權。
capabilities 只能含不重複的 `audit`, `item-write`, `erase-content`, `root-maintenance`。

## 有限 profile；沒有產品預設

下列十二個欄位全部必填且為正整數。每次變更 profile 都要重新取得分開的 context
綁定及新 confirmation／retention／continuation acceptance；不能修改 profile 後沿用舊確認。

| 欄位 | 單位與意義 |
| --- | --- |
| `max_items` | root 內 item 數量，包含 erased identity marker。 |
| `max_versions` | 每個 item 的版本數，包含目前版本。 |
| `history_seconds` | update／restore 後歷史版本自 `retired_at` 起的保留年齡上限。 |
| `max_payload_bytes` | 一個完整 version 的 canonical JSON byte 上限。 |
| `max_proofs` | 一般新增／修改後允許的 durable proof 數量上限，包含 pending。 |
| `maintenance_proof_reserve` | 額外保留給 stop／erase／prune／compact 的 proof 名額；總上限是兩者之和。 |
| `proof_seconds` | 已完成 proof 可保留的時間窗口；超過才可顯式裁剪。 |
| `marker_seconds` | erased marker 的最短保留窗口；到期且無保留 proof 引用才可裁剪。 |
| `confirmation_seconds` | 預覽發出到過期的最大秒數，不得大於 proof 窗口。 |
| `max_scan_items` | 一次 audit 可列舉的 item 上限。 |
| `budget_bytes` | 受管理儲存與維護所需空間的總 envelope 上限。 |
| `reserve_bytes` | 成功變更前必須有的外部空間；一般寫入另須在 budget 內保留同額空間。 |

checker 自身另限輸入檔 1 MiB、100 items、20 versions/item、100 proofs、100 scan items；
這些是 G0 測試資源上限，不是已接受的產品容量。單 version 最多 16 個不重複 cue。
fixture 使用的秒數、byte 與數量只供測試；不採用或核准原提案的 10 版／30 日／80%。
profile 的 reserve 必須小於 budget；payload 上限不得超過 budget。

一般 add／update／restore／resume 必須留下 byte 與 proof 預留；達上限就拒絕。
stop／erase-content／prune-history／compact 可以使用預留 proof 名額，且 file_bytes
可以已達 budget；仍須外部工作空間與足以容納 after 控制資料的有界儲存。
全部預留已耗盡或磁碟無工作空間時如實拒絕，audit 保持可讀；不承諾無限寫入。

目前版本的 `retired_at` 為 null；update／restore 將舊 current 的 retired_at 設為 now。
歷史版本的 retired_at 不早於 created_at，且不晚於下一個保留版本的 created_at。
這使久未修改的 current 仍可更新。過期歷史不會自動移除，audit 仍可盤點；
若 update／restore 會保留過期歷史，就先取得精確 `prune-history` 確認。
prune 不要求刪除整個 item，且絕不可刪除 current。G1／G2 仍須實作真實維護。

## 候選、預覽與確認

自然語言只產生未接受候選。G0 不解析自然語言，不能替歧義、來源不足、
「忘掉它」或清理建議選擇破壞性動作。候選經精確化後才成為下列 preview。
首版 maintenance 一次只針對一個 item，compact 則針對一個 root。

preview 精確欄位：

```text
scope, operation_id, nonce, issued_at, expires_at, epoch,
before_digest, profile_digest, operation, item_id, identity_epoch, expected_revision,
next_version, restore_revision, erase_revisions, managed_files,
unmanaged_copies, reclaim_space
```

scope、完整前態、profile 必須與 context 一致。`issued_at <= confirmed_at <= now < expires_at`，
且有效窗口不得超過 profile 上限。等於過期時間即拒絕。epoch 必須等於目前 epoch，
`issued_at >= reject_before`；舊 epoch 或較早時間的請求不能因 proof 已裁剪而重新接受。
相同 `operation_id` 已出現在 durable proof 時拒絕重播；nonce 也納入 preview 摘要。

confirmation 精確為 `principal_id`, `preview_digest`, `confirmed_at`。
principal 必須相符，preview 摘要必須涵蓋上述全部欄位，完整 confirmation 摘要
還須在分開的 `context.accepted_confirmations` 中。改動目標、scope、內容、版本、
維護集合或時間，都使舊確認失效。readback 的未來讀取權限不能由 confirmation 自行推定。

| 操作 | 目標／資料與狀態要求 |
| --- | --- |
| `add` | 新 identity、identity_epoch 等於目前 state epoch、expected revision 為 null、next version 為 revision 1；建立 active/index 1。 |
| `update` | 精確現有 revision，next revision 嚴格加 1，原子替換目前 pointer/index；stopped 保持 stopped。 |
| `stop` | active → stopped；版本保留，index 為 null，不聲稱清除或省空間。 |
| `resume` | stopped → active；重新對準目前 revision index。 |
| `restore` | `restore_revision` 必須仍存在，next version 的正文／摘要／cues 必須與該舊版相同，但 revision 加 1；不復用舊 revision。 |
| `erase-content` | 全部現存版本精確列於排序且無重複的 `erase_revisions`；移除 versions/index，保留 erased identity 與 revision high-water。 |
| `prune-history` | 精確、非空、已存在的歷史 revision 集合；不得包含 current，其餘版本、狀態與 index 不變。 |
| `compact` | item／identity_epoch／expected revision 為 null；不改 items，僅作 root 維護聲明。 |

update／restore 的新 version `created_at` 必須等於 context now。
未使用的 next_version／restore_revision 必須為 null；無關集合必須為空。
除 compact 外的一般操作需要 `item-write`；erase／prune 需要 `erase-content` 與
`root-maintenance`，compact 需要 `root-maintenance`。清除不要求原正文重新符合
可新增 eligibility，也不使原正文變可信；未來仍須確實驗證對象、範圍與權限。

item 的 identity_epoch 必須與 preview 相同；erased identity 不可 add/update/resume/restore。
erased_at 為清除 transaction 的 now；其他狀態為 null。marker 保留時，即使換世代
也不能沿用該 item_id；marker 合法回收後才可用目前 epoch 建立新 identity 與新確認。
既有 item 的 identity_epoch 不隨 root epoch 提升而改寫；舊 identity 無法復活。
同一 root 的其他 items 必須完全不變，既有 item 順序不能任意變動。
inactive／erased 的 indexed_revision 必須為 null；active 必須精確指向目前版本。
版本中的正文／摘要／cues 一起退出使用，不會因舊 cue 保留另一條 active index。

## 清除集合、分段結果與 byte 聲明

這個合成 storage profile 固定把 `main`, `fts-shadow`, `wal`, `journal`, `temp`
全部納入 managed_files。任何缺漏或重複拒絕。實際 backend/journal mode 要如何
對應及處理這些受管理物件，須在 G2 明確資格驗證；不能照搬一串 SQLite 指令。
unmanaged_copies 是最多 16 個不重複的合成不透明外部副本 ID，只揭露已知排除範圍，
不授權碰觸它們，也不聲稱完成其清除。

result 精確為 `transaction`, `sanitization`, `compaction`, `outcome`。

| 階段狀態 | outcome 與必要不變條件 |
| --- | --- |
| transaction failed | `failed`；後續階段 not-requested，不聲稱 after 與 before 不同。 |
| transaction unknown | `state-unknown`；不能增加 durable proof 或宣稱任何持久變更已證實。 |
| transaction succeeded，sanitization pending／failed | `sanitization-pending`；內容投影已清除，compaction 尚未執行。 |
| sanitization succeeded，未要求 compact | `complete`；內容清除完成，但不聲稱磁碟空間回收。 |
| sanitization succeeded，已要求 compact 且 pending／failed | `space-reclaim-pending`；已清除內容不得恢復。 |
| 所有要求階段 succeeded | `complete`；各項合成狀態／數值仍須一致。 |

transaction 只允許 succeeded／failed／unknown；sanitization／compaction 只允許
succeeded／pending／failed／not-requested。不得跳過先行階段或把未要求的維護寫成成功。
G0 的 unknown case 中 before/after 相同，意思是**沒有經證實的差異**，不是證明資料庫
回滾；真正 commit 不確定時 G1／G2 必須先取得新的可信 readback，不能自動重放。

成功 transaction 的 item 投影與新 proof 必須同時出現；failed/unknown 都不能寫入 proof。
pending proof 保留 result 與原先確認的 reclaim_space，不能靠過期裁剪移除。
例如 sanitization pending 且 compaction not-requested，仍可由 reclaim_space=true
判定空間回收尚待執行。pending 時拒絕新的 maintenance，保留 audit、合資格 retention
與 continuation，避免後續操作改動尚在處理的範圍。

continuation 以 operation_id 精確找出 pending proof，並重新檢查 root-maintenance；
erase／prune 另須 erase-content。分開的 context.accepted_continuations 必須含以下摘要：
`before_digest`, `after_digest`, `profile_digest`, `operation_id`, `result`, `confirmed_at` 的 object。
confirmed_at 不早於待續 proof 的 recorded_at 與目前拒絕下限，不晚於 now，
且距今嚴格小於 confirmation_seconds；原交易之前的確認不能用來接受剩餘階段。
它只更新同一 proof 的 result／recorded_at，保留原 preview 摘要、身分與 reclaim_space；
items、epoch、floor 及其他 proof 不變。已 succeeded 階段不得倒退或重新執行，
transaction 固定為原先已確認的 succeeded。完成後相同 continuation 不能再被當成 pending。
這仍只是純合成轉換，不提供重試執行 API，也不能還原已刪全文。
此 checker 對舊請求重播的策略是拒絕，沒有用 `idempotent-replay` 冒充已重新執行。

file_bytes 至少涵蓋 state 除 storage 外的 canonical bytes，包括 current/history、
proof 與 identity markers；reclaimable_bytes 不得超過 file_bytes。
成功變更前 free_bytes 至少等於 reserve；一般 growth 的前後 file_bytes 加 reserve
均不得超過 budget，清理／continuation 僅需 file_bytes 不超過 budget。
compact succeeded 時，回收量只能在 0 與前態 reclaimable_bytes 之間；file 減量、free
增量與 reclaimable 減量必須一致。允許零回收並如實表示；沒有 compact 成功時不能
聲稱 file_bytes 減少；未 compact 時 file 增量須等於 free 減量。

這些是**合成量測聲明的算術一致性**，沒有量測真實磁碟或證明物理殘留已清除。
G2 必須另測 lock、ENOSPC、journal/FTS、主檔與暫存殘留及實際空間；
不承諾 SSD、外部備份、快照、加密或共享主機機密性。

## Proof、有限保留與防重播

proof 精確欄位為 `operation_id`, `preview_digest`, `operation`, `item_id`, `identity_epoch`,
`reclaim_space`, `issued_at`, `recorded_at`, `epoch`, `result`。不允許 body、summary、cues、diff、
old/new value 或任意 extension；root/principal 繼承外層 scope。
不透明 ID／digest 仍可能有推知風險，不宣稱匿名或可公開真實 proof。

maintenance 成功時，after.proofs 必須等於原 proofs 加上精確的新 proof；不能同時
裁剪、改寫其他 proof、提高 floor 或改 scope。總數受一般名額加維護預留限制。

retention 是**顯式接受的合成轉換**：context.accepted_retention 必須含
`before_digest`, `after_digest`, `profile_digest`, `confirmed_at` 的 object 摘要，
並具 root-maintenance capability。confirmed_at 不早於前態 floor、不晚於 now，
且距今嚴格小於 confirmation_seconds。裁剪資格以 confirmed_at 判斷，不能先確認
尚未到期的集合再等待它過期；改 profile 必須取得新的 acceptance。
它只描述資料控制轉換，沒有 timer、背景清理或 CLI 寫入能力。

- after epoch 必須嚴格加 1；reject_before 必須提高且不晚於可信 now。
- 只移除 `confirmed_at - recorded_at > proof_seconds` 的已完成 proof；保留其餘原位。
- 所有被移除 proof 的 issued_at 必須嚴格早於新 floor；pending proof 不得裁剪。
- erased marker 只有在 `confirmed_at - erased_at > marker_seconds` 且無保留 proof 引用該
  item_id／identity_epoch 時移除；其 erased_at 必須嚴格早於新 floor。
- 其餘 items 保持原狀；至少移除一個到期 proof 或 marker，不接受空轉換。
- storage 聲明保持原狀；不聲稱裁剪 proof／marker 就回收檔案空間。
- G1／G2 必須先持久提交拒絕下限，再在同一可驗證交易邊界移除舊 proof。
  G0 僅校驗前後聲明，不能證明真實 crash ordering。

erased markers 保留期間計入 max_items；合資格裁剪與 epoch/floor 提高同一合成轉換。
可循環新增、清除、到期裁剪，再以新 epoch identity 新增；未達期限、缺確認、pending
或無空間時拒絕。跨新舊 root 匯入仍需獨立 migration 設計，不能假定舊 M1 副本已刪除。

## Audit、off 與相容性

audit 需要獨立 context 的 audit capability，before/after 必須完全相同。
inventory 可列舉所有狀態的 item；不重複、不越界且有 max_scan_items 上限。
complete 僅當所列 ID 集合等於前態全體 ID 才能為 true；這是枚舉完整性，
不是來源查核覆蓋率或內容可信度。G0 不做自然語言分類與來源驗證。
snapshot_digest 必須綁定完整 before，scanned_count 必須等於列出數量。
reason 只允許 complete／limit／source-unavailable／corrupt／not-started；
complete reason 與 complete flag 一致，limit 必須達 max_scan_items，not-started 必須為空。
每個案例只描述固定 snapshot；跨快照漂移須重新盤點，不把混合快照包成完整清單。

off case 不含 profile/state，函式不接受 caller context。CLI 只讀使用者顯式
指定的合成 case；即使提供 --context 也不探測、不讀取該路徑。
這證明 checker 的該分支沒有額外 state/context I/O，不代表已證明未來 runtime
memory-off 隔離。audit 亦只比較 JSON，不開啟或修復任何 backend。

本專案 off 不代表原生 Codex Memories 或實驗性 context management 已關閉。
原生歷史／筆記不提供此 checker 的 accepted context，也不能提升為真實操作授權。
G0 的 `unmanaged_copies` 只描述顯式合成清單，不保證外部副本盤點完整；
生產格式的未知狀態、全新上下文及效益對照組限制見
[原生記憶共存邊界](native-memory-coexistence.md)。這些限制不改現有 v0 schema。

所有既有 `loop-memory/v1`、M0 v0、M1 v0 文件與可安裝程式保持原樣。
舊 M1 的 delete 仍為 logical delete；本獨立格式不改 enum、回傳值、資料庫版本、
eligibility 或 authority chain。未知格式不得自動轉換或以 extensions 偷渡。

## 重跑與階段接受

```bash
./scripts/project-python scripts/validate-memory-governance-g0.py \
  tests/fixtures/memory-governance-g0/update.json \
  --context tests/fixtures/memory-governance-g0/update.context.json
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_memory_governance_g0
```

CLI 只讀顯式有界 regular files，透過各層目錄 descriptor 拒絕 symlink 元件；
FIFO／device／directory 不可作輸入。成功回傳 0 與無授權的 JSON，拒絕回傳 1
與固定錯誤碼；argument 用法錯誤由 argparse 回傳 2，可能回顯多餘 CLI 參數，
不屬上述 ContractError 不回顯保證。
路徑保護依賴 POSIX 的 O_DIRECTORY／O_NOFOLLOW／dir_fd；未聲稱 Windows 等價支援。

G0 接受條件：格式／資料與安全審查、正反案例、舊契約相容性、參數處置與測試限制
均經確認。G1 才能實作真實盤點／版本維護，G2 才能實作清除／重試／容量管理，
G3 整合各階段實證；每階段安全與故障測試隨實作交付。
生產參數、真實 storage/authority contract、eligibility/readback、實際原子性與
故障復原仍是後續接受與資格驗證事項。G0 合成格式不自動升為生產儲存 schema。

#213 的既有交付證據、待接受範圍與 G1 前置決定見
[G0 接受資料](loops/issue-213/g0-acceptance.md)。
