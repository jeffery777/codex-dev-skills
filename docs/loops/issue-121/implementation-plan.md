# V2d-A Operational Evidence V0 Implementation Plan

## Objective

Implement Issue #121 from the accepted contract in
`docs/loops/issue-121/loop-spec.md`, close review findings, and prepare one
v0.10.0 implementation/release branch up to the next exact human gate.

## Facts And Design Decisions

- V2d-A is the accepted next feature milestone and targets v0.10.0.
- The contract is JSON-only and standard-library-compatible.
- One strict common envelope contains one of five exact payload kinds.
- Document and cross-document validation are separate operations.
- Unknown fields and duplicate keys fail closed; v0 has no extension field.
- Environment privacy uses a coarse allowlist. Prohibited identifiers are
  omitted, never hashed.
- Failure records use a finite taxonomy and carry no arbitrary messages or raw
  logs.
- Artifact references use repository-relative paths, exact Git commits, or
  opaque ids; URLs and machine-local paths are unsupported.
- Operational evidence is non-authoritative even when it references
  verification, review, authorization, or platform artifacts.
- Version metadata, release notes, and release-readiness preparation belong to
  this branch. Merge, tag, and GitHub Release remain later gates.

## Task Slices

1. Create and review the loop spec, implementation plan, task manifest, and
   initial ledger.
2. Implement the strict document model, parser, canonical digest, privacy
   checks, five kind validators, and cross-document validation.
3. Implement `evidencectl.py` with deterministic `validate` and `validate-set`
   results.
4. Add positive and adversarial fixtures plus focused unit/CLI/eval tests.
5. Add the deterministic operational-evidence eval and repository-validation
   integration.
6. Add the public contract/reference docs and align Loop Engineering,
   Operational Evidence program docs, README, roadmap, installer/catalog, and
   release readiness.
7. Prepare v0.10.0 version metadata and release notes in the same branch.
8. Run focused/full verification, deep code review, docs review,
   security/privacy review, formal readiness gates, and close MUST-FIX
   findings.

## Expected Files

### Production contract

- `skills/loop-engineering/scripts/operational_evidence.py`
- `skills/loop-engineering/scripts/evidencectl.py`
- `skills/loop-engineering/references/operational-evidence-v0.md`

### Tests and evals

- `evals/operational-evidence/suite.json`
- `evals/operational-evidence/fixtures/*.json`
- `scripts/eval-operational-evidence.py`
- `tests/test_operational_evidence.py`
- `tests/test_evidencectl.py`
- `tests/test_eval_operational_evidence.py`
- `scripts/validate-repo.sh`

### Public docs and release preparation

- `docs/operational-evidence-contract.md`
- `skills/loop-engineering/SKILL.md`
- `README.md`
- `docs/roadmap.md`
- `docs/programs/operational-evidence/*.md`
- `docs/release-readiness.md`
- `docs/release-notes-v0.10.0.md`
- `install.sh`
- `catalog.yaml`
- `docs/loops/issue-121/*`

Final review may narrow this set when a listed file needs no change. It must
not broaden into V2d-B, V3, runtime services, or private data.

## Implementation Constraints

- Prefer a self-contained V2d-A module over refactoring the accepted V1/V2b
  validators.
- Use exact field sets and finite enum maps.
- Use parser-level duplicate-key rejection.
- Bound encoded document size, nesting depth, string bytes, array counts, and
  safe integers.
- Never include a rejected input value in an error.
- Keep CLI output deterministic and machine-readable.
- Do not dereference URLs or opaque ids.
- Local artifact byte verification is not part of v0 set validation; the
  contract validates typed identities, digests, and relationships only.
- Keep synthetic sentinel data visibly non-secret and non-private.

## Verification

```bash
python3 --version

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence

python3 scripts/eval-operational-evidence.py

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_loop_engineering_core \
  tests.test_validate_loop_ledger \
  tests.test_agent_routing \
  tests.test_memory_contract \
  tests.test_memoryctl \
  tests.test_gitnexus_adapter

python3 scripts/eval-loop-engineering.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh

bash -n install.sh scripts/validate-repo.sh
git diff --check
git status --short --branch
git diff --stat
git diff --name-only main...HEAD
```

## Review Plan

### Spec and plan gate

- `docs-review`
- `docs-review-gate`

The gate blocks implementation for unresolved public-contract,
privacy/redaction, authority, data-placement, release-scope, or verification
semantics.

### Implementation and PR-readiness gates

- `code-review-deep`
- `docs-review`
- Codex Security diff scan for parser, canonicalization, privacy, path,
  tamper, reference, and authority boundaries
- `code-review-gate`
- `merge-review-deep`
- `merge-readiness-gate`

Every MUST-FIX is fixed and the affected review rerun. Other findings receive a
durable disposition.

## Release Plan

- Set `install.sh` and `catalog.yaml` to 0.10.0.
- Update README current baseline and current release-notes link.
- Add `docs/release-notes-v0.10.0.md`.
- Update roadmap and Operational Evidence program status.
- Re-run exact-head verification and release-sensitive reviews after all
  release changes.
- Do not create a second release-preparation branch.
- After an authorized PR merge, separately confirm the reviewed merge SHA
  before seeking authorization for tag `v0.10.0` and GitHub Release
  publication.

## Rollback Or Recovery

- Source rollback can revert the V2d-A commit independently.
- Existing V1/V2a/V2b/V2c code remains intact and is the fallback.
- No backend, database, user configuration, index, hook, scheduler, or private
  record is created by the feature.
- Never delete user state as part of rollback.

## Human Gates

- The GitNexus precondition is satisfied: repository-qualified index-only
  analysis informed the independent-module design, and final tracked change
  detection reported low risk with no affected process. New untracked V2d-A
  files remain covered by direct source, test, diff, and review evidence until
  a later committed-head analysis can index them.
- Stop for new contract/privacy/authority ambiguity.
- Stop before commit, push, PR creation, review submission, merge, tag,
  release, deploy, or another external write without exact authorization.
