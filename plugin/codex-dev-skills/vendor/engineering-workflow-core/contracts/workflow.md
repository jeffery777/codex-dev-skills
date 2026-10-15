# 共用工程工作流契約

本契約定義工程義務與必要輸入輸出；適用入口由接口或使用專案明確選取。它是純 Markdown，不執行路由、判定、狀態轉移或 runtime API，也不授予相容資格或操作權。正式契約以繁體中文為權威文字；identifiers 與引用原文維持原樣。來源、改寫與保留項目見 [source-map](../docs/provenance/source-map.md)，來源授權見 [upstream-notices](../docs/provenance/upstream-notices.md)。

<a id="wf-stages"></a>

## 工程階段與離開條件

小型工作可合併階段並重用仍有效的證據，不能省略適用義務。普通有界交付不要求 durable loop、native Goal、多代理或排程。

| 階段 | 必要輸入與動作 | 產物與離開條件 |
| --- | --- | --- |
| Discover | 讀有效指引、需求、來源與 repo 身分；有 Git 時核對 branch、HEAD、upstream、remotes、完整修改與 ownership；由接口核對當前公開能力／schema／權限 | 目標、scope、DoD、限制、事實／推論／未知；來源衝突先解決 |
| Plan | 選最小一致切片，指定唯一 writer 或不重疊 ownership、依賴、風險、驗收及 review 強度 | 有界計畫；計畫不授權修改、派工或外寫 |
| Implement | 用已授權能力按既有模式完成切片，保留無關修改 | 可讀回的實際 diff 與新增檔案 |
| Verify | 主代理獨立讀回成果、受保護 tests 與需求，執行必要固定驗收 | 命令、exit、結果、來源身分、略過／失敗分類；tests 通過不代替 review |
| Review And Fix | 足夠能力、與作者獨立的 reviewer 唯讀審查當前內容；依風險完成必要 scan | finding IDs、dispositions、修正及重審證據；詳見 [審查契約](review-and-security.md) |
| Docs Sync | 核對行為、需求與限制，同步適用文件／狀態 | code/docs/configuration/package/version 一致；保留歷史與未驗證事項 |
| Delivery Gate | 核對驗證、review、授權與所選專案 overlay；已有 change request 另做完整 exact-head review | 內容 readiness、平台 enforcement、操作授權分列，詳見 [exact-head 契約](exact-head-and-evidence.md) |
| Continue | 中斷前保存有界 checkpoint；接續先查當前來源、修改與 ownership | 同一目標、唯一 writer、剩餘 DoD、findings、證據與下一步；session 記憶僅為 advisory |

<a id="wf-capability"></a>

## 能力選取與替代

1. 保留使用者指定方法及較高優先指令；先讀適用技能／操作入口的必要契約，再選最小相容的直接推理、原生工具、CLI、服務或本地技能組合。不可略過必讀文件、必要工具／驗證器、獨立審查或適用資格程序。
2. 接口只查本次操作相關的當前公開能力與完整 schema、model/provider/effort、資料目的地、context、檔案／網路／憑證邊界。缺事實保留 unknown；初始未列出工具不等於不可用，應依公開 discovery 查核，不可觀察仍為 unknown。一般推理不虛構探測呼叫。
3. 替代方法須逐項保留前置、輸入、目標／scope、讀寫權限、操作、證據、輸出與完成條件。部分相容只重用有效部分並補足缺口；未知、不相容或不可用時採既有安全 fallback。名稱、安裝、help、自述、其他 runtime 紀錄或靜態案例不能證明資格、等價、啟用、授權或完成。不自動讀取或複製其他 runtime credentials。
4. 證據重用先核對內容（含未提交 diff）、revision、scope、假設、政策、階段、環境與新鮮度；漂移時重查受影響部分。保留原始來源／限制，映射回適用輸出契約。PASS、自評或文案重排不替代必要證據與完整 exact-head review。
5. 小任務在既有報告簡述方式、重用與缺口，不另建無需要的 receipt 或能力清冊；必要 artifacts 仍須產出。文句縮短不證明品質、token、成本或延遲改善；跨模型比較須有代表性配對量測。
6. 批次／並行工具編排由當前 surface 證明可用及相容，未知時採順序 fallback。只有各自授權、固定目標且無相依／共享衝突的有界查讀才並行；相依、approval、mutation、wait/resume 保持順序，限制每項及合計輸出並逐項檢查失敗與結果。具體工具 API 留接口。

