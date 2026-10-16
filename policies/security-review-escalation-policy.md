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

Project policy may specialize timing, depth, triggers and justified allowed
exceptions without weakening mandatory safety, independence, exact-head or
authority requirements. After a change, reassess affected paths and assumptions;
retest/review/rescan proportionally and reuse only provably unaffected evidence
with recorded rationale and coverage. Widen for changed trust boundaries or
uncertain impact. Merge Review checks sufficient current final-candidate evidence,
not a mechanical full-repository deep scan. A changed head still requires complete
base-to-head Merge Review; preserve sealed results and unresolved failure history.
