# Living Roadmap

This roadmap is intentionally small and adaptive. `codex-dev-skills` evolves from real project maintenance needs: add or revise skills when repeated work proves that a workflow, policy, template, review primitive, or formal gate adapter should be reusable.

## v0.1.x: Public Foundation

- Keep the installer, catalog, skills, templates, and README aligned.
- Keep validation focused on public hygiene, runtime compatibility labels, and catalog consistency.

## v0.2.x: More Maintainer Workflows

- Desktop Runtime Wrapper V1 is retired. Its non-executable historical record
  does not provide a compatibility or execution path; current behavior belongs
  to native runtime contracts and active runtime callables.
- Loop engineering adds an explicit shared entrypoint for clear bounded objectives: bootstrap from durable source of truth, classify current state, route through existing phase skills, verify and review evidence, continue or hand off when safe, and stop at human gates. It preserves the independent use of implementation, documentation, review, formal gate, continuation, milestone, and Desktop-specific skills.
- Issue #77 / PR #78 delivered repo-owned loop state and ledger support as a
  durable baseline, not a future task-selection target. The repository-owned
  contract, templates, validator, tests, and v0.4.0 point-in-time release note
  record that completed milestone: keep source revision, task state,
  claim/lease state, verification evidence, review evidence, blockers, and next
  decisions in repository files first; treat future external memory adapters as
  optional cache or coordination layers unless a repository explicitly defines
  a stronger reviewed authority model.
- Loop Engineering V1 is tracked in issue #81. It adds one production route and
  transition core, structured YAML validation, revision/event/idempotency
  guards, deterministic workflow evals, native Goal mode, shared subagents, and
  thin scheduler/Desktop task adapters.
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
- Issue #153 evolves that same V2a routing contract with event-driven
  coordination guidance and a Terra-high `senior` tier between routine
  Terra-medium and multi-trigger Sol-medium implementation. Terra-xhigh and
  Luna-max remain eval-first candidates. The `loop_v2a_` namespace remains a
  protocol identifier independent of the V3 improvement program.
- Milestone continuation adds a shared upper-layer workflow for checking bounded milestone task state across repeated invocations, selecting the next ready task, routing through existing delivery and continuation workflows, and keeping runtime scheduling outside the skill.

## Maintenance Approach

- Let real project usage reveal which skills need to be added or corrected.
- Prefer small, reusable workflow improvements over speculative workflow packs.
- Keep repo documentation aligned with installer groups, skill names, templates, and validation.
- Keep human gates explicit whenever a workflow approaches publication, release, merge, destructive action, or material risk.

## Backlog

- Issue #205 / PR #206 completed the v0.22.0 provider-neutral exact-head Merge
  Review baseline. Content readiness binds the final complete range,
  deterministic validation, findings, dispositions, and code/documentation
  coherence. Provider enforcement is reported separately. This repository
  retains its existing GitHub App/check/receipt/ruleset profile, while
  installed shared skills no longer impose it on GitLab CE or another forge.
  This completed baseline is not a future task-selection target.

- Issues #185, #190, #192, and #186 are completed exact-head rollout and
  immediate follow-up milestones, not future task-selection targets. Issue
  #185 delivered the trusted default-branch collector, dedicated GitHub App
  check identity, strict JSON receipt, and canary-first ruleset rollout; Issue
  #190 repaired the completed-check lifecycle; Issue #192 stabilized the Codex
  runtime compatibility baseline; and Issue #186 sharded repository tests
  behind the stable aggregate CI check. Together they form the durable
  post-v0.20 exact-head maintenance baseline while preserving separate human
  gates and the prohibition on executing untrusted PR code in the privileged
  collector.

- Issue #188 / PR #189 is reserved as intentionally retained operational
  canary evidence for that exact-head baseline. It is not pending product work
  and must stay unmerged. Canary cleanup remains a separate
  destructive human gate. Its live platform state, ruleset enforcement, and
  publication truth must be read from GitHub when needed rather than mirrored
  as mutable tracked current-state assertions.

