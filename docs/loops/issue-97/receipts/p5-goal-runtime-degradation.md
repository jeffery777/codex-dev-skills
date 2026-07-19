# P5 Goal Runtime Degradation

Status: **coordination degraded; delivery and scan state remain resumable**.

Two user-requested full-objective Goals were observed changing to `blocked`
without an agent-issued terminal Goal update. The latest instance changed after
approximately 616 seconds and 61,176 reported tokens, with no configured token
budget and no blocker reason exposed by the Goal read interface. During that
interval the owning test suite completed 132/132 successfully. No security
worker/classifier call occurred in that interval, and the preceding security
workers explicitly reported no classifier refusal.

The runtime exposes Goal create/read/terminal-update operations but no
resume/delete operation. A create attempt while the blocked Goal remained
present was rejected because the blocked Goal was still considered unfinished;
only the user UI could delete it. The current `loop-engineering` contract already
requires a running scan to continue through current-session/task-continuation
when Goal projection is blocked, so the delivery continued from repo-owned and
scan-native artifacts.

Durable follow-up (separate bounded workflow objective):

- owner: Loop Engineering runtime-integration maintainer;
- trigger: next Goal/runtime-capability maintenance slice;
- update existing `loop-engineering`, `native-runtime-capabilities`, Desktop UX
  adapters, unit tests, and evals rather than creating a new recovery skill;
- classify blocked Goal plus unavailable resume/clear control once, prohibit
  recreate loops, degrade to sequential/current-session execution, preserve
  repo/scan authority, and emit bounded progress heartbeats;
- host-level root fix: expose blocker reason and documented resume/delete
  callables or prevent spurious automatic terminalization.

This receipt records a runtime limitation and recovery decision. Goal state is
not completion evidence, and this receipt does not authorize or claim merge,
release, or objective completion.
