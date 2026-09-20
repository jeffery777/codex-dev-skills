# Issue #274：單專案唯讀盤點

## 基準與責任

Issue #274 先建立及讀回，才建立 `codex/issue-274-memory-audit`。
隔離 worktree 起點為 `eb7e875ad692e4a9db457d37b398cc2dea17712b`；
開始時乾淨、分支無其他 checkout，本包只有一位 implementation writer。
驗證使用新建 worktree venv、tracked resolver、Python 3.12.9／PyYAML 6.0.3。
獨立 reviewer 唯讀，不繼承平台寫入權。

## 最小實作

1. 沿用 `GovernanceCore.audit`，補盤點期限、錯誤資源收束與逐頁身分／權限重查。
   只在 storage 的完整性串流加入可選預算檢查，不改持久 schema、proof 或 mutation 語意。
2. 新增 `memory_audit.py`：一個 snapshot 內有界消費頁面，輸出結構化及人類可讀報告。
   `governancectl audit` 與 `memory-audit` 技能共用它。可信 host 只能由程式組合注入；
   不加入任意 root、設定檔授權、動態 adapter 或 synthetic production registration。
3. 使用既有隔離 SQLite／Git fixtures 做真實端到端讀取、必要故障注入及復原後新盤點。
   測試負責建立資料，報告入口不建立／更新／清理持久資料。
4. 同步 catalog、installer、generated plugin、active reference／milestone／README。
   既有歷史證據與 release notes 保留。production 空 registry、default-off 與未 qualified 不變。

## 狀態與文案契約

| 狀態 | 回報與處置 |
| --- | --- |
| disabled | 記憶盤點未啟用；不查 host、root 或來源。 |
| unavailable | 尚未取得可驗證結果；權限不足、root 漂移、未取得資格、busy／I/O 等明列原因。 |
| partial | 只顯示本次已驗證範圍；分頁、時間、輸出上限或中斷不冒充完整。 |
| complete | 僅代表這個已授權 snapshot 的項目列舉完整；來源覆蓋另列。 |
| source partial | 來源不明／失效／敏感者遮蔽摘要及來源詳情，保留狀態／版本 metadata。 |

任何失敗不回顯例外原文、路徑或內容；不重試、不自動修復、不清理。
恢復後每次呼叫重新取得 core／authority／snapshot，不接受外部 cursor。
容量目前只回 unknown，不用文字量或部分 item 數估算磁碟容量。
host ports 必須自行約束其 I/O；核心期限檢查與 SQLite progress interruption
不聲稱能強制中止任意可信 host 程式或阻塞中的 OS syscall。

## 驗證及發行判斷

focused tests → checks-only validator 與全部 shards → 獨立 deep/code/docs review、
Security Diff Scan、正式 commit gate → PR 最新完整 Merge Review／CI／receipt／App。
必要 checks 通過後，只因變更、失敗或未解問題重跑。兩輪未完成 review/fix 時重評。
不做 APFS／實體滿載研究。本包是否發版依最後可安裝能力與正式啟用邊界評估；
若仍僅為可信 host 整合準備，保留版本，不以新技能名稱宣稱真實記憶可用。
