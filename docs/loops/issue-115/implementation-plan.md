# Issue #115 Implementation Plan

## Objective

Implement a small CLI-native control-plane adapter after shared orchestration
selects a handoff, without moving task selection or completion authority out of
the shared layer.

## Task Slices

### P0 — Contract And Risk Boundary

- Record the independent CLI/shared/Desktop entry architecture.
- Bind the first implementation to stable `codex exec --json` start/resume
  semantics.
- Define request/result fields, limits, failure taxonomy, and human gates.
- Exclude experimental app-server, private runtime state, interactive UI
  control, automatic retry, and permission widening.

### P1 — Offline CLI Adapter

- Add `skills/cli-session-handoff/SKILL.md`.
- Add a standard-library Python executor under that skill.
- Require an explicit canonical executable, canonical Git worktree, bounded
  prompt, operation, sandbox, and timeout.
- Build argv as an array and parse bounded JSONL without storing raw output.
- Emit a bounded receipt for completed, failed, stopped, fallback, and timeout
  cases without returning untrusted child-summary text.

### P2 — Tests And Distribution

- Add fake-executable fixtures through temporary files outside the repository.
- Cover start/resume argv, success, malformed/duplicate events, missing session
  ID, timeout, non-zero exit, output limits, unsafe paths, symlinks, permission
  widening, child-summary omission, private-clone isolation, and bounded patch
  integration.
- Add the skill to a dedicated CLI catalog/installer group that depends on the
  shared delivery workflow without changing shared or Desktop packaging.
- Add focused contract tests to repository validation.

### P3 — Documentation And Review Closure

- Update README, runtime capability/compatibility docs, skill selection,
  troubleshooting, workflow routing, and examples.
- Run focused tests, full unit tests, repository validation, diff hygiene, and
  privacy checks.
- Run deep code review because the adapter launches an external executable and
  manages permission boundaries.
- Stop at the live-smoke and publication human gates.

## Request Contract

The executor accepts one JSON object on stdin:

```json
{
  "schema_version": 1,
  "operation": "start",
  "codex_executable": "/absolute/path/to/codex",
  "workspace": "/absolute/path/to/git-worktree",
  "prompt": "bounded handoff prompt",
  "sandbox": "read-only",
  "timeout_seconds": 900,
  "expected_head": "40-hex Git commit",
  "prompt_boundary_version": "no-publication-no-recursion/v0",
  "authorization": {
    "marker": "human-approved-single-cli-session-handoff",
    "runtime_session_mutation_authorized": true,
    "external_write_authorized": false,
    "destructive_action_approved": false,
    "sandbox_ceiling": "read-only"
  }
}
```

`resume` additionally requires `session_id`. The initial adapter supports only
`read-only` and `workspace-write`; it does not accept arbitrary CLI flags,
model overrides, approval bypasses, alternate config, extra writable roots, or
environment overrides. Sparse-checkout worktrees and indexes containing
submodules return a capability fallback because the private clone does not
claim to reproduce those worktree shapes.

## Result Contract

The result uses `codex-cli-session-handoff/v0` and includes:

- operation and status/failure class;
- Codex CLI version evidence;
- canonical workspace and exact Git HEAD;
- public session identifier when emitted;
- process exit status and terminal event;
- a fixed omission marker instead of the untrusted final agent summary;
- booleans proving no shell, private-state read, external platform write, or
  completion claim was performed by the adapter.

The result never includes argv with the prompt, raw stdout/stderr, credentials,
environment values, user configuration, or private session paths.

## Risks And Controls

| Risk | Control |
| --- | --- |
| Prompt or path reaches a shell | Invoke a fixed argv array with `shell=False`; reject shell/config passthrough. |
| Executable identity probe hangs, floods output, or leaves an observed child | Run it in a disposable directory with a bounded process group, descendant inventory, timeout, and streaming stdout/stderr limits. |
| Child gains broader permissions | Allow only read-only/workspace-write and require caller authority for the chosen sandbox. |
| Tool subprocess inherits ambient credentials | Fix `shell_environment_policy.inherit="core"` and retain the default KEY/SECRET/TOKEN exclusions. |
| Wrong repository is modified | Canonicalize workspace, require a Git worktree, and match exact expected HEAD before launch. |
| Malformed/hostile JSONL corrupts state | Limit bytes and line length, require JSON objects, whitelist relied-on fields, and fail closed on duplicate/conflicting lifecycle events. |
| Output leaks credentials or local paths | Keep no raw transcript and replace the untrusted final summary with a fixed omission marker. |
| Child completion is trusted | Mark the receipt non-authoritative and retain parent integration/review responsibility. |
| A detached child outlives polling cleanup | Run Codex only in a disposable private clone, remove its source remote, transfer at most one bounded patch after rechecking the original worktree, and retain process-group/PID cleanup as defense in depth. Pair every observed PID with its OS start token so PID reuse cannot redirect cleanup. |
| CLI contract drifts | Record observed version, use fake-contract tests, and classify unknown/malformed events without inventing success. |

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest \
  tests.test_cli_session_handoff \
  tests.test_native_runtime_contract_docs \
  tests.test_installer_agent_profiles
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
bash -n install.sh scripts/validate-repo.sh
./scripts/validate-repo.sh
git diff --check
git status --short --branch
```

The live smoke is excluded from normal verification and requires a separate
explicit authorization naming the operation, workspace, sandbox, and prompt.

## Review Plan

- Security-sensitive implementation review: `code-review-deep`
- Documentation review: `docs-review`
- Formal implementation gate before commit or PR readiness:
  `code-review-gate`
- Base-to-head readiness review if publication is later authorized:
  `merge-review-deep`
