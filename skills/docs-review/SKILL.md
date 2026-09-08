---
name: docs-review
description: Read-only review for docs-only or docs-dominant changes.
---

# docs-review

Runtime compatibility: shared

執行方式選用：先讀 `../../policies/reusable-workflow-contract.md` 的
`Contract-Preserving Capability Selection`；本地安裝改讀
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/reusable-workflow-contract.md`。
可重用契約相容的原生／內建／本地執行結果；本技能的必要步驟、證據與輸出仍適用。

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

## Purpose

Use this skill when the changed surface is documentation.

## Review Focus

- accuracy against code, specs, or product behavior
- missing prerequisites or unsafe instructions
- confusing structure
- stale links or names
- private or machine-specific material
- unsupported claims

## Workflow

1. Inspect docs diff and relevant source evidence.
2. Separate correctness issues from style preferences.
3. Report blockers first.
4. Include verification commands when applicable.

## Output

Use the applicable sections below; omit empty sections unless repository policy
requires them. Keep the reviewed revision/diff, scope, evidence and verification
limits explicit even when no findings are found.

- Executive Summary
- MUST-FIX
- SHOULD-FIX
- NITS
- Questions
- Re-runnable Verification Commands
