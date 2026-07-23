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
- The v0.9.1 alignment patch is tracked in issue #107. It updates the README to
  the shipped V2c-B baseline, records one real machine-local `notify-only`
  project-hook adoption without committing active configuration, and preserves
  the accepted next-program context for later tasks. The live report is
  advisory pilot evidence, not an operational-evidence schema or completion
  authority.
- Loop Engineering V2d is the next planned feature milestone. V2d-A will define
  `loop-operational-evidence/v0` core contracts for run receipts, iteration
  summaries, failure taxonomy, redacted environment fingerprints, and artifact
  references with strict validators and synthetic fixtures. V2d-B will add
  improvement lineage, a tool-neutral human-readable projection boundary, an
  optional Obsidian reference profile, and the minimum typed graph projection
  manifest. See
  [the Operational Evidence program](programs/operational-evidence/README.md).
- A private manual/CI proof of concept must validate the V2d contracts before
  Loop Engineering V3-A begins. V3-A remains the reserved
  Evidence-Driven Self-Improvement milestone and starts with evidence-to-proposal
  workflow only. Candidate output cannot self-approve, activate, merge, release,
  or deploy. Resident hooks, schedulers, controllers, database services, and
  graph execution remain deferred beyond that gate.

## Non-Goals

- General prompt collection.
- Private workflow migration guide beyond the public compatibility notes.
- Runtime-local state capture.
- Credentials, private paths, local logs, app state, or machine-specific config.
