# Reusable Workflow Contract

本檔是 CLI／Desktop 共用的必讀核心與情境入口。讀完整個本檔，再依觸發表
選讀細則；不要預載全部政策。既有章節名稱保留，source、plugin 與 filesystem
安裝共用相同契約。同目錄 [完整細則](reusable-workflow-details.md) 保留展開規則。

## Contract-Preserving Capability Selection

- 保留使用者指定的技能／方法與較高優先指令。先讀適用技能的必要契約，
  再選最小相容的直接推理、原生工具、內建或本地技能組合。不得略過必讀
  指引、必要工具、驗證器、獨立審查或模型資格程序。
- 只查當次操作所需能力，以當前工具清單、公開 schema 與實際技能指引為準。
  名稱、安裝紀錄、其他 runtime 或模型自述不能證明等價；一般推理不需虛構探測。
- 方法可替換，前置、輸入、目標、讀寫權限、操作、證據、輸出及完成條件不得
  減少。部分相容只重用有效部分並補足缺口；未知、不可用或不相容時回到
  既有流程／安全 fallback。必要技能或能力仍缺失就明示未完成要求，不假裝
  執行、降低驗收或由名稱推定契約；繼續不依賴缺失能力的安全工作。
- 重用前核對 revision／diff、scope、假設、政策、環境與驗證新鮮度，漂移時
  重查受影響部分。保留來源與限制，將結果對應原輸出契約；PASS、自評或
  重新排版不能代替證據或完整 exact-head review。小任務只在既有報告簡述
  所選方式、重用與缺口，不另建 receipt／能力清冊；必要 artifacts 仍須產出。

## Contextual Prompt Composition

- 只組合適用共用契約、角色與有界任務。以目前 repo／Git／平台證據核對狀態；
  舊文件、摘要與 receipt 不能覆蓋指令優先序。使用者指示優先於 skill 預設，
  仍受較高優先指令、實際權限及破壞性 safeguards 約束。
- 在授權範圍內完成必要步驟，自行處理沿用模式的局部選擇，記錄重要假設。
  內部階段切換不重問既有授權；缺決策先做獨立安全準備，相依部分等待答案。
- 採用能驗證行為的必要檢查；必跑 checks 完成後，只有新變更、失敗或未解
  疑慮才擴大／重跑。不得省略獨立審查、必要驗證或 changed-head 完整審查。
- 中途修正保留適用成果並重查受影響證據；狀態詢問先簡答再續行，除非目標
  明確取消／替換。使用者摘要精簡，review／gate 證據保留必填欄位、findings、
  commands、skipped checks 與限制。模型專屬提示需實測，不建立 model×effort 矩陣。

## Decision And Stop Conditions

目標、來源、ownership、授權或範圍有未解實質衝突，出現需使用者決策的
安全／資料／信任風險，或高風險驗證不足時，停止相依操作。領域名稱本身
不是停工理由。逐項核對 commit、push、PR、receipt／comment、merge、tag、
Release、deploy 的目標、範圍、授權與 gate；已授權且前置通過就續行。
破壞性操作保留明確意圖、精確預覽、影響與復原條件。

若 skill 造成停止，指出實際讀過的 SKILL.md、條文與適用理由，先核對既有
授權，再提出具體待決事項。工具拒絕須分類，採合規替代或如實回報，不得
繞過權限或當作完成。可用、派送、PASS 與任務狀態都不授予操作權。

## Protected Boundaries

觸發成立時，在相依操作前讀下列細則及該操作入口；未成立的列不載入。
細則與政策位於本檔同目錄，安裝後仍如此。缺少必要文件時按上述 fallback
處理，不能因未讀而豁免義務。

| 觸發 | 必讀細則／入口 | 始終保留的邊界 |
| --- | --- | --- |
| 能力替代／重用的相容性不明 | [Capability Selection](reusable-workflow-details.md#contract-preserving-capability-selection) | 比對完整義務；必要技能缺失不推定等價。 |
| 正式 commit／PR／merge gate | [Review And Merge](reusable-workflow-details.md#review-and-merge)、[Decision And Stop Conditions](reusable-workflow-details.md#decision-and-stop-conditions) 及適用 review gate 技能 | findings、dispositions、blocking、獨立審查；gate 不授權寫入。 |
| 已有 change request、head 改變或宣稱 merge content readiness | [exact-head contract](exact-head-merge-review-contract.md) | 最新完整 base-to-head review；pre-commit verdict 不替代。內容與 provider 分開；只有 repo 選定 GitHub profile 才讀 [GitHub profile](github-exact-head-enforcement-profile.md)。 |
| 驗收失敗或返工 | [Decision And Stop Conditions](reusable-workflow-details.md#decision-and-stop-conditions) 及 [model selection](model-selection-policy.md) 的「返工分類、升級與續行」 | 不放寬驗收或角色資格；兩輪未完成 review/fix 觸發 context-continuity 評估，非自動停工／建立任務。 |
| 委派、角色選取或編排多階段交付 | [Contextual Prompt Composition](reusable-workflow-details.md#contextual-prompt-composition)、[Shared Phases](reusable-workflow-details.md#shared-phases) 及適用編排技能 | 主代理資格核對、ownership、整合與完成責任；reviewer 唯讀、作者獨立；worker 不繼承外寫權。 |
| thread／session／adapter 或持久資料操作 | [Protected Boundaries](reusable-workflow-details.md#protected-boundaries)、[Runtime Differences](reusable-workflow-details.md#runtime-differences)、[Capability Selection](reusable-workflow-details.md#contract-preserving-capability-selection) 及適用操作技能 | runtime discovery、schema、讀回與資料專屬契約；不自行啟用、遷移、雙寫或刪除。 |
| 批次／並行工具呼叫，或大量工具驅動工作需編排 | [Code Mode policy](code-mode-tool-orchestration-policy.md) | 能力須由當前 surface 證明；未知／不相容走 sequential fallback。依賴、approval、mutations、wait/resume 保持順序，限制輸出並逐項檢查結果。 |

## Shared Phases

一般任務依適用技能讀來源、規劃最小範圍、執行、驗證、檢查 diff、必要審查
及文件同步；有界多階段交付另讀上表的 Shared Phases 細則。

## Runtime Differences

共享義務不隨 runtime 改變；子代理與 task／session／schedule 操作分開，
後者有獨立授權與公開 runtime 契約，依上表載入。

## Review And Merge

Primitive 提供品質證據；formal gate 提供 blocking readiness，兩者都不授權
外寫。內容、provider 與 merge 授權分開；依上表取得完整 gate 與 exact-head 要求。

文字量與靜態案例不是 runtime 攔截器、品質或 live 行為等價證明；跨模型、
token、成本、延遲改善須代表性配對量測。
