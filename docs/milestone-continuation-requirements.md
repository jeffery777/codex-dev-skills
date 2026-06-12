# Milestone Continuation Requirements

## 背景

`codex-dev-skills` 目前已有 shared 與 Desktop 專用的專案推進能力：

- `task-continuation`：從 durable repository context 選出下一個 safe task，並準備 continuation prompt、task brief，或 sequential execution path。
- `project-orchestrator` / `project-delivery`：在 bounded project objective 內負責路由、實作、驗證、review、docs sync，以及停在 human gate。
- `desktop-thread-delegation`：在 Codex Desktop 中，當 runtime 支援且使用者明確授權時，將 bounded task 交接到新的 Desktop thread。

這份需求描述一個新的上層能力：在指定 milestone，例如 `MVP1`，尚未完成前，週期性檢查目前 task 狀態；若目前 task 已完成，挑選下一個 ready task 繼續推進；直到 milestone 達成或遇到需要人工決策的情況才停止。

## 目標

- 讓使用者可以指定一個 bounded milestone，例如 `MVP1`。
- 讓 agent 每次被喚醒時，能從 repo 內 durable artifacts 重新判斷目前 milestone 與 task 狀態。
- 若目前 task 未完成，繼續推進目前 task。
- 若目前 task 已完成，標記或確認完成狀態，並選出下一個最小 ready task。
- 若 milestone 已達成，停止並回報完成證據。
- 若遇到 human gate，停止並回報需要使用者決策的原因、最低風險選項，以及可能的下一步。
- 允許在 Codex Desktop 中搭配 heartbeat 或 automation 做週期性喚醒。

## 非目標

- 不取代 `task-continuation`、`project-orchestrator`、`project-delivery` 或 `desktop-thread-delegation`。
- 不在 skill 內硬編碼固定檢查間隔，例如每 10 分鐘。
- 不自行實作排程器、daemon、background service、MCP server、Desktop runtime adapter、app-server client，或任何未公開 Desktop runtime 整合。
- 不讀取或修改 Codex Desktop 私有 runtime state，例如 local databases、logs、sessions、auth files、caches 或 app state。
- 不自動 commit、push、建立 PR、merge、deploy、發布、送出 review、留言到平台，或執行 destructive action，除非使用者針對該精確動作另行授權。

## 排程與提示詞行為

檢查頻率應由 invocation 或 runtime scheduling layer 決定，而不是寫死在 skill 中。

使用者可以在啟用此能力時用提示詞指定期望頻率，例如：

```text
請每 5 分鐘檢查一次目前專案任務狀態。
若目前 task 已完成，請挑選下一項 ready task 執行。
持續推進直到 MVP1 目標達成，或遇到需要人工決策的情況才停下來。
```

這類提示詞應被解讀為排程意圖與每輪執行目標，但真正的週期性喚醒必須由支援的 runtime 能力負責，例如 Codex Desktop heartbeat 或 automation。

若 runtime 不支援指定的頻率，agent 應回報限制，並提供最接近且安全的替代方案，例如產生 paste-ready continuation prompt、改成手動觸發，或使用 runtime 支援的其他排程粒度。

## Source Of Truth

每輪執行前必須重新讀取 durable source-of-truth files。聊天摘要只能作為 context，不可作為權威來源。

建議 milestone-enabled 專案至少具備：

- repo instructions，例如 `AGENTS.md`
- milestone spec，例如 `docs/milestones/MVP1.md`
- task manifest，例如 `docs/tasks/MVP1.yaml`
- project status 或 continuation report
- relevant implementation plan、review evidence、verification commands
- current git branch、status、upstream、diff

若目標 repo 尚未具備足夠 source-of-truth artifacts，此能力應先產生或要求建立必要規格，而不是直接開始自動推進。

## 每輪執行流程

1. 重新讀取 repo instructions、milestone spec、task manifest、status docs、review evidence、templates、policies 與 git state。
2. 確認目標 milestone 是否仍有效，且未被 source-of-truth conflict 阻斷。
3. 分類 task 狀態：`done`、`in_progress`、`ready`、`blocked`、`unsafe`、`unknown`。
4. 用 task 的 DoD 與 verification commands 判斷目前 task 是否完成。
5. 若目前 task 未完成，選擇最小安全行動繼續目前 task。
6. 若目前 task 已完成，更新或準備更新 task 狀態，並選出下一個最小 ready task。
7. 若下一步適合目前 thread，依照 `project-orchestrator` 與 `project-delivery` 繼續。
8. 若下一步適合交接給新 session 或 worker，使用 `task-continuation` 準備 bounded prompt 或 task brief。
9. 若在 Codex Desktop 中需要開新 thread，使用 `desktop-thread-delegation` 的規則，並在明確授權後才呼叫 runtime thread tool。
10. 執行後跑最小相關驗證，檢查 diff，並回報目前 milestone、task、verification、remaining risk 與下一步。

