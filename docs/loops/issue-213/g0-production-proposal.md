# Issue #213：G0 生產契約提案

## 狀態與本次交付

**G0 產品／資料選擇已完整接受；本包完成設計與離線驗證，未啟用 runtime。**
本包延用 [#213](https://github.com/jeffery777/codex-dev-skills/issues/213)，
確認 Issue 後建立 `codex/213-mg1-production-contract`，基準為
`b69d838d2bf239f17a8897f60f2e638a1d2cadd9`（PR #229）。
本文將 [既有接受缺口](g0-acceptance.md)具體化；合併設計提案、合成計算通過、
代理報告或本文件的 status 均不能自行核准產品參數、發行或真實資料操作。

本包交付本文、[profile／合成負載](g0-production-profile.json)、
[合成例與故障 oracle](g0-production-cases.json)、[精確 envelope](g0-production-envelopes.md)、
離線 profile 算式／合成例檢查及其回歸測試。
既有 `mg1-g0-synthetic/v0`、`loop-memory/v1`、M0/M1、安裝來源與 schema 不變。
JSON 提案是可重算的設計輸入，不是 backend 設定檔、操作請求或 migration。

來源為 [MG1 milestone](../../memory-governance-milestone.md)、
[研究](../../memory-governance-research.md)、[G0 合成契約](../../memory-governance-g0-contract.md)
及 [共存邊界](../../native-memory-coexistence.md)。研究不重跑，新增 SQLite 技術取捨
僅用官方文件與本次可重跑的合成證據支持。

## 已接受的產品行為

| 選擇 | 已接受方案 | 實際效果及替代方案 |
| --- | --- | --- |
| 內容 | 同時支援 fact／procedure，使用同一 identity／revision 模型。 | 方法必須有前提、步驟、成功證據與失效條件；不能只存「曾經成功」。首版不做自動技能升級。 |
| 歷史 | 最多 10 個保留版本，含目前版本；退休 30 日的歷史作清理門檻。 | 到門檻只盤點；修改若將超限就拒絕，另列精確歷史集合請求清除。沒有自動淘汰或無限保留承諾。較少版本可降低保留量，但縮小可復原範圍。 |
| 容量 | 每 root 預設 4 GiB 資料上限；建立時可選容量，80% 提醒，維護空間按當次實際用量估算。 | 使用者提出改為 4 GiB，本提案依此調整。筆數配套建議為 10,000 個 item／marker、每個完整 version 16 KiB；journal/temp 工作預算另計。容量不是預先分配，數量上限不保證可同時用滿。 |
| 授權 | 可信 host port 注入當次接受證據；資料 API 不接受請求自行提供的 accepted set。 | 核心不把 JSON 一致性當人類確認。未完成控制面資格驗證的 CLI／Desktop adapter 維持禁止真實寫入。 |
| 儲存 | 單一使用者、單一 principal/root、本機 POSIX、新 SQLite 庫；普通 current-only 索引。 | 先採可有界查詢的摘要／cue，不提供向量或語意搜尋；FTS 另需 shadow-table 清除資格驗證。舊 M1 保持原界面。 |

一般模組切分、診斷碼與測試安排可由代理決定。使用者先接受 1 GiB 容量方向，
再提出「或是改用一般SQL 4GB的上限？」；本輪按維持 SQLite、改為 4 GiB 的方向調整。
4 GiB 為本產品的容量選擇，並非 SQL 或 SQLite 的通用上限；見 [SQLite 官方限制](https://www.sqlite.org/limits.html)。
2026-09-07，使用者在容量調整後，對本方案的歷史／證明保留、數量及版本大小、
確認期限、可信控制面、readback、本機 SQLite 與儲存／故障邊界明確回覆
「接受其餘建議，完成 G0」。接受紀錄見 [#213](https://github.com/jeffery777/codex-dev-skills/issues/213#issuecomment-5567661125)。
這項產品接受與既有提交／PR／合併授權分開；兩者都不等於真實資料操作或發行授權。
profile／cases JSON 及離線工具仍標為 proposal／synthetic，所有 acceptance、runtime、
authority 與 write 旗標維持 false，因為工具輸出不能證明或授予上述人類接受。

## Version 與來源資料

已接受的設計家族為 `mg1-managed-content/v1`；production schema 的完整實作仍屬 G1，
目前沒有可接收此格式的生產入口。
數字為 `0..2^53-1` 精確整數，revision 從 1 起；所有 object 拒絕缺少／額外欄位，未知家族拒絕。
完整 version 的 UTF-8 canonical JSON（sorted keys、無空白、無非有限數字）上限
16 KiB，包括來源、方法、驗證紀錄、摘要及 cue，不能只計正文。

| 物件 | 擬議欄位／界限 |
| --- | --- |
| root metadata | `contract_version, principal_id, root_id, repository_id, schema_fingerprint, profile_digest, policy_fingerprint, epoch, reject_before`；身份由 host 綁定，禁止自動採納庫內自述。 |
| item | `item_id, identity_epoch, status, current_revision, revision_high_water, erased_at`；`status` 為 active/stopped/erased，identity 不以內容相似度推定。 |
| version | `revision, created_at, retired_at, kind, body, summary, cues, applicability, procedure, provenance, validation`。已提交版本不可就地改寫。 |
| body／summary／cues | body 非空；summary 最多 1 KiB；最多 16 個 cue、各最多 128 UTF-8 bytes，正規化後不重複；仍受完整 version 16 KiB 限制。 |
| applicability | `repository_id, paths, conditions`；paths 最多 16 個已正規化 repo-relative 路徑，conditions 最多 16 個非空條件。內容條件不是取得額外讀取權限的指令。 |
| procedure | fact 必須為 null；procedure 為 `prerequisites, steps, success_evidence, invalidation_conditions`，各為 1–16 個非空條目；evidence 使用 provenance 中的 source ID。 |
| provenance | 1–8 個來源，各為 `source_id, kind, reference, source_revision, source_digest, attestation`。kind 只接受下述兩個已定義來源 port，禁止任意 URL 自動抓取。 |
| validation | `content_digest, evidence_id, verified_at, verifier_fingerprint, policy_fingerprint, eligibility`。content_digest 綁定 version 除 validation 與生命週期時間外的內容；eligibility 寫入時僅可為 eligible。 |

body、條件、步驟及前提均為 UTF-8 string；各非空字串仍受完整 version 上限約束。
item/root/principal ID 是 36 字元 UUID，repository_id 是 host registry 的 1–64 ASCII
不透明 ID；source_id／evidence_id 同為 1–64 ASCII ID。digest／fingerprint 是 64 個
小寫 hex。created_at／verified_at 為 UTC 秒；current 的 retired_at 為 null，退休後
由版本切換交易一次設定，不能重新延後；這是 immutable content 的唯一生命週期例外。
paths 以 `/` 分隔、禁止絕對路徑、空 segment、`.`／`..`、NUL；不得追蹤 symlink
越過核准 root。cue 採 Unicode NFC、casefold、首尾去空白，空值拒絕。
provenance.reference 為 `{repository_id, path}`（repo-artifact）或
`{evidence_id}`（human-confirmed-decision）；source_revision 分別是 40/64 hex Git
commit ID 或 1–64 ASCII 不透明決策 revision，source_digest 為安全來源本文 SHA-256。
success_evidence 每項是 provenance 的 source_id；validation.evidence_id 是另一份
host 驗證結果的本機引用，不能由來源本身宣布 eligible。完整 schema 的機械實作屬 G1。

`repo-artifact` 來源由 host 核准的 repository/root 與固定 Git commit、正規化 path、
blob bytes 的 SHA-256 識別，attestation 為 null；reader 只讀該已核准來源，不從 record 內的絕對路徑或 shell
片段擴張讀取。`human-confirmed-decision` 來源由合格 host 保留的當次接受證據識別；
不得將私人對話、原始訊息或完整 session 附進 provenance。安全決定本文只保存在
受管理 version 的 body；host 不另存第二份本文。其 attestation 是
`{scope_digest, policy_fingerprint, issuer_fingerprint, accepted_at, binding_token}`：
前三項是 digest，accepted_at 是本次 host 對 candidate 來源重新接受／發證的 UTC 秒，
不是原始人類決策時間；原決策身份仍由 immutable source_revision/source_digest 保留。
binding_token 是最多 2048 ASCII bytes
的不透明、非本文 host 證據。token 必須由合格 port 認證完整 scope、source ID、
revision/digest、policy、issuer/time 綁定，不接受 caller 自簽 digest 作 token。
沒有合格來源 port 時只保留未保存提案。

human attestation 與引用欄位只存於該 version.provenance，計入 16 KiB；不建立
另一個無上限 host evidence table。後續來源驗證由合格 port 驗證此 metadata/token
及目前撤銷／有效性，不能依賴已消失的原對話；無法驗證時拒絕採用，不能自認有效。
必要 host authority key/registry 的資格由 G1 另驗，初始允許集合為空。
這項 source 能力須在持久證據可離開原 process 驗證時才開放。

provenance、驗證摘要及方法內容均屬受管理版本，清除時一起移除；不能為保留
驗證紀錄而另存原文。恢復舊版會產生新 revision，重新驗證來源／適用範圍並取得
新確認，不複用舊 eligibility。修改後即使正文相同，來源或方法前提變更仍須新 revision。

`verified_at` 是寫入當時的觀察，不是永遠有效的證明。audit／recall 重新查核
當前 scope、來源 revision 及證據有效性，輸出當次 observation，不為刷新時間寫庫。
來源不可得、已改版、互相矛盾或未符合方法前提時，該次不得採用，並標明原因；
不自動刪除或將 stored status 改成 stopped。來源盤點覆蓋率與 item 列舉完整性分開。

內容敏感性規範採 `mg1-content-safety/v1`，延續既有
[M1 禁止內容基線](../../memory-sqlite-reference-contract.md)：secrets、credentials、
PII、private paths、raw chats/sessions/logs、restricted data、未遮蔽設定均不得保存。
scope/policy 的精確 fingerprint material 見 [envelope](g0-production-envelopes.md)。
候選、來源 attestation、validation、preview/confirmation/readback 全部綁同一 policy；
unknown、衝突或 policy 不可得都拒絕保存／採用。需要遮蔽時先形成新的完整 candidate，
重新驗證並呈現預覽；不得確認後才偷偷改寫內容。schema 自洽不等於敏感性檢查通過。

## 可信控制面與 readback

`HostAuthorityPort` 是受信任的呼叫端接口，`request` 與記憶正文為不可信資料。
這是明確的 trusted computing base 邊界，不承諾隔離已控制 host／相同 OS 使用者的攻擊者。
不得將一份 caller JSON、可由 agent 編輯的設定、已存在的記憶或自簽 digest
包裝成獨立授權。沒有合格 host port 就不能啟用任何生產 mutation。

| Port | 可信輸入的來源／規則 | 核心必須比對的結果 |
| --- | --- | --- |
| root binding | 由明確接受的 host 設定註冊獨立 root，解析實體目錄、owner／mode、device/inode 及庫 fingerprint；不從資料請求註冊。 | principal/root/repository、schema/profile、狀態檔身份及核准 capability；一項漂移即拒絕。 |
| source verification | host 在原讀取授權範圍內取得固定 artifact 或當次接受證據，檢查敏感性、來源與內容 revision。 | 完整 candidate digest、source set、repository revision、observed_at、verifier fingerprint、eligible 結果。 |
| preview confirmation | host 將同一 canonical preview 渲染給人，從目前 controlling instruction／明確確認取得接受結果；不能由 request 的 `confirmed=true` 觸發。 | preview digest、principal/root、operation/nonce、before digest、profile、內容/來源與 readback scope、時效；只注入本次接受的完整 bytes 與 digest。 |
| trusted clock | host 提供同次觀察的 UTC 整數秒與 process monotonic clock；UTC 低於上次可信觀察、monotonic 倒退或過期時拒絕 mutation／retention。 | `issued_at <= confirmed_at <= now < expires_at`，期限最多 300 秒；相等過期即拒絕。重開後舊 process handle 無效。 |
| result readback | 獨立的新唯讀 connection 重新讀取已核准庫的 identity、epoch、item/current projection 與 receipt；不可直接採用 executor 回傳物件。 | 實際 transaction／操作ID、before/after revision、投影 digest、pending phases 與檔案量測；對應不上回報 state-unknown。 |

port 的實作與接受 registry 由 host 擁有，呼叫端資料不得覆寫；對 core 的測試
可注入合成 port，但合成回傳只證明綁定及拒絕分支，不能使真實 adapter 取得資格。
G1 必須提供明確的 port protocol、正反測試與允許的 adapter 指紋；初始允許集合為空。
CLI／Desktop 沒有可驗證的 user-confirmation/source port 時，只能 audit 或產生提案，
不能改用讀取記憶、CLI argv、自動輸入 TTY 或檔案自述來補造授權。
這不要求每一步重問人；目標、內容、來源、前態與期限完全相同的有效確認可沿用。

operation confirmation 的完整 preview bytes、source observation 及 execution handle
僅存在本次 process RAM，至過期／結束即失效，不建立 persistent preview cache/log。
durable operation proof 只留本文件列出的不可逆 binding metadata 與 opaque evidence ID；
該 ID 是追溯標籤，不保證原 RAM evidence 可再讀，更不恢復舊確認權限。
readback 依核准庫的精確 scope、state/proof 及可信 port 查核結果，不依賴原 preview 原文。
host 若要持久保存完整 preview 或來源本文，就不符合此首版資格；須先另行設計並
接受容量、保留、清除與外部副本邊界。Codex 原始對話／host history 仍屬外部副本，
只能列已知觀察或 coverage=unknown，不能承諾 managed erase 一併移除它們。

預覽一次綁定 mutation 及精確結果讀回權限；讀回不提供新增 mutation 權限。
所有 source observation 與 confirmation 在執行前再比對。SQLite 交易不能鎖住外部
Git／host 的狀態，不能宣稱跨來源原子性；post-commit 發現來源漂移時，保留已提交
receipt、回報 committed-but-not-adoptable，後續 recall 重新拒絕採用，不以還原／刪除掩蓋結果。

## 預覽、資料交易與 proof

沿用既有 G0 的 scope／identity／revision／exact-set／expiry／epoch／拒絕下限原則，
但新內容、host port、pagination 與持久格式須另行實作，不將 v0 fixture 餵進生產核心。
自然語言只形成候選；add/update/restore/resume 需要可採用來源，stop/erase/prune
則不要求不應保存的舊內容重新通過新增 eligibility，但必須精確定位與授權。

一個成功交易同時寫入 immutable version／狀態、current pointer、current-only
搜尋投影及 proof。停止項目無一般搜尋投影；update stopped item 不會自動 resume。
erase 清除全部版本與衍生投影，保留 identity marker／revision high-water 及無原文 proof。
prune 只刪已確認的精確歷史 revision 集合，不能含 current。
prune 與 erase 同樣先得到 content-removed，再完成受管理歷史／索引／主檔／journal／
temp 殘留檢查；未完成就保持 sanitization-pending，不因仍有 current 而略過舊版清除。
若清除殘留需全庫維護，先取得 root-maintenance，不能沿用單一 item 的權限推定。
prune 不改 current pointer／current content，失敗或 continuation 也不得重新匯入已刪歷史。
舊 M1 的 logical delete、原生記憶、exports/backups 均不是本 root 的清除目標。

proof 每筆 canonical JSON 最多 2048 bytes；固定欄位如下，root scope 由其所在的
已綁定庫與外層 readback envelope 提供，不能將裸 proof 當跨 root 證據：

| 欄位 | 型別／上限 |
| --- | --- |
| contract_version | 固定 `mg1-operation-proof/v1`。 |
| operation_id, item_id | 36 字元 UUID；root 維護的 item_id 為 null。 |
| identity_epoch, acceptance_epoch, before_revision, after_revision, recorded_at | `0..2^53-1` 整數；root 維護的 item revision/identity epoch 為 0。 |
| operation | add/update/restore/stop/resume/erase/prune/compact/retention/recovery/continue-maintenance。 |
| restore_source_revision, target_revisions, parent_operation_id | restore 來源正整數或 null；erase/prune 最多 10 個精確刪除 revision；continuation 的原操作 UUID 或 null。依 envelope 的交叉規則。 |
| preview_digest, before_digest, after_digest, projection_digest | 各 64 個小寫 hex；由核心計算的完整預覽／狀態摘要，不由請求覆寫。 |
| acceptance_evidence_id | 1–64 ASCII 不透明本機引用。 |
| witness_kind, witness_digest | 同 row 無原文 witness 的種類與 digest，或兩者皆 null；詳見 envelope。 |
| phase | sanitization-pending/space-reclaim-pending/complete；不使用含糊的 committed phase。 |
| sanitization, space_reclaim | not-requested/pending/complete。 |

不得含正文、cue、provenance 路徑、差異或可還原原文的值；真實 digest 仍可能有推知風險，
不允許自動匯出至公共 Git。合成最大欄位例可重算 byte 數；G1 對每筆實際編碼
再次檢查 2048 bytes，超過即拒絕，不能截斷。phase 更新不改原始交易／接受綁定。
compact 的獨立 witness 可按已核准 plan 填入後態觀察並更新 witness_digest；不得改 plan。
一般 proof 32768 筆；stop/erase/prune/compact 另有 1024 筆預留，pending proof 計入上限。
retention/recovery/continue-maintenance 也可使用維護預留；需能容納本次 proof。
retention/continuation/compact 另有同 row、同保留期、最多64 KiB的 witness，root 最多
1024份；實際bytes及pending階段未來child名額均計入容量，不能只算2 KiB摘要。
retention 可在同一原子交易利用已授權裁剪釋放的位置，精確規則見 envelope。
proof 與外層 scope、state digest 排除材料、root-maintenance 的 null target、
phase 交叉條件依 [精確 envelope](g0-production-envelopes.md)，不能各 adapter 自訂。
30 日內 32768 筆約相當於每日平均 1092 次一般操作，這是容量取捨，並非速率保證。
10,000 個 erased marker 也會阻止新增 identity；即使內容已空，仍須等保留窗口滿足並
取得精確 marker retention 確認。沒有自動釋放 proof 或 marker 的背景程序。

已完成 proof／erased marker 超過 30 日，且無必要引用，才可在精確 retention 預覽後裁剪。
先提高 durable epoch／reject_before，再於同一交易裁剪；pending proof 不裁剪。
舊 epoch／低於下限／已見 operation ID 的 mutation 均拒絕。commit 回覆遺失時只做
已授權 readback，不將原 request 當新 mutation 重送；沒有 proof 且狀態不可確定則停止。

## 容量與十二項 profile

完整數值以 [profile 提案](g0-production-profile.json)為單一算式輸入。
30 日為 2,592,000 秒，MiB 為 1,048,576 bytes、GiB 為 1,073,741,824 bytes；目前版本不受退休年齡淘汰。
`max_scan_items=256` 是一次 audit page 上限，全部 root item／marker 上限為 10,000。
每頁持有同一唯讀 snapshot 的 opaque cursor；跨呼叫關閉 snapshot 就須重開盤點，
不能混合不同 snapshot 說完整。單次完整盤點至多 40 頁，最多 10,000 items；來源查核另計覆蓋率。

| 欄位 | 建議值 | 拒絕／效果 |
| --- | ---: | --- |
| max_items | 10000 | 包含 active、stopped、erased marker；滿額不得自動刪 marker。 |
| max_versions | 10 | 含 current；update/restore 若超限先要求精確 prune。 |
| history_seconds | 2592000 | retired 歷史超期只具清理資格；禁止自動移除。 |
| max_payload_bytes | 16384 | 完整 version，包含方法／provenance／validation。 |
| max_proofs | 32768 | 一般寫入須留足名額；拒絕紀錄不另寫無界 log。 |
| maintenance_proof_reserve | 1024 | 僅供受授權維護使用；包含必要後續階段名額及實體容量。 |
| proof_seconds | 2592000 | completed proof 超期且滿足拒絕下限條件才可裁剪。 |
| marker_seconds | 2592000 | marker 最短窗口，且必須無保留 proof 引用。 |
| confirmation_seconds | 300 | 過期／重開後失效；不能以延長設定續用舊接受。 |
| max_scan_items | 256 | per-page；cursor綁 snapshot與授權，不接受caller任意offset。 |
| data_limit_bytes | 4294967296 | 每 root 實際受管理檔案上限，包含版本、索引、proof、witness 與頁面。 |
| maintenance_max_bytes | 5368709120 | 單次額外工作空間需求的上限（5 GiB）；不是永久預留，不從資料容量扣除。 |

資料上限 `D = data_limit_bytes` 與工作空間分離。建立新 root 時建議提供
256 MiB、1 GiB、4 GiB（預設）三個有界 preset，各自的 maintenance_max_bytes 為 `5D/4`，
其他欄位不因選擇 preset 自動提高；每個 preset 均須獨立完成 runtime 資格驗證。
完整 profile/digest 在 root 建立時固定；首版不提供既有 root 線上擴縮容，不能偷偷改
config 使歷史 proof 的 profile binding 失真。未來 resize 須另有版本化變更契約。

當次額外工作需求 `R = ceil((J+T+G)/4096)*4096`；J 是 journal 上界，T 是額外
temp/sidecar 上界，G 是包含 proof/witness/metadata 的主資料正成長上界。
這些值由固定 build/schema/SQL/OS/filesystem 的資格證據與實測前態計算，不能只填猜值。
前態要求 `managed_bytes+G <= D`、`R <= maintenance_max_bytes`、實際可用空間 `>= R`；
後態另量測真實檔案大小，完整交叉條件見 envelope。工作預算隨當次資料與操作計算，
空庫不會因 4 GiB 上限被要求永久閒置數 GiB。競爭、峰值及 ENOSPC 仍須實測。
80% 僅針對 fresh measured managed_bytes / D 的預警，不授權自動清除或改寫。

合成估算分開加總完整 versions、current 搜尋投影、無原文 proof及witness、item metadata
及規劃用 SQLite overhead。它們不是量測的 database bytes；實際 file size 已包含
索引／頁面等內容，不能與上述估算再相加。四個例子的資料估算分別約
12.21 MiB、87.64 MiB、556.04 MiB、2017.88 MiB；4 GiB 的資料與工作上限可容納這四個合成例；
1 GiB preset 接受前三個模型負載、拒絕第四例。這些是明列假設的合成負載，不是實際使用分布。
calculator 以 `J=估計資料量`、`T=64 MiB`、`G=1 MiB` 比較動態工作需求，
只供規劃，不是合法 runtime 上界、磁碟量測或 capability 資格。計算結果不接受 profile。
完整數量上限不保證能同時用滿；真實admission以實測檔案、pending名額及峰值為準。

4 GiB 上限下，完整檔案 SHA-256 的一次 preview 加 fresh readback 最多須讀約 8 GiB。
檔案與 logical-state digest 必須串流計算，輸入 bytes/rows 有界；不得把整個 root
物化到 RAM。G1 啟用前須對固定 build/filesystem 測量最壞延遲與鎖定時間，未達資格
則能力維持 unavailable。G0 不宣稱互動效能，也不以 mtime/size 取代完整內容摘要。

## 儲存與故障契約

本提案採獨立 root、新庫、單一 writer，初始化時固定 `page_size=4096`、
`journal_mode=DELETE`、`synchronous=EXTRA`、`auto_vacuum=INCREMENTAL`、
`secure_delete=ON`、`temp_store=MEMORY`、`foreign_keys=ON`、`trusted_schema=OFF`，
`max_page_count=data_limit_bytes/4096`（4 GiB preset 為 1048576）。每個 writer／recovery connection 都設定並讀回連線值；
audit 不為配合提案而更改既有庫。禁止 ATTACH、共享 cache、外部 extension、
自訂 VFS 與 network FS。SQLite 的 EXTRA 在 DELETE journal 模式增加 unlink 後
目錄同步；INCREMENTAL 不會在一般 commit 自動縮檔。
這是依[官方 pragma 語意](https://www.sqlite.org/pragma.html)選定的方案，尚未完成實作資格驗證。
普通 `current_search` table 僅保存 active current 的安全摘要／cue投影，與版本切換同交易；
cue 表鍵為 `(item_id, current_revision, normalized_cue)`，查詢最多 16 個 cue，使用
參數化相等比對並要求所有 cue 都命中（AND），按 item ID 排序；不提供全文、模糊、前綴、片語或 BM25 搜尋。
不建立 FTS shadow tables。SQLite／連線參數與 schema fingerprint 漂移即拒絕。
這些是新契約提議，不授權修改現有庫的 pragma 或 journal。

root 必須是明確核准、owner-only 的本機目錄，拒絕 symlink／非 regular 主檔、
其他 principal、未知內容或損毀；無自動 schema migration、repair、import 或 backup。
受管理集合精確列 main、當次 rollback journal、受控 temporary files；WAL/SHM
不屬已選 envelope 的合法運作產物，發現即停止並回報，不能直接刪掉它們。
外部副本用 known 清單與 coverage=complete/partial/unknown 分開表示；unknown 不填零。

root coordination lock 於明確初始化時建立；audit 只開既有 lock 並持 shared lock，
writer／recovery 持 exclusive lock。鎖不可得或不存在就停止，不在 audit 建立它。
取得鎖後發現非空 rollback journal 就不開 DB，回報 recovery-required；保守拒絕
不表示已證實 journal 是 hot。其餘使用 `mode=ro&cache=private`，不用 `immutable=1`；
query_only 只能作額外限制，不能取代[真正唯讀開啟](https://www.sqlite.org/uri.html)。
audit 不能為開庫而復原 hot journal、調整持久 pragma、建立索引或 checkpoint。
`SQLITE_READONLY_ROLLBACK` 亦回報 recovery-required，不自動升級可寫連線。
先準備精確 root-maintenance
預覽，取得授權後才由指定 recovery path 執行。readback 若同樣受阻就保持 state-unknown。

`temp_store=MEMORY` 並不排除 journal 等所有磁碟暫存。G1/G2 必須對選定 SQLite
build、OS/filesystem、固定 SQL 集合及各操作取得可列舉的 temp envelope，記錄 peak
與所在 filesystem 可用空間；無法建立覆蓋就不開放該寫入／清除 capability。
不依賴未承諾的暫存檔名或把目錄沒有檔案當不存在其他暫存。
這個限制源自[SQLite temporary files](https://www.sqlite.org/tempfiles.html)的種類與實作差異。
G2 首版 compact 只做預覽綁定、有界 `incremental_vacuum(N)`，N 是正整數且至多
當次已核對的 freelist pages；實際縮減可能少於 N，照實讀回，不承諾重排所有頁面。
N、page_size與freelist前態進入compact preview，後態進入同row witness；確認後不能換 N。
尚無 durable pending 的前態漂移可重新預覽；已有 pending/null witness 卻漂移則
state-unknown、禁止重播，不能靠新預覽消解未解析操作。PRAGMA 與階段紀錄的原子性
及 metadata 不改 freelist 的資格規則見 envelope。erase/prune先完成內容與殘留清除，
需要空間回收時另取得compact預覽與確認，不預先猜刪除後的freelist。
完整 VACUUM／VACUUM INTO 不在首版入口；新增前須重新核准 temp／backup 邊界。

| 故障位置 | 應回報與保留的狀態 | 允許的下一步 |
| --- | --- | --- |
| authorization／來源／前態不符 | rejected；不開 mutation transaction。 | 重建候選／預覽；不得重用舊接受。 |
| root／schema／檔案 identity 漂移 | incompatible；不修復或轉換。 | 人類檢查正確root；獨立migration另案。 |
| lock 或可用空間不足 | busy／insufficient-space；不承諾變更成功。 | 現有唯讀能力如實回報；有界重試須確認仍有效。 |
| transaction 尚未 commit 即中斷 | 未證實成功；可能留下需復原的 journal。 | 唯讀 probe 不復原；取得維護授權後處理。 |
| commit／close／同步回覆遺失或例外 | state-unknown，不能由例外推論未提交。 | 新唯讀 readback：proof 與完整後態匹配才證實 applied；無 proof 且完整前態匹配才證實 not-applied；其餘保持 unknown 或 integrity-failed。禁止直接重播 mutation。 |
| row／projection／proof 不一致 | integrity-failed；停止 adoption與mutation。 | 不以任一局部值自證；不自動repair。 |
| erase/prune 交易已成功、殘留檢查未完成 | sanitization-pending；已刪集合不得供recall/history使用，prune 的合法 current 保留。 | 新確認或仍有效且涵蓋範圍的授權處理剩餘階段。 |
| sanitization 成功、未要求compact | erase/prune complete；獨立報告實際大小／可重用空白。 | 不因未縮檔把內容清除改成失敗。 |
| transaction 已提交、容量量測不足／超限 | committed-capacity-unproven，保留已提交 proof。 | 阻止 growth；唯讀重測或另行核准維護，不回復舊內容。 |
| compact 中斷／ENOSPC | space-reclaim-pending；已清除內容不可復活。 | 核對既有proof及剩餘集合，重新確認維護；不還原舊副本。 |
| post-commit 來源漂移 | committed-but-not-adoptable。 | 保留真實receipt，來源重新驗證；不自動stop或delete。 |
| 時間倒退／過期 | clock-untrusted／expired；不裁剪防重播資料。 | 新可信觀察及新preview；保留拒絕下限。 |

清除成功必須區分 SQL 移除、可讀受管理檔案殘留與磁碟回收。
禁止只憑 query 無結果或 `secure_delete=ON` 回覆「全部刪除」。G2 必須覆蓋
所有受管理讀取／歷史／索引路徑及主檔、journal、temp的合成canary；任何未覆蓋
部分標示 pending／unknown。SSD、OS快照、交換區、匯出及第三方副本不在保證範圍。

## 驗證與 G1 進入條件

本包先驗證 profile 算式、版本／來源、preview/confirmation/readback 的合成綁定、
合法 proof 交叉欄位、固定產品數值、拒絕與故障矩陣清單及舊 G0 相容性。
合成情境JSON列的是後續必須通過的oracle；沒有執行器的情境不能宣稱已測試通過。
離線計算工具不連DB、不讀native記憶、不讀隱含路徑、不產生操作授權。

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
./scripts/project-python scripts/evaluate-memory-governance-profile.py \
  docs/loops/issue-213/g0-production-profile.json
./scripts/project-python scripts/validate-memory-governance-proposal-cases.py \
  docs/loops/issue-213/g0-production-cases.json \
  --profile docs/loops/issue-213/g0-production-profile.json
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_governance_profile_proposal tests.test_memory_governance_g0 \
  tests.test_test_shards tests.test_memory_m0_contract_docs \
  tests.test_memory_sqlite_contract_docs tests.test_loop_state_roadmap_docs \
  tests.test_native_runtime_contract_docs tests.test_validate_repo
PYTHONDONTWRITEBYTECODE=1 ./scripts/validate-repo.sh --skip-unit-tests
git diff --check
```

上述是本包的可重跑驗證計畫；完整 production schema、authority port 真偽、SQLite
故障與 residue/ENOSPC oracle 仍由 G1/G2 實作後執行，不能計入本包的通過測試數。

產品／資料選擇已接受；本包正式審查、CI 與合併完成後，G0 的設計接受缺口即關閉，
可另立 G1 執行 Issue。這不代表 G1 實作、host 資格或真實資料操作已通過。
G1 Issue 預定 ownership 如下，取得 Issue ID 後才另開分支並建立這些檔案；
實作發現跨邊界變更時重做影響分析，不將本表當作任意修改既有 M0/M1 的許可：

| 預定檔案／位置 | G1 責任與驗證 |
| --- | --- |
| `skills/loop-engineering/scripts/memory_governance_contract.py` | 新 content/profile/preview/proof schema 與有界編碼；型別、額外欄位、容量、digest／來源綁定正反測試。 |
| `skills/loop-engineering/scripts/memory_governance_host.py` | HostAuthorityPort、source/clock/readback protocol 與空 adapter registry；不得從資料取得 authority。 |
| `skills/loop-engineering/scripts/memory_governance_core.py` | 新庫、鎖、交易、revision/current projection/proof；audit、preview、add/update/restore/stop/resume；獨立 readback 與故障測試。 |
| `skills/loop-engineering/scripts/governancectl.py` | 有界 audit／proposal CLI；真實 mutation adapter 不合格時明確 unavailable，不能把合成 acceptance 轉為真實授權。 |
| `skills/loop-engineering/references/memory-governance-v1.md` | 對應已接受契約、操作及資格邊界，入口與自然語言路由保持關閉直到相應資格完成。 |
| `tests/test_memory_governance_contract.py`, `tests/test_memory_governance_core.py`, `tests/test_governancectl.py` 與 `tests/fixtures/memory-governance/` | 合成 port、subprocess 故障、hot-journal audit、快照、實際檔案／容量驗證；不是用模型評分代替資料正確性。 |

G1 每包須有 code/data deep review、docs gate、Security Diff Scan、精確 head Merge
Review、CI 與本 repository App gate。修改 installed source 時同步 catalog/package
及候選版本規則；release／本機安裝仍需其對應授權與 gate。
初期只允許合成隔離root；真實adapter/host-port未通過資格驗證不得啟用。
G1無erase/purge/compact入口，G2才實作完整清除及工作空間資格驗證；G1不能
以缺少清除路徑放寬資料上限，滿額仍拒寫。各階段另有Issue-first及正式review。

本包不改 catalog 的 source/package 0.24.0，不建立 candidate/release note，
不宣稱當前發布版本；此獨立設計／算式工具不屬installed能力，不另發版。
