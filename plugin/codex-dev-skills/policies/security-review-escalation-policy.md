# Security Review Escalation Policy

Follow [fixed Core loading](core-contract-loading.md) and read full review/security,
including [review-risk-timing](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-risk-timing)
and [review-security](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-security).
Assess risk at task start and on objective, scope, design or impact changes;
unknown is not low. For high risk, obtain independent deep design review and
threat/security analysis early, then deep code review and necessary proportional
Security Diff Scan when substantial code/diff is available. Do not wait for the
final candidate to start. Bind each result to its actual revision, complete diff
(including uncommitted content), assumptions and scope.

Routine code review should include baseline security checks. Escalate to deep review when the change touches:

- credentials or private keys
- permissions, identity, or tenant boundaries
- sensitive user data
- payments or billing
- file upload or parsing
- external APIs
- migrations or persistent data
- deployment or infrastructure
- dependency supply chain
- cryptography or randomness

Escalated review should check source-to-sink flow, failure modes, rollback,
logging, and whether verification evidence is strong enough for the risk.
Assess scan applicability from actual security/trust/permission/data/execution/
dependency/installation impact and concrete concerns, not file extensions or a
clean ordinary review. Record examined scope and rationale for not applicable;
NOT_RUN and not applicable are not Passed.

## Project Policy, Capability Gaps And External Evidence

Before choosing checks, apply fixed Core's full review/security contract. Resolve
the effective policy's source, approval authority and scope against higher-priority,
charter, platform and non-waivable company requirements. Record a decision that a
check is not required separately from a required check that has not run. A PoC
label, a claimed role, an agent score or a missing tool does not grant an exception.

For the actual runtime, use surfaced capabilities and supported bounded discovery
to check the required tools/plugins and their data/permission boundaries. In the
existing report, record check status, confirmed availability, reason, actual
coverage and any required external follow-up. Use `NOT_RUN` for an unexecuted
required check and `UNAVAILABLE` only for confirmed missing capability; preserve
unknowns. Do not record a gap as a vulnerability, not applicable or Passed, or
install, enable, pay for or transmit data to a replacement without authorization.

Follow Core [review-evidence](../vendor/engineering-workflow-core/contracts/review-and-security.md#review-evidence)
when handing off or reading back external checks: bind revision/diff/scope, the
missing check, reason/coverage, owner or explicit unassigned status, evidence
location/pending status and affected delivery action. Unassigned is not formal
Deferred and does not release a gate. Accept matching evidence only for its
covered portion. Required delivery gates await matching evidence or a formal
exception that effective policy permits and an authorized decision-maker approves
for this candidate/check/action. Keep the basis, authority, decision, scope,
reason and residual risk in the existing report; an exception is not a scan Pass
or agent risk acceptance and cannot waive mandatory obligations, independent
review, exact-head or action authority. Ordinary review does not replace a
required scan. Continue only independent, authorized, safe work while a gap is open.
This adapter adds no automatic exception enforcement or receipt schema.

After a change, reassess affected paths and assumptions;
retest/review/rescan proportionally and reuse only provably unaffected evidence
with recorded rationale and coverage. Widen for changed trust boundaries or
uncertain impact. Merge Review checks sufficient current final-candidate evidence,
not a mechanical full-repository deep scan. A changed head still requires complete
base-to-head Merge Review; preserve sealed results and unresolved failure history.
