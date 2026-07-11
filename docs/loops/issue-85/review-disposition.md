# Issue 85 Review Disposition

This file is the durable disposition record for Loop Engineering V2a review
closure. Chat summaries and worker self-reports are coordination evidence only;
the final diff, repository verification, formal review, security finalization,
Git state, and accepted GitHub state determine readiness.

## Gate Rule

- `Fixed` requires a final-diff re-review plus relevant executable evidence.
- `Deferred` requires an owner, durable target, residual risk, verification plan,
  and promotion trigger.
- `Rejected` requires a concrete rationale.
- `Needs Human Decision` blocks PR readiness.
- No finding below is deferred, rejected, or awaiting a product decision.

## MUST-FIX

| Finding ID | Disposition | Resolution evidence | Verification |
| --- | --- | --- | --- |
| `MF-01-classification-factor-coverage` | Fixed | All nine requested factors are validated, classified, and emitted as explainable route evidence; high-risk triggers are non-compensatory. | Production routing unit and eval matrices. |
| `MF-02-authority-invariance` | Fixed | Role/model selection never grants workflow mutation, external-write, scope, gate, or completion authority; custom profile preflight also requires evidence that its technical sandbox does not widen the parent sandbox. | Authority metamorphic evals, sandbox-ceiling tests, and CLI negatives. |
| `MF-03-runtime-profile-trust` | Fixed | The registry binds each namespaced profile to its exact source digest; changed developer instructions, sandbox settings, or model mappings invalidate the trusted deployment. | Profile-preflight tamper and deployed-digest tests. |
| `MF-04-runtime-fallback-validation` | Fixed | Requested and fallback profiles are validated against actual TOML, trusted registry metadata, runtime model/reasoning facts, destination presence, and collision state before selection. | Missing, unavailable, tampered, and fake-fallback regression tests. |
| `MF-05-high-risk-degradation` | Fixed | Unsafe high-risk or coupled work cannot silently downgrade to a low-capability worker; it proceeds only through a safe same-class/parent/sequential path or a human gate. | High-risk, coupled-force, and no-safe-fallback eval cases. |
| `MF-06-receipt-binding` | Fixed | Route, worker, and integration receipts bind selected role, capability class, assigned scope, exact Git branch/HEAD, profile digest, worker/verification artifact digests, and integration disposition. | Stale commit, same-HEAD branch switch, partial, failed, conflicting, forged-scope, and changed-source tests. |
| `MF-07-false-completion` | Fixed | Worker and integration receipts remain coordination evidence and cannot set `completion_proven`; main-agent verification is mandatory. | False-completion and missing-verification evals. |
| `MF-08-installer-atomicity` | Fixed | Profile install/update/uninstall preflights all profile destinations before any expanded dependency/profile mutation, refuses unsafe profile collision or modification, and preserves rollback backups/state. Existing dependency destinations retain normal installer sync semantics. | Isolated installer list/status/diff/install/update/uninstall and collision-before-dependency tests. |
| `MF-09-install-root-isolation` | Fixed | Installed digest state is keyed by target root, so user-level and project-scoped adoption can coexist without source-version drift corrupting rollback. | Dual-root and rollback regression tests. |
| `MF-10-install-path-safety` | Fixed | Custom roots require explicit project opt-in; unsafe paths, symlinks, arbitrary overwrite, and partial deterministic collision are rejected. | Path-containment, symlink, collision, and group-preflight tests. |
| `MF-11-eval-production-parity` | Fixed | The V2a suite invokes production classification/preflight/integration code and checks deterministic outputs instead of duplicating a fixture-only router. | Eval harness contract and full suite. |
| `MF-12-runtime-capability-validation` | Fixed | Runtime surface labels do not grant capability. Routing consumes explicit custom-agent, parent, and sequential capability/preflight evidence; unknown or missing custom-agent capability safely degrades or stops at the required human gate. | CLI/Desktop/IDE capability-variance, no-surface, and V1 sequential-fallback tests. |

