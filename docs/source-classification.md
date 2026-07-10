# Source Classification

This file records how the public workflow set was derived and which layer owns
each contract.

## Source Priority

1. The shared review layer is canonical for reusable review gates and policies.
2. Non-duplicate CLI/shared pack content supplies general planning, delivery,
   implementation, documentation, and review workflows.
3. Desktop pack content supplies only user-owned task/thread/worktree,
   scheduling, and Desktop integration adapters.
4. Accepted repository-native extensions supply Loop Engineering and current
   runtime capability guidance.

Shared subagent delegation belongs to the shared layer. It is not classified as
Desktop-only merely because a Desktop UI can display or coordinate it.

## KEEP_SHARED_CANONICAL

Public outputs:

- closure triage and task continuation;
- code, documentation, and merge readiness gates;
- review artifact cleanup;
- human-gate, model-selection, review, security, delegation, and reusable
  workflow policies;
- shared project/task/review orchestration templates.

## KEEP_CLI_OR_SHARED

Public outputs:

- planning, project delivery, project orchestration, implementation slices,
  and documentation updates;
- routine/deep code review, documentation review, and merge review;
- shared subagent routing with disjoint ownership and main-agent integration.

## KEEP_DESKTOP_ONLY

Public outputs:

- Desktop project-delivery adapter;
- Desktop task/thread delegation adapter;
- Desktop spec/plan, implementation, and PR/merge gates.

These skills may control user-owned Desktop tasks, threads, worktrees, or
schedules when a documented callable and required authority exist. Their
workflow semantics and completion evidence remain shared.

## KEEP_REPO_NATIVE_EXTENSION

Public outputs:

- Loop Engineering skill, executable state/event core, structured ledger CLI,
  eval suite, workflow, templates, and public guidance;
- native Goal, shared subagent, scheduler, hook, Desktop thread, and sequential
  fallback capability mapping;
- runtime compatibility and Desktop adapter-boundary guidance;
- maintained Loop Engineering and Desktop handoff examples.

The `desktop_runtime_*` scripts and the Desktop runtime wrapper V1 plan remain
historical compatibility evidence only. They are not an active runtime path,
must not be imported or executed by Loop Engineering, and their old response
shapes cannot override the current callable schema.

## Boundary

- Desktop task/thread actions are runtime actions, not CLI guarantees.
- CLI fallback uses the current session, shared subagents when supported,
  sequential execution, a task brief, or a continuation prompt.
- Runtime evidence may use documented tools, official/public contract metadata,
  repository files, and ordinary git or shell inspection.
- It must not depend on private Desktop databases, logs, sessions, auth files,
  caches, unpublished endpoints, UI scraping, daemons, or sidecars.
- Runtime contract evidence records action name, version or `version
  unavailable`, capability source, minimal request/response fields,
  `last_verified`, target identity, and adapter mapping.
- Runtime evidence never replaces exact action authority, call-site target and
  response validation, or repository completion evidence.

## DUPLICATE_SHARED_COPY

Pack-local synchronized copies of canonical shared files are not independent
public sources. The public repository keeps one shared output for each skill,
policy, workflow, and template to prevent divergence.

## Installer And Maintenance Scripts

The public installer and catalog are Codex-only rewrites. Repository validation
checks public catalog paths, release/version consistency, runtime labels,
structured Loop Engineering state, executable eval thresholds, installer
safety, and hygiene. Private sync scripts and non-Codex installer targets are
excluded.

## RENAME / REWRITE / EXCLUDE

- Private abbreviations and underscore names were renamed to public kebab-case
  names.
- Kept material was rewritten to remove private paths, secrets, and unsupported
  runtime assumptions.
- Platform-specific MR adapters, private knowledge/vault content, compatibility
  aliases, standalone pass-B reviewers, and external scheduler examples are
  excluded.
