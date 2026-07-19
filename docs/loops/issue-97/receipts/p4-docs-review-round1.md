# P4 Documentation Review — Round 1

Gate result: **BLOCKED**. This is read-only review evidence.

## MUST-FIX

- `MF-DOC-001`: the durable ledger and spec digest were stale; repository
  validation failed and task/qualification state contradicted current evidence.
- `MF-DOC-002`: the documented qualify/status/enable/refresh/disable workflow
  had no supported executable operator interface.
- `MF-DOC-003`: documents conflated the live qualification evidence-bundle
  digest with the production runtime adapter fingerprint.

## SHOULD-FIX / NIT

- `SF-DOC-001`: add `unsupported` to the release readiness state checklist.
- `SF-DOC-002`: clarify that the mandatory V2b oracle is backend-neutral
  regression evidence; this adapter does not earn read/write authority.
- `NIT-DOC-001`: use the consistent `macOS arm64 live qualification` label.

The reviewer confirmed that default-disabled behavior, unsupported query/write
capabilities, safe index-only refresh, no-backend rollback, Linux fixture-only
scope, and V2c-B follow-up were otherwise documented. No files were modified by
the reviewer.
