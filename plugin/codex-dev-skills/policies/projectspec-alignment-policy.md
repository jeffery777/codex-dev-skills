# ProjectSpec Alignment Policy

Runtime compatibility: shared

Use this policy for a project spec, implementation plan, DoD, or explicit user
request. It is a lightweight recording convention for the existing Core duties,
not a second requirements system. Follow the selected
[engineering workflow contract](engineering-workflow-contract.md) and its fixed
Core loading rules; Core remains the source of shared obligations.

## Alignment Rules

- Read the applicable request, spec and plan before implementation. Map each
  task slice to its requirement, DoD item, or explicit user request.
- In the existing plan or task brief, connect the requirement source, conditions
  to preserve, and planned verification. During implementation and review, carry
  that connection into the existing report with actual results and remaining gaps.
- Keep facts, assumptions and unresolved source conflicts distinct. A summary
  or inferred preference does not replace the applicable source. Resolve material
  source-of-truth conflicts before dependent behavior changes under Core's
  authorization/stops contract; an apparently low-risk correction does not grant
  authority to choose new product semantics. Independent authorized work may continue.
- Do not silently expand product scope. For findings, use Core's existing
  `requirement_relation`, `REQ-GAP` and disposition rules through the engineering
  contract's fixed review/security reading. This convention neither redefines
  those rules nor weakens required safety, data-loss, authorization or integrity
  blockers. A finding or a completed record does not authorize extra work.
- Update docs or status files when the repo policy requires it. Preserve existing
  required review, verification and exact-head duties.

## Lightweight Record

Use a short paragraph or bullets in an existing plan, brief or report:

- **Source:** the applicable user request or document location, with version or
  revision when needed to distinguish conflicting or changing sources. Reference
  private material only in an appropriate private record, not in public artifacts.
- **Conditions to preserve:** the requested outcome and relevant limits, existing
  behavior, compatibility or safety conditions that the change must retain.
- **Verification and result:** the check that covers each relevant condition;
  before execution, mark it planned. Afterwards, link observed evidence, covered
  and uncovered requirements, and skipped, failed or unverified checks with reasons.

For a small change, one sentence per item can suffice. No new requirement IDs,
mandatory wiki, separate file, schema, ledger or gate is required. Reuse an
existing project's format and still satisfy any stricter applicable requirements.
For example, a bounded bug fix can name the request, the existing behavior to
retain, and the regression test plus its observed result. Do not claim coverage
from test success alone when a condition has not been checked.

## Related References

Check references in proportion to the change's actual scope and risk. Start with
changed behavior, symbols, paths, commands or contracts and their relevant callers,
consumers, docs, tests and generated artifacts. Check both references the changed
material relies on and references that rely on it. Expand when an affected boundary
or uncertainty requires it; do not require a whole-repository reference scan for
every small edit. Search results are discovery hints, not proof of complete coverage.

A path or command rename needs its affected usages checked. A behavior or contract
change needs relevant upstream/downstream conditions checked. A spelling-only edit
can confirm unchanged meaning and inspect only affected references. Record the
checked scope and remaining uncertainty briefly; unavailable evidence stays
unverified. Reassess affected checks when requirements or scope change, preserving
still-applicable evidence under Core's existing evidence lifecycle.

## Reporting

Reports should state, using the compact record above rather than duplicating it:

- source-of-truth files or user request read
- conditions preserved and requirements covered
- requirements not covered, with verification gaps or reasons
- related-reference scope checked
- assumptions and open product or technical decisions
