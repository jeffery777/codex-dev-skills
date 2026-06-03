# Reusable Workflow Contract

This contract defines the shared shape for Codex CLI and Codex Desktop development workflows.

## Shared Phases

1. Read source-of-truth files and current state.
2. Plan the smallest safe task slice.
3. Implement or delegate within scope.
4. Verify with relevant commands.
5. Inspect the diff.
6. Run review gates when required.
7. Sync docs or status when required.
8. Stop at human gates for ambiguity, risk, destructive actions, or external writes.

## Runtime Differences

Codex CLI may execute phases sequentially in one session or through handoff artifacts.

Codex Desktop may use main-agent orchestration and worker delegation, but Desktop runtime behavior does not replace durable repository artifacts or human gate policy.

## Review And Merge

Review gates provide quality evidence. They do not by themselves authorize commit, push, merge, deploy, or platform publication.
