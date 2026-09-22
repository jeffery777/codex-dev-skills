# Issue #282：驗收及審查證據

## 已實作行為

可信 host-only 預檢提供 target／source acceptance／authority metadata／實際環境
qualification／RAM pending 的固定診斷，沒有初始化、正文讀取或 grant 消耗。
Metadata 許可另綁完整 target/store、同程序雙時鐘、期限及撤銷；source coverage
與 authority row/schema integrity 保持 unknown。Off 在所有接觸前返回。

Canary 使用原 provider/factory/dispatch/audit。Host 新接受才取得 request；預檢結果
不能授權。Authority 環境 guard 進入原有效性與最後揭露路徑，qualification 失效
close instance，正常 take 維持原有 lifecycle 行為。撤銷 callback 後才取樣時間，
避免環境觀察期間跨過期限仍輸出報告。Managed memory 不改；authority bookkeeping
獨立寫入，未知 commit 不能宣稱沒有套用。

## 驗收來源與限制

`tests/test_memory_audit_preflight.py` 的隔離 fixtures 使用真實 SQLite／provider／
dispatch／report，不以最外層 mock 代替處理：

- off 零接觸、缺件／不符／未知、metadata 許可過期／撤銷／錯配零觀察。
- 預檢前後 RAM/store bytes/mtime 不變，pending 仍可單次消耗；內容涵蓋未知。
- 原 owner／foreign／fork／clock rollback／row tamper，預檢不恢復磁碟授權。
- 預檢後 expiry/revoke/scope/fingerprint/environment/identity 漂移及重播拒絕。
- 最後 disclosure close/revoke/authority identity／環境觀察期間 expiry 清空內容及 digest。
- 停止提供 dispatch，owner revoke/close，故障排除後新 provider/新接受恢復。
- FULL/BUSY/IOERR/NOMEM、ENOSPC/ENOMEM、unknown 在 UPDATE、commit 後及
  readback 受控注入，驗實際 rollback/connection/lock cleanup、安全報告及恢復。

原 authority tests 另涵蓋 BEGIN、INSERT、commit 前、初始化、owner revoke 及未知
結果的既有路徑；adapter/dispatch/report/CLI regression 一併驗證。
使用 `scripts/project-python`（Python 3.12.9／PyYAML 6.0.3）。
必要 repo checks、package parity、正式 reviews／Security Diff Scan，以及 PR 後完整
exact-head／CI／receipt/App 的最終結果保存於 PR 證據；本文件不預先宣稱通過。

Synthetic acceptance 不代表實際正式環境資格。不讀真實記憶、不做物理耗盡、
硬 RSS／deadline、跨程序強制撤銷、G2 或清理試驗；這些是範圍／能力限制，
不是本包待補實驗。維持 default-off、空 production registry、source/package 0.24.7。

## 設計審查處置

| ID | Disposition | 處置與驗證 |
| --- | --- | --- |
| D282-01 | Fixed | pending 只觀察 RAM／clock，durable row integrity 保留 unknown；row tamper／foreign／fork／不消耗測試。 |
| D282-02 | Fixed | authority guard 接入既有有效性與最後 disclosure；callback 後重取時間，失效報告清空測試。 |
| D282-03 | Fixed | metadata 許可綁完整目標、issued/expiry/evidence/revocation；不許可時的觸碰陷阱。 |
| D282-04 | Fixed | authority 實際 statvfs/device 與 store identity 獨立綁定；排除動態剩餘容量及複製 target 標籤。 |
| R282-01 | Fixed | metadata 撤銷 callback 後取時，每次 metadata/runtime/fingerprint 觀察前後檢查許可；callback／root open 期間到期或撤銷的觸碰陷阱與 fd close 測試；移除最後多餘 fstat，直接使用已驗證 device。 |
| R282-N1 | Fixed | 移除 disposition rows 之間的空行，保留同一張表。 |
| CI282-01 | Fixed | Linux CI 的 authority environment 序列化遭 invalid-integer 拒絕；filesystem ID 改存完整十進位字串，驗 unsigned／signed 邊界、實際 canary 及 identity 漂移拒絕，不放寬 canonical counter 上限。 |

第一輪獨立實作審查重現 R282-01，修正後須重審。第一輪正式 Security Diff Scan
已完成；同一候選因目前只有 host TCB 入口、沒有低權限攻擊路徑／權限增量而不列
可報告漏洞，但仍保留為本包 MUST-FIX，不能以安全掃描的分類免除修正。

設計審查不是實作 verdict；正式審查結論及後續 findings 仍須逐項保存並讀回。
Merge 尚未授權；PR readiness 不授予 merge、tag、Release 或部署權限。
