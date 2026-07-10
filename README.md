# codex-dev-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Runtime: Codex CLI + Desktop](https://img.shields.io/badge/runtime-Codex%20CLI%20%2B%20Desktop-blue)](#runtime-compatibility)
[![Repo hygiene](https://img.shields.io/badge/hygiene-validate--repo.sh-informational)](#verification)

`codex-dev-skills` is an OSS maintenance workflow pack for OpenAI Codex CLI and Codex Desktop.

It helps maintainers move beyond one-off prompts. Teams can combine reusable
skills, an executable loop contract, native goals, shared subagents, formal
gates, and thin runtime adapters to run bounded implementation, review,
handoff, and release-readiness workflows consistently.

The current development milestone is Loop Engineering V1: one production
routing and transition core, structured ledger validation, deterministic
workflow evals, native goal and shared subagent semantics, and Desktop-specific
task/thread/scheduling adapters. The older Desktop wrapper helper chain remains
legacy compatibility evidence and is not the active native runtime path.

This is not a general prompt collection. It is a curated set of public, reusable workflow contracts for open source and team repositories.

## Who It Is For

- Open source maintainers who want Codex to help with routine repo maintenance.
- Teams using Codex CLI or Codex Desktop for implementation, review, and merge readiness.
- Contributors who need explicit human gates before destructive actions, pushes, releases, or merges.
- Early adopters who want reusable skills instead of one-off prompts.

## Quick Start

Inspect available install groups:

```bash
./install.sh list
```

Install CLI-compatible review workflows to get the normal `code-review` and `docs-review` entry points:

```bash
./install.sh install codex-review-workflow
```

Install CLI-compatible loop, implementation, and delivery workflows when you want Codex to keep a bounded objective moving through planning, implementation, verification, review, documentation sync, continuation, and formal gates:

```bash
./install.sh install codex-delivery-workflow
```

`codex-review-workflow` and `codex-delivery-workflow` install their shared review gate dependencies automatically. Install `shared-review-gates` directly only when you want the formal gate adapters and orchestration templates without the review primitives.

Use the installed skills in Codex by name, for example:

```text
Use loop-engineering for issue #123 and keep the bounded objective moving until PR readiness or the next human gate.
Use implementation-slice to make this focused parser fix and run the targeted tests.
Use code-review on the current working tree.
Use docs-review for the docs-only changes in this branch.
Use milestone-continuation for MVP1.
Use merge-review for main..HEAD.
Use merge-review-deep for the release-sensitive main..HEAD diff.
Use merge-readiness-gate before PR handoff for main..HEAD. Treat the result as gate evidence only; do not commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes unless explicitly authorized.
```

For Codex Desktop delegated delivery, install the Desktop group only when that workflow is intentional:

```bash
./install.sh install desktop-delivery-workflow
```

## How Projects Use These Skills

These skills work best when the target repository keeps durable project context in files that Codex can read before editing: repo-level `AGENTS.md`, project specs, implementation plans, review templates, and policy files.

The workflows are not limited to single task-id execution. When scope is clear, they can advance a bounded milestone slice, such as one MVP capability area, through discovery, planning, implementation, verification, review, documentation sync, and PR readiness.

Global Codex guidance adds useful baseline safety, while repo-level files define the project-specific source of truth. See `docs/usage-model.md` for the recommended project artifacts, delivery scope, and instruction layering model.

For adoption examples that pair well with this repository:

- [examples/global-codex-profile.md](examples/global-codex-profile.md) shows a reusable user-level baseline for `~/.codex/AGENTS.md`.
- [examples/project-agents-overlay.md](examples/project-agents-overlay.md) shows how a repository can layer project-specific rules without weakening global safeguards.
- [examples/project-workflow-overlay.md](examples/project-workflow-overlay.md) shows a compact project workflow overlay for delegated delivery, review closure, PR readiness, and release/tag gates.

## Usage Examples

These examples are written as prompts you can give to Codex after installing the relevant skill group.

### Focused Implementation

Use `implementation-slice` when the desired change is clear and should stay small:

```text
Use implementation-slice to add validation for empty config values.
Read the existing parser tests first, keep the change scoped, run the smallest relevant test command, and do not commit.
```

Codex should inspect repo instructions and current git state, edit only the needed files, run focused verification, inspect the diff, and report residual risk.

### Choosing An Entry Point

For a compact first-time decision guide, see [docs/skill-selection-guide.md](docs/skill-selection-guide.md).
It also explains when to choose routine review versus deep review for code, docs, and merge readiness work.

Use the smallest entry point that matches the request:

- `implementation-slice` for one clear coding task.
- `planning` when the next action or DoD needs to be defined before editing.
- `code-review` for ordinary read-only review of code or mixed diffs.
- `loop-engineering` when Codex should own the repeated bootstrap, route, act, verify, review, continue, handoff, or stop cycle for a clear bounded objective.
- `project-orchestrator` when Codex should classify the task, choose the next safe action, or decide whether to continue, hand off, review, or stop.
- `project-delivery` when the objective is larger than one task but still bounded.
- `milestone-continuation` when a bounded milestone should be checked and advanced across repeated invocations until complete or blocked by a human gate.

`loop-engineering` is a thin entrypoint over the existing phase skills. It should classify the current state, route to the smallest suitable workflow, verify evidence, and stop at human gates. It does not replace focused implementation, review primitives, formal gates, milestone continuation, task continuation, shared subagents, or Desktop user-owned task/thread/worktree controls.

If `project-orchestrator` receives a single clear implementation task, it should route to `implementation-slice` semantics and avoid unnecessary project-level planning.

For automated review closure, let `project-orchestrator` or `project-delivery` compose the primitive shared workflows dynamically. A user or repo policy may set the maximum number of review/fix rounds; the default is 2.

### Routine Code Review

Use `code-review` when you want read-only feedback on a working tree, branch, or patch. This is the normal user-facing entry point for code review:

```text
Use code-review on the current working tree.
Prioritize correctness bugs, regressions, missing tests, and contract risks. Stay read-only.
```

Expected output starts with findings, then questions and re-runnable verification commands.

Use `code-review-gate` only when a workflow needs a formal gate before commit readiness, PR readiness, or merge readiness.
The gate is a thin adapter: it routes routine diffs to `code-review`, escalates high-risk diffs to `code-review-deep`, records evidence, and blocks on unresolved MUST-FIX findings.

### Routine Documentation Review

Use `docs-review` when you want read-only feedback on docs-only or docs-dominant changes. This is the normal user-facing entry point for documentation review:

```text
Use docs-review on the current working tree.
Check accuracy, stale names or links, unsupported claims, and confusing structure. Stay read-only.
```

Use `docs-review-gate` only when a workflow needs a formal documentation gate before commit readiness, PR readiness, or merge readiness.
The gate is a thin adapter: it runs `docs-review`, records evidence, checks for private paths, local runtime state, unsupported claims, and stale instructions, then blocks on unresolved MUST-FIX findings.

### Orchestrated Review Closure

Use `project-orchestrator` when Codex should implement, review, fix blockers, and re-review until it reaches a human gate:

```text
Use project-orchestrator to implement the requested docs validation improvement.
Run at most two review/fix rounds. Stop before commit, push, PR creation, release, platform comments, review submissions, or any external write.
```

The orchestrator uses the smallest shared primitives that fit the current state: `implementation-slice`, `docs-update`, `code-review`, `code-review-deep`, `docs-review`, and merge-readiness workflows when applicable. It uses `code-review-gate` or `docs-review-gate` only for formal commit readiness, PR readiness, merge readiness, or repo-policy blocking decisions. This keeps the same closure model usable in Codex CLI and Codex Desktop.

### Loop Engineering

Use `loop-engineering` when the objective is clear and Codex should keep selecting the next safe workflow until the objective is complete or a human gate is reached:

```text
Use loop-engineering for issue #123.
Read the issue, repo instructions, implementation plan, task manifest, review evidence, and current git state before editing.
Continue through planning, implementation, verification, review, docs sync, continuation, and PR readiness while the objective and DoD remain clear.
Stop before destructive actions, external writes, commit, push, PR creation, merge, release, deploy, platform comments, review submissions, material risk, or unclear source of truth unless I explicitly authorize the exact action.
```

The loop entrypoint repeatedly bootstraps from durable repository files,
executes the production route and transition contract, verifies evidence, and
decides whether to continue, prepare a handoff, stop, or complete. When the user
explicitly requests a native goal, Goal mode controls progress without widening
permissions or replacing repository completion evidence. Independent bounded
packets may use shared subagents in current Desktop, CLI, and IDE runtimes. See
[docs/loop-engineering.md](docs/loop-engineering.md),
[workflows/loop-engineering-workflow.md](workflows/loop-engineering-workflow.md),
and [native runtime capabilities](docs/native-runtime-capabilities.md).

The active skill invokes `loopctl.py decide` with a structured decision input
and an explicit trusted `--protected-history-sha256 <verified-digest-or-none>`;
the prose route table explains the result but does not replace the executable
routing function.

When a loop needs durable memory across repeated invocations, workers, worktrees,
or handoffs, add a repo-owned loop ledger:

```text
Use loop-engineering for issue #123.
If the repo does not already have loop state, create docs/loops/issue-123/ from the loop spec, loop-state-ledger, task manifest, current-task-summary, iteration-report, and task-claim/lease templates.
Treat stable task definitions, validated events, the materialized ledger,
fenced claims, and verification/review evidence according to their documented
authority boundaries.
External memory may be used only as cache or coordination unless this repo explicitly defines a stronger reviewed authority model.
```

See [docs/loop-state-ledger.md](docs/loop-state-ledger.md) for the repo-owned loop state contract.

### Bounded Milestone Slice

Use `project-delivery` when the objective is larger than a single task but still bounded:

```text
Use project-delivery to advance the MVP1 import-validation scope to PR readiness.
Read the repo plan and acceptance criteria first, split the work into safe slices, update docs if behavior changes, run review primitives and required formal gates, and stop before commit, push, PR creation, release, platform comments, or review submissions.
```

This pattern is useful when a maintainer wants Codex to carry a small capability area forward without granting authority to publish or merge.

Use `milestone-continuation` when a bounded milestone should keep advancing across repeated invocations:

```text
Use milestone-continuation for MVP1.
Every time this thread wakes up, read the milestone spec, task manifest, status docs, review evidence, and current git state.
If the current task is incomplete, continue it with the smallest safe action.
If it is complete, choose the next smallest ready task.
Continue until MVP1 is complete or a human gate is reached.
```

The skill defines what to do after each invocation. Runtime cadence, such as a Codex Desktop heartbeat every 5 or 10 minutes, is configured by the active runtime and is not hardcoded in the skill.

### Task Continuation

Use `task-continuation` when a larger bounded task needs the next safe unit of work and a prompt, task brief, continuation prompt, or sequential execution path:

```text
Use task-continuation to choose the next smallest safe task from the repo plan and status files.
Prepare a continuation prompt or task brief if continuation should move to another session or worker, but do not claim that a shared skill can open the session itself.
```

The skill prepares continuation artifacts from durable repository context.
Shared subagents can handle bounded packets when available; opening a separate
user-owned Desktop task or thread remains a runtime-specific control-plane
action.

### Merge Readiness

Use `merge-review` when you want the normal base-to-head merge quality and DoD review:

```text
Use merge-review for main..HEAD.
Check scope alignment, tests, docs, unresolved review findings, and residual risk. Stay read-only.
```

The result is review evidence. It does not grant authority to commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes.

Use `merge-review-deep` when the diff is high-risk, release-sensitive, or policy-required:

```text
Use merge-review-deep for main..HEAD.
Re-check closure evidence, rollback path, security/privacy, migration safety, and hidden regression risk. Stay read-only.
```

The deep result is still review evidence, not merge authorization.

Use `merge-readiness-gate` only when a workflow needs a formal branch readiness gate before PR handoff, merge readiness, or final human approval:

```text
Use merge-readiness-gate for main..HEAD.
Check the plan, diff, tests, and review evidence. Report READY, BLOCKED, or NEEDS HUMAN DECISION. Do not commit, push, merge, deploy, post platform comments, submit reviews, or perform other external writes unless explicitly authorized.
```

The gate is a thin adapter and evidence-and-decision layer: it summarizes verification, review evidence, blocking decisions, residual risk, and the human approval boundary. It is not another merge review primitive and does not automatically authorize commit, push, merge, deploy, platform comments, review submissions, or other external writes. Before any authorized merge or platform-side mutation, confirm the head SHA has not changed and no blockers remain.

### Codex Desktop Delegated Delivery

Use `desktop-project-delivery` when shared project delivery also needs Desktop
task, thread, worktree, or scheduling controls. Ordinary subagent delegation is
shared and does not require this Desktop adapter:

```text
Use desktop-project-delivery to prepare this feature for PR readiness.
Coordinate implementation and review, integrate the output, run verification, and stop for product ambiguity, destructive actions, external writes, or final merge approval.
```

CLI fallback: use `project-delivery`, `project-orchestrator`, prompts, task briefs, continuation prompts, or a sequential execution path; run review primitives after the fallback produces changed files or evidence; and use formal gates only at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates. See [docs/runtime-compatibility.md](docs/runtime-compatibility.md) for the Desktop-to-CLI fallback mapping.

Use `desktop-thread-delegation` only after shared orchestration has selected a
bounded handoff and the user explicitly wants a separate Desktop task or
thread:

```text
Use desktop-thread-delegation for the bounded task already selected by shared orchestration.
Choose only whether that selected task continues here or moves to a new Desktop task/thread/worktree.
If a new Desktop task is appropriate, prepare the handoff prompt and ask before opening it.
If thread creation is unavailable, return the prompt for me to paste manually.
Keep review, commit, PR, merge, platform comments, and other external writes behind explicit authorization.
```

The main thread remains responsible for integrating returned work, checking the diff, running verification, and enforcing review or merge gates.

The active runtime contract is [docs/native-runtime-capabilities.md](docs/native-runtime-capabilities.md).
Use only a callable exposed by the current runtime, validate its target and
response at the call site, and preserve the same CLI fallback. The
`desktop_runtime_*` scripts and [historical V1 plan](docs/desktop-runtime-wrapper-v1-plan.md)
remain regression and migration evidence only; active Loop Engineering skills
must not import, execute, or recommend them.

## Runtime Compatibility

| Label | Meaning |
| --- | --- |
| `shared` | Works in Codex CLI and Codex Desktop with ordinary repository files and shell/git inspection. |
| `cli` | Designed primarily for Codex CLI. Desktop may use the same steps manually or through an equivalent thread. |
| `desktop` | Requires Desktop user-owned task, thread, worktree, UI, or scheduling control. |
| `plugin-dependent` | Requires an installed plugin, connector, or platform tool. The skill must name the dependency. |

## Skills

| Skill | Runtime | Purpose |
| --- | --- | --- |
| `loop-engineering` | shared | Explicit loop entrypoint for clear bounded objectives; routes through planning, implementation, verification, review, continuation, handoff, and gates until complete or stopped. |
| `planning` | shared | Produce scoped implementation plans with assumptions, risks, DoD, and verification. |
| `milestone-continuation` | shared | Continue a bounded milestone across repeated invocations by checking task completion, choosing the next ready task, and stopping at human gates. |
| `project-delivery` | shared | Carry a bounded delivery objective through discovery, plan, implementation, review, docs sync, and PR readiness or the next human gate. |
| `project-orchestrator` | shared | Route bounded work across planning, implementation, review, continuation, handoff, or human gates. |
| `implementation-slice` | shared | Implement a bounded change after read-only inspection, then verify and inspect the diff. |
| `docs-update` | shared | Update user or project docs from code, specs, and verified behavior. |
| `code-review` | shared | Normal user-facing entry point for routine read-only review of code or mixed diffs. |
| `code-review-deep` | shared | Higher-scrutiny review for security, packaging, data, migration, or cross-module risk. |
| `docs-review` | shared | Normal user-facing entry point for read-only review of docs-only or docs-dominant changes. |
| `merge-review` | shared | Normal user-facing entry point for base-to-head merge quality and DoD review evidence. |
| `merge-review-deep` | shared | Higher-scrutiny merge review evidence for high-risk, release-sensitive, or policy-required changes. |
| `code-review-gate` | shared | Thin formal gate adapter that routes to `code-review` or `code-review-deep` before commit, PR, or merge readiness. |
| `docs-review-gate` | shared | Thin formal gate adapter around `docs-review` before commit, PR, or merge readiness. |
| `merge-readiness-gate` | shared | Thin formal branch readiness evidence-and-decision layer before PR handoff, merge readiness, or final human approval. |
| `review-artifact-cleanup` | shared | Dry-run first cleanup workflow for review artifacts. |
| `closure-triage` | shared | Select the next smallest safe packet from repo policy, project overlays, and current state. |
| `task-continuation` | shared | Select the next safe task and prepare a continuation prompt or task brief from durable project context. |
| `desktop-project-delivery` | desktop | Thin Desktop UX adapter over shared project delivery. |
| `desktop-thread-delegation` | desktop | Control a user-authorized Desktop task/thread/worktree handoff selected by shared orchestration. |
| `desktop-spec-plan-gate` | desktop | Desktop gate for spec, plan, and DoD drafts. |
| `desktop-implementation-gate` | desktop | Desktop formal integration gate for worker outputs before commit readiness. |
| `desktop-pr-merge-gate` | desktop | Desktop PR and merge readiness gate that summarizes evidence without publishing or merging. |

## Workflows

- `workflows/loop-engineering-workflow.md`
- `workflows/implementation-workflow.md`
- `workflows/review-workflow.md`
- `workflows/merge-readiness-workflow.md`
- `workflows/desktop-delivery-workflow.md`

Shared orchestration templates include loop engineering specs, repo-owned loop state ledgers, loop iteration reports, loop handoff prompts, task claim/lease templates, task briefs, task manifests, next-session prompt templates, current task summaries, project specs, implementation plans, closure triage overlays, task continuation reports, integration review reports, and orchestrator gate reports.

## Examples

- [Basic implementation](examples/basic-implementation.md)
- [Code review](examples/code-review.md)
- [Docs review](examples/docs-review.md)
- [Loop engineering](examples/loop-engineering.md)
- [Orchestrated review closure](examples/orchestrated-review-closure.md)
- [Multi-step maintenance](examples/multi-step-maintenance.md)
- [Milestone continuation](examples/milestone-continuation.md)
- [Task continuation](examples/task-continuation.md)
- [Desktop thread delegation](examples/desktop-thread-delegation.md)
- [Runtime adapter boundary](examples/runtime-adapter-boundary.md)
- [Language verification](examples/language-verification.md)
- [GitHub workflow guidance](examples/github-workflow-guidance.md)
- [Merge review and readiness](examples/merge-review.md)
- [Desktop project delivery](examples/desktop-project-delivery.md)

See `docs/roadmap.md` for the near-term public roadmap, `docs/release-notes-v0.4.0.md` for the current v0.4.0 release notes, and `docs/release-notes-v0.1.0.md` for the historical v0.1.0 release notes.

## Installation

Use the Codex-only installer:

```bash
./install.sh list
./install.sh install shared-review-gates
./install.sh install codex-review-workflow
./install.sh install codex-delivery-workflow
```

`./install.sh install --all` installs every group, including Desktop-only workflows. Use it only when you want the Desktop group installed too.

For practical installer troubleshooting across install, diff, update, and uninstall flows, see [docs/troubleshooting.md](docs/troubleshooting.md).

Install only shared review gates:

```bash
./install.sh install shared-review-gates
```

Install CLI-compatible review workflows:

```bash
./install.sh install codex-review-workflow
```

Install CLI-compatible loop and delivery workflows:

```bash
./install.sh install codex-delivery-workflow
```

The installed Loop Engineering YAML CLI has one explicit Python dependency.
Install it into the Python environment that will run `loopctl.py`:

```bash
python3 -m pip install -r ~/.codex/skills/loop-engineering/requirements.txt
```

When `CODEX_DEV_SKILLS_TARGET=agents` is used, replace `~/.codex/skills` with
`~/.agents/skills`. The installer reports this prerequisite but does not
silently modify the user's Python environment. `loopctl.py --help` remains
available before the dependency is installed; YAML commands fail closed with
the same installation instruction.

Install Codex Desktop delivery workflows:

```bash
./install.sh install desktop-delivery-workflow
```

Check installed state and local differences:

```bash
./install.sh status
./install.sh diff shared-review-gates
./install.sh diff --all
```

`./install.sh diff --all` checks every group, including Desktop-only workflows.

Update installed files from this repository:

```bash
./install.sh update shared-review-gates
./install.sh update codex-review-workflow
./install.sh update codex-delivery-workflow
```

`./install.sh update --all` updates every group, including Desktop-only workflows. Use it only when that is intentional.

Uninstall is destructive because it removes installed Codex skills and templates for the selected group. It requires explicit confirmation:

```bash
./install.sh uninstall shared-review-gates --yes
```

Installer scope:

- Codex skills are installed to `~/.codex/skills/<skill>/` by default to preserve existing installations.
- To opt in to the current Codex user-skill discovery location, run installer commands with `CODEX_DEV_SKILLS_TARGET=agents`; this installs skills to `~/.agents/skills/<skill>/`.
- Codex templates are installed to `~/.codex/templates/...`.
- Custom `CODEX_SKILLS_DIR` or `CODEX_TEMPLATES_DIR` overrides require `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`.
- The installer refuses symlink target roots and symlink target paths before install, update, diff, or uninstall.
- Installer state is stored under `~/.local/state/codex-dev-skills` unless `XDG_STATE_HOME` changes it.
- State records only non-sensitive metadata such as repository name, version, action, group, and timestamp.
- The installer never overwrites `~/.codex/AGENTS.md`.

Use only one skill installation target for this pack in a given Codex profile. Installing the same skill names into both `~/.codex/skills` and `~/.agents/skills`, or later through a plugin package, can make duplicate skills appear in selectors.

Plugin packaging is intentionally not added by the local installer. If this pack later ships a `.codex-plugin/plugin.json` and repo marketplace entry, treat that as a separate distribution path and avoid installing the same skill names through both the plugin and the filesystem installer.

## Verification

Run the repository hygiene check before proposing a release or PR:

```bash
python3 --version
python3 -m pip install -r requirements.txt
./scripts/validate-repo.sh
python3 scripts/eval-loop-engineering.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

This validates catalog/release consistency, required skill metadata, runtime
labels, symlink safety, structured loop YAML, event/transition behavior,
workflow eval thresholds, and public hygiene checks. PyYAML is the only Python
runtime dependency and is required by the structured ledger commands.
The repository pins Python 3.12.9 with `.python-version`; confirm the active
runtime before installing dependencies.

For tag, release notes, and PR readiness checks, see [docs/release-readiness.md](docs/release-readiness.md).

## Included Scope

This repository includes public software development workflows for:

- planning and implementation
- loop engineering for bounded objectives
- docs updates and docs review
- code review and deep code review
- orchestrated review closure and formal review gates
- merge readiness gates
- delegated delivery
- Codex Desktop orchestration
- shared CLI/Desktop policies and templates

## Excluded Scope

This repository intentionally does not include:

- legacy non-Codex workflows
- presentation or PPTX workflows
- unverified frontend UI workflow packs
- knowledge, Obsidian, or vault capture workflows
- private runtime state, local application state, logs, local databases, machine-specific config, credentials, or private paths

## Contribution Guidelines

Contributions should keep the repository public, runtime-compatible, and low-surprise:

- keep skill names clear to external users
- mark runtime compatibility in every skill and README table
- keep review mode read-only unless the user explicitly asks to fix
- avoid private paths, local runtime files, credentials, and machine-specific assumptions
- separate facts from inference
- include verification steps for workflow changes

## Safety And Privacy

Never add credentials, private keys, local runtime files, logs, local databases, app state, or machine-specific config. When a workflow discusses sensitive data, keep examples generic and never include real values.
