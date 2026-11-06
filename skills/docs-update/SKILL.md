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

Writing requirements come from fixed Core `wf-writing` and its on-demand full
`contracts/writing.md`, resolved through
[Documentation Writing And Review](../../policies/engineering-workflow-contract.md#documentation-writing-and-review).
For filesystem installs, use that section of the installed policy path above.

## Workflow

1. Read the relevant code, specs, README, docs, and current git state when available.
2. Confirm the readers, purpose, genre, language and required understanding or operating depth. Check context and use `wf-writing` to select the reading depth. When a document is the substantive drafting, editing or translation target, read the full fixed writing contract. A requested summary document counts; routine engineering summaries do not automatically require it. Pure spelling/formatting with no meaning change can use the minimum unless stricter rules apply; even short changes to steps, risks or important conclusions are substantive. Separate verified facts, inference, opinion and hypothetical examples.
3. Update only the docs in scope. Apply the selected writing requirements to terminology, sentence meaning, explicit actors/actions and step order. Reduce unnecessary jargon, abbreviations, mixed-language wording and noun sequences for the chosen readers. Keep necessary technical terms and established abbreviations; explain them on first use when the reader needs it. Preserve author voice in general articles and mixed genres without inventing personal experiences, quotations or data; do not force every article into a procedure.
4. Preserve required technical detail, prerequisites, safety, authority, evidence, risks and limitations. Do not rewrite exact machine literals, required quotations or license text for writing style.
5. For bilingual docs, compare obligations, risks, limitations and important information against the authoritative text.
6. Attribute faithful citations and check whether the source supports the specific claim and its conditions; do not require authors to repeat every cited experiment. Own research or effect claims need proportionate real evidence, methods and relevant baselines. For missing or unsupported sources in an existing draft, preserve the claim and flag it for checking or author confirmation; do not silently change its meaning or fabricate support. Do not add unsupported factual/effect claims to a new draft. Retain source conflicts and applicable versions; do not turn unresolved safety information into definite instructions.
7. Check applicable writing requirements and record the sample scope, results and unverified limits in the document or existing report. For English technical text, claim full STE conformance only with complete rules, controlled-dictionary and applicable technical-term checks; otherwise state that full conformance is unverified. Equivalent notices may retain that meaning, subject to stricter downstream wording or placement requirements. General English articles follow their genre. Traditional Chinese uses natural Taiwan wording and consistent terms, not only character conversion; it must not be reported as STE-conformant or an official Chinese ASD standard.
8. Avoid adding private paths, credentials, local runtime state, or machine-specific assumptions.
9. Run lightweight verification such as link checks, markdown lint when available, or targeted text checks. Writing depth changes waive no applicable safety, authorization, review or exact-head duties.

## Output

- Docs changed
- Source evidence used
- Verification run
- Writing checks, sample scope and unverified limits
- Any unverified assumptions
