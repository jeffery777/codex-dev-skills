# Issue #124 Implementation Plan — V2d-B

## Objective

Implement the accepted V2d-B spec as two strict composed contract families,
preserve V2d-A unchanged, and prepare v0.11.0 up to the next exact human gate.

## Relevant Sources

- GitHub Issue #124
- `docs/loops/issue-124/loop-spec.md`
- `docs/operational-evidence-contract.md`
- `skills/loop-engineering/scripts/operational_evidence.py`
- `skills/loop-engineering/scripts/evidencectl.py`
- `scripts/eval-operational-evidence.py`
- `docs/programs/operational-evidence/*.md`
- `README.md`, `docs/roadmap.md`, `install.sh`, and `catalog.yaml`

## Assumptions

- v0.10.0 and Issue #123 are accepted on `main`.
- V2d-B remains offline, JSON-first, standard-library-compatible, and shared
  across Codex CLI and Desktop through the existing Loop Engineering package.
- The existing installer copies added Loop Engineering scripts/references once
  catalog/version metadata and installer tests are aligned.
- Real records and real projection outputs are unavailable and unnecessary for
  the public conformance suite.

## Impact Assessment

The refreshed GitNexus index at accepted `main` reports:

- `validate_document`: 3 direct dependants and 2 affected processes;
- `validate_set`: 2 direct dependants and 2 affected processes;
- `canonical_digest`: 4 direct dependants and 2 affected processes;
- `evidencectl.main`: 1 direct file-level dependant.

The direct consumers are the current CLI and operational-evidence eval path.
Therefore V2d-B will add a separate module and CLI, reuse only stable strictness
primitives where safe, and retain exact V2d-A regression coverage. Public
contract risk is high even though the call-graph blast radius is locally low.

## Task Slices

1. Freeze and pass the pre-implementation docs gate for the spec, plan,
   manifest, ledger, family/version decision, privacy matrix, role model,
   projection model, migration/rollback, and v0.11.0 scope.
2. Implement `loop-improvement-lineage/v0` parsing, canonical digest,
   V2d-A reference resolution, snapshot validation, role rules, and
   deterministic lineage reconstruction.
3. Implement `loop-evidence-projection/v0`, deterministic Markdown and typed
   graph construction/validation, and the optional Obsidian reference profile.
4. Add the bounded offline CLI without filesystem, Git, vault, graph, network,
   ledger, or platform mutation.
5. Add complete positive/adversarial fixtures, focused unit/CLI/projection
   tests, deterministic evals, and repository-validation integration.
6. Align public contract docs, portable references, Loop Engineering skill,
   README, roadmap, program continuation/phases, installer/catalog, version
   metadata, release readiness, and v0.11.0 release notes.
7. Run focused/full verification, GitNexus change detection, deep code/docs
   and security/privacy review, formal readiness gates, and resolve every
   MUST-FIX finding.

## Expected Change Surface

### Contract and CLI

- new `skills/loop-engineering/scripts/improvement_lineage.py`
- new `skills/loop-engineering/scripts/improvementctl.py`
- V2d-A module changes only if a reviewed shared-helper extraction is
  demonstrably safer and exact regressions prove no behavior change

### Fixtures, tests, and eval

- new `evals/improvement-lineage/` synthetic suite
- new focused lineage, CLI, projection, and eval tests
- new `scripts/eval-improvement-lineage.py`
- `scripts/validate-repo.sh`

### Docs and packaging

- new public V2d-B contract and installed references
- optional synthetic Obsidian reference profile
- `skills/loop-engineering/SKILL.md`
- `README.md`, `docs/roadmap.md`
- `docs/programs/operational-evidence/*.md`
- `install.sh`, `catalog.yaml`
- `docs/release-readiness.md`
- `docs/release-notes-v0.11.0.md`
- `docs/loops/issue-124/*`

## Definition Of Done

- The two exact V2d-B families and cross-family resolver match the accepted
  spec.
- V2d-A public files, supported documents, and dispositions remain compatible.
- All role, lineage, privacy, tamper, authority, ordering, and projection
  cases have deterministic positive/negative coverage.
- Repeated human/graph projection runs are byte-identical.
- The Obsidian profile has no runtime dependency or write behavior.
- Existing V1/V2a/V2b/V2c/V2d-A tests and evals remain green.
- Packaging and v0.11.0 documentation agree.
- Required deep reviews and readiness gates have no unresolved MUST-FIX.

## Verification Plan

Pre-implementation:

```bash
python3 scripts/validate-loop-ledger.py
git diff --check
```

Focused implementation commands to finalize with the code:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_lineage \
  tests.test_improvementctl \
  tests.test_eval_improvement_lineage \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-improvement-lineage.py
python3 scripts/eval-operational-evidence.py
```

Full working-tree readiness:

```bash
bash -n install.sh scripts/validate-repo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
gitnexus detect-changes
git diff --check
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
```

Before commit, reconcile the complete tracked/untracked inventory against the
local-patch review worklist; revision-range diffs cannot see uncommitted
content. After a separately authorized commit, run exact-head evidence:

```bash
git diff --name-only main...HEAD
git diff --stat main...HEAD
```

## Risks And Controls

- Contract drift: keep V2d-A version/kinds exact and test its historical
  positive and negative fixtures.
- Cross-family reference confusion: resolve contract, kind, id, and digest,
  never digest alone.
- Stale-baseline ambiguity: define it only relative to an explicit
  predecessor in the supplied closed set.
- Role escalation: require four distinct declared identities while documenting
  that role labels do not authenticate or authorize.
- Projection injection: derive all output from bounded ids/enums/digests and
  deterministic escaping; accept no free-form Markdown/HTML.
- Privacy leakage: apply strict whole-document checks and never echo rejected
  values.
- Apparent promotion: omit promoted/approved/merged/released/deployed states
  and preserve the exact four false-authority fields.
- Release coupling: keep feature and v0.11.0 preparation together, while
  retaining separate commit/push/PR/merge/tag/Release gates.

## Migration, Rollback, And Recovery

- No V2d-A migration is performed.
- No caller record is rewritten in place.
- Projections are regenerated rather than migrated.
- Source rollback reverts the V2d-B commit set; V2d-A remains the functional
  fallback.
- No rollback deletes user files, vaults, databases, indexes, sessions, or
  platform state.

## Review And Human Gates

Before implementation:

- `planning`
- `docs-review`
- `docs-review-gate`

After implementation:

- `code-review-deep`
- `docs-review`
- security/privacy review
- formal code/docs readiness gates
- after a separately authorized commit, exact-head `merge-review-deep`

Stop on unresolved public-contract, privacy, authority, role, deterministic
projection, migration, or release ambiguity. Stop before commit, push, PR
creation/review submission, platform comment, merge, tag, GitHub Release, or
deployment without exact authorization.
