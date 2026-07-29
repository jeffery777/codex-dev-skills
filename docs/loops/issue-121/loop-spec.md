# Loop Engineering V2d-A: Operational Evidence Contract V0 Core

## Objective

Deliver Issue #121 as the public `loop-operational-evidence/v0` contract,
validator, fixture, test, eval, documentation, and v0.10.0 release-preparation
slice. Operational evidence must be deterministic, tamper-evident,
privacy-preserving, and useful without becoming authorization or completion
evidence.

## Source Of Truth

- Repository instructions: `AGENTS.md`
- GitHub objective: Issue #121
- Roadmap: `docs/roadmap.md`
- Program contract:
  `docs/programs/operational-evidence/README.md`
- Architecture decisions:
  `docs/programs/operational-evidence/architecture-decisions.md`
- Accepted phases:
  `docs/programs/operational-evidence/implementation-phases.md`
- Continuation requirements:
  `docs/programs/operational-evidence/continuation.md`
- Implementation plan:
  `docs/loops/issue-121/implementation-plan.md`
- Task manifest:
  `docs/loops/issue-121/task-manifest.yaml`

## Release Boundary

- Target release: v0.10.0.
- The Issue #121 implementation branch owns feature implementation, version
  alignment, release notes, and release-readiness preparation.
- A separate release-preparation branch is not required.
- Merge, tag creation, and GitHub Release publication are separate exact human
  gates and must target the reviewed merge commit.

## Contract Envelope

Every operational-evidence document is one JSON object with exactly these
top-level fields:

- `contract_version`: exact value `loop-operational-evidence/v0`;
- `kind`: one supported document kind;
- `document_id`: bounded opaque identifier;
- `run_id`: bounded opaque identifier shared by a run bundle;
- `objective_id`: bounded opaque identifier;
- `source_revision`: exact repository identity and Git commit;
- `observed_at`: timestamp matching
  `YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)`;
- `producer`: bounded producer kind and opaque producer id;
- `payload`: the exact kind-specific payload;
- `authority_invariants`: the exact false-authority block;
- `document_digest`: lowercase SHA-256 of the canonical document body with
  `document_digest` omitted.

The v0 contract is JSON-only. It has no extension field. Unknown or missing
fields fail closed. Canonical JSON uses sorted ASCII object keys, compact
separators, UTF-8 strings, JSON booleans/null, bounded safe integers, and no
floating-point or non-finite values.

V0 bounds are:

- encoded document size: at most 131,072 bytes;
- document set size: at most 256 documents;
- nesting depth: at most 32;
- string size: at most 512 UTF-8 bytes unless a stricter field rule applies;
- array size: at most 256 items;
- integers: JSON safe integer range, with kind-specific non-negative bounds;
- identifiers: 1–128 ASCII characters matching
  `[A-Za-z0-9][A-Za-z0-9._:-]{0,127}`;
- digests: exactly 64 lowercase hexadecimal SHA-256 characters;
- Git commits: exactly 40 lowercase hexadecimal characters.

Every timestamp uses literal `T`, one to six optional fractional digits, and
an explicit `Z` or numeric timezone offset; arbitrary separators and naive
timestamps fail closed. Values are normalized to UTC for comparison. Start
timestamps must not follow end timestamps.

The source revision contains:

- a bounded opaque `repository_id`, never a filesystem path or credentialed
  remote URL;
- an exact 40-character lowercase Git commit SHA.

No branch, worktree path, home directory, username, hostname, environment
variable, or machine-local locator is part of the common envelope.

The producer object has exactly `kind` and `id`. Producer kinds are `human`,
`agent`, `tool`, and `ci`; the id is an opaque identifier and must not be
derived from a prohibited username, hostname, path, email address, or secret.

A cross-document reference has exactly `document_id` and `document_digest`.
It carries no path or URL. Set validation resolves both fields against the
supplied documents.

