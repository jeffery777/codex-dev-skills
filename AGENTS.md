# Codex Development Skills Baseline

This public repository contains Codex CLI and Codex Desktop software development workflows. Treat this file as a repo baseline for maintaining the repository itself.

## Core Rules

- Read before write.
- Inspect current files and git state before mutation when the directory is a git repository.
- Verify target, scope, identity, environment/context, and current state before mutation.
- Keep changes scoped to the requested objective.
- Do not overwrite unrelated user changes.
- Prefer existing repository patterns over new abstractions.
- Run relevant verification after changes.
- Separate facts from inference.
- Mark unverified claims explicitly.
- Mark runtime-specific behavior explicitly.

## Review Mode

When the user asks for review, stay read-only unless they explicitly ask for fixes. Findings should lead with risks, bugs, regressions, missing tests, or policy violations.

## Checkout Selection

本專案預設單一進行中話題與單一 writer，優先沿用 local checkout。編排 agent
依既有修改、ownership、所需 base 及隔離需求決定 local 或 worktree；需要偏離
local 偏好時，先簡述原因，在既有授權及當次 runtime 契約允許範圍內續行。
不因 Git repository、新話題或開源授權本身建立 worktree；需要隔離時先檢查
可重用的工作樹。新話題、外部寫入及破壞性操作仍保留各自的授權邊界。

## Python Verification Environment

- Use `./scripts/project-python` for this repository's dependency checks,
  scripts, evals, and unit tests. It resolves a repository `.venv`, `pyenv`, or
  an already-correct `python3` and fails closed unless the exact tracked
  `.python-version` is selected.
- Before installing a missing module, print the selected interpreter and verify
  PyYAML with `./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'`.
- If the resolver cannot select the pinned interpreter or import `yaml`, inspect
  environment resolution before treating PyYAML as absent. Do not fall back to
  bare system Python or install into a different Python environment.
- Use the same resolved Python interpreter for dependency checks, scripts,
  evals, and unit tests throughout a verification run.
- Git worktrees and disposable clones must run the tracked resolver too. Do not
  copy `.venv` through `.worktreeinclude`; create or configure an environment
  for the new checkout when the resolver reports that the pinned runtime is
  unavailable.

## Destructive Actions

Destructive actions require explicit confirmation. This includes deletion, force updates, history rewrites, broad external mutation, direct trunk updates, and cleanup actions that cannot be previewed.

## Runtime Compatibility

Do not depend on unpublished Codex Desktop internals. Desktop-only behavior must be labeled Desktop-only and should provide a CLI fallback when possible.

Do not sync local runtime state, credential files, application state, logs, sessions, caches, SQLite databases, or machine-local config into this repository.

## Release State

- Follow `policies/release-state-contract.md` for release preparation and
  release-sensitive review.
- Treat `catalog.yaml` as the canonical offline source/package version; README
  prose, roadmap prose, release-note status, tags, and Releases do not define
  that local version.
- Do not maintain tracked "current published version" or "current development
  candidate" assertions. Verify current publication state from the annotated
  tag and non-draft, non-prerelease GitHub Release metadata at the release gate.
- Keep ordinary repository validation offline. It proves source/package parity
  and candidate structure, not GitHub publication.
- Preserve existing release notes as point-in-time records. Modify an existing
  note only for an independently verified factual or safety defect with an
  explicit in-scope justification.
- A release-sensitive review must classify source/package version, candidate
  preparation, publication truth, active guidance, and historical records. It
  must not pass solely because tests succeed.

## Exact-Head Merge Review

- Follow the provider-neutral `policies/exact-head-merge-review-contract.md`
  after a change request exists and before reporting content readiness.
- This GitHub-hosted repository explicitly selects
  `policies/github-exact-head-enforcement-profile.md`; installed shared skills
  must not infer that profile for GitLab CE or another provider.
- Pre-commit code, documentation, deep, and security review evidence may be
  reused when its revision and scope still match; its verdict cannot replace
  exact-head Merge Review.
- Bind content Merge Review to repository, change request, exact
  base/head/merge-base SHAs, diff identity, deterministic verification,
  findings, dispositions, and code/documentation coherence. Bind hosted CI,
  review threads, receipt readback, and the dedicated App separately through
  this repository's selected GitHub profile.
- After a fix, rerun the appropriate review proportionally to the affected
  boundary. Assess Security Diff Scan applicability under the exact-head
  contract; record the scope and rationale when not applicable. A non-ready draft
  may remain REVIEW_REQUIRED after applicable pre-commit gates. Before readiness,
  merge or release, always review the latest complete base-to-head range; never
  reuse an old-head verdict or change external rulesets, CI or platform gates.
- Clean review and scan results may advance automatically to later read-only or
  already-authorized stages. Stop only at a real decision, authority,
  environment, permission, risk, destructive-action, or unauthorized
  external-write boundary.
