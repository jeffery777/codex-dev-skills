# 獨立審查與必要安全掃描契約

本契約定義品質證據與 blocking readiness；實際 reviewer、工具、資格、scan、validator 與 artifacts 由接口提供。正式文字為繁體中文；來源改寫與 license notices 見 [source-map](../docs/provenance/source-map.md) 及 [upstream-notices](../docs/provenance/upstream-notices.md)。

<a id="review-independent"></a>

## 審查獨立性與範圍

按實際風險選一般、深入或專門審查；文件亦以可遵循契約、正確性、缺前置、不安全指引、私有資料、過期路徑及未支持宣稱為重點。Review request 保持唯讀，只有明確轉為修正／實作才修改受審內容。作者不能用自審取代必要獨立 reviewer；reviewer 須有足夠能力及適用資格，與作者保持角色及工作責任獨立。

可使用同一 runtime 的另經驗證唯讀角色／session 或獨立服務。子代理可繼承 parent sandbox 與核准模式，無通用逐子代理技術隔離要求；唯讀 workflow expectation 不等於獨立 read-only sandbox，對話隔離、toolset 限縮及角色名稱也不能證明品質或必要技術限制。明定技術隔離的任務須另驗該條件。

Reviewer 依 DoD、spec、plan、當前內容與適用 gate 審查，先報風險、缺陷、regressions、漏驗證與 blocker，附檔案／位置、來源證據、影響及阻擋理由；測試通過不代表無 blocker。主代理讀回並驗證整合成果，子代理摘要只是協調資料。

