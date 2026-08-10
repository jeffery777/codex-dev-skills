# Release Notes: v0.12.0

Status: draft release preparation; not released

v0.12.0 prepares Loop Engineering V3-A manual/CI evidence-to-proposal from
Issue #133. Publication, tag, GitHub Release, deployment, activation, and
promotion are not part of the feature branch or draft PR.

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

The final release record must replace this draft status only after separately
authorized merge, exact tag, and GitHub Release evidence.

## Rollback

Review `./install.sh diff --all` before reinstalling. Rolling back removes the
V3-A module, CLI, reference, tests, evals, and docs but does not delete or
rewrite caller evidence/proposals, private data, Git/platform state, installed
runtime state, or external systems. V2d-A/B remain the functional fallback.

## Traceability

- Feature issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/133>
- Draft pull request: pending
- Compare: pending exact draft-PR head
