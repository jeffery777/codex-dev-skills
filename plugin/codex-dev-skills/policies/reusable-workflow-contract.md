# Reusable Workflow Contract

This contract defines the shared shape for Codex CLI and Codex Desktop development workflows.

## Contract-Preserving Capability Selection

規劃、實作、文件更新與審查可由模型直接完成，或使用當前可用的原生工具、
內建技能、本地技能及其組合。技能名稱指定適用契約；除非使用者、較高優先
指令或該契約指定必要方法，不要求為同一工作重跑另一套實作。

先讀適用技能的必要契約，再選最小相容方式。直接呼叫一般技能與經由編排
入口進入時，都遵守下列規則：

1. 保留使用者指定的技能與方法，遵守較高優先指令。不得以本條款跳過必讀
   指引、必要工具、既定驗證器、獨立審查或適用的模型資格程序。
2. 只檢查與當次操作相關的能力。工具可用性依當前工具清單與公開呼叫契約，
   技能依當前可取得的描述與實際指引；不能由名稱相似、安裝紀錄、其他 runtime
   或模型自述推定等價。一般模型推理不需虛構工具或能力探測呼叫，品質由
   任務所需的驗證及審查判斷。
3. 比對必要前置、輸入與目標範圍、唯讀／變更權限、必要操作、證據、輸出欄位
   及完成判定。執行方法可以替換，這些契約義務不能減少。可用不代表已啟用、
   已授權、已完成或品質／成本較佳。
4. 完全相容時採用該方式；部分相容時只重用有效部分，補足缺口。能力未知、
   不可用或不相容時，回到適用技能的既有流程／安全 fallback。若必要能力仍
   不可得，明示缺口，不假裝執行，也不降低驗收標準。
5. 將結果對應到適用輸出契約，保留原始來源與限制。重用證據前比對目前
   revision／diff、scope、假設、政策、環境與驗證新鮮度；漂移時重查受影響部分。
   單獨的 PASS、模型自評或格式重排不能替代必要證據或完整 exact-head review。
6. 在既有報告中簡短交代所選方式、重用證據及尚缺要求；一般小任務不另建
   receipt、能力登錄表或完整技能盤點。契約已要求的 artifacts 則照常產出。

## Protected Boundaries

- Formal gates 保留 findings、dispositions、blocking 與完成語意；符合契約的
  primitive 證據可被採用，但原生 review 結果不能自行跳過 gate。變更後的
  change-request head 仍須完整 base-to-head exact-head Merge Review。
- 子代理的模型／角色選擇仍遵守適用資格及整合規則；原生派送能力不能繞過它們。
- CLI／Desktop adapters 保留身分、授權、schema、回應驗證及操作後讀回要求；
  執行方式替代不授權 session、任務、排程、外部寫入或破壞性操作。
- 記憶與其他持久資料受專屬資料契約控制。原生 recall 不是 M1／MG1 管理
  backend 的等價替代，不得因此自動切換儲存、雙寫、啟用、遷移或刪除。
  scope、來源、版本、精確確認、刪除覆蓋及操作證據仍須由適用契約驗證。

這是指引層的選用規則，不是 runtime 攔截器或模型品質資格證明。跨模型、
token、延遲及成本改善須有代表性配對測量，不能由文字縮短或靜態案例推定。

## Contextual Prompt Composition

每次只組合適用的共用契約、角色責任與當次 task brief。模型特有的行為提示
只在有實測依據時加入，不建立模型乘上 effort 的完整提示詞矩陣。

- 先區分事實來源與指令優先序：以目前 repository／Git／平台證據核對狀態；
  舊文件、交接摘要與 receipt 不得覆蓋較高優先指令或當次明確使用者要求。
  使用者指示優先於 skill 的預設指引，仍須遵守較高優先指令、實際權限與
  適用的破壞性 safeguards。無法釐清的實質衝突才交回決策。
- 由主代理根據實際 workload、風險與驗證負擔選既有 class／tier／profile，
  核對目的 runtime 的模型、effort、角色及資格，再填入有界任務。brief 引用
  既有 route／profile 與當前證據，不自建資格或以「深入思考」取代 effort 設定。
- brief 明列目標、角色、ownership、當前來源、DoD、必要驗證、輸出及升級
  條件。授權記錄須可回溯至有效使用者指示；模板欄位、摘要、PASS、模型
  能力或任務完成狀態本身不能授權操作。
