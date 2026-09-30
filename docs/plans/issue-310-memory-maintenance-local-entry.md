# Issue #310：正式本機 memory-maintenance 入口

狀態：使用者委派下的正式入口五操作驗收、actor 比例驗證與獨立審查已完成。operator 同 UID 信任、隔離官方 runtime 與受限容量契約均已接受。
驗證、finding 處置與 gate 狀態見 [驗證紀錄](issue-310-verification.md)。
僅在新隔離 root 完成初始化、啟用、五操作與停用；未接觸既有真實 memory。
基準 `4da847604ba4713a1a4f36b742395bf8fc09026a`，source/package 0.32.0。
本計畫不授予 root 初始化、來源採納、mutation、發布或部署權限。

## 已確認的現況

- #304 已有五操作 GovernanceCore、process-local provider、factory/dispatch、
  canonical preview、TTL／撤銷／單次 execute 與 fresh readback。維護入口仍缺
  production source、confirmation、qualification ports；不能重建另一個 pilot 冒充交付。
- Core 有 `initialize()`，但 MaintenanceAuthority 明確拒絕初始化；正式首用必須
  有獨立操作、接受與讀回。SingleRootRegistry 是 RAM binding，不能從資料檔
  自述建立可信授權。既有 root/main/lock owner、mode、device/inode 檢查可重用。
- PinnedGitReader 僅支援已准許的本機 loose commit/tree/blob；不 fetch，不讀取
  任意 loader，不以 artifact digest 相同推定語意安全或 eligible。
- 現有 production registry 是空集合，屬目前狀態而非本功能不可改的常數。
  新 adapter 的正式登錄需設計、資格、明確接受及審查證據。
- Work budget 必須來自已資格的 J/T/G 上界；fixture 的估值與取樣峰值不能採用。

## 已接受信任模型 D310-01

建議採使用者自行啟動的 operator CLI，將同 OS 帳號的程式與操作人視為可信
計算基底。原 D310-01 的人工限定已由 2026-09-30 使用者明示委派修訂為 D310-01b：
預設 human；agent 在明確委派範圍內審查並接受，證據如實標記 agent。
本次委派限定新隔離 root、public catalog 來源、五操作及最後停用；不授權背景或跨專案操作。
`--actor agent` 只記錄種類，不能自行證明或建立上游委派。CLI 不提供 `--yes`、
`confirmed=true`、confirmation file、stdin 管線、保存確認或動態 import。
確認介面必須是當次 operator 控制的互動终端，完整 canonical bytes 原樣顯示，
再核對當次 action/digest。TTY 存在本身不是人類證明；同帳號程式可模擬互動，
本方案不能防惡意同帳號偽造；維護者已於本任務明確接受此限制。

若要求抵抗同帳號自動化，需另設獨立 OS 身分／受保護的人工驗證 UI 及可靠
接受 evidence。本包不能從 POSIX TTY、argv 或相互一致 JSON 創造這種保證。
後續不以此限制反覆要求 D310-01 接受，也不宣稱抵抗惡意 same-UID。

## 正式操作流程

固定入口為 `memory_maintenance_local.py`；所有接受仍須當次完整 preview 與 action/digest。

1. `maintenance-local init --enabled`：使用者指定單一 repo 與尚不存在的新 root。
   先以無寫入 preview 顯示實際 repo/root、parent 身分、owner/mode、scope、profile、
   policy/build 與建立內容。另接受 `INITIALIZE <digest>`，新建 root 0700／檔案
   0600，以核心 initialize 建庫，獨立讀回 inode/schema/scope。存在或漂移即拒絕，
   不修復、覆寫或清理。未完成建立保留 partial/unknown 及診斷。
2. Binding descriptor 僅記精確 project/root/main/lock 身分與接受時的 fingerprints；
   以受限權限、無 symlink/hardlink、有限長度及原子寫入建立。它不是 grant。
   重啟後仍須 fresh operator 接受；不可因 JSON 自洽就自動啟用。Descriptor 的
   位置、資料欄位與失敗讀回納入實作 review，不存公開 repository。
3. `maintenance-local run --enabled`：先接受本次 project/root 讀取與 operation scope，
   包含候選、當前／指定 retained revision、source artifacts、proof 與 current-only
   recall 所需讀取。等待不持 storage/provider 鎖。資料輸入只作 bounded proposal。
4. 需要採納內容時，operator 獨立審查完整 version 與固定 Git artifact bytes，核對
   支持關係、適用前提、敏感性與 policy；採納失敗／未知就拒絕。新的 validation
   evidence 由 host 綁 reviewed version/provenance，不複製候選自述。Restore 重新
   審查 retained 內容並產生新 revision/evidence；resume 重審當前來源；stop 不採納內容。
5. 接受本次 operation-specific 環境資格，綁 code/SQL/schema/runtime/profile/
   filesystem/root、資格 evidence、期限及 storage bound。Operator 接受不取代實際
   環境／容量證明。必要證明不足就 unavailable，不填假 qualification。
6. 由既有 provider 建新 request/factory/dispatch。完整 core canonical preview 原樣
   交 operator；另接受 `<OPERATION> <preview_digest>`。返回後重新核對 descriptor、
   revocation、UTC/monotonic TTL、來源、qualification 及完整前態，execute 一次。
7. 由新 core/source reader/read-only connection 核對 proof、state/revision/history/
   projection/current-only recall。輸出 applied/not-applied/unknown；輸出故障保留
   已驗證 outcome，未知不重播或假稱 rollback。新程序不恢復舊 RAM grant/handle。