- The release-state contract separates offline source/package version,
  candidate preparation, GitHub publication truth, active guidance, and
  historical notes. Active roadmap items do not carry a mutable current-release
  pointer; release-time publication checks read annotated tag and non-draft,
  non-prerelease GitHub Release metadata through the connector-first control
  plane. Ordinary repository validation remains offline.

- The v0.18.2 source snapshot recorded the precise `codex mcp-server`
  deprecation boundary without treating external MCP client support,
  connectors, or native Desktop tools as deprecated. It also added the
  fail-closed `--skip-unit-tests` validator mode and changed exact-head CI to
  run all non-unit checks and evals first, followed by one complete unittest
  discovery pass. Default validator behavior remained backward compatible and
  validation coverage was not reduced.

- Issue #175 / PR #176 published the v0.18.1 post-release state-coherence patch
  at merge commit `b5cb03ae467222215f42c3081cad796ad3a2ecf3`. The annotated
  `v0.18.1` tag and non-draft, non-prerelease GitHub Release bind that exact
  commit. The patch aligns active README, roadmap, readiness, continuation,
  version metadata, and drift-prevention contracts with the published v0.18.0
  state without changing shared, CLI, Desktop, or Memory runtime contracts,
  installer logic, target selection, installed payload behavior, or completion
  authority. Installer receipt metadata is 0.18.1. M2, V3-C, and Memory
  activation remain separately gated. The repository has no deployment target
  or publish/deploy workflow, so deployment is not applicable and the GitHub
  Release is not deployment evidence.

- Issue #171 / PR #172 delivered the Desktop Runtime Wrapper V1 retirement;
  Issue #174 / PR #173 published it as the v0.18.0 pre-1.0 minor release at
  merge commit `3b789e2f9749f2643b6fe75397d22f6e21a71ce2`. The retirement keeps
  wrapper-independent security invariants and native authorization, identity,
  fail-closed, private-state, external-write, and non-execution contracts; it
  does not create a replacement compatibility layer. The annotated `v0.18.0`
  tag and non-draft, non-prerelease GitHub Release bind the exact merge commit.
  The repository has no deployment target or publish/deploy workflow, so
  deployment is not applicable and the GitHub Release is not deployment
  evidence.

- Issue #167 / PR #168 published the v0.17.1 public-documentation coherence
  patch. It aligns
  README and the durable Operational Evidence continuation handoff with the
  released v0.14.0 M0/M1 baseline, removes stale routing to completed Issue
  #147 and v0.13.0, and adds regression coverage without activating M1 or
  changing shared, CLI, or Desktop runtime contracts. M2 and V3-C remain
  separately gated with release targets TBD.

- Issue #165 delivered the v0.17.0 context-continuity and fresh-rollover feature.
  Two unfinished review/fix rounds trigger a configurable assessment rather
  than automatic task replacement. The shared contract separates current-
  context regrounding, parallel bounded subagents, history-preserving fork, and
  checkpoint-only fresh rollover; binds single-writer stop/start ownership,
  lineage, idempotency, and anti-recursion; provides Desktop/CLI/IDE capability
  and fallback semantics; and keeps graph lineage advisory. CLI phase one is
  clean and non-interactive only. The bounded same-objective cost/quality pair
  is recorded in `docs/loops/issue-165/paired-run-evidence.md`; PR #166, the
  annotated tag, and the GitHub Release published that reviewed baseline.

- Issue #159 owns the v0.16.1 Linux qualification-timeout follow-up. Refresh
  entrypoints validate the existing bounded refresh timeout before contacting
  GitNexus and share one monotonic deadline across qualification, preflight,
  controller execution, and postconditions. Standalone qualification limits,
  fail-closed expiry, and all v0.16.0 identity/authority boundaries remain.
- Issue #161 owns the v0.16.2 Codex CLI/Desktop runtime-compatibility patch.
  It records CLI 0.149.0, keeps `codex agents` and UUID-only `codex queue` in
  the independent CLI control-plane adapter, adds privacy-gated immutable
  Desktop `share_thread` guidance, and preserves shared orchestration,
  completion authority, opt-in custom-agent profiles, and native runtime
  contract boundaries.