## SHOULD-FIX

| Finding ID | Disposition | Resolution evidence | Verification |
| --- | --- | --- | --- |
| `SF-01-profile-schema-strictness` | Fixed | Unknown keys, invalid role metadata, model/reasoning shape, and sandbox widening are rejected. | Profile validator negative tests. |
| `SF-02-destination-preflight` | Fixed | Route preflight distinguishes source validity from actual destination presence, digest, and same-name collision. | CLI destination-state tests. |
| `SF-03-explicit-profile-adoption` | Fixed | `codex-agent-profiles` is an opt-in installer group and is intentionally excluded from `--all`. | Catalog and installer contract tests. |
| `SF-04-precedence-documentation` | Fixed | User-level and trusted project-scoped paths, Codex precedence, collision handling, and exact environment variables are documented. | Final documentation review. |
| `SF-05-rollback-documentation` | Fixed | Rollback describes diff-before-uninstall, modified-profile refusal, matching custom-root variables, backups, and V1 sequential continuity. | Final documentation review and isolated rollback tests. |
| `SF-06-model-lifecycle-boundary` | Fixed | Shared workflow semantics use capability classes; concrete model IDs are confined to replaceable runtime profiles with availability, verification date, and fallback metadata. | Registry/profile validation and runtime documentation review. |
| `SF-07-cost-claim-calibration` | Fixed | Evals expose latency/token proxies but do not claim measured savings. | Eval output contract and documentation review. |
| `SF-08-private-state-exclusion` | Fixed | Implementation uses repository files and documented custom-agent surfaces only; no Desktop database, session, log, cache, auth, daemon, sidecar, scraper, or unpublished client is introduced. | Scope scan and final diff review. |

## NITS

| Finding ID | Disposition | Resolution evidence | Verification |
| --- | --- | --- | --- |
| `NIT-01-command-examples` | Fixed | Examples distinguish source validation, installed-destination validation, routing, and integration commands. | Documentation review. |
| `NIT-02-role-namespacing` | Fixed | All four public profiles use repository-specific names to reduce collisions with user agents. | Registry/profile validation. |
| `NIT-03-v1-continuity-wording` | Fixed | Docs consistently state that V1 shared/sequential semantics remain usable without the custom-agent surface. | Documentation review and no-surface eval. |

## Prior Documentation Review Findings

The stable identifiers from the formal documentation-review rounds map to the
canonical resolutions above as follows; this table supersedes no evidence and
exists so those findings are not preserved only in chat history.

| Finding ID | Disposition | Canonical resolution and evidence |
| --- | --- | --- |
| `DOC-MF-001` | Fixed | `SF-04-precedence-documentation`: source and installed preflight examples scan the destination plus the other user/project root, detect same TOML `name` under different filenames, and show the exact project opt-in environment. Verified by final docs review, profile-preflight tests, and isolated installer tests. |
| `DOC-MF-002` | Fixed | `SF-05-rollback-documentation`: user/project rollback reuses the matching custom root, performs diff before uninstall, and documents modified-profile refusal and V1 continuity. Verified by final docs review and isolated rollback tests. |
| `DOC-SF-001` | Fixed | `SF-04-precedence-documentation`: project-over-user precedence and trusted project `.codex` behavior are stated only to the extent supported by the official Codex Subagents and Configuration Basics documentation. Verified by official-source readback and final docs review. |
| `DOC-NIT-001` | Fixed | `NIT-01-command-examples`: public commands distinguish source validation, installed-destination validation, route creation, and main-agent integration. Verified by final docs review and command/CLI tests. |

### Final Documentation Re-review

