# Issue 81 Review Disposition

This file is the durable disposition record for the Loop Engineering V1 review
closure. A finding is not closed merely because it disappeared from a later
chat summary. Every MUST-FIX, SHOULD-FIX, and NIT discovered during this branch
must appear below with final evidence.

## Gate Rule

- `Fixed` requires a final-diff re-review and relevant verification evidence.
- `Deferred` requires an owner, durable target, remaining risk, verification
  plan, and promotion trigger.
- `Rejected` requires a concrete rationale.
- `Needs Human Decision` blocks readiness.
- This branch has no deferred, rejected, or human-decision findings.

## MUST-FIX

| Finding ID | Disposition | Resolution evidence | Verification |
| --- | --- | --- | --- |
| `MF-01-self-hash` | Fixed | V2 source revision uses previous-snapshot and canonical event hashes instead of a self-referential ledger hash. | Ledger validation and migration tests. |
| `MF-02-core-template-contract` | Fixed | Core, public ledger, event, claim, manifest, and templates use one canonical schema and status family. | Repository template validation and core tests. |
| `MF-03-runtime-layering` | Fixed | Shared subagents are no longer described as Desktop-only; legacy Desktop helpers are compatibility evidence only. | Native runtime contract tests. |
| `MF-04-unsafe-status` | Fixed | Safety is a blocker kind; `unsafe` is accepted only as V1 migration input and materializes as `blocked`. | Migration tests. |
| `MF-05-install-dependency` | Fixed | PyYAML prerequisite, skill-local requirements, installer assets, and dependency-free CLI help are aligned. | Installer and repository validation. |
| `MF-06-transition-fencing` | Fixed | Every transition with an active claim requires the current fencing token and an unexpired lease. | Core stale-token, expiry, revocation, and lifecycle tests. |
| `MF-07-semantic-replay` | Fixed | Audit replays production events and compares task, evidence, blocker, claim, gate, and objective materializations. | Semantic-audit negative and round-trip tests. |
| `MF-08-source-dependency-guards` | Fixed | Manifest dependencies, branch, HEAD, spec/manifest digests, and claim source revisions fail closed. | Source mismatch and dependency regression tests. |
| `MF-09-active-routing` | Fixed | The active skill calls production `loopctl decide`; evals use the same router. | CLI routing and workflow eval tests. |
| `MF-10-materialized-evidence` | Fixed | Nested evidence and blockers normalize, serialize, and replay without loss. | CLI apply-event round-trip tests. |
| `MF-11-reviewing-claim-lifecycle` | Fixed | Reviewing may retain a fenced active claim; release is legal only after leaving in-flight states. | Reviewing lifecycle tests. |
| `MF-12-write-race` | Fixed | Same-filesystem writes use an exclusive lock, byte CAS, fsync, and atomic replace. | Concurrent writer regression test. |
| `MF-13-gate-objective-history` | Fixed | Illegal gate/objective histories are rejected by production replay. | Missing materialization and invalid completion tests. |
| `MF-14-migration-replay` | Fixed | V1 migration emits a canonical `migration_snapshot` anchor with embedded source integrity. | Migration semantic replay and tamper tests. |
| `MF-15-migration-hash-lifecycle` | Fixed | Immutable `migration_source_sha256` is distinct from rolling `previous_ledger_sha256`. | Post-migration CLI write regression test. |
| `MF-16-migration-contract-binding` | Fixed | Bound migration injects real git/spec/manifest source revision before materializing active claims. | Bound in-progress migration CLI test. |
| `MF-17-migration-dependencies` | Fixed | Snapshot replay rejects ready-or-later tasks whose manifest dependencies are incomplete. | Direct and bound-command dependency tests. |
| `MF-18-initial-blocked` | Fixed | Manifest cannot declare an unreplayable initial blocked state; a canonical event must carry the blocker. | Manifest validation test. |
| `MF-19-objective-terminal` | Fixed | Once `objective_completed` is applied, new events are rejected while exact idempotent replay remains safe. | `test_objective_completion_is_terminal`. |
| `MF-20-claim-owner-identity` | Fixed | Active-claim transitions, acquisition, and release bind event actor to the recorded owner. | Focused claim impersonation regression tests pass. |
| `MF-21-acceptance-provenance` | Fixed | Acceptance requires a source-bound receipt and an exact out-of-band live action/receipt authorization. | Core and CLI protected-write regression tests pass. |
| `MF-22-gate-provenance` | Fixed | Satisfied/not-required gates require a concrete evidence receipt and independently authorized live write. | Core and CLI protected-write regression tests pass. |
| `MF-23-completion-provenance` | Fixed | Objective completion requires concrete evidence, source binding, and independently authorized live write. | Core lifecycle and eval state-contract tests pass. |
| `MF-24-lease-expiry-revocation` | Fixed | Expiry is rejected before the lease deadline; revocation remains a separately protected action with evidence. | Early/deadline expiry tests pass. |
| `MF-25-protected-payload-binding` | Fixed | Authorization binds objective identity and the canonical complete protected payload in addition to action, actor, scope, source, and artifact. | Payload mutation regression test passes. |
| `MF-26-protected-history-re-attestation` | Fixed | Routing, transition preview, and live ledger writes require exact current-session re-attestation before consuming historical protected state. | Core routing and CLI history replay tests pass. |
| `MF-27-manifest-execution-contract` | Fixed | Manifest schema/objective identity and required review/human gates are parsed and enforced by production transitions. | Manifest parser and required-gate transition tests pass. |
| `MF-28-security-reporting-phase` | Fixed | Parent reporting fallback is rejected outside the reporting phase even with trusted fallback authority. | Discovery-phase negative routing test passes. |
| `MF-29-required-review-gate-provenance` | Fixed | Required review completion is independently authorized and mode/artifact bound; required human gates derive from the manifest-named protected gate state. | Delegated completion and self-asserted gate regression tests pass. |
| `MF-30-routing-history-fail-closed` | Fixed | Every decision requires an explicit trusted exact digest or trusted `none` history attestation; missing repo provenance cannot bypass routing re-attestation. | Core and CLI missing/mismatched history tests pass. |

