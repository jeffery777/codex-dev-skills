# Issue #124 Final Deep Code Review

Date: 2026-07-30

Review mode: `code-review-deep`

Gate result: PASS

Authority: advisory read-only review evidence only

## Executive Summary

The final mixed patch preserves the exact V2d-A boundary, adds V2d-B through
separate shared contract families, and does not couple the implementation to
either the CLI session adapter or Desktop task/thread adapter. Parsing, file
reads, record/evidence inventories, lineage, identities, role separation,
privacy checks, canonical digests, projections, CLI output, packaging, and
rollback behavior were inspected against the implementation and tests.

No MUST-FIX, SHOULD-FIX, or NIT finding remains.

## Findings And Dispositions

| Finding | Severity | Disposition | Closure evidence |
| --- | --- | --- | --- |
| `CR124-001` graph projection materialized the evidence iterable before the aggregate count bound | MUST-FIX | Fixed | `build_graph_projection` now uses the shared bounded iterator helper before any full materialization; `test_graph_projection_bounds_evidence_iterables` proves `document-count` rejection |

The security/privacy candidates and their dispositions are recorded in the
canonical security-diff-scan bundle; none remains an unresolved code-review
finding.

## Deep Risk Notes

- V2d-B role identities remain declared structural labels, not authenticated
  principals or authorization.
- Privacy patterns are defense in depth. Real records and projections remain
  caller-controlled and outside public Git.
- Human manifest validation does not attest to separately stored Markdown;
  the public and installed docs now require same-invocation rendering or exact
  byte-digest comparison.
- The CLI and package APIs are offline and explicit-file only. Their aggregate
  record/evidence inventories are bounded before file reads or materialization.
- V2d-A code and public document kinds are unchanged; regression suites remain
  green.

## Evidence

- focused V2d-B/V2d-A suite: 64 tests passed after final code-review fix;
- complete focused suite including docs tests: 67 tests passed before the
  final graph-specific regression, which then passed in the 64-test rerun;
- improvement-lineage eval: 6 positive, 23 negative, zero false-authority
  claims, zero projection mismatches;
- full `./scripts/validate-repo.sh`: passed;
- shell syntax, Python compilation, ledger structure, and `git diff --check`:
  passed;
- the security local-patch inventory includes every tracked and untracked
  changed file, including these final review receipts.

## Re-runnable Verification Commands

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_lineage \
  tests.test_improvementctl \
  tests.test_eval_improvement_lineage \
  tests.test_improvement_lineage_contract_docs \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
PYTHONDONTWRITEBYTECODE=1 python3 scripts/eval-improvement-lineage.py
./scripts/validate-repo.sh
python3 scripts/validate-loop-ledger.py
bash -n install.sh scripts/validate-repo.sh
git diff --check
```