| Finding ID | Disposition | Canonical resolution and evidence |
| --- | --- | --- |
| `DOC2-MF-001-sandbox-authority-wording` | Fixed | Public docs now distinguish technical custom-agent `sandbox_mode` from workflow authorization, and production preflight requires non-widening parent-sandbox evidence before activating a writable profile. Covered by balanced-worker unknown/read-only/workspace-write parent tests. |
| `DOC2-MF-002-verification-digest-closure` | Fixed | Integration now requires a complete verification-artifact digest map, reads each regular non-symlink file below the trusted verification root, and rejects a digest mismatch. Template, docs, positive flow, missing-file, and tamper tests match the implementation. |
| `DOC2-MF-003-installer-preflight-scope` | Fixed | README and canonical disposition now state the exact guarantee: all profile destinations are preflighted before expanded dependency/profile mutation; they no longer claim every dependency destination has a separate preflight. |
| `DOC2-SF-001-backup-rollback` | Fixed | Public rollback docs identify adjacent `.toml.bak` files, whole-profile update refusal on backup collision, a review-and-restore procedure, revalidation, and safe cleanup. Covered by force-update and backup-collision tests. |

### Final Code Re-review

| Finding ID | Disposition | Canonical resolution and evidence |
| --- | --- | --- |
| `V2A-MF-01-transitive-installer-dependency` | Fixed | The opt-in profile group explicitly depends on both `shared-review-gates` and `codex-delivery-workflow`; isolated install asserts the formal gate skill and routing integration template are deployed. |
| `V2A-MF-02-exact-git-identity` | Fixed | Route creation and integration require both exact branch and immutable HEAD; a same-HEAD branch switch is rejected as stale. |
| `V2A-SF-01-security-test-inventory` | Fixed | Integration negatives now cover symlink worker output and an alternate selected profile, in addition to current-state self-attestation, missing/tampered files, stale commit/branch, and absent flags. |

## Security Diff Review Findings

Scan `8967c45b-3999-4d00-bb60-7c3d5d2b8531` completed discovery, validation,
and policy calibration against an earlier working-tree snapshot. Its canonical
finalization correctly rejected snapshot drift after the fixes below began, so
it is discovery evidence only and is not cited as a completed clean scan. A new
scan against the stable final diff remains required by the final gate.

| Finding ID | Disposition | Canonical resolution and evidence |
| --- | --- | --- |
| `SEC-SF-01-installer-source-validation` | Fixed | Install/update validates all repository profile TOML files against the canonical registry, including sandbox and expected digest, before any expanded-group mutation. Covered by unsafe-sandbox and digest-mismatch no-mutation tests. |
| `SEC-MF-01-dependency-preflight-order` | Fixed | The complete set of profile destinations is collision-preflighted before dependency skills, templates, profiles, or state change. Covered by byte-for-byte dependency and state preservation tests. |
| `SEC-MF-02-canonical-registry-trust-root` | Fixed | `agent-route` derives and requires the canonical registry shipped with the executing installed skill; an alternate self-consistent registry fails closed. Covered by alternate-registry CLI tests. |
| `SEC-MF-03-runtime-facts-provenance` | Fixed | Repository route documents cannot supply runtime facts; the CLI requires separate `--runtime-facts` current-session evidence and rejects the old embedded field. Covered by missing-flag and embedded-field negative tests. |
| `SEC-MF-04-integration-real-readback` | Fixed | `agent-integrate` independently reads exact Git branch/HEAD, regular non-symlink worker and verification artifacts, and selected profile from explicit roots; it verifies both artifact digest maps and assignment freshness and rejects receipt-supplied current state. Covered by real temporary-Git positive tests and missing, tampered, stale commit/branch, symlink, alternate-profile, and self-attestation negatives. |

## Final Gate Evidence

The final gate must record or reference all of the following before PR readiness:

- final full repository validation and `git diff --check`;
- clean final code and documentation re-review;
- completed Codex Security diff-scan finalization against the final diff;
- deep merge review and merge-readiness gate;
- commit SHA, pushed remote branch, linked ready-for-review PR, and PR head readback.

Until those checks complete, this artifact records resolved review findings but
does not claim publication or merge readiness.
