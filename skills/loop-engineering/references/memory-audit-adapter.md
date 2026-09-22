# 單專案唯讀 adapter

`memory_audit_adapter.AuditOnlyHost` 是供可信 host 整合的可安裝 Python 元件。
它沿用 `LocalHost`／`SingleRootRegistry`／`GovernanceCore.audit` 與既有報告。
CLI `governancectl.py audit --enabled --format text` 仍因 production registry 為空
回不可用；此文件不授予真實記憶讀取權，也不代表完整 MG1／G1／G2 已完成。

## 信任與單次要求

Host 需先接受一個已存在、owner-only 的 MG1 root。`RootBinding` 固定完整
scope/profile、directory/main/lock 的 device/inode；capabilities 必須恰為
`frozenset({'audit'})`。不採納庫內自述，不由 repo 設定、CLI flags、JSON 或
`confirmed=true` 建立信任。相同 OS 使用者可任意執行 Python 的情境不在隔離保證內。

每個要求使用新的 `ReadGrant`／`AuditReadAuthority`／`AuditOnlyHost`。
Grant 綁完整 binding、principal UUID、request UUID、同程序 UTC／monotonic clock
與最長 300 秒期限；host 的撤銷 callback 每次重新查證。Claim 只允許一次，
即使 qualification 或讀取失敗也不重播。這些 RAM 物件不是可持久化憑證；
host 控制面負責只為新的已授權要求建立物件，不能把同一 grant 複製後重新發放。
缺少／過期／撤銷／倒退時間／程序改變全部拒絕。

沒有 initialize、preview/write、recall、readback、maintenance 的授權或 budget。
Off 在 host discovery、參數驗證、資格探測或檔案讀取之前返回。

## Repository artifact reader

`GitRepositoryBinding` 固定本機 repository root、`.git`、`objects` 身分及 repository ID。
`ArtifactPermit` 固定 source ID、完整 40 位 SHA-1 commit、相對 path、完整 SHA-256。
Provenance 只能選中最多 16 個已接受 tuples；最多 16 層 path。Reader 直接讀
loose commit/tree/blob，每個物件驗完整 Git hash，blob 再驗完整 SHA-256。

Reader 不呼叫 Git、不讀 config／HEAD／工作樹、不使用 alternates、replace、hooks、
filters、submodule、網路或 lazy fetch。固定 commit 是明確的來源版本，不追蹤 branch。
拒絕 symlink、非 regular 檔案、非目前 owner、group/world-writable 來源及漂移。
Packed-only、SHA-256 object format、worktree `.git` file 或缺物件回來源不可用，
不自動 unpack／clone／fetch。Source-unavailable 遮蔽摘要與 revision，不能說來源不存在。

每個 object 的壓縮讀取最多 66,688 bytes，解壓最多 65,664 bytes；blob 最多
65,536 bytes。每個 artifact 250 ms、每 chunk 重查授權與 deadline。
這是合作式本機同步 I/O deadline，不能強制中斷 OS 內不可中斷的 syscall。
遠端／網路／FUSE filesystem、任意不受控 host callback 不屬已驗證環境。

來源 bytes 相符只證明內容綁定。`AcceptedSourceReview` 另由 host 接收獨立 reviewer 的
`SourceAcceptance`：完整 version/provenance/scope/policy digest、verifier、evidence、
eligibility、safety、期限與撤銷。Candidate 的 validation 欄位不會生成這份接受記錄。
缺記錄、無法確認、敏感或不支持的內容均遮蔽。已納入報告的來源接受失效，或先前
驗證的 object／目錄身分漂移時，整份待揭露內容清空。

## Audit qualification 與資源 envelope

`AuditQualification` 必須由可信 host 獨立接受，其資料不來自 agent 或 repository 設定。
`audit_environment` 只產生待接受的觀察。比對完整 bytes，包含 SQLite version/source ID/
compile options、Python、OS/release、machine、implementation、固定 schema/SQL、
filesystem ID/device、memory temp policy、profile、固定 host 程式檔案 digest 及 envelope。
Qualification 另綁 root binding digest、evidence ID、有效期與撤銷；程式更新後重驗。

只接受 POSIX Darwin／Linux 的 256 MiB profile：最多 10,000 items、每項 10 versions、
33,792 proofs、每頁 256 items、40 頁、256 KiB 報告、10 秒讀取期限。更大的 profile
及未匹配的環境一律拒絕。SQLite 使用 `mode=ro`、`query_only`、memory temp、zero busy
wait 與 progress handler；記憶體中的版本 digest descriptors 有數量上界，沒有
把完整庫正文載入報告。256 MiB 是資料庫 profile，10 秒是合作式讀取期限，
不承諾最大資料量必定在期限內全部完成。沒有程序級硬記憶體配額或硬時間保證；
MemoryError／SQLITE_NOMEM／ENOMEM 的處理不能當作整體 RSS 保證。

目前測試只接受 synthetic qualification，沒有 production 資格記錄；Darwin 本機測試
不證明任意 Linux／filesystem 組合可用。正式 qualification 必須接受實際 host
ports／filesystem 的行為、既有數量／bytes／期限限制及故障處理證據；未完成時
保留拒絕，不能把 `audit_environment` 的輸出原樣當作批准。

