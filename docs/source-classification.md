# Source Classification

This file summarizes the read-only classification of the allowed source material.

## Source Priority

1. `shared/review-workflow-codex/codex` is the canonical shared layer source.
2. `packs/review-workflow-codex/codex` provides CLI/shared/core/general workflow concepts, excluding duplicate shared-layer files.
3. `packs/review-workflow-codex-desktop/codex/skills/desktop_*` provides Desktop-only orchestration concepts.
4. Repo-native extensions may be added when later maintenance work defines new public Codex workflows from accepted repository policy and examples.

The shared-layer verification script reported that the shared layer is in sync. Therefore pack-local shared files are duplicate synchronized copies and are not treated as independent public sources.

## KEEP_SHARED_CANONICAL

Source: `shared/review-workflow-codex/codex`

Public outputs:

- closure-triage
- code-review-gate
- docs-review-gate
- merge-readiness-gate
- review-artifact-cleanup
- human gate policy
- model selection policy
- review artifact policy
- security review escalation policy
- runtime/shared workflow policy concepts
- orchestration templates for project specs, implementation plans, task briefs, integration reports, and gate reports

## KEEP_CLI_OR_SHARED

Source: non-duplicate content from `packs/review-workflow-codex`

Public outputs:

- planning
- project-delivery
- project-orchestrator
- implementation-slice
- docs-update
- code-review
- code-review-deep
- docs-review
- merge-review
- merge-review-deep
- orchestrated review closure workflow examples and report templates

## KEEP_DESKTOP_ONLY

Source: `packs/review-workflow-codex-desktop/codex/skills/desktop_*`

- Desktop project delivery, Desktop spec/plan gate, Desktop implementation gate, and Desktop PR/merge gate concepts.

Public outputs:

- desktop-project-delivery
- desktop-spec-plan-gate
- desktop-implementation-gate
- desktop-pr-merge-gate

## KEEP_REPO_NATIVE_EXTENSION

Source: accepted public repository policy, runtime compatibility guidance, and maintained examples.

This bucket covers repo-native documentation that extends the public workflow set after the original source classification. It is limited to accepted public repository policy, runtime compatibility guidance, maintained examples, and the non-state-changing Desktop runtime wrapper V1 planner, capability metadata normalization helper, and contract comparison helper. The implemented surface is limited to those helpers; Desktop runtime integration, runtime-call adapters, daemons, MCP servers, app-server clients, and state-changing Desktop thread-tool paths remain outside the implemented scope.

Public outputs:

- desktop-thread-delegation
- runtime compatibility guidance in `docs/runtime-compatibility.md`
- Desktop runtime adapter v2 boundary guidance in `docs/runtime-adapter-v2.md`
- Desktop runtime wrapper v1 planner helper, capability metadata normalization helper, contract comparison helper, planner `capability_evidence` input path, and implementation plan in `docs/desktop-runtime-wrapper-v1-plan.md`
- runtime adapter boundary example in `examples/runtime-adapter-boundary.md`
- Desktop thread delegation example in `examples/desktop-thread-delegation.md`
- skill selection guidance for Desktop thread delegation and runtime contract evidence in `docs/skill-selection-guide.md`

Boundary:

- Desktop thread actions are runtime actions, not CLI guarantees.
- The CLI-compatible fallback is a prompt, task brief, continuation prompt, or sequential execution path.
- Fallback wording must not imply that Codex CLI can open, fork, continue, message, or control Desktop threads unless a documented or configured thread capability is actually available.
- Repo-native runtime evidence must use public repository files, ordinary git or shell inspection, documented runtime tools, caller-supplied documented metadata, installed connector metadata, normalized capability evidence, or maintained examples.
- It must not depend on private Desktop runtime state such as local databases, logs, sessions, auth files, caches, app state, unpublished endpoints, UI scraping, daemons, background services, local runtime directories, or private runtime files.
- Runtime thread tool/API contract evidence must record contract name, version or `version unavailable` plus capability source, minimal request/response shape, `last_verified`, and workflow, wrapper, or adapter mapping to the underlying contract.
- Runtime/schema change re-checks may compare old wrapper contract evidence with newer normalized capability evidence, but comparison is evidence only and does not authorize Desktop thread-tool calls.

## DUPLICATE_SHARED_COPY

Source: pack-local shared files in both allowed packs.

The following public shared outputs are based only on the canonical shared layer, even though synchronized copies exist in the CLI/shared pack and Desktop pack:

- closure-triage
- code-review-gate
- docs-review-gate
- merge-readiness-gate
- review-artifact-cleanup
- shared orchestration policies
- shared orchestration templates

This avoids copying the same shared skill from multiple locations and prevents public-layer divergence.

## Installer And Maintenance Scripts

Inspected source scripts:

- `install.sh`
- `catalog.yaml`
- `scripts/sync-review-shared-layer.sh`
- `scripts/verify-review-shared-layer.sh`

Public disposition:

- The source installer concept is KEEP_CLI_OR_SHARED, but the implementation is REWRITE. The public installer is Codex-only and removes all non-Codex targets, paths, functions, and branches.
- The source catalog concept is KEEP_CLI_OR_SHARED, but the catalog is REWRITE. The public catalog lists only Codex and Codex Desktop groups.
- The shared-layer sync script is EXCLUDE because the public repo does not keep duplicate pack copies.
- The shared-layer verification script is REWRITE as `scripts/validate-repo.sh`, which checks public repo hygiene, catalog paths, and skill runtime labels.

## RENAME

- Private abbreviations and underscore names were renamed to public kebab-case names.

## REWRITE

- Kept skills and policies were rewritten to remove private naming, local paths, legacy compatibility language, and runtime assumptions.

## EXCLUDE

- Platform-specific MR adapter skills and templates.
- Knowledge, Obsidian, and vault capture content.
- Compatibility aliases.
- Standalone pass-B reviewer skills.
- External scheduler examples.
