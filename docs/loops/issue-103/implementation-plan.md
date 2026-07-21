# V2c-B Implementation Plan

## Objective

Add opt-in GitNexus freshness hooks that notify on stale state and may perform a
safe on-demand refresh through the existing V2c-A controller.

## Source Of Truth

- GitHub Issue #103
- `docs/loops/issue-103/loop-spec.md`
- `docs/loops/issue-103/task-manifest.yaml`
- `skills/loop-engineering/scripts/gitnexus_adapter.py`
- `docs/external-memory-contract.md`
- `docs/native-runtime-capabilities.md`
- Official Codex Hooks documentation

## Facts And Design Decisions

- Codex currently exposes `SessionStart`, but no native `post-commit` event.
- `PostToolUse` can observe `Bash`, including nonzero exits, but cannot undo its
  side effects and does not cover every equivalent Git mutation path.
- The implementation therefore rechecks live freshness after matched Bash tool
  calls without parsing or trusting the command string. `SessionStart` provides
  a compensating check for mutations that hooks did not observe.
- Hook handlers are synchronous command handlers today. The runner keeps
  notify-only checks bounded and leaves heavyweight refresh opt-in.
- Active machine-local values cannot live in repository artifacts. The repo
  ships inactive templates; maintainers materialize an absolute local config
  and hook command only after review.
- V2c-A requires a fresh empty isolated home for every refresh. Auto-on-demand
  therefore creates one `0700` child below a pre-approved secure machine-local
  parent only when refresh is eligible. It does not automatically delete those
  derived homes, so failure evidence and later cleanup remain operator-owned.
- A repository-bound `0600` circuit-breaker marker is persisted in that parent
  after controller failure. Later hooks notify without retrying until an
  operator explicitly inspects and clears the marker.

## Task Slices

1. Define durable V2c-B spec, plan, manifest, and ledger/evidence paths.
2. Add `gitnexus_hook.py` with bounded input/config parsing, event validation,
   repository confinement, freshness evaluation, advisory output, and
   dependency-injected controller delegation.
3. Add inactive `hooks.json` and machine-local configuration examples under
   `templates/hooks/gitnexus-v2c-b/`; include them in the delivery template
   catalog without activating them.
4. Add focused tests for schemas, event filtering, path/identity safety,
   notify-only behavior, refresh eligibility, controller success/failure, and
   no-hook fallback.
5. Update README, usage, external-memory, runtime-compatibility, roadmap, and
   release-readiness documentation.
6. Run targeted and full verification, inspect the diff, perform deep code and
   docs review, close findings, and prepare PR-readiness evidence.

## Ownership

- Current session owns all Issue #103 files.
- Concurrency is one; no worker or background task owns overlapping paths.

## Affected Files

- `skills/loop-engineering/scripts/gitnexus_hook.py`
- `templates/hooks/gitnexus-v2c-b/*`
- `tests/test_gitnexus_hook.py`
- `docs/loops/issue-103/*`
- `README.md`
- `docs/usage-model.md`
- `docs/external-memory-contract.md`
- `docs/native-runtime-capabilities.md`
- `docs/roadmap.md`
- `docs/release-readiness.md`
- `catalog.yaml`
- `install.sh`
- affected installer/catalog/runtime contract tests

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
git diff --check
```

## Review Plan

- Review primitives:
  - `code-review-deep`
  - `docs-review`
- Formal gates:
  - `code-review-gate`
- Formal gate trigger:
  - PR readiness

## Rollback Or Recovery

- Disable or remove the materialized V2c-B hook configuration.
- Leave V2c-A and the no-backend path intact.
- Do not delete machine-local indexes or restore/reset user repositories.
- Source rollback may revert the V2c-B change independently.

## Open Questions

- Plugin packaging remains intentionally deferred. If later approved, plugin
  hooks may use `PLUGIN_ROOT` and `PLUGIN_DATA` but must preserve this contract.
- A future native commit lifecycle event may replace the broad Bash
  compensation hook only after independent runtime qualification.
