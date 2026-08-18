# Living Roadmap

This roadmap is intentionally small and adaptive. `codex-dev-skills` evolves from real project maintenance needs: add or revise skills when repeated work proves that a workflow, policy, template, review primitive, or formal gate adapter should be reusable.

## v0.1.x: Public Foundation

- Keep the installer, catalog, skills, templates, and README aligned.
- Keep validation focused on public hygiene, runtime compatibility labels, and catalog consistency.

## v0.2.x: More Maintainer Workflows

- The former Desktop runtime wrapper V1 chain is frozen as historical
  compatibility and regression evidence. It is not an active execution path;
  future cleanup may archive or remove it only through a separately reviewed
  deprecation slice.
- Loop engineering adds an explicit shared entrypoint for clear bounded objectives: bootstrap from durable source of truth, classify current state, route through existing phase skills, verify and review evidence, continue or hand off when safe, and stop at human gates. It preserves the independent use of implementation, documentation, review, formal gate, continuation, milestone, and Desktop-specific skills.
- Repo-owned loop state and ledger support is the next loop-engineering hardening step: keep source revision, task state, claim/lease state, verification evidence, review evidence, blockers, and next decisions in repository files first; treat future external memory adapters as optional cache or coordination layers unless a repository explicitly defines a stronger reviewed authority model.
- Loop Engineering V1 is tracked in issue #81. It adds one production route and
  transition core, structured YAML validation, revision/event/idempotency
  guards, deterministic workflow evals, native Goal mode, shared subagents, and
  thin scheduler/Desktop task adapters. The v0.x Desktop wrapper chain becomes
  legacy compatibility evidence rather than the active runtime path.
- Loop Engineering V2a shipped in v0.6.0 from issue #85. It adds deterministic
  capability classification, replaceable custom-agent profiles, runtime
  preflight/degradation, and route/worker/integration receipts while preserving
  the V1 authority model. The v0.6.1 compatibility patch from issue #89 aligns
  the deep-capability profile templates with the current Desktop-reported
  `gpt-5.6-sol` model ID while retaining exact-ID preflight and safe fallback.
- Loop Engineering V2a cost-aware routing shipped in v0.7.0 from issue #93. It
  adds a versioned class/tier route: Luna low for mechanical reads, Terra
  low/medium for exploration and routine work, Sol medium/high for advanced
  and deep/security work, and a narrow Sol xhigh exceptional tier. It preserves
  version 1 compatibility and V1/V2b authority.
- Milestone continuation adds a shared upper-layer workflow for checking bounded milestone task state across repeated invocations, selecting the next ready task, routing through existing delivery and continuation workflows, and keeping runtime scheduling outside the skill.
- Keep any later Desktop runtime wrapper slices behind separate review and human approval, especially before adding remediation, broader runtime thread-tool invocation, platform writes, or any other state-changing path.

## Maintenance Approach

- Let real project usage reveal which skills need to be added or corrected.
- Prefer small, reusable workflow improvements over speculative workflow packs.
- Keep repo documentation aligned with installer groups, skill names, templates, and validation.
- Keep human gates explicit whenever a workflow approaches publication, release, merge, destructive action, or material risk.

## Backlog

- High-priority GitNexus index-lifecycle follow-up: at the next suitable
  maintenance window, open a dedicated Issue and branch to define distinct
  `main`, issue-branch, linked-worktree, dirty-tree, and PR-review identities.
  A commit-based "up-to-date" status does not prove dirty or untracked content
  freshness;
  exact evidence needs complete content binding and clean committed base/head
  rules before automation or completion use. Issue #147 records the bounded
  observation in `docs/loops/issue-147/follow-ups.md` without making it M1
  release scope.
- Historical wrapper cleanup: inventory tests and documents that still require
  `desktop_runtime_*`, define a compatibility sunset, then archive or remove
  them without connecting them to the active native path.
- Plugin packaging follow-up: if maintainers want Codex plugin distribution, add a minimal `.codex-plugin/plugin.json` and repo marketplace entry in a separate slice. Keep it distinct from the filesystem installer and document duplicate-skill risks for users who install the same pack through both paths.
- Global profile synchronization follows the accepted Loop Engineering V1
  authority, goal, subagent, and human-gate contract. The separate global
  profile repository should not be edited in issue #81.
- Loop Engineering V2b is tracked in issue #91. It defines a versioned,
  backend-neutral external-memory safety contract, offline validator,
  deterministic dispositions, conformance harness, receipts, tests, and evals.
  It remains useful with no backend and preserves V1/V2a completion authority.
