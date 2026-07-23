# Loop Engineering v0.9.1 Alignment And Live Notify-Only Adoption

## Objective

Deliver GitHub Issue #107 as a bounded patch release that:

1. aligns the public README with the V2c-B baseline shipped in v0.9.0;
2. adopts the existing V2c-B project hook in machine-local `notify-only` mode
   and records sanitized live runtime evidence;
3. creates durable repository context for the next Operational Evidence and
   Evidence-Driven Self-Improvement development stages.

This issue does not implement Operational Evidence V0.

## Source Of Truth

- Repo instructions: `AGENTS.md`
- GitHub objective: Issue #107
- V2c-B contract: `docs/loops/issue-103/loop-spec.md`
- V2c-B public boundary: `docs/external-memory-contract.md`
- Current roadmap: `docs/roadmap.md`
- Program overview: `docs/programs/operational-evidence/README.md`
- Architecture decisions:
  `docs/programs/operational-evidence/architecture-decisions.md`
- Phase plan: `docs/programs/operational-evidence/implementation-phases.md`
- Continuation handoff:
  `docs/programs/operational-evidence/continuation.md`
- Implementation plan: `docs/loops/issue-107/implementation-plan.md`
- Task manifest: `docs/loops/issue-107/task-manifest.yaml`

Repository files, Git state, verification, review, and accepted platform state
remain authoritative. Hook output, GitNexus metadata, research reports,
runtime summaries, and future operational evidence remain advisory context.

## Scope

### In Scope

- Correct the README's stale V2b milestone statement.
- Add v0.9.1 release notes and roadmap alignment.
- Materialize and validate one machine-local V2c-B project hook in
  `notify-only` mode.
- Use the normal Codex project-layer trust review before the hook runs.
- Observe at least one supported live hook event when the runtime permits it.
- Record a sanitized adoption report that contains no active configuration,
  private path, credential, transcript, raw log, host/user identity, or
  machine-specific configuration.
- Record the accepted program objective, architecture decisions, phase order,
  original V3-A mapping, deferred work, acceptance gates, and next issue.
- Explicitly dispose of the supplied deep-research report as a research input
  rather than a repository source of truth.

### Out Of Scope

- Editing the V2c-A adapter or V2c-B hook implementation.
- `auto-on-demand` mode or any hook-driven index refresh.
- Scheduler, daemon, controller service, database, graph runtime, vector
  database, background controller, or automatic promotion.
- Private operational data, raw large logs, credentials, secret values,
  transcripts, private paths, local databases, or unredacted machine config.
- Treating hook output, operational evidence, Obsidian projection, GitNexus
  data, or repository records as completion authority or protected
  authorization.
- Committing the pre-existing local `AGENTS.md` modification.
- Implementing the Operational Evidence V0 contracts.

## Loop Policy

- Entry skill: `loop-engineering`
- Classification: `bounded-delivery-objective`
- Default execution mode: `current-session`
- Concurrency: one
- Review closure round limit: two
- Desktop task or thread mutation: none
- External writes:
  - Issue #107 creation and local branch creation are authorized.
  - Machine-local notify-only adoption is authorized for this repository.
  - Hook trust remains an explicit user/runtime review action.
  - Commit, push, PR, merge, tag, and release require exact publication
    authority before execution.

## Definition Of Done

- README identifies V2c-B/v0.9.0 as the current released Loop Engineering
  baseline without weakening optional/no-backend behavior.
- v0.9.1 release notes describe only the alignment, live notify-only adoption
  evidence, and durable planning records delivered here.
- The active hook config validates and remains untracked and machine-local.
- No refresh path is configured or invoked.
- At least one live supported event is observed, or the precise runtime
  limitation is recorded without overstating coverage.
- Public adoption evidence is sanitized, bounded, and explicitly
  non-authoritative.
- Program documents make the next issue executable from a new conversation
  without relying on this chat.
- The research report has a durable retention/supersession decision.
- Relevant focused tests, repository validation, `git diff --check`, and a
  formal docs review gate pass with no unresolved MUST-FIX findings.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
./scripts/validate-repo.sh
git diff --check
```

Machine-local validation uses the shipped runner with an absolute local config
path. The path and active configuration must not appear in tracked artifacts.

## Human Gates

Stop before:

- trusting a hook definition without normal Codex review;
- any unexpected runtime mutation or private-data exposure;
- expanding from `notify-only` to `auto-on-demand`;
- changing public contract behavior rather than documentation;
- committing, pushing, opening or merging a PR, tagging, or publishing a
  release without exact authority for that action.
