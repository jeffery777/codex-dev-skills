# Issue #169 Wrapper V1 Readiness Crosswalk

## Scope and terms

This is a non-destructive preparation record. It classifies all 16 historical
Desktop Runtime Wrapper V1 scripts and their 263 test assertions. It does not
authorize wrapper execution, archiving, or deletion.

Source baseline: `864fe8cf61553f6d7db52456a31235da0456f2d3` (`v0.17.1`).
The canonical artifact list is
[`docs/desktop-runtime-wrapper-v1-inventory.yaml`](../../desktop-runtime-wrapper-v1-inventory.yaml).

`current-native-covered` means the current user-visible capability and its
authority boundary are specified in
[`docs/native-runtime-capabilities.md`](../../native-runtime-capabilities.md)
and checked by `tests/test_native_runtime_contract_docs.py`. It does not make
any historical response shape, cache record, injected callable, or helper a
supported native interface.

- **obsolete-wrapper-mechanism**: do not port this helper/schema.
- **current-native-covered**: keep the present semantic through native docs/tests.
- **extract-security-fixture**: preserve the listed safety property without any
  `desktop_runtime_*` import, load, subprocess, or path fixture.
- **historical-only**: retain only non-executable historical evidence if needed.

## Behavior disposition

| Historical script / focused test | Assertions | Historical behavior | Disposition | Required successor evidence |
| --- | ---: | --- | --- | --- |
| `capability_discovery` | 10 | Normalizes caller-supplied metadata. | obsolete-wrapper-mechanism; current-native-covered | Native Desktop callable schema; extract refusal of unknown/private evidence as runtime contract. |
| `contract_compare` | 11 | Compares old/new wrapper request and response fields. | obsolete-wrapper-mechanism; historical-only | Do not retain comparison output; extract fail-closed handling of changed required fields where it protects a native contract. |
| `wrapper_planner` | 19 | Dry-run planning and fallback prompt. | obsolete-wrapper-mechanism; current-native-covered | Native capability families and sequential fallback; extract private-state and external-write refusal. |
| `create_thread_preflight` | 11 | Evidence-only target/prompt/authorization readiness. | obsolete-wrapper-mechanism; current-native-covered | Native `create_thread` target and authorization rules; extract external-write/private-state refusal. |
| `create_thread_authorization_gate` | 15 | Wrapper pre-call authorization envelope using cache/status evidence. | obsolete-wrapper-mechanism; current-native-covered | Native state-changing call-site rule; extract exact action authorization, no destructive-approval substitution, no private state. |
| `create_thread_executor_boundary` | 16 | Proposal-only executor boundary. | obsolete-wrapper-mechanism; historical-only | Extract that prior evidence cannot replace target, permission, or response validation. |
| `create_thread_executor_shell` | 19 | Validates a shell request for a future injected executor. | obsolete-wrapper-mechanism; historical-only | Extract no direct/private runtime path, no daemon/sidecar claim, and required call-site checks. |
| `create_thread_executor` | 20 | Calls an injected non-live callable and validates wrapper response. | obsolete-wrapper-mechanism; current-native-covered | Native `create_thread` response identity; do not retain runner/flag compatibility; extract permission/auth and malformed/absent response refusal. |
| `create_thread_callable_wiring` | 20 | Produces a non-live callable descriptor. | obsolete-wrapper-mechanism; historical-only | Do not port descriptor schema; extract unsupported-tool, private-state, external-write, and non-execution safeguards. |
| `create_thread_callable_bundle` | 22 | Assembles wiring evidence into executor preview. | obsolete-wrapper-mechanism; historical-only | Do not port bundle output; extract preview-is-not-execution, direct-shape refusal, and no live test invocation. |
| `create_thread_live_smoke` | 27 | Separately approved injected live-call smoke wrapper. | obsolete-wrapper-mechanism; current-native-covered | Highest-priority extraction: explicit human authorization; private-state/external-write refusal; auth failure; required returned identity/status; queued identity distinction. Do not retain any smoke entrypoint. |
| `read_thread_preflight` | 13 | Evidence-only `read_thread` preflight. | obsolete-wrapper-mechanism; current-native-covered | Native read-only observation contract; extract `threadId`/known `hostId` and read-only classification refusal. |
| `evidence_pipeline` | 11 | Runs discovery/compare/preflight without a call. | obsolete-wrapper-mechanism; historical-only | No replacement pipeline; extract target-action selection and explicit external-write-false boundary only if absent elsewhere. |
| `session_compatibility_status` | 14 | Validates wrapper-local compatibility status. | obsolete-wrapper-mechanism; historical-only | Do not retain status/schema hashes; extract status-is-not-authorization and no-private-state rules. |
| `session_compatibility_handshake` | 14 | Produces first-use wrapper compatibility status. | obsolete-wrapper-mechanism; historical-only | Do not retain handshake/schema; extract current-session evidence cannot replace authorization/response validation. |
| `session_compatibility_cache` | 21 | Reads/writes wrapper-local session cache. | obsolete-wrapper-mechanism; historical-only | Do not port cache files/scope; extract stale/session mismatch and cache-not-authorization only where applicable to native design. |

