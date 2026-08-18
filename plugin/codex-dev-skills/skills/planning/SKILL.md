---
name: planning
description: Create a scoped software development plan with assumptions, risks, DoD, and verification strategy.
---

# planning

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

## Purpose

Use this skill when the user asks for a plan, implementation outline, task breakdown, or risk assessment before code changes.

## Workflow

1. Read the requested scope, repo instructions, README, relevant docs, and current git state when available.
2. Identify facts separately from inference.
3. Define the smallest coherent task slices.
4. List assumptions, risks, human gates, and verification commands.
5. Stop before editing files unless the user explicitly asks to continue into implementation.

## Output

- Objective
- Relevant source-of-truth files
- Proposed task slices
- Definition of Done
- Risks and human gates
- Verification plan
