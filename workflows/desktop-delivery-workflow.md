# Desktop Delivery Workflow

Runtime compatibility: desktop

Use this workflow in Codex Desktop when the user delegates a bounded project objective.

1. Main agent reads durable repo artifacts, current files, and git state.
2. Main agent defines source-of-truth, phase plan, ownership, verification, and human gates.
3. Worker tasks are bounded and include expected files, DoD, and verification.
4. Workers do not commit, publish, merge, deploy, or perform destructive actions.
5. Main agent integrates outputs, checks ownership, and runs verification.
6. Main agent runs review-before-commit gates.
7. Main agent prepares PR or merge readiness evidence.
8. Main agent stops for human approval before external writes or final merge/deploy actions.

CLI fallback: use `project-delivery` and `project-orchestrator` with generated task briefs and sequential review gates.
