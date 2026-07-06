---
name: closure-triage
description: Select the next smallest safe packet from repo policy, project overlays, current state, and verification evidence.
---

# closure-triage

Runtime compatibility: shared

## Purpose

Use this skill when a project needs to decide what to do next: implement, verify, review, document, clean artifacts, or stop at a human gate.

## Workflow

1. Read repo policy, project plan, status or handoff docs, review evidence, and git state.
2. Identify accepted baseline and current delta.
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
