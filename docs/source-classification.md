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

This bucket covers repo-native documentation that extends the public workflow set after the original source classification. It is limited to accepted public repository policy, runtime compatibility guidance, maintained examples, and the Desktop runtime wrapper V1 planner, capability metadata normalization helper, contract comparison helper, create-thread preflight helper, read-thread preflight helper, evidence pipeline helper, session compatibility status validator, first-use handshake helper, session-scoped compatibility cache helper, create-thread authorization/evidence gate helper, create-thread executor boundary proposal helper, create-thread executor shell helper, single documented create-thread callable executor helper, create-thread callable wiring-boundary helper, and create-thread callable bundle / executor-request assembly helper. The implemented executor, wiring, and bundle surface is limited to caller-injected documented callable adapters, caller-supplied documented descriptors, explicit non-live adapter wiring contracts, and non-live executor request previews; it is non-live by default. Desktop runtime integration, live runtime-call adapters, daemons, MCP servers, app-server clients, and broad state-changing Desktop thread-tool paths remain outside the implemented scope.

Public outputs:

- desktop-thread-delegation
- runtime compatibility guidance in `docs/runtime-compatibility.md`
- Desktop runtime adapter v2 boundary guidance in `docs/runtime-adapter-v2.md`
- Desktop runtime wrapper v1 planner helper, capability metadata normalization helper, contract comparison helper, create-thread preflight helper, read-thread preflight helper, evidence pipeline helper, session compatibility status validator, first-use handshake helper, session-scoped compatibility cache helper, create-thread authorization/evidence gate helper, create-thread executor boundary proposal helper, create-thread executor shell helper, single documented create-thread callable executor helper, create-thread callable wiring-boundary helper, create-thread callable bundle / executor-request assembly helper, planner `capability_evidence` input path, and implementation plan in `docs/desktop-runtime-wrapper-v1-plan.md`
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
- Session compatibility status validation may report `ready` only when explicit caller-supplied status matches expected wrapper/helper identity, target action, tool/API name, schema hash or normalized contract evidence, compatible comparison result, `last_verified`, and session marker evidence. It is evidence only, does not write a compatibility cache, and does not replace runtime action authorization, external-write authorization, target validation, permission handling, or response validation.
- First-use handshake may report `ready` only when caller-supplied documented metadata compares as compatible, the helper constructs a session compatibility status, and that status validates. It is evidence only, does not read or write a compatibility cache, and does not replace runtime action authorization, external-write authorization, target validation, permission handling, or response validation.
- Session-scoped compatibility cache read/write may report `ready` only when a caller-explicit cache envelope matches expected wrapper/helper identity, status helper version, target action, tool/API name, schema hash or normalized contract evidence, compatible comparison result, `last_verified`, session marker, and same-session lifecycle marker. It is contract compatibility evidence only; Codex CLI/Desktop restart, session marker mismatch, stale/expired cache, fallback, or stopped status must block later runtime-call paths. It does not replace runtime action authorization, external-write authorization, target validation, permission handling, or response validation.
- Create-thread preflight may report `ready` only when repo, prompt, capability, compatible comparison, exact thread-action authorization, and blocked external-write evidence are complete. `ready` is evidence only for a future separately approved runtime call and does not call `create_thread` or authorize external writes.
- Create-thread authorization/evidence gate may report `ready` only when exact create-thread action/tool evidence, repo/remote/branch/expected-head target evidence, prompt evidence, ready preflight evidence, ready same-session status/cache evidence, exact caller authorization intent, next-step human approval marker, blocked external-write/destructive boundaries, target validation, permission/auth failure handling placeholders, runtime response validation placeholders, `runtime_call_performed: false`, and no private runtime state read evidence are complete. `ready` is evidence only for a human to consider separately approving one future implementation slice and does not call or authorize `create_thread`.
- Create-thread executor boundary proposal may report `ready` only when ready authorization gate evidence, exact create-thread action/tool evidence, repo/remote/branch/expected-head target evidence, prompt evidence, a proposal-only human approval marker, blocked external-write/destructive boundaries, `runtime_call_performed: false`, no private runtime state read evidence, one documented `create_thread` tool path, and call-site rechecks for target identity, authorization intent, permission/auth failure result, runtime response shape, returned thread id, and returned status are complete. `ready` is proposal readiness only for a human to consider separately approving one future true executor wiring slice and does not call or authorize `create_thread`.
- Create-thread executor shell may report `ready` only when ready executor boundary proposal evidence, exact create-thread action/tool evidence, repo/remote/branch/expected-head target evidence, prompt evidence, an executor-shell-only human approval marker, blocked external-write/destructive boundaries, `runtime_call_performed: false`, no private runtime state read evidence, `surface_only: true`, `runtime_call_authorized: false`, a non-executed callable descriptor or injected-adapter placeholder for `create_thread`, and call-site contract evidence for target identity, authorization intent, permission/auth failure classification, runtime response shape, returned thread id, and returned status are complete. `ready` is implementation-surface readiness only for a human to consider separately approving one future documented `create_thread` wiring slice and does not call or authorize `create_thread`.
- Single documented create-thread callable executor may report `ready` only when ready executor shell evidence is present, the helper itself rechecks target identity and authorization intent, prior proposal/gate/cache/preflight/shell evidence is not used as call-site validation, an explicit caller-injected documented adapter returns a valid response, auth/permission failures are classified and returned, returned thread id and status are valid, and the adapter reports `desktop_runtime_call_performed: false`, no private runtime state read, and no external write. CLI use without an injected runner returns `fallback`. `ready` is injected adapter contract completion only and does not authorize or prove live Desktop runtime `create_thread` execution.
- Create-thread callable wiring boundary may report `ready` only when ready executor evidence is present, exact create-thread action/tool evidence, repo/remote/branch/expected-head target evidence, prompt evidence, an exact human wiring marker, blocked external-write/destructive boundaries, `runtime_call_performed: false`, no private runtime state read evidence, an allowed caller-supplied documented descriptor source, and a single `create_thread` descriptor are complete. `ready` is callable wiring readiness only and does not call, authorize, discover, obtain, import, or prove live Desktop runtime `create_thread` execution. CLI/default use without a descriptor returns `fallback`, tests use explicit non-live wiring, and prior evidence cannot replace executor call-site target validation, permission/auth handling, response validation, returned thread id validation, or returned status validation.
- Create-thread callable bundle / executor-request assembly may report `ready` only when ready callable wiring evidence, ready executor-shell evidence, exact create-thread action/tool evidence, repo/remote/branch/expected-head target evidence, prompt evidence, an exact human bundle marker, the executor implementation marker expected by the executor helper, blocked external-write/destructive boundaries, `runtime_call_performed: false`, no private runtime state read evidence, no runner, no callable object, no direct runtime call shape, no live Desktop runtime flag, and a single `create_thread` path are complete. `ready` is executor request preview readiness only and does not call, authorize, discover, obtain, import, execute an injected runner, or prove live Desktop runtime `create_thread` execution. CLI/default use without wiring evidence returns `fallback`, tests produce only a non-live preview, and prior evidence cannot replace executor call-site target validation, permission/auth handling, response validation, returned thread id validation, or returned status validation.
- Create-thread live smoke may report `ready` only when exact human approval and a runtime-provided documented `create_thread` callable are injected, the helper rechecks target identity and authorization intent at the actual call site, the read-only audit smoke prompt is present, external-write/destructive boundaries remain blocked, permission/auth failures are classified, and the runtime response includes explicit `private_runtime_state_read: false` and `external_write_performed: false` flags plus a valid `thread_id` or `pendingWorktreeId` with an allowed status. CLI/default/tests without an injected callable return `fallback`. `ready` is single live smoke completion only and does not mean the audit completed, does not authorize another runtime call, and does not authorize comments, reviews, file edits, commits, pushes, PRs, merges, labels, status changes, or other platform writes. Prior evidence cannot replace call-site target validation, permission/auth handling, response validation, returned id validation, or returned status validation.
- Read-thread preflight may report `ready` only when repo, thread id, read-request purpose, read-only capability, compatible comparison, and blocked external-write evidence are complete. `ready` is evidence only for a future separately approved read-only runtime call and does not call `read_thread`, read Desktop private runtime state, or authorize external writes.
- The evidence pipeline may report aggregate `ready`, `fallback`, or `stopped` only by chaining caller-supplied metadata through discovery, contract comparison, and create/read preflight helpers. It is evidence only and does not call Desktop thread tools, collect metadata, read Desktop private runtime state, or authorize runtime calls or external writes.

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
