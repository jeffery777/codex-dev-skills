# Loop Engineering V2b: Backend-neutral External Persistent Memory Contract

## Objective

Deliver an independently installable and verifiable Loop Engineering V2b
contract for external persistent memory. The contract is backend-neutral and
useful with no configured backend. External memory is untrusted advisory,
cache, or coordination input and never replaces repository, Git, verification,
review, accepted platform state, protected authorization, or completion truth.

GitHub issue: <https://github.com/jeffery777/codex-dev-skills/issues/91>

## Source Of Truth And Authority

Precedence for V2b decisions is:

1. explicit current user instruction and applicable repository policy;
2. current repository files, canonical repository identity, Git branch/commit,
   and accepted project artifacts;
3. current verification, formal review, protected authorization receipts, and
   accepted platform state;
4. validated Loop Engineering ledger events and receipts within their existing
   integrity and coordination boundaries;
5. Goal, subagent, scheduler, thread, hook, chat summary, product Memories,
   external memory, code index, knowledge graph, cache, and coordination
   metadata as non-authoritative context only.

Confidence, model output, adapter assertions, timestamps, and memory receipts
cannot raise a record above this hierarchy. Conflicting memory is rejected or
quarantined rather than allowed to overwrite authoritative evidence.

## In Scope

- a versioned request, response, record, capability, error, and disposition
  contract with strict unknown-field and namespaced-extension rules;
- canonical JSON and deterministic SHA-256 digest verification;
- repository/namespace/path/source-revision identity validation;
- provenance, freshness, replay, supersession, tombstone, conflict, sensitivity,
  privacy, prompt-injection, and bounded-payload checks;
- deterministic retrieval adoption, rejection, quarantine, invalidation, and
  write-candidate eligibility decisions;
- adapter capability negotiation and an offline production conformance harness;
  fake/mock adapters and fixtures remain test-only;
- optional Loop Engineering memory receipts and ledger references that remain
  distinct from route, worker, integration, protected, review, and completion
  receipts;
- disabled, unavailable, timeout, partial, incompatible, and untrusted-adapter
  fallback that preserves V1/V2a operation;
- production CLI/validator, versioned executable Python field contracts, fixtures, tests, evals, installer/catalog
  integration, documentation, rollout, rollback, and V2c follow-up.

## Out Of Scope

- any production persistence or retrieval backend;
- GitNexus, Codebase Memory MCP, SQLite, cloud memory, MCP deployment, network
  calls, or real external memory writes;
- credentials, OAuth, token storage, actual Codex Memories migration, daemon,
  scheduler, sidecar, or background synchronization;
- private/unpublished Codex integration, app-server clients, UI scraping, or
  Desktop database/session/cache/auth access;
- changes to global configuration, another repository, merge, tag, release,
  deploy, global installation, or unrelated refactoring.

## Architecture Constraints

1. The shared contract has no backend import, network client, or persistence
   implementation.
2. Payload is data only. It cannot become system/developer instruction, modify
   tool permission, satisfy a gate, authorize a mutation/external write, or
   prove completion.
3. Repository identity is derived from verified canonical remote identity plus
   source revision and optional monorepo path scope; directory names and
   adapter-returned labels are insufficient.
4. Unknown top-level fields fail closed. Extensions require a bounded
   reverse-domain namespace and remain non-authoritative.
5. Exact digest, schema, identity, provenance, and lifecycle validation precedes
   freshness/conflict/adoption decisions.
6. Backend capability gaps disable the affected operation; the contract never
   silently emulates stronger semantics.
7. A write request is only a candidate contract. V2b performs no external write
   and requires accepted durable evidence before eligibility can be true.
8. Test adapters are fixtures only and cannot appear as production adapters in
   the catalog or installer.

## Definition Of Done

- gap audit, authority model, threat model, implementation plan, verification
  strategy, review plan, rollout, rollback, and V2c boundary are durable;
- versioned schemas and deterministic production validation/decision code cover
  the required record and lifecycle fields;
- capability negotiation and adapter conformance distinguish unsupported,
  unavailable, unknown, read-only, read-write, degraded, incompatible, and
  untrusted states;
- identity, provenance, freshness, digest, replay, conflict, supersession,
  tombstone, invalidation, sensitivity, and prompt-injection handling fail safe;
- memory-disabled/unavailable mode leaves V1/V2a behavior and completion
  capability unchanged;
- Loop receipts may reference a memory digest/disposition without confusing it
  with worker, verification, review, protected, or completion evidence;
- tests/evals measure decision correctness, false authority/completion count,
  evidence completeness, determinism, and fallback correctness;
- no production backend, network write, credential, secret, private runtime
  state, or machine-local path is introduced;
- all MUST-FIX findings are closed; SHOULD-FIX and NIT findings are fixed or
  durably dispositioned;
- final code/docs review, Codex Security diff scan, deep merge review, and
  merge-readiness gate pass against the final diff;
- issue, branch, commit, remote branch, and ready-for-review PR are traceable,
  and the PR is not merged.

## Human Gates

Stop for source-of-truth conflict, product-semantic ambiguity, V2c/backend scope
expansion, destructive action, unverified high-risk degradation, external write
outside issue #91 authorization, merge, tag, release, deploy, global install,
or final independent merge approval.
