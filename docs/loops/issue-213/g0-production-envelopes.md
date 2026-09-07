# G0 production envelope 提案

本文件補充 [#213 生產契約](g0-production-proposal.md)。以下是已接受的設計格式，
不是已安裝的 API；合成 checker 只檢查列出的設計例，不能認證 host 或 backend。

## 編碼與共用型別

`C(x)` 是 UTF-8 JSON，鍵排序、無額外空白、`ensure_ascii=false`、拒絕重複鍵、
非有限數字、surrogate、bool 作整數、缺漏與額外欄位。`H(x)=SHA256(C(x))`。
ID 為 36 字元小寫 UUID；digest 為 64 個小寫 hex；時間／epoch／revision 為
`0..2^53-1` 整數。`null` 只在明列處允許。opaque ID 為 1–64 ASCII 字元，
符合 `[A-Za-z0-9][-A-Za-z0-9._:]{0,63}`；
不得使用原文、路徑或可辨識個人的名稱。

`scope` 的精確欄位是 `principal_id, root_id, repository_id, schema_fingerprint,
profile_digest, policy_fingerprint`。前兩項為 UUID；repository_id 為 opaque ID；
其餘為 digest。每個 preview、confirmation、readback 均攜帶完整 scope 並逐欄比對。
相同 item UUID 位於另一 root 或既有 M1 庫，仍是不同目標。

profile digest 只取 [profile JSON](g0-production-profile.json)的十二欄 `profile`
object：`H(profile)`；不含 status、profile_id、model 或 workload 估算。
policy fingerprint 是 `H({policy_id, prohibited, unknown_action, redaction})`：
policy_id 固定 `mg1-content-safety/v1`；prohibited 是排序、無重複的
`credentials, pii, private-paths, raw-chats, raw-logs, raw-sessions, restricted-data,
secrets, unredacted-config` 字串陣列；unknown_action 固定 `reject`，redaction 固定
`new-candidate-and-preview`。變更 policy 要新 fingerprint、重新驗證與新確認。

## 狀態與 digest material

logical state 的精確欄位是 `scope, epoch, reject_before, items`。items 依 item_id
排序、最多 profile.max_items（預設 10,000）筆；每筆為 `item_id, identity_epoch, status, current_revision,
revision_high_water, erased_at, versions, projection_digest`。前六欄型別沿用主契約，
current_revision 為整數或 erased 時 null，erased_at 為 UTC 秒或 null。
versions 依 revision 排序、最多 10 筆，各為 `{revision, version_digest}`，
version_digest 是**完整 stored version** 的 H，包含 validation 與生命週期時間。
erased item 無 versions；stopped/erased 無一般投影，projection_digest 為 `H([])`。
active 投影按 normalized cue 排序，每列 `{cue, summary, revision}`，digest 為 H(列陣列)。

restore 必須逐欄複製 retained source 的 `kind, body, summary, cues, applicability,
procedure`，以及 provenance 各來源的 `source_id, kind, reference, source_revision,
source_digest`（包含順序）。只重新產生更大的 revision、created_at、retired_at=null、
validation 及 human attestation；repo-artifact attestation 仍為 null。新驗證覆蓋同一
語意內容與來源 revision；來源失效就拒絕。改語意或換來源須走 update，不修改來源版本。
restore 的 validation.evidence_id 必須不同於來源版本；每個 human attestation 的
binding_token 也必須重新產生。accepted_at 表示本次 host 對 candidate 來源重新接受／
發證時間，不改寫原始決策身份，並滿足
`candidate.created_at <= accepted_at <= candidate.validation.verified_at <= preview.issued_at`，
允許同秒。新 token 與時間／digest 自洽仍不能取代合格 host 的認證。

`state_digest=H(logical_state)` 不包含 proof table、當次 proof、當次讀取觀察時間、
host RAM handle、page layout 或檔案大小。proof 的 before_digest／after_digest
因此沒有自我雜湊循環。proof 必須另按操作 ID、完整 binding 與實際集合讀回，
不能因 state digest 正確就略過。retention 另比對 proof/marker 的精確刪除集合。

`file_snapshot` 為最多 32 筆 `{file_id, role, bytes, sha256}`，依 file_id 排序。
file_id 是核准 root registry 的 opaque ID，不接受 caller 路徑；role 為
main/journal/temp/coordination-lock。bytes 為整數，sha256 是對已核准 regular file
的實際內容摘要。集合未知或無法有界讀取時不形成可執行 maintenance preview。

## 外部副本與預覽

`external_copies` 精確欄位為 `coverage, observed_at, copies`；coverage 為
complete/partial/unknown，copies 最多 32 筆、依 copy_id 排序，每筆為
`{copy_id, kind, observation}`。copy_id 為 opaque ID，kind 為
native-memory/export/backup/host-history/other；observation 為 known-present/unknown。
不保存外部原文或路徑，不自動存取／刪除副本。只有 host 的有界已核准 inventory
才能回 complete；空清單不能推出 complete。未知副本範圍不阻止明確限定的 managed
清除，但確認畫面必須揭露 unknown/partial，結果不得宣稱全域清除。

preview 家族 `mg1-preview/v1`，完整 C(preview) 最多 256 KiB：

| 精確欄位 | 型別／規則 |
| --- | --- |
| contract_version | 固定 `mg1-preview/v1`。 |
| scope | 上述完整 scope。 |
| operation_id, nonce | 各一個新 UUID。 |
| operation | add/update/restore/stop/resume/erase/prune/compact/retention/recovery/continue-maintenance。 |
| item_id | item 操作為 UUID；compact/retention/recovery 為 null；continuation 沿原目標。 |
| acceptance_epoch, issued_at, expires_at | 整數；`0 < expires_at-issued_at <= 300`。 |
| before | `{kind, digest}`；kind 為 logical-state 或 recovery-file-snapshot，digest 分別為 H(logical_state) 或 H(file_snapshot)。 |
| expected_after_digest | digest；僅 recovery 可為 null，表示核准復原後完整性檢查，不預先宣稱內容結果。 |
| candidate | add/update/restore 為完整新 version；其餘 null。時間與來源觀察於 preview 固定，執行不偷偷換新版本 bytes。 |
| target_revisions | 最多 10 個排序、無重複正整數；prune 必須非空且不含 current，erase 為該 item 全部保留版本；restore 精確一個仍保留的來源 revision；其他空陣列。 |
| target_proofs, target_markers | 每批各最多 128 個 `{id, digest}`，排序且無重複；僅 retention 非空，不能裁剪 pending 或仍必要引用的紀錄。 |
| managed_files | 所有 mutation 的實測前態 file_snapshot，須有 main 且非空；非檔案維護也不能略過容量盤點。 |
| storage | 下述實測前態 storage object；不是 workload 模型估算。 |
| external_copies | 上述 envelope；清除範圍外的觀察與不確定性一起受 preview digest 綁定。 |
| phases | 精確 `{content, sanitization, space_reclaim}`，各為 requested/not-requested，遵守下方 operation 矩陣；erase/prune 不合併空間回收。 |
| authority | 排序、無重複的 capability 陣列；值只可為 readback/content-write/erase-content/root-maintenance。所有 mutation 都需 readback；涉及全庫檔案的階段另需 root-maintenance。 |
| continuation | null，或 `{operation_id, proof_digest, remaining_phases}`；remaining_phases 是 sanitization/space_reclaim 的非空無重複陣列，必須與原 pending proof 相符。 |
| compact | compact 的 `{requested_pages, page_size, freelist_pages_before}`；其他 null，continuation 由 parent witness 繼承。page_size=4096；`1 <= requested_pages <= freelist_pages_before <= data_limit_bytes / 4096`。 |

下列矩陣為精確規則；capabilities 不得多給或漏給。R=readback、W=content-write、
E=erase-content、M=root-maintenance。phases 依序為 content/sanitization/space_reclaim，
1=requested、0=not-requested。除 recovery 的 file-snapshot 外，before 均為 logical-state。

| operation | item / candidate | revision targets / retention targets | phases | authority | continuation |
| --- | --- | --- | --- | --- | --- |
| add/update/restore | UUID / 新 version | restore 唯一來源，其餘空 / 空 | 1/0/0 | R,W | null |
| stop/resume | UUID / null | 空 / 空 | 0/0/0 | R,W | null |
| erase/prune | UUID / null | 全部保留版本／精確非 current 集合 / 空 | 1/1/0 | R,E,M | null |
| compact | null / null | 空 / 空 | 0/0/1 | R,M | null |
| retention | null / null | 空 / 至少一個精確 proof 或 marker | 0/0/0 | R,M | null |
| recovery | null / null | 空 / 空 | 0/0/0 | R,M | null |
| continue-maintenance | 繼承 parent / null | 空 / 空 | content=0，其餘恰為 parent pending 集合 | R,M；sanitization 才加 E | 必填 |

首個 storage envelope 的 erase/prune 不合併空間回收；內容清除後，以新 compact
預覽盤點 freelist 並確認 N，避免在 SQL 刪除改變 freelist 前猜測工作量。
phase、capabilities、continuation、target 任一不符就拒絕。acceptance_epoch 必須等於
before.epoch，issued_at 不得早於 before.reject_before；caller 不得降低拒絕下限。

proof target 的 id 為 operation_id，digest 為下述 `proof_record_digest`；marker
target 的 id 為 item_id，digest 為 `H(logical_state.items 中該 erased item 完整 object)`。
readback 的 deleted 集合使用同一 recipe。每批 retention 都有新 operation ID、
preview、confirmation/proof；不能以一次確認暗中遍歷後續批次。128+128 個最大寬度
targets 的編碼仍須加上完整 envelope 後檢查 256 KiB，超過即拒絕，不能截斷集合。

storage 精確欄位是 `{filesystem_id, managed_bytes, available_work_bytes, coverage, work_budget}`；
filesystem_id 為核准 root registry 的 opaque ID，數量為精確整數，coverage 為
complete/partial/unknown。第一個合格 storage envelope 要求所有 managed files
位於同一核准 filesystem；若 SQLite 會使用其外的 temp，該 build/操作不合格。
managed_bytes 等於 managed_files 的 bytes 總和（含所有存在的 sidecar），
available_work_bytes 是同一 filesystem 可用空間的觀察，扣除本 host 已承諾而未分配的
並行工作預算；不是永久預留或對其他程式的磁碟空間保證。

preview 的 work_budget 必須為 `{qualification_id, file_snapshot_digest,
journal_bound_bytes, temp_bound_bytes, growth_bound_bytes, required_work_bytes}`。
qualification_id 是 opaque ID，file_snapshot_digest 必須等於 H(managed_files)；
其餘為非負精確整數。J、T、G 分別為 journal、temp/sidecar 及主資料正成長的上界，
彼此不重複計數；G 包含 proof/witness/metadata，不得因操作是刪除就假設為 0。
`R = required_work_bytes = ceil((J+T+G)/4096)*4096`；加總、取整與乘法的結果
均須在 `0..2^53-1`，溢位拒絕，不能依賴浮點近似。
所有 mutation 的 preflight 須 coverage=complete、`managed_bytes+G <= data_limit_bytes`、
`R <= maintenance_max_bytes` 且 `available_work_bytes >= R`。
執行前重新量測；可用空間增加不擴大權限，減少但仍滿足 R 可執行，低於 R 則拒絕。

上界由合格 host 對固定 SQLite build/schema/SQL、操作、OS/filesystem、完整 profile_digest
與實測前態計算並注入；qualification_id 必須命中受信任 registry，並逐項重算／比對
上述綁定與 J/T/G，不能只檢查 ID 存在或接受 caller 自行聲明。
開啟 mutation transaction 前再次驗證資格仍有效與可用空間達 R。
未知資格、無法界定任何一項上界、前態或資格漂移，都拒絕操作。合成例中的 ID 與
J/T/G 只供算式與綁定檢查，不能證明真實資格。執行仍須處理競爭與 ENOSPC，
事後的檔案大小不能證明曾經使用的峰值。維護名額也須有受管理容量內的實體空間，
G1/G2 必須證明滿額時保留的必要維護仍可執行；只預留計數不符合資格。

recovery 必須用 recovery-file-snapshot、candidate=null、item_id=null、
root-maintenance 與 readback；其餘操作用 logical-state。compact 的 logical state
保持相同，布局／大小另行量測。writer 在正常交易到 fresh readback 期間持有 root
exclusive coordination lock，不能把另一個 writer 的狀態混進本次結果。
若程序中斷後其他已授權操作使狀態前進，延後 readback 可回 state-unknown，
不能僅因完整狀態不再相同就錯判資料損壞，也不能重播原 mutation。

`preview_digest=H(preview)`。執行前 external_copies 或 managed_files 的集合、身份、
bytes、摘要或 coverage 漂移，使原 preview 失效；重新預覽並確認。重新觀察相同集合
只更新觀察時間不構成新增範圍，但不能延長確認期限；接受的原 preview bytes 保持不變。
執行後產生的正常 journal/temp 變化須由獲准 runtime envelope 解釋，否則結果 pending。

## 確認與獨立讀回

confirmation 家族 `mg1-confirmation/v1`，精確欄位為
`contract_version, scope, operation_id, nonce, preview_digest, confirmed_at,
expires_at, host_evidence_id`，最多 4 KiB。IDs/digest 沿用共用型別；scope、operation_id、
nonce、expires_at 必須與 preview 相同；`issued_at <= confirmed_at <= now < expires_at`。
確認只由合格 HostAuthorityPort 在本次 execution handle 注入；JSON 含此結構仍不構成權限。

readback 家族 `mg1-readback/v1`，精確欄位為
`contract_version, scope, operation_id, preview_digest, observed_at, result,
state_digest, proof, related_proofs, deleted_proofs, deleted_markers, managed_files, storage, external_copies,
sanitization, space_reclaim, witness, related_witnesses`，最多 256 KiB。
result 為 applied/not-applied/state-unknown/integrity-failed/committed-but-not-adoptable/
committed-capacity-unproven；
state_digest 為 digest 或不可讀時 null；proof 為精確 durable proof 或 null；
related_proofs 對 continuation 為含原操作更新後 proof 的單元素陣列，其餘為空；
witness 為本次 proof 的完整 witness 或 null；related_witnesses 與 related_proofs
逐項對齊，無 witness 時為 null。所有 witness 都須核對其 digest。
deleted_proofs/deleted_markers 為與 preview 同型的精確集合；其餘沿用上述型別。
sanitization/space_reclaim 為 not-requested/pending/complete。

managed_files/storage 是**操作後**的新量測，不能拿 preview 前態當實測；
不要求前後檔案 bytes/hash 相同。applied 必須有 main、coverage=complete、
managed_bytes 等於後態檔案 bytes 總和且 <= data_limit_bytes。
後態 storage.work_budget 必須 null；available_work_bytes 如實回報，並不要求永久留足
下一個未知操作的空間。下一次 mutation 必須重新建立該次前態與工作預算。
若 transaction/proof 已證實提交而容量上限或覆蓋無法證實，回
committed-capacity-unproven，保留真實 proof、停止後續 growth；不能回 not-applied
或還原已刪內容。後續只重做核准唯讀量測或另取得維護授權。
filesystem_id 必須與 preview 相同。外部副本 observation 必須來自本次後態讀取，
observed_at 在 proof.recorded_at 與 readback.observed_at 之間；同秒不代表允許快取。
外層 sanitization/space_reclaim 必須與同次 proof 相同。

applied 必須有完整 scope、一致 proof 與實測後態；not-applied 必須 proof 不存在且
完整前態相符。proof 與其 preview binding 自相矛盾才是 integrity-failed；檔案、後態
或來源不可確定維持 unknown/不可採用。需要的 readback 不完整時不得回 applied。
所有 readback 欄位由新的唯讀 connection 與核准 file/source ports 重新取得，
不是把 executor 的 expected result 原樣包裝。root maintenance 一樣核對完整 scope。

## Proof 交叉欄位規則與 oracle

主契約 proof 的 operation 另允許 continue-maintenance。compact/retention/recovery 的
item_id 為 null，identity_epoch/before_revision/after_revision 均為 0；item 操作
必須有 UUID。erase/prune 必須要求 sanitization；compact 必須要求 space_reclaim。
proof 另有 `restore_source_revision`（restore 的精確來源正整數，其餘 null）、
`target_revisions`（erase/prune 的原精確刪除集合，其餘空）、
`parent_operation_id`（continue-maintenance 的原操作 UUID，其餘 null）。
restore_source_revision 必須與 preview 唯一 target revision 相符；恢復仍產生新 revision，
不把來源 revision 偷換成新 revision。continuation 的 item/identity epoch 繼承其原 proof，
可為 item 或 root 維護，不准擴大範圍。
item proof 的 before_revision/after_revision 是對應 logical state 的 current_revision，
不存在或 erased 時使用 0；identity_epoch 取同一 item（add 取 after，其餘取 before）。
projection_digest 是 after item 的投影 digest；root proof 則是
`H([{item_id, projection_digest} for each active after item in item_id order])`。
acceptance_evidence_id 必須等於本次 confirmation.host_evidence_id；recorded_at 是
最後一次寫入前的可信 UTC 觀察，須在 confirmed_at 與 expires_at 之間（不含到期點），
不是宣稱作業系統完成 fsync 的精確時鐘。readback.observed_at 不得早於 recorded_at。
`phase=sanitization-pending` 要求 sanitization=pending；space-reclaim-pending 要求
sanitization 不是 pending、space_reclaim=pending；complete 不得含 pending。
pending phase 不能與兩個 not-requested 同時出現。最大寬度測試是合法 prune pending
proof，不能用不合法的 retention/item 混合物充當正例。

不使用 `committed` phase。一般單交易操作在 commit 時寫 complete；erase/prune
起始為 sanitization-pending、space_reclaim=not-requested，compact
起始為 space-reclaim-pending。phase 只描述 durable 工作階段；即使 complete，caller
仍須 fresh readback 才能報 applied，crash/例外不能提供重播權限。
原有效 execution handle 可執行預覽已授權的剩餘階段並記錄 phase；phase 記錄是
明確 mutation，不由 audit/readback 寫入。handle 消失或過期後使用以下續作流程。

continue-maintenance 固定採**同一交易更新原 pending proof 並新增 child proof**：
before 集合含原 operation_id 與 preview.continuation.proof_digest 精確匹配的 proof，
child operation_id 尚不存在；parent_operation_id 指向原 erase/prune/compact proof，
不形成任意深度 chain。只更新原 proof 的 phase/sanitization/space_reclaim，compact
另按下述 witness 規則更新後態觀察與 witness_digest，保留其
原 operation/target/digest/acceptance/time；新 child 保存本次 confirmation 的完整
binding metadata、parent ID、實際前後 state digest 與階段結果。
after 集合是更新後原 proof 加 child；兩者與 phase 改動原子提交。readback 必須
讀 child、related_proofs 中的原 proof 及其 witness，核對只發生已核准的 phase／觀察轉換。
失敗只保留實際 pending，不宣稱原 proof 已 complete；不得重做已完成的 SQL 刪除。
新 child 佔一個維護名額；先依下述 liability admission 保留名額，不靠日後清除解套。
retention 可用同交易中已核准、可裁剪 proof 釋放的名額：先提升拒絕下限並裁剪，
再加入本次 proof，交易任一可見狀態都不超限；不要求滿額時額外存在第 33793 個位置。

合成 cases 固定包含 fact/procedure、合法 proof、scope/profile/policy、preview、
confirmation/readback 的正例。其故障 oracle 是後續實作的期望結果，
checker 通過只表示設計例自洽；它沒有模擬或驗證真實人類授權、來源、交易、檔案清除。

## 同 row 的持久 maintenance witness

proof row 為 `{proof, witness}`；proof canonical bytes 仍最多 2048，witness 為 null
或獨立 canonical blob，最多 65536 bytes。proof 新增 `witness_kind, witness_digest`：
兩者同時 null，或 kind=retention/continuation/compact 且 digest=H(witness)。witness
不含自己的 digest，也不含正文、來源、路徑或完整 preview。兩個 blobs 同交易寫入，
同保留期、同一次 retention 裁剪，不許 orphan。64 KiB 是明列的產品格式上限，
其實際 bytes 計入 managed_files；合成模型另計 `witness_count × 65536`。

`proof_record_digest=R(record)=H({proof_digest:H(record.proof), witness_digest:record.proof.witness_digest})`。
計算 R 前必須驗證 witness bytes 與承諾相同。`P(records, excluded_id)` 是按 operation_id
排序的 `H([{operation_id,record_digest:R(record)}])`，排除恰好 excluded_id，不遞迴
展開其他 witness。`M(items)=H([{id:item_id,digest:H(item)}])`，只取排序的 erased markers。
proof-set after root 排除當次新 proof，因此沒有自我雜湊循環。

下列為三個互斥格式，contract_version 固定 `mg1-maintenance-witness/v1`：

| kind / operation | 精確欄位（另含 contract_version, kind, operation_id） |
| --- | --- |
| retention / retention | target_proofs, target_markers, before_proof_set_digest, after_proof_set_digest_without_self, before_marker_set_digest, after_marker_set_digest |
| continuation / continue-maintenance | parent_before_record, parent_after_record_digest, remaining_phases, before_proof_set_digest, after_proof_set_digest_without_self |
| compact / compact | plan, freelist_pages_after, actual_pages_reclaimed, file_snapshot_before_digest |

retention 保存完整 128+128 上限的 `{id,digest}` manifest，與 preview 完全相同。
target digest/count 直接由持久陣列的 H／length 推導，不能用摘要取代可展開集合。
新的唯讀 readback 驗證 target IDs 均不存在；當前 proof 集合排除 self 後符合 after
root；把 target leaves 加回當前集合可重建 before root。marker 集合同理。它驗證
原子提交的 manifest／集合／提高後的 floor，不重新證明已刪 proof 當年的 age/phase；
eligibility 是 commit 前對完整目標紀錄的必要檢查，不把 post-commit 缺失猜成合格。

continuation 的 parent_before_record 為原 erase/prune/compact 的完整 `{proof,witness}`，
最多 8192 bytes；不能以另一 continuation 或 retention 作 parent。preview.proof_digest
仍為 H(parent proof)，witness 則攜带完整 record，兩者須符合現有資料。
readback 核對 parent 目標／identity epoch 不變；只能把 requested pending phase 單向
推進，未請求的 phase 不變。compact parent 另只允許填入其 witness 兩個後態欄位
及對應 proof.witness_digest；plan、before file digest 與其他 binding 均不變。
用 parent_before_record 置換當前集合的 parent 可重建 before root；排除 child 的當前
集合應符合 after root 及 parent_after_record_digest。reply 遺失後不需 RAM preview
即可核對此次 proof-set 轉換；若其他合法操作使集合前進，則回 state-unknown。

compact witness 的 plan 等於 preview.compact；freelist_pages_after、actual_pages_reclaimed
在 pending 時皆 null，完成後填本次量測。
`file_snapshot_before_digest = H(preview.managed_files) = preview.storage.work_budget.file_snapshot_digest`；
continuation 必須沿用 parent 原始值，不能換成本次 continuation 的前態檔案摘要。
`actual_pages_reclaimed = freelist_pages_before - freelist_pages_after`，範圍為 `0..N`；
0 或小於 N 都是合法有限進展，實際檔案 bytes 另由 readback 報告，不以 N 換算宣稱。
持久 witness 不保存後態檔案 hash：main 檔包含 witness，保存自身最終 hash 會形成循環。
後態檔案 hash 只在 commit 後，由外層 fresh readback 獨立取得，不回寫庫。

執行 compact plan 的交易必須把 `incremental_vacuum(N)` 與 witness/phase 放在
**同一 SQLite transaction**；若由 continue-maintenance 執行，該 child record 也在同一交易。
初次 compact 不要求 child。初次 pending row 建立、既有 row 更新及
child 新 row 均須有資格驗證的 metadata 空間，這些寫入不得改變 freelist；否則整筆
rollback、capability-unavailable，不把 metadata allocation 計為 reclaimed pages。
PRAGMA 緊鄰前後讀取 freelist，分別須為 plan 的前態及記錄的後態；寫完 metadata 再
核對後態未變才 commit。因此 durable pending/null witness 表示該次 plan 沒有已提交效果。
pending 若觀察到 freelist 漂移，只回 state-unknown 並禁止重播原 N；確認權不涵蓋
猜測 remaining work。一般新的 compact 可重新預覽，不能靠它默默改写未解析的 parent。
確認後不得改 N、page_size 或執行 full VACUUM；若 build/SQL 無法满足以上不變量就不准入。

SQLite 的[官方增量回收測試](https://github.com/sqlite/sqlite/blob/master/test/incrvacuum.test)
包含 transaction／rollback 情境；這支持上述資格驗證方向，不替代 G2 對指定 build、
journal、故障點與 metadata 空間的實測，也不證明本提案已有可執行實作。

一般 proof 的 witness 必須 null；只有上述三種 operation 有 witness。每 root 的
retained witnesses 上限為 maintenance_proof_reserve（預設 1024）。新增 pending 操作時，
每個尚待階段各保留一份未來 child proof/witness 的名額；admission 同時要求
`after_proof_count + remaining_phase_liability <= max_proofs+maintenance_proof_reserve`（33792）與
`after_witness_count + remaining_phase_liability <= maintenance_proof_reserve`（1024）。retention 可先在同交易裁剪
已授權過期 rows 再計算 after count。continuation 沒有 durable phase 進展則不提交
新 child；有進展才消耗對應預留並更新剩餘 liability，避免滿額令 pending 永久無法續作。