Unknown contract versions fail closed. Any future field addition, kind,
taxonomy code, locator kind, or enum value requires a new reviewed contract
version rather than a permissive v0 extension.

## Document Kinds

### `run-receipt`

Records a bounded run outcome without claiming task or objective completion.
Its payload contains:

- `started_at` and `ended_at`;
- `execution_mode`;
- `outcome`;
- ordered unique iteration-summary references;
- one environment-fingerprint reference;
- one artifact-reference-set reference;
- zero or more unique failure-summary references;
- bounded verification, review, and human-gate observations.

The payload has exactly those fields. Execution modes are `current-session`,
`shared-subagents`, `sequential-fallback`, and `ci`. Verification observations
are `not-run`, `passed`, `failed`, and `skipped`. Review observations are
`not-required`, `required`, `passed`, and `blocked`. Human-gate observations
are `not-required`, `pending`, and `satisfied`.

Allowed run outcomes are `work-recorded`, `stopped-failure`,
`stopped-human-gate`, and `cancelled`. `work-recorded` means only that this
receipt recorded the run; it does not mean the task or objective is complete.

### `iteration-summary`

Records one machine-readable iteration:

- positive integer sequence;
- bounded phase;
- bounded result;
- optional opaque task id;
- start/end timestamps;
- zero or more artifact ids from the referenced artifact set;
- zero or more failure-summary references.

The payload has exactly `sequence`, `phase`, `result`, `task_id`, `started_at`,
`ended_at`, `artifact_ids`, and `failure_summaries`. Sequence is in
`1..1,000,000`. Task id is either null or an opaque identifier. Phases are
`bootstrap`, `planning`, `implementation`, `verification`, `review`,
`integration`, and `release-preparation`.

Allowed results are `continue`, `handoff-prepared`,
`blocked-by-human-gate`, and `work-recorded`. The existing Markdown iteration
report remains an optional human-readable artifact; this JSON summary does not
replace it or mutate the loop ledger.

### `failure-summary`

Uses no arbitrary failure message or raw exception text. Its payload contains:

- optional iteration sequence;
- bounded phase;
- bounded category and category-compatible code;
- bounded retry disposition;
- zero or more artifact ids.

The payload has exactly `iteration_sequence`, `phase`, `category`, `code`,
`retry`, and `artifact_ids`. `iteration_sequence` is either null for a
run-level failure or an integer in `1..1,000,000`. Phase uses the iteration
phase enum.

An iteration summary is the digest-bound owner of its failure-summary
references. A failure summary records only the owner's sequence, not a digest
reference back to that iteration. This deliberately avoids a cyclic
content-digest dependency while still allowing set validation to require
exactly one matching iteration owner for every non-null sequence.

Failure categories are:

- `contract-validation`;
- `source-conflict`;
- `authority-boundary`;
- `privacy-redaction`;
- `capability`;
- `tooling`;
- `verification`;
- `review`;
- `integration`;
- `resource-bound`;
- `external-action-gate`;
- `unclassified`.

Every category has an explicit finite code set in the public reference. The
`unclassified` category has only the `unclassified` code. Retry dispositions
are `never`, `manual`, `after-input`, and `after-environment-change`.

The category-compatible code map is:

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

Uses an allowlist rather than a redaction blocklist. Its payload contains only:

- `runtime_surface`;
- `os_family`;
- `architecture`;
- Python `major` and `minor`;
- `execution_mode`;
- `sandbox_mode`;
- `redaction_applied: true`;
- `prohibited_fields_present: false`.

The payload has exactly those fields. Runtime surfaces are `codex-cli`,
`codex-desktop`, `codex-ide`, `ci`, and `other`. OS families are `macos`,
`linux`, `windows`, and `other`. Architectures are `arm64`, `x86_64`, and
`other`. Python major/minor values are integers in `0..99`. Execution mode uses
the run-receipt enum. Sandbox modes are `read-only`, `workspace-write`,
`danger-full-access`, and `unknown`.

