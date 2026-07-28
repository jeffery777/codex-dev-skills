# Release Notes: v0.9.3

Release date: 2026-07-28

v0.9.3 is a workflow-safety and performance maintenance release for the V2c-B
feature baseline. It adds one repository-owned Code Mode tool-orchestration
policy for skills that perform substantial tool inspection, planning, review,
implementation, or orchestration. It does not change workflow authority,
approval, sandbox, source-of-truth, completion, or Loop Engineering milestone
semantics, and it does not implement V2d-A.

## Code Mode Tool Orchestration

- Added `policies/code-mode-tool-orchestration-policy.md` as the single
  authoritative batching and concurrency policy.
- Defined a bounded stage as calls whose targets, scope, authority, and next
  decision point are fixed before execution and whose results cannot change
  whether another call in the stage should run.
- Prefer bounded concurrent execution only when the active runtime exposes
  `functions.exec` or an equivalent capability and every call is independent.
  Missing, unknown, or incompatible capabilities use sequential fallback.
- Use `Promise.allSettled` when partial results remain useful and inspect every
  fulfilled or rejected result. Use `Promise.all` only for fail-fast
  aggregation, without claiming that it cancels already-started work.
- Keep dependencies, adaptive investigation, approval gates, wait/resume,
  discovered identifiers and cursors, shared locks, shared files, Git state,
  and database or service mutations sequential.
- Bound query scope, per-call output, batch size, and aggregate return volume.
  Batching may reduce outer round trips and latency, but does not necessarily
  reduce total token use.

## Packaging And Validation

- Installed the policy through `shared-review-gates` at
  `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`.
  Existing review, delivery, CLI handoff, Desktop delivery, and opt-in agent
  profile groups receive it through their normal dependency expansion.
- Added concise source and installed-target references only to the 13 skills
  that perform substantial tool execution; thin gates, aliases, adapters, and
  unrelated skills remain unchanged.
- Added consistency validation for single policy ownership, required policy
  clauses, affected-skill references, catalog dependencies, installer manifest
  parity, installed content, and duplicate or missing sources.
- Added isolated install, `--all`, update, missing-source, wrong-reference, and
  untrusted-fixture regression tests without touching live user skill,
  template, agent-profile, or runtime-state directories.
- Kept cross-repository validation data-only: `--repo-root` may select policy,
  catalog, and skill content, but the validator executes only its own trusted
  checkout's installer manifest with bounded time and output. Caller-selected
  source reads require regular non-symlink files and enforce per-file,
  Markdown-count, and aggregate-size bounds.

## Installation And Update

Review local differences before updating:

```bash
./install.sh diff --all
./install.sh update --all
```

Install the shared review group and its policy:

```bash
./install.sh install shared-review-gates
```

Restart Codex or begin a new task after installation so changed skills and
templates are rediscovered.

## Verification

Re-run the release candidate verification from the repository root:

```bash
python3 --version
bash -n install.sh
bash -n scripts/validate-repo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_code_mode_tool_policy
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

The exact-head formal review, security diff scan, and release-readiness evidence
must be recorded for Issue #119 after all implementation and release-prep
changes are present. This file does not claim that those later gates have
already completed.

## Rollback

Review `./install.sh diff --all` before reinstalling or updating from v0.9.2.
Restoring the v0.9.2 source and running the ordinary reviewed update path
restores the earlier skill content. An already installed policy file may remain
unreferenced because update is not a delete-sync operation. Do not delete,
move, or overwrite existing skills, templates, machine-local state, sessions,
tasks, or unrelated configuration as an implicit rollback.

## Traceability

- Code Mode tool-orchestration issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/119>
- Compare:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.9.2...v0.9.3>
