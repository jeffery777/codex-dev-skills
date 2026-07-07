# Loop Engineering

Loop engineering in this repository means a bounded, evidence-driven agent workflow that repeatedly decides what to do next, routes to the smallest existing skill, verifies the result, reviews or gates when appropriate, and either continues, hands off, stops for a human gate, or completes only when evidence proves the objective.

The user-facing entrypoint is `loop-engineering`.

## What It Adds

`loop-engineering` gives maintainers a clear way to ask Codex to keep a bounded objective moving when the objective, source of truth, Definition of Done, verification, and human gates are clear.

It adds a shared loop vocabulary:

- bootstrap from durable repository files;
- classify the current state;
- route to existing focused skills;
- verify and review evidence;
- decide whether to continue, hand off, stop, or complete.

It does not add a scheduler, daemon, Desktop runtime adapter, platform writer, release bot, or replacement for existing phase skills.

## Relationship To Existing Skills

`loop-engineering` is the outer entrypoint. It keeps the existing skills independently usable:

- Use `implementation-slice` directly for one clear coding task.
- Use `docs-update` directly for a bounded docs sync.
- Use `project-orchestrator` directly when the main need is route selection or bounded review closure.
- Use `project-delivery` directly when the objective is one bounded delivery effort in the current session.
- Use `milestone-continuation` directly when repeated milestone wakeups are the distinctive requirement.
- Use `task-continuation` directly when the immediate need is next-task selection or a handoff artifact.
- Use review primitives and formal gates directly when the task is review or readiness evidence.
- Use Desktop-specific skills directly when Desktop worker or thread delegation is explicitly intended.

Use `loop-engineering` when the user wants the agent to own the full repeated loop and choose among those skills as state changes.

## Required Source Of Truth

A loop should have enough durable context to re-bootstrap without trusting chat memory:

- repo instructions such as `AGENTS.md`;
- a loop spec, project spec, issue, or implementation plan;
- task manifest or current task summary when multiple tasks exist;
- review evidence or gate reports when relevant;
- verification commands and expected artifacts;
- current git branch, status, upstream, and diff.

If those files do not exist, the first loop iteration should create or propose them instead of pretending the objective is already executable.

## Runtime Compatibility

Shared behavior works in Codex CLI and Codex Desktop with repository files, ordinary shell commands, git inspection, and durable artifacts.

Desktop-only behavior includes heartbeat wakeups, worker delegation, thread creation, thread forking, thread messaging, and thread inspection. Those actions require documented runtime capability and exact user authorization.

The CLI fallback is a current-session sequential path, paste-ready prompt, task brief, or continuation prompt.

## Completion Standard

A loop objective is complete only when current evidence proves the actual requirements:

- all explicit requirements are satisfied;
- all named artifacts exist and are aligned;
- DoD items are verified;
- required review or gate evidence exists;
- no human-gate condition remains unresolved;
- residual risk is reported.

Passing tests, plausible intent, chat summaries, or worker self-reports are not enough by themselves.
