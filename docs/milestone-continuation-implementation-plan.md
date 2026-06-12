# Milestone Continuation Implementation Plan

## Objective

Define the smallest safe implementation path for a new `milestone-continuation` workflow that can advance a bounded milestone, such as `MVP1`, across repeated invocations until the milestone is complete or a human gate is reached.

This plan is written on branch `codex/doc-only-milestone-continuation-plan` and is documentation-only. It does not implement the skill yet.

## Source Of Truth

Facts:

- `docs/milestone-continuation-requirements.md` defines the requested behavior and acceptance criteria.
- `skills/task-continuation/SKILL.md` already selects the next safe task from durable project context and prepares continuation prompts or task briefs.
- `skills/project-orchestrator/SKILL.md` already routes bounded work across implementation, review, continuation, handoff, or human gates.
- `skills/project-delivery/SKILL.md` already carries bounded delivery objectives through planning, implementation, verification, review, docs sync, and PR readiness or the next human gate.
- `skills/desktop-thread-delegation/SKILL.md` already handles Codex Desktop thread handoff when runtime tools exist and the maintainer explicitly authorizes the action.
- `docs/runtime-adapter-v2.md` defines Desktop thread-tool boundaries and prohibits private Desktop runtime state, unpublished endpoints, UI scraping, daemons, sidecars, and unapproved runtime adapters.
- `templates/orchestration/task-manifest.template.yaml` already exists and may be reusable for milestone task manifests.

Inference:

- `milestone-continuation` should be an upper-layer orchestration skill, not a replacement for existing delivery, continuation, or Desktop delegation skills.
- The first implementation should be docs/skill-contract heavy and should avoid any new scheduler, daemon, runtime adapter, or live Desktop thread-call wrapper.
- Scheduling cadence, such as every 5 minutes or every 10 minutes, should remain an invocation/runtime concern handled by Codex Desktop heartbeat or automation when available.

## Proposed Scope

Implement one small shared skill and supporting docs:

- Add `skills/milestone-continuation/SKILL.md`.
- Add `examples/milestone-continuation.md`.
- Update user-facing discovery docs so maintainers know when to use the new skill.
- Reuse existing task manifest templates unless a concrete gap is found.
- Add catalog and installer discovery only after confirming whether this implementation slice is allowed to touch non-Markdown metadata files.

The skill should remain shared runtime compatible. It may describe Desktop heartbeat or automation usage as runtime-specific scheduling, but it must not depend on Desktop-only behavior for its core milestone/task reasoning.

## Task Slices

### Slice 1: Skill Contract

Add `skills/milestone-continuation/SKILL.md`.

Required content:

- Runtime compatibility: `shared`.
- Purpose: continue a bounded milestone from durable repo context across repeated invocations.
- CLI fallback: current session, paste-ready prompt, task brief, or sequential execution path.
- Desktop note: heartbeat/automation may wake the thread; `desktop-thread-delegation` handles any authorized Desktop thread handoff.
- Workflow:
  - re-read repo instructions, milestone spec, task manifest, status docs, review evidence, templates, policies, and git state;
  - classify milestone and task state;
  - verify current task completion against DoD and verification commands;
  - continue current task or select the next smallest ready task;
  - route implementation/review/handoff through existing skills;
  - stop at human gates.
- Output contract:
  - milestone status;
  - current task status;
  - selected next task;
  - execution mode;
  - verification run or required;
  - files changed if any;
  - residual risk;
  - human gate if any.
- Stop conditions aligned with `docs/milestone-continuation-requirements.md`.

### Slice 2: Example

Add `examples/milestone-continuation.md`.

The example should show:

- manual invocation;
- scheduled Desktop heartbeat wording;
- a paste-ready prompt for `MVP1`;
- how the skill composes with `project-delivery`, `task-continuation`, and `desktop-thread-delegation`;
- a clear statement that the prompt can request a cadence, but runtime scheduling performs the wakeup;
- CLI fallback when no runtime scheduler exists.

### Slice 3: Discovery Docs

Update user-facing docs:

- `README.md`: add a short usage example near bounded milestone or task continuation sections.
- `docs/skill-selection-guide.md`: add when to choose `milestone-continuation` versus `project-delivery` and `task-continuation`.
- `docs/usage-model.md`: mention repeated milestone continuation as a good fit when durable milestone/task artifacts exist.
- `docs/roadmap.md`: record the accepted milestone-continuation work or backlog closure, if appropriate.

