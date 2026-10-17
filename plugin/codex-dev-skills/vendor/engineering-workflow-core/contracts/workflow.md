# 共用工程工作流契約

本契約定義工程義務與必要輸入輸出；適用入口由接口或使用專案明確選取。它是純 Markdown，不執行路由、判定、狀態轉移或 runtime API，也不授予相容資格或操作權。正式契約以繁體中文為權威文字；identifiers 與引用原文維持原樣。來源、改寫與保留項目見 [source-map](../docs/provenance/source-map.md)，來源授權見 [upstream-notices](../docs/provenance/upstream-notices.md)。

<a id="wf-stages"></a>

## 工程階段與離開條件

小型工作可合併階段並重用仍有效的證據，不能省略適用義務。普通有界交付不要求 durable loop、native Goal、多代理或排程。

| 階段 | 必要輸入與動作 | 產物與離開條件 |
| --- | --- | --- |
| Discover | 讀有效指引、需求、來源與 repo 身分，依目標、設計與預期影響初判任務風險；有 Git 時核對 branch、HEAD、upstream、remotes、完整修改與 ownership；由接口核對當前公開能力／schema／權限 | 目標、scope、DoD、限制、風險及事實／推論／未知；unknown 不默認低風險，來源衝突先解決 |
| Plan | 選最小一致切片，指定唯一 writer 或不重疊 ownership、依賴、驗收、review 與安全檢查強度／時機；適用時先做 [前提與方案取捨](#wf-assumptions-and-options)，scope 或設計變動重評風險 | 有界計畫；高風險及早深查，不等最終候選；計畫不授權修改、派工或外寫 |
| Implement | 用已授權能力按既有模式完成切片，保留無關修改 | 可讀回的實際 diff 與新增檔案 |
| Verify | 開發期間持續做快速測試及廉價、適用的安全檢查；主代理獨立讀回成果、受保護 tests 與需求，完成必要驗收 | 命令、exit、結果、來源身分、略過／失敗分類；tests 或快速檢查不代替 review／必要 scan |
| Review And Fix | 足夠能力、與作者獨立的 reviewer 唯讀審查當前內容；高風險在設計與實作初期即深入審查及安全分析，有實質 diff 即按必要性做比例 scan | finding IDs、dispositions、修正及重審／重測證據；詳見 [審查契約](review-and-security.md) |
| Docs Sync | 核對行為、需求與限制，依 [簡明寫作要求](#wf-writing) 同步適用文件／狀態 | code/docs/configuration/package/version 一致；保留歷史與未驗證事項；在既有 review 記錄適用寫作要求的抽查 |
| Delivery Gate | 核對驗證、review、授權與所選專案 overlay；已有 change request 另做完整 exact-head review | 內容 readiness、平台 enforcement、操作授權分列，詳見 [exact-head 契約](exact-head-and-evidence.md) |
| Continue | 中斷前保存有界 checkpoint，依 [證據生命週期](#wf-evidence-lifecycle) 維護索引；接續先查當前來源、修改與 ownership | 同一目標、唯一 writer、剩餘 DoD、findings、證據與下一步；session 記憶僅為 advisory |

階段是安排指引，不把深入 review 或安全工作鎖在最後。普通流程可先快速檢查，再獨立 review、修正及重驗，形成較穩定候選；必要安全工作可提早或在無相依衝突時並行。高風險先深查，最終固定版本用於證據綁定與 merge 驗收，詳見 [風險、時機與候選規則](review-and-security.md#review-risk-timing)。

<a id="wf-writing"></a>

## 文件與交付摘要的簡明寫作

本節適用於本工作流產出的自然語言文件與交付摘要。正式契約仍以繁體中文為權威；寫作清楚不保證所有技術文件都適合非工程讀者。依文類與任務採用下列要求：

1. 先確認讀者、目的及所需操作深度，再安排內容。按文類交代目的、必要前提、下一步與完成判準；短回覆可合併表達，不必每次重複四個欄位。
2. 使用直接句型，清楚說出誰要做什麼；一句聚焦一個主題，操作步驟順序明確。一個概念使用一致術語；必要技術詞首次出現時，按讀者需要解釋，保留所需技術細節。
3. 不得為了簡短而刪除安全、授權、證據、必要前提、風險或限制，也不得犧牲技術精度。必要條件、建議與選用事項須能區分。
4. 英文技術文件以 ASD-STE100 Issue 9（2025-01-15）為依據。未完整核對正式寫作規則、受控詞典及適用技術詞，不得聲稱符合。未取得全文時，仍依本節可查核的清晰原則寫作；在適用文件或既有審查報告明示「依 ASD-STE100 原則編寫，尚未完成完整符合性驗證」，不得記為 Passed，也不因此阻擋所有文件。工具檢查或模型自評不能取代完整核對；[官方依據與本次取得範圍](../docs/provenance/source-map.md#plain-writing-update) 另有記錄。
5. 繁體中文採對應的簡明原則調適，不宣稱符合 ASD-STE100，也不稱為官方中文 ASD 標準。不硬套英文單字數或使用無依據的數字規則。
6. 雙語版本的義務、風險、限制與重要資訊須一致；翻譯不改變正式繁中權威。Code、commands、flags、API、paths、logs 等機器字面，以及須保留的引用與授權原文維持原樣，不為自然語言寫作要求改動。

在既有文件 review 中，按變更範圍抽查讀者與文類是否適切、術語與步驟是否清楚、重要資訊是否保留，以及雙語一致性與符合性宣稱的依據。於既有報告記錄抽查範圍、結果及未驗證限制；發現問題沿用 [finding 與重審流程](review-and-security.md#review-findings)。不新增 gate、receipt 制度或認證系統。

<a id="wf-capability"></a>

## 能力選取與替代

1. 保留使用者指定方法及較高優先指令；先讀適用技能／操作入口的必要契約，再選最小相容的直接推理、原生工具、CLI、服務或本地技能組合。不可略過必讀文件、必要工具／驗證器、獨立審查或適用資格程序。
2. 接口只查本次操作相關的當前公開能力與完整 schema、model/provider/effort、資料目的地、context、檔案／網路／憑證邊界。缺事實保留 unknown；初始未列出工具不等於不可用，應依公開 discovery 查核，不可觀察仍為 unknown。一般推理不虛構探測呼叫。
3. 替代方法須逐項保留前置、輸入、目標／scope、讀寫權限、操作、證據、輸出與完成條件。部分相容只重用有效部分並補足缺口；未知、不相容或不可用時採既有安全 fallback。名稱、安裝、help、自述、其他 runtime 紀錄或靜態案例不能證明資格、等價、啟用、授權或完成。不自動讀取或複製其他 runtime credentials。
4. 證據重用先核對內容（含未提交 diff）、revision、scope、假設、政策、階段、環境與新鮮度；漂移時重查受影響部分。保留原始來源／限制，映射回適用輸出契約。新成功是否取代舊失敗，另核對 [替代覆蓋](#wf-evidence-lifecycle)。PASS、自評或文案重排不替代必要證據與完整 exact-head review。
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

工程驗收依當前 repo/Git、必要驗證、獨立 review 與 DoD；Outcome 驗收逐項核對使用者目標、限制及實際可讀回的成果。未執行、失敗、未完成與負面案例依 [證據生命週期](#wf-evidence-lifecycle) 保留情境與結果，不能只記成功案例。Synthetic fixture 只證明列出的 functional outcomes，不能證明模型等價、隔離、獨立 review、正式 gate 或整套 runtime qualification；runtime/model/profile 身分由接口可信查核，私密實測資料不寫入共用庫。

必要 checks 通過後，只因新變更、失敗或未解疑慮擴大／重跑；不能以預算省略必跑檢查、獨立 review 或 changed-head 完整審查。服務、認證、環境、資料、權限及 context 失敗與品質返工分開分類，不能靠提高 effort 解決環境或權限缺失。兩輪未完成 review/fix（或適用明定門檻）觸發假設、方法、能力及 context 重評，並非自動停工、新建話題或無限重構。換模型／session 不清除 findings、修正歷史或預算。

改善驗收在既有報告有界記錄缺口、原因依據與下一步，先核對既有 evidence/proposal/evaluation 契約的涵蓋，再提最小補強。Operational Evidence、proposal、評分、evaluation、重播或 promotion packet 都不是授權或完成證據；不因此新增反思 executor、memory、hooks 或 scheduler。P1 的具體涵蓋評估見 [既有改善契約](../docs/provenance/source-map.md#improvement-coverage)。

中途需求修正保留仍適用成果並重查受影響證據；狀態或旁支問題先簡答再續行，除非明確取消／替換目標。使用者摘要依 [簡明寫作要求](#wf-writing) 清楚精簡；review/gate 產物保留 commands、必填欄位、findings、dispositions、skipped checks 與限制。續行與停止均依 [授權與停止契約](authorization-and-stops.md)。

<a id="wf-assumptions-and-options"></a>

### 檢驗前提、比較方案與停止改善

重要／高風險工作、反覆無效修正、來源／目標矛盾、已知顯著維護負擔，或準備新增具有實質複雜度的 validator、fallback、持久 state、wrapper 等機制時，依本節評估。簡單低風險任務可在既有計畫或報告短述相關判斷，省略無關項目，不強制完整長表或轉入 Loop。

先確認真正目標與根因的已知事實、假設及 unknown，核對共同前提、支持來源、可推翻它的反證與信任邊界。兩位 reviewer 同意同一前提不會製造獨立事實；應檢查來源是否獨立及是否真正支持結論。Timestamp 新鮮、標籤、manifest 或 digest 本身不證明資源歸屬；後來盤點也不能倒證外部工具改寫／轉格式前的狀態。人類同意可授權特定行動，不能自行證明這些事實。

比較足以處理問題的相關選項，例如根因修正、集中邊界檢查、合併／移除重複機制、管理措施、縮限自動化、人工處理或維持現狀；不必無差別列全套。在既有報告記採用／拒絕理由、獨特保障、現有機制不足、維護／審查成本與殘餘風險。新增防護須說明其獨特作用；不以層數、負 LOC 或未量測的成本節省作目標。

管理措施須有實際責任人、可驗證前提、可行的維持方式及失效時的停止／交接安排。沒有可信前提時，不用更多相同來源的 validator 製造確定性；停止或縮限相依的高風險／破壞性自動化，或交由人工處理，無相依且已授權的安全工作可續。人工處理仍須查證、授權及符合 [破壞性操作前置](authorization-and-stops.md#auth-destructive)；主管同意不能取代歸屬證據。簡化不得移除必要安全、獨立 review、操作授權、exact-head、完整性及保存保障。

在既有報告區分下列處置；這是驗收與改善判讀，不替換 [finding disposition](review-and-security.md#review-findings)，也不新增 gate 或自動授權後續工作。

| 判讀 | 處理與停止點 |
| --- | --- |
| 必要修正 | 正式需求／DoD 未達、必要安全或相容性失效、有不可接受退化時，不宣稱完成；在授權與相依條件內修正 |
| 值得改善 | 已達正式要求且有證據支持改善機會，記理由及有界後續；不以非阻擋最佳化無限延後正常交付 |
| 維持現狀 | 替代方案證據不足、收益有限、風險或導入成本過高時，記理由及何種新證據才重評 |
| 需要人類決策 | 涉及重大架構、擴權、產品取捨、明顯支出或超出授權時，先完成無相依安全準備，再提供比較與建議待決 |

研究在既有報告界定問題、目標、範圍、可用證據、合理成本／預算、停止條件與下一步；沒有足以改變判斷的新證據，不重複相同研究。DoD 已滿足、必要風險及 findings 已依規處理後，停止追求理論 bug-free 或無限重構，按原交付流程續行。停止改善不表示免除必跑檢查、必要 review／scan、exact-head 或操作授權；另有 mandatory gap 仍阻擋相依 readiness。

<a id="wf-evidence-lifecycle"></a>

## 長任務的證據生命週期

本節協助執行者、reviewer 與接續者判讀證據，避免反覆載入冗長材料或遺失重要失敗。採用本工作流時，以下是共用預設；專案有效政策可專化位置、保留期與歸檔方式，但不得弱化必要安全、授權、保存義務或指令優先序。分類供人閱讀，不是執行狀態機：

| 分類 | 判讀與保存要求 |
| --- | --- |
| Active（現用） | 支持當前判定或仍被引用；保留可讀來源與判定所需證據 |
| Superseded（已取代） | 已驗證對應替代關係；保留原因、修正、版本及替代引用，不因分類就取得清理權 |
| Unresolved（未解） | 未解、間歇或結果仍不確定；保留失敗情境、結果、已知限制與後續核對事項，不用較新 PASS 關閉 |

成功替代須覆蓋原失敗情境及受影響邊界，記明原版／修正版 revision、scope、outcome 與可讀替代證據。無關測試 PASS、只知其他版本成功或有限單次成功，都不自動取代原失敗或關閉間歇問題。保留精簡原因／修正／版本／替代線索，以及支持必要驗證、review、merge 與 acceptance 的實質證據；摘要不取代 [exact-head 證據義務](exact-head-and-evidence.md)。

未解／間歇失敗、安全或資料遺失事件，以及共享／仍被引用證據，須依專案有效要求及保護例外適當保留；即使標為已取代，也先核對其他使用者與引用。這不表示每份 raw log 都須永久保存。

接續時可先載入索引、摘要及當前必要證據，再按問題補讀來源。減少上下文載入與刪除來源 records 是兩件事；來源缺失須明記未能驗證，不能偽造已驗證或把摘要升格為原始證據。

只有在安全結案時，才對已取代的冗長材料做有界摘要、索引或歸檔。操作前核對專案 retention（保存與清理規則）、保護例外、共享／引用、精確範圍、實際授權及必要 preview／dry-run。缺少保留期間或有效政策不代表立即刪除；先保留來源並記錄待決事項，不自定通用天數。實際搬移、歸檔與清理仍依 [保存及操作授權](authorization-and-stops.md#auth-data)；不可逆刪除須操作當下確認，本文件變更不授權實際清理。

以下僅示意判讀，不是實際操作、刪除指令或保存期限；在既有 review 報告抽查這些情境，不新增 gate 或 receipt 制度。

| 示意情境 | 應有判讀 |
| --- | --- |
| r1 在情境 S 失敗；r2 已完成 S 及受影響邊界的必要驗收 | 記原因／修正、r1/r2、scope、outcome 與替代引用，僅就已覆蓋範圍標為已取代；保留必要 review／merge／acceptance 證據 |
| S 曾失敗，但只看到無關 T 或其他版本的 PASS | 不證明 S 已修正，原失敗仍保留 |
| 間歇失敗後單次成功，或安全／資料遺失事件仍有待查事項 | 不自動關閉；依有效事件保存要求保留相關來源與限制 |
| 冗長材料已有摘要，但其他工作仍引用或多人共用 | 先核對引用、其他使用者與保護例外；摘要與較新 PASS 不釋放保存義務 |
| 沒有可用 retention 政策或未定保留期間 | 保留來源並記待決事項；不推定可刪除，也不虛構通用天數 |
