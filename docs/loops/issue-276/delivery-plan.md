# Issue #276 交付計畫

基線為 `c23d7ce541c65de1d2fd3ca1d0f908602540b668`；唯一實作分支為
`codex/issue-276-memory-audit-adapter`。Issue 已先於分支建立，原工作任務已停止寫入。

1. 沿用 `LocalHost`／`SingleRootRegistry`／`GovernanceCore.audit`／現有報告。
   新增單次要求的 audit-only authority、固定 Git artifact reader、獨立接受記錄及
   精確環境資格比對；所有接受資料來自 host 程式，不提供 JSON 註冊或動態載入。
2. 支援範圍先收斂為 POSIX 本機、固定 SHA-1 commit 的 loose Git objects。
   reader 不執行 Git、不讀 config、不使用 alternates／replace／網路或工作樹內容；
   不支援的儲存方式明確遮蔽，沒有自動轉換。來源 bytes 相符不等於語意／安全接受。
3. 故障驗收使用同一測試流程建立的暫存 root／Git／SQLite；真實 reader 與
   SQLite、注入的 I/O／時間故障，以及 synthetic 人類接受／資格資料分開記錄。
4. 驗證撤銷、期限、身分漂移、資料完整性、來源遮蔽、鎖定、資源上限與新授權恢復。
   特別檢查安全 partial 的再次授權／完整性判定及 reader／lock 收束。
   依 2026-09-21 使用者範圍決定，以故障處理與恢復為必要驗收；最大規模耗時／RSS、
   實體耗盡與硬資源上限不列入本包 blocker 或後續待辦，未提供的保證保留為限制。
5. 同步安裝來源與 generated package，跑必要回歸、offline release-state 與獨立
   code/docs/deep review、Security Diff Scan，修正 blocker 後重審。
6. 交付精確啟用方案及發版建議。未指定正式 principal/root 與資格接受，不註冊
   production adapter；不加入寫入／維護能力，不發 tag／Release 或部署。

完成證據以當前程式、測試執行及獨立審查為準。使用者已授權更新 Issue，必要正式
審查及 Security Diff Scan 通過後 commit／push／建立 PR，再完成完整 Merge Review，
無 findings 且通過 repo 合併 gate 後合併；不包含真實記憶啟用或發版／部署。
