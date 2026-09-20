# 唯讀 adapter 與發行評估

## 已實作與啟用界線

`memory_audit.audit_report` 實際呼叫 `GovernanceCore.audit`，在一個只讀 SQLite
snapshot 內完成有界頁面列舉、來源驗證及報告。隔離 Git／SQLite 端到端驗證
使用真實檔案、版本、停止狀態及來源 blob；fixture 的獨立 source acceptance、
人類 authority 與環境 qualification 仍是 synthetic，不能升格為正式資格。
不是只回傳 success 的 report mock，也沒有將 fixture 加入 production registry。

新增可安裝的 `memory-audit` 技能及 report 模組；CLI 的 production host 仍因
空 registry 回 unavailable。能力供受信任 host 整合及隔離驗證，尚未讓一般使用者
盤點真實記憶。不聲稱完整 G1、MG1 或 G2 已完成。

## 正式唯讀啟用的最小可審查方案

下個人類決策須指定一個 principal／repository／root，不能由 agent 的 JSON、
repo 設定或記憶內容建立 registry。沿用 `RootBinding`／`SingleRootRegistry`：

1. Host 在自己的可信程式與權限控制面綁定 canonical scope/profile、root 與
   directory/main/lock identity；現有 root 必須有獨立接受證據，不自動採納庫內自述。
2. 只授予 `audit` capability。`authorize_read` 重新核對本次人類要求、精確 scope、
   有效期與撤銷狀態；不產生 initialize／write／maintenance confirmation。
3. 來源 reader 用 host 擁有的允許集合綁 repository／revision／artifact，限制每次
   bytes／時間並重查撤銷；`RepositorySource` 再核對完整 bytes digest。
   來源 reviewer 另證明語意支持、敏感性及 evidence binding；內容 hash 不是安全資格。
4. `qualify(..., operation="audit")` 綁定目的 runtime／SQLite build／固定 SQL／
   profile／OS／filesystem／temp／host ports 與唯讀的數量、記憶體、時間上界。
   audit 資格不授予 writer 的 J/T/G 或 G2 維護資格；未完成的最壞 profile 保持拒絕。
5. 以隔離 root 驗證這個實際 adapter 的正常及錯誤處置，獨立審查後才提出精確
   factory／registry 變更與啟用目標供使用者決定。本包沒有這項真實啟用授權，
   所以不製造「confirmed=true」、任意 path 或 agent 可改 registry 的替代品。

本次程式、測試及報告已能獨立完成；以上未解的真實身分／權限來源
是後續啟用決策，不能以抽象風險否定已完成的隔離程式驗證。

## 本包版本建議

建議不為 #274 單獨發版：有新增可安裝程式，但真正的一般使用入口仍欠正式
adapter／read authority／資格接受。依 Issue 的「僅內部準備可不發版」原則，
現階段以完整 PR 交付較準確，不為 minor 宣稱擴大 production 範圍。
這不是永久不發版；後續真實唯讀入口達成可使用條件時再評估 pre-1.0 minor，
不預設版號。本包也不是既有已啟用能力的相容性修補，因此不建議另發 patch。

依 release-state contract：source/package 保持 `catalog.yaml` 的 0.24.7，
installer／plugin manifest 同值；不新增 candidate release note，既有 notes 保留
歷史角色。Active guidance 描述穩定能力與缺口，不記 mutable 最新發行指標。
本判斷不需要推定 GitHub 當下最新 Release；未查核 publication truth，
不以 offline release-state／package parity 當成已發布證據。
沒有本包待發布的 commit／tag／Release payload，merge／發行／安裝仍未執行。
