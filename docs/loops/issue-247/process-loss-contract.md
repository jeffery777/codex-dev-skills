# G1 程序重啟讀回契約

本文件描述 Issue #247 的實作契約；本文件本身不是通過證據。僅供新建 test-owned
roots／repositories 的合成驗證；production registry 保持不可變空集合、default-off。
沿用 [G0 proposal](../issue-213/g0-production-proposal.md)、
[envelopes](../issue-213/g0-production-envelopes.md)及
[scope/lifecycle](../../memory-scope-lifecycle-design.md)的來源、身分及外部副本邊界。

## 最小持久證據

現有 v1 proof 已保存 operation ID、preview digest、item/revision/epoch、前後態／
投影 digest、acceptance evidence ID。缺少原 external-copy 比較基準，因此原 preview
隨 process 消失時，來源仍有效也不能判定 applied。

| 選項 | 保留與相容成本 | 判斷 |
| --- | --- | --- |
| 完整 preview 或另一份內容 | 至多 256 KiB／筆，重複保存候選、來源及檔案集合；增加清除邊界。 | 排除，違反本次範圍。 |
| 獨立 evidence table／host journal | 新保留集合、引用一致性、容量與跨提交邊界。 | 不採用。 |
| 在新版 proof 內加入固定摘要 | 沿用每筆 2 KiB、相同 proof 名額／保留期及同一交易；不複製正文或原副本集合。 | 選定；最大寬度 1,324 bytes 已驗。 |

`mg1-operation-proof/v2` 保留 v1 的 G1 欄位，僅增加必填 `readback_basis`：

- `scope_digest = H(scope)`：綁 principal/root/repository/schema/profile/policy。
- `binding_digest = H({scope_digest, directory_identity, main_identity, lock_identity,
  filesystem_id, adapter_fingerprint})`：identity 以整數 pair 編碼；不保存實體路徑。
  來源為已核准 host binding，重新開啟不得採納庫內自述 identity。
- `copies_digest = H({coverage, copies})`：保留原 preview 的已排序、有限、非內容
  副本觀察之比較 commitment，不保存副本 ID 清單或外部路徑。
- `copies_observed_at`：原 preview 中的觀察時間，必須不晚於 proof.recorded_at。
- `readback_until = recorded_at + profile.proof_seconds`：新程序可用此比較證據的
  嚴格到期界線，等於即過期；整數溢位拒絕。不是 mutation confirmation 的展期。

`H` 沿用 canonical JSON／SHA-256。整個 proof 必須 <= 2048 bytes，不截斷。
欄位只能由 core 在重新驗證 preview／confirmation／source／root 後組成，與 item、
version、current projection 同一 SQLite transaction 提交。proof 中既有 operation、
preview、revision、前後態與 acceptance 欄位直接綁定此 basis，不新增可由 caller
提供的 receipt、basis 或 recovery API。digest 是 binding，並非簽章；既有可信 host／
root TCB 不變，不防禦已控制相同 OS 使用者或 host 的攻擊者。真實摘要也可能有推知
風險，因此不自動匯出真實資料，本切片只保存新建合成資料。

## 重新開啟的判定

core 輸出 `mg1-readback/v2`，沿用 v1 envelope 欄位與 result enum。
純 validator 保留 v1 的原 preview 要求，v2 才可使用完整 v2 proof 的 basis。
validator PASS 仍不認證 host 或資料來源；applied 必須由 core 從核准庫的新唯讀
connection 讀回，不能採用 caller 傳來的 proof／preview 或 executor 的返回物件。

依序取得 fresh read authority、核對固定 root/schema、重播所有 proof 的完整狀態
鏈、檢查 request tuple 與 v2 basis、確認該 operation 為鏈中最新提交且當前全庫
state 等於當筆 after_digest、
重新驗證來源、量測 managed files／capacity，並重新觀察外部副本。fresh 副本的
coverage/copies commitment 及觀察時間須與 basis 相容；unknown coverage 不改為
complete，也不表示「沒有外部副本」。

