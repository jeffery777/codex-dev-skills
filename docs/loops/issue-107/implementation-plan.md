# Issue #107 Implementation Plan

## Objective

Close the v0.9.1 alignment gap, prove a bounded live V2c-B notify-only adoption,
and leave durable handoff material for the Operational Evidence program.

## Facts

- V2c-B shipped in v0.9.0 from Issue #103.
- README still calls V2b the current development milestone.
- The repository ships inactive V2c-B hook/config templates and a strict
  validator, but v0.9.0 did not include a live active project-hook run.
- The current GitNexus index is derived and ignored, and hook output has no
  authorization, review, gate, mutation, or completion authority.
- The working tree contains a pre-existing local `AGENTS.md` modification. It
  remains outside Issue #107 and must not be staged or overwritten.
- The supplied research report is useful design input but contains ephemeral
  research citation identifiers and is not a durable repository authority.

## Task Slices

### P0 — Contract And Program Records

- Create the Issue #107 loop spec, plan, and task manifest.
- Add a canonical Operational Evidence program directory.
- Record architecture decisions, implementation stages, re-entry gates, and a
  continuation handoff.
- Mark the raw research report as superseded input rather than copying it.

### P1 — Public v0.9.1 Alignment

- Update README's released milestone statement.
- Add v0.9.1 release notes.
- Update roadmap sequencing to place V2d before V3-A.
- Link the durable program plan from the roadmap and release notes.

### P2 — Live Notify-Only Adoption

- Resolve and bind the existing qualified GitNexus 1.6.9 runtime using
  machine-local values only.
- Materialize a secure local config outside the repository.
- Materialize an untracked project `.codex/hooks.json` only after confirming no
  existing file would be overwritten.
- Validate the config with the shipped hook runner.
- Review/trust the exact hook definition through the supported Codex flow.
- Observe supported `SessionStart` and/or `PostToolUse` behavior.
- Record only sanitized results and explicitly state coverage limits.

### P3 — Verification And Review Closure

- Run focused V2c-B and V2c-A tests.
- Run repository validation and diff hygiene checks.
- Inspect tracked and untracked state for accidental private material.
- Run docs review and the formal docs review gate.
- Fix findings within two closure rounds.
- Prepare publication readiness evidence and stop at the required publication
  gate if exact authorization is absent.

## Research Report Disposition

The source file with the working name `deep-research-report (6).md` will not be
copied into the public repository. Its useful conclusions are normalized into
the program documents in `docs/programs/operational-evidence/`.

Reasons:

- its `turn...` citation identifiers cannot be resolved by future readers;
- it mixes repository facts, research inference, and proposed scope;
- its draft issue proposal has been refined by the subsequent repository
  reassessment;
- a canonical decision record is smaller, reviewable, and easier to maintain.

The report remains research context only. It does not prove architecture,
authorization, or completion.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Active config leaks private paths or runtime data | Keep it outside Git; scan the final diff and untracked files. |
| Notify-only is mistaken for automatic maintenance | State that it never refreshes and collect only advisory evidence. |
| Hook trust is bypassed | Use normal project-layer trust review; do not use bypass flags. |
| Current dirty `AGENTS.md` contaminates the patch | Preserve it unchanged and exclude it from staging/review scope. |
| Research draft becomes a hidden authority | Supersede it with named accepted decision records. |
| V2d scope leaks into v0.9.1 | Document future stages only; do not add contracts, validators, or runtime services. |

## Verification

```bash
python3 --version
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_hook
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_gitnexus_adapter
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

## Review Plan

- Primitive: `docs-review`
- Formal gate: `docs-review-gate`
- Final release-sensitive comparison: `merge-review-deep` for `main..HEAD`
- Maximum review closure rounds: two

## Rollback

- Disable or remove the untracked project hook definition.
- Leave derived indexes and unrelated user work unchanged.
- Remove the machine-local config only through a separate exact-target cleanup
  decision.
- Revert the tracked docs patch independently if publication is rejected.
