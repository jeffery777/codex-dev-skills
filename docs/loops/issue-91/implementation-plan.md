# Issue 91 Implementation Plan

## Baseline

- Repository: `jeffery777/codex-dev-skills`
- Default branch: `main`
- Starting revision: `a213f7a0039bc87e1bff662b55e5464e353dc71b` (`v0.6.1`)
- Working branch: `codex/loop-engineering-v2b-memory-contract`
- V1 owns workflow, ledger, protected authorization, review, and completion.
- V2a owns capability routing, profile preflight, and agent receipts.
- V2b adds an optional memory trust/validation contract without a backend.

## Overall Complexity

| Factor | Classification | Reason |
| --- | --- | --- |
| Ambiguity | high | New cross-module contract with future adapter evolution. |
| Reasoning depth | deep | Authority, identity, canonicalization, freshness, conflict, and lifecycle compose. |
| Code/context volume | large | Core, CLI, schemas, fixtures, tests, evals, packaging, and docs. |
| Security/data/public-contract risk | security | Defines a future backend trust boundary and poisoning/injection controls. |
| Write blast radius | broad | Multiple repository surfaces, though no repo-external or backend writes. |
| Latency sensitivity | low | Correctness and evidence take priority. |
| Cost/token sensitivity | low | No cost-driven capability downgrade is allowed. |
| Independence | bounded | Discovery, implementation, and review packets can be disjoint; integration is coupled. |
| Verification burden | high | Adversarial matrices, formal review, security scan, and readiness gate. |

Production class: `security-reviewer` from the non-compensatory security hard
trigger. The main agent retains end-to-end ownership.

## Task Packets

### P1 — Contract And Production Core

- Owned category: memory schemas, canonicalization/digest, validation, lifecycle
  decisions, receipts, and CLI commands under the installable loop skill.
- Acceptance: strict versioned contracts; deterministic validation and decision;
  no backend/network/persistence imports; bounded inputs and safe errors.
- Verification: focused memory-contract unit tests, schema/digest/tamper/replay
  matrices, and CLI negative tests.
- Route: bounded implementation packet, analyzed before delegation. If the
  writable custom profile cannot be proven active, execute sequentially.

### P2 — Conformance, Tests, And Evals

- Owned category: test-only adapter harness, fixtures, unit tests, V2b eval suite,
  metrics, and V1/V2a no-memory regression coverage.
- Acceptance: requested normal/degraded/attack cases; zero false authority or
  completion; deterministic outputs; fake adapter excluded from production.
- Verification: focused tests, V2b eval, Loop Engineering eval, V2a routing eval.

### P3 — Packaging, Templates, And Documentation

- Owned category: catalog/installer/source mapping, templates, README, roadmap,
  loop/ledger/runtime/usage docs, examples, rollout/rollback, and V2c follow-up.
- Acceptance: optional/no-backend behavior is the default; no global config
  changes; test-only adapter cannot be installed as a backend.
- Verification: repository validation, installer/source mapping tests, link and
  public-hygiene scans, formal documentation review.

### P4 — Fresh Formal Review And Security

- Owned category: read-only final diff review and security scan artifacts.
- Acceptance: fresh context separate from implementation; every finding has a
  durable disposition; security scan phases and coverage ledgers finalize.
- Route: deep-reviewer for code/public contract and security-reviewer for the
  security scan. No downgrade below capable parent/sequential execution.

### P5 — Publication To Human Gate

- Owned by the main agent: final verification/readback, commit, push, ready PR,
  issue linkage, deep merge review, merge-readiness evidence, and stop without
  merge.

## Verification Strategy

```bash
git diff --check
bash -n install.sh
bash -n scripts/validate-repo.sh
python3 scripts/validate-agent-profiles.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-agent-routing.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
./scripts/validate-repo.sh
```

Also verify schema canonicalization/digest/tamper, identity/freshness/conflict,
write eligibility, test-only adapter isolation, installer/catalog mapping,
docs links/examples/runtime compatibility, and scan for secrets, credentials,
PII placeholders, machine-local paths, and private runtime state.

## Review And Closure Plan

- `code-review-deep` through `code-review-gate` for production and packaging.
- `docs-review` through `docs-review-gate` for public contract claims.
- `codex-security:security-diff-scan` on the validated final diff.
- `merge-review-deep` and `merge-readiness-gate` after finding closure.
- Fix every MUST-FIX. Fix safe in-scope SHOULD-FIX/NIT findings; otherwise add
  a durable owner, target, reason, residual risk, verification, and promotion
  trigger before rerunning the applicable review.

## Rollout And Rollback

Rollout is optional and backend-free: install/update the delivery workflow,
validate schemas/fixtures, and leave memory disabled unless a future adapter
passes conformance. Roll back by disabling/ignoring the memory path or reverting
the V2b commit; V1/V2a continue without a backend. No user configuration or
external memory data is mutated by this work.

## Durable V2c Follow-up

Owner: future Loop Engineering backend integration issue.

Promotion trigger: a concrete backend is proposed with documented repository
identity, namespace isolation, consistency, idempotency, provenance,
sensitivity, retention/deletion, and audit semantics and passes every mandatory
V2b conformance case. V2c may then implement one adapter without weakening V2b
authority or fallback rules.
