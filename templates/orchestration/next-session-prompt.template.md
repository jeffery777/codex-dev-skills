# Next Session Prompt

<!-- Fill only the next bounded packet. Link current source/evidence paths and
the checkpoint instead of copying all prior reports. Omit empty optional
sections; retain scope, ownership, DoD, verification and action boundaries. -->

Use `task-continuation` for this bounded continuation task.

## Task

- Task id: `<task-id>`
- Objective: `<bounded-objective>`
- Receiving responsibility: `<delivery owner | bounded worker | read-only reviewer>`
- Ownership: `<assigned files/artifacts; verified transfer when required>`

## Read First

以目前 repository／Git 證據核對狀態；依指令優先序處理要求。舊文件或交接
摘要不得覆蓋較高優先指令或當次明確使用者要求；無法釐清的實質衝突才交回。
讀取適用 workflow 的 reusable-workflow contract，尤其 Contextual Prompt
Composition 與 Decision And Stop Conditions。來源位於
`policies/reusable-workflow-contract.md`；filesystem 安裝位於
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/reusable-workflow-contract.md`。

- `<path>`

## Handoff Summary

This summary is context only, not source of truth.

`<current-task-summary>`

## Scope

In scope:

- `<item>`

Out of scope:

- `<item>`

## Files

Files to inspect:

- `<path>`

Files expected to change:

- `<path>`

## Definition Of Done

- `<done-criterion>`

## Verification

- `<command>`
- Required acceptance evidence: `<criteria/artifacts>`
- Expand or repeat for: `<new changes, failures or unresolved concerns>`

## Current Authority And Decisions

- Authorized actions and source: `<exact targets/scope and valid user instruction>`
- Pending decisions: `<concrete unresolved decision, or none>`
- Routine choices allowed: `<local choices within accepted requirements>`

以上欄位供接收者核對，不自授權；摘要本身也不轉移 ownership 或擴大權限。
子代理只繼承有界工作指派，不能承接主代理的 commit／平台寫入權。

## Stop Conditions

停止仍依賴未解決產品／授權／目標／ownership 決策的操作，先釐清無法解決的
來源衝突、範圍擴大、新出現或未解決的實質風險，以及高風險驗證不足。領域
名稱不是停止條件，已指派的唯讀風險審查可繼續。破壞性操作保留明確意圖、
預覽、影響範圍及復原 safeguards。已有明確授權且前置通過則繼續，不因階段
切換重問；缺少授權則先完成安全準備，回報具體待決事項及其來源。

## Rules

- 未有精確有效授權及適用 gate 時，不 commit、push、建立 PR、publish、merge、deploy、post platform comments、submit reviews 或執行破壞性操作；bounded worker 禁止這些操作。
- Reviewer 保持唯讀；主代理依接收者責任整合、驗證並判定整體完成。
- Do not edit outside assigned scope.
- Treat summaries and chat history as context only.
- Report changed files, verification run, skipped checks, risks, and open questions.
