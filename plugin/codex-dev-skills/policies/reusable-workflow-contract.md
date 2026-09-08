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

## Shared Phases

1. Read source-of-truth files and current state.
2. Plan the smallest safe task slice.
3. Implement or delegate within scope.
4. Verify with relevant commands.
5. Inspect the diff.
6. Run review primitives when required; reserve formal review gates for commit readiness, PR readiness, merge readiness, or explicit repo-policy blocking decisions.
7. Sync docs or status when required.
8. Stop at human gates for ambiguity, risk, destructive actions, or external writes.

## Runtime Differences

Codex CLI and Codex Desktop may use bounded shared subagents when supported,
with disjoint ownership and main-agent verification. They may otherwise execute
phases sequentially or through prompts, task briefs, and continuation prompts.

Codex Desktop may additionally control user-owned tasks, threads, worktrees,
and schedules through documented runtime capabilities. Those control-plane
actions do not replace durable repository artifacts or human-gate policy.

## Review And Merge

Review primitives such as `code-review`, `docs-review`, and high-risk `code-review-deep` provide ordinary quality evidence. Formal `code-review-gate` and `docs-review-gate` runs provide blocking readiness evidence only when commit readiness, PR readiness, merge readiness, or explicit repo policy requires that decision. Neither review evidence nor formal gate evidence by itself authorizes commit, push, merge, deploy, platform comments, review submissions, or platform publication.
