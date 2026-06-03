# Runtime Compatibility

This repository uses four compatibility labels.

## `shared`

Works in Codex CLI and Codex Desktop using repository files, ordinary shell commands, git inspection, and durable artifacts. Shared workflows must not require Desktop-only orchestration.

## `cli`

Designed primarily for Codex CLI. A Desktop user may still follow the workflow manually, but the skill should document the fallback.

## `desktop`

Requires Codex Desktop behavior such as main-agent orchestration, worker delegation, or Desktop-specific handoff. Desktop workflows must not be presented as guaranteed CLI workflows.

## `plugin-dependent`

Requires an installed plugin, connector, or platform-specific tool. The dependency must be named, and the workflow must define what happens when the dependency is unavailable.

## Metadata

Every skill should include a runtime line near the top:

```markdown
Runtime compatibility: shared
```

The README skill table must include the same value.

## Fallbacks

Desktop-only workflows should provide a CLI fallback such as generated task briefs, separate CLI sessions, or manual review gates.

CLI-only workflows should provide a Desktop fallback such as running the same read-plan-implement-verify sequence in a Desktop thread, with Desktop-only actions clearly omitted.

## Evidence

Evidence should state where it came from:

- CLI evidence: command, working directory, exit status, and relevant output summary.
- Desktop evidence: thread action, worker output, artifact path, screenshot path, or manually verified UI state.

When evidence is incomplete, mark the claim as unverified.