- 在已授權範圍內自主完成必要步驟。沿用既有模式的局部實作選擇可自行決定，
  簡短記錄影響結果的假設；已明確授權的操作不因內部階段結束而重問。
  缺少決策時先完成不依賴該決策的安全準備；不得執行仍依賴答案的部分。
- 主代理負責拆解、整合、獨立驗證、gate 與整體完成。子代理只完成指定
  工作包，不能繼承主代理的外部寫入權；worker 維持檔案 ownership，reviewer
  保持唯讀。有獨立、可驗證且能改善品質或耗時的工作才委派，不為配額拆工。
  子代理只回報需主代理決策的 blocker 與最後 receipt；使用者進度由主代理說明。
- 小任務採用必要且能驗證行為的檢查；完成適用必要 checks 後，只有新變更、
  失敗或未解決疑慮才擴大或重跑。不得以測試預算省略必跑檢查、獨立審查或
  changed-head 的完整 exact-head review。失敗先分類；資料、環境或權限
  缺失不以提高 effort 處理。複雜度改變則由主代理重新分類，不私改固定 profile。
- 使用者中途修正範圍時，保留仍適用的成果並重查受影響證據；詢問狀態或
  旁支問題時，先簡短回答再續行原目標，除非使用者明確取消或替換目標。
  輸出依接收者：使用者摘要清楚精簡，worker／review／gate
  artifacts 保留必填欄位、findings、commands、skipped checks 與證據限制。

## Decision And Stop Conditions

領域名稱不是停止判定。處理 security、migration 或 public contract 的有界
唯讀審查可繼續；變更涉及新出現或未解決的行為、資料、信任邊界等實質風險，
且需要使用者決策或高風險驗證不足時，停止受影響的操作。目標／ownership／
授權不明、無法釐清的來源衝突、範圍擴大，亦須先釐清。

Commit、push、PR、receipt／comment、merge、tag、Release、deploy 等逐項
核對當前目標、範圍、授權與適用 gate。沒有授權就完成安全準備後交回；已有
明確授權且前置通過就繼續。破壞性操作仍須明確意圖、精確預覽、理解影響及
復原條件，不能由一般自主執行指引略過。

GitHub profile 的順序為：完成內容審查及 required CI → 在已授權範圍發布並
讀回 receipt → dedicated App 驗證該 receipt → 合併前重新讀回全部必要狀態。
該次 receipt 的 App verdict 不能成為其發布前置；receipt 發布也不能取代
合併 gate 或自動授予 merge 權限。這不修改 runtime 自動核准機制。

若 skill 導致停下來，指出實際讀過的 SKILL.md 路徑、相關條文及其適用原因，
區分明文要求與推論。先查目前授權是否已涵蓋，再提出具體待決事項；不要由
模糊措辭另加 approval 流程。工具拒絕時分類原因，採用合規替代或如實回報，
不得繞過權限或把拒絕當作已完成。

## Shared Phases

1. Read source-of-truth files and current state.
2. Plan the smallest safe task slice.
3. Implement or delegate within scope.
4. Verify with relevant commands.
5. Inspect the diff.
6. Run review primitives when required; reserve formal review gates for commit readiness, PR readiness, merge readiness, or explicit repo-policy blocking decisions.
7. Sync docs or status when required.
8. Apply Decision And Stop Conditions to unresolved decisions, insufficient authority or verification, and destructive safeguards; otherwise continue the authorized work.

## Runtime Differences

Codex CLI and Codex Desktop may use bounded shared subagents when supported,
with disjoint ownership and main-agent verification. They may otherwise execute
phases sequentially or through prompts, task briefs, and continuation prompts.

Codex Desktop may additionally control user-owned tasks, threads, worktrees,
and schedules through documented runtime capabilities. Those control-plane
actions do not replace durable repository artifacts or human-gate policy.

## Review And Merge

Review primitives such as `code-review`, `docs-review`, and high-risk `code-review-deep` provide ordinary quality evidence. Formal `code-review-gate` and `docs-review-gate` runs provide blocking readiness evidence only when commit readiness, PR readiness, merge readiness, or explicit repo policy requires that decision. Neither review evidence nor formal gate evidence by itself authorizes commit, push, merge, deploy, platform comments, review submissions, or platform publication.
