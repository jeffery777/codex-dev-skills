# Live Notify-Only Adoption Receipt

## Scope

This receipt records a bounded V2c-B adoption exercise for Issue #107 on
2026-07-23. It is a sanitized human-readable summary, not a runtime log,
authorization record, completion authority, or reusable Operational Evidence
contract.

## Environment Boundary

- Repository identity: `github.com.jeffery777.codex-dev-skills`
- Repository release baseline: v0.9.0
- Test branch: `codex/issue-107-v0.9.1-alignment`
- Platform family: macOS arm64
- Codex CLI: 0.144.6
- GitNexus CLI: 1.6.9
- Adoption mode: `notify-only`
- Refresh command: absent

The active hook definition and machine-local binding configuration are not
tracked. This receipt excludes private paths, host/user identifiers, active
configuration, trust records, raw logs, transcripts, local databases, and
secret values.

## Configuration And Trust

- The shipped V2c-B runner accepted the active configuration as `valid` in
  `notify-only` mode.
- The project hook file remained ignored by Git.
- The Codex hook review showed one installed and active `SessionStart` hook and
  one installed and active `PostToolUse` hook from the project layer.
- Both exact commands were reviewed through the normal Codex trust flow. No
  trust-bypass option was used.

## Observed Lifecycle Evidence

### SessionStart

Two actual Codex CLI lifecycle attempts were observed:

1. The first startup invoked the named GitNexus freshness hook but reached the
   bounded adapter-probe deadline. The hook emitted a fail-safe skip advisory
   and explicitly performed no refresh or index adoption.
2. A clean retry invoked the same named `SessionStart` hook and completed
   without an advisory. This is consistent with a fresh index disposition,
   for which the shipped notify-only evaluator is intentionally silent.

The first outcome is retained as a runtime limitation rather than discarded.
It demonstrates fail-safe behavior when the adapter probe cannot qualify
within the hook deadline.

### PostToolUse

After one read-only shell action, Codex CLI invoked the named `PostToolUse`
GitNexus hook. It completed without an advisory or refresh. This is consistent
with the shipped rule that a dirty working tree at the same indexed commit
does not request refresh in notify-only mode.

## Safety Result

- No hook-driven `gitnexus analyze` command ran.
- No index was adopted by the hook.
- No tracked file contains the active hook configuration.
- Hook results remained advisory and did not authorize mutation, external
  writes, review closure, promotion, or completion.

## Coverage Limits

- This exercise covers Codex CLI 0.144.6 on one macOS arm64 environment.
- Codex CLI 0.145.0, Codex Desktop hook execution, Linux, and Windows were not
  tested.
- No changed-HEAD advisory case was manufactured because doing so was not
  necessary to prove hook activation and would have expanded the exercise.
- No `auto-on-demand` path or refresh command was configured or tested.
- The outcome is evidence for refining future public contracts, not itself a
  normative run-receipt schema.