- Issue #157 completed GN-FU-01 in v0.16.0. It defines
  distinct primary-main, primary-branch, linked-worktree, detached, dirty, and
  PR base/head identities; binds exact evidence to complete relevant content,
  tool/configuration, and freshness; and makes old or missing sidecars
  explicitly advisory. Linked-worktree automatic refresh and remote-only merge
  advancement remain fail-closed. GitNexus remains non-authoritative.
- Issue #163 owns the v0.16.3 patch that prepared the historical V1 retirement
  evidence. Issue #171 later removed that obsolete surface after separate
  review, security evidence, recovery planning, and explicit authorization.
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
  consider a second provider or MCP adapter only after M1 passes. V3-B and M1
  were later published through their separately authorized Issues; M2 and
  V3-C release targets remain TBD. PlugMem and Mem0 remain excluded.
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
- Issue #149 / PR #150 published the v0.14.1 compatibility and packaging patch.
  It refreshed
  current Desktop automation/thread/panel/terminal and Linux-preview contracts,
  keeps CLI `/plugins` and `/import` outside `cli-session-handoff`, packages
  the canonical repository skill tree as one universal plugin, makes the
  filesystem installer fail closed on imported/plugin duplicates, and
  separates Codex/ChatGPT memories and Computer History from Memory M1. It
  did not change the v0.14.0 M0/M1 feature baseline or activate M1.
- Issue #151 owns the v0.14.2 installer-backup isolation hotfix. It moves
  forced-update backups for filesystem skills, templates, and agent profiles
  into a deterministic managed state-root hierarchy outside Codex discovery
  roots; existing slots, unsafe boundaries, and cross-device rename conditions
  fail closed before mutation in the supported cooperating-installer model.
  Cooperating updates share a canonical managed-state namespace; distinct state
  roots targeting one custom path do not share its lock and rely on apply-time
  drift detection rather than process isolation. Legacy adjacent `*.bak`
  remains user-owned and receives dry-run-first guidance only. This does not implement GN-FU-01,
  change the M0/M1 feature baseline, or authorize merge, tag, Release, or
  deployment.
- Issue #153 / PR #154 published the v0.15.0 agent-orchestration and routing
  release. It
  reduces unchanged-state polling and worker progress chatter, prefers
  ownership-based packets over one-agent-per-discipline fan-out, and inserts a
  Terra-high `senior` tier before multi-trigger Sol-medium implementation.
  Terra-xhigh and Luna-max remain eval-only; existing `loop_v2a_` identities
  remain stable because that namespace names the routing protocol rather than
  the repository or V3 program version.
- Issue #155 owns the v0.15.1 runtime compatibility patch. It preserves the
  shared-layer/CLI-adapter/Desktop-adapter architecture while adding CLI
  `codex exec fork`, Desktop worktree-fork lifecycle semantics, a shared
  GitHub connector-first control-plane policy, and checkout-aware GitNexus hook
  guidance. Linked-worktree automatic refresh remains fail-closed; post-merge
  refresh applies only after the primary checkout advances locally.
- Issue #157 delivered the v0.16.0 GitNexus index-lifecycle release. Its
  `gitnexus-index-identity/v1` sidecar prevents clean-HEAD metadata from
  impersonating dirty, untracked, ignored-content, cross-worktree, or
  cross-branch state and adds clean PR base/head pair identities. It does not
  activate query adoption, shared indexes, scheduling, or completion authority.

## Memory M1 Local Pilot

Issue #209 owns the v0.23.0 default-off thin local opt-in pilot. It preserves
the M1 SQLite/FTS5 schema and M0/V2b authority chain, exposes only explicit
manual/CI use, and qualifies synthetic retrieval safety evidence. It does not
authorize activation, promotion, real-world efficacy claims, external
providers, automatic lifecycle behavior, or private/raw data storage.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
