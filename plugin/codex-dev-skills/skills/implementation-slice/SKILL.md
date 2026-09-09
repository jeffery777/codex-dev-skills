---
name: implementation-slice
description: Implement a bounded software change after read-only inspection, then verify and inspect the diff.
---

# implementation-slice

Runtime compatibility: shared

執行方式選用：先讀 `../../policies/reusable-workflow-contract.md` 的
`Contract-Preserving Capability Selection`；本地安裝改讀
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/reusable-workflow-contract.md`。
可重用契約相容的原生／內建／本地執行結果；本技能的必要步驟、證據與輸出仍適用。
同一契約的 Contextual Prompt Composition 與 Decision And Stop Conditions
規範當次工作包、驗證尺度、已授權續行及真正停止條件。

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

## Purpose

Use this skill for a focused implementation task where the target behavior is clear.

## Workflow

1. Read repo instructions, relevant files, tests, and current git state when available.
2. Identify affected files and likely verification before editing.
3. Make the smallest scoped change that satisfies the objective.
4. Avoid unrelated refactors and do not overwrite unrelated user changes.
5. Run the smallest relevant verification.
6. Inspect the diff before reporting.

## Commit Behavior

Do not commit unless the user explicitly asks for a commit or repo policy clearly requires it and the human gate is satisfied.

## Output

- Changed files
- Behavior changed
- Verification run
- Skipped verification, if any
- Residual risk
