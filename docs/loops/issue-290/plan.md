# Issue #290 — Controller outcomes

Issue: <https://github.com/jeffery777/codex-dev-skills/issues/290>
Branch: `codex/issue-290-controller-outcomes`
Baseline: `9f5ff271ac46654b112c98b34220ca7b998ffd01`

## Scope and DoD

Separate known unmet prerequisites from controller execution faults. A dedicated
App failure remains mandatory for missing receipt or absent/non-success CI.
Only a verified completed failure plus native-latest readback permits job exit 0.
Unknown, malformed, drifted, API, identity, publication and readback errors remain
nonzero. Reject existing output before access; never reuse a success envelope.
No offline validator/schema, token permissions, ruleset or App authority changes.

Verify missing/valid receipt, CI pending/failure/unknown, stale or invalid receipt,
publication and both readback failures, stale output and no-op handling. Focus on
proper abnormal handling through controlled tests, not producing real physical
failures. Existing success/double-read evidence tests remain applicable.

Prepare patch candidate 0.26.1 with source/package parity and new historical note;
preserve prior candidate records. No tag, Release, deploy or automatic merge.
Hosted controller executes trusted main only: candidate tests cannot prove live
new behavior before merge. Record that limitation explicitly.

## Sequence

Issue created/read back → Issue branch created/pushed before edits → bounded
implementation/tests/docs/version → independent review and Security Diff Scan →
verification and PR readiness. Commit/push/PR/receipt follow their valid authority;
merge and publication remain separate decisions.