### Slice 4: Catalog And Installer Metadata

Update packaging metadata only if the maintainer agrees this is in scope for the implementation branch:

- `catalog.yaml`: add `skills/milestone-continuation` to the appropriate group, likely `codex-delivery-workflow` or `shared-review-gates` depending on dependency direction.
- `install.sh`: add the skill to the matching install group output.

Open decision:

- If the next branch must stay strictly Markdown/docs-only, defer `catalog.yaml` and `install.sh` to a separate metadata implementation slice.
- If the next branch is allowed to include repository packaging metadata, include these updates with the skill so installation remains coherent.

Recommended choice:

- Implement the skill, example, and docs first.
- Update `catalog.yaml` and `install.sh` in the same implementation PR only if the maintainer confirms non-Markdown metadata is allowed.

### Slice 5: Template Gap Check

Check whether existing templates are sufficient:

- `templates/orchestration/task-manifest.template.yaml`
- `templates/orchestration/task-continuation-report.template.md`
- `templates/orchestration/current-task-summary.template.md`
- `templates/orchestration/next-session-prompt.template.md`

Default decision:

- Do not add a new milestone template in the first implementation unless the skill or example clearly needs one.
- If a gap is found, add a small Markdown milestone spec template in a later slice.

## Definition Of Done

- `milestone-continuation` is documented as a shared skill that composes with existing workflows.
- The skill separates runtime scheduling cadence from per-wakeup behavior.
- The skill preserves existing human gates and Desktop runtime boundaries.
- The skill treats repo files as source of truth and chat summaries as context only.
- The example shows both manual and Desktop scheduled usage without claiming CLI can open Desktop threads.
- User-facing docs explain when to choose `milestone-continuation`.
- Catalog/installer state is either updated or explicitly deferred with rationale.
- Verification passes for documentation and repository hygiene.

## Risks

- Risk: the skill could blur the boundary between scheduling and task execution.
  Mitigation: make cadence an invocation/runtime parameter and keep the skill focused on per-wakeup behavior.

- Risk: the skill could duplicate `project-delivery` or `task-continuation`.
  Mitigation: define it as an upper-layer loop that routes to those existing skills.

- Risk: Desktop heartbeat or automation behavior could be described as shared capability.
  Mitigation: label scheduling and thread creation as runtime-specific, with CLI fallback.

- Risk: the first implementation could accidentally authorize external writes or Desktop thread actions.
  Mitigation: keep commit, push, PR, merge, deploy, platform mutation, destructive actions, and Desktop thread tools behind explicit human gates.

- Risk: packaging metadata updates may make the branch no longer docs-only.
  Mitigation: keep this plan branch docs-only and decide separately whether the implementation branch may touch metadata files.

## Human Gates

Stop for maintainer decision before:

- adding or changing runtime automation behavior;
- creating a scheduler, daemon, wrapper, MCP server, app-server client, or Desktop runtime adapter;
- calling `create_thread`, `fork_thread`, `send_message_to_thread`, `handoff_thread`, or other Desktop thread tools as part of implementation;
- touching `catalog.yaml` or `install.sh` if the active branch must remain strictly Markdown/docs-only;
- adding a new template instead of reusing existing templates;
- committing, pushing, opening a PR, merging, releasing, deploying, or posting platform comments.

## Verification Plan

For this documentation-only plan:

```bash
git diff --check
```

For the future implementation slice:

```bash
./scripts/validate-repo.sh
git diff --check
```

Additional checks if packaging metadata changes:

```bash
./install.sh list
```

If only Markdown skill/docs/examples are changed and no executable behavior changes, no Python unit tests are expected unless validation or review identifies a specific need.

## Open Questions

- Should `milestone-continuation` be installed with `codex-delivery-workflow`, `shared-review-gates`, or a new group?
- Should the first implementation include a new milestone spec template, or rely on existing task/project templates?
- Should the implementation branch be strictly Markdown/docs-only, or may it include `catalog.yaml` and `install.sh` packaging metadata?
- Should the Desktop heartbeat example stay in docs only, or should a later slice add an automation setup example using Codex Desktop runtime tools?

## Recommended Next Step

After maintainer approval, implement Slice 1 through Slice 3 in a small docs/skill slice. Defer Slice 4 unless packaging metadata is approved for the implementation branch.