- Loop Engineering V2c-A shipped in v0.8.0 from issue #97. It establishes a
  default-disabled GitNexus 1.6.9 qualification boundary, strict schema-5
  identity/freshness metadata, an honestly narrowed handshake with `read_query`
  and all backend mutations unsupported, and an explicit offline `index-only`
  refresh controller. It remains unable to replace repository completion truth.
- Loop Engineering V2c-B shipped in v0.9.0 from issue #103. It adds bounded
  `SessionStart` plus `PostToolUse` Bash freshness checks and separately
  enabled auto-on-demand refresh only through the qualified V2c-A controller.
  Codex currently exposes no native `post-commit` event, so the Bash signal is
  explicitly incomplete and `SessionStart` compensates. Hooks remain optional,
  inactive-by-default guardrails; the adapter stays safe when hooks are absent,
  untrusted, malformed, or unavailable. V2c-B does not add eager reindexing,
  scheduling, a daemon, or a direct bare GitNexus mutation path.
- The v0.9.1 alignment patch was completed by issue #107 and PR #108. It
  updates the README to the shipped V2c-B baseline, records one real
  machine-local `notify-only` project-hook adoption without committing active
  configuration, and preserves the accepted next-program context for later
  tasks. The live report is advisory pilot evidence, not an
  operational-evidence schema or completion authority.
- The v0.9.1 repository-guardrail follow-up was completed by issue #109 and PR
  #110. It makes direct GitNexus analysis index-only by default and requires
  ready pull requests to close an open same-repository Issue through a
  template, fail-closed validator, and least-privilege CI check. These controls
  provide repository hygiene and traceability only; they do not change
  completion or merge authority.
- The bounded v0.9.1 release closure is tracked in issue #111. It aligns
  version and release metadata, closes Phase 0 program handoff evidence, and
  proves the post-bootstrap PR linkage workflow without implementing V2d-A.
- The v0.9.2 runtime-compatibility release closure is tracked in issue #117.
  It publishes the Codex CLI/Desktop interface refresh from issue #113 and the
  bounded CLI-only session handoff adapter from issue #115 without changing
  the V2c-B feature baseline or implementing V2d-A.
- The v0.9.3 Code Mode tool-orchestration maintenance release is tracked in
  issue #119. It adds one shared repository-owned batching and concurrency
  policy, deploys it through existing workflow-group dependencies, validates
  source and installed references, and preserves sequential fallback,
  approval, mutation-order, output-bound, and runtime-compatibility contracts.
  It does not change the V2c-B feature baseline or implement V2d-A.
- Loop Engineering V2d-A is delivered by issue #121 for v0.10.0. It defines
  `loop-operational-evidence/v0` core contracts for run receipts, iteration
  summaries, failure taxonomy, redacted environment fingerprints, and artifact
  references with strict offline validators, typed relationship rules,
  synthetic adversarial fixtures, and deterministic evals. The contract
  preserves false authorization, completion, external-write, and promotion
  invariants and stores no real operational records in this public repository.
- Loop Engineering V2d-B is delivered by issue #124 in v0.11.0.
  It adds separate strict improvement-lineage and projection families,
  baseline/candidate lineage, declared role separation, deterministic
  tool-neutral Markdown and typed graph manifests, and an optional declarative
  Obsidian profile while preserving V2d-A. See
  [the Operational Evidence program](programs/operational-evidence/README.md).
- The v0.11.1 compatibility patch release is tracked in issue #131. It
  publishes the Issue #129 / PR #130 Codex Desktop task-registration,
  project-placement, same-directory continuation, host-routing, and sidebar
  compatibility refresh; adds the bounded CLI manual interactive-fork
  guidance; and makes Python/PyYAML verification environment-aware without
  changing the V2d-B feature baseline or shared workflow semantics.
- Loop Engineering V3-A evidence-to-proposal is delivered by issue #133 and
  PR #134 in v0.12.0. It adds a separate strict proposal-set family,
  complete V2d-A/B lineage, deterministic integer scoring, stable ties and
  duplicate suppression, bounded hypotheses/output intents, synthetic
  adversarial evals, and a stdout-only manual/CI CLI. All outputs remain
  proposal-only behind a pending independent human/platform promotion gate.
  PlugMem, Mem0, external-memory integration, V3-B candidate execution, V3-C
  automation, approval, activation, merge, release, and deployment are not
  included.
