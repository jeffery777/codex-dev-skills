# Issue #109 Implementation Plan

## Objective

Close the repository-hygiene and PR-traceability gaps discovered after the
v0.9.1 alignment work without changing the V2c authority model.

## Task Slices

### P0 — Clean Baseline And GitNexus Default

- Remove only the generated GitNexus block from the uncommitted `AGENTS.md`.
- Synchronize `main`, create the Issue #109 branch, and refresh the derived
  index with the explicit `--index-only` command.
- Track the smallest exact `.gitnexusrc` that makes index-only the default.

### P1 — Guardrail Validators And Tests

- Add a strict `.gitnexusrc` validator and deterministic negative tests.
- Add a PR event validator that requires open same-repository Issues.
- Integrate both guardrails into `scripts/validate-repo.sh`.

### P2 — Pull Request Template And CI

- Add the closing-Issue placeholder to a repository PR template.
- Add a read-only `pull_request_target` workflow that checks out only the base
  SHA and executes only the trusted base validator.
- Pin third-party action code by full commit SHA.

### P3 — Documentation And Review Closure

- Document the operator behavior, policy, authority boundary, and first-PR
  bootstrap limitation.
- Run focused tests, full repository validation, a live bare-analysis check,
  diff/private-data inspection, formal implementation review, formal
  documentation review, and final merge review.

## Risks And Controls

| Risk | Control |
| --- | --- |
| GitNexus regenerates `AGENTS.md` or provider files | Exact tracked index-only default, strict validator, live before/after check. |
| A fork PR executes attacker-controlled code with a token | `pull_request_target`, trusted base SHA only, read-only permissions, no head checkout. |
| A PR number is accepted as an Issue | Query the Issue API and reject responses containing `pull_request`. |
| A stale or unrelated Issue is used | Require every closing reference to be open and in the exact base repository. |
| CI status is mistaken for authority | Policy states that linkage is traceability only and preserves all existing gates. |
| The introducing PR appears covered by its own workflow | Record and manually verify the base-workflow bootstrap limitation. |

## Verification

```bash
python3 scripts/validate-gitnexus-config.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_gitnexus_config_guard \
  tests.test_pr_issue_link
bash -n scripts/validate-repo.sh
./scripts/validate-repo.sh
git diff --check
```

The live GitNexus check snapshots repository instruction/provider paths, runs
bare `gitnexus analyze`, and confirms that only the ignored derived index may
change.

## Review Plan

- Security-sensitive implementation review: `code-review-deep`
- Formal implementation gate: `code-review-gate`
- Documentation review: `docs-review-gate`
- Final base-to-head review: `merge-review-deep`

Review evidence remains read-only and non-authoritative.
