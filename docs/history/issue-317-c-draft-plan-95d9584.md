> **歷史草案（PR #317，head `95d9584`）**：以下保存拆分前的 A/B/C
> 工程計畫及當時證據；其中「當前」「下一包」「尚未執行」均是當時描述，
> 不代表 2026-10-07 合併 #322 後的狀態、runtime 資格或可執行指引。
> 現行有限基礎見[工程計畫](../plans/issue-316-local-model-mapping.md)；
> 未完成的真實模型執行與受限 C 工作由
> [Issue #323](https://github.com/jeffery777/codex-dev-skills/issues/323) 追蹤。

# Issue #316 本機角色模型映射工程計畫

## 當前優先順序與本期產品邊界（2026-10-07）

依[需求](../requirements/local-model-routing-and-recovery.md)及
[三層設計與 DoD](../design/native-model-integration-layers.md)，先驗收 A 原生模型
接入與 B 角色選模／返工，再評估是否重啟下一包 C。目標是 Codex CLI／Desktop
主對話與 subagent 的官方模型及 LiteLLM 本地模型；LiteLLM 不接入 Hermes。
CLI、bundled CLI、Desktop 及各自的模型／context／工具資格不能互相推定。

1. A 按 CLI／Desktop × 主對話／subagent × 官方／LiteLLM 的實際公開入口
   建立支援表；先驗證原生配置、工具結果 continuation、串流終結、context
   容量、權限與獨立結果讀回。無公開派工入口者標「尚未支援」，不以合成
   gateway 成功填格；可用入口按具名模型／scope 有限交付。
2. B 沿用現有 classifier、qualification、planner 與返工 lineage。先交付
   default-off advisory；實際切換須分別有 A 的目標資格、目的地授權、秘密
   排除與公開 dispatch 讀回。一般 subagent 失敗由存活主 agent 在已知靜止
   邊界用 Codex 原生編排重新派工；未知效果先查證，不交給 C controller。
3. C 下一包實作暫停。僅保留存活本地 coordinator、單一受管執行器失聯、
   可信 checkpoint 已持久化、舊 writer 已證明停止或隔離的有界情境。
   新隔離副本只在原授權內續作，遲到成果拒收、unknown 不重播，原驗收及
   獨立審查不變；任一前提缺證即停止自動接手並回報。主 agent／coordinator／
   dots 失聯、任意時點／工具／外部副作用恢復不屬本期 C DoD。

下方既有 C 工程包、N1–N4 與測試紀錄保留其發生時的目的、失敗與證據；
凡稱「下一包」「完整 C」「全工具」或 release blocker 的舊段落不覆蓋本節
選定範圍。現有 C 程式與 fixture 保留為 default-off 的有界能力，production
registry 仍空；不刪除持久 unknown 或重寫已封存掃描。工具直接使用者是本地
agent；dots 派工入口不另列本地資格。A/B 的驗收與本期 C 分開，但現有
PR #317 累積 A/B/C 與效率工程、仍是 draft／REVIEW_REQUIRED；一份混合 PR
不能只用 A/B 的 PASS 取得整份 PR readiness。

### A/B 獨立交付的 PR 處置提案（尚未執行）

若要在 C 未完成時先合併 A/B，須先從 PR #317 的最新 base-to-head 差異盤點
A/B、C、共用依賴與安裝資源；以 Issue #316 的新分支從當前 main 製作最小
A/B-only 變更及相應文件／測試，不盲目依 commit 日期 cherry-pick，也不改寫
或 force-push #317。新 PR 逐入口標示完整／有限／尚未支援，獨立完成適用
審查、Security Diff Scan、CI 與 exact-head receipt；#317 繼續保留 C 與原始
歷史為 draft，待 A/B 合併後再核對重疊差異、重新調整 base 與完整審查。
若依賴無法安全分離，先提出受影響檔案與替代切分供使用者決定；不以文件
宣告消除實際 PR 耦合。未取得拆分決策前，只更新本 Issue 與 #317 的範圍，
不建立新 PR 或宣稱 A/B 已可發行。

對 `4451a0d` 的初步唯讀盤點：#317 的 base-to-head 已有 183 檔差異，
早期 `13da0fd` 包含較乾淨的 default-off A mapping 基線；`8123ff0` 的
初版 `model_failover.py` 可作 B 純 advisory 起點，但同一 commit 也加入 C
packet／task execution，不能整個 cherry-pick。現行 `loopctl.py` 入口、
`model_failover.py` 的後續 packet guards 與 `cli_session_handoff.py` 的 C
imports 是具體交纏點。建議先提 A mapping＋Codex 原生角色／已知靜止邊界
返工；若要同時交付新的 B advisory planner，只選初版純決策、
`agent_routing.py` wrapper、`model-failover-plan` 命令及對應測試，排除
`model-task-execute`、journal／packet 與 isolation probes，並做獨立 review。
兩種切法都須
重新核對實際檔案相依、installer／plugin parity、入口資格與原驗收，不能
以這份初盤清單直接生成可合併 patch。
`13da0fd` 的 parent 早於目前 main；`catalog.yaml`、`install.sh`、plugin
manifest／同步器、test shards、roadmap 及 0.34.0 候選說明要按新 PR 的實際
內容重建，不從舊 commit 或 #317 receipt 沿用。A/B 合併後，#317 再吸收
main、處理重疊並核對完整最新差異；若無法安全保留既有 C 工作，須先提出
精確的檔案／狀態處置方案，不清理或覆寫。

## 最小 host 控制接點工程包與當前驗收

### 接續工程包：原始任務輸入與來源 consumer 契約

解除的具體缺口是執行 consumer 尚未讀回原始任務／驗收內容與實際來源。
重用 protected user store、Git 身分查核、現有 routing 與 CLI packet executor；
加入唯讀薄接點，不新增 authority service、恢復框架或 probe。

最小 DoD：具名 task／scope、原始 CLI request（目的地 reference 除外）、驗收
內容 digest、允許目的地及來源 HEAD／Git marker／原 origin／index／指定檔案一致；
派發前及 executor launch 前重查，變更、停用、過期、非正規檔案與偽造 schema
拒絕。同一任務 packet 身分不因新的 input reference 改變，不能避開 unknown。
耗時來源讀回後重讀受保護目標，最後同時核對兩者有效期；若已 claim，失效
維持 unknown，不將有限時效查核宣稱為 OS 原子撤權或完整自動接手。
先做真實 temporary Git／protected-input consumer smoke，再做局部契約及比例
獨立審查、必要 SDS。沒有執行資格／containment 仍為零派發。

這是 operator 輸入限制，不是獨立授權或 runtime qualification。固定 native
reader／admission 不改；一般原生 authority、失聯判定、仍存活 writer 控制與
安全成果整合仍未完成。本包不以輸入通過宣稱真實 C1 admission 或完整 C。
只支援有界指定來源的 raw Git blob／mode 一致性；整個 checkout 的 clean gate
仍由既有 CLI 承擔。Ingress 不執行 working-tree filter；source allowlist 是核對範圍，不是新的
檔案隔離邊界。既有秘密排除、資格、writer 隔離與 review gate 繼續適用。

解除的 blocker：原生 v6 現有實體 readback 仍以歷史 committed_at 表示時間，
且 fixed reader 不提供真實撤銷來源。先加入 host-owned clock／observation／
experimental permit 限制接點；不把匿名實驗授權轉成 production qualification。

DoD：可信 coordinator 的本輪 issuance／captured-source reference、protected
packet 身分、mode 與有效 session 必須一致；實際時鐘由 host 取樣，過期、
rollback、epoch 不明與 descriptor drift 拒絕。撤銷在同一 packet lock 下持久化，
fresh consumer 不復活 permit；撤銷後仍可唯讀觀察，但不新增效果或採納晚到成果。
Historical runtime bytes／C 身分不刷新，actual sample interval 另外記錄。
Control reference 必須持久綁入 admission mode；缺 port 或降回舊 mode 不可
開啟受控 packet。Session descriptor 不繼承給 child，關閉後不得補 issue 或
接任 holder；忙鎖撤銷保持 not-applied，coordinator 停止後續協調，不能宣稱
已撤銷、已停止 writer 或可正常派 successor。

先做接口／型別／session-lock 與既有 consumer smoke，再做局部正負測試、
完整有界深入審查；只重跑既有單一兩次執行 E2E 驗證新接點，穩定後完成適用
SDS。不新增局部 Docker probe。原失敗／unknown／sealed evidence 保留。
此包不完成 journal 的實際 service elapsed budget、一般 authority reader、
來源整合、登入／provider-client containment、N1–N4 或真實模型資格；原完整
DoD／release BLOCKED，draft REVIEW_REQUIRED，production registry 保持空。

2026-10-06 已完成上述有限失聯切片與 host-control 接線實測：producer exit 86／
完整 wait/EOF、原 C 與 immutable refs 保留、實體 runtime 重新確認、不同副本
generation 2 完成 C2，舊 generation 新效果拒絕且零副作用。首輪 consumer
等待逾時的 packet 仍保留 unknown；診斷後只調整匿名 verifier 的 stage／session
有界預算，兩項局部契約及比例獨立重審後，一次 fresh fixture 在 263.35 秒通過。
原受影響模組的 25 項測試及未漂移的十二檔審查重用，不因進入正式 gate 而
全套重跑。正式 Security Diff Scan／pre-commit gate 是保存此 draft head 的
前置；整份 PR 仍 REVIEW_REQUIRED，一般 authority、實際服務時鐘、
真實跨 provider／登入及選定 runtime／工具邊界仍未資格。

下一最小工程包：先解除固定 `FixedReader` 的真實 task/source admission 缺口，
以一個具名本地任務的 host-owned admission/source readback 薄接點重用原
native lifecycle、host control 與完整 gates，不新增協調／排程框架。必要驗證
是 consumer 契約、原 scope／acceptance／source／授權與秘密排除、撤銷／
漂移／偽造 input／資格不足的拒絕；沒有真實 authority 或合格目標仍不得派工。
其他本地 C 缺口依[具體盤點](../design/native-model-integration-layers.md#本地-c-尚缺能力與下一工程包)
逐包完成，不以未驗證 dots 或新增固定故障矩陣代替。

## 本輪最小原生 v6 接手工程包

解除的 blocker：v4 native execution 與 v6 selection／rework／ownership 尚未
接線。一次工程包包含獨立 native mode／domain、真實 transaction lease／artifact
port、原生 predecessor 及 successor recipe、兩個 fresh host processes 的驗證入口；
不另建 retry journal、不接受 fake v4 record、不啟用 production dispatcher。

DoD：舊 R1／B1／R2 consumer 拒絕新 authority；CID／volume／workspace 與原始
artifact 在採認前後維持同 transaction；未提交候選不能授權；lost reply 不重播；
原 checkpoint／失敗／budget／floor／ownership 在兩次實際執行間保留，successor
還原原 C 並產生 C2。必要驗證依序為 source／import／image／回傳型別 preflight、
局部契約與既有 consumer 測試、plugin parity／test shard inventory、完整工程包
前置深入審查、單一兩次執行 E2E、原始證據追加覆核、穩定包的適用完整 SDS。

使用 `scripts/verify-model-native-governance.py --opt-in --preflight-only`，再以相同
入口的普通 opt-in 進行實驗；各次建立新的 fixture，使用已採認 private 0700 evidence parent、
固定已核對的 binary 與 Docker Unix endpoint，加入必要 `--evidence-root`、
`--binary-path`、`--endpoint`。不得重用失敗 CID、unknown attempt 或舊 source
capture 假稱新測試。Source 和工程文件提交；raw evidence／review／scan 不提交。

匿名核心 E2E 已完成：兩個獨立程序各 create／start 一次，producer 的實際 wait／
EOF 早於 consumer 啟動；同一 v6 journal 保存原 C、39 個 immutable refs、失敗
事件與 owner epochs，successor 還原 C 後發布 C2。私有 transport 原始回覆可供
獨立 review 讀回；未知與失敗紀錄保留，不作後續重播輸入。一次實測約 104.5 秒，
不是與舊 v4 路徑同範圍的比較，整體流程成本及節省百分比仍未知。

固定 synthetic grants、固定時鐘與單一 quality event 僅證明此匿名接手路徑；
真實撤權／freshness、elapsed budget、非零升級 floor 與模型品質仍未資格化。
工程包的正式 review／SDS gate 另依最新內容核對，不能由此 E2E 推定通過。
一般 source authority／唯一 integrator、官方訂閱受控登入、可信 observer／撤權、全工具／N1–N4 與真實
context／品質／跨來源驗收仍未完成；完整 DoD、release BLOCKED，draft
REVIEW_REQUIRED，所有原 qualification false。

## 已完成的 journal admission 前置範圍

前置包的起點是 v4 原生實體執行與 v6 saved R2 選模／返工／ownership 治理；
直接包裝兩者會混淆 authority。已將既有 container backend 的 journal admission
與實體 readback 分離，解除 v6 port 無法重用 physical code 的具體相依。
本前置包不另建 retry／ownership journal，也不接受新的模型、來源或登入權限。

DoD：現有 native consumer 使用採認接點；原 descriptor、bootstrap receipt、
phase、fence、immutable artifacts 與物理 policy 保留；未採認輸入及失效 fence
不觸發 CID lookup／start；局部 consumer／v6 相容測試、plugin parity、獨立深入
審查及適用 scan 通過。前置安全 review 後，以一條匿名 native-source E2E
驗證現有原生路徑，不把此次重跑當作 v6 接線成功。

其後的獨立 native mode／domain、同 v6 transaction artifact port、實際 successor
launch 與 predecessor 採用，已由上方匿名核心路徑實測。一般 source authority、受控訂閱
登入及 N1–N4、context／品質／跨來源資格仍是依賴；原完整 DoD 與 release
保持 BLOCKED、draft REVIEW_REQUIRED。

## 需求與範圍

提供 default-off、provider-neutral 的本機角色模型映射。只有受保護的使用者
配置可以替換模型與 effort；保留 canonical class/tier、指令、sandbox、scope、
獨立 review、操作授權與完成契約。配置不進共享 Git 或套件。

CLI 與 Desktop 分別依公開 runtime 介面驗證；不依賴 private API，不從傳輸
成功推定正式角色資格。操作與 schema 見[指南](../guides/local-model-mapping.md)。

## 自動路由擴充需求

本 Issue 後續範圍包含自架與官方模型同時可用的 internal-first 路由，以及
服務失敗與品質返工兩條獨立升級路徑。以下是待實作與驗證的目標，現有
schema 1 mapping 不具備這些自動切換能力，不得以原有測試通過宣稱完成。

沿用既有 `agent_routing.classify_task`、profile preflight／qualification 及
`model-selection-policy.md` 的返工重評規則。官方單一 provider 的既有選模
流程繼續適用；自架目標是新增候選及執行入口，不另建部署者專屬選模腦或另訂
修補門檻。新增 helper 只處理供應商順序、服務預算與返工 lineage 的下一步意圖，
由既有 V2 classifier 綁定當前 class/tier/scope，不得以自填較低要求繞過分類。

| 情境 | 目標行為 |
| --- | --- |
| 自架與官方均可用 | 優先使用適合角色與工作範圍、已取得資格的自架模型。 |
| 已取得新鮮證據確認自架服務不可達 | 略過自架來源重試，選擇已核准且可用的官方模型；不能只憑位置或網路名稱判斷。 |
| 可重試服務錯誤 | 在有界次數及總時間內重試，持續失敗後轉官方；冷卻期間不逐請求重走失敗鏈。 |
| 合理修補後同一核心驗收仍失敗 | 重新分類並補足診斷；能力不足時先升到同角色／scope 已資格的自架來源最高能力目標。 |
| 同工作包兩輪修補陸續出現不同缺陷 | 保留 correction lineage，檢查完整工作流及契約；能力不足時依相同鏈升級，不因 A 變 B 清零。 |
| 自架來源最高能力目標仍無法修復 | 以原驗收與診斷證據轉到已核准的官方目標；重新驗證及獨立 review。 |

「最高能力」由實際角色品質與 class/tier 資格決定，不能由名稱、供應商、
effort 或可連線狀態推定。官方階段仍失敗時改變診斷／方法並持續已授權工作；
不無限升級、循環切模，亦不因達門檻直接停止或放寬驗收。

服務重試與品質修補分別計數。一輪品質修補必須含修正假設、修改與指定驗收；
review finding 本身不等於已完成一輪修補。Scope 真正新增須明確分類，舊失敗
仍保留。環境／權限／資料缺口、context 超限、認證／配置錯誤及外部寫入結果
不明不能直接算作能力不足或通用服務 fallback；外部結果先獨立讀回。

採用者可以預先核准所有本機開發任務使用官方目標，但仍排除憑證與機密。
授權保存在受保護的本機 policy，綁定目標、scope 與可撤銷狀態，不成為套件
對所有使用者的預設授權。送出前須核對輸入、工具結果、歷史與交接包的排除
條件；未知或無法排除的內容不可跨目的地轉送。不得把敏感全文留在證據中。

任務重新分類而提高 tier 時，下一個目的地須符合最新 V2 requirements；已完成
的歷史來源則須核對原 dispatch 當時的合法分類，不能因舊 tier 低於新需求而
阻擋升級。例外須由可信 host 讀回原 request／route receipt、實際 attempt 與
完整 correction lineage，綁定現有 ledger；歷史摘要或可自填的舊 tier 不足以
放行。原 route 的 hash 正確也不能代替有效的 path assignment、disjoint ownership
與同 task／scope／acceptance 綁定的原 authority contract。首包限定同 class 的
tier 提升，當前授權、撤銷、身分、scope 與新鮮度
防護不變；再次選取低 tier 來源仍須拒絕。

### 決策與執行分層

1. 既有選模流程讀取受保護 policy、新鮮可用性／資格及 correction lineage，產出
   可重建的下一步與原因；決策成功不代表 runtime 已執行切換。
2. 執行 adapter 只能使用當次公開 CLI／Desktop 能力，綁定實際 provider、
   model、effort、profile、catalog/context 與目的地。缺公開能力標示未完成，
   不改 private internals，也不以設定檔變更冒充本回合已切模。
3. 切換時建立有界交接包，保留原驗收、finding 處置、目前 diff 與失敗 lineage；
   不盲目重播已執行工具或外部寫入，不拼接不同模型的部分串流回應。
4. 每個目標按實際 input/output/total/reasoning 限制重新核對完整輸入及預留；
   需要時先壓縮或重建交接包。容量不明、不能安全縮減或工具不相容時不可送出。
5. Gateway 的 API retry/fallback 僅處理服務錯誤；品質升級由工程 workflow
   根據驗收與 review 證據決定。透明 alias 換後端仍須識別實際目標及 context，
   不能沿用原模型資格與容量。

本次官方存取路徑明確採用 Codex ChatGPT 登入／訂閱；不新增 OpenAI API
費用，不把 LiteLLM 的 OpenAI API upstream 當成訂閱 fallback。自架端可使用
本機 gateway，官方端須由 Codex 原生訂閱入口執行。不得將 Codex 登入憑證
抽出交給 LiteLLM。兩端的公開執行能力與資料處理政策分別核對。依
[官方驗證方式](https://developers.openai.com/codex/auth)核對；服務路由可參考
[LiteLLM Router](https://docs.litellm.ai/docs/routing)，文件能力不等於本機版本已驗證。

### 擴充驗收

- 離線合成案例涵蓋自架來源優先、自架來源不可達、重試耗盡／冷卻、自架來源高能力及官方
  品質升級、A→B 回歸不清零、原因未知先診斷、外部結果未知不重播。
- 撤銷／scope／資格／目的地漂移、秘密／機密輸入、較小 context、catalog
  同名模型衝突、工具不相容均須拒絕不安全 dispatch；不僅驗證 selector 輸出。
- 公開 adapter 的合成主／子代理循環及切換後讀回另行驗證；Desktop 與兩種
  CLI 各自標示支援與缺口，未完成 adapter 不宣稱端到端自動化。
- 新增跨目的地及返工控制的完整獨立 review、Security Diff Scan 與 changed-head
  Merge Review；原 mapping 審查僅可重用未變動的部分。完成前不合併／發行舊範圍。

### 中斷接手與恢復規則

接手沿用既有 context-continuity 的 digest-bound checkpoint、單一 writer、
lineage 及不重播契約。模型失去連線不代表原程序停止；新執行者啟動前須由
可信 runtime 確認舊程序及其寫入子程序已停止，並重新核對工作目錄現況。
無法確認停止時保留結果不明狀態；只有下述隔離、撤銷與可信 checkpoint 條件全部成立，才允許在另一個副本接手。

Checkpoint 保留原目標與驗收、repository／branch／HEAD、tracked 與 untracked
修改的有界快照、已完成與未完成步驟、測試／finding 處置、失敗與升級原因、
外部操作的已知及未知結果。不得保存憑證或機密；不能以摘要代替實際 diff
及讀回證據，亦不串接中斷的工具參數或模型串流。新目標重新核對整個交接
輸入的 context 預算、資格及資料目的地授權。

接手中的目標保持 ownership，原服務恢復不造成搶占。當前工作單元完成、
產生 checkpoint 且停止 writer 後，才重新評估下一單元；服務可用性恢復須
有新鮮證據及冷卻判定。品質不足導致的升級設為當前任務的最低能力要求，
不能由服務恢復降級或清除 correction lineage。新獨立任務重新分類。

外部寫入 unknown 先獨立查讀，將查證結論追加到原 lineage；不能刪除失敗
事件、把 unknown 改成未執行或重新送出同一操作。接手再次中斷也沿用同一
任務、驗收、ownership 與交接鏈，不重設返工／服務預算。

既有 CLI private-clone executor 僅接受 clean exact source；typed target 支援
不改此條件。半成品交接仍須完成獨立設計與驗證，不能自動 commit 使用者
修改、清掉 dirty files 或偷偷放寬 executor 來取得接手能力。當前一包 dispatch
介面不是持久接手 controller，亦未證明真實 provider 或 production 資格。

必要故障案例包括：寫檔中斷、舊程序尚活著、cleanup 失敗、外寫已成功但回應
遺失、快照後檔案漂移、接手再次中斷、原服務中途恢復、較小 context、以及
重啟後 checkpoint／dispatch replay。所有案例須核對實際 dispatch 與檔案，
不能僅測 selector 意圖。上述行為須經 Astra 深入設計審查及獨立實作審查。

### 持久工作包協調器設計草案

下列是接手 blocker 的修正方向，尚待設計審查與實作，不是現有功能。
父代理保留交付與整合責任；自架及官方模型僅執行有界工作包。協調器不另建
選模分類或品質規則，使用同一 V2 classifier、provider 順位與返工 lineage。

| 狀態 | 必須保留的事實與下一步 |
| --- | --- |
| ready | 已驗證 checkpoint、原始 source 身分／digest、尚無 active attempt。 |
| claimed | 在受保護本機紀錄原子保留 attempt ID／target binding／checkpoint；重播不再啟動。 |
| running | 紀錄 runtime process identity 與唯一 packet writer；服務恢復不能搶占。 |
| reconciling | 中斷、失敗或重啟後讀回受控執行邊界已停止，或確認舊副本已隔離且結果採用權已撤銷；程序樹掃描不足以建立此證據。再核對可封存成果與未知外寫。 |
| checkpointed | 停止寫入後保存修改 digest、驗收／返工／讀回證據；選模前重新核對容量與授權。 |
| integration-ready | 完整驗證與獨立 review 通過，父代理再核對 source 沒有漂移，僅整合已審內容。 |
| blocked | ownership、結果或 snapshot 無法查明；保留成果及紀錄，拒絕相依 dispatch。 |

`claimed` 與 `running` 在 crash 後均不能靠時間過期當成未執行；lease／冷卻
只控制選模頻率，不是停止程序的證明。Ledger lock 忙碌立即拒絕；不能刪除
或重建 ledger 解除未知狀態。恢復使用追加的查證紀錄，綁定原 attempt、
checkpoint 與操作 identity，保留原先的不確定事件。

Privately fenced packet workspace 必須由可信 executor 建立及管理。失敗時
不整合半成品、不清掉可恢復的私有修改；成功的一輪也先保留 checkpoint，
讓下一輪在同一隔離任務成果上修補，直到整體驗收及 review 通過才整合。
初始 user source 的 dirty files 不得自動 commit 或覆寫；若納入受控快照，
需先完成非秘密內容檢查、檔案型別／path／大小限制與一致性核對。

任何 attempt 都不得重新取得 commit／push／PR／deploy 權限；外部寫入由
父代理原有授權與 gate 管理。協調器沒有可信外部結果讀回能力時保留 blocked，
不能由子模型文字、自填 JSON 的 `stopped: true` 或 exit code 推定安全接手。

### Writer containment 資格缺口與待決範圍

深入 review 的受控本機程序反例顯示：root process 在首次 inventory 前已退出，
detached descendant 仍存活時，既有 polling tracker 可返回成功。Polling 不能
證明從未觀測到的子程序不存在；即使補強 root birth identity 也不能據此完成
writer containment 資格。Portable 公開 CLI 尚無本專案已資格的完整停止保證。

因此 `PACKET_STOP_ADAPTERS` production 清冊維持空，packet executor 及共用
consumer 在派工前拒絕未資格的執行路徑。測試的 synthetic stop adapter 不得
被當成 production adoption。現在已實作的 durable claim／checkpoint primitive
及受控接線保留，不能以其離線測試通過取代停止保證。

採用隔離副本、可信監督器及單一成果整合器的完整寫入路徑。模型及其背景
程序只能修改本次 attempt 的副本；來源、封存 checkpoint、ledger、其他副本、
主機控制介面與憑證不得暴露為可寫資源。不同目錄或同 UID 的權限不足以證明隔離。

舊執行環境無法確認停止時，僅在可信主機即時讀回隔離仍有效、外部效果已排除、
舊 generation 已撤銷結果採用權後，允許新副本從上一個封存 checkpoint 接手。
不讀取舊環境的即時半成品，亦不把 quarantine 記為程序已停止。晚到結果必須拒收。
原模型恢復不搶占目前 attempt；工作單元完成後才重新評估。

Linux 優先資格化受限 rootless container 與受控生命週期；cgroup 只提供程序與
資源管理，另需檔案、憑證、控制介面及網路隔離。Mac 可使用本機 Docker Linux VM
提供相同邊界，或其他獨立資格的隔離環境。公開 CLI 的 native permission profile 可作另一候選，
但 shell 的讀寫拒絕不能證明內建工具、繼承 FD、子程序、網路與憑證排除全部合格；
每個入口均須逐項驗證。未具備資格時保留安全暫停與確認停止後
續作。這些規則也適用官方訂閱模型的服務失敗，不能推導 API 付費 fallback。

合成容器測試只能驗證有限的隔離性質。正式 adoption 仍須驗證啟動前隔離、重啟、
撤銷、可信輸出擷取、外部效果讀回及成果整合；production adapter 清冊在完整資格
通過前維持空，不因單一主機測試成功開放自動接手。

正式資格依下列順序完成，每項須綁定執行檔、profile、工具清冊與環境身分，
不能由其他主機或入口的合成測試代替：

1. N1：檔案讀寫、rename、link、symlink、繼承 FD、背景／脫離程序，及 TCP、
   UDP、Unix socket 的邊界；另核對控制介面、資源上限及重啟後隔離是否仍有效。
2. N2：使用合成 provider 驅動真正 CLI dispatcher，逐項驗證所有啟用工具、
   nested CLI、hooks、project config 與 escalation；未驗證入口停用。未解析
   native metadata 的實驗不得作為工具清冊資格。
3. N3：可信 prepare／launch／inspect／quarantine／export 與唯一整合器，
   驗證 crash、重啟、撤銷、late result fencing、checkpoint 擷取及重放邊界。
4. N4：逐 provider 驗證真實自架來源登入及官方訂閱入口、credential broker 與
   機密排除；以當前 context、能力及授權證據完成新 target 的資格。

本 Issue 的發行評估必須涵蓋上述資格與端到端交付驗收。只有合成隔離測試、
default-off primitive 或純選模決策通過時，不得以完整自動切換功能發行。
控制面與 worker bridge 的候選設計及公開 CLI 限制見
[隔離模型執行與可信接手](../design/isolated-model-execution.md)。

### 可重跑的局部驗證與剩餘資格

N3-A 已提供 host-injected backend 的 durable supervisor：啟動前保留 runtime
身分及 launch intent，恢復只 inspect 原 runtime，不重播 launch；停止及封存
成果經綁定與 generation fence 後產生 integration candidate。Unknown observations
保留於同一 ledger，查證後追加 resolution，不刪除原事件。Candidate 讀回同時
核對實際 checkpoint 與 sealed bytes；合法空 patch 仍須通過相同控制。
此介面另接入固定合成 recipe 的本機 Docker backend（N3-B1）；create 後的
physical descriptor 必須在同一 ledger 封存，才可 start。恢復只讀回 exact ID，
回覆遺失不重建或重啟。Bounded export 不執行 worker Git，累積 checkpoint
不丟失前輪成果。Production backend／來源整合器仍未資格化，亦未驗 daemon restart。
原始 execution 身分的首次採認仍須 qualifier；共享 daemon 的首次啟停時間
觀察不能排除曾再次 start，缺證明時不發布 integration candidate。

B2 已實作私有、獨占 synthetic Git source 的唯一整合 fixture；固定 add-update
與 noop 產生持久 intent，crash／reply-lost 只讀回，部分完成保留 unknown。
授權與驗收／review artifacts 僅供固定 fixture，不授予使用者 repository 寫入權。
Schema4 與原 ledger 共存；任何 integration record 阻擋後續 claim，正式整合後
續作尚未資格化。CLI／Docker 實測須另有當前入口證據，單元測試不代替它。

N1 probe 擴充固定合成檔案、rename、hardlink、symlink、繼承 FD、背景程序與
TCP／UDP／Unix socket 正反控制。缺少工具或正控制失敗時保留 unknown；不能
以工具不存在推定隔離成功。它尚不涵蓋 detached Codex、重啟及全部資源邊界。
N2 的固定 PreToolUse hook 故障案例需先讀回 hook 執行標記，再核對 OS 唯讀
邊界；hook 錯誤不能成為唯一寫入防線。全部啟用工具與配置入口仍須資格化。

官方訂閱另有固定無工具回覆 smoke probe，保留實際 CLI、catalog、使用者
instructions digest 與診斷計數，不抽取登入憑證。短請求成功不證明角色品質、
完整 context、credential broker 或 provider/model 獨立讀回；未解的 CLI
diagnostic 仍記為缺口。自架模型不可達時仍可完成以上實作與合成驗證，自架來源
真實連線、工具循環、品質升級及接手驗收則延後，不能宣稱端到端完成。

對未曾派工的不可達自架來源，選模介面可由可信 host 注入 `UnusedSourceGuard`：
真正 packet ledger 須已存在且從未使用，另有新鮮治理讀回，綁定身分、授權、
撤銷、task／scope／acceptance 與舊能力證據。只有能力資格 TTL 過期可被略過；
官方目的地仍須全部新鮮資格。JSON 或空 events 不能建立此權限；缺 guard 保留
原保守行為。此規劃 snapshot 不授予 dispatch，production governance reader
及 executor 的再次核對仍須另外接入。

匿名 public app-server probe 另驗證 no-environment 與固定 dynamic tool 的有限
正反控制；host-only stdio transport 保留 unknown、不重播及 direct-child-only
退出讀回。它仍未建立完整工具／憑證清冊、隔離 worker bridge 或實際派工能力，
也未將 C1 治理 reservation 轉為 executor claim。自架來源不可達不是這些本機接線
工作的阻擋原因，不能把待自架來源驗收誤寫成唯一剩餘項目。

匿名配置觀察另使用 public config／requirements／thread feature／MCP status
readback；固定保留啟動前隔離與 thread 快照未資格化，未知配置在模型 turn 前
停止。專用官方訂閱 home 的登入流程仍需採用者確認，不能抽取目前登入憑證。
單一 ledger 的實際 execution claim／lifecycle 接線須先完成 v6 設計審查；
v5 reservation 不因 metadata 觀察成功而取得 writer 權限。

## 設計與實作順序

1. 核對公開 runtime/schema，使用有界合成資料驗證主／子代理工具循環。
2. 載入 protected default-off store，只允許 model/effort 兩欄替換。
3. 綁定當前 provider、runtime、model/effort、canonical/effective profile、scope、
   quality/context evidence 與逐模型 catalog；缺件或漂移停止。
4. 在 route/receipt/integration 重新驗證資格與新鮮度，禁止靜默 fallback。
5. Installer 保留 user-owned target，同步文件、測試及 generated package。

## Schema 1 的 Context 與驗收條件

- 未啟用時保留 baseline；啟用不能降低 class/tier、擴權或切換資料目的地。
- 無效、不可用、撤銷、漂移、scope/runtime 不符皆停止，不自動換 provider/model。
- 更新不得覆寫 user mapping；consumer 拒絕損壞 receipt 時保留既有回報契約。
- 逐模型核對實際部署的 input/output/合計限制、推理計算與超限行為。
- 完整輸入加輸出／推理預留與安全餘裕不得超過實際容量，提前壓縮。
- 容量未知時不採用；設定合理性檢查不能取代逐 request enforcement。
- 真實 catalog 載入、長上下文、壓縮後工具續答與角色品質須另外取得證據。
- 不把 standalone CLI 的驗證當成 Desktop 保證；不把合成資格當 production 資格。
- 自架後端／gateway 離線時不得自動跨 provider 切回官方模型。Unavailable facts
  應停止路由；尚未觀察到離線的 facts 不保證請求成功。網路環境切換須重新
  核對 provider、store、baseline 角色載入、catalog/context 與 runtime facts。

以上是現有 schema 1 的邊界；自動路由擴充必須另外明確啟用及完成前述驗收，
不能把配置損壞、資格撤銷或目的地漂移解讀為可 fallback 的服務錯誤。

## 證據位置與重建

需求、設計、測試與以下程序受 Git 追蹤。執行輸出與 review/gate 收據存放
`.work/verification/issue-316/`，已由 `.gitignore` 排除。歷次輸出使用不同 run
目錄，保留失敗及過期結果。它們不是套件內容，也不能提交為公開文件。

在 repository root 使用以下程序；不連線自架 gateway，不修改 provider 配置。
全部 Python 驗證使用 pinned resolver。先核對 working tree，確保新的受審檔案
已納入 Git diff；未追蹤來源須另列路徑與內容 digest，不能只記 HEAD。

```sh
mkdir -p .work/verification/issue-316
evidence_dir=$(mktemp -d .work/verification/issue-316/run-XXXXXX)
git rev-parse HEAD > "$evidence_dir/head.txt"
git diff --binary HEAD > "$evidence_dir/working-tree.patch"
git status --short > "$evidence_dir/status.txt"
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version); print(yaml.__version__)' > "$evidence_dir/environment.txt" 2>&1
printf '%s\n' "$?" > "$evidence_dir/environment.exit"
./scripts/project-python -m unittest tests.test_loopctl tests.test_local_model_mapping tests.test_agent_routing -q > "$evidence_dir/tests.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/tests.exit"
./scripts/validate-repo.sh --skip-unit-tests > "$evidence_dir/structure.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/structure.exit"
./scripts/project-python scripts/sync-plugin-package.py > "$evidence_dir/package.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/package.exit"
git diff --check > "$evidence_dir/diff-check.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/diff-check.exit"
git diff --binary HEAD > "$evidence_dir/working-tree-after.patch"
cmp "$evidence_dir/working-tree.patch" "$evidence_dir/working-tree-after.patch"
printf '%s\n' "$?" > "$evidence_dir/source-stability.exit"
```

必要時另在新 run 目錄執行全量：

```sh
./scripts/project-python -m unittest discover -s tests -q > "$evidence_dir/full-tests.log" 2>&1
printf '%s\n' "$?" > "$evidence_dir/full-tests.exit"
```

核對所有退出碼與 log；有缺件、失敗、略過或來源漂移不能直接判 PASS。
`--skip-unit-tests` 只驗證結構，不能稱全量測試通過。比例重驗須在 review
收據說明修正範圍、未重跑項目及重用證據的理由；保留原失敗結果。

以上可重建離線驗證的內容與判定，時間／耗時等欄位不保證相同。Runtime
PoC、模型品質、容量與 Security Diff Scan／人工 review 必須另外按當前環境
重新執行；不能由單元測試產生先前的 scan ID、finding 處置或 live 觀察。

## Review 與交付邊界

Code review 檢查實作、驗收條件、適用證據與 finding 處置；merge review
重新核對當前完整 base-to-head、來源／diff digest、證據範圍、新鮮度與剩餘缺口。
Reviewer 不能只看 PASS 摘要；本機證據不在其 checkout 時須重跑，或使用核可
artifact 交換機制。Security 原生 scan 收據留在工具管理位置，以 ID／digest
定位，不搬入追蹤文件，也不宣稱測試可以重建安全分析結論。

本項為 additive pre-1.0 minor candidate；source/package 版本依 catalog，
候選紀錄與 publication truth 分離。Commit/content push／PR、exact-head、
merge、tag/Release、安裝與清理各自核對授權與 gate。既有 memory production、
M2／V3-C gates 維持不變。


### v6 前置：共用持鎖規劃接口

`PacketStore.planning_context(fd)` 只在 caller 已取得同一 store lock 時建立
host-only context；UG／HSG／RUG 與 V2 classifier 共用同一 snapshot，不再次
取鎖。Context 離開交易即失效，前後核對原始 ledger bytes、store、完整 root／ancestor、lock FD／path 與 directory
identity；沒有 JSON loader，也不授予 dispatch authority。既有 v2–v4 證據
仍按原規則核對；v5／v6 尚未接入，不能把這一前置接口當成 execution claim。

下一包採單一 ordered journal 的 v6 全部 synthetic lifecycle：原治理 request
與實際 execution request 分別保存；acquire、once-launch、unknown readback、
checkpoint、terminal release 及 successor 共用同一歷史與預算。正常 completed
先作為 objective terminal，不能偽造 failure 或清空 history。非空 v2–v5 不遷移，
沒有可信 objective locator 或停止／隔離證據就拒絕接手。完整流程與 crash、
revocation、alias、原始 bytes 漂移負例須同包審查，production registry 保持空。


### v6 synthetic lifecycle 候選範圍

候選實作已接同一 ledger 的 admit／actual acquire／once-launch／unknown
observation／cause resolution／seal／publish／terminal release／successor。
不重播 launch／export；隔離存續時從先前可信 checkpoint 或初始 source 接手。
正常 completed 關閉 objective，不增造服務或品質失敗。原始 events、獨立的治理
與 execution bytes、floors、預算及 canonical alias locator 均持久保存並完整回放。
Revocation 保留 host containment 讀回，禁止新模型效果。舊入口與非空 v2–v5
不遷移、不降版，dirty source 不採認。

效果前與成果採用前另重核來源、sticky revocation 與 retained writer containment；
acquire 後的漂移不能沿用先前許可。Export intent crash 的安全 quarantine 不重播
export，保留 predecessor 及原始失敗計數。Execution generation 與 owner epoch
採嚴格整數契約，bool／float 不能作為相同值採認。

驗收以 synthetic 固定 backend 與獨立 host 原始檔案為限，尚不接實際 provider、
Docker／app-server writer 或使用者工作區。完整 runtime／quality／context／
credentials qualification 維持未完成；V6 stale-unused 接線見下一節，legacy
例外不移植，historical-tier 仍須另接，不能以 fixture 通過替代。


### v6 未使用來源接點的合成實作

接線範圍為特定 source 從未 actual acquired 的 V6 私有 guard，包含初次 official
接手與 official 同 stage retry。完整原 execution／prefix 回放、每次新 proof、
原 archive 與目前 destination qualification 分開；沿用既有 selector，不建立
第二份 retry journal，也不偽造 legacy artifact。驗收需涵蓋 source 已 acquire
但未 launch、source ID／identity 改名、proof／prefix／runtime／destination 漂移、
callback fence、目前權限／context 過期、未知效果、服務及品質預算耗盡。
Legacy unused 語義與非空 v2–v5 blocker 保留；historical-tier 仍需另接。


### v6 歷史能力需求接點的合成實作

Schema 3 接線使用原 actual-acquire journal；不移植 legacy HSG artifact，
不把 event 數量當成 execution generation。新 claim 的完整歷史 proof 與目前
source／destination observation 分開；來源只適用最高原需求，仍要求新鮮、未撤銷
及相同 identity／scope／class。新目標符合目前分類與完整 context／executor／
subscription 契約，品質或服務政策決定 stage，升 tier 本身不升 stage。

驗收涵蓋內部至最佳模型及兩個歷史來源至官方／official retry、原最高需求、
原 archive 缺失／綁定漂移、每次新 proof、reader fence、目前資格與 context
漂移、pre-/post-intent gate、禁止的 failure cause、unknown overlay、預算／floor／
predecessor 保留、無使用證據／pending owner／gratuitous proof 及 schema 1／2
相容性。證據維持 ignored／原生工具儲存；production 接線、獨立 reader、provider、
credential／tool broker、source integrator 及各 runtime 資格不由此包宣稱完成。

### R1 準備交易接點

先完成 explicit prepared admission、host immutable plan、durable prepare intent
及獨立 saved descriptor／observation 確認。Flat／prepared 閉集合互斥，authority
原始 bytes 不變；歷史 operation archive-only replay 不呼叫今日 callback，新 ID
不可重複 phase。提交前／後失敗與 lost reply 保留 owner／intent，不因 absent／
created 宣稱 never-started，也不轉為 service／quality outcome。

驗收包含原 source／execution／policy／instance／nonce／control／prefix 綁定、
模式／phase／backend 型別、private artifact、pre-/post-intent current gates、
independent readback、archives／callback fence、freshness 與 immutable observation
更新，以及 schema 1 live gate、schema 2 first official unused TTL 和 schema 3
無 actual history 拒絕。Bootstrap／start／adoption／infra successor 尚未接線；
Docker／provider／登入與自架來源驗收分開，發行評估仍保留未就緒。

### B1 固定 bootstrap 接點

採獨立 bootstrap fixture mode，六類 phase 只到 bootstrapped；未來完整執行模式
須另建 packet，不沿用 B1／R1 journal authority。Input 由 sealed plan／descriptor
純函式推導，durable intent 先於固定 saved file 效果；receipt 綁 actual committed
intent ref 與 input，新鮮 observation 及四份獨立 exact bytes readback 才確認。

驗收三份 artifact 每個寫入失敗點、partial／lost reply、phase uniqueness、
archive-only replay、raw input／receipt／observation 綁定、私有檔案與兩個實體
fence，以及前／後 intent 的 source／authority／context gates。任何 bootstrap
狀態都不構成 model failure、writer stopped 或治理完成；owner／unknown 保留。
完整啟動／runtime／export／安全 finish／同 journal HSG 接手另在新模式實作。
真實自架模型驗收仍待自架服務可用的環境；專用 CODEX_HOME 官方訂閱登入安排仍待使用者
決策。這些證據不代表 production 或 release readiness。

### R2 完整 saved-fixture 接點

新 mode／packet 串接 preparation、bootstrap、launch、獨立 runtime、export、
publish 與 safe finish，不遷移 B1／R1／flat authority。Launch binding 將原 acquire
與 immutable artifact chain／actual committed launch ref 綁定；原六類與 execution
schemas 不改。只有固定 running genesis 確認 fixture start，infra partial 不能
補造 genesis、model failure 或 successor authority。

Runtime 讀全部 bounded immutable events，包含 publish／finish 原 proof 的
monotonic frontier；缺失尾端、gap、fork、partial 或舊 mode proof 均拒絕。
驗收原 mode projection／replay 不變、四效果提交前後／lost reply／phase uniqueness、
兩個實體 fence／current gates、反 rollback 及保留 unknown／owner。以同一真實
R2 journal 的失敗、safe finish 與多次 actual acquire 驗收 HSG：原需求 tier 不同，
取最高需求的正反案例，保留 quality／service 預算、floors 與 predecessor；來源
模型恢復不得 preempt 接手者。First-official schema 2 另走完整合成鏈。

完整 saved fixture 不等於完整 runtime qualification。自架模型／context／角色
驗收等自架服務可用的環境；官方訂閱登入、公開工具／credential 接點、production authority
reader／sole integrator 與各入口 qualification 仍須各自證據，發行保持未就緒。

### N1 固定 double-fork／兩輪啟動補充控制

既有 isolation probe 的 opt-in `--lifecycle` 增加固定 double-fork／setsid／
launcher exit、host process inventory、實際 writer 的 private cgroup 數值讀回，
以及 exact own container 的第二次 start。每輪實際 own write 與 protected path
嘗試、policy／mount／image、StartedAt、host canary 和自然退出均須核對；
缺正控制或 incomplete observation 保持未通過。證據綁 executable／profile
與當前環境身分，全部在 Git 外，重跑可重建等價 assertions。

這是固定 synthetic writer 的實際 Docker 測試，不是完整 N1 qualification。
Protected exact-path mounted positive、daemon／host restart、resource enforcement、
任意 Codex descendant 與全部 tool／credential 邊界仍未驗證。接通 production
authority reader／sole integrator 須先確立上述執行路徑；不能新增另一份合成
registry 作為全域 authority，也不能由這些補充控制開啟正式派工。

### 不需自架服務網路的 N2 容器路徑

固定公開 Codex source 的完整工具註冊查讀支持匿名 native CLI 的 Docker 候選，
其設計與 inventory 條件見 [匿名原生 CLI](../design/isolated-model-execution.md#匿名原生-cli-的容器候選)。
先核對固定官方 Linux asset、版本／公開 flags、create intent／cidfile 與前後 policy；
再用固定 provider 呼叫 native exec／patch 並讀回 scratch 與未掛載的 host canaries。
這些是可在不依賴自架服務的環境推進的局部測量，不是全工具、N2 或 production 資格。

後續須補完整 source／runtime inventory 對帳、每個允許工具與排除入口的實測、
native sessions、巢狀 CLI、hooks、project config、escalation 與可信 observer。
N1 剩餘隔離控制、N3 真實 backend／authority reader／整合器與官方訂閱登入資格
亦不能由自架模型端點恢復自動完成；專用登入環境仍待採用者決策。自架服務可用的環境只負責
真實自架 target／context／能力／登入與跨 provider 的端到端驗收，不能取代上述工作。

固定 28-case native container probe 已將重跑 recipe 納入工程 source；證據仍在
Git 外。涵蓋 default namespace、被排除 handler 名稱、exec 內隱與 argv0 patch、
升權拒絕及逐輪 advertisement。Host 固定案例身分／數量與 exact continuation，
不由 worker 自述決定 coverage；engine／policy／mount 逐次讀回且未知結果不重送。
Transport 綁核對過的本機 Desktop Unix socket，拒絕 context 名稱同名但遠端
或漂移的 endpoint；證據根目錄限定核對 owner／sticky mode 的系統 `/private/tmp`。
只掛載已驗證公開 binary bytes 的 private 唯讀副本，不以先前原路徑雜湊代替
實際執行內容身分；反例涵蓋原檔替換、非 regular descriptor、未知內容與副本漂移。
此版只測固定 Mac Docker／Linux arm64 CLI tuple，維持 registry／startup／
production 未資格化。CLI 的預設 local environment 與 app-server 空 environment
為不同入口；system／managed／cloud／project config closure 及完整 dispatcher
readback 仍是 N2 後續工作，不由兩個 ignore flags 或三工具 advertisement 宣稱完成。

### N1 exact-path read/write 控制

以獨立固定 recipe 補三份 synthetic source／checkpoint／sibling canary 的讀寫
對照，正控制額外掛載單一檔案至其 exact host paths，確認實際可讀寫與退出後
才重設；負控制移除 canary mounts，保持同 image／UID／program／paths／政策，
每項 read 與 write 必須各自遭 boundary denial，host bytes／inodes 不變。
兩輪有獨立 workspace 正控制、intent／CID／policy／自然退出及 unknown 不重播。
反例覆蓋 mount、身份、數量／案例混用、缺 write、未知 errno、OOM／running、
canary／reset 漂移，以及 unknown positive 不 reset／不啟動 negative。
工程 source 與重跑方式納入 repository，證據保留 Git 外；不放寬舊 probe 契約，
亦不宣稱其餘 N1、N2、N3、訂閱登入或自架服務可用的環境驗收已完成。

### N1 固定 PID 上限控制

新增獨立無 host mounts 的 Mac Docker fixture，PID1 單一 task、30 秒 explicit
deadline、上限控制最多 32 次 fork，含正控制整輪最多 33 次。先完成
single-child readiness／wait 正控制，再要求
31 個不同 children、第 32 次 EAGAIN、current 32 及兩種本地可讀 max events 各
增加一次；EOF 釋放後逐一 wait exit 0、current 回 1。反例涵蓋無 counter 的
EAGAIN、counter／PID／UID／policy／mount 漂移、缺 readiness／wait、child 異常、
未知 create／start 不重播；離線測試不在 host fork。工程 source 可重跑等價
assertions，證據留 Git 外。這不完成全部資源隔離、N1／N2／N3 或 production 資格，
也不由 cgroup events 推定 ancestor 的拒絕因果；不依賴自架服務的環境可獨立執行此控制。

### N2 匿名 project config／hook 局部控制

以固定匿名容器、唯一 exec call／兩次 Responses requests，驗證受控 user provider／
project trust 與 project-local `PreToolUse` 路徑；不需要自架來源網路或登入。先盤點固定
local config candidates，未知檔案／symlink 停止；不把此清單當成完整 cloud 或
effective-layer readback。Project hook／self-trust state 兩輪相同，user normalized
hash 一輪正確、一輪刻意不符；不使用 trust bypass。正控制要求一次 hook event
及 tool marker，負控制要求 hook 無效果且 tool 正常執行，維持 exact continuation、
advertisement、實際 project config bytes 與 container policy 身分。未知 positive
不接續或重播。工程 source／反例與重跑方法 tracked，採證留 Git 外；不宣稱完整
N2／startup／hook trust／credentials／production 資格。後續 sessions、nested CLI、
其他 hook 故障與完整 contributor／registry 對帳仍分別驗證。

### N2 匿名 native terminal session 局部控制

不依賴自架服務的環境可繼續依[app-server 工具清冊設計](../design/app-server-tool-inventory.md)
逐項對帳 source guards、公開 readback 與實際 dispatch；清冊本身不完成資格。

固定 recipe 使用兩個新 CLI／獨立 loopback provider 與匿名 homes。A 的 TTY
terminal 先產生 READY；B 在無 terminal 的另一個 CLI 實際使用 A 的 ID，要求
unknown。A 空 poll 不重現 READY，固定 chars 只送一次；唯一 ACK／marker 加上
工具 exit 0 後，再驗證舊 ID unknown。Host 只接受原始 header 的本輪 process ID，
對帳 UUID、固定 call sequence、當輪 continuation、model、宣告 schema 與 exact
container policy，不宣稱完整 request／input byte 對帳；不把 thread UUID 當工具
ID，也不從正文推定身分。Poll 是消耗式操作，
未知結果不重播。Fixture 有整體 50 秒及 subprocess／barrier 上限，證據保存在
Git 外、方法與反例 tracked。此包不完成 nested CLI、完整配置／工具
清冊、restart、credentials 或 N2／production 資格；後續分項仍保留。自架來源
模型端點恢復不能取代這些驗證，官方訂閱專用登入安排仍待原先提出的決策。

補充 `--mode non-tty` 的固定匿名 recipe：以 stdin EOF／READY 啟動，驗證跨 CLI
ID 拒收、空 poll 消耗性、一次非空輸入的 closed-stdin 拒收及拒收後同 ID 仍
running，再由匿名 provider 完整寫好 staging file、fsync 並以不覆寫的 hardlink
單次發布固定 scratch release，允許程式產生唯一 ACK 並
自然退出。Host 要求 Schema 2 與當次 terminal mode 精確相符，non-TTY 不接受
輸入 echo；舊 TTY Schema 1 收據保留為原版本紀錄。此補充不驗證 interrupt、
nested CLI、production observer 或完整 N2；資格 flags 仍 false，實測證據留
Git 外。工程方法與反例按同一驗收強度審查，不能由 public source 推定實測成功。

### N2 匿名 nested CLI 局部控制

新增固定 P→原生 exec→wrapper→C+／C− recipe，不需要登入或自架來源端點。
沿用原 image／binary／兩個 mounts；三個 CLI 的 HOME、cwd、provider port 與
UUID 獨立。C+ 讀受控 user model，C− 以 argv 覆寫；由實際 request model 對帳。
Parent／C+ 的原生 env 繼承指定 synthetic marker，C− inherit none 要求缺席。
Wrapper 不補 marker 或剔除原生 guard，只改 child HOME，未知 env key 停止。
每個 child 先實際拒收 P 的 live process ID，再經固定 tool 完成自身 scratch
正控制及三個未掛載 host canary 的讀寫負控制。Host 另讀 child 原始輸出、
exact continuations、當輪 advertisement、canary 身分／bytes 與容器 policy。

固定整體／subprocess／release／poll／輸出上限，未知 create／start／spawn／poll
不重送；缺自然退出或原始證據不能通過。已知隔離／marker 違規保留 failed。
工程 source、方法與反例 tracked，raw evidence／host receipt 留 Git 外。此包
只驗證所選配置／環境及固定巢狀工具路徑；完整 layers／registry、credentials、
restart、可信 observer、Desktop 與 N2／production 資格仍未完成，flags 保持 false。
官方訂閱專用登入安排仍等待原先提出的決策，與本匿名控制獨立。

同一 runner 增加 opt-in 三例 startup-layer 控制：clean 完成原 nested workflow，
固定既存 config 與 dangling symlink 在首次 CLI／provider 前拒絕。逐筆原始
觀察、完整 decision、host seed 身分／bytes、case／attempt、create argv、own
CID、engine、policy 與 canaries 必須綁定；負例保持自然 exit 1，不能由一般錯誤
或缺證冒充拒絕通過。後續 I/O 不能抹去已保存的確定反例，未知效果不重播。
工程方法與離線反例 tracked，runtime 收據及原始 artifacts 留 Git 外；重跑須
重建相同 assertions，動態身分可不同。這仍是選定 startup paths 的局部控制，
不是完整 layers、可信 never-spawn／observer、重啟或 N2／production 資格。

### N3 固定實體 checkpoint 接手組合控制

沿既有 one-shot container supervisor／sole integrator 補非空 C→存活且隔離的
A→新副本 B 的匿名案例，scope／acceptance 保持同一固定驗收。B 用 noop 仍須
保留 C 的累積 patch，A 的活躍 `holding` 不得進入 B；host exact readback 在
candidate／整合前後以 bounded process table 核對同一個 live 降權 child、holding
階段與無 completion 的 root control 綁定，不把 init running 當成 worker 存活。
唯一整合器採納 B，拒收 A 晚到的各個入口；
未知副作用不重播，隔離／checkpoint／authority 漂移須拒絕。這不替換 R2 saved
backend、不啟用 production registry、不接 provider，不完成全域 authority 或
完整 N3／原生工具／訂閱資格。工程方法與反例 tracked，原始證據留 Git 外。

### N1 Mac 原生 socket 補充控制

既有 `verify-model-permissions.py` 增加 opt-in `--network-controls`，在相同
私有 workspace／filesystem profile 上對照 network 開關。固定 C client
只用 system libraries；可信 host 分別驗證 loopback TCP／UDP 與允許路徑的
Unix socket 正控制 nonce 往返，再觀察負控制到完整期限。TCP／Unix 必須在
connect、UDP 必須在 sendto 得到明確拒絕，且 host 沒有負控制收件或 stream
accept；其它錯誤、缺失／逾期證據、compiler 或 observer 不可用保留 unknown。
Binary／設定漂移不得沿用原結果，收到負階段連線或 nonce 就回報 failed。

此包可在 Docker 不可用及自架來源不可達時測量 Mac 原生 sandbox 的固定
邊界；相關反例包括實際無隔離收件，不以缺工具或無回應當成功。設計與可重跑
assertions tracked，原始證據保存在 Git 外，供 code／merge review 讀回。
它不補足完整 N1、native tool inventory、credentials、restart 或 production
authority／executor 資格；原 N1–N4 與發行條件保持適用。

### N3 私有 controller reload 局部工程包

既有 runner 新增互斥 opt-in `--controller-reload-only`：私有 producer 只建立
S→非空 C→live old，封存 original refs 並自然退出；coordinator 取得原 process
wait exit 0 後，才由不同 PID consumer 重新建立原 store／backend／supervisor。
固定 private source closure、isolated import preflight、interpreter／engine／
run binding 與 no-follow bounded refs 均須相符，不提供任意 loader／argv／root
CLI。Consumer 只 reconcile old 一次且保持 exact unknown；transport exact
read allowlist、sticky running-only backend proof 及前後完整 same-worker observation
共同阻止 live→stop race 寫 export-intent。沒有 quarantine、successor、authority、
source write 或 production registry；C／descriptor／source 不變，僅允許合法
unknown ledger append／dedup。Raw trace 與 helper lifecycle 另由 coordinator 對帳。

Old start 前 T0+25 秒是完整預算，transport 預留 10+2 秒；兩 helpers 必須自然
exit 0，最後 readback 仍在期限內。Unknown spawn、timeout、partial reply、
refs／policy 漂移或 backend error 不重送，不宣稱所有 Docker children 已停止。
工程反例與方法 tracked；native runtime 測量、獨立正式 review／Security Diff Scan
與完整 DoD 仍由後續驗證處理，不能由離線成功推定 READY。這不完成完整 N3、
self-hosted／auth／daemon restart 或任何 production qualification；flags 保持 false。

### N3 fresh producer／consumer integration 與撤銷工程包

新增互斥 opt-in `--fresh-integration-only` 固定八案：applied-control、intent-crash、
write-intent-crash、mid-write、commit-crash、reply-lost、revoked-before-intent、
revoked-after-intent。每案獨立匿名 source／packet；planned callback 封 refs／marker
後直接 `os._exit`，自然正控制則 exit 0。原 Popen 精確 exit、marker 與實際 durable
source／ledger 三者相符後，才能啟動不同 PID consumer；沿用 captured private
bundle／pinned interpreter／clean HOME／closed FDs。兩個 revoked 案由 coordinator
在 producer 實際退出後，reopen 原 authority 並經既有 revoke API 撤銷，不重發。

Consumer 重新核對原 stopped worker／control／candidate／C 與 authority，僅以
exact Docker reads 及原 source 的 fixed Git `rev-parse HEAD` 執行 reconciliation。
禁止 prepare／start／export／source write replay；actual tree／mode／identity／
HEAD／index／outscope 與原 artifacts 保持，合法單次 canonical result／ledger
append 後再實際 reconcile 去重。Write-intent 的 record 保持 integration-intent、
writer_started true；revoked-before-intent 沒有 operation，reconcile 的早期
unavailable 拒絕與 integrate 的 revoked 拒絕分別保存，不虛構統一 reason。

每案 60 秒、全包 240 秒固定預算；缺 durable state／source lock、identity／
generation／runtime proof／bundle 漂移、wrong CID／op／authority、unexpected
exit／marker、journal／cleanup fault 或未知副作用均不得形成成功收據。工程方法
與 meaningful offline controls tracked；native runtime、獨立 code／security review
及完整 DoD 留待當輪證據。此包不完成 N3／daemon restart／模型或訂閱 qualification，
所有 production／runtime／adapter／N3 flags false，原始證據保留 Git 外。

### 匿名 native packet admission 工程包

新增互斥 `--native-packet-admission-only`，先由固定匿名 Responses conversation
取得一次 `packet_probe({})` 的嚴格 message／thread／turn／call binding 與精確 token。
Callback 只做記憶體 latch；token continuation、同 turn completion、binary／client／
sentinel、fixture 停止與 protocol-observed／direct-child-exit-0 全部讀回後，才由
host coordinator 封存 admission，並把 digest 注入既有 packet identity／request／
target。所有 native unknown 都在 backend construction 前拒絕。

重用既有唯一 checkpoint-overlap lineage：seed 非空 C、old live quarantine、
不同 successor 從 C 停止／export、唯一 synthetic integrator 和正式 reconcile。
不新增 dispatch registry 或 core 契約，不重新 export quarantined old；admission
不是 source authority，固定 tool 回覆不包含最後整合結果。原 lineage／generation／
request／target／C／descriptor／policy 漂移只能拒絕，不開新 packet、不重播。

固定同 host coordinator 另行盤點 18-file import closure，驗證來源與已載入 origins，
保存 source bytes／identity／hash；不沿用 13-file fresh bundle qualification。
Wire／token／close／binding／Docker／C／authority／results／source proof 與 failure
保留 Git 外。Tracked tests 涵蓋精確 latch、token、原始 pipe bytes、unknown gates 的
零 backend effects，以及 packet binding／generation 漂移不啟動後續 attempt。
Native CLI＋Docker 實測與獨立 review／scan 留待當輪來源凍結後處理；所有 native／
tool／startup／isolation／runtime／production／完整 N3 qualification flags false。

### Prestart app-server container 工程包

新增固定 opt-in `verify-model-app-server-container.py --prestart-container-fixture`，
讓匿名 app-server 在首次 config／discovery／turn 前，已處於 host 完整核對的固定
network-none container。僅做一次 `packet_probe({})` memory admission；不重做前包
checkpoint／successor／source integration。固定現有 image／Linux binary SHA，
no-follow bounded capture 與新 20-file closure；不接受任意 image／provider／model／
source／commands 或 loader。

固定 image 的 raw Env／Labels／Config snapshot 僅留 Git 外，封存 reference 與完整
config digest，再注入 expected fullpolicy 精確比對；不新增 image／env override。
精確非 root host UID/GID 之 private control、RO capture／binary 與 guest ownership
在 spawn 前核對；無 host parent／engine／auth mounts。Create intent 與原 cidfile
保留，固定 `--pull=never`，未知只 inspect 原 CID；full created policy 與 durable start intent 合格後，
只有一次固定 start-attach。OpenStdin／StdinOnce true、Tty false 是明確預期，mapping
或 policy 不符拒絕，不重新 create／start、reattach／exec 或 host fallback。

Docker client close、原 container policy＋exited 0、同一 guest CLI child 自然 wait 0／
provider stopped 分開驗證；raw nullable wire、固定 token／turn／call、provider requests、
spawn／source／policy／failure artifacts 留 Git 外。離線反例覆蓋 journal uncertainty
的零後續 start、policy／source drift、stdio pollution／partial／duplicate／extra args、
wrong token、client 0 但 container running、CLI／container nonzero 與 unknown close。

離線 peers 不證明 start-attach EOF 能讓同一 CLI／wrapper 自然退出；此為首個真實
runtime gap，需當輪 native measurement 與獨立 review／scan。所有 qualification 與
N1–N3 flags false；same-UID guest receipt 不是 production trusted observer。

### 固定原生 workspace writer 局部工程包

Prestart runner 增加兩個固定 native-workspace-case，各次新 private root／CID。
沿用原 admission latch／token，再由匿名 provider 發出一次原生 exec_command；
不是 host callback 代寫。公開 experimental environment object 與 probe-writer
named permissions 綁定，workspace 為唯一 write 路徑，capture／control／HOME
保持排除；必要固定公開 binary 與單一 host seeded synthetic canary 僅 read。
避免同路徑 deny 與父目錄遮罩阻擋必要 helper／canary。三輪原始 provider bytes、
declaration 相容性／不漂移、call／thread／turn、command lifecycle、terminal output
與 host no-follow postimage／canary 必須一致。

正例只接受唯一固定檔案／bytes、自然 exit 0；負例只接受固定 canary 的 native
明確 OS 拒絕及 nonzero exit，且 host identity／bytes 不變、workspace 無新檔。
Guest CLI bounded stderr 持續 drain，overflow／truncation／缺 EOF 或 reader 未
結束均 unknown；Docker start-client stderr not-captured，不由此推測故障原因。
Writer 額外要求 fixed bundle bwrap，只有精確 binary／sidecar read；移除會
遮住允許子路徑的 parent masks，其他路徑由 root default deny 排除。
Writer image Config 比較僅允許明列 13 個精確型別空值／缺省等價，原 raw
snapshot／private metadata 與其他欄位保留；default admission 的 raw-exact gate
不變，不因遇到 drift 切換規則。新增固定 16 MiB tmpfs 作 wrapper／exec-server
staging，host map／mounts 與 guest 實際
tmpfs 另行核對，model 不取得 temp write。Provider／CLI 前的固定有界 namespace
與 canary probe 失敗就零啟動，不重試；其成功也不代表 native writer 資格。
原 admission 的 argv／env／capture／mount 契約保持，以上都是 writer-only。
空白匿名 workspace／HOME 經核對後才使用 project_doc_max_bytes=0。
Native refusal 須先讀到固定 canary，讀取失敗不能作寫入拒絕正例。
原 container 限制不升權；預設內層 Linux sandbox 無法建立時不改 sandbox、
入口或重播。Raw evidence 留 Git 外，shared docs 記方法與限制；當輪 native
測量、正式獨立 CodeGate／SDS 與完整 merge review 仍需分別執行。這不完成
N1–N4、production observer／authority 或 provider 資格，所有 flags false。

### 外層 OS executor 傳輸準備工程包

先擴充 canonical transport、plugin mirror 與 transport tests，提供 per-Session
明確 opt-in 的公開 thread/settings/update 及固定有界 memory-only stderr
觀測。Default methods／DEVNULL 與 close 回傳契約保持；所有 config／auth writes
仍拒絕。設定更新 ACK 不代表生效，caller 的 raw notification／target／policy
核對 gate 尚待後續獨立 fixture 實作，沒有將新介面接入原 bwrap runner。

65,536-byte 原始前綴、持續 drain、copy／hash 與 EOF／overflow／truncation／
reader 完整性分開記錄，close 使用單一 deadline、不 kill 或 relaunch。
直接 child exit 0 但其他程序仍持有 stderr pipe 時保持 unknown；晚到觀測
或再次 close 不提升結果。原始證據留 Git 外，工程方法存放 design。

後續 external OS fixture 須獨立 opt-in、新 run／CID、唯一 host RW workspace、
RO capture／inputs 與私有有界 tmpfs；不掛 host controller／auth／receipts，
不升 privilege 或重播失敗 attempt。Bootstrap、設定生效、兩個 native case
與全部 production／N1–N4 資格仍待驗收；本包只提供傳輸介面與匿名控制。

### 外層 OS bootstrap 的有限前置驗證

另行實作明確 opt-in 的 `verify-model-external-bootstrap.py` 與固定 guest。
先在新 CID 的 RO capture／inputs、唯一 host RW workspace、私有 tmpfs 中
驗證 read-only thread/start、externalSandbox settings ACK 與 raw notification
順序。此 packet 不送 turn、不派工具、不採用帳號或真實模型，不改原 bwrap
runner，也不提高 privilege 或重播 unknown attempt。

完成工程包需有反例測試、深入審查、適用完整 Security Diff Scan 與新 head
完整 Merge Review；匿名原生觀測另保存於 Git 外。即使此前置流程通過，
workspace-write／external-write-refusal、工具清冊、官方原生登入、來源權限、
唯一整合器、程序撤權及端到端接手仍待後續實作／驗證，全部資格維持 false。

### External OS 的兩個固定 native case

在已完成的 anonymous bootstrap 之上，另設 opt-in native-workspace-case。
每例建立新 run／CID；host 確認 raw settings 後才送一次固定 turn，以兩次
有限 loopback HTTP response 觀察原生 exec_command 寫 workspace 或嘗試寫
RO canary。Case-only catalog 從 tracked literal 建立，固定單一 direct alias、
4 KiB 上限、EXCL／no-follow／0600，host 重建 bytes／hash 並核對 task 前後的
file identity。Receipt 標示 synthetic 來源及 query spawn count 0，只有一次 task
CLI spawn；default bootstrap 不增加 catalog。這不驗證官方 catalog、真實模型
tool mode 或 context 資格；固定 context 等欄位僅供匿名 client 測試。
先核對 guard，再核對明確 OS denial，不能以 generic nonzero
替代拒寫。CLI／provider／client／原 CID 自然退出、完整 EOF、raw call lifecycle
與 host no-follow postimage 分別驗證，不提高權限、不重播未知 attempt。

HTTP、raw bundle、壓縮資料及 final frame 均固定上限；超限、部分請求、第三次
請求、錯誤 thread／turn、approval／reroute、額外工具、symlink／額外檔案都
不得通過。原始證據仍留 Git 外。此局部包需深入審查、適用完整 Security
Diff Scan、相關測試與新 head 完整 Merge Review；固定兩例通過也不構成
context capacity、背景程序撤權、來源／credential broker、production 或 N1–N4
資格，亦不消除自架服務可用環境與正式 subscription 登入的獨立驗收依賴。

### External OS 的兩個固定 native patch case

在上述 exec 控制旁增加 `workspace-patch` 與 `patch-canary-write-failure`，
沿用新 run／CID、三 mounts、固定匿名 catalog、一次 turn 與兩次有界 HTTP，
不增加 provider、登入、來源權限、privilege、backend 或 production registry。
先依固定公開版本的 custom Lark declaration、plaintext carrier、FileChange
契約與 unified diff 規則建立預期值，再實測正例固定 workspace 檔案與負例
固定 canary 替換。Host 另核對精確 postimage、原 canary identity／bytes、
原 CID／client 自然退出與完整 stderr／wire；planned changes 不證明實際寫入。

Patch writer 的頂層錯誤丟失 errno，故負例驗收名稱為「寫入階段失敗觀測」，
明列 `failure_cause=unknown` 與 `os_refusal_proven=false`。一般錯誤、讀取失敗、
截斷與其他路徑不能通過，也不能替代 exec 的明確 OS 拒寫控制。工程方法
與限制列於 design；原始實測、review 與 scan 證據仍不追蹤。局部反例測試、
深入 review、適用完整 Security Diff Scan、相關驗證及新 head 完整 Merge
Review 通過後可交付工程包；全工具、checkpoint intake、唯一整合器、撤權、
restart／handoff E2E、正式登入、真實 context／品質與所有資格仍待後續驗收。

### External OS 的固定互動工具控制

下一個受控包增加 `input-default-guard` 與 `input-disabled-dispatch`：前者
驗證工具已註冊、Default mode 明確拒絕合法固定呼叫，後者驗證工具未宣告且
registry 拒絕同一呼叫。匿名 default 明確 disable，另一個可允許 Default mode
互動的 feature 亦明確 false；新案例固定 Default turn／settings、raw events false、
零 server-request 回覆、零 native tool items 與兩次有限 HTTP。Guard 在 argument
parse 前返回，host payload 校驗與原生解析分開，不接受 generic failure。

設定採納須依固定 upstream 契約：bootstrap instructions 為 null，turn 指定
固定匿名非空字串，核對恰好兩份獨立 settings 值與「bootstrap → turn/start
out-sent → adopted settings → turn/started → turn/completed」順序，另保存
採納 notification／sequence；bootstrap 唯一性只適用該 prefix。RPC response
可在通知之間交錯。缺少、額外、倒序或任何其他 settings 漂移保持 unknown。
設計與負向測試先核對 normalization／apply／task／projection，才以新來源
執行；早先因漏掉採納通知而停止的 attempt 維持 unknown，不能追認通過。
新案例另明確設定 approvals reviewer、空 disabled plugins、effort／summary／
service tier／personality，依 pinned apply／projection 固定十四欄完整 dictionary
與精確鍵集合；兩份觀測各有逐欄缺漏、有效值漂移及額外鍵反例。此控制
不接受從第一筆 native settings 建立任意 baseline，亦不改既有 exec／patch。

先閉合固定 upstream handler／router／future／history／app-server projection，
再凍結五檔來源並做深入審查、反例測試、實測與適用完整 Security Diff Scan。
工具設定改變 argv／advertisement；如報告此新來源的完整 runner 已實測，
須建立 bootstrap、四個既有 native cases 與兩個新 cases 各自的新 run／CID，
不得重新啟動、重附著或重分類舊 unknown attempt。Host 將固定 canary 的
initial ref 保存於 Git 外收據，供前後 identity／bytes 的獨立 readback。
新 head 仍須完整 Merge Review；測量結果不完成 N1–N4 或 production
DoD，也不消除專用訂閱登入、可信撤權／checkpoint intake、唯一整合器與
自架來源實際能力／context／E2E 的獨立缺口，發行評估仍與 Issue #316 同案。

### 固定原生 checkpoint intake 工程包

本包把匿名原生 `apply_patch` 的固定更新接入受保護的一次執行鏈：只將既有
`example.txt` 的 `old` 改為 `new`，保留 `remove.txt`，不接受任意程式、路徑或
patch。獨立 `OneShotNativeFixtureBackend` 維持 descriptor schema 2／supervisor
schema 4；production dispatcher、CLI registry、source integrator 的 gate 不變。

Host private capture 使用 0700／0600；另一份 guest capture 使用目錄 0555、
source 0444、固定 binary 0555，僅 guest tree 以 readonly／rprivate 掛載。
完整來源清冊、各目錄與檔案的 identity／mode／owner／單一 link／hash 由 host
事先保存，create／start／export／fresh consumer 各階段重新核對。原 capture
與 unknown attempts 不修改、不重用執行。Root caps 仍精確限於 SETGID、
SETPCAP、SETUID；claim fsync 後，child 關閉 control FD、清除 capabilities／
bounding set、groups，改為 UID/GID 65534 與 NNP，再執行固定 helper。

驗收入口須在任何 mkdtemp／capture／write 之前逐層核對 evidence root 的
完整受信任 ancestry、Git 排除與 0700 leaf，並保留 parent／fixture descriptor。
每次 stage intent 與 captured-code load 前重新檢查相同 inode；最後收據也須
維持原 fixture。上層可被其他 UID 替換、symlink、Git 或非 private leaf 都
在建立子目錄前拒絕。事後 PacketStore guard 不能替代載入前檢查；修正這類
captured source 後須以三個全新 fixture 重驗，不重分類既有實測或 unknown。

正例只有 host 查證原 CID 的完整 policy、自然退出、protected input／claim／
completion 與精確 postimage 後，才 export／seal／publish 非空 C。Coordinator
等待 producer 確實退出後才啟動新的 consumer process；consumer 只 reconcile
原 attempt，禁止 prepare／bootstrap／launch／export／source apply，且原 C、
seal、descriptor、ledger 不得改變。這是 checkpoint intake，尚非來源整合。

撤銷案在原生修改與 CLI 關閉後固定保留有界等待；host 核對原 CID 仍 running、
精確 postimage 與隔離 policy，才 quarantine。合法的遲到 completion 也不能
發布 C。窗口錯失或證據不足保持 unknown；隔離／採納權撤銷不等於 writer 已停。
固定 `claim-replay` 案例只再 start 該輪首次已知正常完成的專用 CID，要求第二次
root exit 73、原控制鏈與原生 frame 不變、無第二次 native invocation、無 C。
撤銷案另預留新 generation 而不 launch，核對遲到舊結果 fence；不是完整接手驗收。
2026-10-05 已以三個全新專用匿名 fixture 分別通過上述案例，並讀回原始
protocol、root control chain、原 CID、source capture、actual PID／wait 與 packet
refs：正常案由新程序取得同一非空 C；撤銷案 generation 2 不 launch successor，
遲到結果拒收且 C 保持 null；第二次 start 為 root exit 73，僅一次 native
invocation，fresh consumer 仍保持 unknown／無 C。完整 generation／競態反例
與 production 接手資格仍須補足，不由這三案或離線測試代替。

重跑使用 repository pinned Python；原始證據存於 Git 外的 private root：

```sh
./scripts/project-python -m unittest tests.test_model_native_checkpoint tests.test_model_container_launcher tests.test_model_container_backend
./scripts/project-python scripts/verify-model-native-checkpoint.py --native-checkpoint-only --case checkpoint --evidence-root "$PRIVATE_EVIDENCE_ROOT" --binary-path "$VERIFIED_LINUX_CLI" --endpoint "$LOCAL_DOCKER_ENDPOINT"
./scripts/project-python scripts/verify-model-native-checkpoint.py --native-checkpoint-only --case quarantine --evidence-root "$PRIVATE_EVIDENCE_ROOT" --binary-path "$VERIFIED_LINUX_CLI" --endpoint "$LOCAL_DOCKER_ENDPOINT"
./scripts/project-python scripts/verify-model-native-checkpoint.py --native-checkpoint-only --case claim-replay --evidence-root "$PRIVATE_EVIDENCE_ROOT" --binary-path "$VERIFIED_LINUX_CLI" --endpoint "$LOCAL_DOCKER_ENDPOINT"
```

Native run 只使用既有固定 digest 的 Python image／Linux CLI，建立各自新的
scratch container／control volume 並保留資源；不接受既有 repository，不清理、
重啟共享 daemon、帶入 credentials 或套用來源。原生 raw readback 已完成；正式 code／security review、
readiness／merge／release 前最新完整 Merge Review 與必要 CI 須分別完成；
未 ready draft 可維持 REVIEW_REQUIRED。所有 native、
runtime、adapter、isolation、startup、production 與 N1–N4 資格仍 false；完整
DoD 與同案發行評估仍 BLOCKED。

早先匿名 native checkpoint 建立後的嚴格 inspect 核對，因 macOS Docker Desktop 唯讀 fixture bind 的固定路徑轉換而保留 `prepare-reply-unknown`；容器保持 created，沒有 bootstrap／start intent，沒有 native 寫入。不得重用或啟動該 attempt。修正只固定各 host 平台的完整預期 source 並納入 policy digest，完成離線負向驗證及 preexec 重審後，以全新 fixture 重測三案。

另一個歷史匿名 native 實測曾產生非空 C，producer 由 coordinator 實際 wait 成功退出；fresh consumer 因 Docker image inspect 省略原先空白 `User`／`WorkingDir` 而拒絕建構，因此整案仍為失敗，不能宣稱接手完成。保留該原始 C／producer／consumer 失敗證據、不重放舊 attempt；只補官方 API 支援的未設定欄位語義與負向測試，該失敗不追認成功；後續三個全新 fixture 已完成驗收。

## 同案工程流程效率切片

依 [效率需求與 DoD](../requirements/engineering-workflow-efficiency.md)，解除
draft 每次更新即重做完整 Merge Review、契約／consumer 問題發現過晚與歷史
敘述測試過度綁定的 blocker。落實共用規範、技能、模板、package 與早期驗證
入口；先完成低／中／高風險固定代表性路徑，不新增逐項 NIT 交付循環。
前一穩定 native 工程包的有效測試、獨立審查與封存掃描按 source／scope／
assumptions／policy／environment 核對後重用；效率切片另審其公開契約及入口。
原完整 DoD、未解資格與同案發行評估維持 BLOCKED；公司環境可用性只是依賴之一。

## 原生 checkpoint 到固定來源整合的最小切片

本輪解除「原生非空 C 已取得，但 fresh consumer 尚無來源整合接線」的
fixture blocker。DoD 是一條固定匿名 `apply_patch → C → producer wait/EOF →
fresh consumer → host authority → 唯一 integrator → applied → same-operation
readonly reconcile`；必須核對原 immutable refs／C、來源 HEAD／index、精確
postimage，且 revoked authority、來源漂移、錯誤 backend／case、capture 漂移、
acceptance mismatch 在來源寫入前拒絕。

原 `PacketIntegrator` 的 exact synthetic backend gate 保留。另設 exact-type
`NativeFixturePacketIntegrator`，只接受 captured native checkpoint recipe、
host-created `SyntheticSource` 與固定 `native-update` authority；scope 僅
`example.txt`。只建立 Git 外的 private fixture，不能輸入一般 repository，
不帶 credentials。整合允許 ledger 與兩份 integration journal 及其 staging
links 增加；原 descriptor／seal／C／runtime evidence 保持原內容與 identity。
同 operation 重讀不得再 apply 或 start runtime。固定 staging Git child 使用
022 mask 以維持 text 0644；host capture 仍 077，其他 child 不受改動。

先做 pinned Python／Docker image shape／既有 consumer smoke，再做 scoped
正負測試與獨立深入 pre-execution review；穩定後才跑 Security Diff Scan。
有效的未改動 primitive 證據可重用，不作新 bridge 完成證據。

```sh
./scripts/project-python -m unittest tests.test_model_native_checkpoint tests.test_model_packet_integrator
./scripts/project-python scripts/verify-model-native-checkpoint.py --native-source-integration-only --case checkpoint --evidence-root "$PRIVATE_EVIDENCE_ROOT" --binary-path "$VERIFIED_LINUX_CLI" --endpoint "$LOCAL_DOCKER_ENDPOINT"
```

原 intake 的三個模式與 failed／unknown attempts 保留；新 source 模式只有
checkpoint 正例，不擴為一般模型或任意 patch 接手。原完整 DoD、訂閱登入、
可信 generic observer／撤權／checkpoint intake、一般來源整合、N1–N4、
context／quality escalation／跨 provider E2E 與同案 release 仍 BLOCKED。
production／native／runtime／adapter／isolation／startup／N1–N4 資格全部 false。

## 本機簽發者的最小前置包（2026-10-06）

使用者核准以預設關閉的受信任本機 host 簽發者承擔具名任務的短期許可，
不要求不存在的 Desktop-native attestation。先只驗 fixture domain 的
issue／readback／revoke 契約：重讀已核對的原始 task/source 與 CLI target，
綁 action、證據 digest、時效、session 與撤權 epoch；可信注入 reader 每次
重讀受保護 target 原件。缺來源、漂移、過期、時鐘回退、root 替換及撤權後
renewal 均拒絕；已觀察的過期或時鐘歧義會持久封鎖舊 reference。Fixture grant 不進
NativeLifecycle 或 production dispatch，原 `synthetic_only` 與空 containment
registry 不變。原始人工授權及獨立 CLI 資格的真實 reader／證據仍是下一步
相依；不得由 summaries 或合成 granted 字串補造。

具名任務採一次初始人工核准，限期內以短期 permit 接手；初始 grant 固定
原驗收、來源、允許目的地與 action、sandbox ceiling 及最長期限，撤銷與
到期後不能由 agent 自行續期。fixture 已把 task grant 與 session permit
分開並驗證同一 grant 的 successor、越界拒絕；這不證明核准者身分。
下一包只處理實際受信任本機入口及獨立資格 reader 的最小接點，先在
macOS 與 Linux 各自核對 OS 權限／身分邊界與部署條件；未有可信根時
保持 default-off，不能把 TTY 確認或同 UID 私有檔當成授權。

先跑廉價 schema／source/target 契約，再跑聚焦正負測試、package parity、
比例獨立審查與適用安全掃描。原 877bb36 工程包封存的 27/27 scan 與
17 個 hosted 成功檢查僅按未變範圍重用；draft 的 exact-head readiness
因缺最新完整審查憑證未通過，不能以這些局部證據追認。一般失聯、未知
writer 控制、真實來源成果整合及完整 C、release 的 blocker 維持。

## 單一路徑收斂：checkpoint 後失聯（2026-10-06）

此節調整上一節的實作順序，不撤銷其 fixture 結果或既有授權。暫不把
管理員簽發安裝、任意背景 writer 或 coordinator 重啟擴成新的恢復平台。
本包只修一個實際 blocker：先前 producer 在 C 封存後仍須寫
`handoff.json`，fresh consumer 才能續作；若兩者間失聯，就無法使用可信
進度。現在 producer 封存 C 後立即退出，不再寫交接檔；存活 coordinator
讀回 wait／EOF，fresh consumer 從原 ledger 與不可變 request／execution
重建，核對 writer 停止、owner 與 checkpoint 後取得 generation 2。

同一固定匿名 Docker／CLI fixture 實測通過：無 `handoff.json`、原 C 保留、
新隔離副本完成 C2、舊 generation export 零效果拒收。遲到 publish 拒收
沿用既有局部測試；本次實體路徑不聲稱有該項證據。原失敗、unknown 與
先前封存證據保留，production／native／runtime／adapter／isolation／
startup／N1–N4 資格仍 false。

下一工程包只選一個具名本地任務接到現有 admission／source reader；先核對
Codex 原生授權邊界與當前 CLI 資格，不能用 fixture grant 代替。管理員
簽發工具暫不安裝；若現有能力對具體信任缺口不足，再提出精確差異與
驗證，不預建一般服務。完整 C、PR readiness 與 release 仍未完成。

## 選定本地任務的初始授權邊界（2026-10-07）

本節更新上一節的待決信任選擇，保留 2026-10-06 fixture 工程與其限定
證據。使用者接受 Codex Desktop 本地任務及其 agent 作為單一本地 C 路徑
的可信初始授權來源。具名任務的原 request／驗收、source、scope、允許
目的地、action、sandbox ceiling 及有效期由可信 agent 明確綁定；接手
只能在原範圍內縮小，停用、撤銷、到期、來源漂移與擴權拒絕。新任務需要
自己的原授權。此選擇不要求獨立簽發者、另一次本機核准或 Desktop 原
對話的獨立身分證明；因此也不宣稱防止可信 agent 偽造原授權。

`FixturePermitIssuer` 仍只提供 fixture 回歸，不升格為正式 authority。
獨立 host 簽發者退出本路徑的必要條件；`NativeHostControl` 的 live
session、撤銷及 clock watermark 仍保留。下一個有界工程包應先驗證
可信 task/source 與既有 Native admission 的接點，再分別讀回當前 CLI／
Native 目標資格、秘密排除及 writer containment。不可將 `TaskSourceInput`
的 digest、target summary 或 agent 信任當成資格、隔離與成果採認證據。
目前 Native reader 仍 synthetic-only、固定 source／patch，正式 containment
registry 為空；尚無選定真實任務的 dispatch 或完整 C 資格。缺真實
consumer 時維持拒絕，不用新簽發平台填補其他四項 C 缺口。現有
`TaskSourceInput` 的 300 秒新鮮度可更新，尚無跨 reference 的原任務最長
授權期限／持久撤權；下一包需在可信本地入口驗證這兩項，不以更新 input
當成原授權續期。

### 原任務期限與持久撤銷的 CLI consumer 切片（2026-10-07）

既有 `model-task-execute` 的 planned 路徑現要求 protected schema v2：可信
本地 agent 提供與具名 task／workspace 固定對應的原 grant，綁定 request、
acceptance、source、目的地、唯一 `start` action、sandbox ceiling 與最長
24 小時期限。短期 record 仍限 300 秒，其更新／alias 不能越過原 grant 到期。
同一 task key 的 protected revocation 標記跨 reference 與重開後保持拒絕；
撤銷 key 從 protected record 而非 caller workspace 字串導出；同步失敗後
重試須再同步既存 marker 與目錄。缺少標記目錄、舊 schema 或
scope／source／grant 漂移都 fail closed。
實際 CLI packet 的 claim、launch、封存邊界沿原 `TaskSourceInput` 讀回；
撤銷發生於最後 target readback 時，不啟動 session 且保留 unknown。

此切片只收緊既有 CLI consumer；沒有接通固定 `NativeLifecycle` 的 source／
patch，也沒有創建正式 target qualification 或 writer containment。Grant
仍由可信本地 agent／同 UID host 管理，不是防偽的獨立簽發證據；跨重啟
時鐘回退及撤銷與 session 啟動之間的競態仍待真實 host-control 邊界驗證。
此後 C 工程包暫停。若依本期有界情境重啟，先查當前 CLI／Native 目標資格、
秘密排除、選定 task 的 Native consumer 型別與四項接手前提；未取得各項
證據前 registry 保持空、C successor 不派發。當前先執行上方 A/B 入口驗收
與獨立交付評估。