## Exact evidence for retained current semantics

The following table is deliberately narrower than the historical helper
surface. Each row identifies the retained current semantic, its canonical
native source, the exact test method that checks that native boundary, and the
wrapper-specific material that remains obsolete. A cited test does not preserve
an old V1 JSON schema, callable descriptor, cache envelope, or smoke command.

| Historical helper | Canonical native heading/path | Exact test method | Covered current semantic | Obsolete disposition |
| --- | --- | --- | --- | --- |
| `desktop_runtime_capability_discovery.py` | `docs/runtime-adapter-v2.md` — `## Allowed Sources` and `## Contract Family Boundary` | `tests.test_native_runtime_contract_docs.NativeRuntimeContractDocsTests.test_desktop_callable_contract_covers_new_boundaries` | Supported documented Desktop tools, project/target forms, host-aware routing, and unavailable-capability boundary. | The V1 metadata-normalizer request/output schema and helper version are obsolete; no adapter is retained. |
| `desktop_runtime_wrapper_planner.py` | `docs/native-runtime-capabilities.md` — `### Sequential fallback` | `tests.test_native_runtime_contract_docs.NativeRuntimeContractDocsTests.test_contract_covers_capability_families_and_authority` | A missing optional runtime capability changes execution mode but not authority, verification, or completion semantics. | The dry-run result, capability-evidence payload, and V1 fallback prompt are obsolete. |
| `desktop_runtime_create_thread_preflight.py` | `docs/runtime-adapter-v2.md` — `## Contract Version Tracking` and `## Stop Conditions` | `tests.test_native_runtime_contract_docs.NativeRuntimeContractDocsTests.test_desktop_target_selection_preserves_project_and_worktree_intent` | Native create preparation preserves selected project/worktree intent and stops rather than inferring a projectless target. | The V1 `ready`/`fallback`/`stopped` preflight envelope is obsolete and is not authorization. |
| `desktop_runtime_create_thread_authorization_gate.py` | `docs/runtime-adapter-v2.md` — `## Safety Model` | `tests.test_desktop_wrapper_security_fixtures.DesktopWrapperSecurityFixtureTests.test_fixture_evidence_is_present_in_current_native_sources` | Explicit user authorization for state-changing thread actions and separate external-write/destructive boundaries. | The V1 authorization-marker, session-status, and cache-evidence envelope are obsolete. |
| `desktop_runtime_create_thread_executor.py` | `docs/native-runtime-capabilities.md` — `### Desktop thread control plane` | `tests.test_native_runtime_contract_docs.NativeRuntimeContractDocsTests.test_desktop_post_create_visibility_contract` | A ready `threadId` and a queued `clientThreadId` have distinct lifecycle meaning; registration/visibility is not completion. | The injected runner, wrapper flags, and historical response-acceptance logic are obsolete. |
| `desktop_runtime_create_thread_live_smoke.py` | `docs/native-runtime-capabilities.md` — `### Desktop thread control plane`; `docs/runtime-adapter-v2.md` — `## Safety Model` | `tests.test_desktop_wrapper_security_fixtures.DesktopWrapperSecurityFixtureTests.test_fixture_evidence_is_present_in_current_native_sources` | No private runtime state, no authority escalation, and no interchange of queued and ready identities. | The live-smoke entrypoint and its human marker are obsolete; no smoke invocation is retained. |
| `desktop_runtime_read_thread_preflight.py` | `docs/native-runtime-capabilities.md` — `### Desktop thread control plane` | `tests.test_native_runtime_contract_docs.NativeRuntimeContractDocsTests.test_desktop_wait_observation_is_host_aware_and_non_authoritative` | Observation preserves runtime-returned `hostId`, is bounded/non-authoritative, and cannot prove completion. | The V1 read preflight evidence chain and legacy `thread_id` compatibility rule are obsolete. |

