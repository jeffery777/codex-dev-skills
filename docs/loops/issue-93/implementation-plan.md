# Issue 93 Implementation Plan

## Baseline

- Repository: `jeffery777/codex-dev-skills`
- Default branch: `main`
- Starting revision: `f955f50dd0c8c05aa50f105551ea6b4bf6c55472`
- Working branch: `codex/issue-93-cost-aware-agent-routing`
- V1 owns workflow, ledger, protected authorization, review, and completion.
- V2a owns capability classification, custom-agent preflight, and agent
  receipts.
- V2b owns the optional external-memory trust contract and remains unchanged by
  model selection.

## Facts And Assumptions

Facts:

- the current registry contains four profiles and selects same-class candidates
  without a cost/capability tier;
- current runtime mappings are Terra low for exploration, Sol medium for the
  balanced worker, and Sol high for deep/security review;
- profile and route validation already bind exact model, reasoning, sandbox,
  digest, source revision, and workflow scope evidence;
- GitHub PR #92 is merged and is the branch baseline.

Assumptions to verify through tests:

- current Codex surfaces accept the documented GPT-5.6 model IDs and reasoning
  values when runtime facts report them;
- route contract version 1 can remain supported without weakening version 2
  tier validation;
- tier ordering is useful only as deterministic routing policy and must not be
  described as measured price or quality data.

## Complexity Classification

| Factor | Classification | Reason |
| --- | --- | --- |
| Ambiguity | high | Adds a second routing dimension and compatibility behavior. |
| Reasoning depth | deep | Class, tier, fallback, sandbox, and receipt invariants compose. |
| Code/context volume | large | Router, preflight, CLI, profiles, installer, tests, evals, and docs change. |
| Security/data/public-contract risk | public-contract | Alters a published routing and receipt contract. |
| Write blast radius | broad | Multiple maintained repository surfaces are affected. |
| Latency sensitivity | low | Contract correctness precedes delivery speed. |
| Cost/token sensitivity | high | Usage reduction is the objective but cannot override hard risks. |
| Independence | coupled | Contract changes must be integrated sequentially across shared schemas. |
| Verification burden | high | Backward compatibility, fallback, installer, and deterministic evals are required. |

The implementation remains in the current session because contract ownership
is coupled. Fresh read-only review may use a separate context later if the
runtime and repository policy permit it.

## Task Slices

### P1 — Versioned Routing And Tier Contract

- Add capability-tier constants, ranks, workload-kind validation, and version 2
  classification.
- Preserve version 1 exact-nine-factor behavior.
- Bind required and selected tier evidence into route receipts and integration
  validation.
- Replace alphabetical same-class choice with lowest sufficient tier choice.

Verification: focused routing unit tests, legacy receipt tests, and negative
unknown/downgrade/tamper cases.

### P2 — Profiles, Registry, And Preflight

- Add mechanical reader, advanced worker, and exceptional researcher profiles.
- Remap the balanced worker to Terra medium.
- Tighten the security reviewer instructions around defensive intent,
  local-first validation, non-invasive evidence, and explicit handling of
  safety-policy refusals without classifier evasion.
- Add tier/rank metadata to every registry entry and update source digests.
- Make preflight same-class fallback tier aware and preserve sandbox
  non-widening and collision behavior.

Verification: profile validator tests, runtime-fact matrices, exact-ID checks,
digest checks, and installer isolation tests.

### P3 — CLI, Templates, Evals, And Compatibility

- Accept route input versions 1 and 2 with strict per-version shapes.
- Carry class/tier capability facts through parent/default and sequential
  fallback.
- Expand deterministic evals for Luna/Terra/Sol selection, insufficient-tier
  rejection, cost-degraded higher-tier fallback, and exceptional human gates.
- Preserve V1/V2a no-profile and V2b memory-disabled/unavailable behavior.

Verification: `test_loopctl`, routing evals, Loop Engineering evals, and memory
contract regression tests.

### P4 — Installer And Documentation

- Add all profile sources to the opt-in installer group without changing
  `--all` behavior.
- Update model selection, runtime capability, delegation, README, examples,
  roadmap, and rollback guidance.
- Keep release version `0.6.1` and historical release notes unchanged on this
  feature branch.

Verification: installer install/update/diff/uninstall tests, repository
validation, documentation review, and public-hygiene scans.

### P5 — Review Closure And PR Readiness

- Run full validation and inspect `main...HEAD` plus the working-tree diff.
- Run deep code review and documentation review because the routing contract is
  public and release-sensitive.
- Run a security diff review focused on sandbox, fallback, untrusted runtime
  facts, path/digest validation, and false authority/completion.
- Close findings within the configured review-round limit and prepare a
  PR-readiness handoff.

Commit, push, PR creation, merge, tag, and release remain separate human gates.

## Verification Commands

```bash
git diff --check
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
python3 scripts/eval-agent-routing.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
```

Also verify deterministic profile selection, no lower-tier substitution,
version 1 compatibility, version 2 strict shapes, profile digest/source mapping,
installer rollback, no automatic global install, no unsupported cost claim,
and defensive local-only security instructions.

## Rollout And Rollback

Profiles remain explicit opt-in. Existing installed profiles are not changed by
editing this repository. A later installer update must show diffs and preserve
backups under the existing force-update rules. Roll back by uninstalling the
opt-in profile group or returning to version 1/no-profile routing; V1 and V2b
continue without custom-agent profiles.
