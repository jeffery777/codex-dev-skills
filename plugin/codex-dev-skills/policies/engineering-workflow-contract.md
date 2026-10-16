# Portable Engineering Workflow Contract

This is the compatible Codex/Hermes policy entry. First follow the
[fixed Core loading contract](core-contract-loading.md): verify the selected
snapshot and read the full required workflow and authorization/stops documents.
Shared obligations have one fixed Core source. This adapter does not grant
qualification, external writes or production execution.

## Stages And Evidence

The full Discover, Plan, Implement, Verify, Review And Fix, Docs Sync, Delivery
Gate and Continue duties are in Core [wf-stages](../vendor/engineering-workflow-core/contracts/workflow.md#wf-stages).
Keep the existing entry skills and task DoD. Small work may combine stages but
must retain applicable duties. Plans and session states do not prove completion.

## Risk, Review Timing And Evidence Lifecycle

At task start and after scope/design changes, assess actual impact and unknowns
under Core [review-risk-timing](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-risk-timing).
Unknown is not low risk. Read full fixed review/security before selecting review
timing/depth; high-risk work needs early independent deep design/security analysis,
then deep code review and necessary proportional scanning as substantial code or
diff becomes available. Keep cheap applicable checks during development. Final
candidate binding is an acceptance duty, not a prerequisite for starting review.
Use the existing [security policy](security-review-escalation-policy.md) and
project overlay; impact determines retest/review/rescan and justified evidence reuse.

During work and closeout, use Core
[wf-evidence-lifecycle](../vendor/engineering-workflow-core/contracts/workflow.md#wf-evidence-lifecycle)
through the full workflow/authorization reading above and the existing
[artifact policy](review-artifact-policy.md). Keep a compact cause/fix/version/
replacement index in existing reports. Load current evidence and summaries first;
context slimming grants no source deletion authority. Unresolved, intermittent,
shared or still-referenced evidence remains protected. Missing retention policy
or period means retain and mark pending, not invent a universal deadline.

## Documentation Writing And Review

For natural-language documents and delivery summaries, apply Core
[wf-writing](../vendor/engineering-workflow-core/contracts/workflow.md#wf-writing).
Read the full fixed workflow through the loading contract above. For filesystem
templates, that clause is in
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/core/contracts/workflow.md#wf-writing`.
The existing docs-update and docs-review skills apply this shared obligation;
docs-review-gate retains its existing evidence and blocking duties. This adds no
separate writing standard, gate or conformance checker.

## Runtime Capability Selection

Use Core [wf-capability](../vendor/engineering-workflow-core/contracts/workflow.md#wf-capability),
[wf-delegation](../vendor/engineering-workflow-core/contracts/workflow.md#wf-delegation)
and [wf-verification](../vendor/engineering-workflow-core/contracts/workflow.md#wf-verification).
Codex-specific discovery remains in
[native capabilities (source/plugin)](../docs/native-runtime-capabilities.md);
filesystem installs read
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/docs/native-runtime-capabilities.md`.
Do not require Codex TOML, Desktop callables or functions.exec from Hermes.
Keep each runtime's credentials, actual permissions, model/effort and identity
separate. Existing qualification/profile preflight and fallback remain in effect.

## Adapter Boundaries

- Codex retains project-delivery, project-orchestrator, primitive review and
  implementation plus CLI/Desktop adapters. Custom-agent selection follows
  existing qualification/profile preflight; no defaults or fallback change.
- Hermes retains hermes-project-delivery, hermes-review-gate and
  hermes-task-continuation with complete sibling dependencies. Shared does not
  qualify other Codex skills for Hermes.
- Record adapter version, surface/backend, instruction/profile bytes and actual
  acceptance scope. Limited support does not qualify all tools, delegation,
  OS sandbox or automatic lifecycle. Unknown capability stays unknown.

## Verification And Publication

Use `scripts/verify-engineering-workflow.py` only for its fixed functional fixture.
Each entry prepares and verifies its own observations; independently read back
protected tests/spec/docs. It does not prove model equivalence, isolation,
independent review, a formal gate or complete runtime qualification. Keep failed
and incomplete cases. Private runtime/model/profile evidence stays outside Git.

Review follows the applicable skills and [exact-head adapter](exact-head-merge-review-contract.md).
GitHub operations use the selected [control-plane policy](github-control-plane-policy.md).
Commit/push/PR/MR/merge/tag/Release/deploy/cleanup each retain their own authority
and gates; neither tests nor a helper's success grants permission.
