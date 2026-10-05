# Portable Engineering Workflow Contract

本契約供 Codex CLI／Desktop 與 Hermes CLI 的已驗證入口共用。它定義工程
階段、必要證據與完成標準；runtime adapter 負責工具、模型、session、權限及
能力發現。引用本契約不授予相容資格、外部寫入或 production 執行權。

## Stages And Evidence

小型工作可合併階段、重用有效證據；不能省略任務需要的義務。普通有界交付
不要求 durable loop、native Goal、多代理或排程。依當前來源選下一步：

| 階段 | 必要輸入與動作 | 可查證產物／離開條件 |
| --- | --- | --- |
| Discover | 讀指令、需求、repo 身分、branch/head/upstream/remotes、完整修改與 ownership；查當次工具／schema／權限 | 目標、範圍、DoD、已知限制；來源衝突須先解決 |
| Plan | 選最小一致切片、指定 writer、依賴、驗收、風險與 review 強度 | 有界計畫；不把規劃當修改、派工或外寫授權 |
| Implement | 使用已授權的檔案／命令能力，保留無關修改；按既有模式完成切片 | 實際 diff／新增檔案，不只模型敘述 |
| Verify | 父代理讀回成果、核對受保護 tests／需求，執行適當固定驗收 | 命令、exit、結果、來源身分與略過／失敗分類；tests 通過不代替 review |
| Review And Fix | 獨立且足夠能力的 reviewer 唯讀審查當前 diff；依風險完成必要 scan | finding IDs、Fixed／Deferred／Rejected／Needs Human Decision 與證據；blocker 修正後重審 |
| Docs Sync | 對照實際行為、需求與限制同步文件及狀態 | code/docs 一致；保留 historical records 與未驗證事項 |
| Delivery Gate | 核對上列證據、授權與 repo 選定的 provider 規則；draft 可維持 REVIEW_REQUIRED，宣稱 readiness 前做最新完整 exact-head review | content readiness、provider enforcement、外寫授權分開；舊 head verdict 不沿用 |
| Continue | 中斷前保存有界 checkpoint；接續先讀回當前 source／修改／ownership | 同一目標、唯一 writer、剩餘 DoD、finding、證據與下一步；session 記憶只作 advisory |

## Workflow Efficiency

流程效率是產品品質與 DoD 的一部分，適用於本專案及部署後的其他專案。
依任務規模完成下列義務；小型切片可在既有 plan／report 簡記，不另建 ledger。

1. 先核對正在執行的操作、副作用及唯一 writer；保留失敗、unknown attempts、
   有效證據與未解 findings。選一條最小端到端交付路徑，寫明解除的 blocker、
   DoD、必要驗證及剩餘依賴。新增 probe 必須解除具體 blocker。
2. 修改／修補前先做廉價的契約、環境與整合 smoke，核對回傳型別、consumer、
   實際 CLI／Docker reply schema、版本與權限；再跑局部測試。差異不能藉放寬
   安全邊界接受。無法執行的檢查標示未驗證，阻擋依賴它的資格宣告。
3. 審查強度依實際風險選取；第一次覆蓋完整工程包，修補後只重審受影響程式、
   上下游契約、信任邊界與未解 finding。正式 gate 核對並重用仍有效的 primitive，
   不為階段名稱再執行一次。重用前核對 content（含未提交修改）、scope、
   assumptions、phase、policy、environment；來源 SHA 相同仍須檢查其餘綁定。
4. 有副作用或新權限邊界的實測保留前置獨立安全審查；適用的正式 Security Diff
   Scan 在工程包穩定後完成。封存掃描不可改寫；安全修補使證據失效時補足
   相應重審與掃描。Blocker 必須修正；NIT／SHOULD-FIX 可批次記錄簡潔處置，
   非 blocker 延後須有原因、負責人及後續目標。仍須滿足所選 provider gate。
5. 連續兩輪未收斂時，先改變診斷方法、補整合證據或縮小切片，再續行；
   不能只提高 effort、換模型或重跑同一整套流程。保留原失敗及未完成資格。
6. 以同範圍的簡單計時、審查輪次、重複查讀及返工原因評估成本；未量測或
   不可比較者標示 unknown，不宣稱節省百分比。固定合成案例只證明列出的
   行為，不能證明真實模型品質、完整自動切換或 production 資格。

| 代表性任務 | 前移檢查與必要審查 | 成本與證據邊界 |
| --- | --- | --- |
| 低風險：局部文件／連結修正 | 連結、schema、狀態一致性；docs review | 重用未變內容；不為措辭增加鏡像測試或完整交付循環 |
| 中風險：有界功能及 consumer | 回傳形狀／consumer smoke、局部行為測試；code review | 有效證據重用，漂移只補受影響邊界；兩輪不收斂改診斷 |
| 高風險：writer／credential／公開契約 | 環境與信任邊界 smoke；獨立 deep review，適用安全審查／scan | 成本偏好不能降低資格、隔離或審查強度；readiness 綁定最新完整 head |