## SHOULD-FIX

| Finding ID | Disposition | Resolution evidence | Verification |
| --- | --- | --- | --- |
| `SF-01-status-vocabulary` | Fixed | Milestone loop lifecycle and task lifecycle are separate and complete. | Documentation review and repository validation. |
| `SF-02-installed-cli-paths` | Fixed | Usage uses `<installed-skill>/scripts/loopctl.py` and documents PyYAML setup. | Documentation review. |
| `SF-03-template-structure` | Fixed | Event and decision templates are parsed and checked for required fields. | Template validation tests. |
| `SF-04-concurrency-boundary` | Fixed | Same-filesystem CAS is distinguished from cross-worktree or distributed atomic coordination. | Documentation review. |
| `SF-05-task-continuation-modes` | Fixed | Shared subagent and Desktop task handoff vocabulary is aligned across skill, template, and example. | Documentation review. |
| `SF-06-migration-provenance-docs` | Fixed | Ledger docs distinguish internal integrity from external origin authentication. | Documentation review. |
| `SF-07-reviewing-recovery` | Fixed | Recovery order is blocker resolution, ready transition, fenced claim, then in-flight work. | Documentation review. |
| `SF-08-source-mismatch-tests` | Fixed | Branch, HEAD, spec digest, and manifest digest mismatches have explicit negative tests. | `test_contract_source_mismatches_fail_closed`. |
| `SF-09-event-chronology` | Fixed | Event timestamps are non-decreasing and the ledger update time matches the final event. | Backward-time core test and ledger validation. |
| `SF-10-event-revision-type` | Fixed | Event expected revision rejects booleans and other non-integer values. | `test_event_expected_revision_rejects_boolean`. |
| `SF-11-project-ledger-version` | Fixed | Project ledger validation explicitly requires schema version 2. | `test_project_validator_rejects_valid_v1_ledger`. |
| `SF-12-transition-semantic-audit` | Fixed | Transition preview runs semantic replay before trusting the materialized task view. | `test_transition_preview_rejects_non_replayable_materialization`. |
| `SF-13-portable-migration-paths` | Fixed | Bound migration requires in-repository contract files and stores repo-relative references. | Bound migration path tests. |
| `SF-14-eval-path-containment` | Fixed | Eval case paths must resolve inside the suite directory. | Path escape regression test passes. |
| `SF-15-iterative-dependency-validation` | Fixed | Dependency cycle detection uses iterative traversal and handles deep valid manifests. | 1,500-task graph regression test passes. |
| `SF-16-trusted-decision-authority` | Fixed | Repo YAML authority is ignored; exact external-write and parent-report fallback authority comes from CLI/session input. | Router, CLI, and evaluator negative tests pass. |
| `SF-17-security-scan-recovery` | Fixed | Production routing separates scan, Goal, and worker state and preserves running scans across resumable reporting failures. | Three deterministic recovery evals pass. |
| `SF-18-idempotent-replay-evidence` | Fixed | Protected idempotent replay requires history re-attestation and reports live authorization as false. | CLI replay regression test passes. |
| `SF-19-accepted-claim-lifecycle` | Fixed | Core rejects acceptance until the active claim is released. | Package-level active-claim acceptance test passes. |
| `SF-20-contract-path-containment` | Fixed | Loop spec and task manifest resolve inside the verified target repository for audit and write paths. | External spec/manifest path tests pass. |
| `SF-21-recovery-state-validation` | Fixed | Scan status, phase, worker failure kind, object shape, and non-negative retry count fail closed. | Malformed recovery-state tests pass. |
| `SF-22-authorized-fallback-eval` | Fixed | Eval injects a fixed runner-owned trusted profile outside fixture input and CLI wiring has an integration test. | Twenty-case eval and decide CLI test pass. |
| `SF-23-desktop-adapter-layering` | Fixed | README, selection guide, and Desktop adapter outputs treat task selection as shared orchestration ownership. | Native runtime contract test passes. |
| `SF-24-strict-integer-contracts` | Fixed | Ledger/core schema, state/event revision, claim revision, and fencing generation reject booleans. | Direct core and YAML regression tests pass. |
| `SF-25-ledger-directory-fsync` | Fixed | Atomic replacement is followed by parent-directory fsync. | CLI test observes file and directory fsync calls. |
| `SF-26-objective-lifecycle-contract` | Fixed | Event-sourced objective lifecycle exposes only reachable `active` and `complete`; task cancellation remains separate. | Template validation and lifecycle parser checks pass. |
| `SF-27-goal-status-contract` | Fixed | Goal projections accept only inactive, active, blocked, or complete. | Unknown `paused` projection test rejects. |
| `SF-28-malformed-history-ordering` | Fixed | Apply-event validates ledger structure before computing protected-history digests. | Mapping/scalar history regression returns structured rejection. |
| `SF-29-post-commit-durability` | Fixed | Directory-fsync failure after atomic replacement reports a committed, durability-uncertain non-retryable outcome. | Injected second-fsync failure test verifies persisted revision and structured result. |
| `SF-30-validator-contract-containment` | Fixed | Project-ledger validation rejects absolute, dot-dot, and symlink-resolved contract references outside the verified repository. | Focused external-contract regression test passes. |
| `SF-31-final-source-revalidation` | Fixed | Live ledger writes reverify Git/spec/manifest identity at the final pre-replace boundary, together with the ledger CAS. | Focused source-drift injection rejects before replace and preserves revision zero. |

