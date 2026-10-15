# Reusable Workflow Contract

本檔保留 Codex CLI／Desktop 與既有 Hermes 工程入口及七個舊 anchors。
先依 [固定 Core 載入契約](core-contract-loading.md) 核對實際 root／lock／bytes，
讀完整固定 workflow 與 authorization/stops；review/exact-head 按觸發讀全文。
共用義務唯一來源是 Core；本檔與 [細則](reusable-workflow-details.md) 只保留
Codex 操作接點、既有必要技能及條件入口。不預載未觸發的接口政策。

## Contract-Preserving Capability Selection

完整共用規則見 Core [wf-capability](../vendor/engineering-workflow-core/contracts/workflow.md#wf-capability)。
保留使用者方法、較高優先指令、完整必要義務與驗證新鮮度；不能略過必讀、
驗證器、獨立審查或資格。必要技能或能力仍缺失時回報未完成要求，僅續行
獨立安全部分。名稱、安裝、PASS 或另一 runtime 的紀錄不證明等價／授權。

## Contextual Prompt Composition

共用委派與驗證見 Core wf-delegation／wf-verification。依當前 Codex
model-selection／qualification／context-continuity 與適用技能處理實際設定；
完整 brief、ownership 與主代理整合責任見下方觸發。摘要與舊 receipt 不覆蓋來源。

## Decision And Stop Conditions

每次依 Core authorization/stops 保留精確 scope、有效既有授權、未知效果讀回、
破壞性 safeguards 與真正停止條件。缺必要獨立審查／scan／驗證或發生實質
authority／來源／風險衝突，停止相依操作；不是每個內部階段重新索取授權。
Skill 停止須引用實際條文；工具拒絕先分類，不繞過或假報完成。

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

讀完整固定 Core workflow 的八階段；[工程 adapter](engineering-workflow-contract.md)
保留 Codex/Hermes 既有入口、fixture 與工具接點。一般任務不強制 loop／Goal／多代理。

## Runtime Differences

核心共用義務不等於 runtime 等價。CLI/TUI/Desktop/Bundled CLI 各自核對有效
工具、schema、model/effort、權限／session 與實際載入 bytes；thread/session/schedule
仍有獨立操作契約與授權。不得從共享 sandbox 推定獨立技術唯讀隔離。

## Review And Merge

Primitive 提供品質證據，formal gate 提供 blocking readiness；都不授權外寫。
依觸發讀完整 Core review/security／exact-head 與所選專案 overlay。內容、平台、
操作授權分列；靜態檢查與文字量不能證明 runtime、品質、token／成本或延遲改善。