Every value is an enum or bounded integer. No free-form environment field is
allowed. A prohibited value must be omitted, not hashed. The validator rejects
unknown environment fields and contradictions to the two redaction booleans.

### `artifact-reference-set`

Contains an ordered array of typed artifact references. Each reference has
exactly:

- `artifact_id`;
- `artifact_kind`;
- `locator_kind`;
- `locator`;
- `content_sha256`;
- `media_type`.

Supported artifact kinds cover:

- `loop-ledger` and `loop-event`;
- `route-receipt`, `worker-receipt`, and `integration-receipt`;
- `memory-receipt`;
- `verification` and `review`;
- `git-commit`;
- `platform-artifact`;
- `gitnexus-fingerprint`;
- `other-public-artifact`.

Supported locator kinds are:

- normalized repository-relative path;
- exact Git commit;
- bounded opaque id.

Artifact kind and locator kind must be compatible. URLs, absolute paths,
filesystem-relative traversal, user-home aliases, credentialed locators, and
machine-local paths are not supported. Artifact ids and locator/digest pairs
must be unique.

Compatibility is exact:

- loop, route, worker, integration, memory, verification, review, and other
  public artifacts use `repository-relative-path`;
- Git commits use `git-commit`;
- platform artifacts use `opaque-id`;
- GitNexus fingerprints use `repository-relative-path` or `opaque-id`.

Repository-relative paths are normalized POSIX paths with no absolute prefix,
empty component, `.` component, `..` component, backslash, tilde, URL scheme,
or percent-encoded traversal. Media types are `application/json`,
`application/yaml`, `text/markdown`, and `text/plain`.

`content_sha256` is caller-supplied content identity. Offline validation checks
its syntax and relationship consistency but does not dereference the artifact.
Current-state consumers must independently re-read and revalidate an artifact
before using it for any authoritative decision.

## Cross-Document Validation

The offline CLI validates a document independently and validates a supplied set
without a backend:

- the supplied set contains at most 256 documents;
- every document has the same run id, objective id, and source revision;
- document ids are unique;
- exactly one run receipt exists;
- the run receipt resolves one environment fingerprint and one artifact set;
- the run receipt and its referenced environment fingerprint declare the same
  execution mode;
- every referenced iteration and failure summary resolves by document id and
  digest;
- iteration sequences are unique, contiguous from one, and referenced in
  sequence order;
- every failure with a non-null iteration sequence is referenced by exactly one
  iteration with that sequence; run-level failures with a null sequence are
  not referenced by an iteration;
- artifact ids referenced by iteration/failure documents exist in the artifact
  set;
- conflicting, duplicate, missing, or kind-mismatched references fail closed.

Exact duplicate document ids are rejected rather than silently deduplicated.
V0 does not define improvement lineage or graph projection.

## Authority Invariants

Every validated document contains exactly:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

A validator result, valid bundle, content digest, current timestamp, successful
run outcome, referenced verification/review artifact, or accepted platform
reference cannot raise these values or imply equivalent authority.

Operational evidence:

- does not authenticate its producer;
- does not mutate a ledger or task status;
- does not satisfy a human gate;
- does not prove task or objective completion;
- does not authorize an external write, promotion, merge, tag, release, or
  deploy.

## Relationship Rules

| Existing source | Allowed relationship | Forbidden interpretation |
| --- | --- | --- |
| Loop ledger/event | Repository-relative typed reference plus content digest and source commit | Evidence cannot mutate, replace, or authenticate ledger state |
| Route receipt | Reference selected route/profile/fallback | Route/profile cannot widen scope or permission |
| Worker receipt | Reference worker output and digest | Worker `complete` cannot prove completion |
| Integration receipt | Reference integration disposition | `integration_accepted` cannot prove completion |
| `loop-memory/v1` receipt | Advisory reference | Memory cannot authorize, satisfy a gate, or prove completion |
| Verification/review artifact | Exact repository artifact reference | Reference does not make evidence accepted or current |
| Git/platform artifact | Exact commit or opaque platform id | Reference grants no live platform action |
| GitNexus fingerprint | Advisory identity/freshness artifact | Index state cannot replace repository truth or enable unsupported capabilities |

