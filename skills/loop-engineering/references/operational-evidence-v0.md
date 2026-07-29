# Loop Operational Evidence V0 Reference

Contract version: `loop-operational-evidence/v0`

Runtime compatibility: shared, offline, standard-library Python

## Envelope

Every document is one JSON object with exactly:

| Field | Contract |
| --- | --- |
| `contract_version` | Exact value `loop-operational-evidence/v0` |
| `kind` | `run-receipt`, `iteration-summary`, `failure-summary`, `environment-fingerprint`, or `artifact-reference-set` |
| `document_id` | Opaque identifier |
| `run_id` | Opaque identifier shared by the set |
| `objective_id` | Opaque identifier shared by the set |
| `source_revision` | Exact `repository_id` and 40-character lowercase Git `commit_sha` |
| `observed_at` | `YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)` |
| `producer` | Exact `kind` (`human`, `agent`, `tool`, or `ci`) and opaque `id` |
| `payload` | Exact kind-specific object |
| `authority_invariants` | Exact false-authority object below |
| `document_digest` | SHA-256 of canonical JSON with this field omitted |

Canonical JSON uses sorted ASCII object keys, compact separators, UTF-8,
JSON booleans/null, and bounded integers. Floating-point and non-finite values
are unsupported. Identifiers match
`[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`. Digests are 64 lowercase hexadecimal
characters. V0 has no extension field.

Timestamps require literal `T`, one to six optional fractional digits, and an
explicit `Z` or numeric timezone offset. Arbitrary separators and naive
timestamps are unsupported.

Bounds:

- encoded document: 131,072 bytes;
- supplied set: 256 documents;
- nesting depth: 32;
- string: 512 UTF-8 bytes unless a field is stricter;
- array: 256 items;
- integer: JSON safe range, plus kind-specific limits.

## Kind Payloads

### `run-receipt`

Exact fields:

- `started_at`, `ended_at`;
- `execution_mode`: `current-session`, `shared-subagents`,
  `sequential-fallback`, or `ci`;
- `outcome`: `work-recorded`, `stopped-failure`, `stopped-human-gate`, or
  `cancelled`;
- ordered unique `iteration_summaries` document references;
- one `environment_fingerprint` document reference;
- one `artifact_reference_set` document reference;
- unique `failure_summaries` document references;
- `verification_observation`: `not-run`, `passed`, `failed`, or `skipped`;
- `review_observation`: `not-required`, `required`, `passed`, or `blocked`;
- `human_gate_observation`: `not-required`, `pending`, or `satisfied`.

`work-recorded` means the receipt recorded the run; it does not mean the
objective completed.

### `iteration-summary`

Exact fields:

- `sequence`: integer `1..1,000,000`;
- `phase`: `bootstrap`, `planning`, `implementation`, `verification`,
  `review`, `integration`, or `release-preparation`;
- `result`: `continue`, `handoff-prepared`, `blocked-by-human-gate`, or
  `work-recorded`;
- nullable opaque `task_id`;
- `started_at`, `ended_at`;
- unique `artifact_ids`;
- unique digest-bound `failure_summaries`.

### `failure-summary`

Exact fields:

- nullable `iteration_sequence` in `1..1,000,000`;
- phase from the iteration phase enum;
- `category` and category-compatible `code`;
- `retry`: `never`, `manual`, `after-input`, or
  `after-environment-change`;
- unique `artifact_ids`.

Failure summaries contain no arbitrary message or raw exception. An iteration
owns digest references to its failures; a failure records the owner's sequence
without a digest reference back to the iteration, avoiding a content-digest
cycle.

