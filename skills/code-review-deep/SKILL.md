---
name: code-review-deep
description: Deep read-only code review for high-risk changes involving security, data, packaging, migrations, external integrations, or cross-module contracts.
---

# code-review-deep

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

Use this skill when routine review is not enough because the change has material blast radius or hidden failure modes.

## Additional Focus

- data integrity and migration rollback
- permission and identity boundaries
- sensitive data handling
- dependency and packaging risk
- concurrency and idempotency
- cross-module contracts
- observability and failure modes

## Workflow

Follow `code-review`, then add adversarial checks for edge cases, stale assumptions, rollback gaps, and evidence quality.

## Output

Use the `code-review` output structure and add a Deep Risk Notes section.
