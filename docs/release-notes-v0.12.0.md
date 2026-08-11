# Release Notes: v0.12.0

Release date: 2026-08-11

v0.12.0 introduces Loop Engineering V3-A manual/CI evidence-to-proposal from
Issue #133 / PR #134. It also publishes the Issue #135 / PR #136 planning-only
roadmap that keeps V3-B isolated candidate evaluation, Agent Memory, and V3-C
automation behind later evidence and human gates.

## Evidence-To-Proposal

- Added strict `loop-improvement-proposal/v0` proposal-set generation and
  regeneration validation downstream of unchanged V2d-A/B contracts.
- Added fixed integer-only scoring, stable ties, structured duplicate
  suppression, bounded hypotheses, and description-only patch/branch/artifact/
  draft-PR intents.
- Preserved complete run/failure/environment/artifact/baseline/improvement
  lineage and proposer/evaluator/independent-verifier/promoter separation.
- Added exact proposal-only and false-authority/action fields plus a required
  pending independent human/platform promotion gate.
- Added explicit-file, stdout-only `proposalctl.py` with no apply, Git,
  platform, network, scheduler, service, database, or write operation.

## Evaluation And Privacy

- Added production-backed synthetic positive and 17-case adversarial evals for
  false completion, wrong route, unauthorized action, evidence completeness,
  recovery, manual/CI equivalence, score/tie/deduplication determinism,
  tamper/mismatched lineage, private paths, host/user fields, tokens, PII, and
  raw logs.
- Exact thresholds require every positive rate to be 1.0 and every false
  authority/action/promotion outcome to be zero.
- Real/private evidence and proposals remain outside public Git. PlugMem,
  Mem0, and every external-memory backend remain excluded and disabled.

## Roadmap And Authority Boundary

- V3-B remains unimplemented and must begin through a separate Issue/spec only
  after current release evidence is independently reverified.
- Memory M0 remains readiness design/qualification only. No SQLite/FTS5,
  provider, MCP adapter, database, schema, migration, or runtime was added.
- M1 remains default-disabled future qualification after V3-B evidence; M2 and
  V3-C remain behind later decisions.
- Proposal, evaluation, verification, merge, tag, and Release evidence cannot
  activate, promote, deploy, or authorize later phases.

## Verification

```bash
python3 -c 'import sys, yaml; print(sys.executable); print(yaml.__version__)'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/eval-improvement-proposal.py
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-improvement-lineage.py
./scripts/validate-repo.sh
git diff --check
```

The annotated tag and GitHub Release are bound to the exact reviewed Issue
#137 release-closure merge commit. Release publication does not activate or
promote V3-A output and does not authorize V3-B or Agent Memory implementation.

## Rollback

Review `./install.sh diff --all` before reinstalling. Rolling back removes the
V3-A module, CLI, reference, tests, evals, and docs but does not delete or
rewrite caller evidence/proposals, private data, Git/platform state, installed
runtime state, or external systems. V2d-A/B remain the functional fallback.

## Traceability

- Feature issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/133>
- Feature pull request:
  <https://github.com/jeffery777/codex-dev-skills/pull/134>
- Planning-only roadmap issue and pull request:
  <https://github.com/jeffery777/codex-dev-skills/issues/135>
  <https://github.com/jeffery777/codex-dev-skills/pull/136>
- Release closure issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/137>
- Release pull request:
  <https://github.com/jeffery777/codex-dev-skills/pull/138>
- Compare:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.11.1...v0.12.0>
