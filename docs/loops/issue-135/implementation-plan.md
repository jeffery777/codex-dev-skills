# Issue #135 Implementation Plan — Docs-Only Roadmap

## Objective

Align the public roadmap, Operational Evidence program, architecture decisions,
and external-memory boundary with the Issue #135 roadmap specification. Keep
the change additive, docs-only, and independently reviewable through exact-head
draft-PR readiness.

## Facts And Assumptions

- Issue #135 is the only open Issue currently found for this scope.
- `origin/main` includes merged V3-A PR #134.
- The latest formal release is v0.11.1; v0.12.0 remains a draft release
  preparation and is not released.
- The existing GitNexus index is bound to the V3-A head. That head and current
  accepted main have the same Git tree, so its code graph is content-current
  even though the merge commit id differs.
- V2b production, tests, and evals are read-only evidence for this task.
- No release after v0.12.0 is assumed or promised.

## Change Surface

- `README.md`
- `docs/roadmap.md`
- `docs/programs/operational-evidence/README.md`
- `docs/programs/operational-evidence/implementation-phases.md`
- `docs/programs/operational-evidence/continuation.md`
- `docs/programs/operational-evidence/architecture-decisions.md`
- `docs/external-memory-contract.md`
- `docs/loops/issue-135/roadmap-spec.md`
- `docs/loops/issue-135/implementation-plan.md`
- `docs/loops/issue-135/task-packet.md`
- docs-only verification/review receipts under `docs/loops/issue-135/receipts/`

No runtime, tests, fixtures, evals, workflows, packaging, catalog, installer,
version, or release-note file is in scope.

## Work Slices

1. Freeze the verified baseline, gap matrix, protocol boundary, threat model,
   V3-B evaluation seam, and next Issue brief in the roadmap spec.
2. Align the roadmap and program phase order with the release interlock and
   M0/M1/M2 dependencies.
3. Record the architecture decisions for provider neutrality, operation
   authority, execution receipts, and the M1/V3-C gates.
4. Align README and the external-memory public boundary without changing
   `loop-memory/v1`.
5. Run docs-focused and repository validation, review the full diff for
   authority/security/privacy claims, close findings, and create an exact-head
   draft PR only after every gate passes.

## Verification Plan

Use one `.python-version`-resolved interpreter for every Python command,
beginning with:

```bash
python3 -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
```

Then run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_memory_contract \
  tests.test_memoryctl \
  tests.test_eval_memory_contract \
  tests.test_improvement_proposal_contract_docs
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
./install.sh manifest
./install.sh diff --all
bash -n install.sh scripts/validate-repo.sh
git diff --check
git status --short --branch
git ls-files --others --exclude-standard
```

The installer/package commands are consistency reads. They must not produce a
tracked content change. If validation requires a runtime/test edit, stop at a
human gate instead of expanding scope.

## Review Plan

- docs review over the complete diff;
- deep read-only authority, data, concurrency, security, and privacy review;
- formal docs-review gate with durable dispositions for every finding;
- exact-head merge-review-deep and merge-readiness evidence for draft-PR
  handoff;
- hosted GitHub Actions on the exact pushed head;
- unresolved review-thread and draft-state checks.

## Risks And Controls

- **Premature completion:** every new document says what is planned versus
  verified and does not claim release, V3-B, M0, or M1 completion.
- **Contract drift:** no V2b source/reference fields change; future protocol
  schemas remain separately gated.
- **Backend coupling:** the V3-B seam is provider-neutral and memory-off by
  default; SQLite/FTS5 belongs only to later M1.
- **Authority confusion:** eligibility, operation authority, execution receipt,
  acceptance, and promotion remain separate.
- **Privacy leakage:** only generic public design content is recorded; no
  machine-local values, raw records, credentials, PII, host/user identity,
  paths, logs, or config enter the diff.
- **Release coupling:** v0.12.0 closure stays first and separate; later release
  targets stay TBD.

## Human Gates

Stop for source-of-truth conflict; any required runtime/test change; public
contract or data-model semantics; unresolved authority/security/privacy risk;
backend implementation; V3-C automation; destructive action; ready transition;
merge; tag; release; deployment; or activation.
