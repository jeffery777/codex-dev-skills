# Agent Delegation Policy

Use this policy when a workflow delegates work to another agent, session, or worker.

## Delegation Rules

- Delegate only bounded tasks with clear scope, expected files, DoD, and verification.
- The delegating agent remains responsible for integration, review, and human gates.
- Workers must not commit, push, publish, merge, deploy, or perform destructive actions.
- Workers must report changed files, commands run, skipped checks, risks, and open questions.
- Worker summaries are evidence, not source of truth. Re-check important claims against repository files.

## Task Brief Requirements

Each delegated task should include:

- objective
- in-scope and out-of-scope work
- source files and policies to read
- expected outputs
- verification commands
- stop conditions

## Stop Conditions

Stop delegation when ownership overlaps, source-of-truth files conflict, the task requires a product decision, or the worker would need external write permission.