| Category | Codes |
| --- | --- |
| `contract-validation` | `malformed-document`, `unsupported-version`, `unknown-field`, `duplicate-key`, `digest-mismatch`, `reference-mismatch` |
| `source-conflict` | `repository-mismatch`, `revision-mismatch`, `identity-conflict` |
| `authority-boundary` | `invariant-violation`, `authorization-required`, `completion-evidence-prohibited`, `promotion-prohibited` |
| `privacy-redaction` | `sensitive-data-detected`, `private-path-detected`, `raw-log-detected`, `prohibited-environment-field` |
| `capability` | `capability-unavailable`, `capability-unsupported` |
| `tooling` | `tool-failed`, `tool-output-invalid` |
| `verification` | `verification-failed`, `verification-skipped` |
| `review` | `review-blocked`, `review-incomplete` |
| `integration` | `worker-evidence-invalid`, `integration-rejected` |
| `resource-bound` | `timeout`, `size-limit`, `count-limit` |
| `external-action-gate` | `human-gate-pending`, `external-write-not-authorized` |
| `unclassified` | `unclassified` |

### `environment-fingerprint`

Exact allowlisted fields:

- `runtime_surface`: `codex-cli`, `codex-desktop`, `codex-ide`, `ci`, or
  `other`;
- `os_family`: `macos`, `linux`, `windows`, or `other`;
- `architecture`: `arm64`, `x86_64`, or `other`;
- `python`: exact integer `major` and `minor` in `0..99`;
- execution mode from the run enum;
- `sandbox_mode`: `read-only`, `workspace-write`, `danger-full-access`, or
  `unknown`;
- `redaction_applied: true`;
- `prohibited_fields_present: false`.

Do not retain usernames, hostnames, paths, emails, credentials, environment
variables, or machine configuration, including hashes of low-entropy private
identifiers.

### `artifact-reference-set`

The payload has only `artifacts`. Each artifact has exactly `artifact_id`,
`artifact_kind`, `locator_kind`, `locator`, `content_sha256`, and
`media_type`.

| Artifact kinds | Allowed locator |
| --- | --- |
| `loop-ledger`, `loop-event`, `route-receipt`, `worker-receipt`, `integration-receipt`, `memory-receipt`, `verification`, `review`, `other-public-artifact` | `repository-relative-path` |
| `git-commit` | `git-commit` |
| `platform-artifact` | `opaque-id` |
| `gitnexus-fingerprint` | `repository-relative-path` or `opaque-id` |

Media types are `application/json`, `application/yaml`, `text/markdown`, and
`text/plain`. Repository-relative paths are normalized POSIX paths without
absolute prefixes, empty/`.`/`..` components, backslashes, tildes, URL
schemes, or encoded traversal. Artifact ids and locator/digest pairs are
unique.

Validation does not dereference artifacts. Current-state consumers must
independently reread and revalidate them before any authoritative decision.

## Set Relationships

A valid set has:

- no more than 256 documents;
- consistent run, objective, repository, and source commit identity;
- unique document ids;
- exactly one run receipt, environment fingerprint, and artifact set;
- matching execution modes in the run receipt and referenced environment
  fingerprint;
- complete digest-resolved iteration and failure inventories;
- iteration sequences ordered and contiguous from one;
- exactly one matching iteration owner for every non-null failure sequence;
- no iteration owner for a run-level failure with a null sequence;
- artifact ids resolved against the artifact set.

## Authority

Every document contains exactly:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

Validation does not authenticate the producer, mutate state, satisfy a gate,
prove completion, authorize an external write, or authorize promotion.

## Privacy And Errors

Exact fields, finite enums, bounded identifiers, and typed locators are the
primary privacy controls. Defense-in-depth string checks reject private-key and
credential patterns, bearer tokens, emails, private/home paths, credentialed
URLs, traceback/stack traces, timestamped logs, and shell transcripts.
Prohibited values are omitted, not hashed.

Stable rejection codes are `file-boundary`, `document-size`,
`invalid-encoding`, `invalid-json`, `duplicate-key`, `invalid-structure`,
`unsupported-contract`, `privacy-violation`, `digest-mismatch`, and
`relationship-mismatch`. Messages are generic and do not echo rejected input.

## CLI

```bash
python3 scripts/evidencectl.py validate <document.json>
python3 scripts/evidencectl.py validate-set <document.json>...
```

The CLI is offline and performs no mutation. Exit zero means only that the
requested validation passed.
