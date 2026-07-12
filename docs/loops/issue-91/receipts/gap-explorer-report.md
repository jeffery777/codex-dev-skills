# V2b Gap Explorer Report

Task: `issue-91-gap-explorer`

Route receipt: `0d95914b9be9345a2ce5b679dbaa86c1ae37c5973d6684e6b57891c74a064e16`

Status: complete (coordination evidence only)

## Evidence And Recommendations

- Existing canonical/digest behavior is deterministic compact sorted JSON in
  `agent_routing.py` and `loop_core.py`; V2b must use one explicit algorithm and
  must not claim RFC 8785/JCS compatibility without proof.
- V2a already binds non-escalation invariants and keeps worker output as
  coordination-only evidence. Memory receipts should remain a separate typed
  contract referenced by digest and must not enter route/completion fields.
- `loopctl.py` is strict and fail-closed, but a standalone thin `memoryctl.py`
  avoids unnecessary V2a receipt-version churn while remaining installable.
- The existing ledger `external_memory` field is an unvalidated prose stub. Its
  authority wording should become explicit advisory-only/no-authorization.
- `install.sh` copies the entire `skills/loop-engineering` tree. Production code
  and schemas may live there without a new catalog leaf; fake adapters must stay
  under `tests/` so they cannot become installed production backends.
- Add a dedicated memory eval runner and repository-validation hook. Do not
  overload V2a routing metrics.
- Validate identity/integrity/authority before timestamp/confidence. Wrong
  repository or principal, tamper, tombstone, replay, conflict, or untrusted
  adapter must reject or quarantine; partial/unknown freshness must not adopt.
- Repository identity should combine a trusted-caller canonical opaque id and
  human-readable canonical remote, plus namespace, principal digests, source
  revision, and path scope. The adapter must not derive the trusted identity.
- Prefer strict stdlib executable validation plus normative JSON schemas and
  parity tests, avoiding a new runtime dependency.

## Verification Reported By Worker

- 79 V2a/CLI unit tests passed.
- Agent routing eval passed 17/17.
- Assigned route receipt validated with no issues.
- `git diff --check` passed.

## Risks

- Duplicated canonicalization can cause digest confusion.
- A test adapter inside the skill tree would be shipped as a backend.
- Fresh timestamps can mask poisoned or wrong-identity records if validation
  ordering is wrong.
- Changing route receipt schema is unnecessary and would invalidate V2a
  fixtures and durable receipts.

Conflicts: none.
