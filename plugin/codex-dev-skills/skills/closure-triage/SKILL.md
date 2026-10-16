---
name: closure-triage
description: Select the next smallest safe packet from repo policy, project overlays, current state, and verification evidence.
---

# closure-triage

Runtime compatibility: shared

Code Mode tool orchestration: follow
`../../policies/code-mode-tool-orchestration-policy.md` relative to this skill in source or plugin checkouts, or
`${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/code-mode-tool-orchestration-policy.md`
after filesystem installation.

Evidence lifecycle: follow `../../policies/review-artifact-policy.md` in source
or plugin, or `${CODEX_TEMPLATES_DIR:-$HOME/.codex/templates}/orchestration/policies/review-artifact-policy.md`
after filesystem installation, including its full fixed Core reading.

## Purpose

Use this skill when a project needs to decide what to do next: implement, verify, review, document, clean artifacts, or stop at a human gate.

## Workflow

1. Read repo policy, project plan, status or handoff docs, review evidence, and git state.
2. Identify accepted baseline and current delta. Keep compact cause/fix/version/
   replacement references. A replacement must cover the original failure and
   affected boundaries; unrelated PASS does not close unresolved/intermittent
   work. Preserve shared/still-referenced and protected records. Missing retention
   policy/period means retain and pending; closure grants no cleanup authority.
3. List candidate packets.
4. Prefer the smallest packet that advances closure without expanding scope.
5. Stop if source-of-truth files conflict and the conflict cannot be resolved cheaply.

## Output

- Current state facts
- Inferences
- Candidate packets
- Recommended next packet
- Required verification
- Human gate, if any