- The v0.12.0 release closure is tracked in issue #137. It finalizes the V3-A
  release record, preserves Issue #135 / PR #136 as planning-only
  documentation, and binds the annotated tag and GitHub Release to the exact
  reviewed release merge commit without implementing V3-B or Agent Memory.
- The v0.12.1 compatibility patch is released through issue #139. It
  refreshes the current Desktop `create_thread` title, project-association,
  worktree-default, and list schema contract; adds one repository-owned Python
  resolver shared by Desktop worktrees, CLI worktrees/private clones, and CI;
  and preserves the independent runtime adapters and unchanged V3-A/shared
  workflow authority. Its annotated tag and GitHub Release are bound to the
  exact reviewed merge commit.
- The private manual/CI proof of concept satisfied the durable V3-A re-entry
  gate without placing private records or platform identity in this public
  repository. Issue #133 now implements the evidence-to-proposal slice only.
  Candidate output cannot self-approve, activate, merge, release, or deploy.
  V3-B execution and V3-C hooks, schedulers, controllers, database services,
  and graph execution remain deferred behind new gates.
- Issue #135 owns a separate docs-only V3-B re-entry and Agent Memory roadmap.
  It does not perform release closure, V3-B implementation, M0 qualification,
  backend implementation, or automation. The accepted dependency order is:
  after the separately published v0.12.0 baseline, implement and qualify V3-B
  isolated candidate evaluation; only then qualify a thin default-disabled
  local/manual/CI SQLite/FTS5 Memory M1 reference adapter through a separate
  Issue/spec/ADR/security review; and consider V3-C optional resident
  automation only after another human decision. M0 defines the
  contract-to-runtime, provider-neutral protocol, operation-authority,
  execution-receipt, lifecycle, concurrency, security/privacy, and
  memory-off/on qualification requirements without adding a backend. M2 may
  consider a second provider or MCP adapter only after M1 passes. V3-B, M1,
  M2, and V3-C release targets are TBD; PlugMem and Mem0 remain excluded.
- Issue #141 / PR #142 deliver the bounded V3-B isolated
  candidate-evaluation family as `loop-candidate-evaluation/v0`; Issue #143
  publishes that reviewed baseline in v0.13.0. V3-B uses closed synthetic
  manual/CI observations, one fixed policy, exact public environment matching,
  deterministic independent replay, memory-off by default, and an optional
  digest-only V2b-validated advisory-context seam. Its packet cannot promote,
  merge, release, deploy, activate, or perform an external write. Memory M1/M2
  and V3-C remain separate future human gates with release targets TBD.
- Issue #145 owns Memory M0 provider-neutral readiness. Its bounded candidate
  adds separate `loop-memory-operation/v0` and
  `loop-memory-qualification/v0` offline families, caller-owned exact
  operation authority, authorized-request composition, atomic receipt
  validation, logical-delete/idempotency/privacy/recovery boundaries, and a
  safety/conformance-only paired wrapper over unchanged V3-B outputs. It adds
  no SQLite/FTS5 import/probe/backend, schema/database, persistence, provider,
  MCP, PlugMem/Mem0, automatic recall/write, or V3-C. Memory-off remains zero
  backend/filesystem touch; physical purge and efficacy claims are deferred.
  M0 is included in the v0.14.0 public baseline but remains a non-backend
  authority and qualification layer.
- Issue #147 owns the separate Memory M1 SQLite/FTS5 reference-adapter
  candidate. It is additive, default-disabled, and local/manual/CI-only; uses
  an explicit approved machine-local state root; behavior-probes an isolated
  temporary FTS5 database; binds exact SQLite build, tokenizer, platform,
  schema, and capability fingerprints; accepts only bounded structured query;
  and carries M0 authority through atomic logical state plus receipt. It makes
  no efficacy, shared-host confidentiality, encryption, cross-host, physical
  purge, migration/repair, activation, or promotion claim. Issue #147 / PR
  #148 select **v0.14.0** for the reviewed M1 safety/conformance baseline.
- Issue #149 owns the v0.14.1 compatibility and packaging patch. It refreshes
  current Desktop automation/thread/panel/terminal and Linux-preview contracts,
  keeps CLI `/plugins` and `/import` outside `cli-session-handoff`, packages
  the canonical repository skill tree as one universal plugin, makes the
  filesystem installer fail closed on imported/plugin duplicates, and
  separates Codex/ChatGPT memories and Computer History from Memory M1. It
  does not change the v0.14.0 M0/M1 feature baseline, activate M1, or authorize
  tag/release publication before the reviewed merge gate.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