本包以失敗處理與恢復為必要驗收：在實際讀取流程注入適用錯誤或使期限到期，
驗證不改資料、資源收束、安全 partial、失效內容清空及新授權恢復。注入故障
必須經過實際清理／報告路徑，不能只偽造最外層回覆。最大規模耗時／RSS 量測、
實體記憶體或磁碟耗盡、硬上限保證不列為本包 blocker 或後續待辦；只有未來另有
明確容量／效能／隔離需求時才另定範圍。未提供上述保證是能力限制，不是待補實驗。

## 錯誤與恢復

可處理的鎖定、逾時、I/O、ENOSPC、記憶體不足錯誤會停止本次讀取並關閉
reader／connection／lock；不承諾 OS 強制終止或不可中斷 syscall 也能執行清理。
不自動重試、修復、清理或修改持久狀態。部分報告只有在當前授權仍有效且已驗證
snapshot 的持久檔案未變時保留；不能從錯誤類別推論可安全揭露。

使用者再次提出盤點時，host 核對故障已解除，取得新 read authority，建立新 host／
snapshot；舊 cursor、已關閉 snapshot 或已 claim 的 host 不能續接。新要求不代表
可以採納被替換 root 的新身分；那需要重新接受精確目標。報告不回顯原始 exception、
路徑、source 內容或機密；external copies/capacity 未量測時維持 unknown。

## 正式啟用預覽

正式 target 尚未指定。Host owner 需要提供一組精確 principal/root/repository/scope、
固定 artifact permits、獨立 source acceptance、受支援環境及 qualification evidence。
建構順序為接受的 `RootBinding` → `SingleRootRegistry` → 當次 `ReadGrant` →
`AuditReadAuthority` → `AcceptedSourceReview` → `AuditOnlyHost`，最後呼叫既有
`audit_report(enabled=True, host=host)`。這個 factory 應在 host 的可信控制面實作與審查，
每次要求產生新 host，不把一次性 host 永久重用。

本包沒有修改 `PRODUCTION_ADAPTERS`。若未來要讓既有 CLI 的 `local` key 使用 factory，
還須將固定可信 factory 接到 lookup，並驗證每次取得當前要求、單次 claim 與撤銷。
不得改成任意 import-path 或 JSON plugin loader。Repository 工作區／agent 可改檔案
不是正式 authority store。啟用 preview 必須列 target、接受證據、factory/registry 精確 diff、
可回退停用方式及唯讀 canary；待這些實際值指定後才有可批准的 activation payload。

## 單次要求的固定 factory／dispatch

`memory_audit_dispatch.AuditHostFactory` 保存上述已接受的 binding、repository、
permits、source acceptance 與 qualification，以及 host 的 clock／撤銷 callbacks。
`AuditRequest` 僅含 principal UUID、request UUID 與完整 scope digest；request 本身
不是讀取授權。`take_grant(request)` 是 host 另行實作的可信控制面：原子取得並消耗
當次已接受的 `ReadGrant`，沒有授權就拒絕，不能因收到 request 自行批准。
必須拒絕相同 request 跨 dispatch／factory／程序的再次發放；後續資格、建構或
讀取失敗不會恢復 grant。dispatch 本身不提供持久 authority store；
可由可信 host 組合 [本機單次授權 provider](memory-audit-authority.md)。
該 provider 保存 lifecycle，但不從磁碟恢復 grant，也不代表 production 啟用。

每個要求建立 `AuditDispatch(factory, request)`，再由可信程式呼叫
`governancectl.main(['audit', '--enabled', '--format', 'text'], audit_dispatch=dispatch)`，
或 `audit_report(enabled=True, dispatch=dispatch)`。這是同程序 TCB 整合，
不是 shell 可載入的參數。dispatch 的非等待鎖保護單次消耗，先標記已使用才呼叫
factory；跨程序使用、重播與同時使用都拒絕。新 request 使用新的 dispatch、grant、
authority 與 host。關閉模式不消耗 dispatch，也不探測 factory 或讀取資料。
原有 `host=` 程式介面保持相容，但不可與 `dispatch=` 同時使用。

factory 核對完整 binding、principal/request 及 scope，並建立既有 `AuditOnlyHost`。
整合點及 CLI 程式 bytes 已納入 qualification fingerprint。控制面與 host 一般例外
轉成固定安全報告，未知錯誤清空內容，不回顯 traceback／原始例外；`BaseException`
不被吞掉。錯誤處理不自動重試、不修復、不寫入 production registry。

啟用預覽需要：精確目標與來源接受、provider 的原子消耗／撤銷契約、實際環境
qualification、固定 factory/CLI dispatch 的精確 diff、唯讀 canary、停用及回退步驟。
停用方式是在可信入口停止提供 dispatch 並撤銷已核發要求；未配置入口維持原先
adapter-unavailable，不刪資料。僅這份串接程式及隔離測試通過不能批准真實讀取。

可信 host 的[啟用前預檢與隔離 canary](memory-audit-preflight.md)提供有限 metadata
觀察與獨立 authority filesystem qualification；不取代本頁的授權及最後揭露契約。