The assertion counts total **263** test methods. They are not all independently
valuable security tests. The names above expand to exact canonical paths as
`scripts/desktop_runtime_<name>.py` and
`tests/test_desktop_runtime_<name>.py`.

## Required wrapper-independent security fixture families

The receiving fixture is `tests/test_desktop_wrapper_security_fixtures.py`
with `tests/fixtures/desktop_wrapper_security_invariants.yaml`. Before deleting
a historical test module, it must prove these families with no wrapper
dependency:

1. **Authority boundary** — creation is state-changing; explicit exact user
   authorization is required; cache/readiness records cannot substitute for
   call-site decisions.
2. **Target and routing identity** — the native contract test preserves
   project/target/worktree intent; the wrapper-independent fixture preserves
   returned `threadId` versus queued `clientThreadId` and known `hostId` as
   distinct identities.
3. **Failure and response handling** — auth/permission failures, malformed
   responses, and invalid/missing identities never count as successful creation.
4. **Private-state/external-write boundary** — private runtime state, private
   paths, unpublished hints, and unauthorized writes cannot satisfy a call.
5. **Non-execution** — docs/contract tests create no thread; no daemon,
   sidecar, injected live runner, or background executor replaces the wrapper.

The v2 fixture now preserves the fixture-backed portions of these families as
explicit cases and expected outcomes. The combined successor evidence is
checked through the following exact symbols: the native contract suite checks
target-selection intent, while the wrapper-independent receiver checks the
fixture-backed identity and security cases. Historical symbols are provenance
only and are parsed as text, never imported or executed.

| Security family | Fixture invariant/case IDs | Exact independent test symbols |
| --- | --- | --- |
| Authority boundary | `state-changing-actions-need-explicit-human-authorization`; `cache-or-status-cannot-replace-exact-authorization`; `destructive-approval-cannot-replace-exact-action-authorization` | `DesktopWrapperSecurityFixtureTests.test_fixture_evidence_is_present_in_current_native_sources`; `DesktopWrapperSecurityFixtureTests.test_case_mappings_are_complete_and_reference_existing_test_symbols` |
| Target and routing identity | `response-identities-are-not-interchangeable`; `missing-or-invalid-identity-stops`; `known-host-identity-requires-registry-verification` | `NativeRuntimeContractDocsTests.test_desktop_target_selection_preserves_project_and_worktree_intent`; `DesktopWrapperSecurityFixtureTests.test_fixture_evidence_is_present_in_current_native_sources`; `NativeRuntimeContractDocsTests.test_desktop_fork_preserves_remote_host_identity` |
| Failure and response handling | `auth-or-permission-failure-stops`; `malformed-or-absent-response-stops`; `missing-or-invalid-identity-stops` | `DesktopWrapperSecurityFixtureTests.test_fixture_has_a_complete_and_stable_schema`; `DesktopWrapperSecurityFixtureTests.test_fixture_evidence_is_present_in_current_native_sources` |
| Private-state/external-write boundary | `private-runtime-state-is-prohibited`; `external-writes-remain-separately-authorized` | `DesktopWrapperSecurityFixtureTests.test_fixture_evidence_is_present_in_current_native_sources` |
| Non-execution | `historical-wrappers-do-not-define-native-execution` | `DesktopWrapperSecurityFixtureTests.test_security_fixture_is_independent_of_historical_entrypoint_imports`; `NativeRuntimeContractDocsTests.test_native_core_does_not_depend_on_legacy_desktop_helpers` |

These fixture and native-contract mappings preserve the current security
semantics, not the V1 helper mechanisms, cache schemas, response flags,
injected runner, or smoke entrypoint.

## Later-removal conditions

- A retained semantic must map to a native contract/test, or be explicitly
  classified obsolete. It may not disappear under a generic historical label.
- No current behavior may depend on a wrapper response flag, cache envelope,
  helper version, callable descriptor, or smoke command.
- This crosswalk is planning evidence only. It satisfies neither independent
  review nor the separate destructive-action authorization requirement.
