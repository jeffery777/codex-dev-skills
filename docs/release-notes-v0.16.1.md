# Release Notes: v0.16.1

Status: release candidate; commit, push, pull request creation, merge, tag,
GitHub Release, and deployment require the separately authorized exact-state
delivery flow.

v0.16.1 is a fail-closed Linux qualification timing fix over v0.16.0. It
implements Issue #159 without changing GitNexus version support, index identity,
memory, review, gate, completion, or release authority.
The adapter/hook driver identities advance to `gitnexus-v2c-a/4` and
`gitnexus-v2c-b-hook/3`, so prior qualification fingerprints fail closed and
must be regenerated from caller-owned provenance.

## Shared Refresh Deadline

- Keeps standalone qualification at the existing 10-second default and
  `1..300` validation.
- Validates the existing refresh timeout (`1..3600`, 120 seconds by default)
  before contacting GitNexus and derives one monotonic deadline.
- Charges executable/package/runtime qualification, repository preflight,
  controller execution, analyze, and postconditions to that same budget.
- Caps the controller to the earlier shared deadline so no phase can reset or
  extend the configured refresh budget.
- Applies the same contract to auto-on-demand hooks; notify-only hooks retain
  standalone qualification timing.

Detected absolute-budget expiry remains fail closed with
`probe-deadline-expired`, no partial index adoption, and no implicit retry.
The analyze runner retains a bounded slice that reserves postcondition time;
slice exhaustion before the absolute deadline remains `refresh-timeout` and
also cannot adopt an index. The v0.16.0 exact identity, dirty/untracked,
linked-worktree, primary-main local-advancement, isolated-home, lock,
circuit-breaker, and false-authority boundaries remain unchanged.

## Deterministic Coverage

Clock-controlled tests cover a valid qualification completing after 10 seconds
but within the refresh budget, standalone expiry, controller exhaustion before
runner execution, shared operator/hook deadlines, invalid values, and Linux-
relevant `1`/`3600` boundaries without wall-clock sleeps.

## Verification And Release Gate

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_adapter
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest tests.test_eval_gitnexus_index_lifecycle
./scripts/project-python scripts/eval-gitnexus-index-lifecycle.py
./scripts/project-python scripts/sync-plugin-package.py --write
./scripts/project-python scripts/sync-plugin-package.py
./scripts/validate-repo.sh
git diff --check
```

Formal code and documentation review, Security Diff Scan, deep merge review,
and exact-head merge-readiness must be current and finding-free. After the
annotated tag and non-draft/non-prerelease GitHub Release identities are proven,
run one bounded released-artifact requalification on the authorized Rocky Linux
9.8 host in a new evidence root. That external evidence remains advisory and
does not replace repository or release authority.

## Traceability

- Issue #159: <https://github.com/jeffery777/codex-dev-skills/issues/159>
- Base release: <https://github.com/jeffery777/codex-dev-skills/releases/tag/v0.16.0>
- Compare after publication: <https://github.com/jeffery777/codex-dev-skills/compare/v0.16.0...v0.16.1>
