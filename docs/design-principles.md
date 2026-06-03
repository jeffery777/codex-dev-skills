# Design Principles

- Public-first: no private paths, local runtime files, or machine-specific assumptions.
- Codex-focused: workflows target Codex CLI and Codex Desktop.
- Clear names: skill names should be understandable without private context.
- Runtime honesty: Desktop-only and plugin-dependent behavior must be labeled.
- Read before write: inspect source-of-truth files and current state before mutation.
- Human gates: stop for destructive actions, external writes, product ambiguity, and material risk.
- Review discipline: review mode is read-only unless the user explicitly asks for fixes.
- Evidence over confidence: merge readiness depends on inspected scope, review findings, and verification evidence.
