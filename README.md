# codex-dev-skills

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Runtime: Codex CLI + Desktop](https://img.shields.io/badge/runtime-Codex%20CLI%20%2B%20Desktop-blue)](#runtime-compatibility)
[![Repo hygiene](https://img.shields.io/badge/hygiene-validate--repo.sh-informational)](#verification)

`codex-dev-skills` is an OSS maintenance workflow pack for OpenAI Codex CLI and Codex Desktop.

It helps maintainers delegate repeatable software development work to Codex with clear read-before-write behavior, scoped implementation, documentation updates, code review, orchestrated review closure, delivery gates, and merge readiness checks.

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

Install CLI-compatible implementation and delivery workflows when you want Codex to plan, implement, and route formal gates:

```bash
./install.sh install codex-delivery-workflow
```

`codex-review-workflow` and `codex-delivery-workflow` install their shared review gate dependencies automatically. Install `shared-review-gates` directly only when you want the formal gate adapters and orchestration templates without the review primitives.

Use the installed skills in Codex by name, for example:

```text
Use implementation-slice to make this focused parser fix and run the targeted tests.
Use code-review on the current working tree.
Use docs-review for the docs-only changes in this branch.
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

Global Codex rules add useful baseline safety, while repo-level files define the project-specific source of truth. See `docs/usage-model.md` for the recommended project artifacts, delivery scope, and global-rule layering model.

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
- `project-orchestrator` when Codex should classify the task, choose the next safe action, or decide whether to continue, hand off, review, or stop.
- `project-delivery` when the objective is larger than one task but still bounded.

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

### Bounded Milestone Slice

Use `project-delivery` when the objective is larger than a single task but still bounded:

```text
Use project-delivery to advance the MVP1 import-validation scope to PR readiness.
Read the repo plan and acceptance criteria first, split the work into safe slices, update docs if behavior changes, run review primitives and required formal gates, and stop before commit, push, PR creation, release, platform comments, or review submissions.
```

This pattern is useful when a maintainer wants Codex to carry a small capability area forward without granting authority to publish or merge.

### Task Continuation

Use `task-continuation` when a larger bounded task needs the next safe unit of work and a prompt, task brief, continuation prompt, or sequential execution path:

```text
Use task-continuation to choose the next smallest safe task from the repo plan and status files.
Prepare a continuation prompt or task brief if continuation should move to another session or worker, but do not claim that a shared skill can open the session itself.
```

The skill prepares continuation artifacts from durable repository context. Actually opening a new Codex conversation is runtime-specific and requires Desktop worker delegation, a CLI runner, MCP tool, plugin, or equivalent orchestrator.

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

Use `desktop-project-delivery` when working in Codex Desktop and delegating a bounded objective:

```text
Use desktop-project-delivery to prepare this feature for PR readiness.
Coordinate implementation and review, integrate the output, run verification, and stop for product ambiguity, destructive actions, external writes, or final merge approval.
```

CLI fallback: use `project-delivery`, `project-orchestrator`, prompts, task briefs, continuation prompts, or a sequential execution path; run review primitives after the fallback produces changed files or evidence; and use formal gates only at commit readiness, PR readiness, merge readiness, or explicit repo-policy gates. See [docs/runtime-compatibility.md](docs/runtime-compatibility.md) for the Desktop-to-CLI fallback mapping.

Use `desktop-thread-delegation` when Codex Desktop should choose the next safe task and decide whether to continue in the current thread or hand off to a new thread:

```text
Use desktop-thread-delegation to choose the next safe task from the current repo state.
If the task is suitable for this thread and workflow rules allow it, continue here.
If the task is better for a new Desktop thread, prepare the handoff prompt and ask before opening it.
If thread creation is unavailable, return the prompt for me to paste manually.
Keep review, commit, PR, merge, platform comments, and other external writes behind explicit authorization.
```

The main thread remains responsible for integrating returned work, checking the diff, running verification, and enforcing review or merge gates.

For the boundary of a possible future runtime-call adapter, see [docs/runtime-adapter-v2.md](docs/runtime-adapter-v2.md). That document defines allowed sources, prohibited Desktop runtime state, safety gates, runtime API/tool contract version tracking, CLI fallback behavior, and stop conditions without adding a runtime-call adapter or Desktop runtime integration.
When `desktop-thread-delegation` prepares to use a Desktop thread tool such as `create_thread`, `fork_thread`, or `send_message_to_thread`, it must record the same contract/version tracking fields before the runtime action.
For the current Desktop runtime wrapper V1 helpers and CLI usage examples, see [docs/desktop-runtime-wrapper-v1-plan.md](docs/desktop-runtime-wrapper-v1-plan.md). The capability discovery helper normalizes caller-supplied documented metadata only, the contract comparison helper re-checks old wrapper contract evidence against newer normalized capability evidence before runtime/schema changes are trusted, and the planner can accept normalized output as `capability_evidence` to produce dry-run, fallback, or stopped evidence. The `create_thread` preflight helper checks whether create-thread readiness evidence is complete before a future separately approved runtime call, and the create-thread authorization/evidence gate checks the final caller-supplied envelope before a human considers approving one separate implementation slice. The create-thread executor boundary proposal helper accepts ready authorization gate evidence and defines the single documented `create_thread` call-site contract a future executor would have to satisfy. The create-thread executor shell helper accepts ready boundary proposal evidence and validates the final implementation surface only, including a non-executed callable descriptor or injected-adapter placeholder, target re-check, authorization-intent re-check, permission/auth failure handling, response validation, returned thread id/status validation, and the separate human approval boundary. The create-thread documented callable executor helper accepts ready shell evidence, rechecks the call-site target and authorization intent, and can execute only a caller-injected documented callable adapter; the CLI default remains non-live and returns fallback when no runner is injected. The create-thread callable wiring-boundary helper accepts ready executor evidence plus a caller-supplied documented `create_thread` descriptor or explicit non-live adapter wiring contract and converts it into the executor helper's injected adapter contract shape without invoking Desktop runtime. The create-thread callable wiring evidence bundle / executor-request assembly helper accepts ready wiring evidence plus caller-supplied target, prompt, authorization, and executor-shell evidence to produce a complete non-live executor request preview / handoff bundle; CLI/default and tests do not execute an injected runner or call Desktop runtime.

The V1 live boundary is limited to `scripts/desktop_runtime_create_thread_live_smoke.py`: a single documented `create_thread` live smoke helper that can call one runtime-provided documented callable only when the caller injects that callable and provides exact human approval. It rechecks target identity, authorization intent, repo, remote, branch, expected head, read-only smoke prompt, permission/auth handling, and response shape at the actual call site. `ready` means only that the smoke call created or queued a new Desktop thread and delivered the read-only audit prompt; it does not mean the audit completed. CLI/default/tests remain non-live and return `fallback` without an injected callable. The smoke prompt is read-only and forbids comments, reviews, file edits, commits, pushes, PRs, merges, label/status changes, and other platform writes. Any remediation after the audit requires separate human approval.

The `read_thread` preflight helper checks read-only evidence readiness without treating preflight as runtime-call authorization. The evidence pipeline helper chains discovery, comparison, and create/read preflight into one CLI evidence example for maintainers who want to follow planner -> discovery -> compare -> preflight order; it can run a single `--target-action` and includes a top-level summary for ready/fallback/stopped scanability. The session compatibility status validator checks explicit caller-supplied status for wrapper/helper identity, contract evidence, comparison result, and session marker before later preflight reference. The first-use handshake helper constructs that status from caller-supplied documented metadata, old wrapper contract evidence, expected wrapper/helper identity, and an explicit session marker, then validates it. The session-scoped compatibility cache helper reads or writes caller-explicit cache envelopes for same-session contract compatibility evidence only. `ready` means evidence, proposal, executor-shell surface readiness, injected adapter contract completion, callable wiring readiness, executor request preview readiness, or single live smoke completion only; it does not mean the CLI default called Desktop runtime, that `read_thread` was called, that the smoke audit task finished, that session status, handshake evidence, cache evidence, preflight evidence, authorization-gate evidence, executor-boundary proposal evidence, executor-shell evidence, injected executor evidence, callable wiring evidence, callable bundle evidence, or prior smoke evidence authorized another live runtime call, or that commit, push, PR creation, merge, platform comments, reviews, labels, status changes, or other external writes are authorized. Shell, proposal, gate, cache, preflight, executor, wiring, bundle, and prior smoke evidence cannot replace actual call-site target validation, permission/auth handling, response validation, returned thread id or `pendingWorktreeId` validation, or returned status validation. These helpers do not read Desktop private runtime state, add a daemon, MCP server, app-server client, sidecar, background service, skill, catalog item, or installer entry.

## Runtime Compatibility

| Label | Meaning |
| --- | --- |
| `shared` | Works in Codex CLI and Codex Desktop with ordinary repository files and shell/git inspection. |
| `cli` | Designed primarily for Codex CLI. Desktop may use the same steps manually or through an equivalent thread. |
| `desktop` | Requires Codex Desktop behavior such as main-agent orchestration or worker delegation. |
| `plugin-dependent` | Requires an installed plugin, connector, or platform tool. The skill must name the dependency. |

## Skills

| Skill | Runtime | Purpose |
| --- | --- | --- |
| `planning` | shared | Produce scoped implementation plans with assumptions, risks, DoD, and verification. |
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
| `desktop-project-delivery` | desktop | Codex Desktop delivery entrypoint for delegated project work. |
| `desktop-thread-delegation` | desktop | Choose the next safe task, continue in the current thread when appropriate, or hand off to a new Desktop thread when authorized and supported. |
| `desktop-spec-plan-gate` | desktop | Desktop gate for spec, plan, and DoD drafts. |
| `desktop-implementation-gate` | desktop | Desktop formal integration gate for worker outputs before commit readiness. |
| `desktop-pr-merge-gate` | desktop | Desktop PR and merge readiness gate that summarizes evidence without publishing or merging. |

## Workflows

- `workflows/implementation-workflow.md`
- `workflows/review-workflow.md`
- `workflows/merge-readiness-workflow.md`
- `workflows/desktop-delivery-workflow.md`

Shared orchestration templates include task briefs, task manifests, next-session prompt templates, current task summaries, project specs, implementation plans, closure triage overlays, task continuation reports, integration review reports, and orchestrator gate reports.

## Examples

- [Basic implementation](examples/basic-implementation.md)
- [Code review](examples/code-review.md)
- [Docs review](examples/docs-review.md)
- [Orchestrated review closure](examples/orchestrated-review-closure.md)
- [Multi-step maintenance](examples/multi-step-maintenance.md)
- [Task continuation](examples/task-continuation.md)
- [Desktop thread delegation](examples/desktop-thread-delegation.md)
- [Runtime adapter boundary](examples/runtime-adapter-boundary.md)
- [Language verification](examples/language-verification.md)
- [GitHub workflow guidance](examples/github-workflow-guidance.md)
- [Merge review and readiness](examples/merge-review.md)
- [Desktop project delivery](examples/desktop-project-delivery.md)

See `docs/roadmap.md` for the near-term public roadmap and `docs/release-notes-v0.1.0.md` for the published v0.1.0 release notes.

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

Install CLI-compatible delivery workflows:

```bash
./install.sh install codex-delivery-workflow
```

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

- Codex skills are installed to `~/.codex/skills/<skill>/`.
- Codex templates are installed to `~/.codex/templates/...`.
- Custom `CODEX_SKILLS_DIR` or `CODEX_TEMPLATES_DIR` overrides require `CODEX_DEV_SKILLS_ALLOW_CUSTOM_TARGETS=YES`.
- The installer refuses symlink target roots and symlink target paths before install, update, diff, or uninstall.
- Installer state is stored under `~/.local/state/codex-dev-skills` unless `XDG_STATE_HOME` changes it.
- State records only non-sensitive metadata such as repository name, version, action, group, and timestamp.
- The installer never overwrites `~/.codex/AGENTS.md`.

## Verification

Run the repository hygiene check before proposing a release or PR:

```bash
./scripts/validate-repo.sh
```

This validates catalog consistency, required runtime labels, symlink safety, and public hygiene checks for excluded private or legacy terms.
The repository pins Python with `.python-version`; when Python helpers or tests are in scope, confirm the active runtime first:

```bash
python3 --version
```

The expected pinned version is Python 3.12.9.

For tag, release notes, and PR readiness checks, see [docs/release-readiness.md](docs/release-readiness.md).

## Included Scope

This repository includes public software development workflows for:

- planning and implementation
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