<a id="wf-delegation"></a>

## 有界委派與接口責任

主代理按任務推理需求、風險、上下文量與驗證負擔選擇模型、思考深度及角色，由各接口核對實際生效的 model/effort、繼承／覆寫與必要資格。符合需求時可沿用 parent 設定；不固定最高 effort 或永久模型 ID，不用「深入思考」等提示取代有效設定。模型特定提示需實測，不建立 model×effort 完整提示矩陣。

子代理可沿用 parent sandbox 與核准模式，不要求逐個建立獨立技術隔離。角色唯讀工作約束仍生效；作者／reviewer 獨立性及品質資格不因共用 sandbox 消失。若個別任務明定技術隔離，再由接口驗證該要求；對話隔離、縮小 toolsets 或角色提示本身不證明技術隔離。

只有獨立、可驗證並能改善品質或耗時的有界工作才委派，不為配額拆工。Brief 明列目標、角色、ownership、當前來源、DoD、必要驗證、輸出、升級條件與可追溯的授權。主代理負責拆解、整合、獨立驗證、gate 及整體完成；子代理回報需決策的 blocker 與最後 receipt，不能繼承主代理的外部寫入權。多 writer 必須 ownership 不重疊；reviewer 保持唯讀。

缺委派能力採單一 writer；缺 session／排程 API 採手動 checkpoint。缺必要 review、scan、平台或安全執行能力時完成不相依工作並阻擋相依 readiness，不降低 DoD 或製造 qualification。Thread/session/schedule 是各接口獨立操作，另查公開契約、權限、回應與操作後讀回，不由共享工程流程自行啟動。

各接口分別記錄版本、surface、backend、instruction/profile bytes 與驗收範圍；有限支援不等於完整工具、委派、OS sandbox 或自動 lifecycle 合格。共享 Markdown 不宣稱 Codex/Grok 或各 surface 行為等價。核心無反向執行依賴；模型、effort、profile/session 控制、程式接口、validators、安裝與組裝皆由接口承擔。

<a id="wf-verification"></a>

## 驗收、失敗與持續改善

工程驗收依當前 repo/Git、必要驗證、獨立 review 與 DoD；Outcome 驗收逐項核對使用者目標、限制及實際可讀回的成果。未執行、失敗、未完成與負面案例都保留，不只記成功案例。Synthetic fixture 只證明列出的 functional outcomes，不能證明模型等價、隔離、獨立 review、正式 gate 或整套 runtime qualification；runtime/model/profile 身分由接口可信查核，私密實測資料不寫入共用庫。

必要 checks 通過後，只因新變更、失敗或未解疑慮擴大／重跑；不能以預算省略必跑檢查、獨立 review 或 changed-head 完整審查。服務、認證、環境、資料、權限及 context 失敗與品質返工分開分類，不能靠提高 effort 解決環境或權限缺失。兩輪未完成 review/fix（或適用明定門檻）觸發假設、方法、能力及 context 重評，並非自動停工、新建話題或無限重構。換模型／session 不清除 findings、修正歷史或預算。

改善驗收在既有報告有界記錄缺口、原因依據與下一步，先核對既有 evidence/proposal/evaluation 契約的涵蓋，再提最小補強。Operational Evidence、proposal、評分、evaluation、重播或 promotion packet 都不是授權或完成證據；不因此新增反思 executor、memory、hooks 或 scheduler。P1 的具體涵蓋評估見 [既有改善契約](../docs/provenance/source-map.md#improvement-coverage)。

中途需求修正保留仍適用成果並重查受影響證據；狀態或旁支問題先簡答再續行，除非明確取消／替換目標。使用者摘要清楚精簡；review/gate 產物保留 commands、必填欄位、findings、dispositions、skipped checks 與限制。續行與停止均依 [授權與停止契約](authorization-and-stops.md)。