| 證據 | result／意義 |
| --- | --- |
| 所有綁定有效、仍在讀回窗口、當前狀態匹配、來源有效、副本比較相符、容量完整 | applied；只證明精確受管理範圍。 |
| 匹配 durable proof／當前後態，但 fresh source 不可採用 | committed-but-not-adoptable；不是 rollback 或自動 stop。 |
| 匹配 durable proof／當前後態，但後態容量未證明 | committed-capacity-unproven；不宣稱 source 同時有效。 |
| 原 preview 遺失且找不到 proof | state-unknown；不推斷未提交，不重播。 |
| proof 存在但 basis 過期、root binding 或副本比較不相符，或之後合法操作已前進 | state-unknown，保留可驗證的 proof；不把歷史 committed 當成目前 applied。 |
| schema／proof/basis 欄位損壞或鏈不一致 | integrity-failed；不能拿 caller preview 補齊缺少證據。 |
| 沒有 fresh read authority 或合格 binding／clock | 明確拒絕或 state-unknown，不讀取未授權內容。 |
| 非空 journal | state-unknown／recovery-required；不開 DB 恢復、不修改 journal。 |

「proof 有效且存在」只證明歷史提交；applied 額外要求最新提交、目前狀態與所有 fresh 檢查。
既有連續 `sequence` 與 snapshot proof count 判斷最新提交；即使 stop/resume 往返
回到相同 state digest，舊 operation 仍為 state-unknown，不能再次被判為目前 applied。
source 與 capacity 不確定性不能互相代替；單一 result 的優先序維持既有 core 語意，
文件及測試明示它未證明的面向。後續合法操作有獨立新 preview／confirmation；舊
operation 不因查到 proof、過期或缺 proof 而取得重播權。ExecutionHandle 永遠只在
原 core/process RAM 有效，readback 不產生 handle、不消耗或重建 confirmation。

## 格式、保留及相容性

本切片新建 synthetic root 使用 `mg1-managed-content/v2` 與包含 proof-v2 契約的
新 fingerprint。固定 SQL schema 及每筆 proof 2 KiB 限制維持；metadata／proof
家族不相容時拒絕舊庫，不自動採納、升級、搬移或改寫 M1/G0/舊 G1。
既有 G0 合成 v0、production proposal v1、M0/M1/V2b 格式與歷史文件原樣保留。

basis 與 proof 共用 32,768 一般名額及 1,024 maintenance reserve；stop 可用 reserve。
期限到達只失去恢復讀回的充分性，不刪除或延期 proof；G1 不提供 retention。
總 proof payload 上界仍為 33,792 * 2,048 = 69,206,016 bytes，SQLite 頁面／索引／
journal 另計，且受實測 data limit 與 J/T/G 准入限制。不可把 payload 上界當作
SQLite 實際容量或峰值資格。新 contract/schema/runtime 指紋使舊 qualification 不可
直接沿用；合成 budget 仍只測契約，不聲稱 production qualification。

## 必要合成驗證

新 test-owned root/repository 由 parent fixture 明確註冊；writer subprocess 在
before-transaction、after-item-write、before-commit、after-commit 中斷，以及回覆
遺失。另一個獨立 reader subprocess 只收到有界 request／已註冊 host identities／
非內容來源批准 descriptors，完整 preview、candidate、confirmation、handle 不傳遞。
source 仍須讀取固定 Git artifact 並比對獨立批准，不由 stored version 自行批准。

矩陣涵蓋：正常重啟、缺 proof、缺 basis、未知版本、invalid JSON／digest／時間、
到期邊界、principal/scope/root/policy/revision/request 不匹配、external-copy 漂移及
觀察失敗、source/readback 撤銷、後續合法操作、舊 handle／raw request 重播拒絕。
每次讀回比較 managed files 的完整 bytes／identity，拒絕 writer connections。
最大合法 proof 編碼及超限拒絕、proof 名額／reserve 與原 M0/M1/V2b 回歸均需驗證。

APFS ENOSPC 實驗保持 incomplete，不操作保留映像；power-loss、完整 J/T/G、
4 GiB 最壞 lock time、production source/authority/registry 資格仍排除在此切片之外。