符合 [前提與方案取捨的觸發](workflow.md#wf-assumptions-and-options) 時，reviewer 獨立檢查共同前提的支持來源、可推翻的反證、信任邊界，以及方案的獨特保障、維護／審查成本與殘餘風險。共識不取代事實；管理或人工措施須有實際責任、可驗證前提、維持與失效停止／交接方式，不能以同意代替資源歸屬或破壞性前置。確認簡化未弱化必要安全、獨立性、授權、exact-head、完整性與保存；對立證據及 unknown 沿既有 findings／報告保留，簡單低風險任務不要求無關長清單。

<a id="review-required-read-only"></a>

### 必要 reviewer 的有效唯讀條件

凡計入必要獨立審查的所選 reviewer 路徑，包括首選及替代路徑，在當次介面中不得具有能改動受審內容或任務明定受保護資源的有效寫入通道。角色名稱、唯讀 brief、未回報寫入或 Git 前後未變，都不能單獨滿足這項資格條件。

接口須以當次支援且可核實的控制與生效證據，確認相關寫入工具未提供，或相關寫入在操作前受到強制拒絕。核對範圍涵蓋選定介面實際暴露、涉及該資源的直接及 shell／broker 通道；一個工具被拒不能證明其他相關通道已受限。

這項限制針對必要 reviewer 與任務資源，不要求每個子代理另建 OS sandbox 或整台主機所有目錄不可寫，也不以抵抗有管理權者蓄意改寫可信控制或證據為驗收前提。沿用 parent sandbox 仍須滿足當次必要條件；條件不符合、未知或路徑不支援時，必要 review 保持未完成，停止相依 gate 並回報缺口，不用作者自審或仍可對受保護資源寫入的替代者充當，無相依且已授權的安全工作可續。

取得上述資格後，仍須實際完成當前 revision／diff 的獨立 review 與既有 findings 處置。目標、scope 或有效控制改變時重查受影響證據；每個新 head 的完整審查仍依 [exact-head](exact-head-and-evidence.md#exact-transition) 執行，文字測試與資格本身不構成審查完成或 runtime 技術限制的證明。

前述必要 reviewer 有效唯讀條件及其相依停止，得採本段的具體例外：有效寫入通道因必要用途（例如執行測試）無法移除時，使用者可對特定執行環境一次性接受其殘餘風險，允許該環境中的所選路徑計入必要獨立審查，但不得將這項接受記為技術唯讀資格成立。接受紀錄須可追溯至使用者的明確決定，綁定所接受的執行環境與適用規則，並記錄有效寫入通道、保留理由、替代偵測方法，以及偵測未涵蓋的資源、改動或時間範圍；Agent 不自行接受或推定接受。

同一環境與適用規則未變且接受仍有效時，後續審查不需逐次請求確認，但每次仍核對接受紀錄適用於當前路徑與資源，並執行已記錄的替代偵測及實際當前內容審查。環境或規則改變時，須重新取得使用者接受；相關工具或權限、受保護資源及替代偵測的變更均納入環境核對。缺有效接受或必要紀錄時，前述相依停止仍適用，不能沿用其他環境或另一 consumer 的接受。

這項例外保留有效寫入能力及偵測缺口，指示約束或審查前後的 HEAD／status／diff hash 等比對均不等於技術禁寫，也不保證發現審查期間的所有改動。審查期間若偵測到受審內容改動，該次審查作廢並回報，保留原有證據，對重新固定的候選完成必要審查後才可解除相依 gate；未偵測到差異不能倒證沒有改動或歸因於特定 actor。

一次性接受只適用於本項有效唯讀前置的具體例外，不免除作者／reviewer 獨立、實際審查、必要 scan、exact-head、資料保護、操作授權或較高優先及不可豁免要求，也不授予 reviewer 修改受審內容的工作權。

<a id="review-findings"></a>

## Findings、修正與 formal gate

每項 MUST-FIX、SHOULD-FIX、NIT 或其他適用 finding 給穩定 ID 與一個 disposition：`Fixed`、`Deferred`、`Rejected`、`Needs Human Decision`。Fixed 附修正／驗證與重審證據；Rejected 附來源與理由；Deferred 必須有持久後續目標、owner、原因、剩餘風險、驗證計畫與 promotion trigger；Needs Human Decision 保留具體待決事項。NIT 只有明確 disposition 後才可非阻擋，不能從 gate 記錄消失。

每個 finding 另記 `requirement_relation`，以當前已確認的需求與範圍判定為 `in-scope`、`gap`、`no-requirement` 或 `unrelated`，並附需求來源或來源不足的說明。`in-scope` 表示既有需求已涵蓋；`gap` 表示需求尚未涵蓋但有理由提請納入；`no-requirement` 表示沒有需求依據支持所提變更；`unrelated` 表示不屬當前目標。需求來源可以是有效使用者要求、適用 Core 義務或其他有效專案要求，不強制另建需求編號系統。

`requirement_relation` 不取代嚴重度或既有 disposition。`gap` 另標為 `REQ-GAP`，本輪不因該 finding 自行加入需求或實作，記為 `Needs Human Decision`，由使用者決定加入需求、延後或拒絕。`no-requirement` 的新增工作視為範圍擴張，本輪不加入；`unrelated` 依既有 disposition 要求記為剩餘風險或後續事項。使用者決定新增需求後，先重新確認範圍、驗收及受影響證據，再於後續 review/fix 輪次處理；後續輪次可沿用同一 Session。

前述需求關係分類不解除安全、資料遺失、授權或完整性的 Core 阻擋項；阻擋 readiness 本身也不授權越界修正、增加需求或執行外部寫入。

實作流程先修正 blocker，再按受影響邊界重審；可安全修正的其他 finding 一併處理，其餘留下上述完整 disposition。修正後可選足以證明 fix 的最小普通／深入 code/docs review 範圍，記 unchanged 證據仍適用的理由；shared contract、data/trust、generated artifacts、packaging、文件宣稱或假設變動時擴大範圍。

前述可安全修正的其他 finding，限於既有已授權範圍。

Primitive review 提供品質證據；formal gate 在 commit、PR/MR、merge readiness 或明定專案政策時提供 blocking 判定。內容／範圍／來源假設／環境與驗證仍符合時可重用 primitive 結果，不為進 gate 重複同一次審查。Gate 必須阻擋未解 MUST-FIX、缺 disposition、Deferred 缺必填後續資訊或未解 Needs Human Decision；結果明列 PASS／BLOCKED／NEEDS HUMAN DECISION、findings、dispositions、evidence 與 required follow-up。

Pre-commit verdict 只證明所檢內容；已有 change request 後不能直接作 merge readiness。每個新 head 都須完整 base-to-head [exact-head Merge Review](exact-head-and-evidence.md)，比例 fix review 不構成例外。任何 review/gate 都不授權 commit、push、平台 comment/review、merge、publication 或 deploy。

<a id="review-risk-timing"></a>

## 任務風險與檢查時機

任務開始即依目標、設計、預期行為與受影響資料／信任邊界判定風險，在既有計畫或報告記明依據。Scope、設計、實作或影響變動時重評。資訊不足先補查，仍不明就保留 unknown 與限制，不能默認低風險；需要決策或缺安全能力時依 [停止條件](authorization-and-stops.md#auth-stops) 處理。

高風險任務在設計初期就做獨立深入設計審查與威脅／安全分析；已有實作時及早深入 code review，有可辨識的實質 code／diff 即按必要性啟動比例適當掃描，不等待最終候選。認證／授權、permissions、tenant isolation、敏感資料路徑、破壞性行為及信任邊界是重點；深度須涵蓋受影響資料流、控制與失敗模式，不只看改動行數。

開發期間持續做快速測試與廉價、適用的安全檢查。普通流程先獨立 review、修正及必要重測，再形成較穩定候選，是安排指引，不是禁止早期或並行安全工作的硬順序；相依或衝突操作仍依序執行。快速檢查、clean review 與設計分析各有用途，不能替代必要正式 scan。

每次候選、review 與 scan 綁定實際檢查的 revision、完整內容／diff（含適用未提交修改）、scope、假設與證據。固定最終版本是為了證據與 merge 驗收，不是開始深入檢查的前提；進入最終候選時，須核對必要審查及安全證據充分覆蓋當前內容。

<a id="review-security"></a>

## Security Diff Scan 適用性

共用技能與方法提供預設要求。先辨識較高優先指令、有效章程、平台強制及公司不可豁免要求，再核對具有可查證來源、核定權責與適用範圍的有效專案政策。該政策可依 PoC、用途及風險決定特定檢查的方法、觸發條件、深度、時機與適用 gate；未有效調整者沿用共用預設。不得弱化不可豁免要求、必要安全、作者／reviewer 獨立性、exact-head 或操作授權。PoC 標籤、主管身分自述、Agent 評分或工具缺失不自行構成豁免。

依上述權責與政策判定適用性，以下為共用預設：依當次任務風險、當前 diff／scope、實際影響與仍存在的具體疑慮評估，不能只按檔案類別決定。Security/trust boundaries、permissions、authentication、敏感資料、具有安全影響的 executable、dependencies、installation paths 或未解具體 security concern，須完成比例適當的 Security Diff Scan。Markdown／agent policy 也按實際影響判斷。一般 code review 含基線安全檢查，但 clean review 不替代必要 scan。

不確定時先查受影響邊界；未解實質安全風險阻擋 readiness。沒有上述影響時，記錄 examined scope 與 rationale，結論為不適用；未執行或略過不得記為 Passed。Model/effort-only、documentation、generated files 既非自動必掃，也非 blanket exemption；scope／假設變動後重評。

有效政策判定某特定檢查不要求時，記錄政策來源、核定權責、理由與 scope；這是適用性決定，不是欠掃描，也不是掃描 Passed。已確定必要的檢查，若因工具／plugin、權限或環境缺失而未執行，則分別記執行狀態 `NOT_RUN` 與已確認的能力狀態 `UNAVAILABLE`、原因、已覆蓋／未覆蓋範圍及外部補查需求。缺工具本身不是已發現漏洞、不適用或 Passed；尚未查清的能力保留 unknown 與限制。

必要 scan 的未執行、未完成、失敗或 coverage 不足均不可視為通過。結果記工具／方式、當前 diff 身分、完成與 coverage、findings/dispositions、限制；需要獨立安全 reviewer／深入審查時不得用作者自評替代。Credentials、permission/identity/tenant、敏感資料、付款、upload/parsing、external APIs、persistent data/migrations、deploy/infrastructure、supply chain、crypto/randomness 等實質變更須按風險升級審查，檢查 source-to-sink、failure modes、rollback、logging 與驗證充分性。

各接口核對當次公開能力、所需工具／第三方 plugin、實際可用性，以及資料與操作權限邊界；初始清單未列出不等於已確認不可用。正式安全檢查依有效適用性判定及風險選 diff、受影響範圍或必要的更廣分析，不要求每項任務都跑 SAST／SCA，也不機械要求每次 merge 做全 repository deep scan。方法不固定供應商或模型；缺能力不授權自動安裝、啟用、新增付費路線或外傳資料，普通 review 或模型對話不得冒充所欠必要 scan。此為共用通則，不新增 review skill、gate framework、掃描迴圈或通用成本改善承諾。

掃描後內容變動就形成新候選，依受影響行為、依賴與信任邊界補做測試、重審及必要重掃。只重用可證未受影響且仍符合內容、scope、假設、政策、階段、環境與新鮮度的證據，記明理由與 coverage；不盲沿舊 PASS。信任邊界改變或影響不明時擴大分析；新候選不抹除舊失敗、未解 findings 或 [保存義務](workflow.md#wf-evidence-lifecycle)。每個 changed head 仍須完整 [base-to-head Merge Review](exact-head-and-evidence.md)。

<a id="review-publication-data"></a>

### 公開操作的資料檢查

公開 repository 的每次 commit、push、merge，以及擬公開的 tag、PR／Issue 文字或隨附資料，在該動作前須針對預定內容、必要中繼資料及實際目的地做有界敏感資料檢查。檢查範圍包含金鑰、密碼／token、憑證、機密文件、私人路徑、主機與帳號、未核定可公開的真名或 email，以及不必要的執行紀錄；有來源支持的核定公開身分與完整授權 notices，不因字面命中便逕行刪除。

建立 commit 前，先檢查 staged 內容與預定的 author／committer、message、trailers，以及會序列化公開的簽署者資訊與相關簽署設定，不為此取得私鑰、密碼或其他簽署秘密。物件建立後，須在相依公開動作前核對實際 raw object；預先檢查不表示其後產生的簽章或中繼資料已受查核，實際資料不同時重查受影響範圍。

Push 與 merge 檢查須涵蓋本次預定公開或合併的完整 commit 範圍及每個 commit 的原始身分、訊息、trailer 與簽章資料，不能只檢查 HEAD diff。Merge／squash 須另查其預期結果物件的必要內容與中繼資料，tag 檢查須含實際 tag object 與隨附簽章／證書中的公開資訊；簽章可見性檢查不等於密碼學驗證。

檢查以固定物件身分的原始資料為依據，不採用被 mailmap、replace refs 或 pretty／signature 顯示設定改寫或省略的檢視作替代。Push 前須核對實際送出的所有 URL／refspec 及相關 rewrite，不能只憑 fetch remote；PR／Issue 等非 Git payload 須另查該次實際擬發內容與支援的必要 metadata，Git 檢查不代替它們。

內容、來源、範圍或目的地漂移時，重查受影響部分。必要的資料或預期結果未知、讀取失敗或檢查未完成時，停止相依公開動作並記明未驗證範圍，不把 unknown 記為 clean，不以舊 HEAD 或其他路徑的成功補足，也不以公開後讀回倒證事前缺口已滿足；不確定寫入先只讀對帳，不盲目重送或覆蓋他人變更。

這項資料檢查與本節依風險判定的正式 Security Diff Scan 分開；不要求每次公開文字都執行完整正式掃描，也不免除適用的必要掃描、獨立 review 或操作授權。原始敏感證據留在有效政策允許的受控位置，公開記錄只保留安全來源、必要遮蔽類別、結果範圍與限制，不公開私人值或其可猜測 hash；有界檢查不能宣稱已偵測所有秘密或防止所有平台外的人為繞過。

<a id="review-evidence"></a>

## 證據與續行

審查與 gate 明列當前 revision/diff、scope、來源假設、DoD、已執行／略過命令與結果、findings/dispositions、剩餘風險及驗證限制，即使零 findings 亦保留綁定資訊。可機械查核的事實使用 deterministic checks；人或模型審查不可替代，tests 也不可替代語意一致性審查。

適用的 [有界改善判讀](workflow.md#wf-assumptions-and-options) 沿同一報告記前提／反證、採拒方案、必要修正或後續／維持現狀／待決理由與停止條件。區分正式需求未達與非阻擋最佳化；研究預算或停止改善不能關閉必要 gate，也不新增報告制度。

必要檢查待外部補查時，在既有報告記 exact revision／diff／scope、所欠檢查、原因與 coverage、補查責任人（或明示待指派）、證據位置／待補狀態及受影響的交付動作。「待指派」不滿足正式 Deferred finding 的必填後續資訊，也不解除 gate。讀回外證後逐項核對候選與 scope；revision／scope 不符或只覆蓋部分時，不關閉全部缺口，僅重用可證匹配的部分，依影響補查並保留新 head 完整 Merge Review。

工具缺失應產出可讀狀態，不使整體開發一律出錯或停擺；可繼續無相依、已授權且安全的開發。政策確定必要的 merge／release／delivery gate，仍待匹配當前候選的外部證據，或適用政策明確允許、由有權責者依核可流程作成且綁定該候選／檢查／交付動作的正式例外。報告保留例外依據、核定權責、決定、範圍、理由及剩餘風險；例外不把未執行 scan 改記 Passed，Agent 不自行接受風險，也不得越過不可豁免要求、獨立 review、exact-head 或操作授權。能力缺口只阻擋相依操作，仍依 [停止條件](authorization-and-stops.md#auth-stops) 處理。

Clean 內部 review/scan 可續行下一個唯讀或已授權階段；實際授權／環境／風險決策仍依 [授權與停止條件](authorization-and-stops.md)。共享 Markdown、synthetic eval、profile 安裝、service availability 或平台綠燈都不能單獨證明獨立審查、runtime 資格或工程完成。
