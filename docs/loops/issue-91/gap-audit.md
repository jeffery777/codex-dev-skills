# Issue 91 Gap And Authority Audit

## Verified Baseline

- `main@a213f7a` is the accepted v0.6.1 baseline.
- V1 provides a repo-owned event ledger, protected authorization, completion
  guards, deterministic workflow decisions, Goal/subagent boundaries, and safe
  sequential fallback.
- V2a provides nine-factor capability classification, four reviewed profiles,
  current-runtime preflight, safe degradation, and route/worker/integration
  receipts.
- Existing docs already state that external memory is optional cache or
  coordination context and cannot replace repository completion truth.
- No V2b issue, branch, PR, production memory schema, adapter interface,
  validation command, conformance harness, test suite, or eval exists at the
  starting revision.

## Gaps

| Area | Current state | Required V2b closure |
| --- | --- | --- |
| Authority | Prose-only external-memory caveat | Executable, versioned non-authority invariants and dispositions. |
| Schema | No shared memory contract | Strict request/response/record/capability/error/receipt schemas. |
| Identity | Git identity exists for loop receipts | Canonical repository/namespace/path/revision binding for memory. |
| Integrity | Loop events and V2a receipts use digests | Memory-specific canonicalization, digest, replay, and tamper checks. |
| Freshness | No memory lifecycle | Exact/diverged/unknown revision, TTL, supersession, tombstone, conflict rules. |
| Injection | General instruction hierarchy only | Explicit payload-as-data validation and forbidden authority effects. |
| Privacy | Public-hygiene scans | Record/candidate sensitivity policy and secret/PII rejection. |
| Capability | V2a profile preflight only | Adapter capability handshake and conformance evidence. |
| Fallback | V1/V2a sequential fallback | Disabled/unavailable/partial/incompatible/untrusted memory fallback. |
| Integration | Ledger has a prose external-memory field | Typed optional memory receipt references kept separate from completion receipts. |
| Execution | No validator or CLI | Deterministic production validation/decision/conformance command surface. |
| Evidence | No tests/evals | Attack/degradation matrices and decision-quality metrics. |

## Trust Boundary

Untrusted side: adapter identity/capability claims, backend locators, retrieval
order, timestamps, confidence, content, extensions, provenance assertions, and
backend status. Trusted only after independent validation: schema version,
canonical digest, repository/namespace/path identity, source revision,
provenance references, sensitivity, lifecycle state, and operation binding.

Even a validated record remains advisory. Adoption means only “eligible to be
used as data context for this bounded operation.” It never means “instruction,”
“authorization,” “accepted evidence,” or “completion.”

## Architectural Decision

Add a self-contained `memory_contract.py` production module and CLI subcommands
beside the installed loop core, plus versioned executable Python field contracts
and an offline production conformance harness. Fake/mock adapters and fixtures
remain test-only. Keep the module free of backend imports. Integrate through optional
memory receipt summaries rather than changing protected ledger authority.
