# Issue #278：單專案唯讀要求串接

## 目標與基準

由 main `7ab2d6dd7e39abdbbcce3d493dc7cdf4518389a5` 承接 #276／PR #277。
先建立並讀回 Issue #278，再建立／push `codex/issue-278-memory-audit-dispatch`，
之後才實作。此包交付可信程式整合、隔離驗收與啟用準備，不啟用真實記憶。

## 範圍與設計

- `AuditHostFactory` 固定已接受的單 root、repository、來源 allowlist、review
  與 qualification，透過可信 `take_grant(request)` 取得當次已接受的授權。
- `AuditRequest` 只有 principal/request/scope 身分，不會批准讀取。
  `AuditDispatch` 先消耗單次機會，再取得 grant／建立 host；失敗不能重播。
- 接入 `audit_report`／`governancectl.main(..., audit_dispatch=...)`，沒有新增
  CLI、環境變數、JSON 或任意 import loader。未配置 production 時仍不可用。
- provider 必須原子消耗已接受要求，包括跨 factory／程序的重播防護；本模組
  不以 RAM ticket 取代正式 authority store，也不自行建立這個控制面。
- 新增程式與 CLI 納入 qualification fingerprint。更新後須重新接受資格。

## 驗收與界限

依 2026-09-21 使用者指示，必要條件是異常處置，並不要求以物理耗盡觸發
`SQLITE_FULL`。故障注入必須進入實際 adapter／SQLite／reader 的處理與清理路徑，
驗證安全分類、內容遮蔽、資源收束、資料未改、無重試、舊要求失效及新授權恢復。
不以偽造最外層回覆代替行為驗收。隔離測試專案即可驗收，不需要真實專案。

保留 default-off、空 production registry、唯讀能力。一般例外只輸出固定結果，
不攔截 `BaseException`，不保證程序被 OS 終止或不可中斷 syscall 的清理。
不擴充 G2、原生記憶、跨專案、物理耗盡、最大 RSS 或硬期限驗證。
正式 root/repository/principal/scope、授權及撤銷來源仍由後續啟用決策指定。

## 交付檢查

新要求及重播／撤銷／期限／控制面例外、SQLite FULL/BUSY/IOERR/NOMEM、
ENOSPC/ENOMEM、reader FD、partial safety、qualification fingerprint；
必要 repository checks／plugin parity、獨立 code/deep/docs review、Security Diff Scan，
PR 後完整 exact-head Merge Review 與 GitHub profile gates。正式啟用、merge、
tag／Release／安裝／部署保留各自授權；本包不自行啟用或發版。
