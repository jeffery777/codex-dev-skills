# 啟用前預檢與隔離 canary

`memory_audit_preflight` 是可信 host 的程式 API，沒有 shell flags、JSON loader、
自動初始化或 production 登錄。`preflight_report(enabled=True, context=...)`
只觀察 host 已接受的記錄。`observed` 不是 PASS、正式資格、讀取權或啟用批准；
缺件為 missing、不符為 invalid、無法確認為 unknown。報告只含固定狀態與安全原因，
不輸出路徑、正文、來源 revision、原始 exception 或機密。

## 明確觀察邊界

`AuditPreflightContext` 保存既有 target、source acceptance、qualification 與 store。
Host 另行給 `MetadataInspection`，綁完整 target digest、精確 authority store、
同程序 clock sample、1–300 秒期限、evidence 及撤銷 callback。這只允許已接受
managed／authority 目錄的 resolve/open-directory/fstat、固定檔名 inventory/stat，
以及本機 OS/Python、獨立 SQLite `:memory:` probe 與固定安裝程式 fingerprint。
不開啟持久 SQLite／lock、不取得 flock、不查 lifecycle、不讀 Git objects 或正文。
沒有 metadata 許可或已失效時，這些觀察不執行；callback 後取時，每個有界
觀察前後重查，失效即停止後續觀察並關閉目錄 fd。這是合作式邊界，無法中斷
正在進行的 OS syscall。off 在驗參數及 callbacks 前返回。
同 OS 使用者可任意執行 Python 不在此 TCB API 的隔離保證內。

預檢可核對 source acceptance 的格式、scope、policy、期限與撤銷，但不讀 managed
versions 或來源正文，因此 source coverage 永遠 unknown。Authority schema、row
integrity 亦保持 unknown，留給執行的既有 provider 驗證。`pending_current(request)`
只觀察原 owner 的 RAM／PID／request／雙時鐘，不消耗、不 pop、不關閉 provider，
也不讀 durable row；True 不代表持久授權仍有效。重複預檢不改 lifecycle。

## 獨立 authority 環境資格

`authority_environment(store)` 只回待接受觀察，不自動產生資格。可信 host 必須另行
接受 `AuthorityQualification` 的精確 environment bytes、evidence、期限及撤銷來源。
觀察綁 authority directory/main/lock identity、store ID、target digest、實際 device／
filesystem identity、穩定 statvfs block-size/flags、runtime、authority schema 與 ports。
Filesystem identity 以完整十進位字串保存 OS 回傳值，避免平台的 unsigned／signed
識別碼超出 application counter 整數範圍；比較仍綁精確值，不截斷或取餘數。
不採 `store.files` 從 managed target 複製的 filesystem/profile/adapter 標籤，
也不把動態剩餘容量列入相等比較。這不是任意 filesystem 可用的資格證明；
synthetic 接受及 canary 成功不能轉成 production qualification。

## Canary 與停止／恢復

Host 先為新的明確要求呼叫既有 `provider.accept()`，再將同一 target/store 的
provider、request、context 交給 `canary_report(enabled=True, ...)`。Canary 不呼叫
accept，也不接受預檢結果作為權限；沿用 provider → factory → single-use dispatch →
`audit_report`。新 authority qualification guard 進入 take 及既有撤銷／最後揭露
路徑；先完成可能耗時的觀察，再重新核對 clock。Managed/source/qualification
仍按既有 adapter 核對，不能用預檢成功跳過。任何已揭露條件失效都清空待輸出內容。

Authority qualification 失效會 close 該 canary provider，避免同要求在解除失效後
重新使用。持久 consume／commit 結果不明仍按既有規則停用 instance，不能說成
未套用。`write_performed=false` 僅指 managed-memory 唯讀；accept／take／revoke
會獨立寫 authority bookkeeping，失敗時亦可能已提交。

停用是在可信入口停止提供 dispatch，並由 owner revoke／close 已核發要求；
不刪除資料。排除故障並核對精確目標後，以新 provider、新 host 接受、新 request
恢復，不回收舊授權。未提供入口仍回 adapter-unavailable。Production registry
保持空；正式啟用仍需另一份精確目標、可信接受來源、實際資格、整合 diff 與停用預覽。
本包不提供跨程序強制撤銷、daemon、G2、清除、輪替或遷移。

隔離測試以真實 SQLite、provider、dispatch 及既有報告驗 FULL/BUSY/IOERR/NOMEM、
ENOSPC/ENOMEM、未知錯誤及提交結果不明的清理、拒絕、保密與新接受恢復。
不要求物理耗盡，不承諾硬 RSS／deadline 或 OS 強制終止仍會執行 cleanup。

固定 synthetic 的可操作入口見 [操作 pilot](memory-audit-pilot.md)；該入口自行建立
新 fixture，不改變本模組的 host-only／advisory 契約。