8. 撤銷控制需能在等待後與交易前獨立觀察；descriptor 停用／身分或 fingerprint
   漂移需使 pending request 失效。撤銷機制與跨程序競態在實作前凍結，不能用
   永遠 False 的 callback 充當正式 port。

Default-off 在沒有 `--enabled` 時不讀候選、設定、stdin、root 或來源。每次 run
只接受一個 project/root/operation，無背景服務、原生 memory、G2、任意 loader 或
跨專案管理。Desktop 使用公開互動終端提供同 CLI 路徑；操作者為人類或明確受委派的 agent。
終端不可用時明示 unavailable，不用私有 API 或測試 callback 補足。

## 儲存資格方案 Q310-01

最小方案沿用 256 MiB 合法 profile，單一 writer、固定 SQL、DELETE journal、
page 4096、temp MEMORY、禁止 ATTACH/extension、max_page_count 限制。需要分別
證明初始化與五操作的 disk journal/temp/growth 上界、受支援 SQLite build/VFS 與
filesystem envelope；source 推導與受限資格證據見 [storage 資格](../../skills/loop-engineering/references/memory-maintenance-local-storage.md)，不將取樣峰值當作合格上界。

SQLite 官方 [atomic commit](https://www.sqlite.org/atomiccommit.html) 與
[file format](https://www.sqlite.org/fileformat.html) 說明 journal 可包含 sector padding
與重複 header；不可只用主庫 bytes 加一次 header 推定 J。官方
[PRAGMA](https://www.sqlite.org/pragma.html) 的 max_page_count 限 main DB，temp_store
受 build 條件影響。推論：需要 pin/驗證相關 pager/VFS 行為及有效 pragmas，建立
保守可證上界，再由現況 files 與 committed work 重算；一般成功測試不能取代此步。

若現行 1.25× maintenance envelope 無法容納已證明的 J+T+G，先研究固定 SQL 的
更緊上界或有界 admission；不得靜默增加限額、改 schema、採用全庫理論 growth
卻故意低報 required_work_bytes。需要修改 profile/public contract 時另呈具體設計。
容量無法保證時保持拒絕；實體 FULL/power-loss/硬 deadline/RSS 不在成功宣稱內。

獨立設計 review 發現 exact vendor source、maintenance reserve 僅計數及 initialize
缺 capacity admission。使用者已接受官方 source 隔離 runtime 與版本化
`mg1-local-operation/v1`：容量不足安全拒絕，不宣稱完整 G1/MG1 或滿庫 stop 保證。
使用者另明示不要求實體滿庫實驗；重點是收到 `SQLITE_FULL` 等錯誤後的可控行為，
以故障注入驗證獨立讀回、分類與不重播。初始化仍需建立前／等待後的容量准入。
Operator 環境接受不能取代 fixed SQL、實際 pragmas 與 exact source 的容量推導。

## 實作切片與驗收

單一 writer 沿用本機 checkout；deep/security reviewer 唯讀並保持作者獨立。

| 切片 | 產物 | 完成證據 |
| --- | --- | --- |
| 信任與 root 首用 | local entry、bounded descriptor、init preview／accept/readback | D310-01 接受；取消/既有/漂移/partial fault 零覆寫 |
| 正式來源與環境資格 | fixed Git review、revocation、storage derivation/evidence | reviewed bytes 綁定、unknown 拒絕、qualification drift 拒絕 |
| 五操作接核心 | 同 provider/factory/dispatch/fresh readback | 正式 operator 入口由已授權 actor 完成 add/update/stop/resume/restore，重啟後 fresh 接受 |
| 負向與故障 | focused tests 與 actor 驗收紀錄 | expiry/replay/revoke/source/state/root drift、transaction/output/readback fault |
| 安裝與文件 | skill/reference/catalog/generated parity、首用手冊 | 隔離 fresh install/upgrade 後從正式入口驗收 |
| Review／gate | independent deep、Security Diff Scan、dispositions、formal gate | blocker 修正重審；PR 出現後另做 complete exact-head |

自動 tests 可控制 fault/clock；只能證明機制。正式五操作由受委派 agent 在真實
controlling terminal 逐項審查與接受，如實記錄 actor；不使用 Python callback、
盲目餵入 digest 或 approve flag 補足。本任務尚未指定或接觸既有真實 memory。

所有 Python 用 `./scripts/project-python`。實作後跑 focused maintenance/local/storage
回歸、必要 repo checks/package parity、隔離安裝。更動 core/storage 共用邊界時再跑
完整 shards；只因新變更／失敗／疑慮擴大驗證。Security Diff Scan 在具體安全相關
patch 存在後執行；設計 review 不代替 scan 或正式 gate。

## 版本與授權

功能通過上述 DoD 後評估 pre-1.0 minor 版本；目前不改 canonical version、不編造
候選或發布完成。Catalog 定義 source/package，Release metadata 才證明 publication，
歷史 notes 不改寫。本話題授權到實作、驗證、獨立審查與 PR 準備；commit/push/PR、
receipt、merge、tag/Release、deploy、精確 root 真正啟用各核對其有效授權。

## 伴隨用量觀察

見 [比較與資料缺口](../issue-310-usage-comparison.md)。缺資料不阻止已授權產品工作；
不降低本任務 effort、不讀私人 DB/log/session、不從共享額度推算任務費用。
