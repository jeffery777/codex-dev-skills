# Migration From Private Packs

This document records old private names only to explain the public rename. Do not use old private names in new skills or workflows.

## Canonical Shared Layer

`shared/review-workflow-codex/codex` is the canonical shared layer source for version 1. The synchronized shared files under `packs/review-workflow-codex/codex` and `packs/review-workflow-codex-desktop/codex` are duplicate pack copies.

The private verification script reported the shared layer is in sync. Public migration therefore keeps one renamed shared layer only:

- `shared_code_review_gate` -> `code-review-gate`
- `shared_doc_review_gate` -> `docs-review-gate`
- `shared_merge_review_gate` -> `merge-readiness-gate`
- `shared_review_artifact_cleanup` -> `review-artifact-cleanup`
- `closure_triage` -> `closure-triage`

Do not migrate pack-local duplicate copies separately.

| Old private name | Public name | Classification |
| --- | --- | --- |
| `u1_plan` | `planning` | RENAME, REWRITE |
| `u1_deliver` | `project-delivery` | RENAME, REWRITE |
| `u1_implement` | `implementation-slice` | RENAME, REWRITE |
| `u1_docs` | `docs-update` | RENAME, REWRITE |
| `code_review` | `code-review` | RENAME, REWRITE |
| `code_review_deep` | `code-review-deep` | RENAME, REWRITE |
| `doc_review` | `docs-review` | RENAME, REWRITE |
| `merge_review` | `merge-review` | RENAME, REWRITE |
| `merge_review_deep` | `merge-review-deep` | RENAME, REWRITE |
| `mr_followup_plan` | `review-follow-up-plan` | RENAME, REWRITE |
| `review_followup_impl` | `review-follow-up-implementation` | RENAME, REWRITE |
| `doc_review_followup_impl` | `docs-review-follow-up` | RENAME, REWRITE |
| `mr_review_followup` | `review-follow-up-review` | RENAME, REWRITE |
| `implement_review_loop` | `review-loop` | RENAME, REWRITE |
| `shared_code_review_gate` | `code-review-gate` | KEEP_SHARED_CANONICAL, RENAME, REWRITE |
| `shared_doc_review_gate` | `docs-review-gate` | KEEP_SHARED_CANONICAL, RENAME, REWRITE |
| `shared_merge_review_gate` | `merge-readiness-gate` | KEEP_SHARED_CANONICAL, RENAME, REWRITE |
| `shared_review_artifact_cleanup` | `review-artifact-cleanup` | KEEP_SHARED_CANONICAL, RENAME, REWRITE |
| `closure_triage` | `closure-triage` | KEEP_SHARED_CANONICAL, RENAME, REWRITE |
| `desktop_project_delivery` | `desktop-project-delivery` | RENAME, REWRITE |
| `desktop_project_orchestrator` | `desktop-project-orchestrator` | RENAME, REWRITE |
| `desktop_spec_plan_gate` | `desktop-spec-plan-gate` | RENAME, REWRITE |
| `desktop_implementation_gate` | `desktop-implementation-gate` | RENAME, REWRITE |
| `desktop_pr_merge_gate` | `desktop-pr-merge-gate` | RENAME, REWRITE |
| `merge_review_dual` | `merge-review-dual-pass` | EXCLUDE from version 1 skills, documented as future candidate |
| `merge_review_dual_deep` | `merge-review-dual-pass-deep` | EXCLUDE from version 1 skills, documented as future candidate |
| `merge_review_autoloop` | `merge-review-autoloop` | EXCLUDE from version 1 skills, documented as future candidate |
| `codex_merge_review` | `merge-review-pass-b` | EXCLUDE as standalone public skill |
| `codex_merge_review_deep` | `merge-review-deep-pass-b` | EXCLUDE as standalone public skill |
| `dual-engine` | `dual-pass` | EXCLUDE as a legacy alias |

## Version 1 Classification

KEEP_SHARED_CANONICAL:

- code-review-gate
- docs-review-gate
- merge-readiness-gate
- review-artifact-cleanup
- closure-triage

KEEP_CLI_OR_SHARED:

- planning
- project-delivery
- implementation-slice
- docs-update
- code-review
- code-review-deep
- docs-review
- merge-review
- merge-review-deep
- review-follow-up-plan
- review-follow-up-implementation
- docs-review-follow-up
- review-follow-up-review
- review-loop

KEEP_DESKTOP_ONLY:

- desktop-project-delivery
- desktop-project-orchestrator
- desktop-spec-plan-gate
- desktop-implementation-gate
- desktop-pr-merge-gate

DUPLICATE_SHARED_COPY:

- shared-layer copies inside `packs/review-workflow-codex/codex`
- shared-layer copies inside `packs/review-workflow-codex-desktop/codex`

KEEP_CLI_ONLY:

- none in version 1; CLI-priority concepts were rewritten as shared workflows where possible.

REWRITE:

- all kept skills were rewritten for public names, runtime labels, and public-safe wording.

EXCLUDE:

- platform-specific MR adapter skills
- knowledge or vault capture skills and templates
- compatibility aliases
- standalone pass-B reviewer skills
- generated workflow examples for external schedulers
- shared-layer sync script, because the public repo does not keep duplicate pack copies

## Installer Migration

The private installer and catalog were inspected but not copied verbatim.

Public replacements:

- `install.sh`: Codex-only installer for skills and templates.
- `catalog.yaml`: Codex-only public catalog with shared, review, delivery, and Desktop workflow groups.
- `scripts/validate-repo.sh`: public hygiene validator replacing duplicate shared-layer verification.

The old shared-layer sync workflow is not retained because the public repository keeps one shared layer and does not maintain pack-local duplicate copies.
