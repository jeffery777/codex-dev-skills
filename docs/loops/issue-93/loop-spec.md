# Issue 93: Cost-aware GPT-5.6 Agent Routing

## Objective

Extend Loop Engineering V2a with cost-aware custom-agent selection that uses
the lowest verified GPT-5.6 capability tier suitable for the assigned work and
escalates only when task evidence or failed verification requires it.

GitHub issue: <https://github.com/jeffery777/codex-dev-skills/issues/93>

The feature prepares one part of a later `v0.7.0` release. Release metadata,
tag creation, publication, and global installation remain separate human
gates.

## Source Of Truth And Authority

Model and reasoning selection changes execution quality, latency, and usage;
it does not change task scope, repository authority, sandbox permissions,
external-write authority, review requirements, human gates, or completion
criteria. Current-session runtime facts remain required for exact model and
reasoning availability.

The existing workflow capability classes remain authoritative for work shape
and sandbox expectations:

- `fast-read-explorer`: read-only search, extraction, summarization, and
  evidence gathering;
- `balanced-worker`: bounded workspace edits and focused verification;
- `deep-reviewer`: read-only deep analysis and review;
- `security-reviewer`: read-only security and authority-boundary review.

Cost-aware model tiers are a separate routing dimension and cannot widen a
capability class.

## Capability Tiers

The ordered tiers are:

1. `mechanical`: `gpt-5.6-luna` with low reasoning for clear, repeatable,
   high-volume read-only work;
2. `efficient`: `gpt-5.6-terra` with low reasoning for bounded exploration and
   codebase mapping;
3. `everyday`: `gpt-5.6-terra` with medium reasoning for routine coding,
   tests, documentation, and bounded fixes;
4. `advanced`: `gpt-5.6-sol` with medium reasoning for difficult but bounded
   implementation requiring stronger cross-file judgment;
5. `deep`: `gpt-5.6-sol` with high reasoning for difficult review,
   architecture, migration, public-contract, and security work;
6. `exceptional`: `gpt-5.6-sol` with xhigh reasoning for narrowly defined
   quality-first research or orchestration where the task evidence justifies
   the additional usage.

These are replaceable runtime mappings, not permanent provider assumptions.
The registry must preserve exact model IDs and reasoning efforts, and preflight
must reject unavailable or unsupported mappings instead of guessing aliases.

## Routing Contract

The cost-aware route must record both:

- `capability_class`, which owns sandbox and allowed workflow scope; and
- `capability_tier`, which owns the minimum model/reasoning requirement.

The route input adds an explicit workload kind so mechanical work, exploration,
implementation, review, security review, and exceptional research are not
inferred from task names or cost sensitivity alone. Version 1 route inputs and
receipts remain valid through a compatibility path with their existing
four-class behavior. Version 2 inputs require the workload kind and emit tier
evidence.

Non-compensatory rules:

- security risk always selects `security-reviewer` at no less than `deep`;
- data, migration, public-contract, high-risk, or broad-write work cannot be
  downgraded by latency or cost preferences;
- bounded routine writes may use `everyday`; bounded writes needing deep
  reasoning use `advanced` rather than a read-only reviewer;
- `exceptional` requires an explicit research/orchestration workload plus
  multiple quality-first triggers and is never selected merely because work is
  multi-step;
- Luna high/xhigh and Terra xhigh are not default profiles.

## Profile Selection And Fallback

Within a capability class, select the lowest available profile whose tier is
at least the required tier. Selection uses registry-defined tier rank and exact
validated profile evidence, never alphabetical filename order.

Fallback order is:

1. the lowest-cost verified profile in the same class that meets or exceeds
   the required tier;
2. a parent/default session explicitly reporting the required class and tier;
3. sequential current-session execution explicitly reporting the required
   class and tier;
4. a human gate when the required high-risk or exceptional capability cannot
   be satisfied safely.

A lower tier cannot silently satisfy a higher-tier request. A higher tier used
for a lower-tier task is recorded as cost-degraded execution, not as an
equivalent optimum.

## In Scope

- versioned cost-aware route classification and receipts;
- tier-aware profile registry, preflight, fallback, and integration checks;
- Luna-low mechanical reader, Terra-low explorer, Terra-medium balanced
  worker, Sol-medium advanced worker, Sol-high deep/security reviewers, and a
  narrow Sol-xhigh exceptional researcher;
- installer, catalog, templates, examples, policy, runtime, and rollback docs;
- defensive, local-first security-reviewer instructions that prefer static
  analysis, local fixtures, negative tests, synthetic inputs, and minimal
  non-invasive validation;
- deterministic unit, CLI, installer, and routing eval coverage;
- compatibility tests for route contract version 1, no-profile operation, and
  V1/V2a/V2b fallback behavior.

## Out Of Scope

- machine-local `~/.codex/config.toml` changes;
- measured pricing claims not provided by current runtime evidence;
- automatic global profile installation;
- classifier evasion, concealed intent, or access to or mutation of systems
  outside the assigned local scope;
- replacement of externally installed Codex Security plugin workflows;
- production external-memory adapters or V2c work;
- commit, push, PR creation, merge, tag, release, deploy, or publication
  without the corresponding human gate.

## Definition Of Done

- class and tier are independently validated and receipt-bound;
- profile selection is deterministic and cost ordered, not name ordered;
- routine implementation selects Terra medium when its exact mapping is
  available;
- advanced bounded implementation selects Sol medium without widening scope;
- mechanical and exploration routes distinguish Luna low from Terra low;
- deep/security hard triggers remain non-compensatory;
- security validation falls back to safer local evidence or records an explicit
  verification limit when runtime policy rejects a path, without weakening the
  finding or attempting to evade the policy;
- exceptional xhigh routing is narrow and fails safe;
- compatible version 1 inputs and receipts retain their documented behavior;
- installer/profile collision, digest, sandbox non-widening, and exact-ID
  checks pass;
- focused tests, full repository validation, code/docs review, security diff
  review, and PR-readiness evidence are complete;
- no release metadata or tag is changed in the feature branch.

## Human Gates

Stop for product-semantic ambiguity, an incompatible route-contract migration,
unverified model/effort availability, sandbox widening, source-of-truth
conflict, destructive action, global installation, external publication,
merge, tag, release, deploy, or final independent approval.