部署後可先用下述 fixture `preflight` 查契約，再以專案自己的固定驗收及
已驗證 routing／review 入口實測；本 repo 的快速代表性入口為
`./scripts/validate-repo.sh --workflow-smoke`。它不取代完整 CI／正式 gate。

## Runtime Capability Selection

1. 從當前公開介面確認工具與完整 schema、model/provider/effort、資料目的地、
   context、檔案／網路／憑證邊界；依任務選適當能力，不要求兩種 runtime 使用
   相同工具名、模型、設定或 session ID。缺事實保留 unknown。
2. 工程流程採當次可用的相容工具、CLI 或服務。能力替代須保留前置、scope、
   authority、證據、驗證與完成條件；安裝、help、自述及另一 runtime 的結果
   不能證明資格。不要把 Codex TOML、Desktop callables 或 `functions.exec`
   當成 Hermes 的必要介面；不自動讀取或複製其他 runtime credentials。
3. 獨立 reviewer 可在同一 runtime 的另經驗證唯讀角色／session，或使用另經
   驗證的獨立服務。Security scan 與 forge control plane 亦按能力選取；Hermes
   不必安裝或呼叫 Codex。作者自審、對話隔離、縮小 toolsets 都不能代替必要
   的獨立性、實際權限限制或角色品質。
4. 缺委派能力時維持單一 writer；缺排程／session API 時採手動 checkpoint
   接續。缺獨立 review、必要 scan、平台或安全執行能力時，完成不相依工作，
   阻擋相依 readiness，不放寬 DoD、不製造 qualification。
5. Model routing、tools、記憶、Goal、排程、工作協調與 repo 完成證據分開。
   服務／認證／環境／權限／context 失敗與品質返工分開分類；未知外部效果不
   重播。兩輪未完成修正觸發假設、方法與 context 重評；換模型／session 不
   清除 findings、修正歷史或預算。
6. 基本 provider／模型接入先沿用原生設定、工具 loop、history／context 與
   sandbox；選模／返工重用既有決策層。執行中接手的 writer 隔離、checkpoint、
   撤權與成果整合另列進階 DoD。按選定 runtime／scope 獨立驗收基礎與決策，
   不要求未使用的恢復系統全部資格；缺相依仍阻擋真正 dispatch／接手。
   新 supervisor、broker、observer、container 或 integrator 必須解除具體的
   原生能力缺口，不以設定／help 成功、advisory 或 fixture 取得執行資格。

## Adapter Boundaries

- Codex 入口保留既有 `project-delivery`、`project-orchestrator`、primitive
  review／implementation 與 CLI／Desktop adapters。Custom-agent selection
  仍依原 qualification／profile preflight，不因本契約改 default 或 fallback。
- Hermes 入口為 `hermes-project-delivery`、`hermes-review-gate` 與
  `hermes-task-continuation`；專用安裝器保留全部 sibling dependencies。
  不以 `shared` 標籤宣稱其他 Codex skills 已資格化於 Hermes。
- 每個 adapter 必須分別記錄版本、surface、backend、profile／instruction
  bytes 與驗收範圍。有限支援不等於全部工具／委派／OS sandbox／自動 lifecycle
  合格；能力未知時按上列 fallback。Runtime availability 不改 source-of-truth。

## Verification And Publication

同案例驗收使用 `scripts/verify-engineering-workflow.py` 的固定合成 fixture；
source／plugin 從套件根目錄解析，Codex filesystem 安裝使用
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/scripts/verify-engineering-workflow.py`，
Hermes 使用安裝 namespace 下的 `scripts/verify-engineering-workflow.py`；
不要從專案 cwd 推定已安裝入口。
兩入口各自 prepare，保留 case digest，再以 `preflight --fixture-root <absolute-path>
--expected-case-sha256 <digest>` 檢查受保護契約、bounded entries 與 identity，
不執行 fixture code。通過 preflight 不代表功能通過或隔離；經實際工具修改
後由操作人員 verify。固定 tests、spec 與
文件驗收須獨立讀回。它只證明列出的 functional outcomes，不證明模型等價、
隔離、獨立審查、正式 gate 或整套 runtime qualification。失敗與未完成結果
保留，不只比較成功案例；runtime/model/profile 身分由可信操作人員另存 Git 外。

正式 review 依適用 review skill／風險與
[exact-head contract](exact-head-merge-review-contract.md)。Provider 操作依所選
repo profile；需要 GitHub 時依 [control-plane policy](github-control-plane-policy.md)。
Commit、push、PR/MR、merge、tag/Release、deploy 與清理逐項核對現存授權及
gate，不能由 tests 或 helper 回傳值推定允許。
