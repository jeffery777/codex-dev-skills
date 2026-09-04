# Memory Operation Contract V0

`loop-memory-operation/v0` is the provider-neutral Memory M0 contract for one
caller-authorized future memory operation. It adds no backend and does not
change `loop-memory/v1`.

## Artifact Chain And Authority

```text
V2b mutation candidate -> eligibility receipt -> caller-owned operation authority
  -> authorized-operation request -> future adapter execution
  -> atomic execution receipt -> independent acceptance/promotion
```

The family has four kinds: `operation-authority`, `trusted-time-receipt`,
`authorized-operation-request`, and `execution-receipt`. The caller supplies
accepted authority-, eligibility-, and trusted-time-receipt digest sets
separately. Request and receipt validation reconstruct the complete external
evidence chain; a standalone resealed request is never authorization.

Authority is exact-operation-only. It binds repository/principal/namespace/
revision/path, operation/target/candidate/idempotency, expiry/nonce,
eligibility, trusted observation time, adapter/schema/capability, and approved state-root identity. It
does not authorize unrelated external writes, completion, acceptance,
promotion, merge, release, deploy, or activation.

## Execution Receipts

An execution receipt is `applied`, `idempotent-replay`, or `failed`.
`applied` requires one atomic state-plus-receipt commit. Replay binds the
original applied receipt and performs no second mutation. Timeout, lock, disk,
integrity, schema, fingerprint, transaction, or commit uncertainty is failed
and cannot claim partial success.

M0 validates receipt structure; it does not prove a real adapter or transaction
exists. M1 must qualify the executor independently.

## Lifecycle, Placement, And Privacy

V2b `delete` has the M0 lifecycle effect `logical-delete`. Physical purge is
unsupported. Schema mismatch fails closed and automatic migration/repair is
absent. Future M1 is single-host local/manual/CI only and uses an explicitly
approved machine-local state root outside public Git.

Only public/internal structured records are eligible. Secrets, credentials,
PII, private paths, raw chats/sessions/logs, and unredacted machine config are
excluded. M0 makes no encryption-at-rest or shared-host confidentiality claim.

## Offline CLI

```bash
./scripts/project-python skills/loop-engineering/scripts/operationctl.py validate <authority.json>
./scripts/project-python skills/loop-engineering/scripts/operationctl.py authorize \
  <authority.json> <mutation-candidate.json> <eligibility-receipt.json> \
  --accepted-authority-receipts <accepted-authority.json> \
  --accepted-eligibility-receipts <accepted-eligibility.json> \
  --trusted-time <trusted-time-receipt.json> \
  --accepted-trusted-time-receipts <accepted-time.json> \
  [--expected-pre-state-digest <sha256>]
./scripts/project-python skills/loop-engineering/scripts/operationctl.py validate-receipt \
  <execution-receipt.json> <authorized-request.json> \
  --authority <authority.json> --mutation-candidate <candidate.json> \
  --eligibility-receipt <eligibility.json> \
  --accepted-authority-receipts <accepted-authority.json> \
  --accepted-eligibility-receipts <accepted-eligibility.json> \
  --trusted-time <trusted-time-receipt.json> \
  --accepted-trusted-time-receipts <accepted-time.json> \
  [--original-applied-receipt <receipt.json>]
```

`validate-request` uses the same caller-owned arguments as `validate-receipt`.
The accepted receipt files have exactly
`{"receipt_digests":["<sha256>"]}`. Commands read only explicit bounded regular
non-symlink files and emit canonical stdout or generic stderr. There is no
execute, backend, database, provider, network, platform, or mutation route.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 ./scripts/project-python -m unittest \
  tests.test_memory_operation tests.test_operationctl tests.test_eval_memory_operation
./scripts/project-python scripts/eval-memory-operation.py
```

Passing is conformance evidence only. This contract is included in
**v0.14.0** and does not authorize a backend or operation.

The v0.23.0 thin local pilot does not relax this chain: explicit remember and
logical invalidate require the same complete accepted eligibility, exact
authority, trusted time, identity, and pre-state bindings before M1 is opened.
The profile cannot mint, infer, or reuse authority.
