# P0 Inventory Worker Report

Status: complete (coordination evidence only; main-agent verification required).

Route: `loop_v2a_mechanical_reader`, tier `mechanical`, intended mapping
`gpt-5.6-luna` with low reasoning; runtime used same-tier parent/default
fallback (`degraded: true`, `cost_degraded: false`).

## Evidence Summary

- V2b authority/no-backend, repository identity, handshake, request/response,
  record, retrieval, write-candidate, extension, and future V2c boundaries were
  mapped to the normative docs and production Python implementation.
- The production adapter must remain separate from V2b core and call the
  existing validation/decision/conformance functions rather than weakening or
  duplicating them.
- V2b's adapter fingerprint covers handshake adapter/capability bytes, not
  extensions; the exact GitNexus driver fingerprint must therefore be bound in
  adapter/capability semantics.
- Mandatory adapter conformance is the exact nine-case oracle in
  `memory_contract.py`; the 31-case memory eval is a separate production
  behavior oracle. Neither inventory may be reduced or adapter-selected.
- Catalog/install copy the complete Loop Engineering skill directory, so a new
  production script is included without a backend-specific installer group.
- The tracked `.gitignore` lacked `.gitnexus/`; only machine-local Git exclude
  state ignored the index, which is not a portable public safety control.
- Proposed docs and verification surfaces were enumerated without editing.

## Commands Reported

- 46 focused V2b tests: PASS.
- 31-case V2b eval: PASS; all rates `1.0`, false authority/completion `0`.
- shell syntax, catalog/install mapping, `memoryctl --help`, and
  `git diff --check`: PASS.
- Full repository validation and live GitNexus analysis were intentionally
  skipped in this read-only packet.

## Risks And Questions

- A production `read_query` capability must remain unsupported unless an exact
  stable structured interface is qualified; human output cannot be parsed.
- Machine-local executable/index/registry paths and metadata `repoPath` must
  not enter receipts, docs, fixtures, or golden files.
- Fake adapters remain test-only; production conformance must preserve
  caller-owned evidence and the mandatory oracle.
