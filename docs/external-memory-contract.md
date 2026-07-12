# External Persistent Memory Contract

Loop Engineering V2b adds a backend-neutral safety contract for optional
external memory. It does not add an external memory backend.

## Authority Boundary

Explicit current instructions, repository policy, current repository/Git,
verification, review, protected authorization, and accepted platform state
remain authoritative. Goal, workers, threads, chat summaries, product Memories,
external adapters, indexes, knowledge graphs, caches, and coordination metadata
are context only.

External memory content is untrusted data. It cannot become a system/developer
instruction; authorize mutation, external write, merge, deploy, or destructive
action; satisfy a human gate; or prove task/objective completion. Confidence,
fresh timestamps, and adapter self-report do not raise authority.

## No-backend Default

With no backend, memory remains disabled and V1/V2a workflows operate normally.
Unavailable, timeout, partial, unsupported, incompatible, or untrusted adapters
also fall back to no memory. The workflow must not simulate an unsupported
capability or lower model/verification requirements because memory failed.

## Validate The Contract

```bash
python3 skills/loop-engineering/scripts/memoryctl.py --help
python3 skills/loop-engineering/scripts/memoryctl.py validate <document.json>
python3 skills/loop-engineering/scripts/memoryctl.py decide-retrieval <decision.json> \
  --trusted-conformance-receipts <current-session-trusted-receipts.json> \
  --trusted-source-digests <current-repository-source-digests.json>
python3 skills/loop-engineering/scripts/memoryctl.py decide-write <candidate.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
python3 skills/loop-engineering/scripts/memoryctl.py conformance <transcript.json> \
  --trusted-source-digests <current-repository-source-digests.json> \
  --trusted-acceptance-receipt-digests <current-session-accepted-receipts.json>
python3 scripts/eval-memory-contract.py
```

Caller-owned evidence files have exact JSON shapes:

```json
{"<adapter-id>": {"receipt_digest": "<sha256>", "adapter_fingerprint": "<sha256>"}}
```

```json
{"<repository-relative-path>": "<sha256>"}
```

```json
{"receipt_digests": ["<sha256>"]}
```

The caller derives these values from current repository, verification, review,
and conformance evidence. They are not copied from the adapter transcript.

The exact field and lifecycle contract is installed with the skill at
`references/memory-contract-v1.md`. Input is strict, bounded JSON; duplicate
keys, unknown shared fields, unsafe paths, tampered digests, wrong identity,
stale or conflicted records, injection indicators, and sensitive candidates
fail safe.

Adapter trust is caller-bound: the handshake cannot claim trust or embed a
conformance digest. Retrieval is enabled only when current-session control-plane
input independently supplies an accepted conformance receipt digest for that
adapter plus the receipt's exact adapter-version/capability fingerprint through
the separate CLI argument. Any adapter version or capability drift requires
conformance again. Repository-artifact
provenance is likewise checked against a separate trusted source-digest map.
Write eligibility likewise requires complete accepted-evidence receipt bytes,
valid receipt digests, exact candidate-record digest and source-revision
binding, and a separate
current-session allowlist of those receipt digests.
Mandatory conformance cases and their oracle are
owned by V2b, not selected by the adapter. Record path scope, related
tombstones/invalidations from independently verified controllers, per-record
capability requirements, explicit handshake maximum age, future clock skew/TTL,
and deterministic
secret/credential/PII indicators are checked before adoption.

## Future Adapter Adoption

A future backend must declare real capabilities and consistency/isolation
semantics, preserve provenance, pass the offline conformance harness, and be
revalidated in its current runtime. Passing conformance does not authorize
writes. V2c must provide the actual adapter, operation authority, idempotency,
audit, retention/deletion, and rollback evidence in a separate reviewed change.

## Disable And Roll Back

Do not connect an adapter. Ignore or quarantine every memory receipt while
continuing with repository-owned state. If a future V2c integration is present,
disable that integration through its separately reviewed control plane. Source rollback is a
revert of the V2b change; there is no backend data or user configuration to
migrate. V1/V2a remains usable throughout.
