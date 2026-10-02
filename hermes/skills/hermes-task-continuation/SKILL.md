---
name: hermes-task-continuation
description: Resume bounded repo work from verified durable checkpoints.
metadata:
  hermes:
    requires_toolsets: [terminal]
---

# Hermes task continuation

Runtime compatibility: Hermes CLI, limited manual continuation. Automated
session resume/fork, cron, gateway and Desktop control are not provided.

## When to Use

For continuing one authorized repository objective after interruption or in a
new supervised Hermes session.

## Procedure

1. Read `../../policies/delivery-drift-control-policy.md` and
   `../../policies/human-gate-policy.md`. Verify repo/worktree/branch/head,
   uncommitted content, instructions, ownership and remaining DoD. Runtime
   memory, context compression and session titles are advisory only.
2. Read durable plan, current status, findings and Git-external evidence.
   Reuse evidence only after checking source/diff, scope, assumptions, policy,
   environment and stage. Missing references require rebuilding the affected
   evidence, not treating a summary as proof.
3. Save branch/head/base, dirty diff identity, phase, exact owned paths,
   verification, findings/dispositions, pending gates, evidence paths and next
   bounded action using `../../templates/orchestration/current-task-summary.template.md`
   and `../../templates/hermes/next-session-prompt.template.md`.
   Separate durable source from private runtime state; never export raw
   session DB, credentials, tool logs or personal config into Git.
4. Continue in the current session or manually open a new supervised session
   at the verified cwd and load `hermes-project-delivery`. Maintain one writer.
   Native resume requires separately verified exact session identity/history,
   effective cwd, model, tools and permissions; do not use latest/title as
   authoritative identity. No automatic lifecycle dispatch is implemented.
5. On base drift preserve other roadmap items and reconsider dependency,
   version and acceptance claims. Repeat affected verification and complete
   exact-head Merge Review for a changed request head. Continue already
   authorized work; stop only for a concrete unresolved decision or required
   capability gap. A new session does not erase correction lineage.

## Pitfalls

Session restoration is not repository success. No scheduler or Goal-mode
equivalence follows from this manual adapter. Do not assume a resumed session
restores the same cwd or permission boundary without readback.

## Verification

Report current source/worktree identity, accepted checkpoint evidence,
remaining objective, next action, checks to refresh and any real decision.
