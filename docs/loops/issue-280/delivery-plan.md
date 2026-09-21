# Issue #280：持久授權 provider

## 基準與範圍

由 main `753feebafbc397211d5bfd864275798cb5dc71cd` 承接 #278。
Issue #280 建立並讀回後，先建立及 push `codex/issue-280-audit-authority-provider`，
再實作。主代理唯一 writer；獨立 security reviewer 審查信任及故障邊界。

新增 host-owned 單專案授權 lifecycle SQLite；使用獨立的已接受空目錄，
沿用既有 owner-only／檔案身分／flock／SQLite 限制，與 managed memory 分離。
磁碟紀錄不產生讀取權。可信 host 每次接受新要求，建立新 UUID 與 RAM grant；
每個 provider 有獨立 session，fork、restart 或新 instance 不恢復舊 grant。

## 狀態與失敗規則

- accept durable commit/readback 後才供應 pending RAM grant。
- take 先消耗 RAM，再以交易寫入 consumed；commit/readback 成功才返回 grant。
- revoke 限原 owner provider，先使 RAM 失效再持久化；foreign provider 明確拒絕。
- consumed grant 的每次查詢仍需原 provider RAM ownership 及持久 consumed 紀錄。
- 儲存／提交結果不明時停用整個 provider，沒有自動重試或宣稱未套用。
  故障排除後以新 provider、新 host 接受要求恢復，舊要求維持不可用。
- tombstone 不刪除或重用；有界列數／容量達限就拒絕，沒有遷移或清理 API。

同 OS 使用者任意 Python／可信儲存回滾不在隔離保證內。跨程序強制撤銷服務、
通用 IAM、持久 grant 恢復、真實資料啟用、G2、發版及安裝不在本包。

## 驗證

隔離 fixture 使用真實 SQLite lifecycle → provider → factory → dispatch →
audit adapter／CLI，驗盤點資料未改、資源收束、報告不洩露原始錯誤。
必要故障注入包含 accept/take/revoke 的交易、commit 前後及 readback、FULL／BUSY／
IOERR／NOMEM／ENOSPC／ENOMEM、重播／併發／程序中斷、最後揭露撤銷及 store 漂移。
不要求實體耗盡；部分初始化／hot journal 不自動修復。

主代理驗證、獨立 code/deep/docs 審查、Security Diff Scan、generated parity 及
required repository checks 後，才 commit/push/PR；PR 後另作完整 exact-head 審查與
CI／receipt／App gate。交付至 PR readiness；merge 與正式啟用保留確切授權。
