---
name: hermes-project-delivery
description: Hermes bounded delivery with verified capabilities and gates.
metadata:
  hermes:
    requires_toolsets: [terminal]
---

# Hermes project delivery

Runtime compatibility: Hermes CLI, limited baseline; see
`../../docs/guides/hermes-agent.md` relative to this skill directory. `shared`
Codex skills are not automatically Hermes-compatible.

## When to Use

Use for a bounded software objective on a verified Hermes runtime. Planning,
implementation, verification, review, docs sync and delivery remain separate
evidence stages. The skill is guidance, not a sandbox or authorization grant.

## Procedure

1. Read repo instructions, status/branch/upstream/remotes/diff and the requested
   DoD. Load `../../policies/human-gate-policy.md` and
   `../../policies/delivery-drift-control-policy.md` with native file/terminal
   reads. Resolve paths from this installed skill directory, never from cwd.
   Preserve existing user edits. Inspect target, identity and ownership before
   mutation; follow repo Issue/branch/worktree sequencing.
2. Discover the active Hermes tools and exact schemas. Check CLI version/help,
   backend, mounts, network, credential source and approval semantics. Do not
   translate Codex tool names, profiles, session IDs or config fields. Reject
   `--oneshot`, `--yolo`, approval off and automatic hook acceptance. Unknown
   permissions stop dependent operations. Supervised CLI does not itself prove
   containment; maintain exact authorization even inside a container.
3. Prepare a repo-owned plan from `../../templates/orchestration/implementation-plan.template.md`,
   with scope, disjoint ownership, DoD, verification and review risk. Implement
   the smallest slices; inspect diff and use the project's pinned interpreter
   when required. Load dependencies explicitly; do not install packages or MCP
   servers merely because a skill mentions them.
4. Use native delegation only after verifying the current schema, chosen
   model/provider/effort, authorized data destination, role quality, actual
   tool/OS constraints and result handling. Read
   `../../policies/multi-agent-integration-policy.md`. No role mapping or
   Codex TOML import is provided. With missing evidence keep a single writer;
   obtain independent review through a separately verified runtime. A prompt
   saying read-only does not enforce read-only terminal access.
5. On repeated correction failures, classify cause and re-evaluate assumptions,
   method and capability. After two unfinished rounds, re-ground against repo
   state and prepare a fresh bounded checkpoint if needed. Upgrade only to an
   already authorized, verified target. Authentication, environment, permissions
   and unknown tool outcomes need their own recovery, not model escalation or
   blind replay. Changed model/source cannot erase correction history.
6. Run risk-appropriate deterministic verification and independent review via
   `hermes-review-gate`. Keep raw evidence under the repo's ignored review root,
   otherwise `.work/review/`. Verify evidence bytes and final diff; worker
   summaries, runtime memory and passing tests cannot prove completion.
7. Sync requirements/design/engineering docs and roadmap with actual state.
   If another branch merges first, update this task's isolated checkout and
   recheck semantic dependencies, status and version even without Git conflicts.
8. Continue already-authorized commit/push/PR only after the formal gate. For
   merge, use `hermes-review-gate` exact-head mode and current platform readback.
   Release/deploy/destructive actions retain their own exact authority. If a
   required capability is missing, finish independent work and state the gap.

## Pitfalls

Skill load, source inspection and synthetic tests cannot establish model,
delegation, isolation or lifecycle qualification. Never read or import Codex
credentials automatically, activate API fallback, or send secrets/private
runtime state to a model or repository. Terminal environment and provider
credentials require separate verification; credentials used by the provider
must not become tool-visible test content.

## Verification

Read back each artifact and run the acceptance commands, inspect the integrated
diff, record findings/dispositions and the exact gate. Report source revision,
changed files, checks run/skipped, actual runtime surface, remaining acceptance
gaps and next real decision. Preserve the objective until completed or blocked
by a concrete authority/environment/risk decision.
