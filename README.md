# codex-dev-skills

`codex-dev-skills` is an open, Codex-focused repository of software development skills and workflows for Codex CLI and Codex Desktop.

This is not a general prompt collection. It is a curated workflow set for planning, implementation, documentation updates, review, review follow-up, delivery gates, and merge readiness.

Version 1 is derived only from the private shared review layer plus the `review-workflow-codex` and `review-workflow-codex-desktop` packs. The content has been rewritten for public use with private names, local paths, runtime state, and legacy provider references removed.

## Source Priority

The shared layer canonical source is `shared/review-workflow-codex/codex` in the private source repository. Pack-local copies of shared skills, shared policies, and shared orchestration templates are treated as synchronized copies, not independent sources.

Source priority for version 1:

1. Shared layer canonical source for shared gates, shared policies, and shared orchestration templates.
2. Codex CLI/shared/core/general pack content for non-duplicate planning, implementation, docs, review, and delivery workflows.
3. Codex Desktop-only orchestration skills with the `desktop-` public prefix.

The public repository keeps only one renamed shared layer to avoid forks.

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
| `implementation-slice` | shared | Implement a bounded change after read-only inspection, then verify and inspect the diff. |
| `docs-update` | shared | Update user or project docs from code, specs, and verified behavior. |
| `code-review` | shared | Routine read-only review for code or mixed diffs. |
| `code-review-deep` | shared | Higher-scrutiny review for security, packaging, data, migration, or cross-module risk. |
| `docs-review` | shared | Read-only review for docs-only or docs-dominant changes. |
| `merge-review` | shared | Routine merge readiness review for base-to-head changes. |
| `merge-review-deep` | shared | Deep merge readiness gate for high-risk or release-sensitive changes. |
| `review-follow-up-plan` | shared | Build a read-only plan from review findings and verification gaps. |
| `review-follow-up-implementation` | shared | Apply scoped code or mixed-diff fixes from review findings. |
| `docs-review-follow-up` | shared | Apply scoped documentation fixes from docs review findings. |
| `review-follow-up-review` | shared | Verify whether prior review findings were closed. |
| `review-loop` | shared | Run implementation, review, follow-up, and re-review until blockers close or a human gate is reached. |
| `code-review-gate` | shared | Formal code review gate before commit, PR, or merge readiness. |
| `docs-review-gate` | shared | Formal documentation review gate before commit, PR, or merge readiness. |
| `merge-readiness-gate` | shared | Formal branch readiness gate after implementation and review evidence exist. |
| `review-artifact-cleanup` | shared | Dry-run first cleanup workflow for review artifacts. |
| `closure-triage` | shared | Select the next smallest safe packet from repo policy, project overlays, and current state. |
| `desktop-project-delivery` | desktop | Codex Desktop delivery entrypoint for delegated project work. |
| `desktop-project-orchestrator` | desktop | Main-agent orchestration building block for Desktop projects. |
| `desktop-spec-plan-gate` | desktop | Desktop gate for spec, plan, and DoD drafts. |
| `desktop-implementation-gate` | desktop | Desktop integration gate for worker outputs and review-before-commit. |
| `desktop-pr-merge-gate` | desktop | Desktop PR and merge readiness gate that summarizes evidence without publishing or merging. |

## Workflows

- `workflows/implementation-workflow.md`
- `workflows/review-workflow.md`
- `workflows/merge-readiness-workflow.md`
- `workflows/desktop-delivery-workflow.md`

Shared orchestration templates include task briefs, project specs, implementation plans, closure triage overlays, integration review reports, and orchestrator gate reports.

## Installation

Use the Codex-only installer:

```bash
./install.sh list
./install.sh install shared-review-gates
./install.sh install codex-review-workflow
./install.sh install codex-delivery-workflow
```

`./install.sh install --all` installs every group, including Desktop-only workflows. Use it only when you want the Desktop group installed too.

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

## Included Scope

This repository includes public software development workflows for:

- planning and implementation
- docs updates and docs review
- code review and deep code review
- review follow-up and review gates
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

More detail is in `docs/excluded-packs.md`.

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
