# Release Notes: v0.13.0

Release date: 2026-08-12

v0.13.0 publishes Loop Engineering V3-B isolated candidate evaluation from
Issue #141 / PR #142. It adds a strict offline evaluation family downstream of
the unchanged V2d-A, V2d-B, V3-A, and V2b contracts. Issue #143 owns the
separate release closure.

## Isolated Candidate Evaluation

- Added strict `loop-candidate-evaluation/v0` input, evaluation-result,
  independent-verification-result, and promotion-packet kinds.
- Added a closed synthetic evaluator for bounded baseline and candidate
  observations under one fixed policy, identical scenarios and limits, exact
  public environment equivalence, and integer-only acceptance thresholds.
- Added deterministic independent replay and input-permutation equivalence.
- Added explicit fail-closed outcomes for invalid baseline evidence,
  environment mismatch, regression, timeout, resource bound, interruption,
  uncertainty, verification failure, and tampered or incomplete V3-A/V2d
  lineage.
- Added stdout-only `evaluationctl.py` routes for evaluate, verify, packet, and
  packet validation. The CLI cannot execute arbitrary candidate code or apply,
  commit, push, create a PR, approve, merge, release, deploy, activate,
  promote, or write externally.

## Advisory Context, Privacy, And Authority

- `memory-off` is the default complete path.
- The optional provider-neutral seam accepts only complete explicit context
  paired with the existing V2b production retrieval decision, trusted
  conformance receipts, and trusted repository-source digests.
- Accepted synthetic advisory context is digest-bound data only. Missing,
  partial, stale, untrusted, sensitive, conflicting, unsupported, or invalid
  context falls back to `memory-off` without changing evaluation semantics.
- Evaluation, verification, and packet outputs preserve false authorization,
  completion, external-write, and promotion invariants. The independent
  human/platform promotion gate remains required and pending.
- Public fixtures are synthetic. Private evidence, raw chats/sessions/logs,
  credentials, PII, host/user identity, private paths/configuration, runtime
  databases, and real evaluation records remain outside public Git.

## Qualification

- Added 26-case deterministic evaluation coverage for the required pass,
  regression, baseline, verification, environment, lineage, replay, authority,
  memory, context, execution-bound, manual/CI, and packet scenarios.
- Added focused production, CLI, contract-document, fixture, and eval tests.
- The reviewed V3-B head passed 864 repository tests, repository validation,
  installer/package checks, routine/deep/docs/security/privacy review, and
  exact-head hosted CI before merge.

## Boundaries And Next Stage

This release does not add SQLite, FTS5, a Memory M1/M2 backend, PlugMem, Mem0,
a provider or MCP adapter, automatic recall/write, resident hooks, a scheduler,
controller, daemon, queue, V3-C, deployment, activation, or promotion. The next
roadmap stage is a separately scoped M1 readiness/spec/ADR/security decision;
it is not authorized or implemented by this release.

## Verification

```bash
./scripts/project-python -c 'import sys, yaml; print(sys.executable); print(sys.version.split()[0]); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest discover -s tests -p 'test_*.py'
./scripts/project-python scripts/eval-candidate-evaluation.py
./scripts/validate-repo.sh
./install.sh manifest
git diff --check
```

The annotated `v0.13.0` tag and non-draft, non-prerelease GitHub Release are
bound to the exact reviewed Issue #143 release-closure merge commit. Release
publication does not approve or promote an evaluated candidate and does not
authorize Memory M1/M2 or V3-C.

## Rollback

Review `./install.sh diff --all` before reinstalling. Rolling back to v0.12.1
removes the public V3-B evaluator, CLI, reference, tests, evals, and docs but
does not delete or rewrite evaluation inputs/results, private data, Git or
platform state, installed runtime state, or external systems. V3-A remains the
released proposal-only fallback.

## Traceability

- V3-B feature issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/141>
- V3-B feature pull request:
  <https://github.com/jeffery777/codex-dev-skills/pull/142>
- Release closure issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/143>
- Release pull request:
  <https://github.com/jeffery777/codex-dev-skills/pull/144>
- Compare:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.12.1...v0.13.0>