## Task Selection Rules

- 優先選擇最小、ready、低風險、能直接推進 milestone 的 task。
- 不選擇 source-of-truth 不明、DoD 不明、依賴未滿足、風險過高或需要人工決策的 task。
- 不因為排程自動化而放寬 human gate。
- 不把「測試通過」單獨視為 task 完成；仍需符合 DoD、scope、review 或 docs sync 需求。
- 若多個 task 都 ready，選擇 blast radius 最小且驗證最清楚的 task。

## Human Gates

遇到以下情況必須停止：

- product semantics 或 scope 不清
- source-of-truth files 互相衝突
- 需要 destructive action
- 需要 external write
- 需要 commit、push、PR、merge、deploy、release、平台留言或 review submission
- 涉及 material security、privacy、data、migration、payment、permission 或 deployment risk
- 驗證不足以支撐高風險變更
- Desktop thread tool contract、permission、target identity、branch、worktree 或 response shape 不清楚
- 只有 unpublished Desktop internals、private runtime state、UI scraping、daemon 或 sidecar path 可用

## 與現有技能的關係

這個新能力應作為上層 orchestration loop，並重用現有技能：

```text
runtime heartbeat / automation
-> milestone-continuation
-> project-orchestrator / project-delivery
-> task-continuation
-> desktop-thread-delegation, only when Desktop handoff is needed and authorized
```

現有技能仍可直接使用：

- 單純要挑下一個 safe task：使用 `task-continuation`。
- 要在 bounded delivery objective 內持續推進：使用 `project-delivery`。
- 要在 Desktop 中交接到新 thread：使用 `desktop-thread-delegation`。
- 要週期性推進 milestone：使用這個新 milestone continuation 能力，再視需要路由到上述技能。

## Runtime Compatibility

Shared behavior:

- 讀取 durable repo artifacts。
- 判斷 milestone / task 狀態。
- 準備 continuation prompt 或 task brief。
- 在目前 session 中執行安全的小步驟。
- 停在 human gate。

Desktop-only behavior:

- 使用 heartbeat 或 automation 週期性喚醒 thread。
- 在 runtime tool 存在且使用者授權後，建立、fork、讀取或傳訊給 Desktop thread。

CLI fallback:

- 不宣稱 CLI 可以自行開 Desktop thread。
- 產生 paste-ready prompt、task brief、continuation prompt，或在目前 CLI session 內走 sequential execution path。

## Suggested Invocation Prompt

```text
Use milestone-continuation for MVP1.

Every time this thread wakes up, read the repository instructions, milestone spec,
task manifest, status docs, review evidence, and current git state.

Check whether the current task is complete using its DoD and verification commands.
If it is incomplete, continue the current task using the smallest safe action.
If it is complete, update or prepare the task state update and choose the next
smallest ready task.

Continue until MVP1 is complete or a human gate is reached.

Stop for product ambiguity, source-of-truth conflict, scope expansion, destructive
action, external write, commit/push/PR/merge/deploy/release approval, platform-side
mutation, material security/privacy/data/migration/payment/permission risk, or
insufficient verification for a high-risk change.

At the end of each run, report the current milestone status, current task status,
files changed, verification run, remaining risk, and the next intended task.
```

When used with Codex Desktop scheduling, the user can add a runtime-level instruction such as:

```text
Wake this thread every 5 minutes and run the MVP1 milestone-continuation loop.
```

The scheduling instruction configures the runtime wakeup cadence; the skill defines what to do after each wakeup.

## Acceptance Criteria

- The requirement distinguishes skill behavior from runtime scheduling behavior.
- The feature composes with existing continuation, delivery, orchestration, and Desktop thread delegation skills.
- The feature preserves existing human gates and Desktop runtime boundaries.
- The feature does not depend on chat memory as source of truth.
- The feature supports user-specified cadence, such as 5 minutes or 10 minutes, without hardcoding a cadence in the skill.
- The feature has a clear CLI fallback and does not claim Desktop-only behavior is available in CLI.
