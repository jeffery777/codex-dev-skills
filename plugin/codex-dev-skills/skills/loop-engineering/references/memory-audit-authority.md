# 本機單次授權 provider

`memory_audit_authority.AuditAuthorityProvider` 是可信 host 的程式整合元件。
Host 必須先接受精確 root／principal／scope 與每次人類讀取要求，才呼叫 `accept()`；
這個 API 本身不驗證人類身分，不從 argv、JSON、repo 設定或 agent 自述取得授權。
沒有正式人類確認 UI、production registration 或真實資料資格。相同 OS 使用者
的任意 Python／可信儲存回滾不在隔離保證內。

## 儲存與接受

Host 明確建立一個與 managed root 不重疊的空 owner-only 目錄，呼叫
`initialize_store(path, audit_binding)`，獨立接受傳回的 `AuthorityStoreBinding`。
初始化只建立 `managed.sqlite3`／`coordination.lock`；這裡是獨立 authority schema，
不是記憶內容庫。沿用檔名是為重用既有 inventory／identity／flock／SQLite 防護，
不可把兩種 store binding 互換。沒有自動 discovery、初始化、遷移、修復或刪除。
失敗初始化保留部分產物，由 host 另外處置；不能原地重試覆寫。

SQLite 僅含 schema/store/完整 target digest 與 request UUID、provider session UUID、
principal、scope digest、expiry、accepted/consumed/revoked。沒有正文、完整 root
路徑、來源內容、clock sample 或可反序列化的 ReadGrant。每庫最多 1,024 requests、
主檔 page quota 4 MiB，tombstone 不刪除、不重用；達限拒絕新接受，不自動輪替。
這不是總 filesystem 空間或 RSS 上界；rollback journal 可能另占空間。

每次操作核對 owner-only／regular／nlink=1／device/inode、目錄身分與固定 inventory；
非空 journal、WAL/SHM、缺檔、unexpected file、schema/meta 不符皆拒絕，不自動 recovery。
writer 使用 `BEGIN IMMEDIATE`、`synchronous=EXTRA`；reader `mode=ro/query_only`，
busy timeout 0、memory temp、extension 關閉，沿用既有 SQLite 限制。

## 生命週期與整合

1. 建立 `AuditAuthorityProvider(store_binding, audit_binding, clock=host_clock)`。
   新 instance 有新 session；建構本身不開啟 store，也不載入任何 grant。
2. Host 每次接受新的明確要求後呼叫 `request = provider.accept(lifetime_seconds=300)`。
   期限為 1–300 秒；UUID 由 provider 新建。commit/readback 成功後才建立 pending RAM。
3. Factory 使用 `take_grant=provider.take_grant`、`request_revoked=provider.revoked`，
   其餘 root、source acceptance 與 qualification 仍按 adapter 契約獨立接受。
4. `AuditDispatch(factory, request)` 經既有可信 Python CLI 入口輸出報告。
   `take_grant` 先 pop RAM，再核對當次要求與 clocks，commit/readback consumed 後才返回。
5. `provider.revoke(request.request_id)` 僅接受原 provider 擁有的要求，先使 RAM
   失效再寫 revoked；foreign provider 明確拒絕，不能宣稱取消另一個 owner 的要求。
   `provider.close()` 停止該 instance 的所有授權，不宣稱寫入 durable revoked。

RAM grant 只屬原 instance／PID；新 provider、fork、restart 沒有恢復入口。
每次有效性查詢同時要求原 provider RAM ownership 及同 session 的 consumed row。
期限／雙時鐘仍由既有 AuditReadAuthority 檢查。不同程序可以各自接受新要求，
但無法藉讀取資料庫接手舊要求；本包不提供跨程序強制撤銷服務。

## 失敗與結果界限

accept、take 或 owner revoke 在儲存／commit／readback 失敗時，永久停用該 provider，
清空 pending/live RAM。commit 可能已生效，不能把例外說成未套用，也不自動重試。
revocation 查詢失敗回 True，已讀資料會在後續／最終 disclosure 失效；未知錯誤只回
固定安全報告。故障排除並確認 store 可用後，以新 provider、新接受要求恢復，
不重新發舊要求。hot journal／損毀儲存仍拒絕，另需復原決策。

Provider 使用程序內 mutex 序列化自己的 lifecycle，磁碟交易另用非等待 flock。
不保證 OS 不可中斷 syscall／強制終止時的硬期限或清理；trusted clock 不得重入
provider 或執行不受控的阻塞工作。

盤點報告 `write_performed=false` 僅指 managed memory 內容未修改；啟用本 provider
會寫獨立 authority lifecycle。off 在 dispatch/acquire 前返回，不接觸兩個 store，
但 host 先前主動呼叫 accept 的寫入不會被 off 回溯取消。

隔離 fixture 證明 provider 的儲存、消耗、撤銷、拒絕與恢復機制，不代表正式 host
接受流程、來源或 filesystem qualification。部署仍需精確整合、資格、唯讀 canary
與停用預覽；本包維持 default-off 與空 production registry。

可信 host 的[啟用前預檢與隔離 canary](memory-audit-preflight.md)提供有限 metadata
觀察與獨立 authority filesystem qualification；不取代本頁的授權及最後揭露契約。
