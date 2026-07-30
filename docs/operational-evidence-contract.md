# Operational Evidence Contract V0

`loop-operational-evidence/v0` is the public Loop Engineering V2d-A contract
for bounded, tamper-evident, privacy-preserving run evidence. It is useful for
inspection and later projection, but it is never authorization or completion
evidence.

The portable contract reference is installed with the Loop Engineering skill
at
[`skills/loop-engineering/references/operational-evidence-v0.md`](../skills/loop-engineering/references/operational-evidence-v0.md).

## Document Family

Every JSON document has an exact common envelope and one of five exact kinds:

- `run-receipt`
- `iteration-summary`
- `failure-summary`
- `environment-fingerprint`
- `artifact-reference-set`

The envelope binds an opaque document/run/objective identity, exact repository
identity and Git commit, timestamp, bounded producer, kind payload, the four
false-authority invariants, and a canonical SHA-256 digest. V0 has no extension
field; missing fields, unknown fields, duplicate JSON keys, floating-point
values, unsupported enums, and unknown contract versions fail closed.

The validator bounds each encoded document to 131,072 bytes, each document set
to 256 documents, nesting depth to 32, strings to 512 UTF-8 bytes, arrays to
256 items, identifiers to 128 safe ASCII characters, and integers to the JSON
safe range plus kind-specific limits.

Timestamps use
`YYYY-MM-DDTHH:MM:SS[.ffffff](Z|+HH:MM|-HH:MM)`: literal `T`, one to six
optional fractional digits, and an explicit UTC marker or numeric offset.
Arbitrary separators and naive timestamps fail closed.

## Authority And Data Placement

| Data or action | Public contract role | Authority |
| --- | --- | --- |
| Validated operational-evidence document | Advisory, digest-bound observation | Cannot authorize, satisfy a gate, prove completion, or promote |
| Loop ledger or event | Typed repository-relative artifact reference | Remains governed by its own replay, protected-action, and acceptance rules |
| Route, worker, or integration receipt | Typed artifact reference | Cannot widen scope or turn worker/integration status into completion |
| `loop-memory/v1` receipt | Advisory artifact reference | Cannot become trusted memory or write authorization |
| Verification or review artifact | Typed repository-relative reference | Must be independently reread and revalidated before an authoritative decision |
| Git commit or platform artifact | Exact commit or opaque platform identity | Grants no live platform action |
| GitNexus fingerprint | Advisory identity/freshness artifact | Cannot replace repository truth or enable unsupported capabilities |
| Real run data, logs, transcripts, machine state | Private or caller-controlled storage | Must not enter this public repository |

Every validated document contains exactly:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

A valid document, bundle, digest, successful observation, or referenced review
cannot raise or imply any of these values.

## Privacy And Redaction

The environment fingerprint uses a finite allowlist: runtime surface, OS
family, architecture, Python major/minor, execution mode, sandbox mode,
`redaction_applied: true`, and `prohibited_fields_present: false`. Usernames,
hostnames, paths, emails, credentials, environment variables, and raw machine
configuration are omitted rather than hashed.

Artifact locators are restricted to normalized repository-relative paths,
exact Git commits, or bounded opaque ids according to artifact kind. URLs,
absolute paths, traversal, home aliases, and machine-local locators are
unsupported.

All document strings receive defense-in-depth checks for synthetic secret and
credential patterns, emails, private/home paths, credentialed URLs,
tracebacks/stack traces, timestamped logs, and shell transcripts. Rejections
return a stable code and generic message without echoing the rejected value.

Public Git content may contain only contracts, validators, CLIs, synthetic
fixtures, tests, evals, policies, relationship docs, and release docs. Real
operational records, credentials, logs, transcripts, private PoC evidence,
indexes, databases, caches, and app/runtime state stay outside this repository.

## Offline Validation

Validate one document or a complete supplied set:

```bash
python3 skills/loop-engineering/scripts/evidencectl.py validate <document.json>
python3 skills/loop-engineering/scripts/evidencectl.py validate-set \
  <run-receipt.json> \
  <iteration-summary.json> \
  <failure-summary.json> \
  <environment-fingerprint.json> \
  <artifact-reference-set.json>
```

Set validation requires one run receipt, one environment fingerprint, and one
artifact-reference set; consistent run/objective/source identity; unique
document ids; digest-resolved inventories; ordered contiguous iteration
sequences; exactly one matching iteration owner for every iteration-level
failure; matching run/environment execution modes; and resolvable artifact
ids.

Exit code zero means only that validation passed. The validator performs no
network access, artifact dereference, ledger mutation, external write,
promotion, or completion transition.

Run the production-backed fixture suite:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-operational-evidence.py
```

The checked-in suite includes valid documents/bundles and tamper,
duplicate-key, unknown-field, synthetic assignment-secret, standalone-token,
private-path, raw-log, invalid-reference, duplicate-document-id, and
cross-record-mismatch rejections.

## Separate Composed Work

V0 does not define improvement records, baseline/candidate lineage, or
projections. V2d-B adds those capabilities through the separate
`loop-improvement-lineage/v0` and `loop-evidence-projection/v0` families; it
does not extend this envelope. See
[Improvement Lineage And Projection Contracts V0](improvement-lineage-contract.md).

Private PoC data, automatic collection, hooks, schedulers, controllers,
databases, graph execution, production Obsidian synchronization, and automatic
promotion remain out of scope.
