# Context Continuity And Fresh-Context Rollover

This guide defines the public `loop-context-continuity/v1` contract introduced
for Issue #165. It is additive to the existing loop ledger and does not migrate
or reinterpret existing V1/V2 ledger events.

## Quick Assessment

Copy the installed template, replace every placeholder with current repository
evidence, and run the read-only command:

```bash
cp templates/orchestration/context-continuity.template.yaml /tmp/context-health.yaml
./scripts/project-python skills/loop-engineering/scripts/loopctl.py \
  context-health /tmp/context-health.yaml
```

The default `assessment_trigger_rounds` is `2`, but it is configurable. The
threshold only starts assessment. Output always reports
`automatic_rollover_authorized: false`, `runtime_action_performed: false`, and
`task_created: false`.

## Decision Evidence

| Decision | Required evidence |
| --- | --- |
| Continue | Context is healthy, the threshold is not reached, or only token/compaction pressure is present. |
| Reground | Durable sources can be reread but the checkpoint, exclusive transfer, source stop-writing, safe runtime path, or measured benefit is incomplete. |
| Delegate | The high-noise packet is independent and has disjoint ownership; the current delivery owner retains integration. |
| Prepare fresh rollover | Same repository/objective, complete checkpoint, clean supported automatic path, source stopped, destination unique, progress since prior rollover, and non-conflicting rollover identity. |
| Human gate | Product/source ambiguity, material risk, conflicting rollover ID, or repeat rollover without progress. |

The checkpoint digest is computed from canonical UTF-8 JSON with sorted keys.
Exact rollover replay is reported as a no-op and must not dispatch a duplicate
task.

## Fresh Create, Fork, And Delegation

```text
Parallel subagent:
- Goal: isolate an independent noisy packet.
- History: receives only its bounded task brief.
- Ownership: packet-only; main delivery owner remains active.

Fork:
- Goal: continue the same task with completed conversation history.
- History: copied.
- Ownership: sequential transfer for same-directory/worktree continuation.

Fresh rollover:
- Goal: escape stale/noisy context and bootstrap only from durable evidence.
- History: deliberately not copied.
- Ownership: source stops writing; destination becomes the sole delivery owner.
```

For Desktop, a fresh rollover uses an authorized `create_thread` with the
checkpoint branch as an explicit `startingState` and `onMissing: error`;
using `fork_thread` would retain history and therefore changes the requested
semantics. The destination verifies its exact branch and HEAD read-only before
writer ownership activates. For CLI, `fresh-continuation` is a new `codex exec --json` session
whose prompt is appended with the validated checkpoint. The executor accepts
only a clean non-interactive path, verifies canonical `origin` host/path identity, and
writes one atomic at-most-once ledger indexed by rollover ID and checkpoint
digest below the Git control directory before the session call. Ledger updates
use a non-blocking lock, descriptor-relative temporary file, atomic replacement,
and file/directory durability sync. A dirty or interactive CLI assessment selects a
manual/current-session fallback; the executor itself stops without a session
call and the surrounding workflow prepares that fallback artifact. IDE
has no assumed task control plane and uses the same safe fallback.

## Capability Matrix

| Capability | Desktop | CLI | IDE |
| --- | --- | --- | --- |
| Shared context assessment | Yes | Yes | Yes |
| Shared parallel subagents | When exposed | When exposed | When exposed |
| History-preserving fork | `fork_thread` | `codex exec fork` or manual `codex fork` | Only if publicly exposed and qualified |
| Fresh automatic path | Authorized `create_thread` | Clean non-interactive `fresh-continuation` | None assumed |
| Dirty worktree automatic fresh path | No | No | No |
| Missing control-surface fallback | Current task or prompt | Current session or prompt | Current session or prompt |

All runtime actions remain capability-detected and separately authorized. No
workflow depends on unpublished Desktop internals, private CLI state, UI
scraping, app-server clients, daemons, or sidecars.

## Migration And Compatibility

- Existing review/fix round limits continue to work. The new default means the
  second unfinished round requests assessment rather than automatic task
  replacement.
- Existing `start`, `resume`, `fork`, and manual interactive-fork CLI paths are
  unchanged. `fresh-continuation` is additive and requires a valid continuity
  assessment.
- Existing Desktop fork semantics are unchanged. Fresh rollover selects
  `create_thread` intentionally and does not redefine fork lineage.
- Existing loop ledger schema remains supported. Repositories may store the
  template or its digest in their own checkpoint artifacts without making it a
  protected event or authority receipt.
- Graph lineage is optional. Missing or conflicting projections do not change
  canonical repository decisions.

Rollback removes the new assessment/template usage and continues with the
v0.16.3 current-session, subagent, fork, and prompt paths. It does not delete
tasks, sessions, worktrees, runtime state, or repository history.

## Evaluation

```bash
./scripts/project-python scripts/eval-context-continuity.py
./scripts/project-python -m unittest \
  tests.test_context_continuity \
  tests.test_eval_context_continuity \
  tests.test_cli_session_handoff
```

The synthetic suite covers clean/dirty worktrees, interactive/non-interactive
CLI behavior, absent control surfaces, parallel delegation, repeated rollover,
unknown comparison input, and same-context versus fresh-rollover metric routing.
The fresh token total includes bootstrap overhead; a shifted cost or quality
regression fails qualification and selects regrounding instead. These values
are explicitly provenance-labelled synthetic fixtures, not empirical release
evidence. Before release, maintainers must attach paired runs of the same
objective with raw results, measurement method, quality rubric, and all listed
metrics; until then the v0.17.0 release gate remains open.
