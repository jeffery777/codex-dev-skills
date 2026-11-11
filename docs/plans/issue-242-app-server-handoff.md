# #242: App Server task handoff

Status: implementation in progress. This plan does not declare review, release,
installation, or production runtime qualification.

## Requirement sources and preserved conditions

The maintainer revised [Issue #242](https://github.com/jeffery777/codex-dev-skills/issues/242)
on 2026-11-10 to include the official App Server alternative. Preserve the old
diagnosis and draft [PR #244](https://github.com/jeffery777/codex-dev-skills/pull/244).
Do not create a replacement Issue or claim that native task tools were restored.

- Restore useful create, continue, and fork operations when native tools are
  missing. Check native discovery before selecting a compatible alternative.
- Development handoff is the final objective. Read-only is the measured
  baseline, not a permanent restriction. Keep explicit workspace-write authority,
  target ownership, sandbox and verification separate from that baseline.
- Use one local stdio App Server per invocation on the execution host. Do not
  implement SSH transport, a listener, shared daemon, private state reader or
  general RPC proxy. Use the selected CLI's existing authentication.
- Preserve user work, protected consumer repositories, fixed Core and the paused #385 research. No commit,
  push, PR, merge, release or installation is authorized by this plan.
- Maintain explicit session-action authority. A JSON authorization field records
  a caller decision; it cannot create human permission.

## Evidence and limits

Prototype tests on macOS CLI 0.166.0 and Linux CLI/App Server 0.167.0 completed
read-only work, continuation in one connection, continuation after process exit,
and history forks. Desktop readback and maintainer visual confirmation covered
the correct local and remote projects. Prototype results do not qualify new code.
Private IDs, host aliases, paths, transcripts and screenshots stay outside Git.

Desktop-loaded tasks can reject a separate App Server's resume with active writer.
Idle and a process-local loaded list do not establish writer ownership or release.
Stop that operation; do not clear locks, stop shared processes, or retry by time.

[Issue #251](https://github.com/jeffery777/codex-dev-skills/issues/251) remains open:
its old exec supervisor reported child-identity EPERM after a session call, with
unknown completion. It is not the same error as the observed App Server RPC
writer refusal. Keep the old executor unchanged, do not suppress its errors,
and do not claim a new route fixes that original condition.

`cwd`, App Server `projectId`, Desktop registry and visual placement are separate
evidence. API projectId:null is not proof of absent Desktop placement. Appearance
in both project and global views does not alone prove duplication or a defect.

## Design and scope

Extend `cli-session-handoff` with a separate App Server reference and executor.
Keep the existing exec/private-clone route unchanged. Desktop may select the new
route after discovery and an explicit task-action request, rather than pretending
to possess an absent native tool.

The executor accepts a bounded JSON request on stdin: operation, selected CLI,
existing workspace, sandbox, prompt where needed, exact thread ID for continuation
or fork, bounded timeout and recorded authorization. Start creates and runs one
or up to eight sequential authorized turns in the same connection; authority must
cover the complete prompt list. Resume continues one idle target; fork copies completed history and may run
a supplied, separately authorized prompt in the same connection. It never steers
an unknown active turn. Read metadata and history through public RPCs only.

Default to read-only. Workspace-write requires explicit caller authorization and
exclusive target ownership; use the selected directory as the writable root and
do not silently add network or publication rights. Git targets record/check their
expected HEAD; non-Git targets are supported. Runtime records can be written by
Codex even when project operations are read-only.

Do not inherit integration-tool authority from the host. Use fixed invocation-local
feature overrides and per-server MCP disable settings, verify the effective public
MCP inventory (absent or explicitly disabled with no capabilities) before any
task turn, and stop on unknown/unsupported results. Keep
host configuration untouched. Plugin skills will not autoload in this restricted
child; the caller supplies necessary instruction files explicitly. There is no
external-tool-enabled MVP mode. This is a bounded task route, not a complete host
isolation or defense against a deliberate trusted operator.

Use request IDs, validate returned thread/turn/cwd, match completion to that turn,
and retain IDs after partial success. Distinguish known refusal, completion failure
and unknown effects. No automatic replay. Bound JSONL/output and timeout; reject
unexpected client approval/tool requests instead of granting permissions. Cleanup
may affect only this invocation's process/turn, never an existing owner.

Return a private, bounded receipt with operation, actual version, IDs, permission
mode, status, readback coverage and untrusted result text. Do not serialize prompt,
credentials or raw stderr into public records. Child output is evidence to inspect,
not repository completion or new authority.

## Verification and review

This changes subprocess/RPC, permission and persistent-thread boundaries: use early
independent deep design/security review, then independent code/docs review and a
proportional Security Diff Scan on the actual diff. Effective reviewer read-only
conditions must be established or a matching explicit exception verified; writable
role instructions alone do not qualify. No exception is presumed from another task.

Offline fake-server tests cover normal start/resume/fork, identity and cwd mismatch,
event interleaving, failed completion, writer refusal, early exit, malformed/oversized
output, timeout and unknown effects without retry. Verify workspace-write authority
and sandbox parameters, plus preservation of the old executor. Add the module to
the existing native-runtime shard; verify filesystem/plugin packaging and parity.

Use `./scripts/project-python` for this repository's scripts/tests. Live acceptance
of the new code must distinguish local/remote and read-only/workspace-write. Any
write probe uses a test-owned disposable target, with a simple intended artifact
and protected sentinel. No actual development target is qualified by a fake test.
Record unrun or blocked checks and the candidate they affect.

## Tradeoffs and stopping point

Native tools remain preferable when they satisfy the requested action. The new
route restores bounded tasks without requiring the retired MCP server, but needs
protocol maintenance and cannot take over another writer. Reusing the old exec
supervisor would conflate its patch/private-clone contract and unresolved #251
observation path with the new RPC lifecycle; keep the boundary explicit instead.
Do not add a scheduling, retry, cache, qualification-store or version-monitoring
framework. Stop after scoped requirements and necessary checks pass; do not seek
protection against arbitrary deliberate host tampering.

English follows ASD-STE100 principles; full conformance has not been verified.