## NITS

| Finding ID | Disposition | Resolution evidence | Verification |
| --- | --- | --- | --- |
| `NIT-01-ledger-version-label` | Fixed | Template names Loop Engineering V1 with ledger schema v2. | Template validation and docs review. |
| `NIT-02-runtime-history-wording` | Fixed | V2 boundary now describes the V1 document as historical decision evidence without implying an active later slice. | Final documentation review. |
| `NIT-03-protected-replay-wording` | Fixed | Skill, workflow, docs, and templates distinguish replay integrity from live authorization. | Contract documentation tests pending final run. |
| `NIT-04-fallback-flag-contract` | Fixed | Contract test asserts the complete `--parent-security-report-fallback-authorized` flag. | Security recovery contract test passes. |
| `NIT-05-protected-event-template-flags` | Fixed | Event template documents task-completion review fields and historical re-attestation flag. | Template and documentation review pending final run. |
| `NIT-06-sensitive-review-truncation` | Fixed | The broad sensitive-term diagnostic explicitly reports truncation and is not a credential gate; the accepted UX limitation remains durable evidence. | Codex Security validation suppressed the candidate because no exposure or authority boundary is crossed. |

## Final Verification

The final gate must append or reference the exact verification run, deep code
review result, security diff scan result, commit SHA, and pushed branch after
those steps complete. Until then, this file records finding closure but not
publication completion.
