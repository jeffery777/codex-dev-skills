# Human Gate Policy

Require human approval when the action is not already authorized within its
current target and scope:

- destructive actions
- commits, and external writes or disclosures such as push, PR creation,
  publication, immutable thread-share links, merge, deploy, platform comments,
  or review submissions
- public contract changes when behavior is ambiguous
- data model, migration, payment, permission, or privacy-sensitive changes
- broad scope expansion
- direct updates to a protected or shared trunk branch

An initial delegated objective can authorize research, planning, implementation, local verification, review, and docs sync when the scope is clear. It does not automatically authorize external writes or destructive actions.

An explicit instruction authorizes the stated action; do not ask for the same
approval again while target, scope, current state and risk remain consistent.
Resolve discoverable IDs and prepare the concrete result before any necessary
approval. Reversible local or UI operations already requested by the user may
proceed after target verification. Changed scope, ambiguity, destructive effects
or a newly material risk requires a new decision; runtime capability alone is
never authorization.

When stopping, explain the decision needed, one concrete risk, and the lowest-risk next option.

Apply `reusable-workflow-contract.md` Decision And Stop Conditions. A risk-domain
name alone does not block assigned read-only work. Preserve exact authorization
and required verification for actions; a passing test, scan or review is not
authorization. When authorization is already valid, internal phase transitions
do not create new approval requests. For the selected GitHub profile, authorized
receipt publication/readback precedes that receipt's dedicated-App verdict;
merge still requires the complete gate and fresh readback. This ordering neither
changes the runtime approval system nor permits bypassing a tool rejection.
