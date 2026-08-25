# Release Notes: v0.18.2

Status: release candidate for Issue #179. Commit, push, pull request creation,
merge, annotated tag creation, and GitHub Release publication require the
authorized exact-state delivery flow.

v0.18.2 is a backward-compatible runtime-compatibility and repository-
validation patch over v0.18.1. It refreshes current public guidance for the
2026-08-24 deprecation of `codex mcp-server` and removes redundant unit-test
execution from exact-head CI without reducing the validation boundary.

## Runtime Compatibility

- Adds dated 2026-08-25 evidence for Codex CLI 0.149.1 and official OpenAI
  documentation.
- Records `codex mcp-server` as deprecated but still present in the observed
  CLI; no removal date is published.
- Keeps external MCP client configuration, connectors, native Desktop thread
  tools, app-server, SDK, and retired repository wrappers as distinct surfaces.
- Preserves the 2026-08-21 Desktop callable table as point-in-time evidence
  rather than claiming an unperformed schema revalidation.

## Validation De-duplication

- Adds the fail-closed `./scripts/validate-repo.sh --skip-unit-tests` mode while
  preserving zero-argument behavior.
- Rejects unknown, duplicate, extra, and positional arguments before creating
  validator state or running repository checks.
- Skip mode omits only 15 embedded unittest invocations. Hygiene,
  catalog/installer/version consistency, plugin parity, validators, and all 11
  direct eval acceptance scripts remain active.
- Changes repository-validation CI to run checks first, then one complete
  unittest discovery pass. All discovered modules remain covered (57 in this
  candidate); the validator's 44-module focused subset is no longer rerun in
  the same job.
- Marks skipped unit groups explicitly instead of emitting false passing
  evidence.

## Performance Evidence And Limits

The pre-change content-equivalent GitHub run executed 792 discovery tests in
651.706 seconds and then repeated 556 tests inside a 238-second validator
step. The implemented checks-only mode measured 12.74 seconds locally on
2026-08-25. These measurements come from different runners and are not an SLA;
exact-head CI remains the authoritative hosted-run evidence.

No internal test algorithm is changed in this patch. The largest historical
hot spot is the installer/profile integration group, whose subprocess and
filesystem work is part of its isolation coverage. Removing its duplicate CI
invocation provides the bounded optimization without weakening those tests or
introducing platform-specific fixtures.

## Compatibility And Rollback

Existing zero-argument validator callers, installed skills, runtime adapters,
installer target selection, security and data boundaries, and completion
authority remain compatible. Installer receipt metadata advances to 0.18.2.
Revert this patch or its eventual merge commit to restore the exact starting
source baseline `0a7b000d4fb55e25228d3329a02247540c341932`. The annotated
`v0.18.1` tag remains the base release identity, not the source rollback
target, because current main also contains later published-state coherence
commits. No data migration, deployment target, or destructive cleanup is
involved.

## Verification And Release Gate

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
bash -n scripts/validate-repo.sh
./scripts/project-python -m unittest tests.test_validate_repo tests.test_pr_issue_link tests.test_project_python tests.test_native_runtime_contract_docs tests.test_desktop_wrapper_security_fixtures tests.test_runtime_compatibility_release_docs
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh --skip-unit-tests
./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
git diff --check
git status --short --branch
```

Independent mixed-code review, release-sensitive merge review, exact-head CI,
and merge readiness must be finding-free before the annotated `v0.18.2` tag
and non-draft, non-prerelease GitHub Release are published. This repository has
no deployment target or publish/deploy workflow; deployment is not applicable
and a GitHub Release is not deployment evidence.

## Traceability

- Issue #179: <https://github.com/jeffery777/codex-dev-skills/issues/179>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.18.1>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.18.1...v0.18.2>
