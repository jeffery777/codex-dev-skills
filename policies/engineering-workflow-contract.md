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
