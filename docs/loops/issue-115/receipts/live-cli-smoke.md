# Issue #115 Minimal Live Codex CLI Smoke

Initial run: 2026-07-24  
Last verified: 2026-07-27

## Scope And Authority

The user explicitly authorized one minimal real Codex CLI test. The adapter
used:

- operation: `start`;
- Codex CLI version: `0.145.0`;
- sandbox: `read-only`;
- target: a clean temporary clone at Git HEAD
  `9782a509d7a4e133e398737930b294ee0f6341fa`;
- prompt: return one fixed marker without reading files, running tools, or
  modifying content;
- timeout: 60 seconds;
- publication and destructive authority: absent.

The local session identifier, executable path/digest, temporary path, and raw
transcript are intentionally not persisted in this public repository artifact.

## Result

| Evidence | Result |
| --- | --- |
| Adapter contract | `codex-cli-session-handoff/v0` |
| Status | `completed` |
| Exit status | `0` |
| Terminal event | `turn.completed` |
| Final summary | Expected fixed marker returned |
| Public session identifier | Valid UUID emitted; value intentionally omitted |
| Target Git state after execution | Exact expected HEAD; clean worktree |
| Shell used by adapter | No |
| Raw transcript persisted by adapter | No |
| Repository completion claimed | No |

## Environment Limitation

The first attempt from the Desktop-managed filesystem sandbox returned
`nonzero_exit` before producing a public session identifier. The same exact
read-only request succeeded after the user-approved command was rerun outside
that parent sandbox.

The successful rerun demonstrates compatibility with the real Codex CLI
contract. The contrast strongly suggests a parent-sandbox restriction on CLI
runtime state, but the adapter intentionally does not retain raw stderr, so
that root cause is an inference rather than verified evidence.

No resume operation, repository mutation, commit, push, pull request, merge, or
external platform write was performed.

## Post-fix Recheck

After the fixed argv added the documented
`shell_environment_policy.inherit="core"` override and retained the default
KEY/SECRET/TOKEN exclusions, the same minimal test shape was rerun against a
new empty temporary Git repository:

| Evidence | Result |
| --- | --- |
| Codex CLI version | `0.145.0` |
| Status | `completed` |
| Exit status | `0` |
| Terminal event | `turn.completed` |
| Final summary | `ISSUE115_FINAL_SMOKE_OK` |
| Public session identifier | Valid UUID emitted; value intentionally omitted |
| Sandbox | `read-only` |
| Target Git state | Exact expected HEAD; clean worktree |

The recheck required no file reads, tool calls, repository mutation,
publication, or destructive authority. Local executable identity, temporary
path, receipt digest, raw transcript, and session UUID remain intentionally
excluded from this public artifact.
