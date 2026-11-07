---
name: docs-review
description: Read-only review for docs-only or docs-dominant changes.
---

# docs-review

Runtime compatibility: shared

工程階段與完成標準共用 `../../policies/engineering-workflow-contract.md`；
filesystem 安裝改讀 `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/engineering-workflow-contract.md`。
Runtime 操作依當次 adapter 與能力證據選取，既有 Codex qualification 仍適用。

執行方式選用：先讀 `../../policies/reusable-workflow-contract.md` 完整核心與觸發表；本地安裝改讀
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/reusable-workflow-contract.md`。
可重用契約相容的原生／內建／本地執行結果；本技能的必要步驟、證據與輸出仍適用。

Code Mode tool orchestration: before batching/concurrent tool calls or substantial
tool-driven orchestration, read
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

## Purpose

Use this skill when the changed surface is documentation.

Writing requirements come from fixed Core `wf-writing` and its on-demand full
`contracts/writing.md`, resolved through
[Documentation Writing And Review](../../policies/engineering-workflow-contract.md#documentation-writing-and-review).
For filesystem installs, use that section of the installed policy path above.

## Review Focus

- accuracy against code, specs, or product behavior
- missing prerequisites or unsafe instructions
- confusing structure
- stale links or names
- private or machine-specific material
- unsupported claims
- reader, purpose, genre, language and understanding or operating depth under the full fixed writing contract when the document itself is the review target
- consistent terminology, sentence meaning, explicit actors/actions, step order and necessary term explanations
- unnecessary jargon, abbreviations, mixed-language wording and noun sequences for the intended readers; keep necessary technical terms and established abbreviations, explain them when needed, and preserve precise meaning and machine literals
- preservation of technical detail, safety, authority, evidence, prerequisites, risks and limitations; writing-style changes must preserve exact machine literals, required quotations and license text
- bilingual equivalence against the authoritative text, including obligations and important information
- evidence for any full STE claim: formal rules, controlled dictionary, applicable technical terms and reviewed scope; short sentences, a checker or self-assessment alone are insufficient
- faithful attributed citations that support the specific claim and its conditions, distinct from the author's own research/effect claims requiring proportionate real evidence, methods and relevant baselines; no blanket requirement to repeat cited experiments
- missing/unsupported sources in an existing draft flagged for checking or author confirmation without silently changing the original claim; no fabricated support or unsupported new factual/effect claims
- author voice and genre preserved without invented experiences; natural Taiwan Traditional Chinese and meaningful translation, not only character conversion

## Workflow

1. Inspect docs diff and relevant source evidence. When the document itself is the review target, read the full fixed writing contract. Use `wf-writing` to distinguish routine engineering summaries from requested summary documents, and pure spelling/formatting from even short substantive changes to steps, risks or important conclusions. Check context and preserve stricter requirements; the reading condition waives no applicable safety, authorization, review or exact-head duties.
2. Sample the applicable writing requirements in the existing review; record scope, results and unverified limits. For English technical text, verify the evidence for any full STE claim and state when full conformance is unverified. Equivalent notices must retain that meaning and any stricter downstream wording/placement requirements; do not impose English technical controlled language on every general article. Traditional Chinese must not be reported as STE-conformant or an official Chinese ASD standard.
3. Apply Lightweight Requirements Traceability in the engineering policy above.
   Check that the docs preserve the required conditions and that their sources
   support the changed claims; inspect affected references proportionally and
   record verification gaps. Separate correctness issues from style preferences.
4. Report blockers first.
5. Include verification commands when applicable.

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
- Writing sample scope, results and unverified limits
