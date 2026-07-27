# Issue #115 Review Disposition

This ledger records findings raised during the CLI session handoff deep code
and documentation reviews. Runtime summaries do not close findings; the final
diff and rerunnable verification evidence do.

| Finding ID | Severity | Disposition | Evidence |
| --- | --- | --- | --- |
| `CLI-MF-RECEIPT-LEAK` | MUST-FIX | Fixed | Invalid requests and launch failures now return stable classifications without echoing attacker-controlled operations, revisions, paths, or exceptions. |
| `CLI-MF-SCHEMA-STRICT` | MUST-FIX | Fixed | Request, authorization, and JSONL objects reject unknown fields, duplicate keys, invalid booleans, conflicting lifecycle events, and out-of-order terminal events. |
| `CLI-MF-EXECUTABLE-RACE` | MUST-FIX | Fixed | The adapter records the canonical executable digest and rechecks it immediately before launch. |
| `CLI-MF-WORKTREE-RACE` | MUST-FIX | Fixed | Canonical worktree identity, clean state, and exact 40-character HEAD are rechecked immediately before launch. |
| `CLI-MF-PROCESS-CLEANUP` | MUST-FIX | Fixed | POSIX process groups receive bounded termination on timeout or interruption; non-POSIX hosts fail closed. |
| `CLI-MF-OUTPUT-BOUND` | MUST-FIX | Fixed | Git reads, stdout, stderr, JSONL lines/events, and returned summaries have explicit bounds. Raw transcripts are not persisted. |
| `CLI-MF-RESUME-IDENTITY` | MUST-FIX | Fixed | Resume accepts only an exact canonical UUID and requires the emitted public session UUID to match it. |
| `CLI-MF-PROMPT-BOUNDARY` | MUST-FIX | Fixed | The adapter appends a fixed versioned no-publication/no-recursion boundary and sends the prompt through stdin, never argv. |
| `CLI-MF-REDACTION` | MUST-FIX | Fixed | The receipt no longer returns untrusted child-summary text; it emits one fixed omission marker. |
| `CLI-MF-USER-CONFIG` | MUST-FIX | Fixed | Child execution uses `--ignore-user-config`; arbitrary config, flags, environment overrides, and writable roots are not accepted. |
| `CLI-SF-VERSION-ERRORS` | SHOULD-FIX | Fixed | Version probing requires a strict semantic version and does not return hostile version output or raw process errors. |
| `CLI-SF-INVALID-TYPES` | SHOULD-FIX | Fixed | Invalid or unhashable operation values fail with stable validation errors rather than raising. |
| `CLI-DOC-AUTH-EXAMPLE` | SHOULD-FIX | Fixed | The implementation-plan request example now includes the required exact authorization object. |
| `CLI-DOC-STDIN` | SHOULD-FIX | Fixed | The loop spec now documents stdin prompt delivery instead of a prompt argv. |
| `CLI-SF-DESKTOP-PACKAGE-CLOSURE` | SHOULD-FIX | Fixed | `cli-session-handoff` now belongs to the dedicated CLI-only `codex-cli-session-handoff` group. Catalog closure and isolated-installer tests prove that the shared and Desktop groups do not install it transitively. |
| `CLI-SF-APPROVAL-POLICY` | SHOULD-FIX | Fixed | The fixed argv now sets `--ask-for-approval never`, so a child cannot request a permission escalation and the no-widening contract does not depend on a CLI default. |
| `CLI-MF-AMBIENT-SECRET-ENV` | MUST-FIX | Fixed | Fixed argv sets `shell_environment_policy.inherit="core"` with the CLI's default KEY/SECRET/TOKEN exclusions; receipt output independently omits the untrusted child summary. |
| `CLI-MF-DESCENDANT-CLEANUP` | MUST-FIX | Fixed | macOS/Linux execution inventories and terminates observed descendants as defense in depth. Target integrity no longer relies on polling completeness; see `CLI-MF-FAST-DETACHED-ESCAPE`. |
| `CLI-SF-UNINSTALL-DEPENDENCY-CLOSURE` | SHOULD-FIX | Fixed | Single-group uninstall now removes only the selected group, preserves shared dependencies, and refuses direct shared-group removal while installed same-root dependents remain. |
| `CLI-SF-TEST-ENV-ISOLATION` | SHOULD-FIX | Fixed | Installer tests explicitly remove every supported installer target/opt-in override before invoking `install.sh`; a sentinel regression proves inherited custom targets are not modified. |
| `CLI-MF-INVENTORY-ERROR-SUCCESS` | MUST-FIX | Fixed | Cleanup now stops the inventory worker and requires its final availability check before a successful result; inventory failure is classified as `termination_error`. |
| `CLI-SF-POST-TERMINAL-EVENT` | SHOULD-FIX | Fixed | The JSONL state machine now rejects completed agent messages before `thread.started` and every non-terminal event after a terminal turn event. |
| `CLI-SF-INSTALLED-DOC-LINK` | SHOULD-FIX | Fixed | The installed skill now derives its canonical request shape from the bundled executor's non-live `--example` output instead of a repository-only Issue document. |
| `CLI-NIT-CLI-GROUP-PLAN` | NIT | Fixed | The implementation plan now names the dedicated CLI catalog/installer group and its shared dependency without describing the adapter as part of the shared package. |
| `CLI-MF-FAST-DETACHED-ESCAPE` | MUST-FIX | Fixed | The child now runs in a disposable private clone with its source remote removed. Read-only changes are discarded; workspace-write transfers only a bounded binary patch after rechecking the original clean worktree, so an unobserved descendant cannot directly retain target-worktree authority. |
| `CLI-MF-INCOMPLETE-SECRET-REDACTION` | MUST-FIX | Fixed | The adapter returns a fixed omission marker instead of attempting finite-pattern redaction of untrusted child-summary text. |
| `CLI-SF-CUSTOM-PROFILE-ROOT` | SHOULD-FIX | Fixed | Same-root dependency preflight now treats every non-empty per-root `agent-profile-*.tsv` ownership record as an installed profile deployment, including previously selected custom roots. |
| `CLI-MF-CHILD-COMMIT` | MUST-FIX | Fixed | Patch capture compares child HEAD with the authorized expected HEAD and fails with `child_boundary_violation` before integration if the child commits or otherwise moves HEAD. |
| `CLI-MF-NONSTANDARD-WORKTREE` | MUST-FIX | Fixed | Validation rejects sparse-checkout worktrees and indexes containing Git submodules before session launch because the private clone does not claim to reproduce those worktree shapes. |
| `CLI-SF-SUMMARY-RETENTION` | SHOULD-FIX | Fixed | JSONL parsing records only that a completed agent message was present and immediately returns the fixed omission marker; it no longer retains summary strings in a list or calls a misleading redaction helper. |
| `CLI-SF-DOC-ISOLATION-FAILURES` | SHOULD-FIX | Fixed | The skill, example, and troubleshooting guide now document private-clone behavior, omitted summaries, unqualified worktree shapes, and isolation/integration/boundary failure classes. |
| `CLI-MF-PID-REUSE` | MUST-FIX | Fixed | Descendant inventory now records an OS process-start token with each PID and rechecks it before liveness decisions or signals, so a recycled PID is not treated as the original child. |
| `CLI-MF-VERSION-PROBE-BOUNDARY` | MUST-FIX | Fixed | The untrusted executable version probe now runs in a disposable directory and new process group, bounds stdout/stderr and time while streaming, inventories descendants, and cleans up before accepting a strict version identity. |
| `CLI-SF-SESSION-CALL-RECEIPT` | SHOULD-FIX | Fixed | `session_call_performed` is set only after `Popen` succeeds; target, executable, or private-clone failures before launch no longer claim that a CLI session call occurred. |
| `CLI-SF-REQUEST-READ-BOUND` | SHOULD-FIX | Fixed | File-backed requests now read at most the configured input limit plus one byte before rejecting oversized input, matching the existing bounded-stdin behavior. |
| `CLI-NIT-REDACTED-TEST-NAME` | NIT | Fixed | The success test now describes a bounded receipt rather than obsolete summary redaction behavior. |
| `CLI-MF-AMBIENT-GIT-TARGET` | MUST-FIX | Fixed | Every Git identity and dirty-state probe now removes ambient repository, worktree, index, object-store, namespace, discovery, and command-scoped config selectors before invoking native Git. Version probing and the CLI child receive the same target-neutral environment boundary. A two-repository regression proves hostile `GIT_DIR` / `GIT_WORK_TREE` values cannot substitute another repository's HEAD. |

## Final State

- MUST-FIX open: 0
- SHOULD-FIX open: 0
- NIT open: 0
- Needs Human Decision: 0
- Deferred: 0

Gate result: **PASS**. The post-ambient-Git-remediation deep code review found
no remaining MUST-FIX, SHOULD-FIX, NIT, or open question. Current
implementation verification passes. A fresh security diff scan of the changed
snapshot remains required before commit or PR readiness.

The separately authorized minimal live Codex CLI smoke completed successfully.
It predates the private-clone and ambient-Git remediation; the current boundary
is covered by offline tests and no additional live session was created. The
sealed `d36bc891-0b28-4fd9-b019-ec6840be1def` scan is historical pre-fix
evidence with zero reportable security findings; it reproduced the functional
target-identity defect and therefore cannot serve as final snapshot evidence.
Publication, PR readiness, and merge readiness remain separate gates.

Final evidence:

- `receipts/verification-report.md`
- `receipts/live-cli-smoke.md`
- `skills/cli-session-handoff/scripts/cli_session_handoff.py`
- `tests/test_cli_session_handoff.py`
