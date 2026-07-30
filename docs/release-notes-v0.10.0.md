# Release Notes: v0.10.0

Release date: TBD

v0.10.0 introduces Loop Engineering V2d-A: Operational Evidence Contract V0.
It adds a strict, offline, public evidence document family for bounded run
observations while preserving the existing authority, completion, human-gate,
external-write, and promotion boundaries.

## Operational Evidence V0

- Added the versioned `loop-operational-evidence/v0` envelope with exact
  common fields, canonical SHA-256 digests, and no extension surface.
- Added `run-receipt`, `iteration-summary`, `failure-summary`,
  `environment-fingerprint`, and `artifact-reference-set` documents.
- Added a bounded failure category/code taxonomy without arbitrary exception
  messages or raw logs.
- Added a finite redacted environment allowlist that omits usernames,
  hostnames, paths, credentials, emails, environment variables, and machine
  configuration rather than hashing them.
- Added typed artifact locators for repository-relative paths, exact Git
  commits, and opaque platform identities without network or artifact
  dereference.
- Added bundle relationship checks for identity, unique documents, complete
  inventories, digest references, ordered contiguous iterations, failure
  ownership, and artifact-id resolution.

Every validated document keeps:

```json
{
  "used_as_authorization": false,
  "used_as_completion_evidence": false,
  "external_write_authorized": false,
  "promotion_authorized": false
}
```

Validation does not authenticate producers, mutate ledgers, satisfy human
gates, prove completion, authorize external writes, or authorize promotion.

## Validator, CLI, And Evaluation

- Added the standard-library
  `skills/loop-engineering/scripts/operational_evidence.py` validator and
  `evidencectl.py` CLI.
- Added descriptor-level regular/non-symlink file reads, encoded document and
  set bounds, duplicate-key rejection, exact field/enum validation, canonical
  digest checks, privacy indicators, and generic non-echoing errors.
- Added positive document/bundle fixtures plus tamper, duplicate-key,
  unknown-field, synthetic assignment-secret, standalone-token, private-path,
  raw-log, invalid-reference, duplicate-document-id, and cross-record-mismatch
  fixtures.
- Added focused unit/CLI tests and the deterministic
  `scripts/eval-operational-evidence.py` suite.
- Integrated the operational-evidence tests and exact eval thresholds into
  `scripts/validate-repo.sh`.
- Confirmed filesystem installation copies the validator, CLI, and portable
  contract reference with the Loop Engineering skill.

## Documentation And Program Status

- Added the public contract, authority/data-placement matrix, redaction policy,
  relationship rules, CLI usage, and portable installed-skill reference.
- Advanced the roadmap and program continuation to the separate V2d-B
  improvement-lineage and projection-contract slice.
- Kept private PoC records, improvement execution, Obsidian synchronization,
  typed graph projection manifests, hooks, schedulers, controllers, databases,
  graph execution, and automatic promotion out of this release.

## Installation And Update

Review local differences before updating:

```bash
./install.sh diff --all
./install.sh update --all
```

Install the shared delivery workflow:

```bash
./install.sh install codex-delivery-workflow
```

Restart Codex or begin a new task after installation so changed skill content
is rediscovered.

## Verification

Re-run the release candidate verification from the repository root:

```bash
python3 --version
bash -n install.sh scripts/validate-repo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_operational_evidence \
  tests.test_evidencectl \
  tests.test_eval_operational_evidence
python3 scripts/eval-operational-evidence.py
python3 scripts/eval-loop-engineering.py
python3 scripts/eval-memory-contract.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py'
./scripts/validate-repo.sh
git diff --check
```

Exact-head deep code, documentation, security/privacy, merge, and formal
release-readiness evidence must have no unresolved MUST-FIX findings before
publication. These release notes do not independently satisfy those gates.

## Rollback

Restore the prior v0.9.3 source through the ordinary reviewed install/update
path. The V2d-A files are self-contained and do not migrate a database, enable
a hook, activate a controller, mutate a ledger, or create private runtime
state. Do not delete user skills, evidence, configuration, caches, or unrelated
state as an implicit rollback.

## Traceability

- V2d-A implementation issue:
  <https://github.com/jeffery777/codex-dev-skills/issues/121>
- Compare:
  <https://github.com/jeffery777/codex-dev-skills/compare/v0.9.3...v0.10.0>
