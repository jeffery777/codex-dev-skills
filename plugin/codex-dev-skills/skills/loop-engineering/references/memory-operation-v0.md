# Memory Operation V0 Portable Reference

Use this reference with `scripts/operationctl.py`.

`loop-memory-operation/v0` is downstream of unchanged `loop-memory/v1`. Its
four kinds are operation authority, trusted-time receipt,
authorized-operation request, and atomic execution receipt. Caller-owned
accepted authority/eligibility/trusted-time receipt digests are separate
inputs. Request validation reconstructs that complete chain; a standalone
resealed request cannot self-authorize.

The exact chain is V2b candidate -> eligibility -> caller authority -> request
-> future execution -> receipt -> independent acceptance. Receipt outcomes are
applied, idempotent replay, or failed. Success requires atomic state plus
receipt; replay cannot mutate twice; uncertainty is failure. V2b `delete` is
logical only and physical purge is unsupported.

```bash
./scripts/project-python <installed-loop-engineering>/scripts/operationctl.py --help
./scripts/project-python <installed-loop-engineering>/scripts/operationctl.py validate <authority.json>
./scripts/project-python <installed-loop-engineering>/scripts/operationctl.py authorize \
  <authority.json> <candidate.json> <eligibility.json> \
  --accepted-authority-receipts <accepted.json> \
  --accepted-eligibility-receipts <accepted.json> \
  --trusted-time <trusted-time.json> --accepted-trusted-time-receipts <accepted.json>
./scripts/project-python <installed-loop-engineering>/scripts/operationctl.py validate-request \
  <request.json> --authority <authority.json> --mutation-candidate <candidate.json> \
  --eligibility-receipt <eligibility.json> \
  --accepted-authority-receipts <accepted.json> \
  --accepted-eligibility-receipts <accepted.json> \
  --trusted-time <trusted-time.json> --accepted-trusted-time-receipts <accepted.json>
./scripts/project-python <installed-loop-engineering>/scripts/operationctl.py validate-receipt \
  <receipt.json> <request.json> --authority <authority.json> \
  --mutation-candidate <candidate.json> --eligibility-receipt <eligibility.json> \
  --accepted-authority-receipts <accepted.json> \
  --accepted-eligibility-receipts <accepted.json> \
  --trusted-time <trusted-time.json> --accepted-trusted-time-receipts <accepted.json>
```

All commands are offline validation/composition only. No backend exists, and
there is no SQLite/FTS5, database, persistence, provider/MCP, network,
promotion, or execution route.
