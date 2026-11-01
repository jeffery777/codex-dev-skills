# 授權與停止條件契約

本契約描述義務，不提供 permissions、approval engine 或 runtime 攔截。權威語言、來源及授權原文見 [工作流](workflow.md)、[source-map](../docs/provenance/source-map.md)、[upstream-notices](../docs/provenance/upstream-notices.md)。

<a id="auth-scope"></a>

## 指令、範圍與操作權

執行前核對當前目標、身分、來源、scope、ownership、環境、有效指引與修改。有 Git 時核對 branch/HEAD/upstream/remotes、tracked/untracked 與完整 diff。以目前 repo/Git／核可平台證據核對事實；舊文件、摘要、receipt、協調狀態與 memory 不能覆蓋指令優先序。使用者指示優先於技能預設，仍受較高優先指令、實際權限及破壞性 safeguards 約束。

明確委託的有界目標可涵蓋必要查讀、規劃、實作、驗證、review 與文件同步；它不自動授予外部寫入或破壞性操作權。授權須追溯到有效使用者指示或適用的核可平台機制。模型／工具可用、派送成功、模板欄位、PASS、review/scan/gate 或任務狀態都只是證據，不能產生權限。

Commit、push、PR/MR、receipt/comment、review submission、immutable share、merge、tag、Release、deploy、清理及 provider-policy 修改，逐項查當前精確目標、範圍、身分、既有授權與適用 gate。已授權且前置通過就續行；內部階段切換不重問同一授權。已授權範圍的局部模式選擇自行處理並記重要假設；缺決策先完成不相依安全準備，依賴答案部分等待。

Readiness 證據與授權分開；[獨立審查](review-and-security.md) 及 [exact-head](exact-head-and-evidence.md) 通過不能自行授權 merge 或外寫。來源 repo 的 GitHub App/ruleset、Issue/branch 規則、CI 與 receipt profile 不默套其他 repo；由各專案明選 overlay，接口依法定／平台及實際有效限制執行。

<a id="auth-destructive"></a>

## 破壞性操作與未知效果

破壞性操作保留明確意圖、精確目標、已理解的影響、可用且查核的 preview/diff/plan、復原方式（或明示不可復原），並確認沒有剩餘較低風險替代。刪除／purge／prune、force push、歷史／ref 覆寫、廣泛或不可逆 API 修改、共享系統 restart/stop/disable、替換／重建、帶刪除同步與持久資料移除均須依有效政策核對，不由一般自主執行指引略過。

不可逆刪除須在操作當下取得明確確認；一般工作包、清理計畫或先前概括同意不能代替。本次證據生命週期文件變更不授權實際刪除或其他歷史證據清理。

工具或外部動作失敗先分類。外部效果未知時保留嘗試與不確定性，透過正常介面讀回；不能盲目重播、刪除或 abort。工具拒絕不代表成功，也不授權改道繞過權限；可採保留同一契約的合規替代，否則如實回報缺口。

<a id="auth-stops"></a>

## 真正停止與恢復

下列情形停止相依操作，繼續不依賴決策的已授權安全工作：

- 目標、身分、來源、ownership、授權或範圍存在未解實質衝突，或範圍擴大。
- 新出現或未解的行為、資料、migration、auth、隱私、付款、部署、基礎設施或信任風險需要使用者決策；高風險驗證不足。
- 必要能力、獨立 review、必要 scan、驗證或 gate 缺失／未完成／失敗／覆蓋不足；缺安全 fallback。
- 真正環境／權限邊界、尚未符合破壞性 safeguards、未授權的外部寫入或明確人類 gate。

風險領域名稱不是停工理由；有界唯讀研究／審查可以繼續。單一內部階段結束也不是停止理由。修正 blocker 並重審後，其他前置與授權仍成立就續行；恢復前重新核對當前內容、身分、ownership、限制與證據新鮮度，不沿用過期完成判定。

提出待決事項前完成可安全獨立處理的工作。說明問題、結果影響、具體風險、選項、建議與理由；技能造成停止時連結實際讀過的 SKILL.md，引用條文並區分明文要求與推論，先核對授權是否已涵蓋。自動核准拒絕時如實說明動作與 stated reason，不把它當新增使用者授權或改變 sandbox 的理由。

<a id="auth-data"></a>

## 持久資料與證據保存

Memory 與其他持久資料依專屬資料契約。Native recall 不等於已資格化管理 backend，不自行切換儲存、雙寫、啟用、遷移或刪除；scope、來源、版本、精確確認、刪除覆蓋與操作證據仍須驗證。本核心沒有資料 backend 或啟用機制。

Review artifacts 是證據，不取代來源真相；當前、被引用、未解或政策要求的歷史證據須保留，依 [證據生命週期](workflow.md#wf-evidence-lifecycle) 核對替代覆蓋、必要 review／merge／acceptance 證據與保護例外。縮短上下文或新增摘要不授權刪除來源。

實際搬移、歸檔或清理前，核對專案保存規則、共享／仍被引用資料、其他使用者、精確範圍及操作授權，並查核必要 preview；清理先 dry-run。缺保留期間或有效政策不推定立即刪除，不自定通用天數；模糊或高價值資料保留並依精確意圖處理。不可逆刪除仍須 [操作當下確認](#auth-destructive)。實際 artifact root 由專案或接口決定，不由核心固定私有路徑。

共用庫不收 secrets、憑證、真實 logs/transcripts/session、機器／使用者識別、私有路徑、runtime state、databases 或 caches；敏感實測證據由接口保存於適當受控位置，公開記錄只保留安全來源、必要限制與可追溯資訊。
