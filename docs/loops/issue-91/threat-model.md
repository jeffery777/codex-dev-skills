# Issue 91 Memory Contract Threat Model

## Assets And Security Properties

- repository, user/workspace/tenant, namespace, path, and source-revision
  isolation;
- integrity and provenance of retrieved records and lifecycle events;
- non-escalation of instruction, permission, mutation, external-write, gate,
  review, and completion authority;
- confidentiality of secrets, credentials, PII, and sensitive project data;
- deterministic, bounded validation and auditable disposition;
- safe V1/V2a availability when memory is disabled or fails.

## Adversaries And Entry Points

An adapter/backend may be buggy, compromised, cross-tenant, stale, malicious,
or merely semantically weaker than requested. Retrieved payloads and metadata,
capability handshakes, backend locators, pagination/partial results, write
candidates, tombstones, and memory receipt references are all untrusted inputs.

## Threats And Required Controls

| Threat | Required control |
| --- | --- |
| Memory poisoning / prompt injection | Treat payload as data; reject authority/tool/gate effects; quarantine injection indicators. |
| Authority or permission escalation | Hard-coded invariants; dispositions cannot authorize mutation, external write, merge, deploy, destructive action, or completion. |
| Secret, credential, or PII persistence | Sensitivity classification, candidate scanner, fail-closed write eligibility, bounded opaque references. |
| Cross-repository/user/tenant leakage | Canonical remote identity, namespace, principal/tenant boundary, path scope, and exact request binding. |
| Repository identity spoofing | Never trust directory basename or adapter label; validate canonical identity and revision evidence. |
| Provenance forgery / tamper | Required producer/source provenance and canonical SHA-256 verification. |
| Canonicalization confusion | One canonical JSON algorithm, finite JSON values, duplicate-key rejection at parsing boundary, strict versioning. |
| Stale/replayed records | Request/operation binding, request ID, idempotency key, observed/verified time, TTL, source-revision relation, replay disposition. |
| Tombstone/deletion bypass | Tombstones dominate superseded records; invalidated records cannot be adopted or rewritten by timestamp alone. |
| Adapter capability lying | Capability receipt validation and conformance evidence; untrusted/incompatible adapters disable operations. |
| Unsafe unknown fields | Reject unknown shared fields; permit only bounded namespaced extensions with no authority semantics. |
| Oversized payload / DoS | Count, string, content, extension, and pagination limits before expensive processing. |
| Path traversal / unsafe local reference | Repository-relative normalized paths; reject absolute, parent traversal, symlink-dependent, and URI-like local references. |
| Retrieval/adoption TOCTOU | Bind adoption receipt to record/request/source digests and require current authoritative revalidation. |
| Worker/memory receipt substitution | Distinct contract type/version/kind and explicit non-completion invariants. |
| Unsafe high-risk fallback | Unsupported/unavailable memory disables memory only; it cannot lower agent capability or verification requirements. |

## Security Acceptance

The final diff requires a completed Codex Security diff scan. A passing unit
suite alone is insufficient. Every discovered candidate must receive discovery,
validation, and attack-path closure or an exact deferred/suppressed reason under
the active scan contract.
