---
name: docs-update
description: Update project documentation from verified code, specs, plans, or behavior.
---

# docs-update

Runtime compatibility: shared

工程階段與完成標準共用 `../../policies/engineering-workflow-contract.md`；
filesystem 安裝改讀 `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/engineering-workflow-contract.md`。
Runtime 操作依當次 adapter 與能力證據選取，既有 Codex qualification 仍適用。

執行方式選用：先讀 `../../policies/reusable-workflow-contract.md` 的
`Contract-Preserving Capability Selection`；本地安裝改讀
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/reusable-workflow-contract.md`。
可重用契約相容的原生／內建／本地執行結果；本技能的必要步驟、證據與輸出仍適用。

## Purpose

Use this skill when docs need to be aligned with implemented behavior, plans, or repository policy.

Writing requirements come from fixed Core `wf-writing`, resolved through
[Documentation Writing And Review](../../policies/engineering-workflow-contract.md#documentation-writing-and-review).
For filesystem installs, use that section of the installed policy path above.

## Workflow

1. Read the relevant code, specs, README, docs, and current git state when available.
2. Confirm the readers, purpose, document type and required operating depth. Separate verified facts from inferred behavior.
3. Update only the docs in scope. Apply `wf-writing` to terminology, sentence meaning, explicit actors/actions and step order; explain necessary terms for those readers.
4. Preserve required technical detail, prerequisites, safety, authority, evidence, risks and limitations. Do not rewrite exact machine literals, required quotations or license text for writing style.
5. For bilingual docs, compare obligations, risks, limitations and important information against the authoritative text.
6. Check applicable writing requirements and record the sample scope, results and unverified limits in the document or existing report. For English technical text, claim full STE conformance only with complete rules, controlled-dictionary and applicable technical-term checks; otherwise state that full conformance is unverified, as Core requires. Traditional Chinese uses Core's plain-writing adaptation and must not be reported as STE-conformant.
7. Avoid adding private paths, credentials, local runtime state, or machine-specific assumptions.
8. Run lightweight verification such as link checks, markdown lint when available, or targeted text checks.

## Output

- Docs changed
- Source evidence used
- Verification run
- Writing checks, sample scope and unverified limits
- Any unverified assumptions
