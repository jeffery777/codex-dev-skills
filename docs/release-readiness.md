# Release Readiness

Use this guide when maintainers prepare release or PR readiness evidence for this workflow pack or for a target repository using these skills.

This guide describes readiness checks only. It does not authorize commit, push, PR creation, publication, tag creation, merge, deploy, platform comments, or review submissions.

## When To Use

Use release readiness guidance when a bounded change is close to publication and the maintainer needs Codex to organize checks and handoff evidence before a human gate:

- a release notes draft or current release notes file needs to match the intended release scope;
- a tag or version candidate needs local verification before creation;
- a PR should be checked for docs, installer, catalog, and workflow alignment;
- a branch needs merge or release readiness evidence summarized for maintainers.

## Read First

Before preparing release readiness evidence, read the durable source of truth:

- `AGENTS.md`
- `README.md`
- `docs/roadmap.md`
- `docs/release-notes-v0.1.0.md` as historical release context, or the current release notes draft for an unreleased version
- `catalog.yaml`
- `install.sh`
- relevant `skills/`, `templates/`, `workflows/`, and `policies/` files for the changed scope

Also inspect git state:

```bash
git status --short --branch
git log --oneline -10
```

## Readiness Checklist

Check these items before asking a maintainer to approve external writes:

- Scope is clear: changed files match the release or PR objective.
- Roadmap is current: completed public roadmap items are removed or updated without unrelated rewriting.
- Release notes match their role: historical release notes remain a point-in-time record, while current release notes drafts match the intended release scope.
- Installer state is aligned: `catalog.yaml`, `install.sh`, skills, templates, workflows, and README install groups agree.
- Runtime compatibility is labeled: shared, CLI, Desktop, and plugin-dependent behavior is not blurred.
- Human gates are explicit: commit, push, PR creation, tag, publish, merge, release, deploy, platform comments, and review submissions require exact approval.
- Review evidence exists: ordinary review primitives or formal gates were run at the stage that needs them.
- Verification is re-runnable: commands and skipped checks are listed with enough context for another maintainer.

When a change includes the GitNexus adapter, also require evidence that:

- the GitNexus qualification evidence-bundle digest separately binds captured
  package/help/status/query observations without recording machine-local paths;
- caller-owned accepted entry, interpreter, and complete package-tree digests
  originate outside adapter self-report, are compared through descriptor-bound
  no-follow reads before executing the qualified CLI, and package drift is
  checked again at every use;
- the production runtime fingerprint separately binds exact CLI/runtime bytes,
  version, observed analyze flags, schema/capability policy, and symlink policy;
- the handshake is disabled by default and honestly reports `read_query` and
  all backend mutations unsupported;
- stale, dirty, missing, partial, unsupported, incompatible, corrupt, unknown, wrong-repo,
  unsafe-path, symlink, timeout, lock, and capability/version drift cases fail
  closed;
- fixture refresh uses only `analyze --index-only`, isolated `GITNEXUS_HOME`,
  offline environment, expected HEAD, and a pre-existing local-exclude guard;
- every refresh first acquires the deterministic fixed-OS-temp per-user lock
  for the canonical repository root before any optional instance lock; this is
  cooperative same-UID coordination, not distributed or hostile-process isolation;
- complete worktree state (including untracked and ignored paths), protected
  state, the complete local `.git` administrative tree, metadata schema, and
  indexed revision are unchanged or exactly as qualified;
- Git probes and refresh descendants ignore replacement refs and lazy fetch,
  use isolated system/global configuration, disable hooks/fsmonitor/untracked
  cache, and enforce timeout/output bounds;
- macOS arm64 live qualification and Linux portability-only evidence are labeled accurately;
- rollback keeps the V2b no-backend path usable and does not delete or rewrite
  user repository state.

## Suggested Verification

Run the repository hygiene check:

```bash
./scripts/validate-repo.sh
```

For docs-only release readiness work, also run:

```bash
git diff --check
```

When the changed scope includes Python helpers or tests, record the active Python runtime before running Python checks:

```bash
python3 --version
```

This repository pins Python 3.12.9 with `.python-version`.

For the GitNexus adapter scope, run at least:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_memory_contract tests.test_memoryctl tests.test_eval_memory_contract
python3 scripts/eval-memory-contract.py
./scripts/validate-repo.sh
git diff --check
```

Exercise executable-origin regressions as part of the adapter/loop suites:
ambient `PATH` must not select Git, GitNexus qualification must reject an
omitted executable, and an env-node GitNexus entry must reject an omitted Node
runtime. Live qualification must supply absolute machine-local CLI and, when
applicable, Node paths; record their fingerprints but never the paths.

Record any live qualification separately from fixture tests. Running the test
suite does not prove that a local GitNexus executable, Linux runtime, or existing
index was qualified.

For release-sensitive branch readiness, use the review primitive that matches risk:

```text
Use merge-review for main..HEAD.
Use merge-review-deep for release-sensitive main..HEAD.
Use merge-readiness-gate only when a formal readiness decision is required before PR handoff, merge readiness, or final human approval.
```

## Release Notes Review

When updating release notes, verify each claim against repository files:

- skill group names match `catalog.yaml` and installer behavior;
- highlighted workflows exist under `skills/`, `workflows/`, `templates/`, or `policies/`;
- safety claims match `AGENTS.md`, `docs/usage-model.md`, and `policies/human-gate-policy.md`;
- verification commands are current and runnable from the repository root;
- no private paths, credentials, local runtime state, logs, caches, or machine-specific config are included.

Do not backfill post-release maintenance changes into historical release notes such as `docs/release-notes-v0.1.0.md` unless the file is explicitly converted to cumulative or current release notes.

## Tag And Publish Gate

Codex may prepare tag or release readiness evidence, but it should stop before creating tags or publishing releases unless the maintainer explicitly authorizes the exact action.

Before tag or release publication, report:

- target branch and HEAD SHA;
- proposed tag or release name;
- release notes path and summary;
- verification commands run and results;
- review or gate evidence used;
- skipped checks and residual risk;
- whether the action is reversible or requires manual recovery.

## PR Readiness Summary

A release or PR readiness handoff should include:

- changed files and why they are in scope;
- roadmap or release note updates;
- validation and review evidence;
- unresolved questions or skipped checks;
- human gate required for commit, push, PR creation, merge, tag, release publication, platform comments, or review submissions.

Stop and ask before any external write if the target, permissions, release version, tag name, source of truth, or verification evidence is unclear.