## Privacy And Data Placement

Public repository content is limited to contracts, validators, CLIs, synthetic
fixtures/examples, tests, evals, policies, relationship documentation, and
release documentation.

Real run records, credentials, secrets, usernames, hostnames, home directories,
private absolute paths, transcripts, raw logs, raw tool output, unredacted
exceptions, machine configuration, indexes, caches, databases, app state, and
private PoC evidence remain outside the public repository.

All strings are checked against bounded prohibited-data indicators. Rejection
errors use stable error codes and safe generic messages; they must not echo the
rejected value.

At minimum the prohibited-data checks cover synthetic forms of:

- PEM/private-key blocks and credential assignments;
- bearer/access tokens and credentialed URLs;
- email addresses;
- macOS, Linux, and Windows user-home paths, `file://`, and home-relative
  paths;
- traceback/stack-trace headers, shell transcripts, and multi-line timestamped
  log records.

These indicators are defense in depth. Exact field allowlists, identifier
syntax, path syntax, field bounds, and finite taxonomies remain the primary
privacy controls.

## Validator And CLI Boundary

Expected production files:

- `skills/loop-engineering/scripts/operational_evidence.py`;
- `skills/loop-engineering/scripts/evidencectl.py`.

The validator:

- uses no network or backend;
- performs no repository or external mutation;
- opens bounded regular non-symlink JSON files with descriptor-level identity
  checks to prevent path substitution between inspection and read;
- rejects duplicate keys before object construction;
- validates structure, semantics, privacy, digests, and bundle relationships;
- returns deterministic structured results.

CLI commands:

- `validate <document.json>`;
- `validate-set <document.json>...`.

Exit code zero means only that the requested validation passed. It does not
grant authority or prove completion.

Rejections use stable public error codes:

- `file-boundary`;
- `document-size`;
- `invalid-encoding`;
- `invalid-json`;
- `duplicate-key`;
- `invalid-structure`;
- `unsupported-contract`;
- `privacy-violation`;
- `digest-mismatch`;
- `relationship-mismatch`.

The CLI returns code and generic message only; it never echoes rejected field
contents.

## Scope

### In Scope

- All contracts, validators, fixtures, tests, evals, docs, packaging, and
  v0.10.0 preparation described above.

### Out Of Scope

- improvement records and V3 self-improvement;
- Obsidian or tool-neutral projection implementation;
- typed graph projection manifest;
- private PoC data;
- hooks, plugins, schedulers, controllers, daemons, databases, queues, or graph
  runtime;
- backend persistence, network access, or automatic evidence collection;
- automatic promotion, merge, tag, release, or deployment;
- a separate v0.10.0 release-preparation branch.

## Definition Of Done

- Contract and relationship semantics above are implemented and documented.
- Positive fixtures for every document kind and a complete valid set pass.
- Negative, tamper, duplicate-key, unknown-field, secret, private-path,
  raw-log, invalid-reference, duplicate-id, and cross-record mismatch fixtures
  fail closed.
- Canonical serialization, document digests, and set validation are
  deterministic.
- The four authority invariants cannot be omitted or changed.
- Existing V1/V2a/V2b/V2c contracts and evals remain green.
- README, installer, catalog, roadmap, program docs, reference docs, and
  repository validation are aligned.
- v0.10.0 version metadata, release notes, and release-readiness preparation
  are present in the Issue #121 branch.
- Deep code, docs, security/privacy, formal code-readiness, and merge-readiness
  reviews have no unresolved MUST-FIX findings.

## Human Gates

Stop for unresolved public-contract, privacy/redaction, authority, or
data-placement semantics. Also stop before commit, push, PR creation, review
submission, merge, tag creation, GitHub Release publication, deployment, or
another external write without the exact required authorization.
