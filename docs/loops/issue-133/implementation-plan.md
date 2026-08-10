# Issue #133 Implementation Plan — V3-A Evidence-To-Proposal

## Objective

Implement the accepted proposal-only V3-A contract as a new downstream family,
prove deterministic scoring/deduplication and complete validated lineage, and
prepare v0.12.0 through exact-head draft-PR readiness without promotion or
publication.

## Assumptions And Verified Prerequisites

- The worktree began clean at accepted `origin/main`
  `be2ba99a9b234ef8d6a4860929a29ca5de634ded` (`v0.11.1`).
- GitHub Issue #133 owns this scope and no open PR collides with it.
- The ten V3-A re-entry conditions were reconstructed from durable current
  repository/platform evidence; chat context was not used as proof.
- Python resolves to the `.python-version` 3.12.9 interpreter with PyYAML
  6.0.3; the same interpreter will run all verification.
- External memory is disabled. PlugMem, Mem0, and other backends are excluded.

## Impact Assessment

The fresh GitNexus index at accepted main reports:

- V2d-A `validate_set`: 3 direct dependants, 14 total affected symbols, 7
  processes, CRITICAL if modified;
- V2d-B `validate_lineage`: 5 direct dependants, 9 total affected symbols, 5
  processes, CRITICAL if modified.

Therefore V3-A adds a separate module/CLI/reference and calls existing
validators without editing V2d-A/B. Direct source, tests, and validators remain
authoritative; graph results are impact guidance only.

## Task Slices

1. Freeze the exact family, eligibility, lineage, scoring, hypothesis,
   duplicate, role, proposal-only, privacy, CLI, migration, packaging, release,
   verification, and human-gate decisions in a digest-bound planning packet.
2. Implement strict proposal generation and regeneration validation in a new
   `improvement_proposal.py` module.
3. Implement the explicit-file, stdout-only `proposalctl.py` CLI.
4. Add synthetic positive/adversarial fixtures, focused unit/CLI/docs tests,
   deterministic evals, and repository-validation integration.
5. Align public contract/reference/program/roadmap/package/release docs for
   v0.12.0 without publishing it.
6. Run focused/full verification; deep code/docs/security/privacy review;
   formal gates; exact-head review; draft PR; and hosted CI. Fix every MUST-FIX
   and rerun affected evidence.

## Expected Change Surface

### Contract and CLI

- `skills/loop-engineering/scripts/improvement_proposal.py`
- `skills/loop-engineering/scripts/proposalctl.py`
- `docs/improvement-proposal-contract.md`
- `skills/loop-engineering/references/improvement-proposal-v0.md`

V2d-A/B production files are not expected to change.

### Fixtures, tests, and eval

- `evals/improvement-proposal/`
- `tests/test_improvement_proposal.py`
- `tests/test_proposalctl.py`
- `tests/test_eval_improvement_proposal.py`
- `tests/test_improvement_proposal_contract_docs.py`
- `scripts/eval-improvement-proposal.py`
- `scripts/validate-repo.sh`

### Docs and packaging

- `skills/loop-engineering/SKILL.md`
- `README.md`, `docs/roadmap.md`
- `docs/programs/operational-evidence/*.md`
- `install.sh`, `catalog.yaml`
- `docs/release-readiness.md`
- `docs/release-notes-v0.12.0.md`
- `docs/loops/issue-133/*`

## Scenario And DoD Matrix

| Scenario | Required result | Evidence |
| --- | --- | --- |
| Valid V2d-A/B closed set | proposals generated | focused unit/eval |
| Missing or tampered lineage | fail closed | adversarial unit/eval |
| False-complete or authority true | fail closed; zero false outcomes | unit/eval |
| Wrong route or executable intent | fail closed | CLI/unit/eval |
| Recovery signal | score only when exact structured observations satisfy policy | unit/eval |
| Manual versus CI | byte-identical canonical output | repeated eval |
| Duplicate candidates | exactly one deterministic winner | unit/eval |
| Equal score and input permutation | stable tie/rank/output | unit/eval |
| Private/runtime data | generic rejection without echo | unit/eval/scan |
| Symlink/path/count/depth/size | bounded rejection | CLI/unit |
| Generation side effects | zero file/Git/network/platform mutation | CLI/unit |
| V1–V2d regressions | unchanged pass | regression evals/tests |
| Package/install | new files portable and complete | installer/package tests |
| Draft PR head | exact-head reviews and hosted CI pass | receipts/platform |

## Verification Plan

Use the same `.python-version`-resolved Python 3.12.9 interpreter after the
required interpreter/PyYAML proof.

Pre-implementation:

```bash
python3 scripts/validate-loop-ledger.py
git diff --check
```

Focused:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_improvement_proposal \
  tests.test_proposalctl \
  tests.test_eval_improvement_proposal \
  tests.test_improvement_proposal_contract_docs \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_improvement_lineage \
  tests.test_improvementctl
python3 scripts/eval-improvement-proposal.py
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-improvement-lineage.py
```

Expanded regressions:

```bash
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-agent-routing.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
bash -n install.sh scripts/validate-repo.sh
gitnexus detect-changes
git diff --check
git status --short --branch
git diff --stat
git ls-files --others --exclude-standard
```

After the authorized commit, repeat exact-head focused/full evidence, inspect
`origin/main...HEAD`, push, open a draft PR, wait for hosted CI on that exact
head, and confirm unresolved review threads. No passing command authorizes
promotion, ready-for-review, merge, tag, Release, or deployment.

## Risks And Controls

- Public-contract drift: separate V3-A family; do not edit V2d-A/B semantics.
- Digest-only confusion: regenerate every exact source lineage field.
- Score manipulation: integer-only fixed components derived from validated
  structured inputs; no caller weights or free text.
- Duplicate collision: SHA-256 structured signature plus exact signature-field
  regeneration; deterministic winner and suppressed-source receipts.
- Apparent promotion: exact false authority/action objects and a permanently
  pending independent human/platform gate.
- Eval self-authorization: eval is only a typed source artifact; it never sets
  eligibility, completion, or promotion.
- Privacy leakage: whole-document scanning, safe ids/enums, non-echoing errors,
  synthetic fixtures, and public-tree scans.
- CLI side effects: only explicit regular-file reads and stdout/stderr writes;
  no network/platform/Git modules or operations.
- Release coupling: v0.12.0 preparation is scoped here; merge/tag/Release remain
  later human gates.

## Migration, Rollback, And Recovery

- No V2d-A/B migration or rewrite occurs.
- Proposal outputs are regenerated, never migrated in place.
- Rollback reverts V3-A public code/docs/fixtures and leaves caller evidence,
  private data, Git/platform state, and external systems untouched.
- If a required source is missing or mismatched, the workflow returns a stable
  rejection; it does not discover, synthesize, or repair evidence.
- If hosted CI differs from local evidence, stop at the exact failing head and
  diagnose before any publication decision.

## Review And Human Gates

Before implementation:

- `planning`
- `docs-review`
- `docs-review-gate`

After implementation:

- `code-review-deep`
- `docs-review`
- security/privacy diff review
- formal code/docs gates
- `merge-review-deep` and `merge-readiness-gate` on the exact committed head
- hosted GitHub Actions on the exact draft-PR head

Stop on unresolved contract, authority, privacy, score, duplicate, lineage,
data-model, source-of-truth, or acceptance conflict. Stop before destructive
work, external-memory integration, ready-for-review, merge, tag, Release,
deployment, activation, or promotion.
